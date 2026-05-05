from __future__ import annotations

from collections import Counter
import sqlite3
from pathlib import Path

import pandas as pd

from generator_dataset.main import build_phase21
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.validations import validate_phase21
from generator_dataset.workforce_capacity import DIRECT_MANUFACTURING_TITLES


PHASE21_MANAGERIAL_QUERIES = [
    Path("queries/managerial/36_staffing_coverage_vs_work_center_planned_load.sql"),
    Path("queries/managerial/37_rostered_vs_worked_hours_by_work_center_shift.sql"),
    Path("queries/managerial/38_absence_rate_by_work_location_job_family_month.sql"),
    Path("queries/managerial/39_overtime_approval_coverage_and_concentration.sql"),
    Path("queries/managerial/40_punch_to_pay_bridge_for_hourly_workers.sql"),
    Path("queries/managerial/41_late_arrival_early_departure_by_shift_department.sql"),
]

PHASE21_AUDIT_QUERIES = [
    Path("queries/audit/37_scheduled_without_punch_and_punch_without_schedule_review.sql"),
    Path("queries/audit/38_overtime_without_approval_review.sql"),
    Path("queries/audit/39_absence_with_worked_time_review.sql"),
    Path("queries/audit/40_overlapping_or_incomplete_punch_review.sql"),
    Path("queries/audit/41_roster_after_termination_review.sql"),
]


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_path.read_text(encoding="utf-8"), connection)


def test_phase21_schema_extensions_exist() -> None:
    for table_name in ["EmployeeShiftRoster", "EmployeeAbsence", "TimeClockPunch", "OvertimeApproval"]:
        assert table_name in TABLE_COLUMNS

    assert "EmployeeShiftRosterID" in TABLE_COLUMNS["TimeClockEntry"]
    assert "OvertimeApprovalID" in TABLE_COLUMNS["TimeClockEntry"]
    assert "EmployeeShiftRosterID" in TABLE_COLUMNS["AttendanceException"]


def test_phase21_helper_generates_clean_dataset() -> None:
    context = build_phase21("config/settings_validation.yaml", validation_scope="full")
    phase21 = context.validation_results["phase21"]

    assert phase21["time_clock_controls"]["exception_count"] == 0
    assert phase21["workforce_planning_controls"]["exception_count"] == 0

    rosters = context.tables["EmployeeShiftRoster"]
    absences = context.tables["EmployeeAbsence"]
    punches = context.tables["TimeClockPunch"]
    time_clocks = context.tables["TimeClockEntry"]
    overtime = context.tables["OvertimeApproval"]

    assert not rosters.empty
    assert not punches.empty
    assert time_clocks["EmployeeShiftRosterID"].notna().all()

    overtime_entries = time_clocks[time_clocks["OvertimeHours"].astype(float).gt(0.5)].copy()
    if not overtime_entries.empty:
        approved_share = overtime_entries["OvertimeApprovalID"].notna().mean()
        assert approved_share >= 0.95

    grouped_punches = punches.groupby("TimeClockEntryID").size()
    assert grouped_punches.ge(2).all()
    assert grouped_punches.le(4).all()

    absent_roster_ids = set(
        rosters.loc[rosters["RosterStatus"].eq("Absent"), "EmployeeShiftRosterID"].astype(int).tolist()
    )
    if absent_roster_ids:
        assert time_clocks[
            time_clocks["EmployeeShiftRosterID"].notna()
            & time_clocks["EmployeeShiftRosterID"].astype(int).isin(absent_roster_ids)
        ].empty
        assert punches[
            punches["EmployeeShiftRosterID"].notna()
            & punches["EmployeeShiftRosterID"].astype(int).isin(absent_roster_ids)
        ].empty
        assert not absences.empty

    revalidated = validate_phase21(context, scope="full", store=False)
    assert revalidated["time_clock_controls"]["exception_count"] == 0
    assert revalidated["workforce_planning_controls"]["exception_count"] == 0

    assignments = context.tables["EmployeeShiftAssignment"]
    employees = context.tables["Employee"][["EmployeeID", "JobTitle", "IsActive", "PayClass"]].copy()
    work_centers = context.tables["WorkCenter"][["WorkCenterID", "WorkCenterCode"]].copy()
    direct_assignments = assignments.merge(employees, on="EmployeeID", how="left").merge(work_centers, on="WorkCenterID", how="left")
    direct_assignments = direct_assignments[
        direct_assignments["IsPrimary"].astype(int).eq(1)
        & direct_assignments["IsActive"].astype(int).eq(1)
        & direct_assignments["PayClass"].eq("Hourly")
        & direct_assignments["JobTitle"].isin(DIRECT_MANUFACTURING_TITLES)
        & direct_assignments["WorkCenterCode"].notna()
    ].copy()

    assert not direct_assignments.empty

    total_direct = len(direct_assignments)
    share_by_code = (
        direct_assignments["WorkCenterCode"].value_counts().div(float(total_direct)).to_dict()
    )
    target_share_bands = {
        "ASSEMBLY": (0.40, 0.50),
        "FINISH": (0.22, 0.30),
        "CUT": (0.15, 0.22),
        "PACK": (0.08, 0.12),
        "QA": (0.03, 0.06),
    }
    for work_center_code, (low, high) in target_share_bands.items():
        share = float(share_by_code.get(work_center_code, 0.0))
        assert low <= share <= high


