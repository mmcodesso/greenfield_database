from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
import pandas as pd

from generator_dataset.fixed_assets import depreciable_fixed_asset_profiles, fixed_asset_profile
from generator_dataset.master_data import approver_employee_id, current_role_employee_id, valid_employees
from generator_dataset.payroll import (
    monthly_direct_labor_reclass_amount,
    monthly_factory_overhead_amount,
    monthly_manufacturing_overhead_pool_amount,
)
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.settings import GenerationContext
from generator_dataset.utils import money, next_id


ANNUAL_GROWTH_RATE = 0.035
PAYROLL_BURDEN_RATE = 0.18

BASE_ANNUAL_SALARIES = {
    "Staff": 54000.0,
    "Supervisor": 78000.0,
    "Manager": 115000.0,
    "Executive": 210000.0,
}

COST_CENTER_MULTIPLIERS = {
    "Executive": 1.15,
    "Sales": 1.05,
    "Warehouse": 0.90,
    "Manufacturing": 0.96,
    "Purchasing": 1.00,
    "Administration": 1.00,
    "Customer Service": 0.88,
    "Research and Development": 1.10,
    "Marketing": 1.08,
}

SALARY_ACCOUNT_BY_COST_CENTER = {
    "Executive": "6050",
    "Sales": "6010",
    "Warehouse": "6020",
    "Manufacturing": "6260",
    "Purchasing": "6230",
    "Administration": "6030",
    "Customer Service": "6040",
    "Research and Development": "6250",
    "Marketing": "6240",
}

MONTHLY_RENT_BASES = {
    "Office": 18000.0,
    "Warehouse": 24000.0,
}

MONTHLY_ACCRUAL_BASES = {
    "6100": 4500.0,
    "6140": 6000.0,
    "6180": 5000.0,
}

ACCRUAL_ACCOUNT_METADATA = {
    "6100": {
        "description": "Insurance accrual",
        "journal_description": "Month-end insurance accrued expense",
    },
    "6140": {
        "description": "IT and software accrual",
        "journal_description": "Month-end IT and software accrued expense",
    },
    "6180": {
        "description": "Professional fees accrual",
        "journal_description": "Month-end professional fees accrued expense",
    },
}

ACCRUAL_ADJUSTMENTS_PER_YEAR = 1
ACCRUAL_ADJUSTMENT_MIN_AGE_DAYS = 90
ACCRUAL_ADJUSTMENT_MIN_AMOUNT = 250.0

def account_id_by_number(context: GenerationContext, account_number: str) -> int:
    accounts = context.tables["Account"]
    matches = accounts.loc[accounts["AccountNumber"].astype(str).eq(account_number), "AccountID"]
    if matches.empty:
        raise ValueError(f"Account number {account_number} is not loaded.")
    return int(matches.iloc[0])


def fiscal_months(context: GenerationContext) -> list[tuple[int, int]]:
    start = pd.Timestamp(context.settings.fiscal_year_start)
    end = pd.Timestamp(context.settings.fiscal_year_end)
    months = pd.date_range(
        start=pd.Timestamp(year=start.year, month=start.month, day=1),
        end=pd.Timestamp(year=end.year, month=end.month, day=1),
        freq="MS",
    )
    return [(int(month.year), int(month.month)) for month in months]


def stable_seed(context: GenerationContext, *parts: object) -> int:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return (context.settings.random_seed + int.from_bytes(digest[:8], "big")) % (2**32 - 1)


def stable_uniform(context: GenerationContext, low: float, high: float, *parts: object) -> float:
    rng = np.random.default_rng(stable_seed(context, *parts))
    return float(rng.uniform(low, high))


def first_business_day(year: int, month: int) -> pd.Timestamp:
    day = pd.Timestamp(year=year, month=month, day=1)
    while day.day_name() in {"Saturday", "Sunday"}:
        day = day + pd.Timedelta(days=1)
    return day


def first_business_day_on_or_after(timestamp: pd.Timestamp | str) -> pd.Timestamp:
    day = pd.Timestamp(timestamp)
    while day.day_name() in {"Saturday", "Sunday"}:
        day = day + pd.Timedelta(days=1)
    return day


def last_business_day(year: int, month: int) -> pd.Timestamp:
    day = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(1)
    while day.day_name() in {"Saturday", "Sunday"}:
        day = day - pd.Timedelta(days=1)
    return day


def last_calendar_day(year: int, month: int) -> pd.Timestamp:
    return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(1)


def next_month(year: int, month: int) -> tuple[int, int]:
    current = pd.Timestamp(year=year, month=month, day=1) + pd.DateOffset(months=1)
    return int(current.year), int(current.month)


def date_in_range(context: GenerationContext, timestamp: pd.Timestamp) -> bool:
    start = pd.Timestamp(context.settings.fiscal_year_start)
    end = pd.Timestamp(context.settings.fiscal_year_end)
    return start <= timestamp <= end


def sorted_cost_centers(context: GenerationContext) -> pd.DataFrame:
    return context.tables["CostCenter"].sort_values("CostCenterID").reset_index(drop=True)


def sorted_employees(context: GenerationContext) -> pd.DataFrame:
    employees = valid_employees(context, None)
    if employees.empty:
        employees = context.tables["Employee"].copy()
    return employees.sort_values("EmployeeID").reset_index(drop=True)


