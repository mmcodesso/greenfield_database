from __future__ import annotations

from collections import Counter
import sqlite3
from pathlib import Path

import pandas as pd

from greenfield_dataset.main import build_phase20
from greenfield_dataset.validations import validate_phase20


PHASE20_NEW_AUDIT_QUERIES = [
    Path("queries/audit/34_current_state_employee_assignment_review.sql"),
    Path("queries/audit/35_approval_authority_limit_review.sql"),
    Path("queries/audit/36_item_status_alignment_review.sql"),
]

PHASE20_RELATED_AUDIT_QUERIES = [
    Path("queries/audit/29_executive_role_uniqueness_and_control_assignment_review.sql"),
    Path("queries/audit/30_item_master_completeness_review.sql"),
    Path("queries/audit/31_discontinued_or_prelaunch_item_activity_review.sql"),
    Path("queries/audit/32_approval_authority_review_by_expected_role_family.sql"),
    Path("queries/audit/33_terminated_employee_activity_rollup_by_process_area.sql"),
]


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_path.read_text(encoding="utf-8"), connection)


def test_phase20_helper_generates_clean_dataset() -> None:
    context = build_phase20("config/settings_validation.yaml", validation_scope="full")
    phase20 = context.validation_results["phase20"]

    assert phase20["exceptions"] == []
    assert phase20["validation_scope"] == "full"
    assert phase20["master_data_controls"]["exception_count"] == 0
    assert context.validation_results["phase19"]["exceptions"] == []

    revalidated = validate_phase20(context, scope="full", store=False)
    assert revalidated["exceptions"] == []
    assert revalidated["master_data_controls"]["exception_count"] == 0


def test_phase20_new_anomalies_are_logged_with_detection_metadata(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    context = default_anomaly_dataset_artifacts["context"]
    anomaly_counts = Counter(entry["anomaly_type"] for entry in context.anomaly_log)

    for anomaly_type in [
        "approval_above_authority_limit",
        "unexpected_role_family_approval",
        "inactive_employee_current_assignment",
        "prelaunch_item_in_new_activity",
        "item_status_alignment_conflict",
    ]:
        assert anomaly_counts[anomaly_type] > 0

    for entry in context.anomaly_log:
        if entry["anomaly_type"] in {
            "approval_above_authority_limit",
            "unexpected_role_family_approval",
            "inactive_employee_current_assignment",
            "prelaunch_item_in_new_activity",
            "item_status_alignment_conflict",
        }:
            assert str(entry["description"]).strip()
            assert str(entry["expected_detection_test"]).strip()


def test_phase20_new_audit_queries_return_rows_on_default_build(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(default_anomaly_dataset_artifacts["sqlite_path"])
    assert sqlite_path.exists()

    for sql_path in [*PHASE20_NEW_AUDIT_QUERIES, *PHASE20_RELATED_AUDIT_QUERIES]:
        result = _read_sql_result(sqlite_path, sql_path)
        assert not result.empty, f"Expected rows from {sql_path}"


def test_phase20_default_build_preserves_export_and_balance_contract(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    context = default_anomaly_dataset_artifacts["context"]

    assert Path(default_anomaly_dataset_artifacts["sqlite_path"]).exists()
    assert Path(default_anomaly_dataset_artifacts["support_excel_path"]).exists()
    assert Path(default_anomaly_dataset_artifacts["csv_zip_path"]).exists()

    phase8 = context.validation_results["phase8"]
    assert phase8["gl_balance"]["exception_count"] == 0
    assert float(phase8["trial_balance_difference"]) == 0.0


def test_phase20_docs_reference_new_audit_queries() -> None:
    audit_guide = Path("docs/analytics/audit.md").read_text(encoding="utf-8")
    audit_case = Path("docs/analytics/cases/audit-review-pack-case.md").read_text(encoding="utf-8")
    workforce_case = Path("docs/analytics/cases/master-data-and-workforce-audit-case.md").read_text(encoding="utf-8")
    instructor_guide = Path("docs/teach-with-greenfield/instructor-guide.md").read_text(encoding="utf-8")

    assert "34_current_state_employee_assignment_review.sql" in audit_guide
    assert "35_approval_authority_limit_review.sql" in audit_guide
    assert "36_item_status_alignment_review.sql" in audit_guide
    assert "34_current_state_employee_assignment_review.sql" in audit_case
    assert "35_approval_authority_limit_review.sql" in audit_case
    assert "34_current_state_employee_assignment_review.sql" in workforce_case
    assert "35_approval_authority_limit_review.sql" in workforce_case
    assert "Phase 19 and Phase 20 Classroom Sequence" in instructor_guide
