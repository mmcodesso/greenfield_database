from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest
import yaml

from generator_dataset.main import manufactured_fg_flow_diagnostics
from generator_dataset.manufacturing import manufacturing_capacity_diagnostics_by_code
from generator_dataset.main import build_full_dataset, build_phase1, build_phase23
from generator_dataset.master_data import STANDARD_LABOR_HOURS_RANGE, manufacturing_staffing_targets
from generator_dataset.planning import manufactured_planning_diagnostics
from generator_dataset.settings import load_settings
from generator_dataset.workforce_capacity import (
    DIRECT_MANUFACTURING_TITLES,
    STANDARD_MANUFACTURING_SHIFT_HOURS,
)


@pytest.fixture(scope="session")
def phase23_4_one_year_clean_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("phase23_4_one_year_clean")
    settings = load_settings("config/settings.yaml")
    payload = dict(vars(settings))
    payload.update({
        "anomaly_mode": "none",
        "export_sqlite": False,
        "export_excel": False,
        "export_support_excel": False,
        "export_csv_zip": False,
        "export_reports": False,
        "fiscal_year_end": "2026-12-31",
        "generation_log_path": str(workdir / "generation.log"),
    })

    config_path = workdir / "settings_phase23_4_one_year.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    context = build_full_dataset(str(config_path))
    return {
        "context": context,
        "workdir": workdir,
        "generation_log_path": Path(payload["generation_log_path"]),
    }


def test_phase23_4_phase1_staffing_targets_default_and_validation() -> None:
    default_context = build_phase1("config/settings.yaml")
    validation_context = build_phase1("config/settings_validation.yaml")

    for context in [default_context, validation_context]:
        expected = manufacturing_staffing_targets(int(context.settings.employee_count))
        assert expected is not None
        active_employees = context.tables["Employee"][context.tables["Employee"]["IsActive"].astype(int).eq(1)].copy()
        title_counts = active_employees["JobTitle"].value_counts().to_dict()
        for title, expected_count in expected.items():
            assert int(title_counts.get(title, 0)) == expected_count
        for title in ["Production Manager", "Production Supervisor", "Production Planner"]:
            assert int(title_counts.get(title, 0)) == 1


def test_phase23_4_manufactured_item_hours_and_conversion_costs_are_calibrated() -> None:
    context = build_phase23("config/settings_validation.yaml", validation_scope="full")
    items = context.tables["Item"].copy()
    manufactured_sellable = items[
        items["SupplyMode"].eq("Manufactured")
        & items["RevenueAccountID"].notna()
    ].copy()

    assert not manufactured_sellable.empty

    for row in manufactured_sellable.itertuples(index=False):
        item_group = str(row.ItemGroup)
        original_hours_high = float(STANDARD_LABOR_HOURS_RANGE[item_group][1])
        assert float(row.StandardLaborHoursPerUnit) <= round(original_hours_high * 0.95, 2) + 0.01
        expected_conversion_cost = round(
            float(row.StandardDirectLaborCost)
            + float(row.StandardVariableOverheadCost)
            + float(row.StandardFixedOverheadCost),
            2,
        )
        assert round(float(row.StandardConversionCost), 2) == expected_conversion_cost


def test_phase23_4_clean_validation_build_stays_green() -> None:
    context = build_phase23("config/settings_validation.yaml", validation_scope="full")
    phase23 = context.validation_results["phase23"]

    assert phase23["exceptions"] == []
    assert phase23["planning_controls"]["exception_count"] == 0


