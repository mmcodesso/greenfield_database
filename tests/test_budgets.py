from __future__ import annotations

from collections import defaultdict

import pandas as pd
import pytest

from generator_dataset.budgets import SUMMARY_BUDGET_CATEGORIES, _opening_balance_map, budget_horizon_months
from generator_dataset.fixed_assets import depreciable_fixed_asset_profiles
from generator_dataset.journals import (
    PAYROLL_BURDEN_RATE,
    monthly_accrual_amount,
    monthly_depreciation_amount,
    monthly_rent_amount,
    monthly_utilities_amount,
)
from generator_dataset.main import build_phase2
from generator_dataset.o2c import resolve_price_list_line, resolve_promotion
from generator_dataset.payroll import growth_factor_for_year
from generator_dataset.planning import monthly_forecast_targets
from generator_dataset.validations import validate_phase2
from generator_dataset.accrual_catalog import MONTHLY_ACCRUAL_BASES


@pytest.fixture(scope="module")
def phase2_budget_context():
    return build_phase2("config/settings_validation.yaml")


def _budget_summary_from_lines(context) -> pd.DataFrame:
    budget_lines = context.tables["BudgetLine"]
    return (
        budget_lines[
            budget_lines["CostCenterID"].notna()
            & budget_lines["BudgetCategory"].astype(str).isin(SUMMARY_BUDGET_CATEGORIES)
        ][["FiscalYear", "Month", "CostCenterID", "AccountID", "BudgetAmount"]]
        .copy()
        .assign(BudgetAmount=lambda frame: frame["BudgetAmount"].astype(float).round(2))
        .groupby(["FiscalYear", "Month", "CostCenterID", "AccountID"], as_index=False, dropna=False)["BudgetAmount"]
        .sum()
        .sort_values(["FiscalYear", "Month", "CostCenterID", "AccountID"])
        .reset_index(drop=True)
    )


def _budget_summary_table(context) -> pd.DataFrame:
    return (
        context.tables["Budget"][["FiscalYear", "Month", "CostCenterID", "AccountID", "BudgetAmount"]]
        .copy()
        .assign(BudgetAmount=lambda frame: frame["BudgetAmount"].astype(float).round(2))
        .groupby(["FiscalYear", "Month", "CostCenterID", "AccountID"], as_index=False, dropna=False)["BudgetAmount"]
        .sum()
        .sort_values(["FiscalYear", "Month", "CostCenterID", "AccountID"])
        .reset_index(drop=True)
    )


def _account_lookup(context) -> pd.DataFrame:
    return context.tables["Account"][["AccountID", "AccountNumber", "AccountType", "NormalBalance"]].copy()


def _budget_lines_with_accounts(context) -> pd.DataFrame:
    return context.tables["BudgetLine"].merge(_account_lookup(context), on="AccountID", how="left")


def _employee_month_share(employee: pd.Series, month_start: pd.Timestamp, month_end: pd.Timestamp) -> float:
    hire_date = pd.Timestamp(employee["HireDate"])
    termination_date = pd.Timestamp(employee["TerminationDate"]) if pd.notna(employee["TerminationDate"]) else None
    active_start = max(month_start, hire_date)
    active_end = month_end if termination_date is None else min(month_end, termination_date)
    if active_end < active_start:
        return 0.0
    active_days = int((active_end - active_start).days) + 1
    return active_days / float(month_end.day)


def test_generate_opening_balances_and_budgets(phase2_budget_context) -> None:
    context = phase2_budget_context
    results = validate_phase2(context)

    assert results["exceptions"] == []
    assert len(context.tables["JournalEntry"]) == 1
    assert not context.tables["GLEntry"].empty
    assert round(context.tables["GLEntry"]["Debit"].sum(), 2) == round(context.tables["GLEntry"]["Credit"].sum(), 2)
    assert not context.tables["BudgetLine"].empty
    assert not context.tables["Budget"].empty


def test_budget_horizon_and_summary_rollup(phase2_budget_context) -> None:
    context = phase2_budget_context
    expected_months = set(budget_horizon_months(context))
    actual_budget_line_months = {
        (int(row.FiscalYear), int(row.Month))
        for row in context.tables["BudgetLine"][["FiscalYear", "Month"]].drop_duplicates().itertuples(index=False)
    }

    assert actual_budget_line_months == expected_months
    pd.testing.assert_frame_equal(_budget_summary_from_lines(context), _budget_summary_table(context))


