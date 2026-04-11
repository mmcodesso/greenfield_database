from __future__ import annotations

from collections import Counter
import sqlite3
from pathlib import Path

import pandas as pd

from greenfield_dataset.main import build_phase17


TARGETED_AUDIT_QUERY_EXPECTATIONS = {
    "05_duplicate_payment_reference_review.sql": 1,
    "06_potential_anomaly_review.sql": 1,
    "11_payroll_control_review.sql": 1,
    "12_labor_time_after_close_and_paid_without_time.sql": 1,
    "13_over_under_accrual_review.sql": 1,
    "14_missing_routing_or_operation_link_review.sql": 1,
    "15_operation_sequence_and_final_completion_review.sql": 1,
    "16_schedule_on_nonworking_day_review.sql": 1,
    "17_over_capacity_day_review.sql": 1,
    "18_completion_before_scheduled_operation_end.sql": 1,
    "19_time_clock_exceptions_by_employee_supervisor_work_center.sql": 1,
    "20_labor_outside_scheduled_operation_window_review.sql": 1,
    "21_paid_without_clock_and_clock_without_pay_review.sql": 1,
    "22_anomaly_log_to_source_document_tie_out.sql": 1,
    "25_time_clock_payroll_labor_bridge_review.sql": 1,
    "26_duplicate_ap_reference_detail_review.sql": 1,
}


def _execute_all_starter_sql(sqlite_path: Path) -> None:
    sql_files = sorted(Path("queries").rglob("*.sql"))
    assert sql_files, "No starter SQL files were found."

    with sqlite3.connect(sqlite_path) as connection:
        for sql_file in sql_files:
            sql = sql_file.read_text(encoding="utf-8")
            result = pd.read_sql_query(sql, connection)
            assert len(result.columns) >= 1, f"Query returned no columns: {sql_file}"


def test_phase17_helper_generates_clean_dataset() -> None:
    context = build_phase17("config/settings_validation.yaml", validation_scope="operational")
    phase17 = context.validation_results["phase17"]

    assert phase17["exceptions"] == []
    assert phase17["validation_scope"] == "operational"
    assert phase17["time_clock_controls"]["exception_count"] == 0
    assert phase17["capacity_controls"]["exception_count"] == 0


