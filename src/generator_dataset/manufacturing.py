from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
import logging
from typing import Any

import numpy as np
import pandas as pd

from generator_dataset.master_data import (
    ITEM_GROUP_CONFIG,
    approver_employee_id,
    current_role_employee_id,
    employee_ids_for_cost_center_as_of,
    eligible_item_mask,
)
from generator_dataset.o2c import opening_inventory_map, sales_order_line_shipped_quantities, shadow_inventory_state
from generator_dataset.planning import (
    cancel_recommendations,
    expire_recommendations,
    manufacture_recommendations_for_month,
    primary_warehouse_rank,
    weekly_forecast_map,
    update_recommendation_conversion,
    week_end,
    week_start,
)
from generator_dataset.payroll import (
    labor_time_direct_cost_by_work_order,
    next_business_day,
    payroll_period_lookup,
    work_order_overhead_cost_map,
)
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.settings import GenerationContext
from generator_dataset.utils import format_doc_number, money, next_id, qty
from generator_dataset.workforce_capacity import (
    DIRECT_MANUFACTURING_TITLES,
    DIRECT_WORK_CENTER_CODES,
    STANDARD_MANUFACTURING_SHIFT_HOURS,
    allocate_hours_by_work_center,
    blended_capacity_shares,
    direct_work_center_assignments,
    work_center_counts_from_codes,
    work_center_shares_from_counts,
)


LOGGER = logging.getLogger(__name__)


MANUFACTURED_ITEM_SHARE_MIN = 0.35
MANUFACTURED_ITEM_SHARE_MAX = 0.45

BOM_LINE_COUNT_RANGE = {
    "Furniture": (3, 5),
    "Lighting": (2, 4),
    "Textiles": (2, 4),
    "Accessories": (2, 3),
}

RAW_COMPONENT_QUANTITY_RANGE = {
    "Furniture": (1.10, 3.60),
    "Lighting": (0.80, 2.25),
    "Textiles": (1.20, 3.25),
    "Accessories": (0.60, 1.85),
}

PACKAGING_QUANTITY_RANGE = {
    "Furniture": (1.00, 1.30),
    "Lighting": (1.00, 1.20),
    "Textiles": (1.00, 1.40),
    "Accessories": (1.00, 1.15),
}

SCRAP_FACTOR_RANGE = {
    "Raw Materials": (0.00, 0.07),
    "Packaging": (0.00, 0.02),
}

FINISHED_GOODS_BUFFER_RANGE = {
    "Furniture": (8.0, 20.0),
    "Lighting": (12.0, 28.0),
    "Textiles": (10.0, 24.0),
    "Accessories": (6.0, 16.0),
}

WORK_ORDER_SAME_MONTH_COMPLETION_PROBABILITY = 0.78
WORK_ORDER_PARTIAL_COMPLETION_RANGE = (0.45, 0.82)
ISSUE_EVENT_COUNT_PROBABILITIES = ((1, 0.68), (2, 0.32))
COMPLETION_EVENT_COUNT_PROBABILITIES = ((1, 0.72), (2, 0.28))
ISSUE_FACTOR_RANGE = (0.98, 1.04)
MATERIAL_REQUISITION_BUFFER_FACTOR = (1.03, 1.08)
WORK_CENTER_DEFINITIONS = (
    {
        "WorkCenterCode": "CUT",
        "WorkCenterName": "Cutting Work Center",
        "Department": "Manufacturing",
        "ManagerTitles": ("Production Supervisor", "Production Manager"),
    },
    {
        "WorkCenterCode": "ASSEMBLY",
        "WorkCenterName": "Assembly Work Center",
        "Department": "Manufacturing",
        "ManagerTitles": ("Production Supervisor", "Production Manager"),
    },
    {
        "WorkCenterCode": "FINISH",
        "WorkCenterName": "Finishing and Test Work Center",
        "Department": "Manufacturing",
        "ManagerTitles": ("Production Supervisor", "Production Manager"),
    },
    {
        "WorkCenterCode": "PACK",
        "WorkCenterName": "Packing Work Center",
        "Department": "Manufacturing",
        "ManagerTitles": ("Production Planner", "Production Supervisor", "Production Manager"),
    },
    {
        "WorkCenterCode": "QA",
        "WorkCenterName": "Quality Assurance Work Center",
        "Department": "Manufacturing",
        "ManagerTitles": ("Production Manager", "Quality Technician"),
    },
)

WORK_CENTER_FALLBACK_NOMINAL_HOURS = {
    "CUT": 24.0,
    "ASSEMBLY": 48.0,
    "FINISH": 28.0,
    "PACK": 12.0,
    "QA": 8.0,
}

REDUCED_CAPACITY_FACTOR_RANGE = {
    "CUT": (0.78, 0.90),
    "ASSEMBLY": (0.72, 0.86),
    "FINISH": (0.70, 0.84),
    "PACK": (0.82, 0.92),
    "QA": (0.80, 0.90),
}

WORK_CENTER_BOTTLENECK_CODES = {"ASSEMBLY", "FINISH", "PACK"}
CAPACITY_EXCEPTION_REASONS = {"Normal", "Weekend", "Holiday", "Maintenance", "Reduced Capacity"}

ROUTING_PATTERN_BY_GROUP = {
    "Furniture": [
        ("CUT", "Cut Components"),
        ("ASSEMBLY", "Assemble Units"),
        ("FINISH", "Finish and Inspect"),
        ("PACK", "Pack Finished Goods"),
    ],
    "Lighting": [
        ("ASSEMBLY", "Assemble Lighting Units"),
        ("FINISH", "Test and Finish"),
        ("PACK", "Pack Finished Goods"),
    ],
    "Textiles": [
        ("CUT", "Cut Fabric"),
        ("ASSEMBLY", "Sew and Assemble"),
        ("PACK", "Pack Finished Goods"),
    ],
    "Accessories": [
        ("ASSEMBLY", "Assemble Units"),
        ("PACK", "Pack Finished Goods"),
    ],
}

OPERATION_LABOR_WEIGHT = {
    "CUT": 0.20,
    "ASSEMBLY": 0.42,
    "FINISH": 0.25,
    "PACK": 0.09,
    "QA": 0.04,
}

OPERATION_SETUP_HOURS_RANGE = {
    "CUT": (0.30, 0.70),
    "ASSEMBLY": (0.25, 0.55),
    "FINISH": (0.20, 0.45),
    "PACK": (0.08, 0.20),
    "QA": (0.10, 0.22),
}

OPERATION_QUEUE_DAY_OPTIONS = {
    "CUT": (0, 1),
    "ASSEMBLY": (0, 1),
    "FINISH": (1, 2),
    "PACK": (0, 1),
    "QA": (0, 1),
}

LABOR_BEARING_OPERATION_CODES = {"ASSEMBLY", "FINISH", "QA", "CUT"}
WORK_ORDER_COMPONENT_SHORTFALL_PREFIX = "WO-COMPONENT-SHORTFALL"