def test_budget_generation_is_deterministic_for_fixed_seed() -> None:
    first_context = build_phase2("config/settings_validation.yaml")
    second_context = build_phase2("config/settings_validation.yaml")

    first_budget_lines = first_context.tables["BudgetLine"].drop(columns=["BudgetLineID"]).reset_index(drop=True)
    second_budget_lines = second_context.tables["BudgetLine"].drop(columns=["BudgetLineID"]).reset_index(drop=True)
    first_budget = first_context.tables["Budget"].drop(columns=["BudgetID"]).reset_index(drop=True)
    second_budget = second_context.tables["Budget"].drop(columns=["BudgetID"]).reset_index(drop=True)

    pd.testing.assert_frame_equal(first_budget_lines, second_budget_lines)
    pd.testing.assert_frame_equal(first_budget, second_budget)


def test_budget_revenue_price_and_standard_cost_drivers_follow_planning_inputs(phase2_budget_context) -> None:
    context = phase2_budget_context
    budget_lines = _budget_lines_with_accounts(context)
    items = context.tables["Item"].set_index("ItemID")
    sellable_item_ids = set(
        context.tables["Item"].loc[
            context.tables["Item"]["ListPrice"].notna()
            & context.tables["Item"]["RevenueAccountID"].notna()
            & context.tables["Item"]["COGSAccountID"].notna(),
            "ItemID",
        ].astype(int)
    )
    customers = context.tables["Customer"].copy()
    customer_segment_counts = customers["CustomerSegment"].astype(str).value_counts().sort_index()
    total_customers = float(customer_segment_counts.sum())
    customer_weights = {
        str(segment): float(count) / total_customers
        for segment, count in customer_segment_counts.items()
        if float(count) > 0
    }
    representative_customers = {
        segment: customers[customers["CustomerSegment"].astype(str).eq(segment)].sort_values("CustomerID").iloc[0]
        for segment in customer_weights
    }
    pricing_horizon_end = pd.Timestamp(context.settings.fiscal_year_end).normalize()
    fiscal_start = pd.Timestamp(context.settings.fiscal_year_start)
    fiscal_end = pd.Timestamp(context.settings.fiscal_year_end)

    revenue_summary = (
        budget_lines[
            budget_lines["BudgetCategory"].astype(str).eq("Revenue")
            & budget_lines["DriverType"].astype(str).eq("Forecast x Planned Net Price")
            & budget_lines["ItemID"].notna()
        ][["FiscalYear", "Month", "ItemID", "Quantity", "BudgetAmount"]]
        .copy()
        .groupby(["FiscalYear", "Month", "ItemID"], as_index=False, dropna=False)[["Quantity", "BudgetAmount"]]
        .sum()
        .assign(UnitAmount=lambda frame: (frame["BudgetAmount"] / frame["Quantity"]).round(2))
    )
    cogs_summary = (
        budget_lines[
            budget_lines["BudgetCategory"].astype(str).eq("COGS")
            & budget_lines["DriverType"].astype(str).eq("Forecast x Standard Cost")
            & budget_lines["ItemID"].notna()
        ][["FiscalYear", "Month", "ItemID", "Quantity", "BudgetAmount", "UnitAmount"]]
        .copy()
        .groupby(["FiscalYear", "Month", "ItemID"], as_index=False, dropna=False)[["Quantity", "BudgetAmount"]]
        .sum()
        .merge(
            budget_lines[
                budget_lines["BudgetCategory"].astype(str).eq("COGS")
                & budget_lines["DriverType"].astype(str).eq("Forecast x Standard Cost")
                & budget_lines["ItemID"].notna()
            ][["FiscalYear", "Month", "ItemID", "UnitAmount"]].drop_duplicates(),
            on=["FiscalYear", "Month", "ItemID"],
            how="left",
        )
    )

    for fiscal_year, fiscal_month in sorted(
        {
            (int(row.FiscalYear), int(row.Month))
            for row in revenue_summary[["FiscalYear", "Month"]].drop_duplicates().itertuples(index=False)
        }
    ):
        month_start = pd.Timestamp(f"{fiscal_year}-{fiscal_month:02d}-01")
        month_rows = revenue_summary[
            revenue_summary["FiscalYear"].astype(int).eq(fiscal_year)
            & revenue_summary["Month"].astype(int).eq(fiscal_month)
        ].copy()

        if fiscal_start <= month_start <= fiscal_end:
            active_sellable_item_ids = {
                int(item_id)
                for item_id in sellable_item_ids
                if int(items.loc[int(item_id), "IsActive"]) == 1
                and pd.notna(items.loc[int(item_id), "LaunchDate"])
                and pd.Timestamp(items.loc[int(item_id), "LaunchDate"]) <= month_start
            }
            forecast_targets = {
                int(item_id): round(float(quantity), 2)
                for item_id, quantity in monthly_forecast_targets(context, fiscal_year, fiscal_month).items()
                if int(item_id) in active_sellable_item_ids and round(float(quantity), 2) > 0
            }
            generated_targets = {
                int(row.ItemID): round(float(row.Quantity), 2)
                for row in month_rows.itertuples(index=False)
            }
            assert generated_targets == forecast_targets

        pricing_date = min(month_start.normalize(), pricing_horizon_end)
        for row in month_rows.itertuples(index=False):
            item = items.loc[int(row.ItemID)]
            weighted_unit_price = 0.0
            weighted_floor_price = 0.0
            weight_total = 0.0
            for segment, weight in customer_weights.items():
                representative_customer = representative_customers[segment]
                quantity = max(float(row.Quantity) * float(weight), 1.0)
                resolved_line = resolve_price_list_line(
                    context,
                    int(representative_customer["CustomerID"]),
                    str(segment),
                    int(row.ItemID),
                    quantity,
                    pricing_date,
                )
                base_unit_price = float(item["ListPrice"])
                floor_unit_price = float(item["ListPrice"])
                if resolved_line is not None:
                    base_unit_price = float(resolved_line["UnitPrice"])
                    floor_unit_price = float(resolved_line["MinimumUnitPrice"])
                promotion = resolve_promotion(
                    context,
                    str(segment),
                    str(item["ItemGroup"]),
                    None if pd.isna(item["CollectionName"]) else str(item["CollectionName"]),
                    pricing_date,
                )
                discount_pct = float(promotion["DiscountPct"]) if promotion is not None else 0.0
                weighted_floor_price += floor_unit_price * float(weight)
                weighted_unit_price += max(floor_unit_price, base_unit_price * (1.0 - discount_pct)) * float(weight)
                weight_total += float(weight)

            expected_unit_amount = round(weighted_unit_price / weight_total, 2)
            expected_floor_amount = round(weighted_floor_price / weight_total, 2)
            assert abs(round(float(row.UnitAmount), 2) - expected_unit_amount) <= 0.01
            assert round(float(row.UnitAmount), 2) >= expected_floor_amount

    merged_standard_cost = revenue_summary.merge(
        cogs_summary,
        on=["FiscalYear", "Month", "ItemID"],
        how="inner",
        suffixes=("_Revenue", "_COGS"),
    )
    assert not merged_standard_cost.empty
    for row in merged_standard_cost.itertuples(index=False):
        standard_cost = round(float(items.loc[int(row.ItemID), "StandardCost"]), 2)
        assert round(float(row.Quantity_Revenue), 2) == round(float(row.Quantity_COGS), 2)
        assert round(float(row.UnitAmount_COGS), 2) == standard_cost
        assert abs(round(float(row.BudgetAmount_COGS), 2) - round(float(row.Quantity_COGS) * standard_cost, 2)) < 0.02


