from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.state_cache import drop_context_attributes, get_or_build_cache
from greenfield_dataset.settings import GenerationContext
from greenfield_dataset.utils import format_doc_number, money, next_id, qty


DIRECT_MANUFACTURING_TITLES = {
    "Assembler",
    "Machine Operator",
    "Quality Technician",
}

INDIRECT_MANUFACTURING_TITLES = {
    "Production Manager",
    "Production Supervisor",
    "Production Planner",
}

PAYROLL_PAYMENT_METHODS = ["ACH", "Direct Deposit"]
PAYROLL_PERIOD_LENGTH_DAYS = 14
PAYROLL_PERIOD_PAYDATE_LAG_DAYS = 5
PAYROLL_REMITS_DAYS = {
    "Employee Tax Withholding": 7,
    "Employer Payroll Tax": 9,
    "Benefits and Other Deductions": 12,
}
DIRECT_LABOR_FACTOR_RANGE = (0.95, 1.06)
FACTORY_OVERHEAD_FACTOR_RANGE = (0.92, 1.08)
HOURLY_PERIOD_HOURS_RANGE = (75.0, 84.0)
HOURLY_PERIOD_OVERTIME_RANGE = (0.0, 6.0)
DIRECT_WORKER_SPLIT_OPTIONS = ((1, 0.58), (2, 0.34), (3, 0.08))
DIRECT_OPERATION_WEIGHT = {
    "ASSEMBLY": 1.40,
    "FINISH": 1.20,
    "QA": 1.00,
    "CUT": 0.85,
    "PACK": 0.45,
}
EMPLOYEE_TAX_WITHHOLDING_RANGE = (0.11, 0.16)
BENEFITS_DEDUCTION_RANGE = (0.02, 0.05)
EMPLOYER_BENEFIT_RATE_RANGE = (0.04, 0.08)
EMPLOYER_PAYROLL_TAX_RATE = 0.0765
SHIFT_DEFINITION_ROWS = (
    {
        "ShiftCode": "MFG-DAY",
        "ShiftName": "Manufacturing Day Shift",
        "Department": "Manufacturing",
        "WorkCenterCode": "ASSEMBLY",
        "StartTime": "07:00:00",
        "EndTime": "15:30:00",
        "StandardBreakMinutes": 30,
        "ShiftType": "Day",
        "IsOvernight": 0,
    },
    {
        "ShiftCode": "MFG-LATE",
        "ShiftName": "Manufacturing Late Shift",
        "Department": "Manufacturing",
        "WorkCenterCode": "ASSEMBLY",
        "StartTime": "15:00:00",
        "EndTime": "23:30:00",
        "StandardBreakMinutes": 30,
        "ShiftType": "Late",
        "IsOvernight": 0,
    },
    {
        "ShiftCode": "WH-DAY",
        "ShiftName": "Warehouse Day Shift",
        "Department": "Warehouse",
        "WorkCenterCode": None,
        "StartTime": "08:00:00",
        "EndTime": "16:30:00",
        "StandardBreakMinutes": 30,
        "ShiftType": "Day",
        "IsOvernight": 0,
    },
    {
        "ShiftCode": "CS-DAY",
        "ShiftName": "Customer Service Day Shift",
        "Department": "Customer Service",
        "WorkCenterCode": None,
        "StartTime": "08:30:00",
        "EndTime": "17:00:00",
        "StandardBreakMinutes": 30,
        "ShiftType": "Day",
        "IsOvernight": 0,
    },
)
JOB_TITLE_SHIFT_CODE = {
    "Assembler": "MFG-DAY",
    "Machine Operator": "MFG-LATE",
    "Quality Technician": "MFG-DAY",
    "Shipping Clerk": "WH-DAY",
    "Inventory Specialist": "WH-DAY",
    "Customer Service Representative": "CS-DAY",
    "Administrative Specialist": "CS-DAY",
}
JOB_TITLE_WORK_CENTER_CODES = {
    "Assembler": ("ASSEMBLY", "FINISH", "PACK"),
    "Machine Operator": ("CUT", "ASSEMBLY"),
    "Quality Technician": ("QA", "FINISH", "ASSEMBLY"),
}
DIRECT_WORK_CENTER_TITLE_PREFERENCE = {
    "ASSEMBLY": ("Assembler", "Machine Operator", "Quality Technician"),
    "CUT": ("Machine Operator", "Assembler", "Quality Technician"),
    "FINISH": ("Assembler", "Quality Technician", "Machine Operator"),
    "PACK": ("Assembler", "Machine Operator", "Quality Technician"),
    "QA": ("Quality Technician", "Assembler", "Machine Operator"),
}
SHIFT_CLOCK_IN_VARIANCE_MINUTES = (-12, 10)
SHIFT_CLOCK_OUT_VARIANCE_MINUTES = (-8, 18)
SHIFT_OFF_TOLERANCE_MINUTES = 45
STANDARD_SHIFT_REGULAR_HOURS_RANGE = (7.5, 8.25)
STANDARD_SHIFT_OVERTIME_RANGE = (0.0, 2.25)
DIRECT_SUPPORT_TOPUP_HOURS_RANGE = (74.0, 82.0)
MAX_CLOCK_HOURS_PER_DAY = 11.5
TIMECLOCK_APPROVED_STATUS = "Approved"