def append_rows(context: GenerationContext, table_name: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    new_rows = pd.DataFrame(rows, columns=TABLE_COLUMNS[table_name])
    context.tables[table_name] = pd.concat([context.tables[table_name], new_rows], ignore_index=True)
    invalidate_manufacturing_caches(context, table_name)


def drop_context_attributes(context: GenerationContext, attribute_names: list[str]) -> None:
    for attribute_name in attribute_names:
        if hasattr(context, attribute_name):
            delattr(context, attribute_name)


def invalidate_manufacturing_caches(context: GenerationContext, table_name: str) -> None:
    cache_map = {
        "BillOfMaterialLine": ["_bom_lines_by_bom_cache"],
        "RoutingOperation": ["_routing_operations_by_routing_cache"],
        "WorkCenterCalendar": [
            "_work_center_calendar_lookup",
            "_work_center_schedule_usage",
            "_work_center_working_dates_cache",
            "_work_center_working_date_index_cache",
        ],
        "WorkOrderOperation": [
            "_work_order_operation_index_map",
            "_work_order_schedule_bounds",
            "_operation_target_windows",
            "_scheduled_work_order_ids_cache",
            "_final_work_order_activity_dates_cache",
        ],
        "WorkOrderOperationSchedule": [
            "_work_center_schedule_usage",
            "_work_order_operation_schedule_index_map",
            "_work_order_schedule_bounds",
            "_scheduled_work_order_ids_cache",
        ],
        "ProductionCompletion": [
            "_work_order_completed_quantity_map_cache",
            "_work_order_completed_quantity_state",
            "_work_order_standard_material_cost_map_cache",
            "_work_order_standard_conversion_cost_map_cache",
            "_work_order_standard_direct_labor_cost_map_cache",
            "_work_order_standard_overhead_cost_map_cache",
            "_final_work_order_activity_dates_cache",
        ],
        "ProductionCompletionLine": [
            "_work_order_completed_quantity_map_cache",
            "_work_order_completed_quantity_state",
            "_work_order_standard_material_cost_map_cache",
            "_work_order_standard_conversion_cost_map_cache",
            "_work_order_standard_direct_labor_cost_map_cache",
            "_work_order_standard_overhead_cost_map_cache",
        ],
        "MaterialIssue": [
            "_work_order_material_issue_cost_map_cache",
            "_work_order_material_issue_cost_state",
            "_final_work_order_activity_dates_cache",
        ],
        "MaterialIssueLine": [
            "_work_order_material_issue_cost_map_cache",
            "_work_order_material_issue_cost_state",
        ],
    }
    drop_context_attributes(context, cache_map.get(table_name, []))


def month_bounds(year: int, month: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(year=year, month=month, day=1)
    end = start + pd.offsets.MonthEnd(1)
    return start, end


def capacity_rng(context: GenerationContext, *parts: object) -> np.random.Generator:
    seed = context.settings.random_seed
    for part in parts:
        seed = (seed * 31 + sum(ord(char) for char in str(part))) % (2**32 - 1)
    return np.random.default_rng(seed)


def nth_weekday_of_month(year: int, month: int, weekday: int, occurrence: int) -> pd.Timestamp:
    candidate = pd.Timestamp(year=year, month=month, day=1)
    while candidate.weekday() != weekday:
        candidate = candidate + pd.Timedelta(days=1)
    return candidate + pd.Timedelta(days=7 * max(occurrence - 1, 0))


def last_weekday_of_month(year: int, month: int, weekday: int) -> pd.Timestamp:
    candidate = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(1)
    while candidate.weekday() != weekday:
        candidate = candidate - pd.Timedelta(days=1)
    return candidate


def holiday_dates_for_year(year: int) -> set[str]:
    return {
        pd.Timestamp(year=year, month=1, day=1).strftime("%Y-%m-%d"),
        last_weekday_of_month(year, 5, 0).strftime("%Y-%m-%d"),
        pd.Timestamp(year=year, month=7, day=4).strftime("%Y-%m-%d"),
        nth_weekday_of_month(year, 9, 0, 1).strftime("%Y-%m-%d"),
        nth_weekday_of_month(year, 11, 3, 4).strftime("%Y-%m-%d"),
        pd.Timestamp(year=year, month=12, day=25).strftime("%Y-%m-%d"),
    }


def holiday_dates_for_context(context: GenerationContext) -> set[str]:
    years = sorted(pd.to_datetime(context.calendar["Date"]).dt.year.unique().tolist())
    holidays: set[str] = set()
    for year in years:
        holidays.update(holiday_dates_for_year(int(year)))
    return holidays


def work_center_calendar_lookup(context: GenerationContext) -> dict[tuple[int, str], dict[str, Any]]:
    cached = getattr(context, "_work_center_calendar_lookup", None)
    if cached is not None:
        return cached

    work_center_calendar = context.tables["WorkCenterCalendar"]
    if work_center_calendar.empty:
        cached = {}
    else:
        cached = {
            (int(row.WorkCenterID), str(row.CalendarDate)): {
                "WorkCenterCalendarID": int(row.WorkCenterCalendarID),
                "IsWorkingDay": int(row.IsWorkingDay),
                "AvailableHours": float(row.AvailableHours),
                "ExceptionReason": str(row.ExceptionReason),
            }
            for row in work_center_calendar.itertuples(index=False)
        }
    setattr(context, "_work_center_calendar_lookup", cached)
    return cached


def schedule_usage_map(context: GenerationContext) -> dict[tuple[int, str], float]:
    cached = getattr(context, "_work_center_schedule_usage", None)
    if cached is not None:
        return cached

    schedules = context.tables["WorkOrderOperationSchedule"]
    if schedules.empty:
        usage: dict[tuple[int, str], float] = {}
    else:
        grouped = schedules.groupby(["WorkCenterID", "ScheduleDate"])["ScheduledHours"].sum().round(2)
        usage = {
            (int(work_center_id), str(schedule_date)): float(hours)
            for (work_center_id, schedule_date), hours in grouped.items()
        }
    setattr(context, "_work_center_schedule_usage", usage)
    return usage


def work_center_working_dates(context: GenerationContext) -> dict[int, tuple[pd.Timestamp, ...]]:
    cached = getattr(context, "_work_center_working_dates_cache", None)
    if cached is not None:
        return cached

    calendar = context.tables["WorkCenterCalendar"]
    if calendar.empty:
        cached = {}
    else:
        working = calendar[calendar["AvailableHours"].astype(float).gt(0)].copy()
        working["CalendarDateTS"] = pd.to_datetime(working["CalendarDate"], errors="coerce").dt.normalize()
        grouped = working.groupby("WorkCenterID")["CalendarDateTS"].apply(
            lambda values: tuple(sorted(timestamp for timestamp in values.tolist() if pd.notna(timestamp)))
        )
        cached = {
            int(work_center_id): working_dates
            for work_center_id, working_dates in grouped.items()
        }

    setattr(context, "_work_center_working_dates_cache", cached)
    return cached


def work_center_working_date_index(context: GenerationContext) -> dict[int, dict[str, int]]:
    cached = getattr(context, "_work_center_working_date_index_cache", None)
    if cached is not None:
        return cached

    cached = {
        int(work_center_id): {
            pd.Timestamp(work_date).strftime("%Y-%m-%d"): int(index)
            for index, work_date in enumerate(working_dates)
        }
        for work_center_id, working_dates in work_center_working_dates(context).items()
    }
    setattr(context, "_work_center_working_date_index_cache", cached)
    return cached


def operational_calendar_end(context: GenerationContext) -> pd.Timestamp:
    cached = getattr(context, "_operational_calendar_end_cache", None)
    if cached is not None:
        return pd.Timestamp(cached)

    if context.calendar.empty:
        cached = pd.Timestamp(context.settings.fiscal_year_end).normalize()
    else:
        cached = pd.to_datetime(context.calendar["Date"], errors="coerce").max().normalize()
    setattr(context, "_operational_calendar_end_cache", cached)
    return pd.Timestamp(cached)


def next_schedulable_day(context: GenerationContext, work_center_id: int, candidate_date: pd.Timestamp) -> pd.Timestamp:
    working_dates = work_center_working_dates(context).get(int(work_center_id), ())
    current = pd.Timestamp(candidate_date).normalize()
    end_date = operational_calendar_end(context)
    if working_dates:
        working_index = bisect_left(working_dates, current)
        if working_index < len(working_dates):
            return pd.Timestamp(working_dates[working_index])
    return end_date


def previous_schedulable_day(
    context: GenerationContext,
    work_center_id: int,
    candidate_date: pd.Timestamp,
) -> pd.Timestamp | None:
    working_dates = work_center_working_dates(context).get(int(work_center_id), ())
    current = pd.Timestamp(candidate_date).normalize()
    if not working_dates:
        return None

    working_index = bisect_left(working_dates, current)
    if working_index < len(working_dates) and pd.Timestamp(working_dates[working_index]) == current:
        return pd.Timestamp(working_dates[working_index])
    if working_index <= 0:
        return None
    return pd.Timestamp(working_dates[working_index - 1])


def add_schedulable_days(
    context: GenerationContext,
    work_center_id: int,
    candidate_date: pd.Timestamp,
    business_days: int,
) -> pd.Timestamp:
    current = next_schedulable_day(context, int(work_center_id), pd.Timestamp(candidate_date))
    remaining_days = int(max(business_days, 0))
    while remaining_days > 0:
        current = next_schedulable_day(context, int(work_center_id), current + pd.Timedelta(days=1))
        remaining_days -= 1
    return current


def random_date_between(rng: np.random.Generator, start: pd.Timestamp, end: pd.Timestamp) -> pd.Timestamp:
    if end < start:
        end = start
    days = int((end - start).days)
    return start + pd.Timedelta(days=int(rng.integers(0, days + 1)))


def cost_center_id(context: GenerationContext, cost_center_name: str) -> int:
    cost_centers = context.tables["CostCenter"]
    matches = cost_centers.loc[cost_centers["CostCenterName"].eq(cost_center_name), "CostCenterID"]
    if matches.empty:
        raise ValueError(f"{cost_center_name} cost center is required for manufacturing.")
    return int(matches.iloc[0])


def employee_ids_for_cost_center(
    context: GenerationContext,
    cost_center_name: str,
    event_date: pd.Timestamp | str | None = None,
) -> list[int]:
    return employee_ids_for_cost_center_as_of(context, cost_center_name, event_date)


def approver_id(
    context: GenerationContext,
    minimum_amount: float = 0.0,
    event_date: pd.Timestamp | str | None = None,
) -> int:
    return approver_employee_id(
        context,
        event_date,
        preferred_titles=["Production Manager", "Chief Financial Officer", "Controller"],
        minimum_amount=minimum_amount,
        fallback_cost_center_name="Manufacturing",
    )


def warehouse_ids(context: GenerationContext) -> list[int]:
    warehouse_table = context.tables["Warehouse"]
    if warehouse_table.empty:
        raise ValueError("Generate warehouses before manufacturing.")
    return sorted(warehouse_table["WarehouseID"].astype(int).tolist())


def choose_count(rng: np.random.Generator, options: tuple[tuple[int, float], ...]) -> int:
    values = np.array([value for value, _ in options], dtype=int)
    probabilities = np.array([probability for _, probability in options], dtype=float)
    probabilities = probabilities / probabilities.sum()
    return int(rng.choice(values, p=probabilities))


def manufactured_items(context: GenerationContext, event_date: pd.Timestamp | str | None = None) -> pd.DataFrame:
    items = context.tables["Item"]
    rows = items[
        items["SupplyMode"].eq("Manufactured")
        & items["RevenueAccountID"].notna()
        & eligible_item_mask(items, event_date)
    ].copy()
    return rows.sort_values("ItemID").reset_index(drop=True)


def bom_lookup(context: GenerationContext) -> dict[int, dict[str, Any]]:
    if context.tables["BillOfMaterial"].empty:
        return {}
    return context.tables["BillOfMaterial"].set_index("ParentItemID").to_dict("index")


def bom_lines_by_bom(context: GenerationContext) -> dict[int, pd.DataFrame]:
    bom_lines = context.tables["BillOfMaterialLine"]
    if bom_lines.empty:
        return {}
    cached = getattr(context, "_bom_lines_by_bom_cache", None)
    if cached is not None:
        return cached
    cached = {
        int(bom_id): rows.sort_values("LineNumber").reset_index(drop=True)
        for bom_id, rows in bom_lines.groupby("BOMID")
    }
    setattr(context, "_bom_lines_by_bom_cache", cached)
    return cached


def active_routing_by_item(context: GenerationContext) -> dict[int, dict[str, Any]]:
    routings = context.tables["Routing"]
    if routings.empty:
        return {}
    active = routings[routings["Status"].eq("Active")].copy()
    if active.empty:
        return {}
    active = active.sort_values(["ParentItemID", "RoutingID"]).drop_duplicates("ParentItemID", keep="first")
    return active.set_index("ParentItemID").to_dict("index")


def routing_operations_by_routing(context: GenerationContext) -> dict[int, pd.DataFrame]:
    operations = context.tables["RoutingOperation"]
    if operations.empty:
        return {}
    cached = getattr(context, "_routing_operations_by_routing_cache", None)
    if cached is not None:
        return cached
    cached = {
        int(routing_id): rows.sort_values("OperationSequence").reset_index(drop=True)
        for routing_id, rows in operations.groupby("RoutingID")
    }
    setattr(context, "_routing_operations_by_routing_cache", cached)
    return cached


def work_order_operation_index_map(context: GenerationContext) -> dict[int, list[int]]:
    cached = getattr(context, "_work_order_operation_index_map", None)
    if cached is not None:
        return cached

    operations = context.tables["WorkOrderOperation"]
    if operations.empty:
        cached = {}
    else:
        ordered = operations[["WorkOrderID", "OperationSequence"]].copy()
        ordered["__row_index"] = ordered.index
        ordered = ordered.sort_values(["WorkOrderID", "OperationSequence", "__row_index"])
        grouped = ordered.groupby("WorkOrderID")["__row_index"].apply(list)
        cached = {int(work_order_id): [int(index) for index in indexes] for work_order_id, indexes in grouped.items()}

    setattr(context, "_work_order_operation_index_map", cached)
    return cached


def work_order_operations_by_work_order(context: GenerationContext) -> dict[int, pd.DataFrame]:
    operations = context.tables["WorkOrderOperation"]
    if operations.empty:
        return {}
    return {
        int(work_order_id): operations.loc[indexes].copy().reset_index(drop=True)
        for work_order_id, indexes in work_order_operation_index_map(context).items()
    }


def work_order_operations_for_work_order(context: GenerationContext, work_order_id: int) -> pd.DataFrame:
    indexes = work_order_operation_index_map(context).get(int(work_order_id), [])
    if not indexes:
        return context.tables["WorkOrderOperation"].head(0).copy()
    return context.tables["WorkOrderOperation"].loc[indexes].copy()


def work_center_id_by_code(context: GenerationContext) -> dict[str, int]:
    work_centers = context.tables["WorkCenter"]
    if work_centers.empty:
        return {}
    return {
        str(row.WorkCenterCode): int(row.WorkCenterID)
        for row in work_centers.itertuples(index=False)
    }


def manager_for_titles(context: GenerationContext, titles: tuple[str, ...]) -> int:
    for title in titles:
        employee_id = current_role_employee_id(context, title)
        if employee_id is not None:
            return int(employee_id)
    manufacturing_ids = employee_ids_for_cost_center(context, "Manufacturing")
    if manufacturing_ids:
        return int(manufacturing_ids[0])
    return int(context.tables["Employee"].sort_values("EmployeeID").iloc[0]["EmployeeID"])


def active_direct_worker_rows(context: GenerationContext) -> pd.DataFrame:
    employees = context.tables["Employee"]
    if employees.empty:
        return employees.head(0).copy()
    return employees[
        employees["IsActive"].astype(int).eq(1)
        & employees["PayClass"].eq("Hourly")
        & employees["JobTitle"].isin(DIRECT_MANUFACTURING_TITLES)
    ].copy().sort_values("EmployeeID").reset_index(drop=True)


def provisional_direct_assignment_counts(context: GenerationContext) -> dict[str, int]:
    active_direct_workers = active_direct_worker_rows(context)
    if active_direct_workers.empty:
        return {work_center_code: 0 for work_center_code in DIRECT_WORK_CENTER_CODES}
    assignments = direct_work_center_assignments([
        (int(row.EmployeeID), str(row.JobTitle))
        for row in active_direct_workers.itertuples(index=False)
    ])
    return work_center_counts_from_codes(list(assignments.values()))


def active_primary_direct_assignment_counts(context: GenerationContext) -> dict[str, int]:
    assignments = context.tables["EmployeeShiftAssignment"]
    work_centers = context.tables["WorkCenter"]
    active_direct_workers = active_direct_worker_rows(context)
    if assignments.empty or work_centers.empty or active_direct_workers.empty:
        return provisional_direct_assignment_counts(context)

    work_center_code_by_id = {
        int(row.WorkCenterID): str(row.WorkCenterCode)
        for row in work_centers.itertuples(index=False)
    }
    assignment_rows = assignments[
        assignments["IsPrimary"].astype(int).eq(1)
        & assignments["EmployeeID"].astype(int).isin(active_direct_workers["EmployeeID"].astype(int))
        & assignments["WorkCenterID"].notna()
    ].copy()
    if assignment_rows.empty:
        return provisional_direct_assignment_counts(context)

    assignment_rows = assignment_rows.sort_values(["EmployeeID", "EmployeeShiftAssignmentID"])
    assignment_rows = assignment_rows.drop_duplicates("EmployeeID", keep="first")
    assigned_codes = {
        int(row.EmployeeID): work_center_code_by_id.get(int(row.WorkCenterID))
        for row in assignment_rows.itertuples(index=False)
        if int(row.WorkCenterID) in work_center_code_by_id
    }

    provisional_assignments = direct_work_center_assignments([
        (int(row.EmployeeID), str(row.JobTitle))
        for row in active_direct_workers.itertuples(index=False)
    ])
    for row in active_direct_workers.itertuples(index=False):
        employee_id = int(row.EmployeeID)
        assigned_codes.setdefault(employee_id, provisional_assignments.get(employee_id))

    return work_center_counts_from_codes([
        work_center_code
        for work_center_code in assigned_codes.values()
        if work_center_code is not None
    ])


def work_center_nominal_capacity_hours_by_code(context: GenerationContext) -> dict[str, float]:
    assignment_counts = active_primary_direct_assignment_counts(context)
    total_direct_workers = sum(assignment_counts.values())
    if total_direct_workers <= 0:
        return {
            work_center_code: float(WORK_CENTER_FALLBACK_NOMINAL_HOURS.get(work_center_code, 0.0))
            for work_center_code in DIRECT_WORK_CENTER_CODES
        }

    total_daily_capacity = float(total_direct_workers) * STANDARD_MANUFACTURING_SHIFT_HOURS
    capacity_shares = blended_capacity_shares(assignment_counts)
    return allocate_hours_by_work_center(total_daily_capacity, capacity_shares)


def sync_work_center_capacity_from_assignments(
    context: GenerationContext,
    *,
    regenerate_calendar: bool = False,
) -> None:
    work_centers = context.tables["WorkCenter"]
    if work_centers.empty:
        return

    nominal_hours_by_code = work_center_nominal_capacity_hours_by_code(context)
    updated = work_centers.copy()
    for work_center_code, nominal_hours in nominal_hours_by_code.items():
        mask = updated["WorkCenterCode"].eq(str(work_center_code))
        updated.loc[mask, "NominalDailyCapacityHours"] = money(float(nominal_hours))
    context.tables["WorkCenter"] = updated[TABLE_COLUMNS["WorkCenter"]]

    if regenerate_calendar:
        context.tables["WorkCenterCalendar"] = context.tables["WorkCenterCalendar"].head(0).copy()
        reset_capacity_caches(context)
        generate_work_center_calendars(context)


def routing_pattern_for_item(context: GenerationContext, item_group: str, item_id: int) -> list[tuple[str, str]]:
    pattern = list(ROUTING_PATTERN_BY_GROUP.get(str(item_group), ROUTING_PATTERN_BY_GROUP["Accessories"]))
    if str(item_group) == "Lighting" and (context.settings.random_seed + int(item_id)) % 4 == 0:
        pattern.insert(len(pattern) - 1, ("QA", "Quality Check"))
    return pattern


def normalized_operation_run_hours(
    item_standard_labor_hours: float,
    operation_codes: list[str],
) -> list[float]:
    weights = [float(OPERATION_LABOR_WEIGHT.get(code, 0.10)) for code in operation_codes]
    total_weight = sum(weights) or 1.0
    allocated = 0.0
    run_hours: list[float] = []
    for index, weight in enumerate(weights, start=1):
        if index == len(weights):
            value = money(max(float(item_standard_labor_hours) - allocated, 0.0))
        else:
            value = money(float(item_standard_labor_hours) * weight / total_weight)
            allocated = money(allocated + value)
        run_hours.append(value)
    return run_hours


def sequential_operation_windows(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    operation_count: int,
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    if operation_count <= 0:
        return []

    start = pd.Timestamp(start_date)
    finish = pd.Timestamp(end_date)
    if finish < start:
        finish = start
    total_days = max(int((finish - start).days), 0)
    breakpoints = [int(round(total_days * index / operation_count)) for index in range(operation_count + 1)]
    windows: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for index in range(operation_count):
        window_start = start + pd.Timedelta(days=breakpoints[index])
        window_end = start + pd.Timedelta(days=breakpoints[index + 1])
        if window_end < window_start:
            window_end = window_start
        windows.append((window_start, window_end))
    return windows


def manufactured_item_group_share(context: GenerationContext) -> float:
    items = context.tables["Item"]
    sellable = items[items["RevenueAccountID"].notna() & items["ListPrice"].notna()]
    if sellable.empty:
        return 0.0
    manufactured = sellable[sellable["SupplyMode"].eq("Manufactured")]
    return round(len(manufactured) / len(sellable), 4)


def generate_boms(context: GenerationContext) -> None:
    if not context.tables["BillOfMaterial"].empty or not context.tables["BillOfMaterialLine"].empty:
        raise ValueError("BOM master data has already been generated.")

    items = context.tables["Item"].copy()
    raw_materials = items[items["ItemGroup"].eq("Raw Materials") & items["IsActive"].eq(1)].copy()
    packaging = items[items["ItemGroup"].eq("Packaging") & items["IsActive"].eq(1)].copy()
    if raw_materials.empty or packaging.empty:
        raise ValueError("Raw materials and packaging items are required before generating BOMs.")

    manufactured = manufactured_items(context)
    bom_rows: list[dict[str, Any]] = []
    bom_line_rows: list[dict[str, Any]] = []

    items = items.set_index("ItemID")
    for item in manufactured.itertuples(index=False):
        rng = np.random.default_rng(context.settings.random_seed + int(item.ItemID) * 101)
        bom_id = next_id(context, "BillOfMaterial")
        bom_rows.append({
            "BOMID": bom_id,
            "ParentItemID": int(item.ItemID),
            "VersionNumber": 1,
            "EffectiveStartDate": context.settings.fiscal_year_start,
            "EffectiveEndDate": None,
            "Status": "Active",
            "StandardBatchQuantity": 1.0,
        })

        min_lines, max_lines = BOM_LINE_COUNT_RANGE.get(str(item.ItemGroup), (2, 4))
        line_target = int(rng.integers(min_lines, max_lines + 1))
        packaging_item = packaging.iloc[int(rng.integers(0, len(packaging)))]
        raw_component_target = max(1, line_target - 1)
        raw_component_indexes = rng.choice(
            raw_materials.index.to_numpy(),
            size=min(raw_component_target, len(raw_materials)),
            replace=False,
        )
        component_rows = [raw_materials.loc[int(index)] for index in np.atleast_1d(raw_component_indexes)]
        component_rows.append(packaging_item)

        material_cost = 0.0
        for line_number, component in enumerate(component_rows, start=1):
            component_group = str(component["ItemGroup"])
            if component_group == "Packaging":
                qty_low, qty_high = PACKAGING_QUANTITY_RANGE[str(item.ItemGroup)]
            else:
                qty_low, qty_high = RAW_COMPONENT_QUANTITY_RANGE[str(item.ItemGroup)]
            quantity_per_unit = qty(rng.uniform(qty_low, qty_high))
            scrap_low, scrap_high = SCRAP_FACTOR_RANGE[component_group]
            scrap_factor = qty(rng.uniform(scrap_low, scrap_high), places="0.0001")
            material_cost += float(component["StandardCost"]) * quantity_per_unit * (1 + scrap_factor)
            bom_line_rows.append({
                "BOMLineID": next_id(context, "BillOfMaterialLine"),
                "BOMID": bom_id,
                "ComponentItemID": int(component["ItemID"]),
                "LineNumber": line_number,
                "QuantityPerUnit": quantity_per_unit,
                "ScrapFactorPct": scrap_factor,
            })

        new_standard_cost = money(material_cost + float(item.StandardConversionCost))
        prior_standard_cost = max(float(item.StandardCost), 0.01)
        markup_ratio = max(float(item.ListPrice) / prior_standard_cost, 1.10)
        items.loc[int(item.ItemID), "StandardCost"] = new_standard_cost
        items.loc[int(item.ItemID), "ListPrice"] = money(new_standard_cost * markup_ratio)

    context.tables["Item"] = items.reset_index()[TABLE_COLUMNS["Item"]]
    append_rows(context, "BillOfMaterial", bom_rows)
    append_rows(context, "BillOfMaterialLine", bom_line_rows)


def generate_work_centers_and_routings(context: GenerationContext) -> None:
    if (
        not context.tables["WorkCenter"].empty
        or not context.tables["Routing"].empty
        or not context.tables["RoutingOperation"].empty
    ):
        return

    manufactured = manufactured_items(context)
    if manufactured.empty:
        return

    warehouses = warehouse_ids(context)
    work_center_rows: list[dict[str, Any]] = []
    for index, definition in enumerate(WORK_CENTER_DEFINITIONS):
        work_center_code = str(definition["WorkCenterCode"])
        work_center_rows.append({
            "WorkCenterID": next_id(context, "WorkCenter"),
            "WorkCenterCode": work_center_code,
            "WorkCenterName": definition["WorkCenterName"],
            "Department": definition["Department"],
            "WarehouseID": int(warehouses[index % len(warehouses)]),
            "ManagerEmployeeID": manager_for_titles(context, definition["ManagerTitles"]),
            "NominalDailyCapacityHours": money(
                float(WORK_CENTER_FALLBACK_NOMINAL_HOURS.get(work_center_code, 0.0))
            ),
            "IsActive": 1,
        })
    append_rows(context, "WorkCenter", work_center_rows)

    work_center_ids = {row["WorkCenterCode"]: int(row["WorkCenterID"]) for row in work_center_rows}
    items = context.tables["Item"].copy()
    routing_rows: list[dict[str, Any]] = []
    routing_operation_rows: list[dict[str, Any]] = []

    for item in manufactured.itertuples(index=False):
        rng = np.random.default_rng(context.settings.random_seed + int(item.ItemID) * 313)
        routing_id = next_id(context, "Routing")
        routing_rows.append({
            "RoutingID": routing_id,
            "ParentItemID": int(item.ItemID),
            "VersionNumber": 1,
            "EffectiveStartDate": context.settings.fiscal_year_start,
            "EffectiveEndDate": None,
            "Status": "Active",
        })

        pattern = routing_pattern_for_item(context, str(item.ItemGroup), int(item.ItemID))
        operation_codes = [operation_code for operation_code, _ in pattern]
        run_hours = normalized_operation_run_hours(float(item.StandardLaborHoursPerUnit), operation_codes)
        for sequence, ((operation_code, operation_name), operation_run_hours) in enumerate(zip(pattern, run_hours, strict=False), start=1):
            setup_low, setup_high = OPERATION_SETUP_HOURS_RANGE[operation_code]
            queue_options = OPERATION_QUEUE_DAY_OPTIONS[operation_code]
            routing_operation_rows.append({
                "RoutingOperationID": next_id(context, "RoutingOperation"),
                "RoutingID": routing_id,
                "OperationSequence": sequence,
                "OperationCode": operation_code,
                "OperationName": operation_name,
                "WorkCenterID": int(work_center_ids[operation_code]),
                "StandardSetupHours": money(float(rng.uniform(setup_low, setup_high))),
                "StandardRunHoursPerUnit": money(float(operation_run_hours)),
                "StandardQueueDays": int(rng.integers(queue_options[0], queue_options[1] + 1)),
            })

        item_mask = items["ItemID"].astype(int).eq(int(item.ItemID))
        items.loc[item_mask, "RoutingID"] = int(routing_id)

    context.tables["Item"] = items[TABLE_COLUMNS["Item"]]
    append_rows(context, "Routing", routing_rows)
    append_rows(context, "RoutingOperation", routing_operation_rows)


def reset_capacity_caches(context: GenerationContext) -> None:
    drop_context_attributes(context, ["_work_center_calendar_lookup", "_work_center_schedule_usage"])


def generate_work_center_calendars(context: GenerationContext) -> None:
    if not context.tables["WorkCenterCalendar"].empty or context.tables["WorkCenter"].empty:
        return

    work_centers = context.tables["WorkCenter"].copy()
    base_calendar = context.calendar.copy()
    base_calendar["DateTS"] = pd.to_datetime(base_calendar["Date"])
    holiday_dates = holiday_dates_for_context(context)
    calendar_rows: list[dict[str, Any]] = []

    for work_center in work_centers.itertuples(index=False):
        work_center_id = int(work_center.WorkCenterID)
        work_center_code = str(work_center.WorkCenterCode)
        nominal_capacity = float(work_center.NominalDailyCapacityHours)
        maintenance_dates: set[str] = set()
        reduced_capacity_dates: dict[str, float] = {}

        for year in sorted(base_calendar["DateTS"].dt.year.unique().tolist()):
            for quarter in [1, 2, 3, 4]:
                candidates = base_calendar[
                    base_calendar["DateTS"].dt.year.eq(int(year))
                    & base_calendar["Quarter"].eq(int(quarter))
                    & base_calendar["IsWeekend"].eq(0)
                    & ~base_calendar["Date"].isin(holiday_dates)
                ].sort_values("DateTS")
                if candidates.empty:
                    continue
                maintenance_rng = capacity_rng(context, "maintenance-day", work_center_id, int(year), int(quarter))
                maintenance_date = str(candidates.iloc[int(maintenance_rng.integers(0, len(candidates)))]["Date"])
                maintenance_dates.add(maintenance_date)

            for month in range(1, 13):
                month_candidates = base_calendar[
                    base_calendar["DateTS"].dt.year.eq(int(year))
                    & base_calendar["DateTS"].dt.month.eq(int(month))
                    & base_calendar["IsWeekend"].eq(0)
                    & ~base_calendar["Date"].isin(holiday_dates)
                ].sort_values("DateTS")
                if month_candidates.empty:
                    continue
                month_candidates = month_candidates[~month_candidates["Date"].isin(maintenance_dates)]
                if month_candidates.empty:
                    continue
                reduced_rng = capacity_rng(context, "reduced-capacity-day", work_center_id, int(year), int(month))
                reduced_date = str(month_candidates.iloc[int(reduced_rng.integers(0, len(month_candidates)))]["Date"])
                capacity_low, capacity_high = REDUCED_CAPACITY_FACTOR_RANGE[work_center_code]
                reduced_capacity_dates[reduced_date] = money(
                    nominal_capacity * float(reduced_rng.uniform(capacity_low, capacity_high))
                )

        for date_row in base_calendar.itertuples(index=False):
            date_value = str(date_row.Date)
            if int(date_row.IsWeekend) == 1:
                is_working_day = 0
                available_hours = 0.0
                exception_reason = "Weekend"
            elif date_value in holiday_dates:
                is_working_day = 0
                available_hours = 0.0
                exception_reason = "Holiday"
            elif date_value in maintenance_dates:
                is_working_day = 1
                available_hours = money(nominal_capacity * 0.50)
                exception_reason = "Maintenance"
            elif date_value in reduced_capacity_dates:
                is_working_day = 1
                available_hours = float(reduced_capacity_dates[date_value])
                exception_reason = "Reduced Capacity"
            else:
                is_working_day = 1
                available_hours = money(nominal_capacity)
                exception_reason = "Normal"

            calendar_rows.append({
                "WorkCenterCalendarID": next_id(context, "WorkCenterCalendar"),
                "WorkCenterID": work_center_id,
                "CalendarDate": date_value,
                "IsWorkingDay": is_working_day,
                "AvailableHours": available_hours,
                "ExceptionReason": exception_reason,
            })

    append_rows(context, "WorkCenterCalendar", calendar_rows)
    reset_capacity_caches(context)


def material_inventory_state(context: GenerationContext) -> dict[tuple[int, int], float]:
    inventory = getattr(context, "_manufacturing_material_inventory", None)
    if inventory is None:
        opening_inventory = opening_inventory_map(context)
        material_item_ids = set(
            context.tables["Item"].loc[
                context.tables["Item"]["ItemGroup"].isin(["Raw Materials", "Packaging"]),
                "ItemID",
            ].astype(int).tolist()
        )
        inventory = {
            (item_id, warehouse_id): float(quantity)
            for (item_id, warehouse_id), quantity in opening_inventory.items()
            if int(item_id) in material_item_ids
        }
        setattr(context, "_manufacturing_material_inventory", inventory)
        setattr(context, "_manufacturing_processed_receipt_lines", set())
    return inventory


def sync_material_inventory_receipts(context: GenerationContext, year: int, month: int) -> None:
    inventory = material_inventory_state(context)
    processed_ids: set[int] = getattr(context, "_manufacturing_processed_receipt_lines", set())
    goods_receipts = context.tables["GoodsReceipt"]
    goods_receipt_lines = context.tables["GoodsReceiptLine"]
    if goods_receipts.empty or goods_receipt_lines.empty:
        return

    receipt_headers = goods_receipts.set_index("GoodsReceiptID")[["ReceiptDate", "WarehouseID"]].to_dict("index")
    item_groups = context.tables["Item"].set_index("ItemID")["ItemGroup"].to_dict()
    month_start, month_end = month_bounds(year, month)

    for line in goods_receipt_lines.itertuples(index=False):
        goods_receipt_line_id = int(line.GoodsReceiptLineID)
        if goods_receipt_line_id in processed_ids:
            continue
        header = receipt_headers.get(int(line.GoodsReceiptID))
        if header is None:
            continue
        receipt_date = pd.Timestamp(header["ReceiptDate"])
        if not month_start <= receipt_date <= month_end:
            continue
        if str(item_groups.get(int(line.ItemID))) not in {"Raw Materials", "Packaging"}:
            continue
        key = (int(line.ItemID), int(header["WarehouseID"]))
        inventory[key] = round(float(inventory.get(key, 0.0)) + float(line.QuantityReceived), 2)
        processed_ids.add(goods_receipt_line_id)

    setattr(context, "_manufacturing_processed_receipt_lines", processed_ids)


def work_order_completed_quantity_map(context: GenerationContext) -> dict[int, float]:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completions.empty or completion_lines.empty:
        return {}
    state = getattr(context, "_work_order_completed_quantity_state", None)
    if state is None:
        state = {
            "processed_completion_count": 0,
            "processed_completion_line_count": 0,
            "completion_work_order": {},
            "totals": defaultdict(float),
        }

    if int(state["processed_completion_count"]) < len(completions):
        completion_work_order: dict[int, int] = state["completion_work_order"]
        new_headers = completions.iloc[int(state["processed_completion_count"]):]
        for header in new_headers.itertuples(index=False):
            completion_work_order[int(header.ProductionCompletionID)] = int(header.WorkOrderID)
        state["processed_completion_count"] = len(completions)

    if int(state["processed_completion_line_count"]) < len(completion_lines):
        completion_work_order = state["completion_work_order"]
        totals: defaultdict[int, float] = state["totals"]
        new_lines = completion_lines.iloc[int(state["processed_completion_line_count"]):]
        for line in new_lines.itertuples(index=False):
            work_order_id = completion_work_order.get(int(line.ProductionCompletionID))
            if work_order_id is None:
                continue
            totals[int(work_order_id)] += float(line.QuantityCompleted)
        state["processed_completion_line_count"] = len(completion_lines)

    cached = {int(key): qty(float(value)) for key, value in state["totals"].items()}
    setattr(context, "_work_order_completed_quantity_state", state)
    setattr(context, "_work_order_completed_quantity_map_cache", cached)
    return cached


def work_order_material_issue_cost_map(context: GenerationContext) -> dict[int, float]:
    issues = context.tables["MaterialIssue"]
    issue_lines = context.tables["MaterialIssueLine"]
    if issues.empty or issue_lines.empty:
        return {}
    state = getattr(context, "_work_order_material_issue_cost_state", None)
    if state is None:
        state = {
            "processed_issue_count": 0,
            "processed_issue_line_count": 0,
            "issue_work_order": {},
            "totals": defaultdict(float),
        }

    if int(state["processed_issue_count"]) < len(issues):
        issue_work_order: dict[int, int] = state["issue_work_order"]
        new_headers = issues.iloc[int(state["processed_issue_count"]):]
        for header in new_headers.itertuples(index=False):
            issue_work_order[int(header.MaterialIssueID)] = int(header.WorkOrderID)
        state["processed_issue_count"] = len(issues)

    if int(state["processed_issue_line_count"]) < len(issue_lines):
        issue_work_order = state["issue_work_order"]
        totals: defaultdict[int, float] = state["totals"]
        new_lines = issue_lines.iloc[int(state["processed_issue_line_count"]):]
        for line in new_lines.itertuples(index=False):
            work_order_id = issue_work_order.get(int(line.MaterialIssueID))
            if work_order_id is None:
                continue
            totals[int(work_order_id)] += float(line.ExtendedStandardCost)
        state["processed_issue_line_count"] = len(issue_lines)

    cached = {int(key): money(float(value)) for key, value in state["totals"].items()}
    setattr(context, "_work_order_material_issue_cost_state", state)
    setattr(context, "_work_order_material_issue_cost_map_cache", cached)
    return cached


def work_order_standard_material_cost_map(context: GenerationContext) -> dict[int, float]:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completions.empty or completion_lines.empty:
        return {}
    cached = getattr(context, "_work_order_standard_material_cost_map_cache", None)
    if cached is not None:
        return cached
    work_order_lookup = completions.set_index("ProductionCompletionID")["WorkOrderID"].astype(int).to_dict()
    totals: dict[int, float] = defaultdict(float)
    for line in completion_lines.itertuples(index=False):
        work_order_id = work_order_lookup.get(int(line.ProductionCompletionID))
        if work_order_id is None:
            continue
        totals[int(work_order_id)] += float(line.ExtendedStandardMaterialCost)
    cached = {key: money(value) for key, value in totals.items()}
    setattr(context, "_work_order_standard_material_cost_map_cache", cached)
    return cached


def work_order_standard_conversion_cost_map(context: GenerationContext) -> dict[int, float]:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completions.empty or completion_lines.empty:
        return {}
    cached = getattr(context, "_work_order_standard_conversion_cost_map_cache", None)
    if cached is not None:
        return cached
    work_order_lookup = completions.set_index("ProductionCompletionID")["WorkOrderID"].astype(int).to_dict()
    totals: dict[int, float] = defaultdict(float)
    for line in completion_lines.itertuples(index=False):
        work_order_id = work_order_lookup.get(int(line.ProductionCompletionID))
        if work_order_id is None:
            continue
        totals[int(work_order_id)] += float(line.ExtendedStandardConversionCost)
    cached = {key: money(value) for key, value in totals.items()}
    setattr(context, "_work_order_standard_conversion_cost_map_cache", cached)
    return cached


def work_order_standard_direct_labor_cost_map(context: GenerationContext) -> dict[int, float]:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completions.empty or completion_lines.empty:
        return {}
    cached = getattr(context, "_work_order_standard_direct_labor_cost_map_cache", None)
    if cached is not None:
        return cached

    work_order_lookup = completions.set_index("ProductionCompletionID")["WorkOrderID"].astype(int).to_dict()
    totals: dict[int, float] = defaultdict(float)
    for line in completion_lines.itertuples(index=False):
        work_order_id = work_order_lookup.get(int(line.ProductionCompletionID))
        if work_order_id is None:
            continue
        totals[int(work_order_id)] += float(line.ExtendedStandardDirectLaborCost)
    cached = {key: money(value) for key, value in totals.items()}
    setattr(context, "_work_order_standard_direct_labor_cost_map_cache", cached)
    return cached


def work_order_standard_overhead_cost_map(context: GenerationContext) -> dict[int, float]:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completions.empty or completion_lines.empty:
        return {}
    cached = getattr(context, "_work_order_standard_overhead_cost_map_cache", None)
    if cached is not None:
        return cached

    work_order_lookup = completions.set_index("ProductionCompletionID")["WorkOrderID"].astype(int).to_dict()
    totals: dict[int, float] = defaultdict(float)
    for line in completion_lines.itertuples(index=False):
        work_order_id = work_order_lookup.get(int(line.ProductionCompletionID))
        if work_order_id is None:
            continue
        totals[int(work_order_id)] += (
            float(line.ExtendedStandardVariableOverheadCost)
            + float(line.ExtendedStandardFixedOverheadCost)
        )
    cached = {key: money(value) for key, value in totals.items()}
    setattr(context, "_work_order_standard_overhead_cost_map_cache", cached)
    return cached


def work_order_actual_conversion_cost_map(context: GenerationContext) -> dict[int, float]:
    direct_labor = labor_time_direct_cost_by_work_order(context)
    overhead = work_order_overhead_cost_map(context)
    totals: dict[int, float] = defaultdict(float)
    for work_order_id in set(direct_labor) | set(overhead):
        totals[int(work_order_id)] = money(
            float(direct_labor.get(int(work_order_id), 0.0))
            + float(overhead.get(int(work_order_id), 0.0))
        )
    return {key: money(value) for key, value in totals.items()}


def open_work_order_remaining_quantity_map(context: GenerationContext) -> dict[int, float]:
    work_orders = context.tables["WorkOrder"]
    if work_orders.empty:
        return {}
    completed_map = work_order_completed_quantity_map(context)
    remaining: dict[int, float] = {}
    for work_order in work_orders.itertuples(index=False):
        remaining_quantity = qty(float(work_order.PlannedQuantity) - float(completed_map.get(int(work_order.WorkOrderID), 0.0)))
        if remaining_quantity > 0 and str(work_order.Status) != "Closed":
            remaining[int(work_order.WorkOrderID)] = remaining_quantity
    return remaining


def standard_material_unit_cost(context: GenerationContext, bom_id: int) -> float:
    items = context.tables["Item"].set_index("ItemID")
    bom_lines = bom_lines_by_bom(context).get(int(bom_id))
    if bom_lines is None or bom_lines.empty:
        return 0.0
    return money(sum(
        float(items.loc[int(line.ComponentItemID), "StandardCost"]) * float(line.QuantityPerUnit) * (1 + float(line.ScrapFactorPct))
        for line in bom_lines.itertuples(index=False)
    ))


def manufacturing_open_state(context: GenerationContext) -> dict[str, float]:
    work_orders = context.tables["WorkOrder"]
    closes = context.tables["WorkOrderClose"]
    work_center_calendar = context.tables["WorkCenterCalendar"]
    schedules = context.tables["WorkOrderOperationSchedule"]
    issue_cost = work_order_material_issue_cost_map(context)
    standard_material = work_order_standard_material_cost_map(context)
    actual_conversion = work_order_actual_conversion_cost_map(context)
    standard_conversion = work_order_standard_conversion_cost_map(context)

    material_close = closes.set_index("WorkOrderID")["MaterialVarianceAmount"].astype(float).to_dict() if not closes.empty else {}
    conversion_close = closes.set_index("WorkOrderID")["ConversionVarianceAmount"].astype(float).to_dict() if not closes.empty else {}

    wip_balance = sum(
        float(issue_cost.get(work_order_id, 0.0))
        - float(standard_material.get(work_order_id, 0.0))
        - float(material_close.get(work_order_id, 0.0))
        for work_order_id in set(issue_cost) | set(standard_material) | set(material_close)
    )
    clearing_balance = sum(
        float(actual_conversion.get(work_order_id, 0.0))
        - float(standard_conversion.get(work_order_id, 0.0))
        - float(conversion_close.get(work_order_id, 0.0))
        for work_order_id in set(actual_conversion) | set(standard_conversion) | set(conversion_close)
    )
    variance_posted = float(closes["TotalVarianceAmount"].sum()) if not closes.empty else 0.0
    open_work_orders = int(work_orders["Status"].isin(["Released", "In Progress", "Completed"]).sum()) if not work_orders.empty else 0

    return {
        "manufactured_item_count": float(len(manufactured_items(context))),
        "bom_count": float(len(context.tables["BillOfMaterial"])),
        "bom_line_count": float(len(context.tables["BillOfMaterialLine"])),
        "work_center_count": float(len(context.tables["WorkCenter"])),
        "work_center_calendar_count": float(len(work_center_calendar)),
        "routing_count": float(len(context.tables["Routing"])),
        "routing_operation_count": float(len(context.tables["RoutingOperation"])),
        "work_order_operation_count": float(len(context.tables["WorkOrderOperation"])),
        "work_order_operation_schedule_count": float(len(schedules)),
        "open_work_order_count": float(open_work_orders),
        "wip_balance": money(wip_balance),
        "manufacturing_clearing_balance": money(clearing_balance),
        "manufacturing_variance_posted": money(variance_posted),
    }


def manufacturing_capacity_state(context: GenerationContext, year: int, month: int) -> dict[str, float]:
    month_start, month_end = month_bounds(year, month)
    calendars = context.tables["WorkCenterCalendar"]
    schedules = context.tables["WorkOrderOperationSchedule"]
    work_orders = context.tables["WorkOrder"]
    work_order_operations = context.tables["WorkOrderOperation"]

    if calendars.empty:
        return {
            "available_work_center_hours": 0.0,
            "scheduled_work_center_hours": 0.0,
            "utilization_pct": 0.0,
            "fully_booked_days": 0.0,
            "late_operations": 0.0,
            "late_work_orders": 0.0,
            "open_backlog_hours": 0.0,
        }

    month_calendars = calendars[
        pd.to_datetime(calendars["CalendarDate"]).between(month_start, month_end)
    ].copy()
    available_hours = round(float(month_calendars["AvailableHours"].astype(float).sum()), 2)

    month_schedules = schedules[
        pd.to_datetime(schedules["ScheduleDate"]).between(month_start, month_end)
    ].copy() if not schedules.empty else schedules.copy()
    scheduled_hours = round(float(month_schedules["ScheduledHours"].astype(float).sum()), 2) if not month_schedules.empty else 0.0

    fully_booked_days = 0
    if not month_schedules.empty:
        scheduled_by_day = month_schedules.groupby(["WorkCenterID", "ScheduleDate"])["ScheduledHours"].sum().round(2)
        for (work_center_id, schedule_date), hours in scheduled_by_day.items():
            available = month_calendars[
                month_calendars["WorkCenterID"].astype(int).eq(int(work_center_id))
                & month_calendars["CalendarDate"].eq(str(schedule_date))
            ]["AvailableHours"].astype(float)
            if not available.empty and round(float(hours), 2) >= round(float(available.iloc[0]), 2) and float(available.iloc[0]) > 0:
                fully_booked_days += 1

    late_operations = 0
    if not work_order_operations.empty:
        operations = work_order_operations.copy()
        operations["PlannedEndDateTS"] = pd.to_datetime(operations["PlannedEndDate"], errors="coerce")
        operations["ActualEndDateTS"] = pd.to_datetime(operations["ActualEndDate"], errors="coerce")
        late_operations = int(
            (
                operations["ActualEndDateTS"].notna()
                & operations["PlannedEndDateTS"].notna()
                & operations["ActualEndDateTS"].gt(operations["PlannedEndDateTS"])
                & operations["ActualEndDateTS"].between(month_start, month_end)
            ).sum()
        )

    late_work_orders = 0
    if not work_orders.empty:
        work_order_rows = work_orders.copy()
        work_order_rows["DueDateTS"] = pd.to_datetime(work_order_rows["DueDate"], errors="coerce")
        work_order_rows["CompletedDateTS"] = pd.to_datetime(work_order_rows["CompletedDate"], errors="coerce")
        completed_late = (
            work_order_rows["CompletedDateTS"].notna()
            & work_order_rows["DueDateTS"].notna()
            & work_order_rows["CompletedDateTS"].gt(work_order_rows["DueDateTS"])
            & work_order_rows["CompletedDateTS"].between(month_start, month_end)
        )
        open_late = (
            work_order_rows["CompletedDateTS"].isna()
            & work_order_rows["DueDateTS"].notna()
            & work_order_rows["DueDateTS"].lt(month_end)
            & work_order_rows["Status"].isin(["Released", "In Progress"])
        )
        late_work_orders = int(completed_late.sum() + open_late.sum())

    open_backlog_hours = 0.0
    if not work_order_operations.empty:
        operation_rows = work_order_operations.copy()
        operation_rows["PlannedEndDateTS"] = pd.to_datetime(operation_rows["PlannedEndDate"], errors="coerce")
        open_backlog_hours = round(float(
            operation_rows.loc[
                operation_rows["Status"].isin(["Released", "In Progress"])
                & operation_rows["PlannedEndDateTS"].gt(month_end),
                "PlannedLoadHours",
            ].astype(float).sum()
        ), 2)

    utilization_pct = round((scheduled_hours / available_hours) * 100, 2) if available_hours > 0 else 0.0
    return {
        "available_work_center_hours": available_hours,
        "scheduled_work_center_hours": scheduled_hours,
        "utilization_pct": utilization_pct,
        "fully_booked_days": float(fully_booked_days),
        "late_operations": float(late_operations),
        "late_work_orders": float(late_work_orders),
        "open_backlog_hours": open_backlog_hours,
    }


def manufacturing_work_center_utilization_by_code(
    context: GenerationContext,
    year: int,
    month: int,
    work_center_codes: tuple[str, ...] = ("ASSEMBLY", "CUT", "FINISH", "PACK", "QA"),
) -> dict[str, float]:
    month_start, month_end = month_bounds(year, month)
    work_centers = context.tables["WorkCenter"]
    calendars = context.tables["WorkCenterCalendar"]
    schedules = context.tables["WorkOrderOperationSchedule"]
    if work_centers.empty or calendars.empty:
        return {code: 0.0 for code in work_center_codes}

    work_center_id_by_code = {
        str(row.WorkCenterCode): int(row.WorkCenterID)
        for row in work_centers.itertuples(index=False)
    }
    month_calendars = calendars[
        pd.to_datetime(calendars["CalendarDate"]).between(month_start, month_end)
    ].copy()
    month_schedules = (
        schedules[pd.to_datetime(schedules["ScheduleDate"]).between(month_start, month_end)].copy()
        if not schedules.empty
        else schedules.head(0).copy()
    )
    state: dict[str, float] = {}
    for work_center_code in work_center_codes:
        work_center_id = work_center_id_by_code.get(str(work_center_code))
        if work_center_id is None:
            state[str(work_center_code)] = 0.0
            continue
        available_hours = float(
            month_calendars.loc[
                month_calendars["WorkCenterID"].astype(int).eq(int(work_center_id)),
                "AvailableHours",
            ].astype(float).sum()
        )
        scheduled_hours = float(
            month_schedules.loc[
                month_schedules["WorkCenterID"].astype(int).eq(int(work_center_id)),
                "ScheduledHours",
            ].astype(float).sum()
        ) if not month_schedules.empty else 0.0
        state[str(work_center_code)] = round(scheduled_hours / available_hours, 4) if available_hours > 0 else 0.0
    return state


def manufacturing_work_center_available_hours_by_code(
    context: GenerationContext,
    year: int,
    month: int,
    work_center_codes: tuple[str, ...] = ("ASSEMBLY", "CUT", "FINISH", "PACK", "QA"),
) -> dict[str, float]:
    month_start, month_end = month_bounds(year, month)
    work_centers = context.tables["WorkCenter"]
    calendars = context.tables["WorkCenterCalendar"]
    if work_centers.empty or calendars.empty:
        return {code: 0.0 for code in work_center_codes}

    work_center_id_by_code = {
        str(row.WorkCenterCode): int(row.WorkCenterID)
        for row in work_centers.itertuples(index=False)
    }
    month_calendars = calendars[
        pd.to_datetime(calendars["CalendarDate"]).between(month_start, month_end)
    ].copy()
    state: dict[str, float] = {}
    for work_center_code in work_center_codes:
        work_center_id = work_center_id_by_code.get(str(work_center_code))
        if work_center_id is None:
            state[str(work_center_code)] = 0.0
            continue
        state[str(work_center_code)] = round(
            float(
                month_calendars.loc[
                    month_calendars["WorkCenterID"].astype(int).eq(int(work_center_id)),
                    "AvailableHours",
                ].astype(float).sum()
            ),
            2,
        )
    return state


def manufacturing_work_center_nominal_daily_hours_by_code(
    context: GenerationContext,
    work_center_codes: tuple[str, ...] = ("ASSEMBLY", "CUT", "FINISH", "PACK", "QA"),
) -> dict[str, float]:
    work_centers = context.tables["WorkCenter"]
    if work_centers.empty:
        return {code: 0.0 for code in work_center_codes}

    nominal_by_code = {
        str(row.WorkCenterCode): round(float(row.NominalDailyCapacityHours), 2)
        for row in work_centers.itertuples(index=False)
    }
    return {
        str(work_center_code): float(nominal_by_code.get(str(work_center_code), 0.0))
        for work_center_code in work_center_codes
    }


def manufacturing_capacity_diagnostics_by_code(
    context: GenerationContext,
    year: int,
    month: int,
    work_center_codes: tuple[str, ...] = ("ASSEMBLY", "CUT", "FINISH", "PACK", "QA"),
) -> dict[str, dict[str, float]]:
    month_start, month_end = month_bounds(year, month)
    work_centers = context.tables["WorkCenter"]
    rosters = context.tables["EmployeeShiftRoster"]
    schedules = context.tables["WorkOrderOperationSchedule"]
    work_center_id_by_code = {
        str(row.WorkCenterCode): int(row.WorkCenterID)
        for row in work_centers.itertuples(index=False)
    } if not work_centers.empty else {}

    assignment_counts = active_primary_direct_assignment_counts(context)
    assignment_shares = work_center_shares_from_counts(assignment_counts)
    nominal_hours = manufacturing_work_center_nominal_daily_hours_by_code(context, work_center_codes=work_center_codes)
    total_nominal_hours = sum(nominal_hours.values()) or 1.0
    available_hours = manufacturing_work_center_available_hours_by_code(context, year, month, work_center_codes=work_center_codes)
    utilization = manufacturing_work_center_utilization_by_code(context, year, month, work_center_codes=work_center_codes)

    rostered_hours_by_center: dict[int, float] = {}
    if not rosters.empty:
        month_rosters = rosters[
            pd.to_datetime(rosters["RosterDate"], errors="coerce").between(month_start, month_end)
            & rosters["WorkCenterID"].notna()
            & rosters["RosterStatus"].isin(["Scheduled", "Reassigned", "Absent"])
        ].copy()
        if not month_rosters.empty:
            rostered_hours_by_center = {
                int(work_center_id): round(float(hours), 2)
                for work_center_id, hours in month_rosters.groupby("WorkCenterID")["ScheduledHours"].sum().items()
            }

    scheduled_hours_by_center: dict[int, float] = {}
    if not schedules.empty:
        month_schedules = schedules[
            pd.to_datetime(schedules["ScheduleDate"], errors="coerce").between(month_start, month_end)
        ].copy()
        if not month_schedules.empty:
            scheduled_hours_by_center = {
                int(work_center_id): round(float(hours), 2)
                for work_center_id, hours in month_schedules.groupby("WorkCenterID")["ScheduledHours"].sum().items()
            }

    diagnostics: dict[str, dict[str, float]] = {}
    for work_center_code in work_center_codes:
        work_center_id = work_center_id_by_code.get(str(work_center_code))
        diagnostics[str(work_center_code)] = {
            "assigned_direct_worker_count": float(assignment_counts.get(str(work_center_code), 0)),
            "assigned_direct_worker_share": round(float(assignment_shares.get(str(work_center_code), 0.0)), 4),
            "nominal_daily_capacity_hours": round(float(nominal_hours.get(str(work_center_code), 0.0)), 2),
            "nominal_daily_capacity_share": round(float(nominal_hours.get(str(work_center_code), 0.0)) / total_nominal_hours, 4),
            "rostered_hours": round(float(rostered_hours_by_center.get(int(work_center_id), 0.0)), 2) if work_center_id is not None else 0.0,
            "scheduled_hours": round(float(scheduled_hours_by_center.get(int(work_center_id), 0.0)), 2) if work_center_id is not None else 0.0,
            "monthly_available_hours": round(float(available_hours.get(str(work_center_code), 0.0)), 2),
            "monthly_utilization_pct": round(float(utilization.get(str(work_center_code), 0.0)) * 100, 2),
        }
    return diagnostics


def manufacture_recommendation_load_by_work_center(
    context: GenerationContext,
    recommendations: pd.DataFrame,
    work_center_codes: tuple[str, ...] = ("ASSEMBLY", "CUT", "FINISH", "PACK", "QA"),
) -> dict[str, float]:
    if recommendations.empty:
        return {code: 0.0 for code in work_center_codes}

    routing_by_parent = active_routing_by_item(context)
    routing_operations = routing_operations_by_routing(context)
    work_centers = context.tables["WorkCenter"]
    work_center_code_by_id = (
        work_centers.set_index("WorkCenterID")["WorkCenterCode"].astype(str).to_dict()
        if not work_centers.empty
        else {}
    )
    included_codes = {str(code) for code in work_center_codes}
    totals: dict[str, float] = defaultdict(float)

    for recommendation in recommendations.itertuples(index=False):
        routing = routing_by_parent.get(int(recommendation.ItemID))
        if routing is None:
            continue
        operation_rows = routing_operations.get(int(routing["RoutingID"]))
        if operation_rows is None or operation_rows.empty:
            continue
        planned_quantity = float(recommendation.RecommendedOrderQuantity)
        for operation in operation_rows.itertuples(index=False):
            work_center_code = str(work_center_code_by_id.get(int(operation.WorkCenterID), ""))
            if work_center_code not in included_codes:
                continue
            totals[work_center_code] += (
                float(operation.StandardSetupHours)
                + (float(operation.StandardRunHoursPerUnit) * planned_quantity)
            )

    return {
        str(work_center_code): round(float(totals.get(str(work_center_code), 0.0)), 2)
        for work_center_code in work_center_codes
    }


def finished_goods_shortage_by_item(context: GenerationContext, month_end: pd.Timestamp) -> dict[int, dict[str, float]]:
    inventory = shadow_inventory_state(context)
    manufactured = manufactured_items(context, month_end)
    if manufactured.empty:
        return {}

    sales_orders = context.tables["SalesOrder"]
    sales_order_lines = context.tables["SalesOrderLine"]
    shipped_quantities = sales_order_line_shipped_quantities(context)
    if sales_orders.empty or sales_order_lines.empty:
        return {}

    open_lines = sales_order_lines.copy()
    open_lines["ShippedQuantity"] = open_lines["SalesOrderLineID"].astype(int).map(shipped_quantities).fillna(0.0)
    open_lines["RemainingQuantity"] = (open_lines["Quantity"].astype(float) - open_lines["ShippedQuantity"].astype(float)).round(2)
    open_lines = open_lines[open_lines["RemainingQuantity"].gt(0)]
    if open_lines.empty:
        return {}

    order_lookup = sales_orders.set_index("SalesOrderID")[["OrderDate"]].to_dict("index")
    open_lines["OrderDate"] = open_lines["SalesOrderID"].astype(int).map(
        lambda sales_order_id: order_lookup.get(int(sales_order_id), {}).get("OrderDate")
    )
    open_lines = open_lines[pd.to_datetime(open_lines["OrderDate"]).le(month_end)]
    if open_lines.empty:
        return {}

    demand_by_item = open_lines.groupby("ItemID")["RemainingQuantity"].sum().round(2).to_dict()
    open_work_order_qty = open_work_order_remaining_quantity_map(context)
    open_work_orders = context.tables["WorkOrder"]
    open_completion_by_item: dict[int, float] = defaultdict(float)
    if not open_work_orders.empty:
        for work_order in open_work_orders.itertuples(index=False):
            remaining_quantity = float(open_work_order_qty.get(int(work_order.WorkOrderID), 0.0))
            if remaining_quantity <= 0 or str(work_order.Status) == "Closed":
                continue
            open_completion_by_item[int(work_order.ItemID)] += remaining_quantity

    shortages: dict[int, dict[str, float]] = {}
    for item in manufactured.itertuples(index=False):
        item_id = int(item.ItemID)
        backlog = float(demand_by_item.get(item_id, 0.0))
        if backlog <= 0:
            continue
        item_rng = np.random.default_rng(context.settings.random_seed + item_id * 811)
        buffer_low, buffer_high = FINISHED_GOODS_BUFFER_RANGE.get(str(item.ItemGroup), (6.0, 16.0))
        target_buffer = qty(item_rng.uniform(buffer_low, buffer_high))
        on_hand = round(
            sum(float(quantity) for (inventory_item_id, _), quantity in inventory.items() if int(inventory_item_id) == item_id),
            2,
        )
        scheduled_completion = round(float(open_completion_by_item.get(item_id, 0.0)), 2)
        shortage = qty(backlog + target_buffer - on_hand - scheduled_completion)
        if shortage > 0:
            shortages[item_id] = {
                "backlog": qty(backlog),
                "buffer": target_buffer,
                "on_hand": qty(on_hand),
                "scheduled_completion": qty(scheduled_completion),
                "shortage": shortage,
            }
    return shortages


def schedule_operation_rows(
    context: GenerationContext,
    work_order_operation_id: int,
    work_center_id: int,
    earliest_start: pd.Timestamp,
    planned_load_hours: float,
    latest_end: pd.Timestamp,
) -> list[dict[str, Any]]:
    lookup = work_center_calendar_lookup(context)
    usage = schedule_usage_map(context)
    working_dates = work_center_working_dates(context).get(int(work_center_id), ())
    working_date_index = work_center_working_date_index(context).get(int(work_center_id), {})
    start_date = pd.Timestamp(earliest_start).normalize()
    current_date = previous_schedulable_day(
        context,
        int(work_center_id),
        min(operational_calendar_end(context), pd.Timestamp(latest_end).normalize()),
    )
    remaining_hours = money(planned_load_hours)
    schedule_rows: list[dict[str, Any]] = []

    while remaining_hours > 0 and current_date is not None and current_date >= start_date:
        date_key = current_date.strftime("%Y-%m-%d")
        calendar_row = lookup.get((int(work_center_id), date_key))
        available_hours = float(calendar_row["AvailableHours"]) if calendar_row is not None else 0.0
        used_hours = float(usage.get((int(work_center_id), date_key), 0.0))
        free_hours = money(max(available_hours - used_hours, 0.0))
        if free_hours > 0:
            scheduled_hours = money(min(remaining_hours, free_hours))
            schedule_rows.append({
                "WorkOrderOperationScheduleID": next_id(context, "WorkOrderOperationSchedule"),
                "WorkOrderOperationID": int(work_order_operation_id),
                "WorkCenterID": int(work_center_id),
                "ScheduleDate": date_key,
                "ScheduledHours": scheduled_hours,
            })
            usage[(int(work_center_id), date_key)] = money(used_hours + scheduled_hours)
            remaining_hours = money(remaining_hours - scheduled_hours)
        current_index = working_date_index.get(date_key)
        if current_index is None or current_index <= 0:
            break
        current_date = pd.Timestamp(working_dates[current_index - 1])

    if remaining_hours > 0:
        rollback_schedule_usage(context, schedule_rows)
        return []
    schedule_rows.sort(key=lambda row: (str(row["ScheduleDate"]), int(row["WorkOrderOperationScheduleID"])))
    return schedule_rows


def build_work_order_operations(
    context: GenerationContext,
    work_order_id: int,
    routing_id: int,
    planned_quantity: float,
    release_date: pd.Timestamp,
    due_date: pd.Timestamp,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    routing_rows = routing_operations_by_routing(context).get(int(routing_id))
    if routing_rows is None or routing_rows.empty:
        return [], []

    scheduled_operations: list[tuple[int, dict[str, Any], list[dict[str, Any]], pd.Timestamp]] = []
    reserved_schedule_rows: list[dict[str, Any]] = []
    due_date = pd.Timestamp(due_date).normalize()
    release_date = pd.Timestamp(release_date).normalize()
    next_operation_start: pd.Timestamp | None = None

    for row in reversed(list(routing_rows.sort_values("OperationSequence").itertuples(index=False))):
        work_center_id = int(row.WorkCenterID)
        latest_end = due_date
        if next_operation_start is not None:
            latest_end = next_operation_start - pd.Timedelta(days=int(row.StandardQueueDays))
        if latest_end < release_date:
            rollback_schedule_usage(context, reserved_schedule_rows)
            return [], []

        planned_load_hours = money(
            float(row.StandardSetupHours) + float(row.StandardRunHoursPerUnit) * float(planned_quantity)
        )
        work_order_operation_id = next_id(context, "WorkOrderOperation")
        operation_schedule_rows = schedule_operation_rows(
            context,
            work_order_operation_id,
            work_center_id,
            release_date,
            planned_load_hours,
            latest_end,
        )
        if not operation_schedule_rows:
            rollback_schedule_usage(context, reserved_schedule_rows)
            return [], []

        planned_start = pd.Timestamp(operation_schedule_rows[0]["ScheduleDate"])
        planned_end = pd.Timestamp(operation_schedule_rows[-1]["ScheduleDate"])
        if planned_end > latest_end or planned_start < release_date:
            rollback_schedule_usage(context, reserved_schedule_rows + operation_schedule_rows)
            return [], []

        operation_row = {
            "WorkOrderOperationID": work_order_operation_id,
            "WorkOrderID": int(work_order_id),
            "RoutingOperationID": int(row.RoutingOperationID),
            "OperationSequence": int(row.OperationSequence),
            "WorkCenterID": work_center_id,
            "PlannedQuantity": qty(float(planned_quantity)),
            "PlannedLoadHours": planned_load_hours,
            "PlannedStartDate": planned_start.strftime("%Y-%m-%d"),
            "PlannedEndDate": planned_end.strftime("%Y-%m-%d"),
            "ActualStartDate": None,
            "ActualEndDate": None,
            "Status": "Released",
        }
        scheduled_operations.append((int(row.OperationSequence), operation_row, operation_schedule_rows, planned_start))
        reserved_schedule_rows.extend(operation_schedule_rows)
        next_operation_start = planned_start

    scheduled_operations.sort(key=lambda payload: payload[0])
    operation_rows = [payload[1] for payload in scheduled_operations]
    schedule_rows: list[dict[str, Any]] = []
    for _, _, operation_schedule_rows, _ in scheduled_operations:
        schedule_rows.extend(operation_schedule_rows)
    return operation_rows, schedule_rows


def _convert_manufacture_recommendations_to_work_orders(
    context: GenerationContext,
    planned_recommendations: pd.DataFrame,
    *,
    release_floor: pd.Timestamp,
    release_ceiling: pd.Timestamp | None = None,
) -> dict[str, Any]:
    if planned_recommendations.empty:
        return {
            "eligible_planned": 0,
            "converted": 0,
            "expired": 0,
            "converted_recommendation_ids": [],
            "expired_recommendation_ids": [],
            "converted_load_by_work_center": {"ASSEMBLY": 0.0, "CUT": 0.0, "FINISH": 0.0, "PACK": 0.0, "QA": 0.0},
            "expired_load_by_work_center": {"ASSEMBLY": 0.0, "CUT": 0.0, "FINISH": 0.0, "PACK": 0.0, "QA": 0.0},
            "expired_reason_counts": {"due_date_infeasible": 0, "missing_master_data": 0},
        }

    rng = context.rng
    month_end = pd.Timestamp(release_ceiling).normalize() if release_ceiling is not None else None
    manufactured_lookup = manufactured_items(context).set_index("ItemID").to_dict("index")
    manufacturing_cost_center = cost_center_id(context, "Manufacturing")
    bom_by_parent = bom_lookup(context)
    routing_by_parent = active_routing_by_item(context)
    manufacturing_employee_ids_by_date: dict[str, list[int]] = {}

    def manufacturing_employee_ids(release_date: pd.Timestamp) -> list[int]:
        date_key = pd.Timestamp(release_date).strftime("%Y-%m-%d")
        cached = manufacturing_employee_ids_by_date.get(date_key)
        if cached is not None:
            return cached
        employee_ids = employee_ids_for_cost_center(context, "Manufacturing", release_date)
        manufacturing_employee_ids_by_date[date_key] = employee_ids
        return employee_ids

    work_order_rows: list[dict[str, Any]] = []
    work_order_operation_rows: list[dict[str, Any]] = []
    work_order_operation_schedule_rows: list[dict[str, Any]] = []
    conversion_mapping: dict[int, tuple[str, int]] = {}
    expired_recommendation_ids: list[int] = []
    expired_reason_counts = {"due_date_infeasible": 0, "missing_master_data": 0}

    ordered_recommendations = planned_recommendations.copy()
    priority_rank = {"Expedite": 0, "Normal": 1}
    ordered_recommendations["__NeedByDateTS"] = pd.to_datetime(
        ordered_recommendations["NeedByDate"],
        errors="coerce",
    )
    ordered_recommendations["__ReleaseByDateTS"] = pd.to_datetime(
        ordered_recommendations["ReleaseByDate"],
        errors="coerce",
    )
    ordered_recommendations["__PriorityRank"] = ordered_recommendations["PriorityCode"].map(priority_rank).fillna(9).astype(int)
    ordered_recommendations = ordered_recommendations.sort_values(
        ["__NeedByDateTS", "__PriorityRank", "__ReleaseByDateTS", "SupplyPlanRecommendationID"]
    ).reset_index(drop=True)

    for recommendation in ordered_recommendations.itertuples(index=False):
        item_row = manufactured_lookup.get(int(recommendation.ItemID))
        bom = bom_by_parent.get(int(recommendation.ItemID))
        routing = routing_by_parent.get(int(recommendation.ItemID))
        planned_quantity = qty(float(recommendation.RecommendedOrderQuantity))
        if item_row is None or bom is None or routing is None or planned_quantity <= 0:
            expired_recommendation_ids.append(int(recommendation.SupplyPlanRecommendationID))
            expired_reason_counts["missing_master_data"] += 1
            continue

        release_date = max(pd.Timestamp(release_floor).normalize(), pd.Timestamp(recommendation.ReleaseByDate).normalize())
        if month_end is not None and release_date > month_end:
            release_date = month_end
        due_date = max(release_date, pd.Timestamp(recommendation.NeedByDate).normalize())

        work_order_id = next_id(context, "WorkOrder")
        work_order_number = format_doc_number("WO", int(release_date.year), work_order_id)
        operation_rows, operation_schedule_rows = build_work_order_operations(
            context,
            work_order_id,
            int(routing["RoutingID"]),
            planned_quantity,
            release_date,
            due_date,
        )
        if not operation_rows or not operation_schedule_rows:
            expired_recommendation_ids.append(int(recommendation.SupplyPlanRecommendationID))
            expired_reason_counts["due_date_infeasible"] += 1
            continue

        employee_pool = manufacturing_employee_ids(release_date)
        work_order_rows.append({
            "WorkOrderID": work_order_id,
            "WorkOrderNumber": work_order_number,
            "ItemID": int(recommendation.ItemID),
            "BOMID": int(bom["BOMID"]),
            "RoutingID": int(routing["RoutingID"]),
            "WarehouseID": int(recommendation.WarehouseID),
            "PlannedQuantity": planned_quantity,
            "ReleasedDate": release_date.strftime("%Y-%m-%d"),
            "DueDate": due_date.strftime("%Y-%m-%d"),
            "CompletedDate": None,
            "ClosedDate": None,
            "Status": "Released",
            "CostCenterID": manufacturing_cost_center,
            "ReleasedByEmployeeID": int(rng.choice(employee_pool)),
            "ClosedByEmployeeID": None,
            "SupplyPlanRecommendationID": int(recommendation.SupplyPlanRecommendationID),
        })
        work_order_operation_rows.extend(operation_rows)
        work_order_operation_schedule_rows.extend(operation_schedule_rows)
        conversion_mapping[int(recommendation.SupplyPlanRecommendationID)] = ("WorkOrder", work_order_id)

    append_rows(context, "WorkOrder", work_order_rows)
    append_rows(context, "WorkOrderOperation", work_order_operation_rows)
    append_rows(context, "WorkOrderOperationSchedule", work_order_operation_schedule_rows)
    update_recommendation_conversion(context, conversion_mapping)
    expire_recommendations(context, expired_recommendation_ids)

    recommendation_ids = pd.to_numeric(
        ordered_recommendations["SupplyPlanRecommendationID"],
        errors="coerce",
    ).astype("Int64")
    converted_recommendation_ids = sorted(int(recommendation_id) for recommendation_id in conversion_mapping)
    expired_recommendation_ids = sorted({int(recommendation_id) for recommendation_id in expired_recommendation_ids})
    converted_rows = ordered_recommendations.loc[
        recommendation_ids.isin(converted_recommendation_ids)
    ].copy()
    expired_rows = ordered_recommendations.loc[
        recommendation_ids.isin(expired_recommendation_ids)
    ].copy()

    return {
        "eligible_planned": len(planned_recommendations),
        "converted": len(conversion_mapping),
        "expired": len(expired_recommendation_ids),
        "converted_recommendation_ids": converted_recommendation_ids,
        "expired_recommendation_ids": expired_recommendation_ids,
        "converted_load_by_work_center": manufacture_recommendation_load_by_work_center(context, converted_rows),
        "expired_load_by_work_center": manufacture_recommendation_load_by_work_center(context, expired_rows),
        "expired_reason_counts": {key: int(value) for key, value in expired_reason_counts.items()},
    }


def seed_opening_manufacturing_pipeline(context: GenerationContext) -> dict[str, float]:
    fiscal_start = pd.Timestamp(context.settings.fiscal_year_start).normalize()
    recommendations = context.tables["SupplyPlanRecommendation"]
    if recommendations.empty:
        return {
            "opening_candidates": 0,
            "opening_wip_seeded": 0,
            "opening_wip_expired": 0,
            "opening_fg_seeded_from_prefiscal": 0.0,
            "opening_fg_gap_units": 0.0,
        }

    release_dates = pd.to_datetime(recommendations["ReleaseByDate"], errors="coerce")
    recommended_quantities = pd.to_numeric(recommendations["RecommendedOrderQuantity"], errors="coerce").fillna(0.0)
    opening_candidates = recommendations[
        recommendations["RecommendationType"].eq("Manufacture")
        & recommendations["RecommendationStatus"].eq("Planned")
        & release_dates.notna()
        & release_dates.lt(fiscal_start)
        & recommended_quantities.gt(0)
    ].copy()
    opening_candidates = opening_candidates.sort_values(
        ["ReleaseByDate", "PriorityCode", "SupplyPlanRecommendationID"]
    ).reset_index(drop=True)

    conversion_state = _convert_manufacture_recommendations_to_work_orders(
        context,
        opening_candidates,
        release_floor=fiscal_start,
    )

    opening_fg_gap_units = 0.0
    opening_fg_seeded_from_prefiscal = 0.0
    opening_inventory_adjustments: dict[tuple[int, int], float] = dict(getattr(context, "_opening_inventory_adjustments", None) or {})
    opening_fg_recommendation_ids: set[int] = set()
    if conversion_state["expired_recommendation_ids"]:
        expired_candidate_ids = {
            int(recommendation_id)
            for recommendation_id in conversion_state["expired_recommendation_ids"]
        }
        expired_candidates = opening_candidates[
            opening_candidates["SupplyPlanRecommendationID"].astype(int).isin(expired_candidate_ids)
        ].copy()
        for row in expired_candidates.itertuples(index=False):
            key = (int(row.ItemID), int(row.WarehouseID))
            opening_inventory_adjustments[key] = round(
                float(opening_inventory_adjustments.get(key, 0.0)) + float(row.RecommendedOrderQuantity),
                2,
            )
            opening_fg_seeded_from_prefiscal += float(row.RecommendedOrderQuantity)
            opening_fg_recommendation_ids.add(int(row.SupplyPlanRecommendationID))

    manufactured_sellable = context.tables["Item"][
        context.tables["Item"]["SupplyMode"].eq("Manufactured")
        & context.tables["Item"]["RevenueAccountID"].notna()
        & context.tables["Item"]["IsActive"].astype(int).eq(1)
        & context.tables["Item"]["LaunchDate"].notna()
    ].copy()
    if not manufactured_sellable.empty:
        opening_inventory = opening_inventory_map(context)
        forecast_lookup = weekly_forecast_map(context)
        seeded_schedule_bounds = work_order_schedule_bounds(context)
        work_orders = context.tables["WorkOrder"]
        first_two_week_cutoff = fiscal_start + pd.Timedelta(days=13)
        seeded_supply_by_item_warehouse: dict[tuple[int, int], float] = defaultdict(float)
        if not work_orders.empty:
            seeded_work_orders = work_orders[
                work_orders["SupplyPlanRecommendationID"].notna()
            ].copy()
            if not seeded_work_orders.empty:
                seeded_ids = {
                    int(recommendation_id)
                    for recommendation_id in opening_candidates["SupplyPlanRecommendationID"].astype(int).tolist()
                }
                seeded_work_orders = seeded_work_orders[
                    seeded_work_orders["SupplyPlanRecommendationID"].astype("Int64").isin(seeded_ids)
                ].copy()
                for row in seeded_work_orders.itertuples(index=False):
                    schedule_bounds = seeded_schedule_bounds.get(int(row.WorkOrderID))
                    if schedule_bounds is None:
                        continue
                    _, schedule_end = schedule_bounds
                    if pd.Timestamp(schedule_end).normalize() <= first_two_week_cutoff:
                        seeded_supply_by_item_warehouse[(int(row.ItemID), int(row.WarehouseID))] += float(row.PlannedQuantity)

        first_week = week_start(fiscal_start)
        second_week = week_start(fiscal_start + pd.Timedelta(days=7))
        for item in manufactured_sellable.sort_values("ItemID").itertuples(index=False):
            ranked_warehouses = primary_warehouse_rank(context, int(item.ItemID))
            if not ranked_warehouses:
                continue
            primary_warehouse_id = int(ranked_warehouses[0])
            first_two_week_forecast = round(
                float(forecast_lookup.get((first_week.strftime("%Y-%m-%d"), int(item.ItemID), primary_warehouse_id), 0.0))
                + float(forecast_lookup.get((second_week.strftime("%Y-%m-%d"), int(item.ItemID), primary_warehouse_id), 0.0)),
                2,
            )
            if first_two_week_forecast <= 0:
                continue
            current_opening = float(opening_inventory.get((int(item.ItemID), primary_warehouse_id), 0.0))
            seeded_supply = float(seeded_supply_by_item_warehouse.get((int(item.ItemID), primary_warehouse_id), 0.0))
            gap_units = qty(max(first_two_week_forecast - current_opening - seeded_supply, 0.0))
            if gap_units <= 0:
                continue
            opening_inventory_adjustments[(int(item.ItemID), primary_warehouse_id)] = round(
                float(opening_inventory_adjustments.get((int(item.ItemID), primary_warehouse_id), 0.0)) + float(gap_units),
                2,
            )
            opening_fg_gap_units += float(gap_units)

    if opening_inventory_adjustments:
        context._opening_inventory_adjustments = opening_inventory_adjustments
        for attribute_name in [
            "_planning_opening_inventory_cache",
            "_planning_opening_inventory_diagnostics_cache",
            "_planning_inventory_position_cache",
            "_o2c_shadow_inventory",
        ]:
            if hasattr(context, attribute_name):
                delattr(context, attribute_name)
    if opening_fg_recommendation_ids:
        cancel_recommendations(context, opening_fg_recommendation_ids)

    state = {
        "opening_candidates": int(conversion_state["eligible_planned"]),
        "opening_wip_seeded": int(conversion_state["converted"]),
        "opening_wip_expired": int(conversion_state["expired"]),
        "opening_fg_seeded_from_prefiscal": round(float(opening_fg_seeded_from_prefiscal), 2),
        "opening_fg_gap_units": round(float(opening_fg_gap_units), 2),
    }
    setattr(context, "_opening_manufacturing_pipeline_state", state)
    LOGGER.info(
        "OPENING PIPELINE | opening_candidates=%s | opening_wip_seeded=%s | opening_wip_expired=%s | opening_fg_seeded_from_prefiscal=%.2f | opening_fg_gap_units=%.2f",
        state["opening_candidates"],
        state["opening_wip_seeded"],
        state["opening_wip_expired"],
        state["opening_fg_seeded_from_prefiscal"],
        state["opening_fg_gap_units"],
    )
    return dict(state)


def work_order_schedule_bounds(context: GenerationContext) -> dict[int, tuple[pd.Timestamp, pd.Timestamp]]:
    cached = getattr(context, "_work_order_schedule_bounds", None)
    if cached is not None:
        return cached

    schedules = context.tables["WorkOrderOperationSchedule"]
    operations = context.tables["WorkOrderOperation"]
    if schedules.empty or operations.empty:
        cached = {}
    else:
        work_order_lookup = operations[["WorkOrderOperationID", "WorkOrderID"]].copy()
        merged = schedules.merge(work_order_lookup, on="WorkOrderOperationID", how="inner").copy()
        bounds = (
            merged.assign(ScheduleDateTS=pd.to_datetime(merged["ScheduleDate"], errors="coerce"))
            .groupby("WorkOrderID")["ScheduleDateTS"]
            .agg(["min", "max"])
        )
        cached = {
            int(row.Index): (pd.Timestamp(row.min), pd.Timestamp(row.max))
            for row in bounds.itertuples()
        }

    setattr(context, "_work_order_schedule_bounds", cached)
    return cached


def work_order_operation_schedule_index_map(context: GenerationContext) -> dict[int, list[int]]:
    cached = getattr(context, "_work_order_operation_schedule_index_map", None)
    if cached is not None:
        return cached

    schedules = context.tables["WorkOrderOperationSchedule"]
    if schedules.empty:
        cached = {}
    else:
        ordered = schedules[["WorkOrderOperationID", "ScheduleDate"]].copy()
        ordered["__row_index"] = ordered.index
        ordered = ordered.sort_values(["WorkOrderOperationID", "ScheduleDate", "__row_index"])
        grouped = ordered.groupby("WorkOrderOperationID")["__row_index"].apply(list)
        cached = {
            int(work_order_operation_id): [int(index) for index in indexes]
            for work_order_operation_id, indexes in grouped.items()
        }

    setattr(context, "_work_order_operation_schedule_index_map", cached)
    return cached


def scheduled_work_order_ids(context: GenerationContext) -> set[int]:
    cached = getattr(context, "_scheduled_work_order_ids_cache", None)
    if cached is not None:
        return cached

    schedule_index = work_order_operation_schedule_index_map(context)
    if not schedule_index:
        cached = set()
    else:
        operations = context.tables["WorkOrderOperation"]
        operation_lookup = (
            operations.set_index("WorkOrderOperationID")["WorkOrderID"].astype(int).to_dict()
            if not operations.empty
            else {}
        )
        cached = {
            int(operation_lookup[int(work_order_operation_id)])
            for work_order_operation_id in schedule_index
            if int(work_order_operation_id) in operation_lookup
        }

    setattr(context, "_scheduled_work_order_ids_cache", cached)
    return cached


def work_order_operation_schedule_by_operation(context: GenerationContext) -> dict[int, pd.DataFrame]:
    schedules = context.tables["WorkOrderOperationSchedule"]
    if schedules.empty:
        return {}
    return {
        int(work_order_operation_id): schedules.loc[indexes].copy().sort_values("ScheduleDate").reset_index(drop=True)
        for work_order_operation_id, indexes in work_order_operation_schedule_index_map(context).items()
    }


def rollback_schedule_usage(context: GenerationContext, schedule_rows: list[dict[str, Any]]) -> None:
    if not schedule_rows:
        return

    usage = schedule_usage_map(context)
    for row in schedule_rows:
        key = (int(row["WorkCenterID"]), str(row["ScheduleDate"]))
        updated_hours = money(float(usage.get(key, 0.0)) - float(row["ScheduledHours"]))
        if updated_hours <= 0:
            usage.pop(key, None)
            continue
        usage[key] = updated_hours


def operation_actual_target_windows(context: GenerationContext, work_order_id: int) -> dict[int, tuple[pd.Timestamp, pd.Timestamp]]:
    cached = getattr(context, "_operation_target_windows", {})
    if int(work_order_id) in cached:
        return cached[int(work_order_id)]

    work_order_operations = work_order_operations_for_work_order(context, int(work_order_id))
    schedule_index_map = work_order_operation_schedule_index_map(context)
    if work_order_operations is None or work_order_operations.empty:
        return {}

    target_windows: dict[int, tuple[pd.Timestamp, pd.Timestamp]] = {}
    prior_end: pd.Timestamp | None = None
    for row in work_order_operations.itertuples(index=False):
        if not schedule_index_map.get(int(row.WorkOrderOperationID)):
            continue
        if pd.isna(row.PlannedStartDate) or pd.isna(row.PlannedEndDate):
            continue

        planned_start = pd.Timestamp(row.PlannedStartDate)
        planned_end = pd.Timestamp(row.PlannedEndDate)
        rng = capacity_rng(context, "operation-actual-window", int(work_order_id), int(row.WorkOrderOperationID))
        actual_start = add_schedulable_days(context, int(row.WorkCenterID), planned_start, int(rng.integers(0, 2)))
        if prior_end is not None and actual_start < prior_end:
            actual_start = next_schedulable_day(context, int(row.WorkCenterID), prior_end)
        actual_end = add_schedulable_days(context, int(row.WorkCenterID), planned_end, int(rng.integers(0, 3)))
        if actual_end < actual_start:
            actual_end = actual_start
        if prior_end is not None and actual_end < prior_end:
            actual_end = next_schedulable_day(context, int(row.WorkCenterID), prior_end)
        target_windows[int(row.WorkOrderOperationID)] = (actual_start, actual_end)
        prior_end = actual_end

    cached[int(work_order_id)] = target_windows
    setattr(context, "_operation_target_windows", cached)
    return target_windows


def sync_work_order_operation_activity(
    context: GenerationContext,
    work_order_id: int,
    month_end: pd.Timestamp,
) -> dict[str, pd.Timestamp | None]:
    work_order_operations = work_order_operations_for_work_order(context, int(work_order_id))
    if work_order_operations.empty:
        return {
            "first_planned_start": None,
            "first_actual_start": None,
            "final_actual_end": None,
            "last_completed_end": None,
        }

    target_windows = operation_actual_target_windows(context, int(work_order_id))
    first_planned_start = pd.to_datetime(work_order_operations["PlannedStartDate"]).min()
    first_actual_start: pd.Timestamp | None = None
    final_actual_end: pd.Timestamp | None = None
    last_completed_end: pd.Timestamp | None = None
    blocked = False
    changed = False

    for row_index, row in work_order_operations.iterrows():
        target_window = target_windows.get(int(row["WorkOrderOperationID"]))
        if target_window is None or blocked:
            context.tables["WorkOrderOperation"].loc[row_index, "Status"] = "Released"
            changed = True
            continue

        actual_start, actual_end = target_window
        if first_actual_start is None:
            first_actual_start = actual_start
        final_actual_end = actual_end

        if actual_end <= pd.Timestamp(month_end):
            context.tables["WorkOrderOperation"].loc[row_index, "ActualStartDate"] = actual_start.strftime("%Y-%m-%d")
            context.tables["WorkOrderOperation"].loc[row_index, "ActualEndDate"] = actual_end.strftime("%Y-%m-%d")
            context.tables["WorkOrderOperation"].loc[row_index, "Status"] = "Completed"
            last_completed_end = actual_end
            changed = True
            continue

        if actual_start <= pd.Timestamp(month_end):
            context.tables["WorkOrderOperation"].loc[row_index, "ActualStartDate"] = actual_start.strftime("%Y-%m-%d")
            context.tables["WorkOrderOperation"].loc[row_index, "ActualEndDate"] = None
            context.tables["WorkOrderOperation"].loc[row_index, "Status"] = "In Progress"
            blocked = True
            changed = True
            continue

        context.tables["WorkOrderOperation"].loc[row_index, "Status"] = "Released"
        blocked = True
        changed = True

    if changed and hasattr(context, "_final_work_order_activity_dates_cache"):
        delattr(context, "_final_work_order_activity_dates_cache")

    return {
        "first_planned_start": first_planned_start,
        "first_actual_start": first_actual_start,
        "final_actual_end": final_actual_end,
        "last_completed_end": last_completed_end,
    }


def generate_month_work_orders_and_requisitions(context: GenerationContext, year: int, month: int) -> None:
    month_start, month_end = month_bounds(year, month)
    manufactured = manufactured_items(context, month_end)
    if manufactured.empty or context.tables["BillOfMaterial"].empty:
        return

    rng = context.rng
    manufacturing_employee_ids_by_date: dict[str, list[int]] = {}

    def manufacturing_employee_ids(release_date: pd.Timestamp) -> list[int]:
        date_key = pd.Timestamp(release_date).strftime("%Y-%m-%d")
        cached = manufacturing_employee_ids_by_date.get(date_key)
        if cached is not None:
            return cached
        employee_ids = employee_ids_for_cost_center(context, "Manufacturing", release_date)
        manufacturing_employee_ids_by_date[date_key] = employee_ids
        return employee_ids

    planned_recommendations = manufacture_recommendations_for_month(context, year, month)
    if not planned_recommendations.empty:
        fiscal_start = pd.Timestamp(context.settings.fiscal_year_start).normalize()
        conversion_state = _convert_manufacture_recommendations_to_work_orders(
            context,
            planned_recommendations,
            release_floor=fiscal_start,
            release_ceiling=month_end,
        )
        remaining_overdue_planned = len(manufacture_recommendations_for_month(context, year, month))
        available_hours_by_work_center = manufacturing_work_center_available_hours_by_code(context, year, month)
        utilization_by_work_center = manufacturing_work_center_utilization_by_code(context, year, month)
        older_completed_not_closed = completed_not_closed_older_than_one_payroll_period_count(context, month_end)
        LOGGER.info(
            "MANUFACTURING CONVERSION | %s-%02d | eligible_planned=%s | converted=%s | expired=%s | remaining_overdue_planned=%s | expired_due_date_infeasible=%s | expired_missing_master_data=%s | conversion_rate=%.4f",
            year,
            month,
            conversion_state["eligible_planned"],
            conversion_state["converted"],
            conversion_state["expired"],
            remaining_overdue_planned,
            conversion_state["expired_reason_counts"]["due_date_infeasible"],
            conversion_state["expired_reason_counts"]["missing_master_data"],
            (
                conversion_state["converted"] / conversion_state["eligible_planned"]
                if conversion_state["eligible_planned"] > 0
                else 0.0
            ),
        )
        LOGGER.info(
            "MANUFACTURING LOAD | %s-%02d | converted_load_assembly=%s | converted_load_cut=%s | converted_load_finish=%s | converted_load_pack=%s | converted_load_qa=%s | expired_load_assembly=%s | expired_load_cut=%s | expired_load_finish=%s | expired_load_pack=%s | expired_load_qa=%s | available_hours_assembly=%s | available_hours_cut=%s | available_hours_finish=%s | available_hours_pack=%s | available_hours_qa=%s | assembly_utilization=%s | cut_utilization=%s | finish_utilization=%s | pack_utilization=%s | qa_utilization=%s | completed_not_closed_older_than_period=%s",
            year,
            month,
            conversion_state["converted_load_by_work_center"]["ASSEMBLY"],
            conversion_state["converted_load_by_work_center"]["CUT"],
            conversion_state["converted_load_by_work_center"]["FINISH"],
            conversion_state["converted_load_by_work_center"]["PACK"],
            conversion_state["converted_load_by_work_center"]["QA"],
            conversion_state["expired_load_by_work_center"]["ASSEMBLY"],
            conversion_state["expired_load_by_work_center"]["CUT"],
            conversion_state["expired_load_by_work_center"]["FINISH"],
            conversion_state["expired_load_by_work_center"]["PACK"],
            conversion_state["expired_load_by_work_center"]["QA"],
            available_hours_by_work_center["ASSEMBLY"],
            available_hours_by_work_center["CUT"],
            available_hours_by_work_center["FINISH"],
            available_hours_by_work_center["PACK"],
            available_hours_by_work_center["QA"],
            utilization_by_work_center["ASSEMBLY"],
            utilization_by_work_center["CUT"],
            utilization_by_work_center["FINISH"],
            utilization_by_work_center["PACK"],
            utilization_by_work_center["QA"],
            older_completed_not_closed,
        )
        return

    shortages = finished_goods_shortage_by_item(context, month_end)
    if not shortages:
        return

    manufacturing_cost_center = cost_center_id(context, "Manufacturing")
    bom_by_parent = bom_lookup(context)
    bom_lines_lookup = bom_lines_by_bom(context)
    routing_by_parent = active_routing_by_item(context)
    material_items = context.tables["Item"].set_index("ItemID").to_dict("index")
    material_inventory = material_inventory_state(context).copy()
    warehouse_list = warehouse_ids(context)
    requisition_rows: list[dict[str, Any]] = []
    work_order_rows: list[dict[str, Any]] = []
    work_order_operation_rows: list[dict[str, Any]] = []
    work_order_operation_schedule_rows: list[dict[str, Any]] = []

    for item in manufactured.sort_values("ItemID").itertuples(index=False):
        shortage = shortages.get(int(item.ItemID))
        bom = bom_by_parent.get(int(item.ItemID))
        routing = routing_by_parent.get(int(item.ItemID))
        if shortage is None or bom is None or routing is None:
            continue

        launch_date = pd.Timestamp(item.LaunchDate) if pd.notna(item.LaunchDate) else month_start
        release_window_start = max(month_start, launch_date)
        if release_window_start > month_end:
            continue
        release_window_end = min(month_end, release_window_start + pd.Timedelta(days=9))
        release_date = random_date_between(rng, release_window_start, release_window_end)
        lead_days = max(int(item.ProductionLeadTimeDays), 1)
        due_date = release_date + pd.Timedelta(days=lead_days)
        if due_date > month_end and rng.random() <= WORK_ORDER_SAME_MONTH_COMPLETION_PROBABILITY:
            due_date = month_end - pd.Timedelta(days=int(rng.integers(0, 3)))
        elif due_date <= month_end and rng.random() > WORK_ORDER_SAME_MONTH_COMPLETION_PROBABILITY:
            due_date = month_end + pd.Timedelta(days=int(rng.integers(3, 15)))

        work_order_id = next_id(context, "WorkOrder")
        warehouse_id = warehouse_list[int((int(item.ItemID) + year + month) % len(warehouse_list))]
        planned_quantity = qty(float(shortage["shortage"]) * rng.uniform(1.00, 1.12))
        work_order_number = format_doc_number("WO", year, work_order_id)
        operation_rows, operation_schedule_rows = build_work_order_operations(
            context,
            work_order_id,
            int(routing["RoutingID"]),
            planned_quantity,
            release_date,
            due_date,
        )
        if not operation_rows or not operation_schedule_rows:
            continue
        work_order_rows.append({
            "WorkOrderID": work_order_id,
            "WorkOrderNumber": work_order_number,
            "ItemID": int(item.ItemID),
            "BOMID": int(bom["BOMID"]),
            "RoutingID": int(routing["RoutingID"]),
            "WarehouseID": int(warehouse_id),
            "PlannedQuantity": planned_quantity,
            "ReleasedDate": release_date.strftime("%Y-%m-%d"),
            "DueDate": due_date.strftime("%Y-%m-%d"),
            "CompletedDate": None,
            "ClosedDate": None,
            "Status": "Released",
            "CostCenterID": manufacturing_cost_center,
            "ReleasedByEmployeeID": int(rng.choice(manufacturing_employee_ids(release_date))),
            "ClosedByEmployeeID": None,
            "SupplyPlanRecommendationID": None,
        })
        work_order_operation_rows.extend(operation_rows)
        work_order_operation_schedule_rows.extend(operation_schedule_rows)

        bom_lines = bom_lines_lookup.get(int(bom["BOMID"]))
        if bom_lines is None or bom_lines.empty:
            continue
        for bom_line in bom_lines.itertuples(index=False):
            component = material_items[int(bom_line.ComponentItemID)]
            required_quantity = qty(planned_quantity * float(bom_line.QuantityPerUnit) * (1 + float(bom_line.ScrapFactorPct)))
            key = (int(bom_line.ComponentItemID), int(warehouse_id))
            available_quantity = qty(material_inventory.get(key, 0.0))
            if available_quantity >= required_quantity:
                material_inventory[key] = qty(available_quantity - required_quantity)
                continue

            shortage_quantity = qty(required_quantity - available_quantity)
            material_inventory[key] = 0.0
            requisition_quantity = qty(shortage_quantity * rng.uniform(*MATERIAL_REQUISITION_BUFFER_FACTOR))
            estimated_unit_cost = money(float(component["StandardCost"]) * rng.uniform(0.98, 1.05))
            requisition_id = next_id(context, "PurchaseRequisition")
            requisition_rows.append({
                "RequisitionID": requisition_id,
                "RequisitionNumber": format_doc_number("PR", year, requisition_id),
                "RequestDate": release_date.strftime("%Y-%m-%d"),
                "RequestedByEmployeeID": int(rng.choice(manufacturing_employee_ids(release_date))),
                "CostCenterID": manufacturing_cost_center,
                "ItemID": int(bom_line.ComponentItemID),
                "Quantity": requisition_quantity,
                "EstimatedUnitCost": estimated_unit_cost,
                "Justification": f"Manufacturing replenishment for {work_order_number}",
                "ApprovedByEmployeeID": approver_id(context, requisition_quantity * estimated_unit_cost, release_date),
                "ApprovedDate": release_date.strftime("%Y-%m-%d"),
                "Status": "Approved",
                "SupplyPlanRecommendationID": None,
            })

    append_rows(context, "WorkOrder", work_order_rows)
    append_rows(context, "WorkOrderOperation", work_order_operation_rows)
    append_rows(context, "WorkOrderOperationSchedule", work_order_operation_schedule_rows)
    append_rows(context, "PurchaseRequisition", requisition_rows)
    LOGGER.info(
        "MANUFACTURING SHORTAGE CONVERSION | %s-%02d | work_orders=%s | requisitions=%s",
        year,
        month,
        len(work_order_rows),
        len(requisition_rows),
    )


def work_orders_due_for_month(context: GenerationContext, year: int, month: int) -> pd.DataFrame:
    work_orders = context.tables["WorkOrder"]
    if work_orders.empty:
        return work_orders.copy()
    _, month_end = month_bounds(year, month)
    remaining = open_work_order_remaining_quantity_map(context)
    candidates = work_orders[
        pd.to_datetime(work_orders["ReleasedDate"]).le(month_end)
        & work_orders["Status"].ne("Closed")
    ].copy()
    candidates["RemainingQuantity"] = candidates["WorkOrderID"].astype(int).map(remaining).fillna(0.0)
    candidates = candidates[candidates["RemainingQuantity"].gt(0)].copy()
    scheduled_ids = scheduled_work_order_ids(context)
    if scheduled_ids:
        candidates = candidates[candidates["WorkOrderID"].astype(int).isin(scheduled_ids)].copy()
    else:
        return candidates.head(0).copy()
    schedule_bounds = work_order_schedule_bounds(context)
    if schedule_bounds:
        candidates["FirstScheduledDate"] = candidates["WorkOrderID"].astype(int).map(
            lambda work_order_id: schedule_bounds.get(int(work_order_id), (pd.NaT, pd.NaT))[0]
        )
        candidates["FinalScheduledDate"] = candidates["WorkOrderID"].astype(int).map(
            lambda work_order_id: schedule_bounds.get(int(work_order_id), (pd.NaT, pd.NaT))[1]
        )
        candidates = candidates[
            candidates["FirstScheduledDate"].notna()
            & pd.to_datetime(candidates["FirstScheduledDate"]).le(month_end)
        ].copy()
    return candidates.sort_values(["DueDate", "ReleasedDate", "WorkOrderID"]).reset_index(drop=True)


def update_work_order_row(
    context: GenerationContext,
    work_order_id: int,
    status: str,
    completed_date: str | None = None,
    closed_date: str | None = None,
    closed_by_employee_id: int | None = None,
) -> None:
    mask = context.tables["WorkOrder"]["WorkOrderID"].astype(int).eq(int(work_order_id))
    context.tables["WorkOrder"].loc[mask, "Status"] = status
    if completed_date is not None:
        context.tables["WorkOrder"].loc[mask, "CompletedDate"] = completed_date
    if closed_date is not None:
        context.tables["WorkOrder"].loc[mask, "ClosedDate"] = closed_date
    if closed_by_employee_id is not None:
        context.tables["WorkOrder"].loc[mask, "ClosedByEmployeeID"] = int(closed_by_employee_id)


def split_quantities(total_quantity: float, event_count: int, rng: np.random.Generator) -> list[float]:
    if event_count <= 1:
        return [qty(total_quantity)]
    if total_quantity <= 0:
        return [0.0 for _ in range(event_count)]

    remaining = qty(total_quantity)
    quantities: list[float] = []
    for event_index in range(event_count - 1):
        remaining_slots = event_count - event_index - 1
        if remaining <= 0:
            quantities.append(0.0)
            continue
        minimum_reserved = 0.01 * remaining_slots
        if remaining <= minimum_reserved:
            quantities.append(0.0)
            continue
        share = rng.uniform(0.40, 0.65) if event_count == 2 else rng.uniform(0.18, 0.52)
        current_quantity = qty(min(remaining - minimum_reserved, remaining * share))
        quantities.append(current_quantity)
        remaining = qty(remaining - current_quantity)

    quantities.append(qty(max(remaining, 0.0)))
    while len(quantities) < event_count:
        quantities.append(0.0)
    return quantities[:event_count]


def work_order_issued_support_quantity_map(context: GenerationContext) -> dict[int, float]:
    issues = context.tables["MaterialIssue"]
    issue_lines = context.tables["MaterialIssueLine"]
    work_orders = context.tables["WorkOrder"]
    if issues.empty or issue_lines.empty or work_orders.empty:
        return {}
    state = getattr(context, "_material_issue_support_state", None)
    if state is None:
        state = {
            "processed_issue_count": 0,
            "processed_issue_line_count": 0,
            "issue_work_order": {},
            "issued_quantities": defaultdict(float),
            "support_quantities": {},
        }

    if int(state["processed_issue_count"]) < len(issues):
        new_issues = issues.iloc[int(state["processed_issue_count"]):]
        issue_work_order: dict[int, int] = state["issue_work_order"]
        for issue in new_issues.itertuples(index=False):
            issue_work_order[int(issue.MaterialIssueID)] = int(issue.WorkOrderID)
        state["processed_issue_count"] = len(issues)

    if int(state["processed_issue_line_count"]) < len(issue_lines):
        issue_work_order = state["issue_work_order"]
        work_order_bom_lookup = work_orders.set_index("WorkOrderID")["BOMID"].astype(int).to_dict()
        bom_lines_lookup = bom_lines_by_bom(context)
        issued_quantities: defaultdict[tuple[int, int], float] = state["issued_quantities"]
        support_quantities: dict[int, float] = state["support_quantities"]
        touched_work_orders: set[int] = set()

        new_issue_lines = issue_lines.iloc[int(state["processed_issue_line_count"]):]
        for line in new_issue_lines.itertuples(index=False):
            work_order_id = issue_work_order.get(int(line.MaterialIssueID))
            if work_order_id is None:
                continue
            issued_quantities[(int(work_order_id), int(line.BOMLineID))] += float(line.QuantityIssued)
            touched_work_orders.add(int(work_order_id))

        for work_order_id in touched_work_orders:
            bom_id = work_order_bom_lookup.get(int(work_order_id))
            bom_lines = bom_lines_lookup.get(int(bom_id)) if bom_id is not None else None
            if bom_lines is None or bom_lines.empty:
                continue
            supported_quantity: float | None = None
            for bom_line in bom_lines.itertuples(index=False):
                required_per_unit = float(bom_line.QuantityPerUnit) * (1 + float(bom_line.ScrapFactorPct))
                if required_per_unit <= 0:
                    continue
                issued_quantity = float(issued_quantities.get((int(work_order_id), int(bom_line.BOMLineID)), 0.0))
                line_support = issued_quantity / required_per_unit
                supported_quantity = line_support if supported_quantity is None else min(supported_quantity, line_support)
            if supported_quantity is not None and supported_quantity > 0:
                support_quantities[int(work_order_id)] = qty(supported_quantity)

        state["processed_issue_line_count"] = len(issue_lines)

    setattr(context, "_material_issue_support_state", state)
    return {int(work_order_id): qty(float(amount)) for work_order_id, amount in state["support_quantities"].items()}


def parse_work_order_component_shortfall_justification(
    justification: str | None,
) -> tuple[int, int] | None:
    text = str(justification or "")
    if not text.startswith(WORK_ORDER_COMPONENT_SHORTFALL_PREFIX):
        return None

    work_order_id: int | None = None
    component_item_id: int | None = None
    for segment in [part.strip() for part in text.split("|")]:
        if segment.startswith("WO="):
            try:
                work_order_id = int(segment.split("=", 1)[1])
            except ValueError:
                return None
        elif segment.startswith("ITEM="):
            try:
                component_item_id = int(segment.split("=", 1)[1])
            except ValueError:
                return None

    if work_order_id is None or component_item_id is None:
        return None
    return work_order_id, component_item_id


def work_order_component_replenishment_outstanding_quantity_map(
    context: GenerationContext,
) -> dict[tuple[int, int], float]:
    requisitions = context.tables["PurchaseRequisition"]
    if requisitions.empty:
        return {}

    purchase_order_lines = context.tables["PurchaseOrderLine"]
    goods_receipt_lines = context.tables["GoodsReceiptLine"]
    received_by_po_line: dict[int, float] = {}
    if not goods_receipt_lines.empty:
        received_by_po_line = (
            goods_receipt_lines.groupby("POLineID")["QuantityReceived"]
            .sum()
            .round(2)
            .to_dict()
        )

    received_by_requisition: defaultdict[int, float] = defaultdict(float)
    if not purchase_order_lines.empty:
        for line in purchase_order_lines.itertuples(index=False):
            if pd.isna(line.RequisitionID):
                continue
            received_by_requisition[int(line.RequisitionID)] += float(
                received_by_po_line.get(int(line.POLineID), 0.0)
            )

    outstanding: defaultdict[tuple[int, int], float] = defaultdict(float)
    for requisition in requisitions.itertuples(index=False):
        shortfall_key = parse_work_order_component_shortfall_justification(
            getattr(requisition, "Justification", None)
        )
        if shortfall_key is None:
            continue
        remaining_quantity = qty(
            max(
                float(requisition.Quantity)
                - float(received_by_requisition.get(int(requisition.RequisitionID), 0.0)),
                0.0,
            )
        )
        if remaining_quantity <= 0:
            continue
        outstanding[(int(shortfall_key[0]), int(shortfall_key[1]))] += remaining_quantity

    return {
        (int(work_order_id), int(component_item_id)): qty(float(quantity))
        for (work_order_id, component_item_id), quantity in outstanding.items()
    }


def payroll_period_for_work_date(context: GenerationContext, work_date: pd.Timestamp | str) -> dict[str, Any] | None:
    timestamp = pd.Timestamp(work_date)
    for period in payroll_period_lookup(context).values():
        period_start = pd.Timestamp(period["PeriodStartDate"])
        period_end = pd.Timestamp(period["PeriodEndDate"])
        if period_start <= timestamp <= period_end:
            return period
    return None


def payroll_period_end_for_date(context: GenerationContext, work_date: pd.Timestamp | str) -> pd.Timestamp | None:
    period = payroll_period_for_work_date(context, work_date)
    if period is None:
        return None
    return pd.Timestamp(period["PeriodEndDate"])


def payroll_period_processing_gate_date(context: GenerationContext, work_date: pd.Timestamp | str) -> pd.Timestamp | None:
    period = payroll_period_for_work_date(context, work_date)
    if period is None:
        return None
    return pd.Timestamp(period["PayDate"])


def latest_direct_labor_activity_dates(context: GenerationContext) -> dict[int, pd.Timestamp]:
    cached = getattr(context, "_latest_direct_labor_activity_dates_cache", None)
    if cached is not None:
        return cached

    dates: dict[int, pd.Timestamp] = {}
    labor_entries = context.tables["LaborTimeEntry"]
    if not labor_entries.empty:
        direct_entries = labor_entries[
            labor_entries["LaborType"].eq("Direct Manufacturing")
            & labor_entries["WorkOrderID"].notna()
            & labor_entries["WorkDate"].notna()
        ]
        for row in direct_entries.itertuples(index=False):
            dates[int(row.WorkOrderID)] = max(
                dates.get(int(row.WorkOrderID), pd.Timestamp.min),
                pd.Timestamp(row.WorkDate),
            )
    setattr(context, "_latest_direct_labor_activity_dates_cache", dates)
    return dates


def completed_not_closed_older_than_one_payroll_period_count(
    context: GenerationContext,
    month_end: pd.Timestamp,
) -> int:
    work_orders = context.tables["WorkOrder"]
    if work_orders.empty:
        return 0
    periods = context.tables["PayrollPeriod"]
    if periods.empty:
        return 0
    relevant_periods = periods[pd.to_datetime(periods["PeriodEndDate"]).le(month_end)].copy()
    if len(relevant_periods) < 2:
        return 0
    prior_period_end = pd.to_datetime(relevant_periods["PeriodEndDate"]).sort_values().iloc[-2]
    completed_not_closed = work_orders[
        work_orders["Status"].eq("Completed")
        & work_orders["CompletedDate"].notna()
    ].copy()
    if completed_not_closed.empty:
        return 0
    return int((pd.to_datetime(completed_not_closed["CompletedDate"]) < prior_period_end).sum())


def released_work_order_backlog_metrics(
    context: GenerationContext,
    month_end: pd.Timestamp,
) -> dict[str, Any]:
    work_orders = context.tables["WorkOrder"]
    work_order_operations = context.tables["WorkOrderOperation"]
    if work_orders.empty:
        return {
            "open_released_work_orders": 0,
            "open_released_no_actual_start": 0,
            "avg_days_release_to_first_sched_open": 0.0,
            "oldest_open_due_date": None,
            "open_due_before_month_end": 0,
            "open_due_before_year_end": 0,
        }

    released = work_orders[work_orders["Status"].eq("Released")].copy()
    if released.empty:
        return {
            "open_released_work_orders": 0,
            "open_released_no_actual_start": 0,
            "avg_days_release_to_first_sched_open": 0.0,
            "oldest_open_due_date": None,
            "open_due_before_month_end": 0,
            "open_due_before_year_end": 0,
        }

    schedule_bounds = work_order_schedule_bounds(context)
    if schedule_bounds:
        released["FirstScheduledDate"] = released["WorkOrderID"].astype(int).map(
            lambda work_order_id: schedule_bounds.get(int(work_order_id), (pd.NaT, pd.NaT))[0]
        )
    else:
        released["FirstScheduledDate"] = pd.NaT

    actual_start_by_work_order: dict[int, pd.Timestamp] = {}
    if not work_order_operations.empty:
        operation_rows = work_order_operations[
            work_order_operations["ActualStartDate"].notna()
        ].copy()
        if not operation_rows.empty:
            operation_rows["ActualStartDateTS"] = pd.to_datetime(operation_rows["ActualStartDate"], errors="coerce")
            actual_start_by_work_order = (
                operation_rows.dropna(subset=["ActualStartDateTS"])
                .groupby("WorkOrderID")["ActualStartDateTS"]
                .min()
                .to_dict()
            )
    released["FirstActualStartDate"] = released["WorkOrderID"].astype(int).map(actual_start_by_work_order)

    released["ReleasedDateTS"] = pd.to_datetime(released["ReleasedDate"], errors="coerce")
    released["DueDateTS"] = pd.to_datetime(released["DueDate"], errors="coerce")
    released["FirstScheduledDateTS"] = pd.to_datetime(released["FirstScheduledDate"], errors="coerce")
    released["FirstActualStartDateTS"] = pd.to_datetime(released["FirstActualStartDate"], errors="coerce")

    scheduled_open = released.dropna(subset=["ReleasedDateTS", "FirstScheduledDateTS"]).copy()
    avg_days_release_to_first_sched = 0.0
    if not scheduled_open.empty:
        avg_days_release_to_first_sched = round(float(
            (
                scheduled_open["FirstScheduledDateTS"] - scheduled_open["ReleasedDateTS"]
            ).dt.days.mean()
        ), 2)

    oldest_open_due_date = None
    due_dates = released["DueDateTS"].dropna()
    if not due_dates.empty:
        oldest_open_due_date = due_dates.min().strftime("%Y-%m-%d")

    fiscal_year_end = pd.Timestamp(context.settings.fiscal_year_end).normalize()
    return {
        "open_released_work_orders": int(len(released)),
        "open_released_no_actual_start": int(released["FirstActualStartDateTS"].isna().sum()),
        "avg_days_release_to_first_sched_open": avg_days_release_to_first_sched,
        "oldest_open_due_date": oldest_open_due_date,
        "open_due_before_month_end": int(released["DueDateTS"].le(month_end).sum()),
        "open_due_before_year_end": int(released["DueDateTS"].le(fiscal_year_end).sum()),
    }


def generate_month_manufacturing_activity(context: GenerationContext, year: int, month: int) -> int:
    candidates = work_orders_due_for_month(context, year, month)
    _, month_end = month_bounds(year, month)
    if candidates.empty:
        work_orders = context.tables["WorkOrder"]
        scheduled_ids = scheduled_work_order_ids(context)
        released_without_schedule = 0
        released_with_schedule = 0
        open_work_orders = 0
        older_completed_not_closed = completed_not_closed_older_than_one_payroll_period_count(context, month_end)
        backlog_metrics = released_work_order_backlog_metrics(context, month_end)
        if not work_orders.empty:
            open_work_orders = int(work_orders["Status"].isin(["Released", "In Progress", "Completed"]).sum())
            released_with_schedule = int(
                (
                    work_orders["Status"].eq("Released")
                    & work_orders["WorkOrderID"].astype(int).isin(scheduled_ids)
                ).sum()
            )
            released_without_schedule = int(
                (
                    work_orders["Status"].eq("Released")
                    & ~work_orders["WorkOrderID"].astype(int).isin(scheduled_ids)
                ).sum()
            )
        LOGGER.info(
            "MANUFACTURING ACTIVITY | %s-%02d | candidates=0 | scheduled_candidates=0 | open_work_orders=%s | released_with_schedule=%s | released_without_schedule=%s | completed_not_closed_older_than_period=%s | replenishment_requisitions_created=0 | issues_created=0 | completions_created=0",
            year,
            month,
            open_work_orders,
            released_with_schedule,
            released_without_schedule,
            older_completed_not_closed,
        )
        LOGGER.info(
            "MANUFACTURING BACKLOG | %s-%02d | open_released_work_orders=%s | open_released_no_actual_start=%s | avg_days_release_to_first_sched_open=%s | oldest_open_due_date=%s | open_due_before_month_end=%s | open_due_before_year_end=%s",
            year,
            month,
            backlog_metrics["open_released_work_orders"],
            backlog_metrics["open_released_no_actual_start"],
            backlog_metrics["avg_days_release_to_first_sched_open"],
            backlog_metrics["oldest_open_due_date"] or "None",
            backlog_metrics["open_due_before_month_end"],
            backlog_metrics["open_due_before_year_end"],
        )
        return 0

    rng = context.rng
    month_start, month_end = month_bounds(year, month)
    sync_material_inventory_receipts(context, year, month)
    material_inventory = material_inventory_state(context)
    items = context.tables["Item"].set_index("ItemID").to_dict("index")
    bom_lines_lookup = bom_lines_by_bom(context)
    completed_quantities = work_order_completed_quantity_map(context)
    issued_support_quantities = work_order_issued_support_quantity_map(context)
    replenishment_outstanding = work_order_component_replenishment_outstanding_quantity_map(context)
    manufacturing_cost_center = cost_center_id(context, "Manufacturing")
    existing_issue_counts = (
        context.tables["MaterialIssue"].groupby("WorkOrderID").size().to_dict()
        if not context.tables["MaterialIssue"].empty
        else {}
    )
    issued_quantity_by_work_order_bom_line: defaultdict[tuple[int, int], float] = defaultdict(float)
    if not context.tables["MaterialIssueLine"].empty and not context.tables["MaterialIssue"].empty:
        issued_component_frame = context.tables["MaterialIssueLine"].merge(
            context.tables["MaterialIssue"][["MaterialIssueID", "WorkOrderID"]],
            on="MaterialIssueID",
            how="left",
        )
        for row in issued_component_frame.itertuples(index=False):
            issued_quantity_by_work_order_bom_line[(int(row.WorkOrderID), int(row.BOMLineID))] += float(row.QuantityIssued)
    issue_headers: list[dict[str, Any]] = []
    issue_lines: list[dict[str, Any]] = []
    completion_headers: list[dict[str, Any]] = []
    completion_lines: list[dict[str, Any]] = []
    replenishment_requisition_rows: list[dict[str, Any]] = []

    for work_order in candidates.itertuples(index=False):
        work_order_id = int(work_order.WorkOrderID)
        remaining_quantity = qty(float(work_order.RemainingQuantity))
        if remaining_quantity <= 0:
            continue

        bom_lines = bom_lines_lookup.get(int(work_order.BOMID))
        if bom_lines is None or bom_lines.empty:
            continue

        first_planned_start = None
        if pd.notna(work_order.FirstScheduledDate):
            first_planned_start = pd.Timestamp(work_order.FirstScheduledDate)
        if first_planned_start is None or first_planned_start > month_end:
            update_work_order_row(context, work_order_id, "Released")
            continue

        issuable_quantity = remaining_quantity
        for bom_line in bom_lines.itertuples(index=False):
            required_per_unit = float(bom_line.QuantityPerUnit) * (1 + float(bom_line.ScrapFactorPct))
            available_quantity = float(
                material_inventory.get((int(bom_line.ComponentItemID), int(work_order.WarehouseID)), 0.0)
            )
            supported_quantity = available_quantity / required_per_unit if required_per_unit > 0 else remaining_quantity
            issuable_quantity = min(issuable_quantity, supported_quantity)
        issuable_quantity = qty(issuable_quantity)

        already_supported_quantity = qty(
            max(
                float(issued_support_quantities.get(work_order_id, 0.0))
                - float(completed_quantities.get(work_order_id, 0.0)),
                0.0,
            )
        )
        additional_issuable_quantity = qty(max(float(issuable_quantity) - float(already_supported_quantity), 0.0))
        unsupported_parent_quantity = qty(max(float(remaining_quantity) - float(already_supported_quantity), 0.0))

        if unsupported_parent_quantity > 0:
            request_date = max(month_start, first_planned_start)
            requestors = employee_ids_for_cost_center(context, "Manufacturing", request_date)
            for bom_line in bom_lines.itertuples(index=False):
                required_per_unit = float(bom_line.QuantityPerUnit) * (1 + float(bom_line.ScrapFactorPct))
                if required_per_unit <= 0:
                    continue
                key = (int(bom_line.ComponentItemID), int(work_order.WarehouseID))
                available_quantity = qty(float(material_inventory.get(key, 0.0)))
                outstanding_quantity = qty(
                    float(
                        replenishment_outstanding.get(
                            (work_order_id, int(bom_line.ComponentItemID)),
                            0.0,
                        )
                    )
                )
                required_quantity = qty(float(unsupported_parent_quantity) * required_per_unit)
                shortage_quantity = qty(
                    max(
                        float(required_quantity) - float(available_quantity) - float(outstanding_quantity),
                        0.0,
                    )
                )
                if shortage_quantity <= 0:
                    continue
                component = items[int(bom_line.ComponentItemID)]
                requisition_quantity = qty(shortage_quantity * rng.uniform(*MATERIAL_REQUISITION_BUFFER_FACTOR))
                estimated_unit_cost = money(float(component["StandardCost"]) * rng.uniform(0.98, 1.05))
                requisition_id = next_id(context, "PurchaseRequisition")
                replenishment_requisition_rows.append({
                    "RequisitionID": requisition_id,
                    "RequisitionNumber": format_doc_number("PR", year, requisition_id),
                    "RequestDate": request_date.strftime("%Y-%m-%d"),
                    "RequestedByEmployeeID": int(rng.choice(requestors)),
                    "CostCenterID": manufacturing_cost_center,
                    "ItemID": int(bom_line.ComponentItemID),
                    "Quantity": requisition_quantity,
                    "EstimatedUnitCost": estimated_unit_cost,
                    "Justification": f"{WORK_ORDER_COMPONENT_SHORTFALL_PREFIX} | WO={work_order_id} | ITEM={int(bom_line.ComponentItemID)}",
                    "ApprovedByEmployeeID": approver_id(context, requisition_quantity * estimated_unit_cost, request_date),
                    "ApprovedDate": request_date.strftime("%Y-%m-%d"),
                    "Status": "Approved",
                    "SupplyPlanRecommendationID": None,
                })
                replenishment_outstanding[(work_order_id, int(bom_line.ComponentItemID))] = qty(
                    float(outstanding_quantity) + float(requisition_quantity)
                )

        if additional_issuable_quantity > 0:
            issue_event_count = choose_count(rng, ISSUE_EVENT_COUNT_PROBABILITIES)
            issue_window_start = max(month_start, first_planned_start)
            issue_window_end = min(month_end, pd.Timestamp(work_order.FinalScheduledDate))
            if issue_window_end < issue_window_start:
                issue_window_end = issue_window_start
            issue_dates = sorted(
                random_date_between(rng, issue_window_start, issue_window_end)
                for _ in range(issue_event_count)
            )
            issue_quantities_by_line = {
                int(bom_line.BOMLineID): split_quantities(
                    qty(
                        additional_issuable_quantity
                        * float(bom_line.QuantityPerUnit)
                        * (1 + float(bom_line.ScrapFactorPct))
                        * rng.uniform(*ISSUE_FACTOR_RANGE)
                    ),
                    issue_event_count,
                    rng,
                )
                for bom_line in bom_lines.itertuples(index=False)
            }

            issue_line_number_by_header: dict[int, int] = {}
            for event_index, issue_date in enumerate(issue_dates):
                material_issue_id = next_id(context, "MaterialIssue")
                issue_headers.append({
                    "MaterialIssueID": material_issue_id,
                    "IssueNumber": format_doc_number("MI", year, material_issue_id),
                    "WorkOrderID": work_order_id,
                    "IssueDate": issue_date.strftime("%Y-%m-%d"),
                    "WarehouseID": int(work_order.WarehouseID),
                    "IssuedByEmployeeID": int(rng.choice(employee_ids_for_cost_center(context, "Manufacturing", issue_date))),
                    "Status": "Issued",
                })
                issue_line_number_by_header[material_issue_id] = 1

                for bom_line in bom_lines.itertuples(index=False):
                    issue_quantity = qty(issue_quantities_by_line[int(bom_line.BOMLineID)][event_index])
                    if issue_quantity <= 0:
                        continue
                    key = (int(bom_line.ComponentItemID), int(work_order.WarehouseID))
                    available_quantity = qty(float(material_inventory.get(key, 0.0)))
                    line_allowed_quantity = qty(
                        float(work_order.PlannedQuantity)
                        * float(bom_line.QuantityPerUnit)
                        * (1 + float(bom_line.ScrapFactorPct))
                        * 1.10
                    )
                    remaining_line_allowance = qty(
                        max(
                            float(line_allowed_quantity)
                            - float(issued_quantity_by_work_order_bom_line.get((work_order_id, int(bom_line.BOMLineID)), 0.0)),
                            0.0,
                        )
                    )
                    issue_quantity = min(issue_quantity, remaining_line_allowance)
                    issue_quantity = min(issue_quantity, available_quantity)
                    if issue_quantity <= 0:
                        continue
                    material_inventory[key] = qty(
                        max(float(material_inventory.get(key, 0.0)) - float(issue_quantity), 0.0)
                    )
                    issued_quantity_by_work_order_bom_line[(work_order_id, int(bom_line.BOMLineID))] = qty(
                        float(issued_quantity_by_work_order_bom_line.get((work_order_id, int(bom_line.BOMLineID)), 0.0))
                        + float(issue_quantity)
                    )
                    component = items[int(bom_line.ComponentItemID)]
                    issue_lines.append({
                        "MaterialIssueLineID": next_id(context, "MaterialIssueLine"),
                        "MaterialIssueID": material_issue_id,
                        "BOMLineID": int(bom_line.BOMLineID),
                        "LineNumber": issue_line_number_by_header[material_issue_id],
                        "ItemID": int(bom_line.ComponentItemID),
                        "QuantityIssued": issue_quantity,
                        "ExtendedStandardCost": money(issue_quantity * float(component["StandardCost"])),
                    })
                    issue_line_number_by_header[material_issue_id] += 1

            existing_issue_counts[work_order_id] = int(existing_issue_counts.get(work_order_id, 0)) + issue_event_count
            issued_support_quantities[work_order_id] = qty(
                float(issued_support_quantities.get(work_order_id, 0.0)) + float(additional_issuable_quantity)
            )

        if qty(max(float(issued_support_quantities.get(work_order_id, 0.0)) - float(completed_quantities.get(work_order_id, 0.0)), 0.0)) <= 0:
            update_work_order_row(context, work_order_id, "Released")
            continue

        schedule_state = sync_work_order_operation_activity(context, work_order_id, month_end)
        first_actual_start = schedule_state["first_actual_start"]
        final_actual_end = schedule_state["final_actual_end"]
        last_completed_end = schedule_state["last_completed_end"]

        if first_actual_start is None or first_actual_start > month_end:
            update_work_order_row(context, work_order_id, "Released")
            continue

        if final_actual_end is None or pd.Timestamp(final_actual_end) > month_end:
            update_work_order_row(context, work_order_id, "In Progress")
            continue

        completion_quantity = qty(
            min(
                remaining_quantity,
                max(float(issued_support_quantities.get(work_order_id, 0.0)) - float(completed_quantities.get(work_order_id, 0.0)), 0.0),
            )
        )
        if completion_quantity <= 0:
            update_work_order_row(context, work_order_id, "In Progress")
            continue

        completion_event_count = choose_count(rng, COMPLETION_EVENT_COUNT_PROBABILITIES)
        completion_window_start = max(month_start, pd.Timestamp(final_actual_end))
        completion_window_end = max(completion_window_start, min(month_end, pd.Timestamp(final_actual_end) + pd.Timedelta(days=3)))
        completion_dates = sorted(
            random_date_between(rng, completion_window_start, completion_window_end)
            for _ in range(completion_event_count)
        )
        completion_quantities = split_quantities(completion_quantity, completion_event_count, rng)
        item = items[int(work_order.ItemID)]
        standard_material_unit = standard_material_unit_cost(context, int(work_order.BOMID))

        for completion_date, completion_qty in zip(completion_dates, completion_quantities):
            if completion_qty <= 0:
                continue
            completion_id = next_id(context, "ProductionCompletion")
            completion_headers.append({
                "ProductionCompletionID": completion_id,
                "CompletionNumber": format_doc_number("PC", year, completion_id),
                "WorkOrderID": work_order_id,
                "CompletionDate": completion_date.strftime("%Y-%m-%d"),
                "WarehouseID": int(work_order.WarehouseID),
                "ReceivedByEmployeeID": int(rng.choice(employee_ids_for_cost_center(context, "Manufacturing", completion_date))),
                "Status": "Completed",
            })
            standard_material_cost = money(completion_qty * standard_material_unit)
            standard_direct_labor_cost = money(completion_qty * float(item["StandardDirectLaborCost"]))
            standard_variable_overhead_cost = money(completion_qty * float(item["StandardVariableOverheadCost"]))
            standard_fixed_overhead_cost = money(completion_qty * float(item["StandardFixedOverheadCost"]))
            standard_conversion_cost = money(
                standard_direct_labor_cost
                + standard_variable_overhead_cost
                + standard_fixed_overhead_cost
            )
            total_cost = money(standard_material_cost + standard_conversion_cost)
            completion_lines.append({
                "ProductionCompletionLineID": next_id(context, "ProductionCompletionLine"),
                "ProductionCompletionID": completion_id,
                "LineNumber": 1,
                "ItemID": int(work_order.ItemID),
                "QuantityCompleted": completion_qty,
                "ExtendedStandardMaterialCost": standard_material_cost,
                "ExtendedStandardDirectLaborCost": standard_direct_labor_cost,
                "ExtendedStandardVariableOverheadCost": standard_variable_overhead_cost,
                "ExtendedStandardFixedOverheadCost": standard_fixed_overhead_cost,
                "ExtendedStandardConversionCost": standard_conversion_cost,
                "ExtendedStandardTotalCost": total_cost,
            })

        completed_total = qty(float(completed_quantities.get(work_order_id, 0.0)) + sum(completion_quantities))
        if completed_total >= qty(float(work_order.PlannedQuantity)):
            update_work_order_row(
                context,
                work_order_id,
                "Completed",
                completed_date=completion_dates[-1].strftime("%Y-%m-%d"),
            )
        else:
            update_work_order_row(context, work_order_id, "In Progress")

    append_rows(context, "PurchaseRequisition", replenishment_requisition_rows)
    append_rows(context, "MaterialIssue", issue_headers)
    append_rows(context, "MaterialIssueLine", issue_lines)
    append_rows(context, "ProductionCompletion", completion_headers)
    append_rows(context, "ProductionCompletionLine", completion_lines)
    work_orders = context.tables["WorkOrder"]
    scheduled_ids = scheduled_work_order_ids(context)
    released_with_schedule = int(
        (
            work_orders["Status"].eq("Released")
            & work_orders["WorkOrderID"].astype(int).isin(scheduled_ids)
        ).sum()
    ) if not work_orders.empty else 0
    released_without_schedule = int(
        (
            work_orders["Status"].eq("Released")
            & ~work_orders["WorkOrderID"].astype(int).isin(scheduled_ids)
        ).sum()
    ) if not work_orders.empty else 0
    open_work_orders = int(work_orders["Status"].isin(["Released", "In Progress", "Completed"]).sum()) if not work_orders.empty else 0
    older_completed_not_closed = completed_not_closed_older_than_one_payroll_period_count(context, month_end)
    backlog_metrics = released_work_order_backlog_metrics(context, month_end)
    LOGGER.info(
        "MANUFACTURING ACTIVITY | %s-%02d | candidates=%s | scheduled_candidates=%s | open_work_orders=%s | released_with_schedule=%s | released_without_schedule=%s | completed_not_closed_older_than_period=%s | replenishment_requisitions_created=%s | issues_created=%s | completions_created=%s",
        year,
        month,
        len(candidates),
        len(candidates),
        open_work_orders,
        released_with_schedule,
        released_without_schedule,
        older_completed_not_closed,
        len(replenishment_requisition_rows),
        len(issue_headers),
        len(completion_headers),
    )
    LOGGER.info(
        "MANUFACTURING BACKLOG | %s-%02d | open_released_work_orders=%s | open_released_no_actual_start=%s | avg_days_release_to_first_sched_open=%s | oldest_open_due_date=%s | open_due_before_month_end=%s | open_due_before_year_end=%s",
        year,
        month,
        backlog_metrics["open_released_work_orders"],
        backlog_metrics["open_released_no_actual_start"],
        backlog_metrics["avg_days_release_to_first_sched_open"],
        backlog_metrics["oldest_open_due_date"] or "None",
        backlog_metrics["open_due_before_month_end"],
        backlog_metrics["open_due_before_year_end"],
    )
    return len(replenishment_requisition_rows)


def final_work_order_activity_dates(context: GenerationContext) -> dict[int, pd.Timestamp]:
    cached = getattr(context, "_final_work_order_activity_dates_cache", None)
    if cached is not None:
        return cached

    final_dates: dict[int, pd.Timestamp] = {}
    issues = context.tables["MaterialIssue"]
    completions = context.tables["ProductionCompletion"]
    operations = context.tables["WorkOrderOperation"]
    labor_entries = context.tables["LaborTimeEntry"]
    for issue in issues.itertuples(index=False):
        final_dates[int(issue.WorkOrderID)] = max(
            final_dates.get(int(issue.WorkOrderID), pd.Timestamp.min),
            pd.Timestamp(issue.IssueDate),
        )
    for completion in completions.itertuples(index=False):
        final_dates[int(completion.WorkOrderID)] = max(
            final_dates.get(int(completion.WorkOrderID), pd.Timestamp.min),
            pd.Timestamp(completion.CompletionDate),
        )
    for operation in operations.itertuples(index=False):
        if pd.notna(operation.ActualEndDate):
            final_dates[int(operation.WorkOrderID)] = max(
                final_dates.get(int(operation.WorkOrderID), pd.Timestamp.min),
                pd.Timestamp(operation.ActualEndDate),
            )
    for labor_entry in labor_entries.itertuples(index=False):
        if pd.isna(labor_entry.WorkOrderID) or pd.isna(labor_entry.WorkDate):
            continue
        final_dates[int(labor_entry.WorkOrderID)] = max(
            final_dates.get(int(labor_entry.WorkOrderID), pd.Timestamp.min),
            pd.Timestamp(labor_entry.WorkDate),
        )
    setattr(context, "_final_work_order_activity_dates_cache", final_dates)
    return final_dates


def close_eligible_work_orders(context: GenerationContext, year: int, month: int) -> None:
    work_orders = context.tables["WorkOrder"]
    if work_orders.empty:
        return

    month_start, month_end = month_bounds(year, month)
    completed_map = work_order_completed_quantity_map(context)
    issue_cost_map = work_order_material_issue_cost_map(context)
    standard_material_map = work_order_standard_material_cost_map(context)
    standard_direct_labor_map = work_order_standard_direct_labor_cost_map(context)
    standard_overhead_map = work_order_standard_overhead_cost_map(context)
    actual_direct_labor_map = labor_time_direct_cost_by_work_order(context)
    actual_overhead_map = work_order_overhead_cost_map(context)
    activity_dates = final_work_order_activity_dates(context)
    direct_labor_dates = latest_direct_labor_activity_dates(context)
    close_rows: list[dict[str, Any]] = []

    for work_order in work_orders.sort_values("WorkOrderID").itertuples(index=False):
        if str(work_order.Status) == "Closed":
            continue
        if pd.isna(work_order.CompletedDate):
            continue
        completed_quantity = float(completed_map.get(int(work_order.WorkOrderID), 0.0))
        if round(completed_quantity, 2) < round(float(work_order.PlannedQuantity), 2):
            continue

        completed_date = pd.Timestamp(work_order.CompletedDate)
        if completed_date > month_end:
            continue
        if int(work_order.WorkOrderID) not in actual_direct_labor_map:
            continue

        activity_date = max(activity_dates.get(int(work_order.WorkOrderID), completed_date), completed_date)
        direct_labor_date = direct_labor_dates.get(int(work_order.WorkOrderID))
        if direct_labor_date is not None:
            activity_date = max(activity_date, direct_labor_date)
        payroll_gate_date = payroll_period_processing_gate_date(context, activity_date)
        if payroll_gate_date is not None and payroll_gate_date > month_end:
            continue
        if direct_labor_date is None:
            completion_payroll_gate = payroll_period_processing_gate_date(context, completed_date)
            if completion_payroll_gate is not None and completion_payroll_gate > month_end:
                continue
        payroll_period_end = payroll_period_end_for_date(context, activity_date)
        close_anchor_date = max(activity_date, payroll_period_end) if payroll_period_end is not None else activity_date
        close_date = min(month_end, next_business_day(close_anchor_date + pd.Timedelta(days=2)))
        if close_date < month_start:
            close_date = month_start

        material_variance = money(
            float(issue_cost_map.get(int(work_order.WorkOrderID), 0.0))
            - float(standard_material_map.get(int(work_order.WorkOrderID), 0.0))
        )
        direct_labor_variance = money(
            float(actual_direct_labor_map.get(int(work_order.WorkOrderID), 0.0))
            - float(standard_direct_labor_map.get(int(work_order.WorkOrderID), 0.0))
        )
        overhead_variance = money(
            float(actual_overhead_map.get(int(work_order.WorkOrderID), 0.0))
            - float(standard_overhead_map.get(int(work_order.WorkOrderID), 0.0))
        )
        conversion_variance = money(direct_labor_variance + overhead_variance)
        close_rows.append({
            "WorkOrderCloseID": next_id(context, "WorkOrderClose"),
            "WorkOrderID": int(work_order.WorkOrderID),
            "CloseDate": close_date.strftime("%Y-%m-%d"),
            "MaterialVarianceAmount": material_variance,
            "DirectLaborVarianceAmount": direct_labor_variance,
            "OverheadVarianceAmount": overhead_variance,
            "ConversionVarianceAmount": conversion_variance,
            "TotalVarianceAmount": money(material_variance + conversion_variance),
            "Status": "Closed",
            "ClosedByEmployeeID": int(
                employee_ids_for_cost_center(context, "Manufacturing", close_date)[
                    (int(work_order.WorkOrderID) + year + month)
                    % len(employee_ids_for_cost_center(context, "Manufacturing", close_date))
                ]
            ),
        })
        update_work_order_row(
            context,
            int(work_order.WorkOrderID),
            "Closed",
            completed_date=completed_date.strftime("%Y-%m-%d"),
            closed_date=close_date.strftime("%Y-%m-%d"),
            closed_by_employee_id=int(close_rows[-1]["ClosedByEmployeeID"]),
        )

    append_rows(context, "WorkOrderClose", close_rows)
