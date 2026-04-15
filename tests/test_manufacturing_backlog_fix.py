from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from CharlesRiver_dataset.main import _generate_phase2_master_data_and_planning
from CharlesRiver_dataset.main import build_phase23
from CharlesRiver_dataset.main import fiscal_months
from CharlesRiver_dataset.main import generate_month_planning
from CharlesRiver_dataset.manufacturing import (
    generate_month_manufacturing_activity,
    generate_month_work_orders_and_requisitions,
    scheduled_work_order_ids,
    close_eligible_work_orders,
)
from CharlesRiver_dataset.master_data import (
    backfill_cost_center_managers,
    generate_cost_centers,
    generate_employees,
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
from CharlesRiver_dataset.payroll import generate_month_payroll, labor_time_entries
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


def _prepare_context(config_path: str) -> GenerationContext:
    settings = load_settings(config_path)
    context = initialize_context(settings)
    create_empty_tables(context)
    generate_cost_centers(context)
    load_accounts(context, accounts_path="config/accounts.csv")
    generate_employees(context)
    backfill_cost_center_managers(context)
    generate_warehouses(context)
    _generate_phase2_master_data_and_planning(context, log_substeps=False)
    return context


def _run_full_month_sequence(context: GenerationContext) -> dict[tuple[int, int], dict[str, float]]:
    timings: dict[tuple[int, int], dict[str, float]] = {}
    for year, month in fiscal_months(context):
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


def test_manufacturing_backlog_fix_clean_build_controls(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    context = clean_validation_dataset_artifacts["context"]
    assert context.validation_results["phase23"]["exceptions"] == []

    work_orders = context.tables["WorkOrder"].copy()
    work_order_operations = context.tables["WorkOrderOperation"].copy()
    scheduled_ids = scheduled_work_order_ids(context)
    fiscal_end_text = pd.Timestamp(context.settings.fiscal_year_end).strftime("%Y-%m-%d")
    scheduled_operation_ids = (
        set(context.tables["WorkOrderOperationSchedule"]["WorkOrderOperationID"].astype(int).tolist())
        if not context.tables["WorkOrderOperationSchedule"].empty
        else set()
    )

    released_without_schedule = work_orders[
        work_orders["Status"].eq("Released")
        & ~work_orders["WorkOrderID"].astype(int).isin(scheduled_ids)
    ]
    assert released_without_schedule.empty

    unscheduled_fallback_operations = work_order_operations[
        ~work_order_operations["WorkOrderOperationID"].astype(int).isin(scheduled_operation_ids)
        & (
            work_order_operations["PlannedStartDate"].astype(str).eq(fiscal_end_text)
            | work_order_operations["PlannedEndDate"].astype(str).eq(fiscal_end_text)
        )
    ]
    assert unscheduled_fallback_operations.empty

    labor_entries = labor_time_entries(context)
    direct_labor_work_orders = set(
        labor_entries.loc[
            labor_entries["LaborType"].eq("Direct Manufacturing")
            & labor_entries["WorkOrderID"].notna(),
            "WorkOrderID",
        ].astype(int).tolist()
    )
    completed_without_direct_labor = work_orders[
        work_orders["Status"].eq("Completed")
        & ~work_orders["WorkOrderID"].astype(int).isin(direct_labor_work_orders)
    ]
    payroll_period_starts = sorted(pd.to_datetime(context.tables["PayrollPeriod"]["PeriodStartDate"]).tolist())
    latest_payroll_period_start = payroll_period_starts[-2] if len(payroll_period_starts) >= 2 else payroll_period_starts[-1]
    older_completed_without_direct_labor = completed_without_direct_labor[
        pd.to_datetime(completed_without_direct_labor["CompletedDate"]) < latest_payroll_period_start
    ]
    assert older_completed_without_direct_labor.empty

    closed_count = int(work_orders["Status"].eq("Closed").sum())
    completed_count = int(work_orders["CompletedDate"].notna().sum())
    assert closed_count > 0
    assert closed_count >= max(1, int(completed_count * 0.60))

    log_text = Path(clean_validation_dataset_artifacts["generation_log_path"]).read_text(encoding="utf-8")
    assert "MANUFACTURING ACTIVITY | 2026-01 |" in log_text
    assert "released_without_schedule=0" in log_text


def test_manufacturing_backlog_fix_late_horizon_benchmark() -> None:
    context = _prepare_context("config/settings.yaml")
    timings = _run_full_month_sequence(context)

    ordered_months = sorted(timings)
    benchmark_months = ordered_months[-4:]
    month_timing_rows = [timings[month_key] for month_key in benchmark_months]

    for month_timings in month_timing_rows:
        assert "generate_month_manufacturing_activity" in month_timings
        assert "generate_month_work_orders_and_requisitions" in month_timings
        assert "generate_month_payroll" in month_timings
        assert "close_eligible_work_orders" in month_timings

    penultimate = month_timing_rows[-2]
    final_month = month_timing_rows[-1]
    assert final_month["generate_month_manufacturing_activity"] <= penultimate["generate_month_manufacturing_activity"] * 1.25
    assert final_month["generate_month_manufacturing_activity"] < 60.0