def test_phase23_4_one_year_clean_build_hits_manufacturing_targets(
    phase23_4_one_year_clean_artifacts: dict[str, object],
) -> None:
    context = phase23_4_one_year_clean_artifacts["context"]
    phase23 = context.validation_results["phase23"]
    fg_flow = pd.DataFrame(manufactured_fg_flow_diagnostics(context))
    recommendations = context.tables["SupplyPlanRecommendation"].copy()
    fiscal_year_end = pd.Timestamp("2026-12-31")
    release_dates = pd.to_datetime(recommendations["ReleaseByDate"], errors="coerce")
    recommended_quantities = pd.to_numeric(recommendations["RecommendedOrderQuantity"], errors="coerce").fillna(0.0)

    overdue_mask = (
        recommendations["RecommendationStatus"].eq("Planned")
        & release_dates.notna()
        & release_dates.le(fiscal_year_end)
        & recommended_quantities.gt(0)
    )
    overdue_purchase = recommendations[overdue_mask & recommendations["RecommendationType"].eq("Purchase")]
    overdue_manufacture = recommendations[overdue_mask & recommendations["RecommendationType"].eq("Manufacture")]

    assert phase23["planning_controls"]["exception_count"] == 0
    assert phase23["workforce_planning_controls"]["exception_count"] == 0
    assert phase23["time_clock_controls"]["exception_count"] == 0
    assert overdue_purchase.empty
    assert overdue_manufacture.empty

    active_direct_workers = context.tables["Employee"][
        context.tables["Employee"]["IsActive"].astype(int).eq(1)
        & context.tables["Employee"]["PayClass"].eq("Hourly")
        & context.tables["Employee"]["JobTitle"].isin(DIRECT_MANUFACTURING_TITLES)
    ].copy()
    work_centers = context.tables["WorkCenter"].copy()
    nominal_capacity = work_centers.set_index("WorkCenterCode")["NominalDailyCapacityHours"].astype(float).to_dict()
    total_nominal_capacity = sum(nominal_capacity.values())
    expected_nominal_capacity = float(len(active_direct_workers)) * STANDARD_MANUFACTURING_SHIFT_HOURS

    assert expected_nominal_capacity > 0
    assert abs(total_nominal_capacity - expected_nominal_capacity) / expected_nominal_capacity <= 0.05

    target_share_bands = {
        "ASSEMBLY": (0.40, 0.50),
        "FINISH": (0.22, 0.30),
        "CUT": (0.15, 0.22),
        "PACK": (0.08, 0.12),
        "QA": (0.03, 0.06),
    }
    for work_center_code, (low, high) in target_share_bands.items():
        share = float(nominal_capacity.get(work_center_code, 0.0)) / total_nominal_capacity
        assert low <= share <= high

    monthly_diagnostics = {
        month: manufacturing_capacity_diagnostics_by_code(context, 2026, month)
        for month in range(1, 13)
    }
    assembly_median = float(pd.Series([
        monthly_diagnostics[month]["ASSEMBLY"]["monthly_utilization_pct"]
        for month in range(1, 13)
    ]).median())
    finish_median = float(pd.Series([
        monthly_diagnostics[month]["FINISH"]["monthly_utilization_pct"]
        for month in range(1, 13)
    ]).median())
    pack_median = float(pd.Series([
        monthly_diagnostics[month]["PACK"]["monthly_utilization_pct"]
        for month in range(1, 13)
    ]).median())
    assembly_peak_loaded_months = sum(
        1
        for month in range(1, 13)
        if float(monthly_diagnostics[month]["ASSEMBLY"]["monthly_utilization_pct"]) >= 85.0
    )
    finish_peak_loaded_months = sum(
        1
        for month in range(1, 13)
        if float(monthly_diagnostics[month]["FINISH"]["monthly_utilization_pct"]) >= 85.0
    )

    assert 70.0 <= assembly_median <= 85.0
    assert 70.0 <= finish_median <= 85.0
    assert 45.0 <= pack_median < 85.0
    assert assembly_peak_loaded_months >= 5
    assert finish_peak_loaded_months >= 5

    assert not fg_flow.empty
    completion_to_shipment_ratio = round(
        float(fg_flow["CompletionCost"].sum()) / float(fg_flow["ShipmentCost"].sum()),
        2,
    )
    year_end_group_gaps = fg_flow.loc[fg_flow["Period"].eq("2026-12")].set_index("ItemGroup")["CostGap"].to_dict()

    assert 0.95 <= completion_to_shipment_ratio <= 1.35
    assert float(year_end_group_gaps.get("Furniture", 0.0)) <= 750000.0
    assert float(year_end_group_gaps.get("Lighting", 0.0)) <= 350000.0


