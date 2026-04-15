from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from CharlesRiver_dataset.budgets import generate_budgets, generate_opening_balances
from CharlesRiver_dataset.main import build_phase22
from CharlesRiver_dataset.manufacturing import (
    close_eligible_work_orders,
    generate_boms,
    generate_month_manufacturing_activity,
    generate_month_work_orders_and_requisitions,
    generate_work_center_calendars,
    generate_work_centers_and_routings,
)
from CharlesRiver_dataset.master_data import (
    approver_employee_id,
    backfill_cost_center_managers,
    employee_ids_for_cost_center_as_of,
    employee_id_by_titles,
    employee_master,
    generate_cost_centers,
    generate_customers,
    generate_employees,
    generate_items,
    generate_suppliers,
    generate_warehouses,
    load_accounts,
)
from CharlesRiver_dataset.o2c import (
    generate_month_cash_receipts,
    generate_month_customer_refunds,
    generate_month_o2c,
    generate_month_sales_invoices,
    generate_month_sales_returns,
    generate_month_shipments,
)
from CharlesRiver_dataset.p2p import (
    generate_month_disbursements,
    generate_month_goods_receipts,
    generate_month_purchase_invoices,
    generate_month_purchase_orders,
    generate_month_requisitions,
)
from CharlesRiver_dataset.payroll import (
    employee_available_for_work_date,
    generate_month_payroll,
    generate_payroll_periods,
    generate_shift_definitions_and_assignments,
)
from CharlesRiver_dataset.planning import (
    generate_demand_forecasts,
    generate_inventory_policies,
    generate_month_planning,
)
from CharlesRiver_dataset.schema import create_empty_tables
from CharlesRiver_dataset.settings import GenerationContext, initialize_context, load_settings


MONTH_STEP_SEQUENCE = [
    ("generate_month_o2c", generate_month_o2c),
    ("generate_month_planning", generate_month_planning),
    ("generate_month_requisitions", generate_month_requisitions),
    ("generate_month_work_orders_and_requisitions", generate_month_work_orders_and_requisitions),
    ("generate_month_purchase_orders", generate_month_purchase_orders),
    ("generate_month_goods_receipts", generate_month_goods_receipts),
    ("generate_month_manufacturing_activity", generate_month_manufacturing_activity),
    ("generate_month_payroll", generate_month_payroll),
    ("close_eligible_work_orders", close_eligible_work_orders),
    ("generate_month_shipments", generate_month_shipments),
    ("generate_month_sales_invoices", generate_month_sales_invoices),
    ("generate_month_cash_receipts", generate_month_cash_receipts),
    ("generate_month_sales_returns", generate_month_sales_returns),
    ("generate_month_customer_refunds", generate_month_customer_refunds),
    ("generate_month_purchase_invoices", generate_month_purchase_invoices),
    ("generate_month_disbursements", generate_month_disbursements),
]


def _prepare_month_generation_context(config_path: str) -> GenerationContext:
    settings = load_settings(config_path)
    context = initialize_context(settings)
    create_empty_tables(context)
    generate_cost_centers(context)
    load_accounts(context, accounts_path="config/accounts.csv")
    generate_employees(context)
    backfill_cost_center_managers(context)
    generate_warehouses(context)
    generate_items(context)
    generate_boms(context)
    generate_work_centers_and_routings(context)
    generate_work_center_calendars(context)
    generate_customers(context)
    generate_suppliers(context)
    generate_opening_balances(context)
    generate_budgets(context)
    generate_payroll_periods(context)
    generate_shift_definitions_and_assignments(context)
    generate_inventory_policies(context)
    generate_demand_forecasts(context)
    return context


def _run_first_five_months(context: GenerationContext) -> dict[tuple[int, int], dict[str, float]]:
    timings: dict[tuple[int, int], dict[str, float]] = {}
    for year, month in [(2026, 1), (2026, 2), (2026, 3), (2026, 4), (2026, 5)]:
        month_timings: dict[str, float] = {}
        month_started_at = time.perf_counter()
        for step_name, step_fn in MONTH_STEP_SEQUENCE:
            step_started_at = time.perf_counter()
            result = step_fn(context, year, month)
            month_timings[step_name] = time.perf_counter() - step_started_at
            if step_name == "generate_month_manufacturing_activity" and result:
                for followup_name, followup_fn in [
                    ("generate_month_purchase_orders_followup", generate_month_purchase_orders),
                    ("generate_month_goods_receipts_followup", generate_month_goods_receipts),
                    ("generate_month_manufacturing_activity_followup", generate_month_manufacturing_activity),
                ]:
                    followup_started_at = time.perf_counter()
                    followup_fn(context, year, month)
                    month_timings[followup_name] = time.perf_counter() - followup_started_at
        month_timings["month_total"] = time.perf_counter() - month_started_at
        timings[(year, month)] = month_timings
    return timings


