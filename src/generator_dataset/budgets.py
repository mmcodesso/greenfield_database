from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import pandas as pd

from generator_dataset.accrual_catalog import MONTHLY_ACCRUAL_BASES
from generator_dataset.fixed_assets import (
    capex_item_definitions,
    capex_plan_events,
    fixed_asset_opening_balance_amounts,
    load_capex_plan,
)
from generator_dataset.journals import (
    NONMANUFACTURING_PAYROLL_BURDEN_ACCOUNT,
    PAYROLL_BURDEN_RATE,
    SALARY_ACCOUNT_BY_COST_CENTER,
    monthly_accrual_amount,
    monthly_rent_amount,
    monthly_utilities_amount,
)
from generator_dataset.master_data import (
    approver_employee_id,
    current_role_employee_id,
    eligible_item_mask,
)
from generator_dataset.o2c import (
    customer_collection_factor,
    payment_term_days as customer_payment_term_days,
    resolve_price_list_line,
    resolve_promotion,
)
from generator_dataset.p2p import payment_term_days as supplier_payment_term_days
from generator_dataset.payroll import growth_factor_for_year
from generator_dataset.planning import (
    active_policy_lookup,
    monthly_forecast_targets,
    opening_inventory_diagnostics,
    projected_monthly_procurement_cost,
)
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.settings import GenerationContext
from generator_dataset.utils import money, next_id, qty


LOGGER = logging.getLogger("generator_dataset")

OPENING_BALANCE_AP_MONTHS = 1.0
OPENING_BALANCE_CASH_MONTHS = 1.0
FORWARD_BUDGET_MONTHS = 12
MONTHLY_FORWARD_GROWTH_FACTOR = 1.035 ** (1.0 / 12.0)
ACCOUNTS_RECEIVABLE_COLLECTION_SCALAR = 0.68
ACCOUNTS_PAYABLE_PAYMENT_SCALAR = 0.75
ACCRUED_PAYROLL_FRACTION = 0.25
ACCRUED_EXPENSES_FRACTION = 0.65
SUMMARY_BUDGET_CATEGORIES = {"Revenue", "COGS", "Operating Expense"}


OPENING_BALANCE_AMOUNTS = {
    "1010": ("Cash and cash equivalents opening balance", 450000.00, 0.00),
    "1020": ("Accounts receivable opening balance", 380000.00, 0.00),
    "1040": ("Finished goods inventory opening balance", 720000.00, 0.00),
    "1045": ("Materials and packaging inventory opening balance", 115000.00, 0.00),
    "1050": ("Prepaid expenses opening balance", 60000.00, 0.00),
    "2010": ("Accounts payable opening balance", 0.00, 410000.00),
    "2030": ("Accrued payroll opening balance", 0.00, 95000.00),
    "2040": ("Accrued expenses opening balance", 0.00, 85000.00),
    "3010": ("Common stock opening balance", 0.00, 500000.00),
}

BUDGET_ACCOUNTS_BY_COST_CENTER = {
    "Executive": ["6050", "6080", "6100", "6130", "6180"],
    "Sales": ["4010", "4020", "4030", "4040", "6010", "6150", "6160"],
    "Warehouse": ["6020", "6070", "6090", "6120", "6130", "6210"],
    "Manufacturing": ["6110", "6120", "6130", "6140"],
    "Purchasing": ["6230", "6110", "6140", "6180", "6200"],
    "Administration": ["6030", "6080", "6090", "6100", "6110", "6130", "6140", "6180", "6190", "6200"],
    "Customer Service": ["6040", "6080", "6090", "6110", "6140"],
    "Research and Development": ["6220", "6250", "6140", "6110", "6200"],
    "Marketing": ["6150", "6160", "6240", "6140", "6200"],
    "Design Services": ["4080", "6140", "6200", "6280"],
}


def account_id_by_number(context: GenerationContext, account_number: str) -> int:
    accounts = context.tables["Account"]
    matches = accounts.loc[accounts["AccountNumber"].astype(str) == account_number, "AccountID"]
    if matches.empty:
        raise ValueError(f"Account number {account_number} is not loaded.")
    return int(matches.iloc[0])


def budget_horizon_month_starts(context: GenerationContext) -> list[pd.Timestamp]:
    start = pd.Timestamp(context.settings.fiscal_year_start).normalize().replace(day=1)
    end = pd.Timestamp(context.settings.fiscal_year_end).normalize().replace(day=1) + pd.DateOffset(months=FORWARD_BUDGET_MONTHS)
    return list(pd.date_range(start=start, end=end, freq="MS"))


def budget_horizon_months(context: GenerationContext) -> list[tuple[int, int]]:
    return [(int(month_start.year), int(month_start.month)) for month_start in budget_horizon_month_starts(context)]


def _previous_month(month_start: pd.Timestamp) -> pd.Timestamp:
    return (pd.Timestamp(month_start).normalize().replace(day=1) - pd.DateOffset(months=1)).normalize()


def _next_month(month_start: pd.Timestamp) -> pd.Timestamp:
    return (pd.Timestamp(month_start).normalize().replace(day=1) + pd.DateOffset(months=1)).normalize()