def test_phase23_4_manufactured_planning_uses_lot_for_lot_and_non_stacked_backlog(
    phase23_4_one_year_clean_artifacts: dict[str, object],
) -> None:
    context = phase23_4_one_year_clean_artifacts["context"]
    planning_rows = pd.DataFrame(manufactured_planning_diagnostics(context))
    policies = context.tables["InventoryPolicy"].copy()
    items = context.tables["Item"][["ItemID", "SupplyMode", "RevenueAccountID", "LifecycleStatus", "ItemGroup"]].copy()
    manufactured_sellable_items = items[
        items["SupplyMode"].eq("Manufactured")
        & items["RevenueAccountID"].notna()
    ].copy()

    assert not planning_rows.empty
    assert planning_rows["PolicyType"].eq("Lot-for-Lot").all()
    assert planning_rows["GrossRequirementQuantity"].round(2).equals(
        planning_rows[["ForecastQuantity", "BacklogQuantity"]].max(axis=1).round(2)
    )
    assert float(planning_rows["LotSizeUpliftQuantity"].abs().max()) <= 0.01
    assert float((planning_rows["RecommendedOrderQuantity"] - planning_rows["NetRequirementQuantity"]).abs().max()) <= 0.01

    policy_rows = policies.merge(manufactured_sellable_items, on="ItemID", how="inner")
    assert not policy_rows.empty
    assert policy_rows["PolicyType"].eq("Lot-for-Lot").all()

    core_rows = policy_rows[policy_rows["LifecycleStatus"].astype(str).eq("Core")]
    seasonal_rows = policy_rows[policy_rows["LifecycleStatus"].astype(str).eq("Seasonal")]
    if not core_rows.empty:
        assert core_rows["TargetDaysSupply"].astype(int).eq(14).all()
        assert core_rows["SafetyStockQuantity"].astype(float).eq(10.0).all()
    if not seasonal_rows.empty:
        assert seasonal_rows["TargetDaysSupply"].astype(int).eq(18).all()
        assert seasonal_rows["SafetyStockQuantity"].astype(float).eq(14.0).all()


def test_phase23_4_year_end_planning_keeps_a_forward_operating_horizon(
    phase23_4_one_year_clean_artifacts: dict[str, object],
) -> None:
    context = phase23_4_one_year_clean_artifacts["context"]
    recommendations = context.tables["SupplyPlanRecommendation"].copy()
    fiscal_end = pd.Timestamp(context.settings.fiscal_year_end).normalize()
    final_month_label = fiscal_end.strftime("%Y-%m")
    recommendation_dates = pd.to_datetime(recommendations["RecommendationDate"], errors="coerce")
    need_by_dates = pd.to_datetime(recommendations["NeedByDate"], errors="coerce")
    recommended_quantities = pd.to_numeric(
        recommendations["RecommendedOrderQuantity"],
        errors="coerce",
    ).fillna(0.0)

    final_month_rows = recommendations[
        recommendation_dates.dt.strftime("%Y-%m").eq(final_month_label)
        & recommended_quantities.gt(0)
    ].copy()
    forward_horizon_rows = final_month_rows[
        need_by_dates.loc[final_month_rows.index].gt(fiscal_end)
    ].copy()

    assert not final_month_rows.empty
    assert not forward_horizon_rows.empty
    assert forward_horizon_rows["RecommendationStatus"].isin(["Planned", "Converted"]).all()
    assert pd.to_datetime(forward_horizon_rows["BucketWeekStartDate"], errors="coerce").max() > fiscal_end


def test_phase23_4_one_year_clean_build_smooths_opening_state_purchasing(
    phase23_4_one_year_clean_artifacts: dict[str, object],
) -> None:
    context = phase23_4_one_year_clean_artifacts["context"]
    fiscal_start = pd.Timestamp(context.settings.fiscal_year_start).normalize()
    first_period_label = fiscal_start.strftime("%Y-%m")
    steady_state_periods = [
        (fiscal_start + pd.DateOffset(months=offset)).strftime("%Y-%m")
        for offset in range(1, 6)
    ]

    def _median_ratio(values: dict[str, float]) -> tuple[float, float, float]:
        first_value = round(float(values.get(first_period_label, 0.0)), 2)
        steady_values = [float(values.get(period, 0.0)) for period in steady_state_periods if float(values.get(period, 0.0)) > 0]
        steady_state_median = round(float(pd.Series(steady_values).median()), 2) if steady_values else 0.0
        ratio = round(first_value / steady_state_median, 2) if steady_state_median > 0 else 0.0
        return first_value, steady_state_median, ratio

    purchase_orders = context.tables["PurchaseOrder"]
    po_monthly = {
        str(period): round(float(amount), 2)
        for period, amount in purchase_orders.groupby(
            purchase_orders["OrderDate"].astype(str).str.slice(0, 7)
        )["OrderTotal"].sum().items()
    }

    goods_receipts = context.tables["GoodsReceipt"]
    goods_receipt_lines = context.tables["GoodsReceiptLine"]
    goods_receipt_monthly: dict[str, float] = {}
    if not goods_receipts.empty and not goods_receipt_lines.empty:
        goods_receipt_activity = goods_receipt_lines.merge(
            goods_receipts[["GoodsReceiptID", "ReceiptDate"]],
            on="GoodsReceiptID",
            how="left",
        )
        goods_receipt_monthly = {
            str(period): round(float(amount), 2)
            for period, amount in goods_receipt_activity.groupby(
                goods_receipt_activity["ReceiptDate"].astype(str).str.slice(0, 7)
            )["ExtendedStandardCost"].sum().items()
        }

    purchase_invoices = context.tables["PurchaseInvoice"]
    purchase_invoice_monthly = {
        str(period): round(float(amount), 2)
        for period, amount in purchase_invoices.groupby(
            purchase_invoices["InvoiceDate"].astype(str).str.slice(0, 7)
        )["GrandTotal"].sum().items()
    }

    gl = context.tables["GLEntry"]
    accounts = context.tables["Account"][["AccountID", "AccountNumber"]].copy()
    journal_entries = context.tables["JournalEntry"][["JournalEntryID", "EntryType"]].copy()
    gl_accounts = gl.merge(accounts, on="AccountID", how="left").merge(
        journal_entries.rename(columns={"JournalEntryID": "SourceDocumentID", "EntryType": "JournalEntryType"}),
        on="SourceDocumentID",
        how="left",
    )
    gl_accounts = gl_accounts[
        ~(
            gl_accounts["SourceDocumentType"].eq("JournalEntry")
            & gl_accounts["JournalEntryType"].eq("Opening")
        )
    ].copy()
    ap_monthly = {
        str(period): round(float(amount), 2)
        for period, amount in gl_accounts[
            gl_accounts["AccountNumber"].astype(str).eq("2010")
        ].groupby(
            gl_accounts.loc[
                gl_accounts["AccountNumber"].astype(str).eq("2010"), "PostingDate"
            ].astype(str).str.slice(0, 7)
        ).apply(lambda rows: (rows["Credit"].astype(float) - rows["Debit"].astype(float)).sum()).items()
    }

    assert _median_ratio(po_monthly)[2] <= 1.5
    assert _median_ratio(goods_receipt_monthly)[2] <= 1.5
    assert _median_ratio(purchase_invoice_monthly)[2] <= 1.5
    assert _median_ratio(ap_monthly)[2] <= 1.5