def employee_id_by_titles(context: GenerationContext, *job_titles: str) -> int | None:
    for title in job_titles:
        employee_id = current_role_employee_id(context, title)
        if employee_id is not None:
            return int(employee_id)
    return None


def first_executive_id(context: GenerationContext) -> int:
    employees = sorted_employees(context)
    matches = employees.loc[employees["AuthorizationLevel"].eq("Executive"), "EmployeeID"]
    if matches.empty:
        raise ValueError("At least one Executive employee is required for journal approvals.")
    return int(matches.sort_values().iloc[0])


def cost_center_manager_id(context: GenerationContext, cost_center_id: int) -> int:
    cost_centers = context.tables["CostCenter"].set_index("CostCenterID")
    manager_id = cost_centers.loc[int(cost_center_id), "ManagerID"]
    if pd.notna(manager_id):
        return int(manager_id)
    return first_executive_id(context)


def payroll_accrual_approver_id(context: GenerationContext) -> int:
    return approver_employee_id(
        context,
        context.settings.fiscal_year_end,
        preferred_titles=["Controller", "Chief Financial Officer"],
        fallback_cost_center_name="Administration",
    )


def payroll_settlement_creator_id(context: GenerationContext) -> int:
    return employee_id_by_titles(context, "Accounting Manager", "Controller") or first_executive_id(context)


def payroll_settlement_approver_id(context: GenerationContext) -> int:
    return approver_employee_id(
        context,
        context.settings.fiscal_year_end,
        preferred_titles=["Chief Financial Officer", "Controller"],
        fallback_cost_center_name="Administration",
    )


def accounting_journal_creator_id(context: GenerationContext) -> int:
    return employee_id_by_titles(context, "Accounting Manager", "Controller") or first_executive_id(context)


def accounting_journal_approver_id(context: GenerationContext) -> int:
    return approver_employee_id(
        context,
        context.settings.fiscal_year_end,
        preferred_titles=["Controller", "Chief Financial Officer"],
        fallback_cost_center_name="Administration",
    )


def close_journal_creator_id(context: GenerationContext) -> int:
    return employee_id_by_titles(context, "Controller", "Accounting Manager") or first_executive_id(context)


def close_journal_approver_id(context: GenerationContext) -> int:
    return approver_employee_id(
        context,
        context.settings.fiscal_year_end,
        preferred_titles=["Chief Financial Officer", "Controller"],
        fallback_cost_center_name="Administration",
    )


def journal_timestamp(posting_date: str, hour: int) -> str:
    return f"{posting_date} {hour:02d}:00:00"


def next_entry_number(context: GenerationContext, year: int) -> str:
    journal_entries = context.tables["JournalEntry"]
    if journal_entries.empty:
        return f"JE-{year}-000001"

    prefix = f"JE-{year}-"
    year_entries = journal_entries.loc[journal_entries["EntryNumber"].astype(str).str.startswith(prefix), "EntryNumber"]
    if year_entries.empty:
        return f"JE-{year}-000001"

    sequences = year_entries.astype(str).str.rsplit("-", n=1).str[-1].astype(int)
    return f"JE-{year}-{int(sequences.max()) + 1:06d}"


def build_journal_header(
    context: GenerationContext,
    posting_date: str,
    entry_type: str,
    description: str,
    total_amount: float,
    created_by_employee_id: int,
    approved_by_employee_id: int,
    reverses_journal_entry_id: int | None = None,
) -> dict[str, Any]:
    year = pd.Timestamp(posting_date).year
    entry_number = next_entry_number(context, int(year))
    return {
        "JournalEntryID": next_id(context, "JournalEntry"),
        "EntryNumber": entry_number,
        "PostingDate": posting_date,
        "EntryType": entry_type,
        "Description": description,
        "TotalAmount": money(total_amount),
        "CreatedByEmployeeID": int(created_by_employee_id),
        "CreatedDate": journal_timestamp(posting_date, 8),
        "ApprovedByEmployeeID": int(approved_by_employee_id),
        "ApprovedDate": journal_timestamp(posting_date, 9),
        "ReversesJournalEntryID": reverses_journal_entry_id,
    }


def build_journal_gl_row(
    context: GenerationContext,
    journal_entry_id: int,
    voucher_number: str,
    posting_date: str,
    account_number: str,
    debit: float,
    credit: float,
    description: str,
    created_by_employee_id: int,
    cost_center_id: int | None = None,
) -> dict[str, Any]:
    timestamp = pd.Timestamp(posting_date)
    return {
        "GLEntryID": next_id(context, "GLEntry"),
        "PostingDate": posting_date,
        "AccountID": account_id_by_number(context, account_number),
        "Debit": money(debit),
        "Credit": money(credit),
        "VoucherType": "JournalEntry",
        "VoucherNumber": voucher_number,
        "SourceDocumentType": "JournalEntry",
        "SourceDocumentID": int(journal_entry_id),
        "SourceLineID": None,
        "CostCenterID": cost_center_id,
        "Description": description,
        "CreatedByEmployeeID": int(created_by_employee_id),
        "CreatedDate": journal_timestamp(posting_date, 8),
        "FiscalYear": int(timestamp.year),
        "FiscalPeriod": int(timestamp.month),
    }