def test_phase21_queries_execute_and_return_expected_rows(
    clean_validation_dataset_artifacts: dict[str, object],
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    clean_sqlite = Path(clean_validation_dataset_artifacts["sqlite_path"])
    default_sqlite = Path(default_anomaly_dataset_artifacts["sqlite_path"])

    for sql_path in PHASE21_MANAGERIAL_QUERIES:
        result = _read_sql_result(clean_sqlite, sql_path)
        assert not result.empty, f"Expected rows from {sql_path} on clean build"

    for sql_path in PHASE21_AUDIT_QUERIES:
        result = _read_sql_result(default_sqlite, sql_path)
        assert not result.empty, f"Expected rows from {sql_path} on default build"


def test_phase21_new_anomalies_are_logged_and_detected(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    context = default_anomaly_dataset_artifacts["context"]
    anomaly_counts = Counter(entry["anomaly_type"] for entry in context.anomaly_log)

    for anomaly_type in [
        "missing_final_punch",
        "punch_without_roster",
        "absence_with_worked_time",
        "overtime_without_approval",
        "roster_after_termination",
        "overlapping_punch_sequence",
    ]:
        assert anomaly_counts[anomaly_type] > 0

    assert context.validation_results["phase8"]["workforce_planning_controls"]["exception_count"] > 0


def test_phase21_docs_and_sidebar_entries_exist() -> None:
    for path in [
        Path("docs/analytics/cases/workforce-coverage-and-attendance-case.md"),
        Path("docs/analytics/cases/attendance-control-audit-case.md"),
    ]:
        assert path.exists(), f"Missing Phase 21 case doc: {path}"

    sidebar_text = Path("sidebars.js").read_text(encoding="utf-8")
    assert "analytics/cases/workforce-coverage-and-attendance-case" in sidebar_text
    assert "analytics/cases/attendance-control-audit-case" in sidebar_text


def test_phase21_workforce_coverage_case_uses_upgraded_walkthrough_shell() -> None:
    workforce_case = Path("docs/analytics/cases/workforce-coverage-and-attendance-case.md").read_text(encoding="utf-8")

    for snippet in (
        "## Before You Start",
        "## Step-by-Step Walkthrough",
        "## Optional Excel Follow-Through",
        "## Wrap-Up Questions",
        "## Next Steps",
        "managerial/36_staffing_coverage_vs_work_center_planned_load.sql",
        "managerial/37_rostered_vs_worked_hours_by_work_center_shift.sql",
        "managerial/38_absence_rate_by_work_location_job_family_month.sql",
        "managerial/39_overtime_approval_coverage_and_concentration.sql",
        "managerial/41_late_arrival_early_departure_by_shift_department.sql",
        "attendance-control-audit-case.md",
        "workforce-cost-and-org-control-case.md",
    ):
        assert snippet in workforce_case

    assert "## Key Data Sources" not in workforce_case
    assert "## Recommended Query Sequence" not in workforce_case