def test_phase23_4_generation_log_contains_load_diagnostics_and_conversion_logging(
    phase23_4_one_year_clean_artifacts: dict[str, object],
) -> None:
    log_text = phase23_4_one_year_clean_artifacts["generation_log_path"].read_text(encoding="utf-8")

    assert "OPENING PIPELINE | opening_candidates=" in log_text
    assert "MANUFACTURING LOAD | 2026-02 |" in log_text
    assert "converted_load_assembly=" in log_text
    assert "converted_load_pack=" in log_text
    assert "expired_load_assembly=" in log_text
    assert "available_hours_assembly=" in log_text
    assert "available_hours_pack=" in log_text
    assert "opening_fg_seeded_from_prefiscal=" in log_text
    assert "CAPACITY DIAGNOSTIC | 2026-01 | work_center=ASSEMBLY |" in log_text
    assert "CAPACITY DIAGNOSTIC | 2026-01 | work_center=FINISH |" in log_text
    assert "nominal_daily_capacity_share=" in log_text
    assert "monthly_utilization_pct=" in log_text
    assert "OPENING BALANCE CALIBRATION | fiscal_start=2026-01-01 |" in log_text
    assert "OPENING INVENTORY DIAGNOSTIC | item_group=Raw Materials | supply_mode=Purchased |" in log_text
    assert "OPENING STATE SHOCK | metric=purchase_order_total | first_period=2026-01 |" in log_text
    assert "OPENING STATE SHOCK | metric=purchase_invoice_total | first_period=2026-01 |" in log_text
    assert "OPENING STATE DRIVER MIX | window=2025-12_to_2026-02 | driver_type=Component Demand | recommendation_type=Purchase |" in log_text
    assert "MANUFACTURED PLANNING DIAGNOSTIC | recommendation_month=2026-01 |" in log_text
    assert "policy_type=Lot-for-Lot" in log_text
    assert "MANUFACTURED FG FLOW | period=2026-12 | item_group=Furniture |" in log_text
    assert "production_to_shipment_ratio=" in log_text

    pattern = re.compile(
        r"MANUFACTURING CONVERSION \| 2026-(\d{2}) \| eligible_planned=(\d+) \| converted=(\d+) \| expired=(\d+) .*? conversion_rate=([0-9.]+)"
    )
    matches = pattern.findall(log_text)
    assert matches

    for month, eligible, converted, expired, rate in matches:
        eligible_count = int(eligible)
        converted_count = int(converted)
        expired_count = int(expired)
        conversion_rate = float(rate)
        assert 0.0 <= conversion_rate <= 1.0
        assert converted_count + expired_count <= eligible_count