def append_journal(context: GenerationContext, header: dict[str, Any], gl_rows: list[dict[str, Any]]) -> None:
    context.tables["JournalEntry"] = pd.concat(
        [context.tables["JournalEntry"], pd.DataFrame([header], columns=TABLE_COLUMNS["JournalEntry"])],
        ignore_index=True,
    )
    context.tables["GLEntry"] = pd.concat(
        [context.tables["GLEntry"], pd.DataFrame(gl_rows, columns=TABLE_COLUMNS["GLEntry"])],
        ignore_index=True,
    )


def create_journal(
    context: GenerationContext,
    posting_date: str,
    entry_type: str,
    description: str,
    lines: list[dict[str, Any]],
    created_by_employee_id: int,
    approved_by_employee_id: int,
    reverses_journal_entry_id: int | None = None,
) -> dict[str, Any]:
    total_debit = money(sum(float(line["Debit"]) for line in lines))
    total_credit = money(sum(float(line["Credit"]) for line in lines))
    if total_debit <= 0:
        raise ValueError(f"Journal entry {entry_type} on {posting_date} has no debit amount.")
    if total_debit != total_credit:
        raise ValueError(
            f"Journal entry {entry_type} on {posting_date} is not balanced: debit={total_debit}, credit={total_credit}."
        )

    header = build_journal_header(
        context,
        posting_date,
        entry_type,
        description,
        total_debit,
        created_by_employee_id,
        approved_by_employee_id,
        reverses_journal_entry_id,
    )
    gl_rows = [
        build_journal_gl_row(
            context,
            int(header["JournalEntryID"]),
            str(header["EntryNumber"]),
            posting_date,
            str(line["AccountNumber"]),
            float(line["Debit"]),
            float(line["Credit"]),
            str(line["Description"]),
            created_by_employee_id,
            line.get("CostCenterID"),
        )
        for line in lines
    ]
    append_journal(context, header, gl_rows)
    return header


def payroll_amounts_by_cost_center(context: GenerationContext, year: int) -> dict[int, dict[str, float]]:
    employees = sorted_employees(context)
    cost_center_names = context.tables["CostCenter"].set_index("CostCenterID")["CostCenterName"].to_dict()
    growth_factor = 1.0 + ((year - 2026) * ANNUAL_GROWTH_RATE)
    salary_totals = {int(cost_center_id): 0.0 for cost_center_id in cost_center_names}

    for employee in employees.itertuples(index=False):
        if int(employee.IsActive) != 1:
            continue

        cost_center_name = cost_center_names[int(employee.CostCenterID)]
        jitter = stable_uniform(context, 0.94, 1.06, "employee-payroll", int(employee.EmployeeID))
        annual_salary = (
            BASE_ANNUAL_SALARIES[str(employee.AuthorizationLevel)]
            * COST_CENTER_MULTIPLIERS[cost_center_name]
            * growth_factor
            * jitter
        )
        salary_totals[int(employee.CostCenterID)] += annual_salary / 12.0

    return {
        cost_center_id: {
            "salary": money(salary_total),
            "benefits": money(salary_total * PAYROLL_BURDEN_RATE),
            "total": money(money(salary_total) + money(salary_total * PAYROLL_BURDEN_RATE)),
        }
        for cost_center_id, salary_total in salary_totals.items()
    }


def monthly_rent_amount(context: GenerationContext, year: int, month: int, rent_type: str) -> float:
    growth_factor = 1.0 + ((year - 2026) * ANNUAL_GROWTH_RATE)
    jitter = stable_uniform(context, 0.98, 1.02, "rent", rent_type, year, month)
    return money(MONTHLY_RENT_BASES[rent_type] * growth_factor * jitter)


def monthly_utilities_amount(context: GenerationContext, year: int, month: int) -> float:
    growth_factor = 1.0 + ((year - 2026) * ANNUAL_GROWTH_RATE)
    if month in {6, 7, 8}:
        seasonality = 1.12
    elif month in {1, 2, 12}:
        seasonality = 1.10
    else:
        seasonality = 1.00
    jitter = stable_uniform(context, 0.96, 1.04, "utilities", year, month)
    return money(9500.0 * growth_factor * seasonality * jitter)


def monthly_accrual_amount(context: GenerationContext, year: int, month: int, account_number: str) -> float:
    growth_factor = 1.0 + ((year - 2026) * ANNUAL_GROWTH_RATE)
    jitter = stable_uniform(context, 0.97, 1.03, "accrual", account_number, year, month)
    return money(MONTHLY_ACCRUAL_BASES[account_number] * growth_factor * jitter)


def monthly_depreciation_amount(asset_account_number: str) -> float:
    profile = fixed_asset_profile(asset_account_number)
    if profile.useful_life_months <= 0:
        return 0.0
    return money(float(profile.gross_opening_balance) / float(profile.useful_life_months))


def accumulated_depreciation_balance(context: GenerationContext, asset_account_number: str) -> float:
    profile = fixed_asset_profile(asset_account_number)
    accumulated_account_number = profile.accumulated_depreciation_account_number
    if not accumulated_account_number:
        return 0.0
    gl = context.tables["GLEntry"]
    if gl.empty:
        return 0.0
    account_rows = gl[gl["AccountID"].astype(int).eq(account_id_by_number(context, accumulated_account_number))]
    if account_rows.empty:
        return 0.0
    return money(float(account_rows["Credit"].astype(float).sum()) - float(account_rows["Debit"].astype(float).sum()))


