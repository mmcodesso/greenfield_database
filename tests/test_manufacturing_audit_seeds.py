from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


DETAIL_QUERY_PATH = Path("queries/audit/52_released_work_orders_due_without_actual_start_review.sql")
SUMMARY_QUERY_PATH = Path("queries/audit/53_released_work_orders_due_without_actual_start_summary.sql")


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    sql_text = sql_path.read_text(encoding="utf-8")
    connection = sqlite3.connect(sqlite_path)
    try:
        return pd.read_sql_query(sql_text, connection)
    finally:
        connection.close()


def test_manufacturing_audit_seeds_absent_from_clean_validation_build(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    context = clean_validation_dataset_artifacts["context"]
    phase23 = context.validation_results["phase23"]

    assert phase23["manufacturing_controls"]["exception_count"] == 0
    assert phase23["manufacturing_audit_seeds"]["exception_count"] == 0

    detail = _read_sql_result(Path(clean_validation_dataset_artifacts["sqlite_path"]), DETAIL_QUERY_PATH)
    summary = _read_sql_result(Path(clean_validation_dataset_artifacts["sqlite_path"]), SUMMARY_QUERY_PATH)
    assert detail.empty
    assert summary.empty


def test_manufacturing_audit_seeds_present_in_default_published_build(
    default_anomaly_published_package_artifacts: dict[str, object],
) -> None:
    context = default_anomaly_published_package_artifacts["context"]
    phase8 = context.validation_results["phase8"]

    assert phase8["manufacturing_controls"]["exception_count"] == 0
    assert phase8["manufacturing_audit_seeds"]["exception_count"] == 5
    seeded_work_order_ids = {
        int(exception["work_order_id"])
        for exception in phase8["manufacturing_audit_seeds"]["exceptions"]
    }
    assert len(seeded_work_order_ids) == 5
    assert {
        exception["type"] for exception in phase8["manufacturing_audit_seeds"]["exceptions"]
    } == {"released_work_order_due_without_actual_start"}

    log_text = Path(default_anomaly_published_package_artifacts["generation_log_path"]).read_text(encoding="utf-8")
    assert "VALIDATION | phase8.manufacturing_controls | exception_count=0" in log_text
    assert "VALIDATION | phase8.manufacturing_audit_seeds | exception_count=5" in log_text


def test_manufacturing_audit_seed_queries_and_support_workbook_align(
    default_anomaly_published_package_artifacts: dict[str, object],
) -> None:
    context = default_anomaly_published_package_artifacts["context"]
    seeded_work_order_ids = {
        int(exception["work_order_id"])
        for exception in context.validation_results["phase8"]["manufacturing_audit_seeds"]["exceptions"]
    }
    sqlite_path = Path(default_anomaly_published_package_artifacts["sqlite_path"])
    detail = _read_sql_result(sqlite_path, DETAIL_QUERY_PATH)
    summary = _read_sql_result(sqlite_path, SUMMARY_QUERY_PATH)

    assert set(detail["WorkOrderID"].astype(int)) == seeded_work_order_ids
    assert len(detail) == len(seeded_work_order_ids)
    assert set(detail["FirstActualStartStatus"]) == {"No actual start recorded"}
    assert int(summary["WorkOrderCount"].sum()) == len(seeded_work_order_ids)

    support_path = Path(default_anomaly_published_package_artifacts["support_excel_path"])
    checks = pd.read_excel(support_path, sheet_name="ValidationChecks")
    exceptions = pd.read_excel(support_path, sheet_name="ValidationExceptions")

    phase8_check = checks[
        checks["Stage"].astype(str).eq("phase8")
        & checks["Area"].astype(str).eq("manufacturing_audit_seeds")
    ]
    assert not phase8_check.empty
    assert int(phase8_check.iloc[0]["ExceptionCount"]) == 5

    phase8_exceptions = exceptions[
        exceptions["Stage"].astype(str).eq("phase8")
        & exceptions["Area"].astype(str).eq("manufacturing_audit_seeds")
    ]
    assert len(phase8_exceptions) == 5
    assert set(phase8_exceptions["ExceptionType"].astype(str)) == {
        "released_work_order_due_without_actual_start"
    }


def test_manufacturing_audit_seed_docs_and_catalog_entries_exist() -> None:
    query_manifest = Path("src/generated/queryManifest.js").read_text(encoding="utf-8")
    query_doc_collections = Path("src/generated/queryDocCollections.js").read_text(encoding="utf-8")
    audit_guide = Path("docs/analytics/audit.md").read_text(encoding="utf-8")
    audit_case = Path("docs/analytics/cases/audit-review-pack-case.md").read_text(encoding="utf-8")
    instructor_guide = Path("docs/teach-with-data/instructor-guide.md").read_text(encoding="utf-8")

    assert "audit/52_released_work_orders_due_without_actual_start_review.sql" in query_manifest
    assert "audit/53_released_work_orders_due_without_actual_start_summary.sql" in query_manifest
    assert "audit/52_released_work_orders_due_without_actual_start_review.sql" in query_doc_collections
    assert "audit/53_released_work_orders_due_without_actual_start_summary.sql" in query_doc_collections
    assert "released work orders due without actual start review" in audit_guide
    assert "released work orders due without actual start summary" in audit_guide
    assert "manufacturing_audit_seeds" in audit_case
    assert "manufacturing audit-seed" in instructor_guide