def test_budget_payroll_and_recurring_expense_drivers_follow_source_formulas(phase2_budget_context) -> None:
    context = phase2_budget_context
    budget_lines = _budget_lines_with_accounts(context)
    employees = context.tables["Employee"].copy()
    cost_centers = context.tables["CostCenter"][["CostCenterID", "CostCenterName"]].copy()
    cost_center_name_by_id = cost_centers.set_index("CostCenterID")["CostCenterName"].astype(str).to_dict()
    non_manufacturing_ids = {
        int(cost_center_id)
        for cost_center_id, cost_center_name in cost_center_name_by_id.items()
        if str(cost_center_name) != "Manufacturing"
    }

    payroll_budget = (
        budget_lines[
            budget_lines["DriverType"].astype(str).eq("Active Employees x Compensation")
            & budget_lines["BudgetCategory"].astype(str).eq("Operating Expense")
            & budget_lines["CostCenterID"].notna()
        ][["FiscalYear", "Month", "CostCenterID", "BudgetAmount"]]
        .copy()
        .groupby(["FiscalYear", "Month", "CostCenterID"], as_index=False, dropna=False)["BudgetAmount"]
        .sum()
    )
    burden_budget = (
        budget_lines[
            budget_lines["DriverType"].astype(str).eq("Payroll Burden Rate")
            & budget_lines["BudgetCategory"].astype(str).eq("Operating Expense")
            & budget_lines["CostCenterID"].notna()
        ][["FiscalYear", "Month", "CostCenterID", "BudgetAmount"]]
        .copy()
        .groupby(["FiscalYear", "Month", "CostCenterID"], as_index=False, dropna=False)["BudgetAmount"]
        .sum()
    )

    expected_payroll_rows: list[dict[str, float | int]] = []
    for fiscal_year, fiscal_month in budget_horizon_months(context):
        month_start = pd.Timestamp(f"{fiscal_year}-{fiscal_month:02d}-01")
        month_end = month_start + pd.offsets.MonthEnd(1)
        gross_by_cost_center: dict[int, float] = defaultdict(float)
        for _, employee in employees.iterrows():
            if pd.isna(employee["CostCenterID"]):
                continue
            cost_center_id = int(employee["CostCenterID"])
            if cost_center_id not in non_manufacturing_ids:
                continue
            share = _employee_month_share(employee, month_start, month_end)
            if share <= 0:
                continue
            growth_factor = growth_factor_for_year(fiscal_year)
            if str(employee["PayClass"]) == "Hourly":
                standard_hours = float(employee["StandardHoursPerWeek"]) if pd.notna(employee["StandardHoursPerWeek"]) else 40.0
                hourly_rate = float(employee["BaseHourlyRate"]) if pd.notna(employee["BaseHourlyRate"]) else 0.0
                gross_amount = hourly_rate * growth_factor * standard_hours * (52.0 / 12.0) * share
            else:
                annual_salary = float(employee["BaseAnnualSalary"]) if pd.notna(employee["BaseAnnualSalary"]) else 0.0
                gross_amount = annual_salary * growth_factor / 12.0 * share
            gross_by_cost_center[cost_center_id] += gross_amount

        for cost_center_id, gross_amount in gross_by_cost_center.items():
            expected_payroll_rows.append(
                {
                    "FiscalYear": fiscal_year,
                    "Month": fiscal_month,
                    "CostCenterID": cost_center_id,
                    "BudgetAmount": round(gross_amount, 2),
                    "BurdenAmount": round(gross_amount * PAYROLL_BURDEN_RATE, 2),
                }
            )

    expected_payroll = pd.DataFrame(expected_payroll_rows)
    expected_burden = expected_payroll[["FiscalYear", "Month", "CostCenterID", "BurdenAmount"]].rename(
        columns={"BurdenAmount": "BudgetAmount"}
    )
    expected_payroll = expected_payroll[["FiscalYear", "Month", "CostCenterID", "BudgetAmount"]]

    payroll_budget["CostCenterID"] = payroll_budget["CostCenterID"].astype(int)
    burden_budget["CostCenterID"] = burden_budget["CostCenterID"].astype(int)
    payroll_budget["BudgetAmount"] = payroll_budget["BudgetAmount"].astype(float).round(2)
    burden_budget["BudgetAmount"] = burden_budget["BudgetAmount"].astype(float).round(2)
    expected_payroll["CostCenterID"] = expected_payroll["CostCenterID"].astype(int)
    expected_burden["CostCenterID"] = expected_burden["CostCenterID"].astype(int)
    expected_payroll["BudgetAmount"] = expected_payroll["BudgetAmount"].astype(float).round(2)
    expected_burden["BudgetAmount"] = expected_burden["BudgetAmount"].astype(float).round(2)

    payroll_budget = payroll_budget.sort_values(["FiscalYear", "Month", "CostCenterID"]).reset_index(drop=True)
    burden_budget = burden_budget.sort_values(["FiscalYear", "Month", "CostCenterID"]).reset_index(drop=True)
    expected_payroll = expected_payroll.sort_values(["FiscalYear", "Month", "CostCenterID"]).reset_index(drop=True)
    expected_burden = expected_burden.sort_values(["FiscalYear", "Month", "CostCenterID"]).reset_index(drop=True)

    pd.testing.assert_frame_equal(payroll_budget, expected_payroll)
    pd.testing.assert_frame_equal(burden_budget, expected_burden)

    recurring_totals = (
        budget_lines[
            budget_lines["DriverType"].astype(str).isin(
                {
                    "Recurring Rent Driver",
                    "Recurring Utilities Driver",
                    "Recurring Accrual Driver",
                    "Depreciation Schedule",
                }
            )
            & budget_lines["BudgetCategory"].astype(str).eq("Operating Expense")
        ][["FiscalYear", "Month", "DriverType", "BudgetAmount"]]
        .copy()
        .groupby(["FiscalYear", "Month", "DriverType"], as_index=False, dropna=False)["BudgetAmount"]
        .sum()
    )

    expected_recurring_rows: list[dict[str, float | int | str]] = []
    monthly_depreciation_total = round(
        sum(monthly_depreciation_amount(asset_account_number) for asset_account_number in depreciable_fixed_asset_profiles()),
        2,
    )
    for fiscal_year, fiscal_month in budget_horizon_months(context):
        expected_recurring_rows.extend(
            [
                {
                    "FiscalYear": fiscal_year,
                    "Month": fiscal_month,
                    "DriverType": "Recurring Rent Driver",
                    "BudgetAmount": round(
                        monthly_rent_amount(context, fiscal_year, fiscal_month, "Office")
                        + monthly_rent_amount(context, fiscal_year, fiscal_month, "Warehouse"),
                        2,
                    ),
                },
                {
                    "FiscalYear": fiscal_year,
                    "Month": fiscal_month,
                    "DriverType": "Recurring Utilities Driver",
                    "BudgetAmount": round(monthly_utilities_amount(context, fiscal_year, fiscal_month), 2),
                },
                {
                    "FiscalYear": fiscal_year,
                    "Month": fiscal_month,
                    "DriverType": "Recurring Accrual Driver",
                    "BudgetAmount": round(
                        sum(
                            monthly_accrual_amount(context, fiscal_year, fiscal_month, account_number)
                            for account_number in sorted(MONTHLY_ACCRUAL_BASES)
                        ),
                        2,
                    ),
                },
                {
                    "FiscalYear": fiscal_year,
                    "Month": fiscal_month,
                    "DriverType": "Depreciation Schedule",
                    "BudgetAmount": monthly_depreciation_total,
                },
            ]
        )

    expected_recurring = (
        pd.DataFrame(expected_recurring_rows)
        .sort_values(["FiscalYear", "Month", "DriverType"])
        .reset_index(drop=True)
    )
    recurring_totals = recurring_totals.sort_values(["FiscalYear", "Month", "DriverType"]).reset_index(drop=True)

    pd.testing.assert_frame_equal(recurring_totals, expected_recurring)