def remaining_depreciable_base(context: GenerationContext, asset_account_number: str) -> float:
    profile = fixed_asset_profile(asset_account_number)
    return money(
        max(float(profile.gross_opening_balance) - float(accumulated_depreciation_balance(context, asset_account_number)), 0.0)
    )


def generate_payroll_accruals(context: GenerationContext, year: int, month: int) -> None:
    posting_date = last_calendar_day(year, month).strftime("%Y-%m-%d")
    cost_center_names = context.tables["CostCenter"].set_index("CostCenterID")["CostCenterName"].to_dict()
    payroll_totals = payroll_amounts_by_cost_center(context, year)
    approver_id = payroll_accrual_approver_id(context)

    for cost_center_id, amounts in payroll_totals.items():
        cost_center_name = cost_center_names[int(cost_center_id)]
        salary_account = SALARY_ACCOUNT_BY_COST_CENTER[cost_center_name]
        creator_id = cost_center_manager_id(context, int(cost_center_id))
        description = f"{cost_center_name} payroll accrual for {year}-{month:02d}"
        lines = [
            {
                "AccountNumber": salary_account,
                "Debit": amounts["salary"],
                "Credit": 0.0,
                "Description": f"{cost_center_name} salary accrual",
                "CostCenterID": int(cost_center_id),
            },
            {
                "AccountNumber": "6060",
                "Debit": amounts["benefits"],
                "Credit": 0.0,
                "Description": f"{cost_center_name} payroll burden accrual",
                "CostCenterID": int(cost_center_id),
            },
            {
                "AccountNumber": "2030",
                "Debit": 0.0,
                "Credit": amounts["total"],
                "Description": f"{cost_center_name} payroll liability accrual",
                "CostCenterID": None,
            },
        ]
        create_journal(
            context,
            posting_date,
            "Payroll Accrual",
            description,
            lines,
            creator_id,
            approver_id,
        )


def generate_payroll_settlements(context: GenerationContext, accrual_year: int, accrual_month: int, settlement_year: int, settlement_month: int) -> None:
    posting_timestamp = first_business_day(settlement_year, settlement_month)
    if not date_in_range(context, posting_timestamp):
        return

    posting_date = posting_timestamp.strftime("%Y-%m-%d")
    cost_center_names = context.tables["CostCenter"].set_index("CostCenterID")["CostCenterName"].to_dict()
    payroll_totals = payroll_amounts_by_cost_center(context, accrual_year)
    creator_id = payroll_settlement_creator_id(context)
    approver_id = payroll_settlement_approver_id(context)

    for cost_center_id, amounts in payroll_totals.items():
        description = f"{cost_center_names[int(cost_center_id)]} payroll settlement for {accrual_year}-{accrual_month:02d}"
        lines = [
            {
                "AccountNumber": "2030",
                "Debit": amounts["total"],
                "Credit": 0.0,
                "Description": "Settle accrued payroll",
                "CostCenterID": None,
            },
            {
                "AccountNumber": "1010",
                "Debit": 0.0,
                "Credit": amounts["total"],
                "Description": "Payroll cash disbursement",
                "CostCenterID": None,
            },
        ]
        create_journal(
            context,
            posting_date,
            "Payroll Settlement",
            description,
            lines,
            creator_id,
            approver_id,
        )


def generate_rent_journals(context: GenerationContext, year: int, month: int) -> None:
    posting_date = first_business_day(year, month).strftime("%Y-%m-%d")
    creator_id = accounting_journal_creator_id(context)
    approver_id = accounting_journal_approver_id(context)

    for rent_type, expense_account in [("Office", "6080"), ("Warehouse", "6070")]:
        amount = monthly_rent_amount(context, year, month, rent_type)
        create_journal(
            context,
            posting_date,
            "Rent",
            f"{rent_type} rent for {year}-{month:02d}",
            [
                {
                    "AccountNumber": expense_account,
                    "Debit": amount,
                    "Credit": 0.0,
                    "Description": f"{rent_type} rent expense",
                    "CostCenterID": None,
                },
                {
                    "AccountNumber": "1010",
                    "Debit": 0.0,
                    "Credit": amount,
                    "Description": f"{rent_type} rent cash payment",
                    "CostCenterID": None,
                },
            ],
            creator_id,
            approver_id,
        )


def generate_utilities_journal(context: GenerationContext, year: int, month: int) -> None:
    posting_date = last_business_day(year, month).strftime("%Y-%m-%d")
    amount = monthly_utilities_amount(context, year, month)
    creator_id = accounting_journal_creator_id(context)
    approver_id = accounting_journal_approver_id(context)
    create_journal(
        context,
        posting_date,
        "Utilities",
        f"Utilities expense for {year}-{month:02d}",
        [
            {
                "AccountNumber": "6090",
                "Debit": amount,
                "Credit": 0.0,
                "Description": "Utilities expense",
                "CostCenterID": None,
            },
            {
                "AccountNumber": "1010",
                "Debit": 0.0,
                "Credit": amount,
                "Description": "Utilities cash payment",
                "CostCenterID": None,
            },
        ],
        creator_id,
        approver_id,
    )