def append_rows(context: GenerationContext, table_name: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    new_rows = pd.DataFrame(rows, columns=TABLE_COLUMNS[table_name])
    context.tables[table_name] = pd.concat([context.tables[table_name], new_rows], ignore_index=True)
    invalidate_payroll_caches(context, table_name)


def invalidate_payroll_caches(context: GenerationContext, table_name: str) -> None:
    cache_keys_by_table = {
        "PayrollPeriod": [
            "_payroll_period_lookup_cache",
            "_payroll_period_month_lookup_cache",
            "_shift_assignment_map_cache",
        ],
        "ShiftDefinition": ["_shift_definition_by_code_cache", "_shift_definition_lookup_cache"],
        "EmployeeShiftAssignment": ["_shift_assignment_map_cache"],
        "TimeClockEntry": [
            "_time_clock_entries_cache",
            "_time_clock_entry_lookup_cache",
            "_approved_time_clock_hours_by_employee_period_cache",
        ],
        "LaborTimeEntry": [
            "_labor_time_entries_cache",
            "_labor_time_direct_cost_by_work_order_cache",
            "_direct_labor_cost_by_month_work_order_cache",
            "_work_order_overhead_cost_map_cache",
            "_approved_time_clock_hours_by_employee_period_cache",
        ],
        "PayrollRegister": [
            "_payroll_register_lookup_cache",
            "_payroll_register_lines_with_headers_cache",
            "_work_order_overhead_cost_map_cache",
        ],
        "PayrollRegisterLine": [
            "_payroll_register_lines_cache",
            "_payroll_register_lines_with_headers_cache",
            "_work_order_overhead_cost_map_cache",
        ],
        "PayrollLiabilityRemittance": ["_payroll_liability_remitted_amounts_cache"],
    }
    drop_context_attributes(context, cache_keys_by_table.get(table_name, []))


def month_bounds(year: int, month: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(year=year, month=month, day=1)
    end = start + pd.offsets.MonthEnd(1)
    return start, end


def next_business_day(timestamp: pd.Timestamp) -> pd.Timestamp:
    candidate = pd.Timestamp(timestamp)
    while candidate.day_name() in {"Saturday", "Sunday"}:
        candidate = candidate + pd.Timedelta(days=1)
    return candidate


def stable_rng(context: GenerationContext, *parts: object) -> np.random.Generator:
    seed = context.settings.random_seed
    for part in parts:
        seed = (seed * 31 + sum(ord(char) for char in str(part))) % (2**32 - 1)
    return np.random.default_rng(seed)


def choose_count(rng: np.random.Generator, options: tuple[tuple[int, float], ...]) -> int:
    counts = np.array([count for count, _ in options], dtype=int)
    probabilities = np.array([probability for _, probability in options], dtype=float)
    probabilities = probabilities / probabilities.sum()
    return int(rng.choice(counts, p=probabilities))


def accounting_manager_id(context: GenerationContext) -> int:
    employees = context.tables["Employee"]
    for title in ["Accounting Manager", "Controller", "Chief Financial Officer"]:
        matches = employees.loc[employees["JobTitle"].eq(title), "EmployeeID"]
        if not matches.empty:
            return int(matches.iloc[0])
    return int(employees.iloc[0]["EmployeeID"])


def payroll_period_lookup(context: GenerationContext) -> dict[int, dict[str, Any]]:
    def builder() -> dict[int, dict[str, Any]]:
        periods = context.tables["PayrollPeriod"]
        if periods.empty:
            return {}
        return periods.set_index("PayrollPeriodID").to_dict("index")

    return get_or_build_cache(context, "_payroll_period_lookup_cache", builder)


def payroll_period_month(period: dict[str, Any]) -> tuple[int, int]:
    pay_date = pd.Timestamp(period["PayDate"])
    return int(pay_date.year), int(pay_date.month)


def growth_factor_for_year(year: int) -> float:
    return 1.0 + max(int(year) - 2026, 0) * 0.035


def implied_hourly_rate(employee: pd.Series | dict[str, Any], fiscal_year: int) -> float:
    growth_factor = growth_factor_for_year(fiscal_year)
    pay_class = str(employee["PayClass"])
    if pay_class == "Hourly":
        return money(float(employee["BaseHourlyRate"]) * growth_factor)
    annual_salary = float(employee["BaseAnnualSalary"]) * growth_factor
    return money(annual_salary / 2080.0)


def employee_tax_rates(context: GenerationContext, employee_id: int) -> dict[str, float]:
    rng = stable_rng(context, "payroll-rates", employee_id)
    return {
        "employee_tax": float(rng.uniform(*EMPLOYEE_TAX_WITHHOLDING_RANGE)),
        "benefits_deduction": float(rng.uniform(*BENEFITS_DEDUCTION_RANGE)),
        "employer_benefits": float(rng.uniform(*EMPLOYER_BENEFIT_RATE_RANGE)),
    }


def manufacturing_cost_center_id(context: GenerationContext) -> int:
    cost_centers = context.tables["CostCenter"]
    matches = cost_centers.loc[cost_centers["CostCenterName"].eq("Manufacturing"), "CostCenterID"]
    if matches.empty:
        raise ValueError("Manufacturing cost center is required for payroll generation.")
    return int(matches.iloc[0])


def shift_definition_by_code(context: GenerationContext) -> dict[str, dict[str, Any]]:
    def builder() -> dict[str, dict[str, Any]]:
        shift_definitions = context.tables["ShiftDefinition"]
        if shift_definitions.empty:
            return {}
        return {
            str(row.ShiftCode): row._asdict()
            for row in shift_definitions.itertuples(index=False)
        }

    return get_or_build_cache(context, "_shift_definition_by_code_cache", builder)


def shift_definition_lookup(context: GenerationContext) -> dict[int, dict[str, Any]]:
    def builder() -> dict[int, dict[str, Any]]:
        shift_definitions = context.tables["ShiftDefinition"]
        if shift_definitions.empty:
            return {}
        return shift_definitions.set_index("ShiftDefinitionID").to_dict("index")

    return get_or_build_cache(context, "_shift_definition_lookup_cache", builder)


def work_center_ids_by_code(context: GenerationContext) -> dict[str, int]:
    work_centers = context.tables["WorkCenter"]
    if work_centers.empty:
        return {}
    return {
        str(row.WorkCenterCode): int(row.WorkCenterID)
        for row in work_centers.itertuples(index=False)
    }


def primary_work_center_id_for_title(context: GenerationContext, job_title: str) -> int | None:
    work_center_ids = work_center_ids_by_code(context)
    for work_center_code in JOB_TITLE_WORK_CENTER_CODES.get(str(job_title), ()):
        work_center_id = work_center_ids.get(str(work_center_code))
        if work_center_id is not None:
            return int(work_center_id)
    return None


def generate_shift_definitions_and_assignments(context: GenerationContext) -> None:
    generate_shift_definitions(context)
    generate_employee_shift_assignments(context)


def generate_shift_definitions(context: GenerationContext) -> None:
    if not context.tables["ShiftDefinition"].empty:
        return

    work_center_ids = work_center_ids_by_code(context)
    shift_rows: list[dict[str, Any]] = []
    for shift_definition in SHIFT_DEFINITION_ROWS:
        work_center_code = shift_definition["WorkCenterCode"]
        shift_rows.append({
            "ShiftDefinitionID": next_id(context, "ShiftDefinition"),
            "ShiftCode": shift_definition["ShiftCode"],
            "ShiftName": shift_definition["ShiftName"],
            "Department": shift_definition["Department"],
            "WorkCenterID": None if work_center_code is None else work_center_ids.get(str(work_center_code)),
            "StartTime": shift_definition["StartTime"],
            "EndTime": shift_definition["EndTime"],
            "StandardBreakMinutes": int(shift_definition["StandardBreakMinutes"]),
            "ShiftType": shift_definition["ShiftType"],
            "IsOvernight": int(shift_definition["IsOvernight"]),
            "IsActive": 1,
        })

    append_rows(context, "ShiftDefinition", shift_rows)


def generate_employee_shift_assignments(context: GenerationContext) -> None:
    if not context.tables["EmployeeShiftAssignment"].empty:
        return

    generate_shift_definitions(context)
    employees = context.tables["Employee"]
    if employees.empty:
        return

    shift_by_code = shift_definition_by_code(context)
    assignment_rows: list[dict[str, Any]] = []
    start_date = context.settings.fiscal_year_start
    end_date = context.settings.fiscal_year_end

    for employee in employees.sort_values("EmployeeID").itertuples(index=False):
        if str(employee.PayClass) != "Hourly":
            continue
        shift_code = JOB_TITLE_SHIFT_CODE.get(str(employee.JobTitle))
        if shift_code is None:
            if int(employee.CostCenterID) == manufacturing_cost_center_id(context):
                shift_code = "MFG-DAY"
            else:
                shift_code = "WH-DAY"
        shift_definition = shift_by_code.get(str(shift_code))
        if shift_definition is None:
            continue
        assignment_rows.append({
            "EmployeeShiftAssignmentID": next_id(context, "EmployeeShiftAssignment"),
            "EmployeeID": int(employee.EmployeeID),
            "ShiftDefinitionID": int(shift_definition["ShiftDefinitionID"]),
            "EffectiveStartDate": start_date,
            "EffectiveEndDate": end_date,
            "WorkCenterID": primary_work_center_id_for_title(context, str(employee.JobTitle)),
            "IsPrimary": 1,
        })

    append_rows(context, "EmployeeShiftAssignment", assignment_rows)


def primary_shift_assignment_map(context: GenerationContext) -> dict[int, dict[str, Any]]:
    def builder() -> dict[int, dict[str, Any]]:
        assignments = context.tables["EmployeeShiftAssignment"]
        if assignments.empty:
            return {}
        active_assignments = assignments[assignments["IsPrimary"].astype(int).eq(1)].copy()
        if active_assignments.empty:
            active_assignments = assignments.copy()
        active_assignments = active_assignments.sort_values(["EmployeeID", "EmployeeShiftAssignmentID"])
        active_assignments = active_assignments.drop_duplicates("EmployeeID", keep="first")
        return active_assignments.set_index("EmployeeID").to_dict("index")

    return get_or_build_cache(context, "_shift_assignment_map_cache", builder)


def combine_timestamp(date_value: pd.Timestamp | str, time_text: str) -> str:
    date_text = pd.Timestamp(date_value).strftime("%Y-%m-%d")
    return f"{date_text} {time_text}"


def apply_minutes_to_time(time_text: str, offset_minutes: int) -> str:
    timestamp = pd.Timestamp(f"2000-01-01 {time_text}") + pd.Timedelta(minutes=int(offset_minutes))
    return timestamp.strftime("%H:%M:%S")


def time_span_hours(clock_in_time: str | None, clock_out_time: str | None, break_minutes: int | float) -> float:
    if clock_in_time is None or clock_out_time is None:
        return 0.0
    total_minutes = (pd.Timestamp(clock_out_time) - pd.Timestamp(clock_in_time)).total_seconds() / 60.0
    total_minutes = max(total_minutes - float(break_minutes), 0.0)
    return qty(total_minutes / 60.0)


def employee_clock_approver_id(employee: pd.Series | dict[str, Any]) -> int | None:
    manager_id = employee.get("ManagerID") if isinstance(employee, dict) else employee["ManagerID"]
    if pd.notna(manager_id):
        return int(manager_id)
    return None


def payroll_period_month_lookup(context: GenerationContext) -> dict[int, tuple[int, int]]:
    def builder() -> dict[int, tuple[int, int]]:
        period_lookup = payroll_period_lookup(context)
        return {
            int(payroll_period_id): payroll_period_month(period)
            for payroll_period_id, period in period_lookup.items()
        }

    return get_or_build_cache(context, "_payroll_period_month_lookup_cache", builder)


def generate_payroll_periods(context: GenerationContext) -> None:
    if not context.tables["PayrollPeriod"].empty:
        return

    start = pd.Timestamp(context.settings.fiscal_year_start)
    end = pd.Timestamp(context.settings.fiscal_year_end)
    period_start = start
    rows: list[dict[str, Any]] = []
    sequence = 1

    while period_start <= end:
        period_end = min(period_start + pd.Timedelta(days=PAYROLL_PERIOD_LENGTH_DAYS - 1), end)
        pay_date = next_business_day(period_end + pd.Timedelta(days=PAYROLL_PERIOD_PAYDATE_LAG_DAYS))
        rows.append({
            "PayrollPeriodID": next_id(context, "PayrollPeriod"),
            "PeriodNumber": f"PP-{period_start.year}-{sequence:03d}",
            "PeriodStartDate": period_start.strftime("%Y-%m-%d"),
            "PeriodEndDate": period_end.strftime("%Y-%m-%d"),
            "PayDate": pay_date.strftime("%Y-%m-%d"),
            "FiscalYear": int(pay_date.year),
            "FiscalPeriod": int(pay_date.month),
            "Status": "Open",
        })
        period_start = period_end + pd.Timedelta(days=1)
        sequence += 1

    append_rows(context, "PayrollPeriod", rows)


def active_employees_for_period(context: GenerationContext, period_end: pd.Timestamp) -> pd.DataFrame:
    employees = context.tables["Employee"].copy()
    if employees.empty:
        return employees
    employees["HireDateValue"] = pd.to_datetime(employees["HireDate"])
    return employees[
        employees["IsActive"].eq(1)
        & employees["HireDateValue"].le(period_end)
    ].copy()


def payroll_periods_for_pay_month(context: GenerationContext, year: int, month: int) -> pd.DataFrame:
    periods = context.tables["PayrollPeriod"]
    if periods.empty:
        return periods.copy()
    return periods[
        pd.to_datetime(periods["PayDate"]).dt.year.eq(year)
        & pd.to_datetime(periods["PayDate"]).dt.month.eq(month)
        & periods["Status"].ne("Processed")
    ].sort_values(["PayDate", "PayrollPeriodID"]).reset_index(drop=True)


def production_completion_lines_for_period(
    context: GenerationContext,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
) -> pd.DataFrame:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completions.empty or completion_lines.empty:
        return completion_lines.head(0)

    header_mask = (
        pd.to_datetime(completions["CompletionDate"]).ge(period_start)
        & pd.to_datetime(completions["CompletionDate"]).le(period_end)
    )
    period_headers = completions.loc[header_mask, ["ProductionCompletionID", "WorkOrderID", "CompletionDate"]]
    if period_headers.empty:
        return completion_lines.head(0)

    return completion_lines.merge(period_headers, on="ProductionCompletionID", how="inner")


def direct_labor_targets_for_period(
    context: GenerationContext,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
) -> dict[int, dict[str, float]]:
    period_completion_lines = production_completion_lines_for_period(context, period_start, period_end)
    if period_completion_lines.empty:
        return {}

    grouped = (
        period_completion_lines.groupby("WorkOrderID")[["ExtendedStandardDirectLaborCost", "QuantityCompleted"]]
        .sum()
        .reset_index()
    )
    targets: dict[int, dict[str, float]] = {}
    for row in grouped.itertuples(index=False):
        rng = stable_rng(context, "direct-labor-target", int(row.WorkOrderID), period_start.strftime("%Y-%m-%d"))
        targets[int(row.WorkOrderID)] = {
            "actual_direct_labor_cost": money(float(row.ExtendedStandardDirectLaborCost) * rng.uniform(*DIRECT_LABOR_FACTOR_RANGE)),
            "quantity_completed": qty(float(row.QuantityCompleted)),
        }
    return targets


def work_order_latest_completion_date_in_period(
    period_completion_lines: pd.DataFrame,
) -> dict[int, pd.Timestamp]:
    if period_completion_lines.empty:
        return {}
    grouped = period_completion_lines.groupby("WorkOrderID")["CompletionDate"].max().apply(pd.Timestamp)
    return {int(work_order_id): pd.Timestamp(date_value) for work_order_id, date_value in grouped.items()}


def work_order_operation_targets_for_period(
    context: GenerationContext,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
) -> dict[int, list[dict[str, Any]]]:
    targets = direct_labor_targets_for_period(context, period_start, period_end)
    if not targets:
        return {}

    work_order_operations = context.tables["WorkOrderOperation"]
    routing_operations = context.tables["RoutingOperation"]
    period_completion_lines = production_completion_lines_for_period(context, period_start, period_end)
    latest_dates = work_order_latest_completion_date_in_period(period_completion_lines)
    if work_order_operations.empty or routing_operations.empty:
        return {
            int(work_order_id): [{
                "WorkOrderOperationID": None,
                "WorkDate": latest_dates.get(int(work_order_id), period_end),
                "TargetCost": money(float(target["actual_direct_labor_cost"])),
            }]
            for work_order_id, target in targets.items()
        }

    operation_details = work_order_operations.merge(
        routing_operations[
            [
                "RoutingOperationID",
                "OperationCode",
                "OperationSequence",
                "StandardSetupHours",
                "StandardRunHoursPerUnit",
            ]
        ],
        on="RoutingOperationID",
        how="left",
        suffixes=("", "_Routing"),
    )
    target_map: dict[int, list[dict[str, Any]]] = {}

    for work_order_id, target in targets.items():
        work_date_fallback = latest_dates.get(int(work_order_id), period_end)
        candidates = operation_details[
            operation_details["WorkOrderID"].astype(int).eq(int(work_order_id))
        ].sort_values("OperationSequence")
        if candidates.empty:
            target_map[int(work_order_id)] = [{
                "WorkOrderOperationID": None,
                "WorkDate": work_date_fallback,
                "TargetCost": money(float(target["actual_direct_labor_cost"])),
            }]
            continue

        eligible = candidates.copy()
        eligible["Weight"] = (
            eligible["OperationCode"].map(DIRECT_OPERATION_WEIGHT).fillna(0.60).astype(float)
            * (
                eligible["StandardRunHoursPerUnit"].fillna(0.0).astype(float)
                + eligible["StandardSetupHours"].fillna(0.0).astype(float)
                + 0.05
            )
        )
        eligible = eligible[eligible["Weight"].gt(0)].copy()
        if eligible.empty:
            eligible = candidates.copy()
            eligible["Weight"] = 1.0

        total_weight = float(eligible["Weight"].sum()) or 1.0
        allocated = 0.0
        work_order_targets: list[dict[str, Any]] = []
        target_cost_total = float(target["actual_direct_labor_cost"])
        for index, row in enumerate(eligible.itertuples(index=False), start=1):
            if index == len(eligible):
                target_cost = money(max(target_cost_total - allocated, 0.0))
            else:
                target_cost = money(target_cost_total * float(row.Weight) / total_weight)
                allocated = money(allocated + target_cost)
            if target_cost <= 0:
                continue
            work_date_value = row.ActualEndDate or row.ActualStartDate or row.PlannedEndDate or row.PlannedStartDate
            work_order_targets.append({
                "WorkOrderOperationID": int(row.WorkOrderOperationID),
                "WorkDate": pd.Timestamp(work_date_value) if work_date_value is not None else work_date_fallback,
                "TargetCost": target_cost,
            })
        target_map[int(work_order_id)] = work_order_targets or [{
            "WorkOrderOperationID": None,
            "WorkDate": work_date_fallback,
            "TargetCost": money(target_cost_total),
        }]

    return target_map


def working_dates_for_period(
    context: GenerationContext,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
    work_center_id: int | None = None,
) -> list[pd.Timestamp]:
    calendar = pd.date_range(start=period_start, end=period_end, freq="D")
    if work_center_id is None or context.tables["WorkCenterCalendar"].empty:
        return [day for day in calendar if day.day_name() not in {"Saturday", "Sunday"}]

    work_center_calendar = context.tables["WorkCenterCalendar"]
    working_rows = work_center_calendar[
        work_center_calendar["WorkCenterID"].astype(float).eq(float(work_center_id))
        & pd.to_datetime(work_center_calendar["CalendarDate"]).between(period_start, period_end)
        & work_center_calendar["IsWorkingDay"].astype(int).eq(1)
    ].sort_values("CalendarDate")
    return [pd.Timestamp(value) for value in working_rows["CalendarDate"].tolist()]


def direct_worker_candidates_by_work_center(
    context: GenerationContext,
    direct_workers: pd.DataFrame,
) -> dict[int | None, list[int]]:
    assignments = primary_shift_assignment_map(context)
    lookup = direct_workers.set_index("EmployeeID").to_dict("index")
    by_work_center: dict[int | None, list[int]] = defaultdict(list)

    for employee_id, employee in lookup.items():
        assignment = assignments.get(int(employee_id), {})
        work_center_id = assignment.get("WorkCenterID")
        by_work_center[None].append(int(employee_id))
        if pd.notna(work_center_id):
            by_work_center[int(work_center_id)].append(int(employee_id))

    work_center_ids = work_center_ids_by_code(context)
    for work_center_code, preferred_titles in DIRECT_WORK_CENTER_TITLE_PREFERENCE.items():
        work_center_id = work_center_ids.get(str(work_center_code))
        if work_center_id is None:
            continue
        ordered_ids = [
            int(employee_id)
            for employee_id, employee in lookup.items()
            if str(employee["JobTitle"]) in preferred_titles
        ]
        if ordered_ids:
            existing = by_work_center.get(int(work_center_id), [])
            by_work_center[int(work_center_id)] = list(dict.fromkeys(existing + ordered_ids))

    return {
        work_center_id: sorted(employee_ids)
        for work_center_id, employee_ids in by_work_center.items()
        if employee_ids
    }


def add_time_clock_spec(
    context: GenerationContext,
    specs: dict[tuple[int, str], dict[str, Any]],
    employee_lookup: dict[int, dict[str, Any]],
    employee_id: int,
    payroll_period_id: int,
    work_date: pd.Timestamp,
    work_center_id: int | None,
    labor_type: str,
    regular_hours: float,
    overtime_hours: float,
    work_order_id: int | None = None,
    work_order_operation_id: int | None = None,
) -> None:
    total_hours = qty(float(regular_hours) + float(overtime_hours))
    if total_hours <= 0:
        return

    date_text = pd.Timestamp(work_date).strftime("%Y-%m-%d")
    key = (int(employee_id), date_text)
    assignment = primary_shift_assignment_map(context).get(int(employee_id), {})
    employee = employee_lookup[int(employee_id)]
    approver_id = employee_clock_approver_id(employee) or accounting_manager_id(context)

    if key not in specs:
        specs[key] = {
            "EmployeeID": int(employee_id),
            "PayrollPeriodID": int(payroll_period_id),
            "WorkDate": date_text,
            "ShiftDefinitionID": assignment.get("ShiftDefinitionID"),
            "WorkCenterID": None if work_center_id is None else int(work_center_id),
            "WorkOrderID": None if work_order_id is None else int(work_order_id),
            "WorkOrderOperationID": None if work_order_operation_id is None else int(work_order_operation_id),
            "RegularHours": qty(regular_hours),
            "OvertimeHours": qty(overtime_hours),
            "LaborType": labor_type,
            "ClockStatus": TIMECLOCK_APPROVED_STATUS,
            "ApprovedByEmployeeID": int(approver_id),
            "ApprovedDate": date_text,
        }
        return

    spec = specs[key]
    spec["RegularHours"] = qty(float(spec["RegularHours"]) + float(regular_hours))
    spec["OvertimeHours"] = qty(float(spec["OvertimeHours"]) + float(overtime_hours))
    if spec["WorkOrderID"] is None and work_order_id is not None:
        spec["WorkOrderID"] = int(work_order_id)
    if spec["WorkOrderOperationID"] is None and work_order_operation_id is not None:
        spec["WorkOrderOperationID"] = int(work_order_operation_id)
    if spec["WorkCenterID"] is None and work_center_id is not None:
        spec["WorkCenterID"] = int(work_center_id)
    if spec["LaborType"] != "Direct Manufacturing" and labor_type == "Direct Manufacturing":
        spec["LaborType"] = labor_type


def regular_and_overtime_split(existing_hours: float, added_hours: float) -> tuple[float, float]:
    regular_capacity = max(0.0, 8.0 - float(existing_hours))
    regular_hours = qty(min(float(added_hours), regular_capacity))
    overtime_hours = qty(max(float(added_hours) - regular_hours, 0.0))
    return regular_hours, overtime_hours


def build_direct_time_clock_specs(
    context: GenerationContext,
    payroll_period_id: int,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
    employees: pd.DataFrame,
    specs: dict[tuple[int, str], dict[str, Any]],
) -> None:
    work_orders = context.tables["WorkOrder"]
    if work_orders.empty:
        return

    direct_workers = employees[
        employees["JobTitle"].isin(DIRECT_MANUFACTURING_TITLES)
        & employees["PayClass"].eq("Hourly")
    ].copy()
    if direct_workers.empty:
        return

    operation_targets = work_order_operation_targets_for_period(context, period_start, period_end)
    if not operation_targets:
        return

    work_order_operations = context.tables["WorkOrderOperation"]
    operation_lookup = work_order_operations.set_index("WorkOrderOperationID").to_dict("index") if not work_order_operations.empty else {}
    work_order_lookup = work_orders.set_index("WorkOrderID").to_dict("index")
    employee_lookup = direct_workers.set_index("EmployeeID").to_dict("index")
    worker_ids_by_work_center = direct_worker_candidates_by_work_center(context, direct_workers)
    assigned_period_hours: dict[int, float] = defaultdict(float)

    for work_order_id in sorted(operation_targets):
        operation_target_rows = operation_targets.get(int(work_order_id), [])
        if not operation_target_rows:
            continue

        for operation_target in operation_target_rows:
            work_date = next_business_day(pd.Timestamp(operation_target["WorkDate"]))
            if work_date < period_start or work_date > period_end:
                continue
            target_cost = float(operation_target["TargetCost"])
            if target_cost <= 0:
                continue

            operation_id = operation_target["WorkOrderOperationID"]
            operation = operation_lookup.get(int(operation_id)) if operation_id is not None else None
            work_center_id = int(operation["WorkCenterID"]) if operation is not None else None
            candidate_workers = worker_ids_by_work_center.get(work_center_id) or worker_ids_by_work_center.get(None, [])
            if not candidate_workers:
                continue

            rng = stable_rng(
                context,
                "direct-work-order-operation",
                payroll_period_id,
                work_order_id,
                operation_id,
                work_date.strftime("%Y-%m-%d"),
            )
            worker_count = min(len(candidate_workers), choose_count(rng, DIRECT_WORKER_SPLIT_OPTIONS))
            candidate_workers = sorted(
                candidate_workers,
                key=lambda employee_id: (
                    float(specs.get((int(employee_id), work_date.strftime("%Y-%m-%d")), {}).get("RegularHours", 0.0))
                    + float(specs.get((int(employee_id), work_date.strftime("%Y-%m-%d")), {}).get("OvertimeHours", 0.0)),
                    assigned_period_hours.get(int(employee_id), 0.0),
                    int(employee_id),
                ),
            )[:worker_count]
            split_weights = rng.dirichlet(np.ones(worker_count))

            for employee_id, split_weight in zip(candidate_workers, split_weights, strict=False):
                employee = employee_lookup[int(employee_id)]
                hourly_rate = implied_hourly_rate(employee, work_date.year)
                if hourly_rate <= 0:
                    continue
                raw_hours = max(target_cost * float(split_weight) / hourly_rate, 0.0)
                existing_spec = specs.get((int(employee_id), work_date.strftime("%Y-%m-%d")))
                existing_hours = 0.0 if existing_spec is None else (
                    float(existing_spec["RegularHours"]) + float(existing_spec["OvertimeHours"])
                )
                available_hours = max(MAX_CLOCK_HOURS_PER_DAY - existing_hours, 0.0)
                additional_hours = qty(min(raw_hours, available_hours))
                if additional_hours <= 0:
                    continue
                regular_hours, overtime_hours = regular_and_overtime_split(existing_hours, additional_hours)
                work_order = work_order_lookup.get(int(work_order_id), {})
                add_time_clock_spec(
                    context,
                    specs,
                    employee_lookup,
                    int(employee_id),
                    int(payroll_period_id),
                    work_date,
                    work_center_id,
                    "Direct Manufacturing",
                    regular_hours,
                    overtime_hours,
                    work_order_id=int(work_order_id),
                    work_order_operation_id=None if operation_id is None else int(operation_id),
                )
                assigned_period_hours[int(employee_id)] = qty(
                    assigned_period_hours.get(int(employee_id), 0.0) + regular_hours + overtime_hours
                )

    for employee in direct_workers.itertuples(index=False):
        rng = stable_rng(context, "direct-worker-topup", payroll_period_id, int(employee.EmployeeID))
        target_hours = float(rng.uniform(*DIRECT_SUPPORT_TOPUP_HOURS_RANGE))
        assigned_hours = sum(
            float(spec["RegularHours"]) + float(spec["OvertimeHours"])
            for (employee_id, _), spec in specs.items()
            if int(employee_id) == int(employee.EmployeeID)
        )
        remaining_hours = qty(max(target_hours - assigned_hours, 0.0))
        if remaining_hours <= 0:
            continue

        assignment = primary_shift_assignment_map(context).get(int(employee.EmployeeID), {})
        working_dates = working_dates_for_period(
            context,
            period_start,
            period_end,
            None if pd.isna(assignment.get("WorkCenterID")) else int(assignment["WorkCenterID"]),
        )
        for work_date in working_dates:
            key = (int(employee.EmployeeID), work_date.strftime("%Y-%m-%d"))
            if key in specs:
                continue
            daily_regular = qty(min(float(rng.uniform(*STANDARD_SHIFT_REGULAR_HOURS_RANGE)), remaining_hours))
            daily_overtime = 0.0
            if remaining_hours > daily_regular and int(employee.OvertimeEligible) == 1:
                daily_overtime = qty(min(float(rng.uniform(0.0, 1.5)), remaining_hours - daily_regular))
            add_time_clock_spec(
                context,
                specs,
                direct_workers.set_index("EmployeeID").to_dict("index"),
                int(employee.EmployeeID),
                int(payroll_period_id),
                work_date,
                None if pd.isna(assignment.get("WorkCenterID")) else int(assignment["WorkCenterID"]),
                "Indirect Manufacturing",
                daily_regular,
                daily_overtime,
            )
            remaining_hours = qty(max(remaining_hours - daily_regular - daily_overtime, 0.0))
            if remaining_hours <= 0:
                break


def build_hourly_support_time_clock_specs(
    context: GenerationContext,
    payroll_period_id: int,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
    employees: pd.DataFrame,
    specs: dict[tuple[int, str], dict[str, Any]],
) -> None:
    hourly_support = employees[
        employees["PayClass"].eq("Hourly")
        & ~employees["JobTitle"].isin(DIRECT_MANUFACTURING_TITLES)
    ].copy()
    if hourly_support.empty:
        return

    employee_lookup = hourly_support.set_index("EmployeeID").to_dict("index")
    assignments = primary_shift_assignment_map(context)

    for employee in hourly_support.itertuples(index=False):
        rng = stable_rng(context, "hourly-support-clock", payroll_period_id, int(employee.EmployeeID))
        assignment = assignments.get(int(employee.EmployeeID), {})
        work_center_id = None if pd.isna(assignment.get("WorkCenterID")) else int(assignment["WorkCenterID"])
        labor_type = (
            "Indirect Manufacturing"
            if int(employee.CostCenterID) == manufacturing_cost_center_id(context)
            else "NonManufacturing"
        )
        working_dates = working_dates_for_period(context, period_start, period_end, work_center_id)
        if not working_dates:
            continue

        target_regular_hours = float(rng.uniform(*HOURLY_PERIOD_HOURS_RANGE))
        target_overtime_hours = float(rng.uniform(*HOURLY_PERIOD_OVERTIME_RANGE)) if int(employee.OvertimeEligible) == 1 else 0.0
        remaining_regular = qty(target_regular_hours)
        remaining_overtime = qty(target_overtime_hours)

        for work_date in working_dates:
            if remaining_regular <= 0 and remaining_overtime <= 0:
                break
            regular_hours = qty(min(float(rng.uniform(*STANDARD_SHIFT_REGULAR_HOURS_RANGE)), remaining_regular))
            overtime_hours = 0.0
            if remaining_overtime > 0:
                overtime_hours = qty(min(float(rng.uniform(0.0, 1.75)), remaining_overtime))
            add_time_clock_spec(
                context,
                specs,
                employee_lookup,
                int(employee.EmployeeID),
                int(payroll_period_id),
                work_date,
                work_center_id,
                labor_type,
                regular_hours,
                overtime_hours,
            )
            remaining_regular = qty(max(remaining_regular - regular_hours, 0.0))
            remaining_overtime = qty(max(remaining_overtime - overtime_hours, 0.0))


def materialize_time_clocks_and_labor_entries(
    context: GenerationContext,
    specs: dict[tuple[int, str], dict[str, Any]],
    employees: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not specs:
        return [], []

    employee_lookup = employees.set_index("EmployeeID").to_dict("index")
    shift_lookup = shift_definition_lookup(context)
    time_clock_rows: list[dict[str, Any]] = []
    labor_rows: list[dict[str, Any]] = []

    for spec in sorted(specs.values(), key=lambda row: (row["WorkDate"], row["EmployeeID"])):
        employee = employee_lookup[int(spec["EmployeeID"])]
        shift_definition = shift_lookup.get(int(spec["ShiftDefinitionID"])) if pd.notna(spec["ShiftDefinitionID"]) else None
        base_start_time = "08:00:00" if shift_definition is None else str(shift_definition["StartTime"])
        break_minutes = 30 if shift_definition is None else int(shift_definition["StandardBreakMinutes"])
        rng = stable_rng(
            context,
            "time-clock",
            int(spec["EmployeeID"]),
            int(spec["PayrollPeriodID"]),
            str(spec["WorkDate"]),
            spec.get("WorkOrderOperationID"),
        )
        clock_in_time = apply_minutes_to_time(base_start_time, int(rng.integers(*SHIFT_CLOCK_IN_VARIANCE_MINUTES)))
        total_hours = float(spec["RegularHours"]) + float(spec["OvertimeHours"])
        scheduled_minutes = int(round(total_hours * 60.0)) + int(break_minutes)
        clock_out_base = pd.Timestamp(combine_timestamp(spec["WorkDate"], clock_in_time)) + pd.Timedelta(minutes=scheduled_minutes)
        clock_out_time = clock_out_base.strftime("%Y-%m-%d %H:%M:%S")
        clock_in_timestamp = combine_timestamp(spec["WorkDate"], clock_in_time)
        hourly_rate = implied_hourly_rate(employee, pd.Timestamp(spec["WorkDate"]).year)
        time_clock_entry_id = next_id(context, "TimeClockEntry")

        time_clock_rows.append({
            "TimeClockEntryID": time_clock_entry_id,
            "EmployeeID": int(spec["EmployeeID"]),
            "PayrollPeriodID": int(spec["PayrollPeriodID"]),
            "WorkDate": str(spec["WorkDate"]),
            "ShiftDefinitionID": spec["ShiftDefinitionID"],
            "WorkCenterID": spec["WorkCenterID"],
            "WorkOrderID": spec["WorkOrderID"],
            "WorkOrderOperationID": spec["WorkOrderOperationID"],
            "ClockInTime": clock_in_timestamp,
            "ClockOutTime": clock_out_time,
            "BreakMinutes": int(break_minutes),
            "RegularHours": qty(spec["RegularHours"]),
            "OvertimeHours": qty(spec["OvertimeHours"]),
            "ClockStatus": str(spec["ClockStatus"]),
            "ApprovedByEmployeeID": int(spec["ApprovedByEmployeeID"]),
            "ApprovedDate": str(spec["ApprovedDate"]),
        })
        labor_rows.append({
            "LaborTimeEntryID": next_id(context, "LaborTimeEntry"),
            "PayrollPeriodID": int(spec["PayrollPeriodID"]),
            "EmployeeID": int(spec["EmployeeID"]),
            "WorkOrderID": spec["WorkOrderID"],
            "WorkOrderOperationID": spec["WorkOrderOperationID"],
            "TimeClockEntryID": int(time_clock_entry_id),
            "WorkDate": str(spec["WorkDate"]),
            "LaborType": str(spec["LaborType"]),
            "RegularHours": qty(spec["RegularHours"]),
            "OvertimeHours": qty(spec["OvertimeHours"]),
            "HourlyRateUsed": hourly_rate,
            "ExtendedLaborCost": money(
                float(spec["RegularHours"]) * hourly_rate
                + float(spec["OvertimeHours"]) * hourly_rate * 1.5
            ),
            "ApprovedByEmployeeID": int(spec["ApprovedByEmployeeID"]),
            "ApprovedDate": str(spec["ApprovedDate"]),
        })

    return time_clock_rows, labor_rows


def build_time_clock_and_labor_rows_for_period(
    context: GenerationContext,
    payroll_period_id: int,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
    employees: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    specs: dict[tuple[int, str], dict[str, Any]] = {}
    build_direct_time_clock_specs(context, payroll_period_id, period_start, period_end, employees, specs)
    build_hourly_support_time_clock_specs(context, payroll_period_id, period_start, period_end, employees, specs)
    return materialize_time_clocks_and_labor_entries(context, specs, employees)


def labor_entries_by_employee(
    labor_rows: list[dict[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in labor_rows:
        grouped[int(row["EmployeeID"])].append(row)
    return grouped


def build_payroll_registers_for_period(
    context: GenerationContext,
    period: dict[str, Any],
    employees: pd.DataFrame,
    labor_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payroll_register_rows: list[dict[str, Any]] = []
    payroll_register_line_rows: list[dict[str, Any]] = []
    entries_by_employee = labor_entries_by_employee(labor_rows)
    approver = accounting_manager_id(context)
    pay_date = pd.Timestamp(period["PayDate"]).strftime("%Y-%m-%d")
    period_end = pd.Timestamp(period["PeriodEndDate"])

    for employee in employees.sort_values("EmployeeID").itertuples(index=False):
        employee_entries = entries_by_employee.get(int(employee.EmployeeID), [])
        gross_pay = 0.0
        register_id = next_id(context, "PayrollRegister")
        line_number = 1

        if str(employee.PayClass) == "Hourly":
            for entry in employee_entries:
                hourly_rate = float(entry["HourlyRateUsed"])
                if float(entry["RegularHours"]) > 0:
                    amount = money(float(entry["RegularHours"]) * hourly_rate)
                    payroll_register_line_rows.append({
                        "PayrollRegisterLineID": next_id(context, "PayrollRegisterLine"),
                        "PayrollRegisterID": register_id,
                        "LineNumber": line_number,
                        "LineType": "Regular Earnings",
                        "Hours": float(entry["RegularHours"]),
                        "Rate": hourly_rate,
                        "Amount": amount,
                        "WorkOrderID": entry["WorkOrderID"],
                        "LaborTimeEntryID": int(entry["LaborTimeEntryID"]),
                    })
                    line_number += 1
                    gross_pay += amount
                if float(entry["OvertimeHours"]) > 0:
                    amount = money(float(entry["OvertimeHours"]) * hourly_rate * 1.5)
                    payroll_register_line_rows.append({
                        "PayrollRegisterLineID": next_id(context, "PayrollRegisterLine"),
                        "PayrollRegisterID": register_id,
                        "LineNumber": line_number,
                        "LineType": "Overtime Earnings",
                        "Hours": float(entry["OvertimeHours"]),
                        "Rate": money(hourly_rate * 1.5),
                        "Amount": amount,
                        "WorkOrderID": entry["WorkOrderID"],
                        "LaborTimeEntryID": int(entry["LaborTimeEntryID"]),
                    })
                    line_number += 1
                    gross_pay += amount
        else:
            salary_amount = money(float(employee.BaseAnnualSalary) * growth_factor_for_year(period_end.year) / 26.0)
            payroll_register_line_rows.append({
                "PayrollRegisterLineID": next_id(context, "PayrollRegisterLine"),
                "PayrollRegisterID": register_id,
                "LineNumber": line_number,
                "LineType": "Salary Earnings",
                "Hours": None,
                "Rate": None,
                "Amount": salary_amount,
                "WorkOrderID": None,
                "LaborTimeEntryID": None,
            })
            line_number += 1
            gross_pay += salary_amount

        gross_pay = money(gross_pay)
        rates = employee_tax_rates(context, int(employee.EmployeeID))
        employee_tax = money(gross_pay * rates["employee_tax"])
        benefits_deduction = money(gross_pay * rates["benefits_deduction"])
        employee_withholdings = money(employee_tax + benefits_deduction)
        employer_payroll_tax = money(gross_pay * EMPLOYER_PAYROLL_TAX_RATE)
        employer_benefits = money(gross_pay * rates["employer_benefits"])
        net_pay = money(gross_pay - employee_withholdings)

        for line_type, amount in [
            ("Employee Tax Withholding", employee_tax),
            ("Benefits Deduction", benefits_deduction),
            ("Employer Payroll Tax", employer_payroll_tax),
            ("Employer Benefits", employer_benefits),
        ]:
            payroll_register_line_rows.append({
                "PayrollRegisterLineID": next_id(context, "PayrollRegisterLine"),
                "PayrollRegisterID": register_id,
                "LineNumber": line_number,
                "LineType": line_type,
                "Hours": None,
                "Rate": None,
                "Amount": amount,
                "WorkOrderID": None,
                "LaborTimeEntryID": None,
            })
            line_number += 1

        payroll_register_rows.append({
            "PayrollRegisterID": register_id,
            "PayrollPeriodID": int(period["PayrollPeriodID"]),
            "EmployeeID": int(employee.EmployeeID),
            "CostCenterID": int(employee.CostCenterID),
            "GrossPay": gross_pay,
            "EmployeeWithholdings": employee_withholdings,
            "EmployerPayrollTax": employer_payroll_tax,
            "EmployerBenefits": employer_benefits,
            "NetPay": net_pay,
            "Status": "Approved",
            "ApprovedByEmployeeID": approver,
            "ApprovedDate": pay_date,
        })

    return payroll_register_rows, payroll_register_line_rows


def payroll_liability_amounts_for_period(
    payroll_register_line_rows: list[dict[str, Any]],
) -> dict[str, float]:
    line_df = pd.DataFrame(payroll_register_line_rows)
    if line_df.empty:
        line_totals: dict[str, float] = {}
    else:
        line_totals = line_df.groupby("LineType")["Amount"].sum().to_dict()
    return {
        "Employee Tax Withholding": money(float(line_totals.get("Employee Tax Withholding", 0.0))),
        "Employer Payroll Tax": money(float(line_totals.get("Employer Payroll Tax", 0.0))),
        "Benefits and Other Deductions": money(
            float(line_totals.get("Benefits Deduction", 0.0))
            + float(line_totals.get("Employer Benefits", 0.0))
        ),
    }


def build_payroll_payments_for_period(
    context: GenerationContext,
    payroll_register_rows: list[dict[str, Any]],
    pay_date: str,
) -> list[dict[str, Any]]:
    if not payroll_register_rows:
        return []
    rng = stable_rng(context, "payroll-payments", pay_date)
    rows: list[dict[str, Any]] = []
    for register in payroll_register_rows:
        rows.append({
            "PayrollPaymentID": next_id(context, "PayrollPayment"),
            "PayrollRegisterID": int(register["PayrollRegisterID"]),
            "PaymentDate": pay_date,
            "PaymentMethod": PAYROLL_PAYMENT_METHODS[int(rng.integers(0, len(PAYROLL_PAYMENT_METHODS)))],
            "ReferenceNumber": format_doc_number("PRPAY", pd.Timestamp(pay_date).year, int(register["PayrollRegisterID"])),
            "ClearedDate": next_business_day(pd.Timestamp(pay_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "RecordedByEmployeeID": accounting_manager_id(context),
        })
    return rows


def build_liability_remittances_for_period(
    context: GenerationContext,
    period: dict[str, Any],
    liability_amounts: dict[str, float],
) -> list[dict[str, Any]]:
    pay_date = pd.Timestamp(period["PayDate"])
    fiscal_end = pd.Timestamp(context.settings.fiscal_year_end)
    approved_by = accounting_manager_id(context)
    rows: list[dict[str, Any]] = []
    for liability_type, amount in liability_amounts.items():
        if amount <= 0:
            continue
        remittance_date = next_business_day(pay_date + pd.Timedelta(days=PAYROLL_REMITS_DAYS[liability_type]))
        if remittance_date > fiscal_end:
            continue
        agency = {
            "Employee Tax Withholding": "Federal and State Tax Agencies",
            "Employer Payroll Tax": "Payroll Tax Agencies",
            "Benefits and Other Deductions": "Benefits and Deductions Clearinghouse",
        }[liability_type]
        rows.append({
            "PayrollLiabilityRemittanceID": next_id(context, "PayrollLiabilityRemittance"),
            "PayrollPeriodID": int(period["PayrollPeriodID"]),
            "LiabilityType": liability_type,
            "RemittanceDate": remittance_date.strftime("%Y-%m-%d"),
            "Amount": money(amount),
            "AgencyOrVendor": agency,
            "ReferenceNumber": format_doc_number("PLR", remittance_date.year, len(rows) + int(period["PayrollPeriodID"])),
            "ClearedDate": next_business_day(remittance_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "ApprovedByEmployeeID": approved_by,
        })
    return rows


def generate_month_payroll(context: GenerationContext, year: int, month: int) -> None:
    generate_payroll_periods(context)
    generate_shift_definitions_and_assignments(context)
    periods = payroll_periods_for_pay_month(context, year, month)
    if periods.empty:
        return

    for period in periods.to_dict(orient="records"):
        period_start = pd.Timestamp(period["PeriodStartDate"])
        period_end = pd.Timestamp(period["PeriodEndDate"])
        employees = active_employees_for_period(context, period_end)
        time_clock_rows, labor_rows = build_time_clock_and_labor_rows_for_period(
            context,
            int(period["PayrollPeriodID"]),
            period_start,
            period_end,
            employees,
        )
        append_rows(context, "TimeClockEntry", time_clock_rows)
        append_rows(context, "LaborTimeEntry", labor_rows)

        register_rows, register_line_rows = build_payroll_registers_for_period(context, period, employees, labor_rows)
        append_rows(context, "PayrollRegister", register_rows)
        append_rows(context, "PayrollRegisterLine", register_line_rows)

        pay_date = pd.Timestamp(period["PayDate"]).strftime("%Y-%m-%d")
        append_rows(context, "PayrollPayment", build_payroll_payments_for_period(context, register_rows, pay_date))
        append_rows(
            context,
            "PayrollLiabilityRemittance",
            build_liability_remittances_for_period(
                context,
                period,
                payroll_liability_amounts_for_period(register_line_rows),
            ),
        )

        mask = context.tables["PayrollPeriod"]["PayrollPeriodID"].astype(int).eq(int(period["PayrollPeriodID"]))
        context.tables["PayrollPeriod"].loc[mask, "Status"] = "Processed"


def payroll_register_lookup(context: GenerationContext) -> dict[int, dict[str, Any]]:
    def builder() -> dict[int, dict[str, Any]]:
        registers = context.tables["PayrollRegister"]
        if registers.empty:
            return {}
        return registers.set_index("PayrollRegisterID").to_dict("index")

    return get_or_build_cache(context, "_payroll_register_lookup_cache", builder)


def payroll_register_lines(context: GenerationContext) -> pd.DataFrame:
    def builder() -> pd.DataFrame:
        return context.tables["PayrollRegisterLine"].copy()

    return get_or_build_cache(context, "_payroll_register_lines_cache", builder).copy()


def labor_time_entries(context: GenerationContext) -> pd.DataFrame:
    def builder() -> pd.DataFrame:
        return context.tables["LaborTimeEntry"].copy()

    return get_or_build_cache(context, "_labor_time_entries_cache", builder).copy()


def time_clock_entries(context: GenerationContext) -> pd.DataFrame:
    def builder() -> pd.DataFrame:
        return context.tables["TimeClockEntry"].copy()

    return get_or_build_cache(context, "_time_clock_entries_cache", builder).copy()


def time_clock_entry_lookup(context: GenerationContext) -> dict[int, dict[str, Any]]:
    def builder() -> dict[int, dict[str, Any]]:
        time_clocks = context.tables["TimeClockEntry"]
        if time_clocks.empty:
            return {}
        return time_clocks.set_index("TimeClockEntryID").to_dict("index")

    return get_or_build_cache(context, "_time_clock_entry_lookup_cache", builder)


def payroll_register_lines_with_headers(context: GenerationContext) -> pd.DataFrame:
    def builder() -> pd.DataFrame:
        registers = context.tables["PayrollRegister"]
        lines = context.tables["PayrollRegisterLine"]
        periods = context.tables["PayrollPeriod"]
        if registers.empty or lines.empty:
            return lines.head(0)
        merged = lines.merge(
            registers[["PayrollRegisterID", "EmployeeID", "CostCenterID", "PayrollPeriodID"]],
            on="PayrollRegisterID",
            how="left",
        )
        if not periods.empty:
            merged = merged.merge(
                periods[["PayrollPeriodID", "PayDate", "FiscalYear", "FiscalPeriod"]],
                on="PayrollPeriodID",
                how="left",
            )
        return merged

    return get_or_build_cache(context, "_payroll_register_lines_with_headers_cache", builder).copy()


def labor_time_direct_cost_by_work_order(context: GenerationContext) -> dict[int, float]:
    def builder() -> dict[int, float]:
        time_entries = labor_time_entries(context)
        if time_entries.empty:
            return {}
        direct_entries = time_entries[
            time_entries["LaborType"].eq("Direct Manufacturing")
            & time_entries["WorkOrderID"].notna()
        ]
        if direct_entries.empty:
            return {}
        grouped = direct_entries.groupby("WorkOrderID")["ExtendedLaborCost"].sum()
        return {int(work_order_id): money(float(amount)) for work_order_id, amount in grouped.items()}

    return get_or_build_cache(context, "_labor_time_direct_cost_by_work_order_cache", builder)


def direct_labor_cost_by_month_work_order(context: GenerationContext) -> dict[tuple[int, int], dict[int, float]]:
    def builder() -> dict[tuple[int, int], dict[int, float]]:
        time_entries = labor_time_entries(context)
        if time_entries.empty:
            return {}
        period_lookup = payroll_period_lookup(context)
        grouped: dict[tuple[int, int], dict[int, float]] = defaultdict(lambda: defaultdict(float))
        direct_entries = time_entries[
            time_entries["LaborType"].eq("Direct Manufacturing")
            & time_entries["WorkOrderID"].notna()
        ]
        for entry in direct_entries.itertuples(index=False):
            period = period_lookup.get(int(entry.PayrollPeriodID))
            if period is None:
                continue
            key = payroll_period_month(period)
            grouped[key][int(entry.WorkOrderID)] += float(entry.ExtendedLaborCost)
        return {
            key: {int(work_order_id): money(amount) for work_order_id, amount in work_order_map.items()}
            for key, work_order_map in grouped.items()
        }

    return get_or_build_cache(context, "_direct_labor_cost_by_month_work_order_cache", builder)


def monthly_direct_labor_reclass_amount(context: GenerationContext, year: int, month: int) -> float:
    grouped = direct_labor_cost_by_month_work_order(context)
    return money(sum(float(amount) for amount in grouped.get((year, month), {}).values()))


def completion_lines_for_month(context: GenerationContext, year: int, month: int) -> pd.DataFrame:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completions.empty or completion_lines.empty:
        return completion_lines.head(0)
    month_headers = completions[
        pd.to_datetime(completions["CompletionDate"]).dt.year.eq(year)
        & pd.to_datetime(completions["CompletionDate"]).dt.month.eq(month)
    ][["ProductionCompletionID", "WorkOrderID"]]
    if month_headers.empty:
        return completion_lines.head(0)
    return completion_lines.merge(month_headers, on="ProductionCompletionID", how="inner")


def monthly_factory_overhead_amount(context: GenerationContext, year: int, month: int) -> float:
    lines = completion_lines_for_month(context, year, month)
    if lines.empty:
        return 0.0
    standard_total = (
        lines["ExtendedStandardVariableOverheadCost"].astype(float).sum()
        + lines["ExtendedStandardFixedOverheadCost"].astype(float).sum()
    )
    rng = stable_rng(context, "factory-overhead", year, month)
    return money(float(standard_total) * float(rng.uniform(*FACTORY_OVERHEAD_FACTOR_RANGE)))


def monthly_manufacturing_overhead_pool_amount(context: GenerationContext, year: int, month: int) -> float:
    lines = payroll_register_lines_with_headers(context)
    payroll_component = 0.0
    if not lines.empty:
        employees = context.tables["Employee"][["EmployeeID", "CostCenterID"]]
        manufacturing_cost_center = manufacturing_cost_center_id(context)
        manufacturing_employee_ids = set(
            employees.loc[employees["CostCenterID"].eq(manufacturing_cost_center), "EmployeeID"].astype(int).tolist()
        )
        period_lines = lines[
            pd.to_datetime(lines["PayDate"]).dt.year.eq(year)
            & pd.to_datetime(lines["PayDate"]).dt.month.eq(month)
        ].copy()
        earnings_mask = period_lines["LineType"].isin(["Regular Earnings", "Overtime Earnings", "Salary Earnings", "Bonus"])
        manufacturing_earnings = period_lines[
            earnings_mask
            & period_lines["EmployeeID"].astype(int).isin(manufacturing_employee_ids)
            & period_lines["WorkOrderID"].isna()
        ]["Amount"].astype(float).sum()
        manufacturing_burden = period_lines[
            period_lines["EmployeeID"].astype(int).isin(manufacturing_employee_ids)
            & period_lines["LineType"].isin(["Employer Payroll Tax", "Employer Benefits"])
        ]["Amount"].astype(float).sum()
        payroll_component = float(manufacturing_earnings) + float(manufacturing_burden)
    if monthly_direct_labor_reclass_amount(context, year, month) <= 0:
        return 0.0
    return money(payroll_component + monthly_factory_overhead_amount(context, year, month))


def work_order_overhead_cost_map(context: GenerationContext) -> dict[int, float]:
    def builder() -> dict[int, float]:
        direct_by_month = direct_labor_cost_by_month_work_order(context)
        totals: dict[int, float] = defaultdict(float)
        for (year, month), direct_map in direct_by_month.items():
            month_overhead = float(monthly_manufacturing_overhead_pool_amount(context, year, month))
            total_direct = sum(float(amount) for amount in direct_map.values())
            if month_overhead <= 0 or total_direct <= 0:
                continue
            allocated = 0.0
            ordered_entries = sorted(direct_map.items())
            for index, (work_order_id, direct_amount) in enumerate(ordered_entries, start=1):
                if index == len(ordered_entries):
                    allocation = money(month_overhead - allocated)
                else:
                    allocation = money(month_overhead * float(direct_amount) / total_direct)
                    allocated = money(allocated + allocation)
                totals[int(work_order_id)] += float(allocation)
        return {int(work_order_id): money(amount) for work_order_id, amount in totals.items()}

    return get_or_build_cache(context, "_work_order_overhead_cost_map_cache", builder)


def payroll_liability_recorded_amounts(context: GenerationContext) -> dict[str, float]:
    lines = payroll_register_lines_with_headers(context)
    registers = context.tables["PayrollRegister"]
    if lines.empty or registers.empty:
        return {"2030": 0.0, "2031": 0.0, "2032": 0.0, "2033": 0.0}
    return {
        "2030": money(float(registers["NetPay"].astype(float).sum())),
        "2031": money(float(lines.loc[lines["LineType"].eq("Employee Tax Withholding"), "Amount"].astype(float).sum())),
        "2032": money(float(lines.loc[lines["LineType"].eq("Employer Payroll Tax"), "Amount"].astype(float).sum())),
        "2033": money(
            float(lines.loc[lines["LineType"].isin(["Benefits Deduction", "Employer Benefits"]), "Amount"].astype(float).sum())
        ),
    }


def payroll_liability_remitted_amounts(context: GenerationContext) -> dict[str, float]:
    def builder() -> dict[str, float]:
        remittances = context.tables["PayrollLiabilityRemittance"]
        if remittances.empty:
            return {"2031": 0.0, "2032": 0.0, "2033": 0.0}
        liability_map = {
            "Employee Tax Withholding": "2031",
            "Employer Payroll Tax": "2032",
            "Benefits and Other Deductions": "2033",
        }
        totals: dict[str, float] = defaultdict(float)
        for remittance in remittances.itertuples(index=False):
            totals[liability_map[str(remittance.LiabilityType)]] += float(remittance.Amount)
        return {account_number: money(amount) for account_number, amount in totals.items()}

    return get_or_build_cache(context, "_payroll_liability_remitted_amounts_cache", builder)


def approved_time_clock_hours_by_employee_period(context: GenerationContext) -> dict[tuple[int, int], float]:
    def builder() -> dict[tuple[int, int], float]:
        time_clocks = time_clock_entries(context)
        if time_clocks.empty:
            return {}
        approved = time_clocks[time_clocks["ClockStatus"].eq(TIMECLOCK_APPROVED_STATUS)].copy()
        if approved.empty:
            return {}
        approved["TotalHours"] = approved["RegularHours"].astype(float) + approved["OvertimeHours"].astype(float)
        grouped = approved.groupby(["EmployeeID", "PayrollPeriodID"])["TotalHours"].sum()
        return {
            (int(employee_id), int(payroll_period_id)): qty(float(total_hours))
            for (employee_id, payroll_period_id), total_hours in grouped.items()
        }

    return get_or_build_cache(context, "_approved_time_clock_hours_by_employee_period_cache", builder)


def monthly_payroll_state(context: GenerationContext, year: int, month: int) -> dict[str, float]:
    periods = context.tables["PayrollPeriod"]
    if periods.empty:
        return {
            "periods_processed": 0.0,
            "time_clock_entries_created": 0.0,
            "labor_entries_created": 0.0,
            "payroll_registers_created": 0.0,
            "payroll_payments_created": 0.0,
            "liability_remittances_created": 0.0,
            "direct_labor_reclass_amount": 0.0,
            "manufacturing_overhead_reclass_amount": 0.0,
        }

    period_ids = periods[
        pd.to_datetime(periods["PayDate"]).dt.year.eq(year)
        & pd.to_datetime(periods["PayDate"]).dt.month.eq(month)
    ]["PayrollPeriodID"].astype(int).tolist()
    if not period_ids:
        return {
            "periods_processed": 0.0,
            "time_clock_entries_created": 0.0,
            "labor_entries_created": 0.0,
            "payroll_registers_created": 0.0,
            "payroll_payments_created": 0.0,
            "liability_remittances_created": 0.0,
            "direct_labor_reclass_amount": 0.0,
            "manufacturing_overhead_reclass_amount": 0.0,
        }

    labor_entries = context.tables["LaborTimeEntry"]
    time_clocks = context.tables["TimeClockEntry"]
    payroll_registers = context.tables["PayrollRegister"]
    payroll_payments = context.tables["PayrollPayment"]
    remittances = context.tables["PayrollLiabilityRemittance"]
    register_ids = payroll_registers.loc[
        payroll_registers["PayrollPeriodID"].astype(int).isin(period_ids),
        "PayrollRegisterID",
    ].astype(int).tolist()

    return {
        "periods_processed": float(len(period_ids)),
        "time_clock_entries_created": float(len(time_clocks[time_clocks["PayrollPeriodID"].astype(int).isin(period_ids)])),
        "labor_entries_created": float(len(labor_entries[labor_entries["PayrollPeriodID"].astype(int).isin(period_ids)])),
        "payroll_registers_created": float(len(register_ids)),
        "payroll_payments_created": float(len(payroll_payments[payroll_payments["PayrollRegisterID"].astype(int).isin(register_ids)])),
        "liability_remittances_created": float(len(remittances[remittances["PayrollPeriodID"].astype(int).isin(period_ids)])),
        "direct_labor_reclass_amount": monthly_direct_labor_reclass_amount(context, year, month),
        "manufacturing_overhead_reclass_amount": monthly_manufacturing_overhead_pool_amount(context, year, month),
    }
