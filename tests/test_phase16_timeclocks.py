from __future__ import annotations

from collections import Counter

import pandas as pd
import pytest

from generator_dataset.anomalies import inject_anomalies
from generator_dataset.main import build_phase15_2, build_phase16
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.validations import validate_phase8


@pytest.fixture(scope="module")
def phase16_base_context():
    return build_phase16()


@pytest.fixture
def phase16_context(clone_generation_context, phase16_base_context):
    return clone_generation_context(phase16_base_context)


def test_phase15_2_validation_scope_helper_runs_clean() -> None:
    context = build_phase15_2(validation_scope="operational")
    phase15_2 = context.validation_results["phase15_2"]

    assert phase15_2["validation_scope"] == "operational"
    assert phase15_2["exceptions"] == []
    assert phase15_2["gl_balance"]["exception_count"] == 0
    assert phase15_2["capacity_controls"]["exception_count"] == 0


def test_phase16_schema_extensions_exist() -> None:
    for table_name in ["ShiftDefinition", "EmployeeShiftAssignment", "TimeClockEntry", "AttendanceException"]:
        assert table_name in TABLE_COLUMNS

    assert "TimeClockEntryID" in TABLE_COLUMNS["LaborTimeEntry"]


def test_phase16_helper_generates_clean_time_clock_dataset(phase16_context) -> None:
    context = phase16_context
    phase16 = context.validation_results["phase16"]

    assert phase16["exceptions"] == []
    assert phase16["time_clock_controls"]["exception_count"] == 0

    shift_definitions = context.tables["ShiftDefinition"]
    assignments = context.tables["EmployeeShiftAssignment"]
    time_clocks = context.tables["TimeClockEntry"]
    labor_entries = context.tables["LaborTimeEntry"]
    employees = context.tables["Employee"].set_index("EmployeeID")
    work_order_operations = context.tables["WorkOrderOperation"].set_index("WorkOrderOperationID")

    assert len(shift_definitions) == 4
    assert len(assignments) > 0
    assert len(time_clocks) > 0
    assert len(labor_entries) > 0

    assert time_clocks["ClockStatus"].eq("Approved").all()
    assert time_clocks["ClockOutTime"].notna().all()
    assert time_clocks["EmployeeID"].astype(int).map(employees["PayClass"]).eq("Hourly").all()

    direct_time_clocks = time_clocks[time_clocks["WorkOrderOperationID"].notna()].copy()
    assert not direct_time_clocks.empty
    assert (
        direct_time_clocks["WorkOrderOperationID"].astype(int).map(work_order_operations["WorkOrderID"]).astype(int)
        == direct_time_clocks["WorkOrderID"].astype(int)
    ).all()

    direct_labor_entries = labor_entries[labor_entries["LaborType"].eq("Direct Manufacturing")].copy()
    assert not direct_labor_entries.empty
    assert direct_labor_entries["TimeClockEntryID"].notna().all()


def test_phase16_time_clock_anomalies_are_logged_and_detected(phase16_context) -> None:
    context = phase16_context

    inject_anomalies(context)
    results = validate_phase8(context)
    anomaly_counts = Counter(entry["anomaly_type"] for entry in context.anomaly_log)

    for anomaly_type in [
        "missing_clock_out",
        "duplicate_time_clock_day",
        "off_shift_clocking",
        "paid_without_clock",
        "labor_after_operation_close",
    ]:
        assert anomaly_counts[anomaly_type] > 0

    assert results["time_clock_controls"]["exception_count"] > 0


def test_phase16_full_build_respects_anomaly_none_validation_profile(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    context = clean_validation_dataset_artifacts["context"]

    assert context.validation_results["phase16"]["exceptions"] == []
    assert context.validation_results["phase8"]["exceptions"] == []
    assert context.validation_results["phase8"]["row_counts"]["AttendanceException"] == 0
    assert context.tables["AttendanceException"].empty


def test_phase16_full_dataset_clean_validation(full_dataset_artifacts: dict[str, object]) -> None:
    context = full_dataset_artifacts["context"]
    phase16 = context.validation_results["phase16"]
    row_counts = phase16["row_counts"]

    assert phase16["exceptions"] == []
    assert phase16["time_clock_controls"]["exception_count"] == 0
    assert row_counts["ShiftDefinition"] == 4
    assert row_counts["EmployeeShiftAssignment"] > 0
    assert row_counts["TimeClockEntry"] > 0
    assert row_counts["AttendanceException"] >= 0

    time_clocks = context.tables["TimeClockEntry"]
    duplicate_days = time_clocks.groupby(["EmployeeID", "WorkDate"]).size()
    assert duplicate_days.le(1).all()

    span_hours = (
        (
            pd.to_datetime(time_clocks["ClockOutTime"]) - pd.to_datetime(time_clocks["ClockInTime"])
        ).dt.total_seconds() / 3600.0
        - time_clocks["BreakMinutes"].astype(float) / 60.0
    ).round(2)
    recorded_hours = (time_clocks["RegularHours"].astype(float) + time_clocks["OvertimeHours"].astype(float)).round(2)
    assert (span_hours - recorded_hours).abs().le(0.02).all()