def _month_end(month_start: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(month_start).normalize().replace(day=1) + pd.offsets.MonthEnd(1)


def _month_key(month_start: pd.Timestamp) -> tuple[int, int]:
    month_start = pd.Timestamp(month_start).normalize()
    return int(month_start.year), int(month_start.month)


def _month_days(month_start: pd.Timestamp) -> int:
    return int(_month_end(month_start).day)


def _approved_date_for_year(fiscal_year: int) -> str:
    return f"{int(fiscal_year) - 1}-12-15"


def _opening_balance_map(context: GenerationContext) -> dict[str, float]:
    accounts = context.tables["Account"][["AccountID", "AccountNumber", "AccountType"]].copy()
    journal_entries = context.tables["JournalEntry"][["JournalEntryID", "EntryType"]].copy()
    if accounts.empty or journal_entries.empty or context.tables["GLEntry"].empty:
        return {}

    merged = context.tables["GLEntry"].merge(accounts, on="AccountID", how="left")
    merged = merged.merge(journal_entries, left_on="SourceDocumentID", right_on="JournalEntryID", how="left")
    opening_rows = merged[
        merged["SourceDocumentType"].eq("JournalEntry")
        & merged["EntryType"].astype(str).eq("Opening")
    ].copy()
    if opening_rows.empty:
        return {}

    balances: dict[str, float] = {}
    for row in opening_rows.itertuples(index=False):
        account_number = str(row.AccountNumber)
        if str(row.AccountType) == "Asset":
            amount = float(row.Debit) - float(row.Credit)
        else:
            amount = float(row.Credit) - float(row.Debit)
        balances[account_number] = money(float(balances.get(account_number, 0.0)) + amount)
    return balances


def opening_balance_approver_id(context: GenerationContext) -> int:
    approver_id = current_role_employee_id(context, "Chief Financial Officer", "Controller", "Chief Executive Officer")
    if approver_id is not None:
        return int(approver_id)
    employees = context.tables["Employee"]
    if employees.empty:
        raise ValueError("Generate employees before opening balances.")
    return int(employees.sort_values("EmployeeID").iloc[0]["EmployeeID"])


def build_gl_row(
    context: GenerationContext,
    journal_entry_id: int,
    posting_date: str,
    voucher_number: str,
    created_date: str,
    account_number: str,
    debit: float,
    credit: float,
    description: str,
    created_by_employee_id: int,
) -> dict[str, Any]:
    ts = pd.Timestamp(posting_date)
    return {
        "GLEntryID": next_id(context, "GLEntry"),
        "PostingDate": posting_date,
        "AccountID": account_id_by_number(context, account_number),
        "Debit": money(debit),
        "Credit": money(credit),
        "VoucherType": "JournalEntry",
        "VoucherNumber": voucher_number,
        "SourceDocumentType": "JournalEntry",
        "SourceDocumentID": journal_entry_id,
        "SourceLineID": None,
        "CostCenterID": None,
        "Description": description,
        "CreatedByEmployeeID": created_by_employee_id,
        "CreatedDate": created_date,
        "FiscalYear": int(ts.year),
        "FiscalPeriod": int(ts.month),
    }


def _opening_balance_seed_amounts(
    context: GenerationContext,
) -> tuple[dict[str, tuple[str, float, float]], dict[str, object], float]:
    amounts = {
        account_number: (description, float(debit), float(credit))
        for account_number, (description, debit, credit) in OPENING_BALANCE_AMOUNTS.items()
    }
    amounts.update(fixed_asset_opening_balance_amounts())
    diagnostics = opening_inventory_diagnostics(context)
    projected_procurement_cost = money(projected_monthly_procurement_cost(context))
    value_by_account_number = diagnostics.get("value_by_account_number", {})

    fg_value = money(float(value_by_account_number.get("1040", 0.0)))
    component_value = money(float(value_by_account_number.get("1045", 0.0)))
    if fg_value > 0:
        description, debit, credit = amounts["1040"]
        amounts["1040"] = (description, max(float(debit), fg_value), float(credit))
    if component_value > 0:
        description, debit, credit = amounts["1045"]
        amounts["1045"] = (description, max(float(debit), component_value), float(credit))
    if projected_procurement_cost > 0:
        description, debit, credit = amounts["2010"]
        amounts["2010"] = (
            description,
            float(debit),
            max(float(credit), money(projected_procurement_cost * OPENING_BALANCE_AP_MONTHS)),
        )
        description, debit, credit = amounts["1010"]
        amounts["1010"] = (
            description,
            max(float(debit), money(projected_procurement_cost * OPENING_BALANCE_CASH_MONTHS)),
            float(credit),
        )

    return amounts, diagnostics, projected_procurement_cost


def generate_opening_balances(context: GenerationContext) -> None:
    if context.tables["Account"].empty:
        raise ValueError("Load accounts before opening balances.")
    if not context.tables["JournalEntry"].empty or not context.tables["GLEntry"].empty:
        raise ValueError("Opening balances should be generated before other journal or GL rows.")

    approver_id = opening_balance_approver_id(context)
    opening_amounts, opening_diagnostics, projected_procurement_cost = _opening_balance_seed_amounts(context)
    fiscal_start = pd.Timestamp(context.settings.fiscal_year_start).normalize()
    posting_date = fiscal_start.strftime("%Y-%m-%d")
    opening_date_label = fiscal_start.strftime("%B %d, %Y").replace(" 0", " ")
    voucher_number = f"JE-{fiscal_start.year}-000001"
    created_date = f"{posting_date} 08:00:00"
    approved_date = f"{posting_date} 09:00:00"
    journal_entry_id = next_id(context, "JournalEntry")
    debit_total = sum(amount[1] for amount in opening_amounts.values())
    credit_total = sum(amount[2] for amount in opening_amounts.values())
    retained_earnings_credit = money(debit_total - credit_total)
    if retained_earnings_credit <= 0:
        raise ValueError("Opening balance retained earnings plug must be a credit.")

    journal_record = {
        "JournalEntryID": journal_entry_id,
        "EntryNumber": voucher_number,
        "PostingDate": posting_date,
        "EntryType": "Opening",
        "Description": f"Opening balance entry for {opening_date_label}",
        "TotalAmount": money(debit_total),
        "CreatedByEmployeeID": approver_id,
        "CreatedDate": created_date,
        "ApprovedByEmployeeID": approver_id,
        "ApprovedDate": approved_date,
        "ReversesJournalEntryID": None,
    }

    gl_rows = []
    for account_number, (description, debit, credit) in opening_amounts.items():
        gl_rows.append(
            build_gl_row(
                context,
                journal_entry_id,
                posting_date,
                voucher_number,
                created_date,
                account_number,
                debit,
                credit,
                description,
                approver_id,
            )
        )

    gl_rows.append(
        build_gl_row(
            context,
            journal_entry_id,
            posting_date,
            voucher_number,
            created_date,
            "3030",
            0.00,
            retained_earnings_credit,
            "Retained earnings opening balance",
            approver_id,
        )
    )

    total_debits = round(sum(row["Debit"] for row in gl_rows), 2)
    total_credits = round(sum(row["Credit"] for row in gl_rows), 2)
    if total_debits != total_credits:
        raise ValueError(f"Opening balance is not balanced: debit={total_debits}, credit={total_credits}")

    context.tables["JournalEntry"] = pd.DataFrame([journal_record], columns=TABLE_COLUMNS["JournalEntry"])
    context.tables["GLEntry"] = pd.DataFrame(gl_rows, columns=TABLE_COLUMNS["GLEntry"])
    LOGGER.info(
        "OPENING BALANCE CALIBRATION | fiscal_start=%s | opening_fg_value=%s | opening_materials_value=%s | projected_monthly_procurement_cost=%s | opening_cash=%s | opening_ap=%s",
        posting_date,
        money(float(opening_diagnostics.get("value_by_account_number", {}).get("1040", 0.0))),
        money(float(opening_diagnostics.get("value_by_account_number", {}).get("1045", 0.0))),
        projected_procurement_cost,
        next(float(debit) for account_number, (_, debit, _) in opening_amounts.items() if account_number == "1010"),
        next(float(credit) for account_number, (_, _, credit) in opening_amounts.items() if account_number == "2010"),
    )
    for row in opening_diagnostics.get("group_supply_mode", []):
        LOGGER.info(
            "OPENING INVENTORY DIAGNOSTIC | item_group=%s | supply_mode=%s | opening_quantity=%s | coverage_target_quantity=%s | opening_value=%s",
            row["ItemGroup"],
            row["SupplyMode"],
            row["OpeningQuantity"],
            row["CoverageTargetQuantity"],
            row["OpeningValue"],
        )


def budget_approver_id(context: GenerationContext) -> int:
    return approver_employee_id(
        context,
        context.settings.fiscal_year_start,
        preferred_titles=["Chief Financial Officer", "Controller", "Accounting Manager"],
        fallback_cost_center_name="Administration",
    )


def _require_budget_prerequisites(context: GenerationContext) -> None:
    required_non_empty = [
        "CostCenter",
        "Account",
        "Employee",
        "Item",
        "Customer",
        "Supplier",
        "PriceList",
        "PriceListLine",
        "PromotionProgram",
        "PayrollPeriod",
        "ShiftDefinition",
        "EmployeeShiftAssignment",
        "WorkCenter",
        "WorkCenterCalendar",
        "InventoryPolicy",
        "DemandForecast",
        "JournalEntry",
        "GLEntry",
    ]
    missing = [table_name for table_name in required_non_empty if context.tables[table_name].empty]
    if missing:
        raise ValueError(
            "Generate pricing, payroll, planning, work-center, and opening-balance prerequisites before budgets: "
            + ", ".join(missing)
        )


def _cost_center_id_by_name(context: GenerationContext, cost_center_name: str) -> int:
    matches = context.tables["CostCenter"].loc[
        context.tables["CostCenter"]["CostCenterName"].astype(str).eq(cost_center_name),
        "CostCenterID",
    ]
    if matches.empty:
        raise ValueError(f"Cost center {cost_center_name} is not loaded.")
    return int(matches.iloc[0])


def _customer_pricing_context(
    context: GenerationContext,
) -> tuple[dict[str, float], dict[str, pd.Series], float, float]:
    customers = context.tables["Customer"].copy()
    if customers.empty:
        raise ValueError("Generate customers before budgets.")

    counts = customers["CustomerSegment"].astype(str).value_counts().sort_index()
    total = float(counts.sum())
    weights = {
        str(segment): float(count / total)
        for segment, count in counts.items()
        if float(count) > 0
    }
    representatives: dict[str, pd.Series] = {}
    weighted_terms = 0.0
    weighted_collection_factor = 0.0
    for segment in weights:
        segment_rows = customers[customers["CustomerSegment"].astype(str).eq(segment)].sort_values("CustomerID")
        if segment_rows.empty:
            continue
        representative = segment_rows.iloc[0]
        representatives[segment] = representative
        payment_terms = str(representative["PaymentTerms"])
        weighted_terms += float(weights[segment]) * float(customer_payment_term_days(payment_terms))
        weighted_collection_factor += float(weights[segment]) * float(customer_collection_factor(segment, payment_terms))

    return weights, representatives, float(weighted_terms), float(weighted_collection_factor)


def _weighted_supplier_term_days(context: GenerationContext) -> float:
    suppliers = context.tables["Supplier"]
    if suppliers.empty:
        return 30.0

    approved = suppliers[suppliers["IsApproved"].astype(int).eq(1)].copy()
    if approved.empty:
        approved = suppliers.copy()
    term_days = approved["PaymentTerms"].astype(str).map(supplier_payment_term_days).astype(float)
    if term_days.empty:
        return 30.0
    return float(term_days.mean())


def _sellable_items(context: GenerationContext) -> pd.DataFrame:
    items = context.tables["Item"]
    sellable = items[
        items["ListPrice"].notna()
        & items["RevenueAccountID"].notna()
        & items["COGSAccountID"].notna()
    ].copy()
    if sellable.empty:
        raise ValueError("Generate active sellable items before budgets.")
    return sellable.set_index("ItemID").sort_index()


def _warehouse_id_by_item(policy_lookup: dict[tuple[int, int], dict[str, Any]], item_id: int) -> int | None:
    matching = sorted(int(warehouse_id) for policy_item_id, warehouse_id in policy_lookup if int(policy_item_id) == int(item_id))
    return matching[0] if matching else None


def _build_sales_plan(
    context: GenerationContext,
    month_starts: list[pd.Timestamp],
    sellable_items: pd.DataFrame,
) -> dict[tuple[int, int], dict[int, float]]:
    plan: dict[tuple[int, int], dict[int, float]] = {}
    known_targets: dict[tuple[int, int], dict[int, float]] = {}
    sellable_items_with_id = sellable_items.reset_index(drop=False)

    for month_start in month_starts:
        fiscal_year, fiscal_month = _month_key(month_start)
        targets = monthly_forecast_targets(context, fiscal_year, fiscal_month)
        normalized = {
            int(item_id): qty(float(quantity))
            for item_id, quantity in targets.items()
            if float(quantity) > 0
        }
        known_targets[(fiscal_year, fiscal_month)] = normalized

    for month_start in month_starts:
        fiscal_year, fiscal_month = _month_key(month_start)
        plan_key = (fiscal_year, fiscal_month)
        active_mask = eligible_item_mask(sellable_items_with_id, month_start)
        active_ids = set(sellable_items_with_id.loc[active_mask, "ItemID"].astype(int).tolist())
        current_targets = dict(known_targets.get(plan_key, {}))
        if current_targets:
            plan[plan_key] = {
                int(item_id): qty(float(quantity))
                for item_id, quantity in current_targets.items()
                if int(item_id) in active_ids and float(quantity) > 0
            }
            continue

        derived_targets: dict[int, float] = {}
        prior_year_key = (fiscal_year - 1, fiscal_month)
        prior_month_key = _month_key(_previous_month(month_start))
        for item_id in sorted(active_ids):
            prior_year_quantity = float(
                plan.get(prior_year_key, {}).get(int(item_id), known_targets.get(prior_year_key, {}).get(int(item_id), 0.0))
            )
            prior_month_quantity = float(plan.get(prior_month_key, {}).get(int(item_id), 0.0))
            seed_quantity = 0.0
            if prior_year_quantity > 0:
                seed_quantity = prior_year_quantity * 1.035
            elif prior_month_quantity > 0:
                seed_quantity = prior_month_quantity * MONTHLY_FORWARD_GROWTH_FACTOR
            if seed_quantity > 0:
                derived_targets[int(item_id)] = qty(seed_quantity)
        plan[plan_key] = derived_targets

    return plan


def _planned_net_unit_price(
    context: GenerationContext,
    item: pd.Series,
    month_start: pd.Timestamp,
    total_quantity: float,
    customer_weights: dict[str, float],
    representative_customers: dict[str, pd.Series],
) -> float:
    pricing_date = min(
        pd.Timestamp(month_start).normalize(),
        pd.Timestamp(context.settings.fiscal_year_end).normalize(),
    )
    weighted_total = 0.0
    weight_total = 0.0
    list_price = money(float(item["ListPrice"]))
    item_id = int(item.name)

    for segment, weight in customer_weights.items():
        representative = representative_customers.get(segment)
        if representative is None:
            continue
        quantity = max(float(total_quantity) * float(weight), 1.0)
        resolved_line = resolve_price_list_line(
            context,
            int(representative["CustomerID"]),
            str(segment),
            item_id,
            quantity,
            pricing_date,
        )
        base_unit_price = list_price
        floor_unit_price = list_price
        if resolved_line is not None:
            base_unit_price = money(float(resolved_line["UnitPrice"]))
            floor_unit_price = money(float(resolved_line["MinimumUnitPrice"]))

        promotion = resolve_promotion(
            context,
            str(segment),
            str(item["ItemGroup"]),
            None if pd.isna(item["CollectionName"]) else str(item["CollectionName"]),
            pricing_date,
        )
        discount_pct = float(promotion["DiscountPct"]) if promotion is not None else 0.0
        net_unit_price = money(max(floor_unit_price, base_unit_price * (1.0 - discount_pct)))
        weighted_total += net_unit_price * float(weight)
        weight_total += float(weight)

    if weight_total <= 0:
        return list_price
    return money(weighted_total / weight_total)


def _employee_month_share(employee: pd.Series, month_start: pd.Timestamp, month_end: pd.Timestamp) -> float:
    hire_date = pd.Timestamp(employee["HireDate"])
    termination_date = pd.Timestamp(employee["TerminationDate"]) if pd.notna(employee["TerminationDate"]) else None
    active_start = max(month_start, hire_date)
    active_end = month_end if termination_date is None else min(month_end, termination_date)
    if active_end < active_start:
        return 0.0
    active_days = int((active_end - active_start).days) + 1
    return max(active_days / float(_month_days(month_start)), 0.0)


def _monthly_payroll_by_cost_center(
    context: GenerationContext,
    month_starts: list[pd.Timestamp],
) -> dict[tuple[int, int], dict[str, dict[int, float]]]:
    employees = context.tables["Employee"].copy()
    if employees.empty:
        return {}

    payroll_plan: dict[tuple[int, int], dict[str, dict[int, float]]] = {}
    for month_start in month_starts:
        fiscal_year, fiscal_month = _month_key(month_start)
        month_end = _month_end(month_start)
        gross_by_cost_center: dict[int, float] = defaultdict(float)
        headcount_by_cost_center: dict[int, float] = defaultdict(float)
        for _, employee in employees.iterrows():
            if pd.isna(employee["CostCenterID"]):
                continue
            share = _employee_month_share(employee, month_start, month_end)
            if share <= 0:
                continue

            growth_factor = growth_factor_for_year(fiscal_year)
            pay_class = str(employee["PayClass"])
            if pay_class == "Hourly":
                standard_hours = float(employee["StandardHoursPerWeek"]) if pd.notna(employee["StandardHoursPerWeek"]) else 40.0
                hourly_rate = float(employee["BaseHourlyRate"]) if pd.notna(employee["BaseHourlyRate"]) else 0.0
                gross_amount = hourly_rate * growth_factor * standard_hours * (52.0 / 12.0) * share
            else:
                annual_salary = float(employee["BaseAnnualSalary"]) if pd.notna(employee["BaseAnnualSalary"]) else 0.0
                gross_amount = annual_salary * growth_factor / 12.0 * share

            cost_center_id = int(employee["CostCenterID"])
            gross_by_cost_center[cost_center_id] += float(gross_amount)
            headcount_by_cost_center[cost_center_id] += float(share)

        gross_map = {cost_center_id: money(amount) for cost_center_id, amount in gross_by_cost_center.items() if amount > 0}
        payroll_plan[(fiscal_year, fiscal_month)] = {
            "gross": gross_map,
            "burden": {
                cost_center_id: money(amount * PAYROLL_BURDEN_RATE)
                for cost_center_id, amount in gross_map.items()
                if amount > 0
            },
            "headcount": {
                cost_center_id: qty(headcount)
                for cost_center_id, headcount in headcount_by_cost_center.items()
                if headcount > 0
            },
        }

    return payroll_plan


def _allocation_weights(
    context: GenerationContext,
    payroll_gross_by_cost_center: dict[int, float],
    eligible_cost_center_names: list[str],
) -> dict[str, float]:
    weights: dict[str, float] = {}
    for cost_center_name in eligible_cost_center_names:
        cost_center_id = _cost_center_id_by_name(context, cost_center_name)
        payroll_amount = float(payroll_gross_by_cost_center.get(cost_center_id, 0.0))
        if payroll_amount > 0:
            weights[cost_center_name] = payroll_amount

    if not weights:
        return {
            cost_center_name: 1.0 / float(len(eligible_cost_center_names))
            for cost_center_name in eligible_cost_center_names
        }

    total = sum(weights.values())
    return {
        cost_center_name: float(weight / total)
        for cost_center_name, weight in weights.items()
    }


def _append_budget_line(
    context: GenerationContext,
    budget_line_rows: list[dict[str, Any]],
    *,
    fiscal_year: int,
    month: int,
    account_id: int,
    budget_amount: float,
    budget_category: str,
    driver_type: str,
    approved_by_employee_id: int,
    approved_date: str,
    cost_center_id: int | None = None,
    item_id: int | None = None,
    warehouse_id: int | None = None,
    quantity_value: float | None = None,
    unit_amount: float | None = None,
) -> None:
    rounded_amount = money(float(budget_amount))
    rounded_quantity = None if quantity_value is None else qty(float(quantity_value))
    rounded_unit_amount = None if unit_amount is None else money(float(unit_amount))
    if rounded_amount == 0 and (rounded_quantity is None or rounded_quantity == 0):
        return

    budget_line_rows.append({
        "BudgetLineID": next_id(context, "BudgetLine"),
        "FiscalYear": int(fiscal_year),
        "Month": int(month),
        "AccountID": int(account_id),
        "CostCenterID": None if cost_center_id is None else int(cost_center_id),
        "ItemID": None if item_id is None else int(item_id),
        "WarehouseID": None if warehouse_id is None else int(warehouse_id),
        "Quantity": rounded_quantity,
        "UnitAmount": rounded_unit_amount,
        "BudgetAmount": rounded_amount,
        "BudgetCategory": str(budget_category),
        "DriverType": str(driver_type),
        "ApprovedByEmployeeID": int(approved_by_employee_id),
        "ApprovedDate": approved_date,
    })


def _append_allocated_expense(
    context: GenerationContext,
    budget_line_rows: list[dict[str, Any]],
    *,
    fiscal_year: int,
    month: int,
    account_id: int,
    total_amount: float,
    eligible_cost_center_names: list[str],
    payroll_gross_by_cost_center: dict[int, float],
    budget_category: str,
    driver_type: str,
    approved_by_employee_id: int,
    approved_date: str,
) -> None:
    if total_amount <= 0 or not eligible_cost_center_names:
        return

    allocation_weights = _allocation_weights(context, payroll_gross_by_cost_center, eligible_cost_center_names)
    remaining_amount = money(float(total_amount))
    allocation_items = sorted(allocation_weights.items())
    for index, (cost_center_name, weight) in enumerate(allocation_items):
        if index == len(allocation_items) - 1:
            allocated_amount = remaining_amount
        else:
            allocated_amount = money(float(total_amount) * float(weight))
            remaining_amount = money(float(remaining_amount) - float(allocated_amount))
        _append_budget_line(
            context,
            budget_line_rows,
            fiscal_year=fiscal_year,
            month=month,
            account_id=account_id,
            cost_center_id=_cost_center_id_by_name(context, cost_center_name),
            budget_amount=allocated_amount,
            budget_category=budget_category,
            driver_type=driver_type,
            approved_by_employee_id=approved_by_employee_id,
            approved_date=approved_date,
        )


def _inventory_targets_for_month(
    context: GenerationContext,
    month_start: pd.Timestamp,
    sales_plan: dict[tuple[int, int], dict[int, float]],
    sellable_items: pd.DataFrame,
    policy_lookup: dict[tuple[int, int], dict[str, Any]],
    opening_balance_map: dict[str, float],
    opening_procurement_run_rate: float,
) -> dict[str, float]:
    current_month_key = _month_key(month_start)
    next_month_start = _next_month(month_start)
    next_month_key = _month_key(next_month_start)
    current_plan = sales_plan.get(current_month_key, {})
    next_plan = sales_plan.get(next_month_key, current_plan)

    finished_goods_quantity = 0.0
    finished_goods_value = 0.0
    purchased_procurement_cost = 0.0
    next_month_days = max(_month_days(next_month_start), 1)

    for item_id, next_month_quantity in next_plan.items():
        if int(item_id) not in sellable_items.index:
            continue
        item = sellable_items.loc[int(item_id)]
        warehouse_id = _warehouse_id_by_item(policy_lookup, int(item_id))
        policy = None if warehouse_id is None else policy_lookup.get((int(item_id), int(warehouse_id)))
        target_days_supply = float(policy.get("TargetDaysSupply", 21.0)) if policy else 21.0
        coverage_ratio = min(max(target_days_supply / float(next_month_days), 0.20), 1.50)
        target_quantity = float(next_month_quantity) * coverage_ratio
        standard_cost = float(item["StandardCost"])
        finished_goods_quantity += target_quantity
        finished_goods_value += target_quantity * standard_cost

    for item_id, current_month_quantity in current_plan.items():
        if int(item_id) not in sellable_items.index:
            continue
        item = sellable_items.loc[int(item_id)]
        if str(item["SupplyMode"]) == "Purchased":
            purchased_procurement_cost += float(current_month_quantity) * float(item["StandardCost"])

    opening_materials_value = float(opening_balance_map.get("1045", 0.0))
    procurement_driver = max(purchased_procurement_cost, finished_goods_value * 0.12)
    if opening_materials_value > 0 and opening_procurement_run_rate > 0:
        materials_value = opening_materials_value * (procurement_driver / float(opening_procurement_run_rate))
        lower_bound = opening_materials_value * 0.35
        upper_bound = opening_materials_value * 2.50
        materials_value = min(max(materials_value, lower_bound), upper_bound)
    else:
        materials_value = procurement_driver * 0.18

    return {
        "finished_goods_quantity": qty(finished_goods_quantity),
        "finished_goods_value": money(finished_goods_value),
        "materials_value": money(materials_value),
        "procurement_cost": money(purchased_procurement_cost + materials_value),
    }


def _first_business_day_on_or_after(timestamp: pd.Timestamp | str) -> pd.Timestamp:
    current = pd.Timestamp(timestamp)
    while current.day_name() in {"Saturday", "Sunday"}:
        current = current + pd.Timedelta(days=1)
    return current


def _months_between(start_month: pd.Timestamp, end_month: pd.Timestamp) -> int:
    return int((end_month.year - start_month.year) * 12 + (end_month.month - start_month.month))


def _scheduled_note_payment_amount(principal_amount: float, annual_interest_rate: float, term_months: int) -> float:
    if term_months <= 0:
        return 0.0
    monthly_rate = float(annual_interest_rate) / 12.0
    if monthly_rate <= 0:
        return money(float(principal_amount) / float(term_months))
    payment = float(principal_amount) * monthly_rate / (1.0 - (1.0 + monthly_rate) ** (-int(term_months)))
    return money(payment)


def _budget_fixed_asset_records() -> list[dict[str, Any]]:
    plan = load_capex_plan()
    item_definitions = capex_item_definitions()
    disposal_dates_by_asset_code = {
        str(event["source_asset_code"]): pd.Timestamp(event["event_date"]).normalize()
        for event in capex_plan_events()
        if str(event.get("event_type")) == "Disposal" and event.get("source_asset_code")
    }

    rows: list[dict[str, Any]] = []
    for opening_asset in plan["opening_assets"]:
        item = item_definitions[str(opening_asset["item_code"])]
        rows.append({
            "AssetCode": str(opening_asset["asset_code"]),
            "AssetAccountNumber": str(item["asset_account_number"]),
            "AccumulatedDepreciationAccountNumber": str(item["accumulated_depreciation_account_number"]),
            "DepreciationAccountNumber": str(item["depreciation_account_number"]),
            "OriginalCost": money(float(opening_asset["original_cost"])),
            "OpeningAccumulatedDepreciation": money(float(opening_asset.get("opening_accumulated_depreciation", 0.0) or 0.0)),
            "UsefulLifeMonths": int(item["useful_life_months"]),
            "InServiceDate": pd.Timestamp(opening_asset["in_service_date"]).normalize(),
            "DisposalDate": disposal_dates_by_asset_code.get(str(opening_asset["asset_code"])),
            "BehaviorGroup": str(item["behavior_group"]),
        })

    for event in capex_plan_events():
        if str(event.get("event_type")) not in {"Acquisition", "Improvement"}:
            continue
        item = item_definitions[str(event["item_code"])]
        rows.append({
            "AssetCode": str(event["asset_code"]),
            "AssetAccountNumber": str(item["asset_account_number"]),
            "AccumulatedDepreciationAccountNumber": str(item["accumulated_depreciation_account_number"]),
            "DepreciationAccountNumber": str(item["depreciation_account_number"]),
            "OriginalCost": money(float(event["original_cost"])),
            "OpeningAccumulatedDepreciation": 0.0,
            "UsefulLifeMonths": int(event.get("useful_life_months", item["useful_life_months"])),
            "InServiceDate": pd.Timestamp(event["event_date"]).normalize(),
            "DisposalDate": disposal_dates_by_asset_code.get(str(event["asset_code"])),
            "BehaviorGroup": str(item["behavior_group"]),
        })
    return rows


def _budget_monthly_depreciation_rollforward(
    context: GenerationContext,
    month_start: pd.Timestamp,
) -> dict[str, dict[str, float]]:
    fiscal_start = pd.Timestamp(context.settings.fiscal_year_start).normalize()
    fiscal_start_month = pd.Timestamp(year=fiscal_start.year, month=fiscal_start.month, day=1)
    period_start = pd.Timestamp(month_start).normalize().replace(day=1)
    debit_totals: dict[str, float] = defaultdict(float)
    accumulated_totals: dict[str, float] = defaultdict(float)

    for asset in _budget_fixed_asset_records():
        useful_life_months = int(asset["UsefulLifeMonths"])
        original_cost = float(asset["OriginalCost"])
        if useful_life_months <= 0 or original_cost <= 0:
            continue
        monthly_amount = money(original_cost / float(useful_life_months))
        if monthly_amount <= 0:
            continue

        first_depreciation_month = pd.Timestamp(year=asset["InServiceDate"].year, month=asset["InServiceDate"].month, day=1) + pd.DateOffset(months=1)
        depreciation_start_month = max(first_depreciation_month, fiscal_start_month)
        if period_start < depreciation_start_month:
            continue
        disposal_date = asset.get("DisposalDate")
        if disposal_date is not None:
            disposal_month = pd.Timestamp(year=disposal_date.year, month=disposal_date.month, day=1)
            if period_start >= disposal_month:
                continue

        months_elapsed = max(_months_between(depreciation_start_month, period_start), 0)
        accumulated_before = money(float(asset["OpeningAccumulatedDepreciation"]) + (monthly_amount * months_elapsed))
        remaining_base = money(max(original_cost - accumulated_before, 0.0))
        if remaining_base <= 0:
            continue
        amount = money(min(monthly_amount, remaining_base))
        debit_account_number = str(asset["DepreciationAccountNumber"])
        accumulated_account_number = str(asset["AccumulatedDepreciationAccountNumber"])
        debit_totals[debit_account_number] = money(float(debit_totals.get(debit_account_number, 0.0)) + amount)
        accumulated_totals[accumulated_account_number] = money(
            float(accumulated_totals.get(accumulated_account_number, 0.0)) + amount
        )

    return {
        "debit_by_account": dict(debit_totals),
        "accumulated_by_account": dict(accumulated_totals),
    }


def _budget_monthly_capex_by_account(month_start: pd.Timestamp) -> tuple[dict[str, float], float, float]:
    item_definitions = capex_item_definitions()
    gross_additions: dict[str, float] = defaultdict(float)
    cash_capex = 0.0
    note_financed_capex = 0.0
    target_key = _month_key(month_start)

    for event in capex_plan_events():
        event_date = pd.Timestamp(event["event_date"]).normalize()
        if _month_key(event_date) != target_key or str(event.get("event_type")) not in {"Acquisition", "Improvement"}:
            continue
        item = item_definitions[str(event["item_code"])]
        amount = money(float(event["original_cost"]))
        gross_additions[str(item["asset_account_number"])] = money(
            float(gross_additions.get(str(item["asset_account_number"]), 0.0)) + amount
        )
        if str(event.get("financing_type", "Cash")) == "Note":
            note_financed_capex = money(note_financed_capex + amount)
        else:
            cash_capex = money(cash_capex + amount)

    return dict(gross_additions), money(cash_capex), money(note_financed_capex)


def _budget_monthly_note_activity(month_start: pd.Timestamp) -> dict[str, float]:
    target_key = _month_key(month_start)
    principal_borrowed = 0.0
    principal_paid = 0.0
    interest_paid = 0.0

    for event in capex_plan_events():
        if str(event.get("financing_type", "Cash")) != "Note":
            continue
        event_date = pd.Timestamp(event["event_date"]).normalize()
        if _month_key(event_date) == target_key:
            principal_borrowed = money(principal_borrowed + float(event["original_cost"]))

        principal_amount = float(event["original_cost"])
        annual_interest_rate = float(event["annual_interest_rate"])
        term_months = int(event["term_months"])
        payment_start_date = _first_business_day_on_or_after(
            event.get("payment_start_date") or event_date + pd.DateOffset(months=1)
        )
        scheduled_payment = _scheduled_note_payment_amount(principal_amount, annual_interest_rate, term_months)
        remaining_principal = money(principal_amount)
        monthly_rate = annual_interest_rate / 12.0

        for payment_sequence in range(int(term_months)):
            payment_date = _first_business_day_on_or_after(payment_start_date + pd.DateOffset(months=payment_sequence))
            if _month_key(payment_date) != target_key:
                interest_amount = money(remaining_principal * monthly_rate)
                principal_component = money(scheduled_payment - interest_amount)
                if principal_component > remaining_principal or payment_sequence == int(term_months) - 1:
                    principal_component = money(remaining_principal)
                remaining_principal = money(remaining_principal - principal_component)
                continue
            interest_amount = money(remaining_principal * monthly_rate)
            principal_component = money(scheduled_payment - interest_amount)
            if principal_component > remaining_principal or payment_sequence == int(term_months) - 1:
                principal_component = money(remaining_principal)
            principal_paid = money(principal_paid + principal_component)
            interest_paid = money(interest_paid + interest_amount)
            remaining_principal = money(remaining_principal - principal_component)

    return {
        "principal_borrowed": money(principal_borrowed),
        "principal_paid": money(principal_paid),
        "interest_paid": money(interest_paid),
    }


def generate_budgets(context: GenerationContext) -> None:
    if not context.tables["Budget"].empty or not context.tables["BudgetLine"].empty:
        return

    _require_budget_prerequisites(context)
    approver_id = budget_approver_id(context)
    month_starts = budget_horizon_month_starts(context)
    opening_balance_map = _opening_balance_map(context)
    policy_lookup = active_policy_lookup(context)
    sellable_items = _sellable_items(context)
    sellable_items_with_id = sellable_items.reset_index(drop=False)
    sales_plan = _build_sales_plan(context, month_starts, sellable_items)
    payroll_plan = _monthly_payroll_by_cost_center(context, month_starts)
    customer_weights, representative_customers, weighted_customer_term_days, weighted_collection_factor = _customer_pricing_context(context)
    weighted_supplier_term_days = _weighted_supplier_term_days(context)
    opening_procurement_run_rate = max(float(projected_monthly_procurement_cost(context)), 1.0)

    cost_centers = context.tables["CostCenter"][["CostCenterID", "CostCenterName"]].copy()
    cost_center_name_by_id = cost_centers.set_index("CostCenterID")["CostCenterName"].astype(str).to_dict()
    sales_cost_center_id = _cost_center_id_by_name(context, "Sales")
    manufacturing_cost_center_id = _cost_center_id_by_name(context, "Manufacturing")
    administration_cost_center_id = _cost_center_id_by_name(context, "Administration")

    account_ids = {
        account_number: account_id_by_number(context, account_number)
        for account_number in [
            "1010", "1020", "1040", "1045", "1050", "1110", "1120", "1130", "1140", "1150", "1160", "1170",
            "1185", "1186", "2010", "2030", "2040", "2110", "2120", "2130", "3010", "3020", "3030",
            "6060", "6070", "6080", "6090", "6100", "6110", "6120", "6130", "6140", "6180", "6190",
            "6200", "7030",
        ]
        if not context.tables["Account"].loc[
            context.tables["Account"]["AccountNumber"].astype(str).eq(account_number)
        ].empty
    }
    for account_number in MONTHLY_ACCRUAL_BASES:
        if account_number not in account_ids:
            account_ids[account_number] = account_id_by_number(context, account_number)

    budget_line_rows: list[dict[str, Any]] = []
    running_balance = {
        "1010": money(float(opening_balance_map.get("1010", 0.0))),
        "1020": money(float(opening_balance_map.get("1020", 0.0))),
        "1040": money(float(opening_balance_map.get("1040", 0.0))),
        "1045": money(float(opening_balance_map.get("1045", 0.0))),
        "1050": money(float(opening_balance_map.get("1050", 0.0))),
        "2010": money(float(opening_balance_map.get("2010", 0.0))),
        "2030": money(float(opening_balance_map.get("2030", 0.0))),
        "2040": money(float(opening_balance_map.get("2040", 0.0))),
        "2110": money(float(opening_balance_map.get("2110", 0.0))),
        "2120": money(float(opening_balance_map.get("2120", 0.0))),
        "2130": money(float(opening_balance_map.get("2130", 0.0))),
        "3010": money(float(opening_balance_map.get("3010", 0.0))),
        "3020": money(float(opening_balance_map.get("3020", 0.0))),
        "3030": money(float(opening_balance_map.get("3030", 0.0))),
    }
    budget_fixed_asset_records = _budget_fixed_asset_records()
    fixed_asset_gross_balances = {
        account_number: money(float(opening_balance_map.get(account_number, 0.0)))
        for account_number in sorted({str(record["AssetAccountNumber"]) for record in budget_fixed_asset_records})
        if account_number in account_ids
    }
    fixed_asset_accumulated_balances = {
        account_number: money(float(opening_balance_map.get(account_number, 0.0)))
        for account_number in sorted({str(record["AccumulatedDepreciationAccountNumber"]) for record in budget_fixed_asset_records})
        if account_number in account_ids
    }
    current_year_net_income: dict[int, float] = defaultdict(float)
    prior_month_fiscal_year: int | None = None

    for month_start in month_starts:
        fiscal_year, fiscal_month = _month_key(month_start)
        approved_date = _approved_date_for_year(fiscal_year)
        if prior_month_fiscal_year is not None and fiscal_year != prior_month_fiscal_year:
            running_balance["3030"] = money(
                float(running_balance["3030"]) + float(current_year_net_income.get(prior_month_fiscal_year, 0.0))
            )
        prior_month_fiscal_year = fiscal_year

        month_revenue = 0.0
        month_cogs = 0.0
        month_operating_expense = 0.0
        month_payroll_gross = 0.0

        month_plan = sales_plan.get((fiscal_year, fiscal_month), {})
        for item_id, planned_quantity in month_plan.items():
            if int(item_id) not in sellable_items.index or planned_quantity <= 0:
                continue
            item = sellable_items.loc[int(item_id)]
            planned_net_price = _planned_net_unit_price(
                context,
                item,
                month_start,
                float(planned_quantity),
                customer_weights,
                representative_customers,
            )
            warehouse_id = _warehouse_id_by_item(policy_lookup, int(item_id))
            revenue_amount = money(float(planned_quantity) * planned_net_price)
            standard_cost = money(float(item["StandardCost"]))
            cogs_amount = money(float(planned_quantity) * standard_cost)

            _append_budget_line(
                context,
                budget_line_rows,
                fiscal_year=fiscal_year,
                month=fiscal_month,
                account_id=int(item["RevenueAccountID"]),
                cost_center_id=sales_cost_center_id,
                item_id=int(item_id),
                warehouse_id=warehouse_id,
                quantity_value=float(planned_quantity),
                unit_amount=planned_net_price,
                budget_amount=revenue_amount,
                budget_category="Revenue",
                driver_type="Forecast x Planned Net Price",
                approved_by_employee_id=approver_id,
                approved_date=approved_date,
            )
            _append_budget_line(
                context,
                budget_line_rows,
                fiscal_year=fiscal_year,
                month=fiscal_month,
                account_id=int(item["COGSAccountID"]),
                cost_center_id=manufacturing_cost_center_id,
                item_id=int(item_id),
                warehouse_id=warehouse_id,
                quantity_value=float(planned_quantity),
                unit_amount=standard_cost,
                budget_amount=cogs_amount,
                budget_category="COGS",
                driver_type="Forecast x Standard Cost",
                approved_by_employee_id=approver_id,
                approved_date=approved_date,
            )
            month_revenue += float(revenue_amount)
            month_cogs += float(cogs_amount)

        month_payroll = payroll_plan.get((fiscal_year, fiscal_month), {"gross": {}, "burden": {}, "headcount": {}})
        for cost_center_id, gross_amount in sorted(month_payroll["gross"].items()):
            cost_center_name = cost_center_name_by_id.get(int(cost_center_id))
            if cost_center_name is None or cost_center_name == "Manufacturing":
                continue
            salary_account_number = SALARY_ACCOUNT_BY_COST_CENTER.get(cost_center_name)
            if salary_account_number is None:
                continue
            active_headcount = float(month_payroll["headcount"].get(int(cost_center_id), 0.0))
            gross_unit_amount = money(float(gross_amount) / active_headcount) if active_headcount > 0 else money(float(gross_amount))
            _append_budget_line(
                context,
                budget_line_rows,
                fiscal_year=fiscal_year,
                month=fiscal_month,
                account_id=account_id_by_number(context, salary_account_number),
                cost_center_id=int(cost_center_id),
                budget_amount=float(gross_amount),
                budget_category="Operating Expense",
                driver_type="Active Employees x Compensation",
                approved_by_employee_id=approver_id,
                approved_date=approved_date,
                quantity_value=active_headcount if active_headcount > 0 else None,
                unit_amount=gross_unit_amount,
            )
            month_operating_expense += float(gross_amount)
            month_payroll_gross += float(gross_amount)

            burden_amount = float(month_payroll["burden"].get(int(cost_center_id), 0.0))
            if burden_amount > 0:
                burden_unit_amount = money(burden_amount / active_headcount) if active_headcount > 0 else money(burden_amount)
                _append_budget_line(
                    context,
                    budget_line_rows,
                    fiscal_year=fiscal_year,
                    month=fiscal_month,
                    account_id=account_id_by_number(context, NONMANUFACTURING_PAYROLL_BURDEN_ACCOUNT),
                    cost_center_id=int(cost_center_id),
                    budget_amount=burden_amount,
                    budget_category="Operating Expense",
                    driver_type="Payroll Burden Rate",
                    approved_by_employee_id=approver_id,
                    approved_date=approved_date,
                    quantity_value=active_headcount if active_headcount > 0 else None,
                    unit_amount=burden_unit_amount,
                )
                month_operating_expense += burden_amount

        office_rent = monthly_rent_amount(context, fiscal_year, fiscal_month, "Office")
        warehouse_rent = monthly_rent_amount(context, fiscal_year, fiscal_month, "Warehouse")
        utilities_amount = monthly_utilities_amount(context, fiscal_year, fiscal_month)
        _append_budget_line(
            context,
            budget_line_rows,
            fiscal_year=fiscal_year,
            month=fiscal_month,
            account_id=account_id_by_number(context, "6080"),
            budget_amount=office_rent,
            budget_category="Operating Expense",
            driver_type="Recurring Rent Driver",
            approved_by_employee_id=approver_id,
            approved_date=approved_date,
        )
        _append_budget_line(
            context,
            budget_line_rows,
            fiscal_year=fiscal_year,
            month=fiscal_month,
            account_id=account_id_by_number(context, "6070"),
            budget_amount=warehouse_rent,
            budget_category="Operating Expense",
            driver_type="Recurring Rent Driver",
            approved_by_employee_id=approver_id,
            approved_date=approved_date,
        )
        _append_budget_line(
            context,
            budget_line_rows,
            fiscal_year=fiscal_year,
            month=fiscal_month,
            account_id=account_id_by_number(context, "6090"),
            budget_amount=utilities_amount,
            budget_category="Operating Expense",
            driver_type="Recurring Utilities Driver",
            approved_by_employee_id=approver_id,
            approved_date=approved_date,
        )
        month_operating_expense += office_rent + warehouse_rent + utilities_amount

        total_accrual_expense = 0.0
        for account_number in sorted(MONTHLY_ACCRUAL_BASES):
            accrual_amount = monthly_accrual_amount(context, fiscal_year, fiscal_month, account_number)
            total_accrual_expense += accrual_amount
            _append_budget_line(
                context,
                budget_line_rows,
                fiscal_year=fiscal_year,
                month=fiscal_month,
                account_id=account_id_by_number(context, account_number),
                budget_amount=accrual_amount,
                budget_category="Operating Expense",
                driver_type="Recurring Accrual Driver",
                approved_by_employee_id=approver_id,
                approved_date=approved_date,
            )
        month_operating_expense += total_accrual_expense

        depreciation_rollforward = _budget_monthly_depreciation_rollforward(context, month_start)
        depreciation_by_debit_account = depreciation_rollforward["debit_by_account"]
        accumulated_depreciation_by_account = depreciation_rollforward["accumulated_by_account"]
        capex_additions_by_account, cash_capex_total, note_financed_capex_total = _budget_monthly_capex_by_account(month_start)
        note_activity = _budget_monthly_note_activity(month_start)
        operating_depreciation_total = float(depreciation_by_debit_account.get("6130", 0.0))
        interest_expense_total = float(note_activity["interest_paid"])

        for asset_account_number, capex_addition in capex_additions_by_account.items():
            fixed_asset_gross_balances[asset_account_number] = money(
                float(fixed_asset_gross_balances.get(asset_account_number, 0.0)) + float(capex_addition)
            )
        for accumulated_account_number, depreciation_amount in accumulated_depreciation_by_account.items():
            fixed_asset_accumulated_balances[accumulated_account_number] = money(
                float(fixed_asset_accumulated_balances.get(accumulated_account_number, 0.0)) + float(depreciation_amount)
            )

        _append_budget_line(
            context,
            budget_line_rows,
            fiscal_year=fiscal_year,
            month=fiscal_month,
            account_id=account_id_by_number(context, "6130"),
            cost_center_id=administration_cost_center_id,
            budget_amount=operating_depreciation_total,
            budget_category="Operating Expense",
            driver_type="Depreciation Schedule",
            approved_by_employee_id=approver_id,
            approved_date=approved_date,
        )
        if interest_expense_total > 0 and "7030" in account_ids:
            _append_budget_line(
                context,
                budget_line_rows,
                fiscal_year=fiscal_year,
                month=fiscal_month,
                account_id=account_ids["7030"],
                cost_center_id=administration_cost_center_id,
                budget_amount=interest_expense_total,
                budget_category="Operating Expense",
                driver_type="Debt Interest Schedule",
                approved_by_employee_id=approver_id,
                approved_date=approved_date,
            )
        month_operating_expense += operating_depreciation_total + interest_expense_total

        inventory_targets = _inventory_targets_for_month(
            context,
            month_start,
            sales_plan,
            sellable_items,
            policy_lookup,
            opening_balance_map,
            opening_procurement_run_rate,
        )
        ending_accounts_receivable = money(
            month_revenue
            * min(
                max(
                    (weighted_customer_term_days / float(max(_month_days(month_start), 1)))
                    * max(weighted_collection_factor, 0.35)
                    * ACCOUNTS_RECEIVABLE_COLLECTION_SCALAR,
                    0.10,
                ),
                1.10,
            )
        )
        ending_finished_goods_inventory = money(float(inventory_targets["finished_goods_value"]))
        ending_materials_inventory = money(float(inventory_targets["materials_value"]))
        ending_accounts_payable = money(
            float(inventory_targets["procurement_cost"])
            * min(
                max(
                    (weighted_supplier_term_days / float(max(_month_days(month_start), 1)))
                    * ACCOUNTS_PAYABLE_PAYMENT_SCALAR,
                    0.10,
                ),
                1.10,
            )
        )
        total_payroll_gross_all_cost_centers = sum(float(amount) for amount in month_payroll["gross"].values())
        ending_accrued_payroll = money(total_payroll_gross_all_cost_centers * ACCRUED_PAYROLL_FRACTION)
        ending_accrued_expenses = money(total_accrual_expense * ACCRUED_EXPENSES_FRACTION)
        net_income = money(month_revenue - month_cogs - month_operating_expense)
        current_year_net_income[fiscal_year] = money(float(current_year_net_income.get(fiscal_year, 0.0)) + net_income)

        accounts_receivable_change = money(ending_accounts_receivable - float(running_balance["1020"]))
        finished_goods_change = money(ending_finished_goods_inventory - float(running_balance["1040"]))
        materials_change = money(ending_materials_inventory - float(running_balance["1045"]))
        accounts_payable_change = money(ending_accounts_payable - float(running_balance["2010"]))
        accrued_payroll_change = money(ending_accrued_payroll - float(running_balance["2030"]))
        accrued_expenses_change = money(ending_accrued_expenses - float(running_balance["2040"]))
        ending_cash = money(
            float(running_balance["1010"])
            + net_income
            + operating_depreciation_total
            - accounts_receivable_change
            - finished_goods_change
            - materials_change
            + accounts_payable_change
            + accrued_payroll_change
            + accrued_expenses_change
            - cash_capex_total
            + float(note_activity["principal_borrowed"])
            - float(note_activity["principal_paid"])
        )

        running_balance["1010"] = ending_cash
        running_balance["1020"] = ending_accounts_receivable
        running_balance["1040"] = ending_finished_goods_inventory
        running_balance["1045"] = ending_materials_inventory
        running_balance["2010"] = ending_accounts_payable
        running_balance["2030"] = ending_accrued_payroll
        running_balance["2040"] = ending_accrued_expenses
        running_balance["2110"] = money(
            float(running_balance["2110"])
            + float(note_activity["principal_borrowed"])
            - float(note_activity["principal_paid"])
        )

        for account_number in ["1010", "1020", "1040", "1045", "1050", "2010", "2030", "2040", "2110", "2120", "2130", "3010", "3020", "3030"]:
            if account_number not in account_ids or account_number not in running_balance:
                continue
            driver_type = {
                "1010": "Indirect Cash Flow Rollforward",
                "1020": "Collections Timing Rollforward",
                "1040": "Inventory Policy Coverage Rollforward",
                "1045": "Inventory Policy Coverage Rollforward",
                "2010": "Supplier Payment Timing Rollforward",
                "2030": "Payroll Cadence Rollforward",
                "2040": "Accrual Timing Rollforward",
                "2110": "Debt Schedule Rollforward",
                "3030": "Prior-Year Earnings Carryforward",
            }.get(account_number, "Opening Balance Carryforward")
            _append_budget_line(
                context,
                budget_line_rows,
                fiscal_year=fiscal_year,
                month=fiscal_month,
                account_id=account_ids[account_number],
                budget_amount=float(running_balance[account_number]),
                budget_category="Balance Sheet",
                driver_type=driver_type,
                approved_by_employee_id=approver_id,
                approved_date=approved_date,
            )

        for asset_account_number, ending_balance in fixed_asset_gross_balances.items():
            if asset_account_number not in account_ids:
                continue
            _append_budget_line(
                context,
                budget_line_rows,
                fiscal_year=fiscal_year,
                month=fiscal_month,
                account_id=account_ids[asset_account_number],
                budget_amount=float(ending_balance),
                budget_category="Balance Sheet",
                driver_type="CAPEX Plan Rollforward",
                approved_by_employee_id=approver_id,
                approved_date=approved_date,
            )
        for accumulated_account_number, ending_balance in fixed_asset_accumulated_balances.items():
            if accumulated_account_number not in account_ids:
                continue
            _append_budget_line(
                context,
                budget_line_rows,
                fiscal_year=fiscal_year,
                month=fiscal_month,
                account_id=account_ids[accumulated_account_number],
                budget_amount=float(ending_balance),
                budget_category="Balance Sheet",
                driver_type="Accumulated Depreciation Rollforward",
                approved_by_employee_id=approver_id,
                approved_date=approved_date,
            )

    if budget_line_rows:
        budget_lines = pd.DataFrame(budget_line_rows, columns=TABLE_COLUMNS["BudgetLine"])
        budget_lines = budget_lines.sort_values(
            ["FiscalYear", "Month", "AccountID", "CostCenterID", "ItemID", "WarehouseID", "BudgetLineID"],
            na_position="last",
        ).reset_index(drop=True)
    else:
        budget_lines = pd.DataFrame(columns=TABLE_COLUMNS["BudgetLine"])
    context.tables["BudgetLine"] = budget_lines

    summary_source = budget_lines[
        budget_lines["CostCenterID"].notna()
        & budget_lines["BudgetCategory"].astype(str).isin(SUMMARY_BUDGET_CATEGORIES)
    ].copy()
    if summary_source.empty:
        context.tables["Budget"] = pd.DataFrame(columns=TABLE_COLUMNS["Budget"])
        return

    budget_summary = (
        summary_source.groupby(
            ["FiscalYear", "Month", "CostCenterID", "AccountID", "ApprovedByEmployeeID", "ApprovedDate"],
            dropna=False,
            as_index=False,
        )["BudgetAmount"]
        .sum()
        .sort_values(["FiscalYear", "Month", "CostCenterID", "AccountID"])
        .reset_index(drop=True)
    )
    budget_summary["BudgetAmount"] = budget_summary["BudgetAmount"].astype(float).map(money)
    budget_summary.insert(0, "BudgetID", [next_id(context, "Budget") for _ in range(len(budget_summary))])
    budget_summary = budget_summary[TABLE_COLUMNS["Budget"]]
    context.tables["Budget"] = budget_summary
