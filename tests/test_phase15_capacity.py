import pandas as pd

from greenfield_dataset.anomalies import inject_anomalies
from greenfield_dataset.main import build_phase2, build_phase15
from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.validations import validate_phase8


def test_phase15_schema_extensions_exist() -> None:
    assert "WorkCenterCalendar" in TABLE_COLUMNS
    assert "WorkOrderOperationSchedule" in TABLE_COLUMNS
    assert "NominalDailyCapacityHours" in TABLE_COLUMNS["WorkCenter"]
    assert "PlannedLoadHours" in TABLE_COLUMNS["WorkOrderOperation"]


def test_phase15_master_data_generates_capacity_calendar() -> None:
    context = build_phase2()

    work_centers = context.tables["WorkCenter"]
    calendars = context.tables["WorkCenterCalendar"]

    assert not work_centers.empty
    assert len(calendars) == len(work_centers) * len(context.calendar)
    assert calendars["ExceptionReason"].isin(
        ["Normal", "Weekend", "Holiday", "Maintenance", "Reduced Capacity"]
    ).all()

    weekend_rows = calendars[calendars["ExceptionReason"].eq("Weekend")]
    holiday_rows = calendars[calendars["ExceptionReason"].eq("Holiday")]
    maintenance_rows = calendars[calendars["ExceptionReason"].eq("Maintenance")]
    reduced_rows = calendars[calendars["ExceptionReason"].eq("Reduced Capacity")]

    assert not weekend_rows.empty
    assert not holiday_rows.empty
    assert not maintenance_rows.empty
    assert not reduced_rows.empty
    assert weekend_rows["AvailableHours"].astype(float).eq(0.0).all()
    assert holiday_rows["AvailableHours"].astype(float).eq(0.0).all()


def test_phase15_helper_generates_clean_capacity_dataset() -> None:
    context = build_phase15()
    phase15 = context.validation_results["phase15"]

    assert phase15["exceptions"] == []
    assert phase15["capacity_controls"]["exception_count"] == 0

    schedules = context.tables["WorkOrderOperationSchedule"]
    operations = context.tables["WorkOrderOperation"]
    calendars = context.tables["WorkCenterCalendar"]

    assert len(schedules) > len(operations)
    assert pd.to_datetime(schedules["ScheduleDate"]).max() <= pd.Timestamp(context.settings.fiscal_year_end)

    load_by_operation = schedules.groupby("WorkOrderOperationID")["ScheduledHours"].sum().round(2)
    planned_load = operations.set_index("WorkOrderOperationID")["PlannedLoadHours"].astype(float).round(2)
    assert (
        load_by_operation.astype(float).round(2)
        == load_by_operation.index.to_series().map(planned_load).astype(float).round(2)
    ).all()

    scheduled_by_day = schedules.groupby(["WorkCenterID", "ScheduleDate"])["ScheduledHours"].sum().round(2)
    available_by_day = calendars.set_index(["WorkCenterID", "CalendarDate"])["AvailableHours"].astype(float).round(2)
    assert (
        scheduled_by_day.astype(float).round(2)
        <= scheduled_by_day.index.to_series().map(available_by_day).astype(float).round(2)
    ).all()

    planned_end = pd.to_datetime(operations["PlannedEndDate"])
    actual_end = pd.to_datetime(operations["ActualEndDate"], errors="coerce")
    assert int((actual_end.notna() & actual_end.gt(planned_end)).sum()) > 0

    work_orders = context.tables["WorkOrder"].copy()
    work_orders["DueDateTS"] = pd.to_datetime(work_orders["DueDate"])
    work_orders["CompletedDateTS"] = pd.to_datetime(work_orders["CompletedDate"], errors="coerce")
    assert int(
        (
            work_orders["CompletedDateTS"].notna()
            & work_orders["CompletedDateTS"].gt(work_orders["DueDateTS"])
        ).sum()
    ) > 0


def test_phase15_capacity_anomalies_are_logged_and_detected() -> None:
    context = build_phase15()

    inject_anomalies(context)
    results = validate_phase8(context)
    anomaly_types = {entry["anomaly_type"] for entry in context.anomaly_log}

    assert "scheduled_on_nonworking_day" in anomaly_types
    assert "overbooked_work_center_day" in anomaly_types
    assert "completion_before_operation_end" in anomaly_types
    assert results["capacity_controls"]["exception_count"] > 0


def test_phase15_full_dataset_clean_validation(full_dataset_artifacts: dict[str, object]) -> None:
    context = full_dataset_artifacts["context"]
    phase15 = context.validation_results["phase15"]
    row_counts = phase15["row_counts"]

    assert phase15["exceptions"] == []
    assert phase15["gl_balance"]["exception_count"] == 0
    assert phase15["trial_balance_difference"] == 0
    assert phase15["account_rollforward"]["exception_count"] == 0
    assert phase15["o2c_controls"]["exception_count"] == 0
    assert phase15["p2p_controls"]["exception_count"] == 0
    assert phase15["journal_controls"]["exception_count"] == 0
    assert phase15["manufacturing_controls"]["exception_count"] == 0
    assert phase15["payroll_controls"]["exception_count"] == 0
    assert phase15["routing_controls"]["exception_count"] == 0
    assert phase15["capacity_controls"]["exception_count"] == 0

    assert row_counts["WorkCenterCalendar"] > row_counts["WorkCenter"]
    assert row_counts["WorkOrderOperationSchedule"] > row_counts["WorkOrderOperation"]
