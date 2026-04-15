from __future__ import annotations

import pandas as pd

from CharlesRiver_dataset.main import build_phase2, build_phase23
from CharlesRiver_dataset.planning import open_work_order_supply_by_item_warehouse_week
from CharlesRiver_dataset.schema import TABLE_COLUMNS, create_empty_tables
from CharlesRiver_dataset.settings import initialize_context, load_settings


def _row(table_name: str, **values: object) -> dict[str, object]:
    row = {column_name: None for column_name in TABLE_COLUMNS[table_name]}
    row.update(values)
    return row


def test_phase23_3_operational_calendar_extends_past_fiscal_year_end() -> None:
    settings = load_settings("config/settings_validation.yaml")
    context = initialize_context(settings)

    assert pd.Timestamp(context.calendar["Date"].max()) > pd.Timestamp(settings.fiscal_year_end)


def test_phase23_3_open_work_order_supply_uses_scheduled_finish_week() -> None:
    settings = load_settings("config/settings_validation.yaml")
    context = initialize_context(settings)
    create_empty_tables(context)

    context.tables["WorkOrder"] = pd.DataFrame(
        [
            _row(
                "WorkOrder",
                WorkOrderID=1,
                WorkOrderNumber="WO-1",
                ItemID=100,
                BOMID=10,
                RoutingID=20,
                WarehouseID=1,
                PlannedQuantity=12.0,
                ReleasedDate="2026-01-05",
                DueDate="2026-01-31",
                Status="Released",
                CostCenterID=1,
                ReleasedByEmployeeID=1,
            )
        ],
        columns=TABLE_COLUMNS["WorkOrder"],
    )
    context.tables["WorkOrderOperation"] = pd.DataFrame(
        [
            _row(
                "WorkOrderOperation",
                WorkOrderOperationID=1,
                WorkOrderID=1,
                RoutingOperationID=1,
                OperationSequence=1,
                WorkCenterID=1,
                PlannedQuantity=12.0,
                PlannedLoadHours=6.0,
                PlannedStartDate="2026-01-10",
                PlannedEndDate="2026-01-15",
                Status="Released",
            )
        ],
        columns=TABLE_COLUMNS["WorkOrderOperation"],
    )
    context.tables["WorkOrderOperationSchedule"] = pd.DataFrame(
        [
            _row(
                "WorkOrderOperationSchedule",
                WorkOrderOperationScheduleID=1,
                WorkOrderOperationID=1,
                WorkCenterID=1,
                ScheduleDate="2026-01-12",
                ScheduledHours=2.0,
            ),
            _row(
                "WorkOrderOperationSchedule",
                WorkOrderOperationScheduleID=2,
                WorkOrderOperationID=1,
                WorkCenterID=1,
                ScheduleDate="2026-01-15",
                ScheduledHours=4.0,
            ),
        ],
        columns=TABLE_COLUMNS["WorkOrderOperationSchedule"],
    )

    supply = open_work_order_supply_by_item_warehouse_week(context)

    assert supply == {("2026-01-12", 100, 1): 12.0}


def test_phase23_3_phase2_and_phase23_clean_builds_stay_green() -> None:
    phase2_context = build_phase2("config/settings_validation.yaml")
    work_center_calendar = phase2_context.tables["WorkCenterCalendar"]

    assert pd.Timestamp(work_center_calendar["CalendarDate"].max()) > pd.Timestamp(
        phase2_context.settings.fiscal_year_end
    )

    phase23_context = build_phase23("config/settings_validation.yaml", validation_scope="full")

    assert phase23_context.validation_results["phase23"]["exceptions"] == []
