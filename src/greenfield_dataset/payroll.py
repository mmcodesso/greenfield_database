from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from greenfield_dataset.schema import TABLE_COLUMNS
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


def append_rows(context: GenerationContext, table_name: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    new_rows = pd.DataFrame(rows, columns=TABLE_COLUMNS[table_name])
    context.tables[table_name] = pd.concat([context.tables[table_name], new_rows], ignore_index=True)


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
    periods = context.tables["PayrollPeriod"]
    if periods.empty:
        return {}
    return periods.set_index("PayrollPeriodID").to_dict("index")


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


def build_direct_labor_time_entries(
    context: GenerationContext,
    payroll_period_id: int,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
    employees: pd.DataFrame,
) -> list[dict[str, Any]]:
    work_orders = context.tables["WorkOrder"]
    if work_orders.empty:
        return []

    direct_workers = employees[
        employees["JobTitle"].isin(DIRECT_MANUFACTURING_TITLES)
        & employees["PayClass"].eq("Hourly")
    ].copy()
    if direct_workers.empty:
        return []

    targets = direct_labor_targets_for_period(context, period_start, period_end)
    operation_targets = work_order_operation_targets_for_period(context, period_start, period_end)
    approver = accounting_manager_id(context)
    direct_rows: list[dict[str, Any]] = []
    assigned_hours: dict[int, float] = defaultdict(float)
    employee_lookup = direct_workers.set_index("EmployeeID").to_dict("index")
    ordered_worker_ids = sorted(employee_lookup)

    for work_order_id in sorted(targets):
        operation_target_rows = operation_targets.get(int(work_order_id), [])
        if not operation_target_rows:
            continue

        for operation_target in operation_target_rows:
            work_date = next_business_day(pd.Timestamp(operation_target["WorkDate"]))
            target_cost = float(operation_target["TargetCost"])
            if target_cost <= 0:
                continue

            rng = stable_rng(
                context,
                "direct-work-order-operation",
                payroll_period_id,
                work_order_id,
                operation_target["WorkOrderOperationID"],
            )
            worker_count = min(len(ordered_worker_ids), choose_count(rng, DIRECT_WORKER_SPLIT_OPTIONS))
            candidate_workers = sorted(
                ordered_worker_ids,
                key=lambda employee_id: (assigned_hours.get(employee_id, 0.0), employee_id),
            )[:worker_count]
            split_weights = rng.dirichlet(np.ones(worker_count))

            for employee_id, split_weight in zip(candidate_workers, split_weights, strict=False):
                employee = employee_lookup[int(employee_id)]
                hourly_rate = implied_hourly_rate(employee, work_date.year)
                entry_cost = money(target_cost * float(split_weight))
                if entry_cost <= 0 or hourly_rate <= 0:
                    continue

                raw_hours = entry_cost / hourly_rate
                regular_capacity = max(0.0, 80.0 - assigned_hours.get(int(employee_id), 0.0))
                regular_hours = qty(min(raw_hours, regular_capacity))
                overtime_hours = qty(max(raw_hours - regular_hours, 0.0))
                extended_labor_cost = money(regular_hours * hourly_rate + overtime_hours * hourly_rate * 1.5)
                if extended_labor_cost <= 0:
                    continue

                direct_rows.append({
                    "LaborTimeEntryID": next_id(context, "LaborTimeEntry"),
                    "PayrollPeriodID": payroll_period_id,
                    "EmployeeID": int(employee_id),
                    "WorkOrderID": int(work_order_id),
                    "WorkOrderOperationID": operation_target["WorkOrderOperationID"],
                    "WorkDate": work_date.strftime("%Y-%m-%d"),
                    "LaborType": "Direct Manufacturing",
                    "RegularHours": regular_hours,
                    "OvertimeHours": overtime_hours,
                    "HourlyRateUsed": hourly_rate,
                    "ExtendedLaborCost": extended_labor_cost,
                    "ApprovedByEmployeeID": approver,
                    "ApprovedDate": work_date.strftime("%Y-%m-%d"),
                })
                assigned_hours[int(employee_id)] = round(
                    assigned_hours.get(int(employee_id), 0.0) + regular_hours + overtime_hours,
                    2,
                )

    for employee in direct_workers.itertuples(index=False):
        rng = stable_rng(context, "direct-worker-topup", payroll_period_id, int(employee.EmployeeID))
        target_hours = float(rng.uniform(*HOURLY_PERIOD_HOURS_RANGE))
        overtime_target = float(rng.uniform(*HOURLY_PERIOD_OVERTIME_RANGE))
        existing_hours = float(assigned_hours.get(int(employee.EmployeeID), 0.0))
        remaining_regular = qty(max(target_hours - existing_hours, 0.0))
        if remaining_regular <= 0 and overtime_target <= 0:
            continue

        hourly_rate = implied_hourly_rate(employee._asdict(), period_end.year)
        work_date = next_business_day(period_end)
        extended_labor_cost = money(remaining_regular * hourly_rate + overtime_target * hourly_rate * 1.5)
        if extended_labor_cost <= 0:
            continue

        direct_rows.append({
            "LaborTimeEntryID": next_id(context, "LaborTimeEntry"),
            "PayrollPeriodID": payroll_period_id,
            "EmployeeID": int(employee.EmployeeID),
            "WorkOrderID": None,
            "WorkOrderOperationID": None,
            "WorkDate": work_date.strftime("%Y-%m-%d"),
            "LaborType": "Indirect Manufacturing",
            "RegularHours": remaining_regular,
            "OvertimeHours": qty(overtime_target),
            "HourlyRateUsed": hourly_rate,
            "ExtendedLaborCost": extended_labor_cost,
            "ApprovedByEmployeeID": approver,
            "ApprovedDate": work_date.strftime("%Y-%m-%d"),
        })

    return direct_rows


def build_indirect_and_nonmanufacturing_time_entries(
    context: GenerationContext,
    payroll_period_id: int,
    period_end: pd.Timestamp,
    employees: pd.DataFrame,
) -> list[dict[str, Any]]:
    approver = accounting_manager_id(context)
    rows: list[dict[str, Any]] = []
    work_date = next_business_day(period_end)

    for employee in employees.itertuples(index=False):
        title = str(employee.JobTitle)
        is_hourly = str(employee.PayClass) == "Hourly"
        if title in DIRECT_MANUFACTURING_TITLES:
            continue
        if not is_hourly and title not in INDIRECT_MANUFACTURING_TITLES:
            continue

        rng = stable_rng(context, "time-entry", payroll_period_id, int(employee.EmployeeID))
        regular_hours = qty(float(rng.uniform(*HOURLY_PERIOD_HOURS_RANGE)))
        overtime_hours = qty(float(rng.uniform(0.0, 2.5)) if int(employee.OvertimeEligible) == 1 else 0.0)
        hourly_rate = implied_hourly_rate(employee._asdict(), period_end.year)
        labor_type = (
            "Indirect Manufacturing"
            if int(employee.CostCenterID) == manufacturing_cost_center_id(context)
            else "NonManufacturing"
        )
        rows.append({
            "LaborTimeEntryID": next_id(context, "LaborTimeEntry"),
            "PayrollPeriodID": payroll_period_id,
            "EmployeeID": int(employee.EmployeeID),
            "WorkOrderID": None,
            "WorkOrderOperationID": None,
            "WorkDate": work_date.strftime("%Y-%m-%d"),
            "LaborType": labor_type,
            "RegularHours": regular_hours,
            "OvertimeHours": overtime_hours,
            "HourlyRateUsed": hourly_rate,
            "ExtendedLaborCost": money(regular_hours * hourly_rate + overtime_hours * hourly_rate * 1.5),
            "ApprovedByEmployeeID": approver,
            "ApprovedDate": work_date.strftime("%Y-%m-%d"),
        })

    return rows


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
    periods = payroll_periods_for_pay_month(context, year, month)
    if periods.empty:
        return

    for period in periods.to_dict(orient="records"):
        period_start = pd.Timestamp(period["PeriodStartDate"])
        period_end = pd.Timestamp(period["PeriodEndDate"])
        employees = active_employees_for_period(context, period_end)
        labor_rows: list[dict[str, Any]] = []
        labor_rows.extend(build_direct_labor_time_entries(context, int(period["PayrollPeriodID"]), period_start, period_end, employees))
        labor_rows.extend(build_indirect_and_nonmanufacturing_time_entries(context, int(period["PayrollPeriodID"]), period_end, employees))
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
    registers = context.tables["PayrollRegister"]
    if registers.empty:
        return {}
    return registers.set_index("PayrollRegisterID").to_dict("index")


def payroll_register_lines(context: GenerationContext) -> pd.DataFrame:
    return context.tables["PayrollRegisterLine"].copy()


def labor_time_entries(context: GenerationContext) -> pd.DataFrame:
    return context.tables["LaborTimeEntry"].copy()


def payroll_register_lines_with_headers(context: GenerationContext) -> pd.DataFrame:
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


def labor_time_direct_cost_by_work_order(context: GenerationContext) -> dict[int, float]:
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


def direct_labor_cost_by_month_work_order(context: GenerationContext) -> dict[tuple[int, int], dict[int, float]]:
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


def monthly_payroll_state(context: GenerationContext, year: int, month: int) -> dict[str, float]:
    periods = context.tables["PayrollPeriod"]
    if periods.empty:
        return {
            "periods_processed": 0.0,
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
            "labor_entries_created": 0.0,
            "payroll_registers_created": 0.0,
            "payroll_payments_created": 0.0,
            "liability_remittances_created": 0.0,
            "direct_labor_reclass_amount": 0.0,
            "manufacturing_overhead_reclass_amount": 0.0,
        }

    labor_entries = context.tables["LaborTimeEntry"]
    payroll_registers = context.tables["PayrollRegister"]
    payroll_payments = context.tables["PayrollPayment"]
    remittances = context.tables["PayrollLiabilityRemittance"]
    register_ids = payroll_registers.loc[
        payroll_registers["PayrollPeriodID"].astype(int).isin(period_ids),
        "PayrollRegisterID",
    ].astype(int).tolist()

    return {
        "periods_processed": float(len(period_ids)),
        "labor_entries_created": float(len(labor_entries[labor_entries["PayrollPeriodID"].astype(int).isin(period_ids)])),
        "payroll_registers_created": float(len(register_ids)),
        "payroll_payments_created": float(len(payroll_payments[payroll_payments["PayrollRegisterID"].astype(int).isin(register_ids)])),
        "liability_remittances_created": float(len(remittances[remittances["PayrollPeriodID"].astype(int).isin(period_ids)])),
        "direct_labor_reclass_amount": monthly_direct_labor_reclass_amount(context, year, month),
        "manufacturing_overhead_reclass_amount": monthly_manufacturing_overhead_pool_amount(context, year, month),
    }