def test_phase17_new_anomalies_are_logged_and_detectable(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    context = default_anomaly_dataset_artifacts["context"]
    results = context.validation_results["phase8"]
    anomaly_counts = Counter(entry["anomaly_type"] for entry in context.anomaly_log)

    for anomaly_type in [
        "duplicate_supplier_invoice_number",
        "missing_payroll_payment",
        "payroll_payment_before_approval",
        "missing_work_order_operations",
        "invalid_direct_labor_operation_link",
        "overlapping_operation_sequence",
    ]:
        assert anomaly_counts[anomaly_type] > 0

    duplicate_payment_refs = (
        context.tables["DisbursementPayment"]
        .dropna(subset=["CheckNumber"])
        .groupby(["SupplierID", "CheckNumber"])
        .size()
    )
    assert duplicate_payment_refs.gt(1).any()

    duplicate_invoice_numbers = context.tables["PurchaseInvoice"].groupby(["SupplierID", "InvoiceNumber"]).size()
    assert duplicate_invoice_numbers.gt(1).any()

    payment_register_ids = set(context.tables["PayrollPayment"]["PayrollRegisterID"].astype(int))
    approved_registers = context.tables["PayrollRegister"][
        context.tables["PayrollRegister"]["Status"].eq("Approved")
    ]["PayrollRegisterID"].astype(int)
    assert any(register_id not in payment_register_ids for register_id in approved_registers)

    payroll_payment_join = context.tables["PayrollPayment"].merge(
        context.tables["PayrollRegister"][["PayrollRegisterID", "ApprovedDate"]],
        on="PayrollRegisterID",
        how="inner",
    )
    assert (
        pd.to_datetime(payroll_payment_join["PaymentDate"])
        < pd.to_datetime(payroll_payment_join["ApprovedDate"])
    ).any()

    work_orders = context.tables["WorkOrder"][["WorkOrderID", "WorkOrderNumber"]].copy()
    operation_counts = context.tables["WorkOrderOperation"].groupby("WorkOrderID").size().rename("OperationCount")
    work_orders = work_orders.merge(operation_counts, on="WorkOrderID", how="left").fillna({"OperationCount": 0})
    assert work_orders["OperationCount"].eq(0).any()

    labor_entries = context.tables["LaborTimeEntry"].copy()
    operations = context.tables["WorkOrderOperation"][["WorkOrderOperationID", "WorkOrderID"]].copy()
    labor_with_ops = labor_entries.merge(
        operations,
        on="WorkOrderOperationID",
        how="left",
        suffixes=("", "_operation"),
    )
    direct_labor_gaps = labor_with_ops[
        labor_with_ops["LaborType"].eq("Direct Manufacturing")
        & (
            labor_with_ops["WorkOrderOperationID"].isna()
            | labor_with_ops["WorkOrderID_operation"].isna()
            | labor_with_ops["WorkOrderID"].astype("Int64") != labor_with_ops["WorkOrderID_operation"].astype("Int64")
        )
    ]
    assert not direct_labor_gaps.empty

    ordered_operations = context.tables["WorkOrderOperation"].sort_values(["WorkOrderID", "OperationSequence"])
    prior_end = ordered_operations.groupby("WorkOrderID")["ActualEndDate"].shift(1)
    overlap_rows = ordered_operations[
        prior_end.notna()
        & ordered_operations["ActualStartDate"].notna()
        & (
            pd.to_datetime(ordered_operations["ActualStartDate"])
            < pd.to_datetime(prior_end)
        )
    ]
    assert not overlap_rows.empty

    assert results["anomaly_count"] >= len(context.anomaly_log)


def test_phase17_default_build_targeted_audit_queries_return_rows(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(default_anomaly_dataset_artifacts["sqlite_path"])
    assert sqlite_path.exists()

    with sqlite3.connect(sqlite_path) as connection:
        for sql_name, minimum_rows in TARGETED_AUDIT_QUERY_EXPECTATIONS.items():
            sql = Path("queries/audit", sql_name).read_text(encoding="utf-8")
            result = pd.read_sql_query(sql, connection)
            assert len(result) >= minimum_rows, f"Expected rows from {sql_name}, found {len(result)}"


def test_phase17_clean_validation_build_all_starter_sql_executes(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    assert sqlite_path.exists()
    _execute_all_starter_sql(sqlite_path)


def test_phase17_default_build_all_starter_sql_executes(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(default_anomaly_dataset_artifacts["sqlite_path"])
    assert sqlite_path.exists()
    _execute_all_starter_sql(sqlite_path)


def test_phase17_default_sqlite_contains_support_tables(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(default_anomaly_dataset_artifacts["sqlite_path"])
    excel_path = Path(default_anomaly_dataset_artifacts["excel_path"])
    assert sqlite_path.exists()
    assert excel_path.exists()

    with sqlite3.connect(sqlite_path) as connection:
        tables = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('AnomalyLog', 'ValidationSummary')",
            connection,
        )["name"].tolist()
    assert set(tables) == {"AnomalyLog", "ValidationSummary"}


def test_phase17_docs_include_cases_matrix_and_subprocess_diagrams() -> None:
    for path in [
        Path("docs/analytics/cases/index.md"),
        Path("docs/analytics/cases/o2c-trace-case.md"),
        Path("docs/analytics/cases/p2p-accrual-settlement-case.md"),
        Path("docs/analytics/cases/manufacturing-labor-cost-case.md"),
        Path("docs/analytics/cases/audit-exception-lab.md"),
    ]:
        assert path.exists(), f"Missing Phase 17 case doc: {path}"

    audit_doc = Path("docs/analytics/audit.md").read_text(encoding="utf-8")
    assert "## Anomaly Coverage Matrix" in audit_doc

    for path in [
        Path("docs/processes/o2c.md"),
        Path("docs/processes/o2c-returns-credits-refunds.md"),
        Path("docs/processes/p2p.md"),
        Path("docs/processes/manufacturing.md"),
        Path("docs/processes/payroll.md"),
        Path("docs/processes/manual-journals-and-close.md"),
    ]:
        text = path.read_text(encoding="utf-8")
        assert "Subprocess Spotlight" in text
