from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from generator_dataset.settings import GenerationContext
from generator_dataset.utils import money


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAPEX_PLAN_PATH = REPO_ROOT / "config" / "capex_plan.yaml"


@dataclass(frozen=True)
class FixedAssetOpeningProfile:
    asset_code: str
    asset_account_number: str
    description: str
    asset_category: str
    behavior_group: str
    depreciation_debit_account_number: str
    gross_opening_balance: float
    accumulated_depreciation_account_number: str | None
    opening_accumulated_depreciation: float
    useful_life_months: int
    cost_center_name: str
    warehouse_name: str | None = None
    work_center_code: str | None = None


def _normalize_capex_plan(raw: dict[str, Any]) -> dict[str, Any]:
    item_definitions = list(raw.get("item_definitions", []) or [])
    opening_assets = list(raw.get("opening_assets", []) or [])
    events = list(raw.get("events", []) or [])
    if not item_definitions:
        raise ValueError("capex_plan.yaml must define item_definitions.")
    return {
        "item_definitions": item_definitions,
        "opening_assets": opening_assets,
        "events": events,
    }


@lru_cache(maxsize=1)
def load_capex_plan(capex_plan_path: str | Path = DEFAULT_CAPEX_PLAN_PATH) -> dict[str, Any]:
    resolved_path = Path(capex_plan_path)
    with resolved_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"CAPEX plan must contain a mapping: {resolved_path}")
    return _normalize_capex_plan(raw)


def capex_item_definitions(capex_plan_path: str | Path = DEFAULT_CAPEX_PLAN_PATH) -> dict[str, dict[str, Any]]:
    return {
        str(item["item_code"]): dict(item)
        for item in load_capex_plan(capex_plan_path)["item_definitions"]
    }


def fixed_asset_opening_profiles(capex_plan_path: str | Path = DEFAULT_CAPEX_PLAN_PATH) -> dict[str, FixedAssetOpeningProfile]:
    item_map = capex_item_definitions(capex_plan_path)
    profiles: dict[str, FixedAssetOpeningProfile] = {}
    for asset in load_capex_plan(capex_plan_path)["opening_assets"]:
        item = item_map[str(asset["item_code"])]
        asset_code = str(asset["asset_code"])
        profiles[asset_code] = FixedAssetOpeningProfile(
            asset_code=asset_code,
            asset_account_number=str(item["asset_account_number"]),
            description=str(asset["asset_description"]),
            asset_category=str(item["asset_category"]),
            behavior_group=str(item["behavior_group"]),
            depreciation_debit_account_number=str(item["depreciation_account_number"]),
            gross_opening_balance=float(asset["original_cost"]),
            accumulated_depreciation_account_number=(
                str(item["accumulated_depreciation_account_number"])
                if item.get("accumulated_depreciation_account_number")
                else None
            ),
            opening_accumulated_depreciation=float(asset.get("opening_accumulated_depreciation", 0.0) or 0.0),
            useful_life_months=int(item["useful_life_months"]),
            cost_center_name=str(item["cost_center_name"]),
            warehouse_name=(
                str(asset.get("warehouse_name") or item.get("warehouse_name"))
                if asset.get("warehouse_name") or item.get("warehouse_name")
                else None
            ),
            work_center_code=(
                str(asset.get("work_center_code") or item.get("work_center_code"))
                if asset.get("work_center_code") or item.get("work_center_code")
                else None
            ),
        )
    return profiles


def depreciable_fixed_asset_profiles(capex_plan_path: str | Path = DEFAULT_CAPEX_PLAN_PATH) -> dict[str, FixedAssetOpeningProfile]:
    return {
        asset_code: profile
        for asset_code, profile in fixed_asset_opening_profiles(capex_plan_path).items()
        if profile.accumulated_depreciation_account_number and profile.useful_life_months > 0
    }