def manufacturing_completion_lines_for_month(context: GenerationContext, year: int, month: int) -> list[dict[str, Any]]:
    completion_headers = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completion_headers.empty or completion_lines.empty:
        return []

    month_mask = (
        pd.to_datetime(completion_headers["CompletionDate"]).dt.year.eq(year)
        & pd.to_datetime(completion_headers["CompletionDate"]).dt.month.eq(month)
    )
    monthly_headers = completion_headers.loc[month_mask, ["ProductionCompletionID", "WorkOrderID", "CompletionDate"]]
    if monthly_headers.empty:
        return []

    work_order_lookup = monthly_headers.set_index("ProductionCompletionID").to_dict("index")
    rows: list[dict[str, Any]] = []
    for line in completion_lines.itertuples(index=False):
        header = work_order_lookup.get(int(line.ProductionCompletionID))
        if header is None:
            continue
        rows.append({
            "WorkOrderID": int(header["WorkOrderID"]),
            "CompletionDate": str(header["CompletionDate"]),
            "StandardConversionCost": float(line.ExtendedStandardConversionCost),
        })
    return rows


def monthly_manufacturing_conversion_totals(context: GenerationContext, year: int, month: int) -> dict[str, float]:
    salary_total = monthly_direct_labor_reclass_amount(context, year, month)
    overhead_total = monthly_manufacturing_overhead_pool_amount(context, year, month)
    return {
        "actual_total": money(float(salary_total) + float(overhead_total)),
        "salary_total": money(float(salary_total)),
        "overhead_total": money(float(overhead_total)),
    }


def manufacturing_journal_creator_id(context: GenerationContext) -> int:
    return employee_id_by_titles(context, "Production Manager", "Controller", "Accounting Manager") or first_executive_id(context)


def manufacturing_journal_approver_id(context: GenerationContext) -> int:
    return employee_id_by_titles(context, "Controller", "Chief Financial Officer") or first_executive_id(context)


def generate_factory_overhead_journal(context: GenerationContext, year: int, month: int) -> None:
    overhead_total = float(monthly_factory_overhead_amount(context, year, month))
    if overhead_total <= 0:
        return

    posting_date = last_business_day(year, month).strftime("%Y-%m-%d")
    creator_id = manufacturing_journal_creator_id(context)
    approver_id = manufacturing_journal_approver_id(context)
    create_journal(
        context,
        posting_date,
        "Factory Overhead",
        f"Factory overhead for {year}-{month:02d}",
        [
            {
                "AccountNumber": "6270",
                "Debit": overhead_total,
                "Credit": 0.0,
                "Description": "Factory overhead expense",
                "CostCenterID": None,
            },
            {
                "AccountNumber": "1010",
                "Debit": 0.0,
                "Credit": overhead_total,
                "Description": "Factory overhead cash payment",
                "CostCenterID": None,
            },
        ],
        creator_id,
        approver_id,
    )


def generate_direct_labor_reclass_journal(context: GenerationContext, year: int, month: int) -> None:
    salary_total = float(monthly_direct_labor_reclass_amount(context, year, month))
    if salary_total <= 0:
        return

    posting_date = last_business_day(year, month).strftime("%Y-%m-%d")
    creator_id = manufacturing_journal_creator_id(context)
    approver_id = manufacturing_journal_approver_id(context)
    create_journal(
        context,
        posting_date,
        "Direct Labor Reclass",
        f"Direct labor reclass for {year}-{month:02d}",
        [
            {
                "AccountNumber": "1090",
                "Debit": salary_total,
                "Credit": 0.0,
                "Description": "Reclass direct labor to manufacturing clearing",
                "CostCenterID": None,
            },
            {
                "AccountNumber": "6260",
                "Debit": 0.0,
                "Credit": salary_total,
                "Description": "Credit manufacturing labor expense",
                "CostCenterID": None,
            },
        ],
        creator_id,
        approver_id,
    )


def generate_manufacturing_overhead_reclass_journal(context: GenerationContext, year: int, month: int) -> None:
    overhead_total = float(monthly_manufacturing_overhead_pool_amount(context, year, month))
    if overhead_total <= 0:
        return

    posting_date = last_business_day(year, month).strftime("%Y-%m-%d")
    creator_id = manufacturing_journal_creator_id(context)
    approver_id = manufacturing_journal_approver_id(context)
    create_journal(
        context,
        posting_date,
        "Manufacturing Overhead Reclass",
        f"Manufacturing overhead reclass for {year}-{month:02d}",
        [
            {
                "AccountNumber": "1090",
                "Debit": overhead_total,
                "Credit": 0.0,
                "Description": "Reclass manufacturing overhead to clearing",
                "CostCenterID": None,
            },
            {
                "AccountNumber": "6270",
                "Debit": 0.0,
                "Credit": overhead_total,
                "Description": "Credit manufacturing overhead expense",
                "CostCenterID": None,
            },
        ],
        creator_id,
        approver_id,
    )


def generate_depreciation_journals(context: GenerationContext, year: int, month: int) -> None:
    posting_date = last_calendar_day(year, month).strftime("%Y-%m-%d")
    creator_id = close_journal_creator_id(context)
    approver_id = close_journal_approver_id(context)
    for asset_account_number, profile in depreciable_fixed_asset_profiles().items():
        asset_description = f"{profile.description} depreciation"
        amount = money(min(monthly_depreciation_amount(asset_account_number), remaining_depreciable_base(context, asset_account_number)))
        if amount <= 0:
            continue
        create_journal(
            context,
            posting_date,
            "Depreciation",
            f"{asset_description} for {year}-{month:02d}",
            [
                {
                    "AccountNumber": "6130",
                    "Debit": amount,
                    "Credit": 0.0,
                    "Description": asset_description,
                    "CostCenterID": None,
                },
                {
                    "AccountNumber": str(profile.accumulated_depreciation_account_number),
                    "Debit": 0.0,
                    "Credit": amount,
                    "Description": f"Accumulated depreciation for {asset_description.lower()}",
                    "CostCenterID": None,
                },
            ],
            creator_id,
            approver_id,
        )