def test_budget_balance_sheet_rollforwards_reconcile_to_net_income_and_capex_policy(phase2_budget_context) -> None:
    context = phase2_budget_context
    budget_lines = _budget_lines_with_accounts(context)

    operating_budget = budget_lines[budget_lines["BudgetCategory"].astype(str).isin(SUMMARY_BUDGET_CATEGORIES)].copy()
    monthly_income = (
        operating_budget.assign(
            SignedAmount=lambda frame: frame.apply(
                lambda row: float(row["BudgetAmount"])
                if str(row["BudgetCategory"]) == "Revenue"
                else -float(row["BudgetAmount"]),
                axis=1,
            )
        )[["FiscalYear", "Month", "SignedAmount"]]
        .groupby(["FiscalYear", "Month"], as_index=False, dropna=False)["SignedAmount"]
        .sum()
        .rename(columns={"SignedAmount": "NetIncome"})
        .sort_values(["FiscalYear", "Month"])
        .reset_index(drop=True)
    )
    monthly_income["CurrentYearNetIncome"] = (
        monthly_income.groupby("FiscalYear", sort=False)["NetIncome"].cumsum().round(2)
    )

    balance_sheet = budget_lines[budget_lines["BudgetCategory"].astype(str).eq("Balance Sheet")].copy()
    tracked_account_numbers = [1010, 1020, 1040, 1045, 2010, 2030, 2040]
    ending_balances = (
        balance_sheet[balance_sheet["AccountNumber"].astype(int).isin(tracked_account_numbers)][
            ["FiscalYear", "Month", "AccountNumber", "BudgetAmount"]
        ]
        .groupby(["FiscalYear", "Month", "AccountNumber"], as_index=False, dropna=False)["BudgetAmount"]
        .sum()
    )
    ending_balance_pivot = ending_balances.pivot_table(
        index=["FiscalYear", "Month"],
        columns="AccountNumber",
        values="BudgetAmount",
        fill_value=0.0,
    ).reset_index()
    monthly_depreciation = (
        budget_lines[
            budget_lines["DriverType"].astype(str).eq("Depreciation Schedule")
            & budget_lines["BudgetCategory"].astype(str).eq("Operating Expense")
        ][["FiscalYear", "Month", "BudgetAmount"]]
        .groupby(["FiscalYear", "Month"], as_index=False, dropna=False)["BudgetAmount"]
        .sum()
        .rename(columns={"BudgetAmount": "DepreciationExpense"})
    )
    maintenance_capex_ending = (
        balance_sheet[
            balance_sheet["DriverType"].astype(str).eq("Maintenance Capex Rollforward")
        ][["FiscalYear", "Month", "BudgetAmount"]]
        .groupby(["FiscalYear", "Month"], as_index=False, dropna=False)["BudgetAmount"]
        .sum()
        .rename(columns={"BudgetAmount": "MaintenanceCapexEndingBalance"})
        .sort_values(["FiscalYear", "Month"])
        .reset_index(drop=True)
    )
    opening_balance_lookup = _opening_balance_map(context)
    opening_maintenance_capex_balance = round(
        sum(
            float(amount)
            for account_number, amount in opening_balance_lookup.items()
            if str(account_number) in {"1110", "1120", "1130", "1140"}
        ),
        2,
    )
    maintenance_capex = maintenance_capex_ending.copy()
    maintenance_capex["MaintenanceCapex"] = (
        maintenance_capex["MaintenanceCapexEndingBalance"].astype(float).diff().fillna(
            maintenance_capex["MaintenanceCapexEndingBalance"].astype(float) - opening_maintenance_capex_balance
        )
    ).round(2)
    maintenance_capex = maintenance_capex[["FiscalYear", "Month", "MaintenanceCapex"]]

    accumulated_depreciation_ending = (
        balance_sheet[
            balance_sheet["DriverType"].astype(str).eq("Depreciation Rollforward")
        ][["FiscalYear", "Month", "BudgetAmount"]]
        .groupby(["FiscalYear", "Month"], as_index=False, dropna=False)["BudgetAmount"]
        .sum()
        .rename(columns={"BudgetAmount": "AccumulatedDepreciationEndingBalance"})
        .sort_values(["FiscalYear", "Month"])
        .reset_index(drop=True)
    )
    cash_rollforward = (
        ending_balance_pivot
        .merge(monthly_income[["FiscalYear", "Month", "NetIncome"]], on=["FiscalYear", "Month"], how="left")
        .merge(monthly_depreciation, on=["FiscalYear", "Month"], how="left")
        .merge(maintenance_capex, on=["FiscalYear", "Month"], how="left")
        .fillna({"NetIncome": 0.0, "DepreciationExpense": 0.0, "MaintenanceCapex": 0.0})
        .sort_values(["FiscalYear", "Month"])
        .reset_index(drop=True)
    )

    previous_balances = {
        account_number: round(float(opening_balance_lookup.get(str(account_number), 0.0)), 2)
        for account_number in tracked_account_numbers
    }
    for row in cash_rollforward.to_dict("records"):
        ending_cash = round(float(row.get(1010, 0.0)), 2)
        accounts_receivable_change = round(float(row.get(1020, 0.0)) - previous_balances[1020], 2)
        finished_goods_change = round(float(row.get(1040, 0.0)) - previous_balances[1040], 2)
        materials_change = round(float(row.get(1045, 0.0)) - previous_balances[1045], 2)
        accounts_payable_change = round(float(row.get(2010, 0.0)) - previous_balances[2010], 2)
        accrued_payroll_change = round(float(row.get(2030, 0.0)) - previous_balances[2030], 2)
        accrued_expenses_change = round(float(row.get(2040, 0.0)) - previous_balances[2040], 2)
        expected_cash = round(
            previous_balances[1010]
            + float(row["NetIncome"])
            + float(row["DepreciationExpense"])
            - accounts_receivable_change
            - finished_goods_change
            - materials_change
            + accounts_payable_change
            + accrued_payroll_change
            + accrued_expenses_change
            - float(row["MaintenanceCapex"]),
            2,
        )
        assert ending_cash == expected_cash
        previous_balances = {
            1010: ending_cash,
            1020: round(float(row.get(1020, 0.0)), 2),
            1040: round(float(row.get(1040, 0.0)), 2),
            1045: round(float(row.get(1045, 0.0)), 2),
            2010: round(float(row.get(2010, 0.0)), 2),
            2030: round(float(row.get(2030, 0.0)), 2),
            2040: round(float(row.get(2040, 0.0)), 2),
        }

    retained_earnings_account_id = int(
        context.tables["Account"].loc[
            context.tables["Account"]["AccountNumber"].astype(str).eq("3030"), "AccountID"
        ].iloc[0]
    )
    retained_earnings = (
        balance_sheet[balance_sheet["AccountID"].astype(int).eq(retained_earnings_account_id)][
            ["FiscalYear", "Month", "BudgetAmount"]
        ]
        .rename(columns={"BudgetAmount": "RetainedEarnings"})
        .sort_values(["FiscalYear", "Month"])
        .reset_index(drop=True)
    )
    monthly_net_income_by_year = (
        monthly_income.groupby("FiscalYear", as_index=False, dropna=False)["NetIncome"].sum().rename(
            columns={"NetIncome": "FiscalYearNetIncome"}
        )
    )

    retained_lookup = {
        (int(row.FiscalYear), int(row.Month)): round(float(row.RetainedEarnings), 2)
        for row in retained_earnings.itertuples(index=False)
    }
    annual_income_lookup = {
        int(row.FiscalYear): round(float(row.FiscalYearNetIncome), 2)
        for row in monthly_net_income_by_year.itertuples(index=False)
    }

    for fiscal_year in sorted(annual_income_lookup):
        if (fiscal_year, 1) not in retained_lookup or (fiscal_year - 1, 12) not in retained_lookup:
            continue
        retained_earnings_increase = round(
            retained_lookup[(fiscal_year, 1)] - retained_lookup[(fiscal_year - 1, 12)],
            2,
        )
        assert retained_earnings_increase == annual_income_lookup[fiscal_year - 1]

    comparison = maintenance_capex.merge(monthly_depreciation, on=["FiscalYear", "Month"], how="inner")
    assert not comparison.empty
    assert comparison["MaintenanceCapex"].round(2).equals(comparison["DepreciationExpense"].round(2))
    opening_accumulated_depreciation_balance = round(
        sum(
            float(amount)
            for account_number, amount in opening_balance_lookup.items()
            if str(account_number) in {"1150", "1160", "1170"}
        ),
        2,
    )
    accumulated_depreciation_change = accumulated_depreciation_ending.copy()
    accumulated_depreciation_change["DepreciationRollforwardChange"] = (
        accumulated_depreciation_change["AccumulatedDepreciationEndingBalance"].astype(float).diff().fillna(
            accumulated_depreciation_change["AccumulatedDepreciationEndingBalance"].astype(float)
            - opening_accumulated_depreciation_balance
        )
    ).round(2)
    depreciation_comparison = accumulated_depreciation_change.merge(
        monthly_depreciation,
        on=["FiscalYear", "Month"],
        how="inner",
    )
    assert depreciation_comparison["DepreciationRollforwardChange"].round(2).equals(
        depreciation_comparison["DepreciationExpense"].round(2)
    )