def _legacy_valid_employees(
    context: GenerationContext,
    event_date: pd.Timestamp | str | None = None,
    *,
    cost_center_id: int | None = None,
    cost_center_name: str | None = None,
    job_titles: list[str] | tuple[str, ...] | None = None,
    authorization_levels: list[str] | tuple[str, ...] | None = None,
    minimum_approval_amount: float | None = None,
) -> pd.DataFrame:
    employees = employee_master(context)
    if employees.empty:
        return employees.copy()

    if event_date is None:
        rows = employees[employees["IsActive"].astype(int).eq(1)].copy()
    else:
        timestamp = pd.Timestamp(event_date)
        rows = employees[
            employees["HireDateValue"].le(timestamp)
            & (employees["TerminationDateValue"].isna() | employees["TerminationDateValue"].ge(timestamp))
        ].copy()

    if cost_center_name is not None:
        cost_centers = context.tables["CostCenter"]
        matches = cost_centers.loc[cost_centers["CostCenterName"].eq(cost_center_name), "CostCenterID"]
        if matches.empty:
            return rows.head(0)
        cost_center_id = int(matches.iloc[0])
    if cost_center_id is not None:
        rows = rows[rows["CostCenterID"].astype(int).eq(int(cost_center_id))]
    if job_titles:
        rows = rows[rows["JobTitle"].isin(list(job_titles))]
    if authorization_levels:
        rows = rows[rows["AuthorizationLevel"].isin(list(authorization_levels))]
    if minimum_approval_amount is not None:
        rows = rows[rows["MaxApprovalAmount"].astype(float) >= float(minimum_approval_amount)]
    return rows.copy()


def _legacy_employee_ids_for_cost_center_as_of(
    context: GenerationContext,
    cost_center_name_or_id: str | int,
    event_date: pd.Timestamp | str | None = None,
) -> list[int]:
    rows = (
        _legacy_valid_employees(context, event_date, cost_center_name=str(cost_center_name_or_id))
        if isinstance(cost_center_name_or_id, str)
        else _legacy_valid_employees(context, event_date, cost_center_id=int(cost_center_name_or_id))
    )
    if rows.empty:
        rows = _legacy_valid_employees(context, event_date)
    if rows.empty:
        rows = context.tables["Employee"].copy()
    return rows.sort_values("EmployeeID")["EmployeeID"].astype(int).tolist()


def _legacy_employee_id_by_titles(
    context: GenerationContext,
    *job_titles: str,
    event_date: pd.Timestamp | str | None = None,
) -> int | None:
    rows = _legacy_valid_employees(context, event_date, job_titles=job_titles)
    if rows.empty:
        return None
    for title in job_titles:
        matches = rows.loc[rows["JobTitle"].eq(title), "EmployeeID"]
        if not matches.empty:
            return int(matches.sort_values().iloc[0])
    return int(rows.sort_values("EmployeeID").iloc[0]["EmployeeID"])


def _legacy_approver_employee_id(
    context: GenerationContext,
    event_date: pd.Timestamp | str | None = None,
    *,
    preferred_titles: list[str] | tuple[str, ...] | None = None,
    minimum_amount: float = 0.0,
    fallback_cost_center_name: str | None = None,
) -> int:
    authorization_rank = {"Executive": 0, "Manager": 1, "Supervisor": 2, "Staff": 3}
    if preferred_titles:
        preferred_id = _legacy_employee_id_by_titles(context, *preferred_titles, event_date=event_date)
        if preferred_id is not None:
            rows = _legacy_valid_employees(context, event_date, job_titles=preferred_titles)
            if minimum_amount <= 0 or rows.loc[
                rows["EmployeeID"].astype(int).eq(int(preferred_id)),
                "MaxApprovalAmount",
            ].astype(float).fillna(0).ge(float(minimum_amount)).any():
                return int(preferred_id)

    eligible = _legacy_valid_employees(
        context,
        event_date,
        authorization_levels=["Manager", "Executive"],
        minimum_approval_amount=minimum_amount,
    )
    if not eligible.empty:
        eligible = eligible.copy()
        eligible["AuthorizationRank"] = eligible["AuthorizationLevel"].map(authorization_rank).fillna(99)
        return int(eligible.sort_values(["AuthorizationRank", "EmployeeID"]).iloc[0]["EmployeeID"])

    if fallback_cost_center_name is not None:
        ids = _legacy_employee_ids_for_cost_center_as_of(context, fallback_cost_center_name, event_date)
        if ids:
            return int(ids[0])

    any_valid = _legacy_valid_employees(context, event_date)
    if not any_valid.empty:
        return int(any_valid.sort_values("EmployeeID").iloc[0]["EmployeeID"])

    return int(context.tables["Employee"].sort_values("EmployeeID").iloc[0]["EmployeeID"])