def generate_month_end_accruals(context: GenerationContext, year: int, month: int) -> list[dict[str, Any]]:
    posting_date = last_business_day(year, month).strftime("%Y-%m-%d")
    creator_id = accounting_journal_creator_id(context)
    approver_id = accounting_journal_approver_id(context)
    accrual_rows: list[dict[str, Any]] = []
    for account_number, metadata in ACCRUAL_ACCOUNT_METADATA.items():
        amount = monthly_accrual_amount(context, year, month, account_number)
        lines = [
            {
                "AccountNumber": account_number,
                "Debit": amount,
                "Credit": 0.0,
                "Description": metadata["description"],
                "CostCenterID": None,
            },
            {
                "AccountNumber": "2040",
                "Debit": 0.0,
                "Credit": amount,
                "Description": f"Accrued expenses liability for {metadata['description'].lower()}",
                "CostCenterID": None,
            },
        ]
        header = create_journal(
            context,
            posting_date,
            "Accrual",
            f"{metadata['journal_description']} for {year}-{month:02d}",
            lines,
            creator_id,
            approver_id,
        )
        accrual_rows.append({
            "JournalEntryID": int(header["JournalEntryID"]),
            "PostingDate": posting_date,
            "ExpenseAccountNumber": account_number,
            "Amount": amount,
        })
    return accrual_rows


def accrual_journal_details(context: GenerationContext) -> list[dict[str, Any]]:
    journal_entries = context.tables["JournalEntry"]
    gl = context.tables["GLEntry"]
    accounts = context.tables["Account"].set_index("AccountID")["AccountNumber"].astype(str).to_dict()
    accrual_entries = journal_entries[journal_entries["EntryType"].eq("Accrual")].copy()
    if accrual_entries.empty:
        return []

    source_gl = gl[
        gl["VoucherType"].eq("JournalEntry")
        & gl["SourceDocumentType"].eq("JournalEntry")
        & gl["SourceDocumentID"].notna()
    ].copy()
    details: list[dict[str, Any]] = []
    for journal in accrual_entries.itertuples(index=False):
        linked_rows = source_gl[source_gl["SourceDocumentID"].astype(int).eq(int(journal.JournalEntryID))]
        expense_rows = linked_rows[linked_rows["Debit"].astype(float).gt(0)]
        for row in expense_rows.itertuples(index=False):
            account_number = accounts.get(int(row.AccountID))
            if account_number not in ACCRUAL_ACCOUNT_METADATA:
                continue
            details.append({
                "JournalEntryID": int(journal.JournalEntryID),
                "PostingDate": str(journal.PostingDate),
                "ExpenseAccountNumber": account_number,
                "Amount": money(float(row.Debit)),
            })
            break
    return details