def fixed_asset_opening_balance_amounts(capex_plan_path: str | Path = DEFAULT_CAPEX_PLAN_PATH) -> dict[str, tuple[str, float, float]]:
    amounts: dict[str, tuple[str, float, float]] = {}
    gross_totals: dict[str, float] = {}
    accumulated_totals: dict[str, float] = {}
    description_by_account: dict[str, str] = {}

    for profile in fixed_asset_opening_profiles(capex_plan_path).values():
        gross_totals[profile.asset_account_number] = money(
            float(gross_totals.get(profile.asset_account_number, 0.0)) + float(profile.gross_opening_balance)
        )
        description_by_account.setdefault(profile.asset_account_number, f"{profile.asset_category} opening balance")
        if profile.accumulated_depreciation_account_number:
            accumulated_totals[profile.accumulated_depreciation_account_number] = money(
                float(accumulated_totals.get(profile.accumulated_depreciation_account_number, 0.0))
                + float(profile.opening_accumulated_depreciation)
            )
            description_by_account.setdefault(
                profile.accumulated_depreciation_account_number,
                f"Accumulated depreciation {profile.asset_category.lower()} opening balance",
            )

    for account_number, total in gross_totals.items():
        amounts[account_number] = (description_by_account[account_number], float(total), 0.0)
    for account_number, total in accumulated_totals.items():
        amounts[account_number] = (description_by_account[account_number], 0.0, float(total))
    return amounts


def capex_plan_events(capex_plan_path: str | Path = DEFAULT_CAPEX_PLAN_PATH) -> list[dict[str, Any]]:
    return [dict(event) for event in load_capex_plan(capex_plan_path)["events"]]


def capex_item_count(capex_plan_path: str | Path = DEFAULT_CAPEX_PLAN_PATH) -> int:
    return len(load_capex_plan(capex_plan_path)["item_definitions"])


def _account_number_lookup(context: GenerationContext) -> dict[int, str]:
    accounts = context.tables["Account"]
    if accounts.empty:
        return {}
    return (
        accounts.assign(AccountNumber=accounts["AccountNumber"].astype(str))
        .set_index("AccountID")["AccountNumber"]
        .astype(str)
        .to_dict()
    )


def _fiscal_start_month(context: GenerationContext) -> pd.Timestamp:
    start = pd.Timestamp(context.settings.fiscal_year_start).normalize()
    return pd.Timestamp(year=start.year, month=start.month, day=1)


def _month_start(year: int, month: int) -> pd.Timestamp:
    return pd.Timestamp(year=year, month=month, day=1)


def _months_between(start: pd.Timestamp, end: pd.Timestamp) -> int:
    return int((end.year - start.year) * 12 + (end.month - start.month))