def test_phase22_2_employee_cache_matches_legacy_selection_logic() -> None:
    context = _prepare_month_generation_context("config/settings_validation.yaml")
    representative_dates: list[pd.Timestamp | None] = [
        None,
        pd.Timestamp("2026-01-15"),
        pd.Timestamp("2027-06-30"),
        pd.Timestamp("2030-12-31"),
    ]

    for event_date in representative_dates:
        for cost_center in ["Manufacturing", "Purchasing", "Administration"]:
            assert employee_ids_for_cost_center_as_of(context, cost_center, event_date) == _legacy_employee_ids_for_cost_center_as_of(
                context,
                cost_center,
                event_date,
            )
        for job_titles in [
            ("Chief Financial Officer", "Controller"),
            ("Production Planner", "Production Manager"),
            ("Buyer", "Purchasing Manager", "Procurement Analyst"),
        ]:
            assert employee_id_by_titles(context, *job_titles, event_date=event_date) == _legacy_employee_id_by_titles(
                context,
                *job_titles,
                event_date=event_date,
            )
        for minimum_amount in [0.0, 2500.0, 25000.0, 125000.0]:
            assert approver_employee_id(
                context,
                event_date,
                preferred_titles=["Chief Financial Officer", "Controller", "Accounting Manager"],
                minimum_amount=minimum_amount,
                fallback_cost_center_name="Purchasing",
            ) == _legacy_approver_employee_id(
                context,
                event_date,
                preferred_titles=["Chief Financial Officer", "Controller", "Accounting Manager"],
                minimum_amount=minimum_amount,
                fallback_cost_center_name="Purchasing",
            )


def test_phase22_2_payroll_availability_matches_legacy_logic() -> None:
    context = _prepare_month_generation_context("config/settings_validation.yaml")
    employees = employee_master(context).sort_values("EmployeeID").head(12).copy()
    for employee in employees.to_dict(orient="records"):
        hire_date = pd.Timestamp(employee["HireDateValue"])
        test_dates = [
            hire_date - pd.Timedelta(days=1),
            hire_date,
            hire_date + pd.Timedelta(days=30),
        ]
        if pd.notna(employee["TerminationDateValue"]):
            termination_date = pd.Timestamp(employee["TerminationDateValue"])
            test_dates.extend([
                termination_date - pd.Timedelta(days=1),
                termination_date,
                termination_date + pd.Timedelta(days=1),
            ])
        for work_date in test_dates:
            legacy_frame = pd.DataFrame([employee])
            legacy_result = bool(
                (
                    legacy_frame["HireDateValue"].le(pd.Timestamp(work_date))
                    & (
                        legacy_frame["TerminationDateValue"].isna()
                        | legacy_frame["TerminationDateValue"].ge(pd.Timestamp(work_date))
                    )
                ).iloc[0]
            )
            assert employee_available_for_work_date(employee, work_date) == legacy_result


def test_phase22_2_first_five_months_are_deterministic_on_validation_profile() -> None:
    context_one = _prepare_month_generation_context("config/settings_validation.yaml")
    context_two = _prepare_month_generation_context("config/settings_validation.yaml")

    _run_first_five_months(context_one)
    _run_first_five_months(context_two)

    for table_name in [
        "WorkOrder",
        "WorkOrderOperation",
        "WorkOrderOperationSchedule",
        "PurchaseInvoice",
        "DisbursementPayment",
        "TimeClockEntry",
        "LaborTimeEntry",
    ]:
        pd.testing.assert_frame_equal(
            context_one.tables[table_name].reset_index(drop=True),
            context_two.tables[table_name].reset_index(drop=True),
            check_dtype=False,
        )


def test_phase22_2_month_benchmark_meets_targets() -> None:
    context = _prepare_month_generation_context("config/settings.yaml")
    timings = _run_first_five_months(context)
    may_timings = timings[(2026, 5)]

    assert may_timings["generate_month_work_orders_and_requisitions"] < 8.0
    assert may_timings["generate_month_purchase_invoices"] < 2.5
    assert may_timings["generate_month_disbursements"] < 1.5
    assert may_timings["generate_month_payroll"] < 3.5
    assert may_timings["month_total"] < 30.0


def test_phase22_2_month_step_logging_and_clean_build_regression(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    log_path = Path(clean_validation_dataset_artifacts["generation_log_path"])
    log_text = log_path.read_text(encoding="utf-8")

    assert "MONTH STEP | 2026-01 | generate_month_work_orders_and_requisitions |" in log_text
    assert "MONTH STEP | 2026-01 | generate_month_purchase_invoices |" in log_text
    assert "MONTH STEP | 2026-01 | generate_month_payroll |" in log_text
    assert "MONTH DONE | 2026-01 |" in log_text

    context = build_phase22("config/settings_validation.yaml", validation_scope="full")
    assert context.validation_results["phase22"]["exceptions"] == []