def generate_accrual_adjustment_journals(context: GenerationContext) -> None:
    journal_entries = context.tables["JournalEntry"]
    if journal_entries.empty:
        return

    existing_adjustments = journal_entries[journal_entries["EntryType"].eq("Accrual Adjustment")]
    if not existing_adjustments.empty:
        raise ValueError("Accrual adjustment journals have already been generated.")

    purchase_invoice_lines = context.tables["PurchaseInvoiceLine"]
    purchase_invoices = context.tables["PurchaseInvoice"]
    if purchase_invoice_lines.empty or purchase_invoices.empty:
        return

    invoice_headers = purchase_invoices.set_index("PurchaseInvoiceID")[["ApprovedDate", "InvoiceDate"]].to_dict("index")
    linked_invoice_lines = purchase_invoice_lines[purchase_invoice_lines["AccrualJournalEntryID"].notna()].copy()
    settled_by_accrual: dict[int, float] = {}
    invoice_ids_by_accrual: dict[int, set[int]] = {}
    for line in linked_invoice_lines.itertuples(index=False):
        accrual_id = int(line.AccrualJournalEntryID)
        settled_by_accrual[accrual_id] = money(float(settled_by_accrual.get(accrual_id, 0.0)) + float(line.LineTotal))
        invoice_ids_by_accrual.setdefault(accrual_id, set()).add(int(line.PurchaseInvoiceID))

    creator_id = accounting_journal_creator_id(context)
    approver_id = accounting_journal_approver_id(context)
    fiscal_end = pd.Timestamp(context.settings.fiscal_year_end)
    invoice_linked_adjustments: list[dict[str, Any]] = []
    eligible_adjustments_by_year: dict[int, list[dict[str, Any]]] = {}
    for accrual in accrual_journal_details(context):
        accrual_id = int(accrual["JournalEntryID"])
        accrual_amount = float(accrual["Amount"])
        settled_amount = float(settled_by_accrual.get(accrual_id, 0.0))
        residual_amount = money(accrual_amount - min(accrual_amount, settled_amount))
        account_number = str(accrual["ExpenseAccountNumber"])
        metadata = ACCRUAL_ACCOUNT_METADATA[account_number]
        linked_invoice_ids = sorted(invoice_ids_by_accrual.get(accrual_id, set()))
        if linked_invoice_ids:
            if residual_amount <= 0:
                continue

            invoice_approval_dates = []
            for invoice_id in linked_invoice_ids:
                invoice_header = invoice_headers.get(invoice_id)
                if invoice_header is None:
                    continue
                approval_value = invoice_header.get("ApprovedDate")
                if pd.isna(approval_value):
                    approval_value = invoice_header.get("InvoiceDate")
                if pd.isna(approval_value):
                    continue
                invoice_approval_dates.append(pd.Timestamp(approval_value))
            if not invoice_approval_dates:
                continue

            posting_timestamp = first_business_day_on_or_after(max(invoice_approval_dates))
            if not date_in_range(context, posting_timestamp):
                continue
            invoice_linked_adjustments.append({
                "JournalEntryID": accrual_id,
                "PostingDate": posting_timestamp.strftime("%Y-%m-%d"),
                "ExpenseAccountNumber": account_number,
                "Amount": residual_amount,
                "Description": metadata["description"],
                "AccrualPostingDate": accrual["PostingDate"],
            })
            continue

        if residual_amount < ACCRUAL_ADJUSTMENT_MIN_AMOUNT:
            continue

        accrual_date = pd.Timestamp(accrual["PostingDate"])
        earliest_adjustment_date = accrual_date + pd.Timedelta(days=ACCRUAL_ADJUSTMENT_MIN_AGE_DAYS)
        if earliest_adjustment_date > fiscal_end:
            continue

        adjustment_month = pd.Timestamp(year=earliest_adjustment_date.year, month=earliest_adjustment_date.month, day=1)
        posting_timestamp = first_business_day(int(adjustment_month.year), int(adjustment_month.month))
        if posting_timestamp < earliest_adjustment_date:
            posting_timestamp = first_business_day(*next_month(int(adjustment_month.year), int(adjustment_month.month)))
        if not date_in_range(context, posting_timestamp):
            continue

        adjustment_factor = stable_uniform(context, 0.35, 0.80, "accrual-adjustment-factor", accrual_id)
        adjustment_amount = money(residual_amount * adjustment_factor)
        if adjustment_amount <= 0 or adjustment_amount >= residual_amount:
            continue

        adjustment_year = int(posting_timestamp.year)
        eligible_adjustments_by_year.setdefault(adjustment_year, []).append({
            "JournalEntryID": accrual_id,
            "PostingDate": posting_timestamp.strftime("%Y-%m-%d"),
            "ExpenseAccountNumber": account_number,
            "Amount": adjustment_amount,
            "ResidualAmount": residual_amount,
            "Description": metadata["description"],
            "AccrualPostingDate": accrual["PostingDate"],
        })

    for candidate in sorted(
        invoice_linked_adjustments,
        key=lambda candidate: (candidate["PostingDate"], candidate["JournalEntryID"]),
    ):
        create_journal(
            context,
            candidate["PostingDate"],
            "Accrual Adjustment",
            f"Settle residual {candidate['Description'].lower()} after linked supplier invoice",
            [
                {
                    "AccountNumber": "2040",
                    "Debit": float(candidate["Amount"]),
                    "Credit": 0.0,
                    "Description": "Clear residual accrued expenses after invoice settlement",
                    "CostCenterID": None,
                },
                {
                    "AccountNumber": str(candidate["ExpenseAccountNumber"]),
                    "Debit": 0.0,
                    "Credit": float(candidate["Amount"]),
                    "Description": f"Reverse residual {candidate['Description'].lower()} estimate",
                    "CostCenterID": None,
                },
            ],
            creator_id,
            approver_id,
            int(candidate["JournalEntryID"]),
        )

    for year, candidates in eligible_adjustments_by_year.items():
        candidates = sorted(
            candidates,
            key=lambda candidate: (
                candidate["PostingDate"],
                -float(candidate["ResidualAmount"]),
                stable_seed(context, "accrual-adjustment-order", year, candidate["JournalEntryID"]),
            ),
        )
        for candidate in candidates[:ACCRUAL_ADJUSTMENTS_PER_YEAR]:
            create_journal(
                context,
                candidate["PostingDate"],
                "Accrual Adjustment",
                f"Partial cleanup of residual {candidate['Description'].lower()} accrual from {candidate['AccrualPostingDate']}",
                [
                    {
                        "AccountNumber": "2040",
                        "Debit": float(candidate["Amount"]),
                        "Credit": 0.0,
                        "Description": "Reduce residual accrued expenses liability",
                        "CostCenterID": None,
                    },
                    {
                        "AccountNumber": str(candidate["ExpenseAccountNumber"]),
                        "Debit": 0.0,
                        "Credit": float(candidate["Amount"]),
                        "Description": f"Reduce residual {candidate['Description'].lower()} estimate",
                        "CostCenterID": None,
                    },
                ],
                creator_id,
                approver_id,
                int(candidate["JournalEntryID"]),
            )