def monthly_depreciation_entries(context: GenerationContext, year: int, month: int) -> list[dict[str, Any]]:
    fixed_assets = context.tables["FixedAsset"]
    if fixed_assets.empty:
        return []

    account_numbers = _account_number_lookup(context)
    period_start = _month_start(year, month)
    fiscal_start_month = _fiscal_start_month(context)
    entries: list[dict[str, Any]] = []

    for asset in fixed_assets.itertuples(index=False):
        useful_life_months = int(asset.UsefulLifeMonths)
        original_cost = float(asset.OriginalCost)
        residual_value = float(asset.ResidualValue)
        if useful_life_months <= 0 or original_cost <= residual_value:
            continue

        monthly_amount = money((original_cost - residual_value) / float(useful_life_months))
        if monthly_amount <= 0:
            continue

        in_service_date = pd.Timestamp(asset.InServiceDate)
        first_depreciation_month = (
            pd.Timestamp(year=in_service_date.year, month=in_service_date.month, day=1) + pd.DateOffset(months=1)
        )
        depreciation_start_month = max(first_depreciation_month, fiscal_start_month)
        if period_start < depreciation_start_month:
            continue

        disposal_month = None
        if pd.notna(asset.DisposalDate):
            disposal_date = pd.Timestamp(asset.DisposalDate)
            disposal_month = pd.Timestamp(year=disposal_date.year, month=disposal_date.month, day=1)
            if period_start >= disposal_month:
                continue

        months_after_opening = _months_between(depreciation_start_month, period_start)
        opening_accumulated = float(asset.OpeningAccumulatedDepreciation)
        months_depreciated_before = int(round(opening_accumulated / monthly_amount)) + max(months_after_opening, 0)
        if months_depreciated_before >= useful_life_months:
            continue

        accumulated_before = money(opening_accumulated + (monthly_amount * max(months_after_opening, 0)))
        remaining_base = money((original_cost - residual_value) - accumulated_before)
        if remaining_base <= 0:
            continue

        accumulated_account_number = account_numbers.get(int(asset.AccumulatedDepreciationAccountID))
        debit_account_number = account_numbers.get(int(asset.DepreciationDebitAccountID))
        if not accumulated_account_number or not debit_account_number:
            continue

        amount = money(min(monthly_amount, remaining_base))
        entries.append({
            "FixedAssetID": int(asset.FixedAssetID),
            "AssetCode": str(asset.AssetCode),
            "AssetDescription": str(asset.AssetDescription),
            "BehaviorGroup": str(asset.BehaviorGroup),
            "DebitAccountNumber": debit_account_number,
            "AccumulatedAccountNumber": accumulated_account_number,
            "CostCenterID": int(asset.CostCenterID) if pd.notna(asset.CostCenterID) else None,
            "Amount": amount,
        })

    return entries


def total_monthly_depreciation(context: GenerationContext, year: int, month: int) -> float:
    return money(sum(float(entry["Amount"]) for entry in monthly_depreciation_entries(context, year, month)))


def monthly_depreciation_by_debit_account(context: GenerationContext, year: int, month: int) -> dict[str, float]:
    totals: dict[str, float] = {}
    for entry in monthly_depreciation_entries(context, year, month):
        debit_account = str(entry["DebitAccountNumber"])
        totals[debit_account] = money(float(totals.get(debit_account, 0.0)) + float(entry["Amount"]))
    return totals


def financed_capex_invoice_ids(context: GenerationContext) -> set[int]:
    events = context.tables["FixedAssetEvent"]
    if events.empty:
        return set()
    matches = events[
        events["PurchaseInvoiceID"].notna()
        & events["FinancingType"].astype(str).eq("Note")
    ]["PurchaseInvoiceID"]
    return set(matches.astype(int).tolist())


def financed_capex_events_for_month(context: GenerationContext, year: int, month: int) -> pd.DataFrame:
    events = context.tables["FixedAssetEvent"]
    if events.empty:
        return events.head(0)
    event_dates = pd.to_datetime(events["EventDate"])
    mask = (
        events["EventType"].astype(str).isin(["Acquisition", "Improvement"])
        & events["FinancingType"].astype(str).eq("Note")
        & event_dates.dt.year.eq(year)
        & event_dates.dt.month.eq(month)
    )
    return events.loc[mask].copy()


def disposal_events_for_month(context: GenerationContext, year: int, month: int) -> pd.DataFrame:
    events = context.tables["FixedAssetEvent"]
    if events.empty:
        return events.head(0)
    event_dates = pd.to_datetime(events["EventDate"])
    mask = (
        events["EventType"].astype(str).eq("Disposal")
        & event_dates.dt.year.eq(year)
        & event_dates.dt.month.eq(month)
    )
    return events.loc[mask].copy()


def debt_schedule_lines_for_month(context: GenerationContext, year: int, month: int) -> pd.DataFrame:
    debt_schedule = context.tables["DebtScheduleLine"]
    if debt_schedule.empty:
        return debt_schedule.head(0)
    payment_dates = pd.to_datetime(debt_schedule["PaymentDate"])
    mask = payment_dates.dt.year.eq(year) & payment_dates.dt.month.eq(month)
    return debt_schedule.loc[mask].copy()