def generate_recurring_manual_journals(context: GenerationContext) -> None:
    if context.tables["JournalEntry"].empty or context.tables["GLEntry"].empty:
        raise ValueError("Generate opening balances before recurring manual journals.")

    existing_non_opening = context.tables["JournalEntry"][~context.tables["JournalEntry"]["EntryType"].eq("Opening")]
    if not existing_non_opening.empty:
        raise ValueError("Recurring manual journals have already been generated.")

    for year, month in fiscal_months(context):
        generate_rent_journals(context, year, month)
        generate_utilities_journal(context, year, month)
        generate_factory_overhead_journal(context, year, month)
        generate_direct_labor_reclass_journal(context, year, month)
        generate_manufacturing_overhead_reclass_journal(context, year, month)
        generate_depreciation_journals(context, year, month)
        generate_month_end_accruals(context, year, month)


def close_account_lines_for_year(context: GenerationContext, year: int) -> list[dict[str, Any]]:
    gl = context.tables["GLEntry"]
    accounts = context.tables["Account"].copy()
    fiscal_gl = gl[gl["FiscalYear"].astype(int).eq(int(year))]
    balances = fiscal_gl.groupby("AccountID")[["Debit", "Credit"]].sum()
    pl_accounts = accounts[
        accounts["AccountType"].isin(["Revenue", "Expense"])
        & accounts["AccountSubType"].ne("Header")
    ].sort_values("AccountNumber")

    lines: list[dict[str, Any]] = []
    for account in pl_accounts.itertuples(index=False):
        totals = balances.loc[int(account.AccountID)] if int(account.AccountID) in balances.index else None
        if totals is None:
            continue
        net_balance = round(float(totals["Debit"]) - float(totals["Credit"]), 2)
        if net_balance == 0:
            continue

        if net_balance > 0:
            lines.append({
                "AccountNumber": str(account.AccountNumber),
                "Debit": 0.0,
                "Credit": abs(net_balance),
                "Description": f"Close {account.AccountName}",
                "CostCenterID": None,
            })
        else:
            lines.append({
                "AccountNumber": str(account.AccountNumber),
                "Debit": abs(net_balance),
                "Credit": 0.0,
                "Description": f"Close {account.AccountName}",
                "CostCenterID": None,
            })

    total_debits = money(sum(float(line["Debit"]) for line in lines))
    total_credits = money(sum(float(line["Credit"]) for line in lines))
    difference = money(total_debits - total_credits)
    if difference > 0:
        lines.append({
            "AccountNumber": "8010",
            "Debit": 0.0,
            "Credit": difference,
            "Description": "Close profit and loss accounts to income summary",
            "CostCenterID": None,
        })
    elif difference < 0:
        lines.append({
            "AccountNumber": "8010",
            "Debit": abs(difference),
            "Credit": 0.0,
            "Description": "Close profit and loss accounts to income summary",
            "CostCenterID": None,
        })

    return lines


def generate_year_end_close_journals(context: GenerationContext) -> None:
    close_entry_types = {
        "Year-End Close - P&L to Income Summary",
        "Year-End Close - Income Summary to Retained Earnings",
    }
    existing_close_entries = context.tables["JournalEntry"][
        context.tables["JournalEntry"]["EntryType"].isin(close_entry_types)
    ]
    if not existing_close_entries.empty:
        raise ValueError("Year-end close journals have already been generated.")

    creator_id = close_journal_creator_id(context)
    approver_id = close_journal_approver_id(context)

    for year in range(pd.Timestamp(context.settings.fiscal_year_start).year, pd.Timestamp(context.settings.fiscal_year_end).year + 1):
        posting_date = f"{year}-12-31"
        pl_close_lines = close_account_lines_for_year(context, year)
        if len(pl_close_lines) <= 1:
            continue

        create_journal(
            context,
            posting_date,
            "Year-End Close - P&L to Income Summary",
            f"Close {year} revenue and expense accounts to income summary",
            pl_close_lines,
            creator_id,
            approver_id,
        )

        fiscal_gl = context.tables["GLEntry"]
        fiscal_gl = fiscal_gl[fiscal_gl["FiscalYear"].astype(int).eq(int(year))]
        income_summary_id = account_id_by_number(context, "8010")
        income_summary_rows = fiscal_gl[fiscal_gl["AccountID"].astype(int).eq(income_summary_id)]
        income_summary_balance = round(
            float(income_summary_rows["Debit"].sum()) - float(income_summary_rows["Credit"].sum()),
            2,
        )
        if income_summary_balance == 0:
            continue

        if income_summary_balance > 0:
            close_lines = [
                {
                    "AccountNumber": "3030",
                    "Debit": income_summary_balance,
                    "Credit": 0.0,
                    "Description": f"Close {year} loss to retained earnings",
                    "CostCenterID": None,
                },
                {
                    "AccountNumber": "8010",
                    "Debit": 0.0,
                    "Credit": income_summary_balance,
                    "Description": f"Clear income summary for {year}",
                    "CostCenterID": None,
                },
            ]
        else:
            close_lines = [
                {
                    "AccountNumber": "8010",
                    "Debit": abs(income_summary_balance),
                    "Credit": 0.0,
                    "Description": f"Clear income summary for {year}",
                    "CostCenterID": None,
                },
                {
                    "AccountNumber": "3030",
                    "Debit": 0.0,
                    "Credit": abs(income_summary_balance),
                    "Description": f"Close {year} earnings to retained earnings",
                    "CostCenterID": None,
                },
            ]

        create_journal(
            context,
            posting_date,
            "Year-End Close - Income Summary to Retained Earnings",
            f"Close {year} income summary to retained earnings",
            close_lines,
            creator_id,
            approver_id,
        )
