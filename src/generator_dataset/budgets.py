from __future__ import annotations

import pandas as pd

from generator_dataset.master_data import approver_employee_id, current_role_employee_id
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.settings import GenerationContext
from generator_dataset.utils import money, next_id


OPENING_BALANCE_AMOUNTS = {
    "1010": ("Cash and cash equivalents opening balance", 450000.00, 0.00),
    "1020": ("Accounts receivable opening balance", 380000.00, 0.00),
    "1040": ("Finished goods inventory opening balance", 720000.00, 0.00),
    "1045": ("Materials and packaging inventory opening balance", 115000.00, 0.00),
    "1050": ("Prepaid expenses opening balance", 60000.00, 0.00),
    "1110": ("Furniture and fixtures opening balance", 260000.00, 0.00),
    "1120": ("Warehouse equipment opening balance", 850000.00, 0.00),
    "1130": ("Office equipment opening balance", 180000.00, 0.00),
    "1150": ("Accumulated depreciation furniture opening balance", 0.00, 90000.00),
    "1160": ("Accumulated depreciation warehouse equipment opening balance", 0.00, 230000.00),
    "1170": ("Accumulated depreciation office equipment opening balance", 0.00, 75000.00),
    "2010": ("Accounts payable opening balance", 0.00, 410000.00),
    "2030": ("Accrued payroll opening balance", 0.00, 95000.00),
    "2040": ("Accrued expenses opening balance", 0.00, 85000.00),
    "3010": ("Common stock opening balance", 0.00, 500000.00),
}

BUDGET_ACCOUNTS_BY_COST_CENTER = {
    "Executive": ["6050", "6080", "6100", "6130", "6180"],
    "Sales": ["4010", "4020", "4030", "4040", "6010", "6150", "6160", "6170"],
    "Warehouse": ["6020", "6070", "6090", "6120", "6130", "6210"],
    "Manufacturing": ["6260", "6270", "6110", "6120", "6130", "6140"],
    "Purchasing": ["6230", "6110", "6140", "6180", "6200"],
    "Administration": ["6030", "6080", "6090", "6100", "6110", "6130", "6140", "6180", "6190", "6200"],
    "Customer Service": ["6040", "6080", "6090", "6110", "6140"],
    "Research and Development": ["6220", "6250", "6140", "6110", "6200"],
    "Marketing": ["6150", "6160", "6240", "6140", "6200"],
}

BASE_MONTHLY_BUDGET = {
    "4010": 170000.00,
    "4020": 85000.00,
    "4030": 76000.00,
    "4040": 62000.00,
    "6010": 56000.00,
    "6020": 48000.00,
    "6030": 42000.00,
    "6040": 36000.00,
    "6050": 52000.00,
    "6070": 39000.00,
    "6080": 18000.00,
    "6090": 12000.00,
    "6100": 9000.00,
    "6110": 6500.00,
    "6120": 10500.00,
    "6130": 22000.00,
    "6140": 14000.00,
    "6150": 30000.00,
    "6160": 9500.00,
    "6170": 5500.00,
    "6180": 15000.00,
    "6190": 3500.00,
    "6200": 8000.00,
    "6210": 9000.00,
    "6220": 24000.00,
    "6230": 42000.00,
    "6240": 38000.00,
    "6250": 44000.00,
    "6260": 51000.00,
    "6270": 26000.00,
}


def account_id_by_number(context: GenerationContext, account_number: str) -> int:
    accounts = context.tables["Account"]
    matches = accounts.loc[accounts["AccountNumber"].astype(str) == account_number, "AccountID"]
    if matches.empty:
        raise ValueError(f"Account number {account_number} is not loaded.")
    return int(matches.iloc[0])


def opening_balance_approver_id(context: GenerationContext) -> int:
    approver_id = current_role_employee_id(context, "Chief Financial Officer", "Controller", "Chief Executive Officer")
    if approver_id is not None:
        return int(approver_id)
    employees = context.tables["Employee"]
    if employees.empty:
        raise ValueError("Generate employees before opening balances.")
    return int(employees.sort_values("EmployeeID").iloc[0]["EmployeeID"])


def build_gl_row(
    context: GenerationContext,
    journal_entry_id: int,
    posting_date: str,
    account_number: str,
    debit: float,
    credit: float,
    description: str,
    created_by_employee_id: int,
) -> dict:
    ts = pd.Timestamp(posting_date)
    return {
        "GLEntryID": next_id(context, "GLEntry"),
        "PostingDate": posting_date,
        "AccountID": account_id_by_number(context, account_number),
        "Debit": money(debit),
        "Credit": money(credit),
        "VoucherType": "JournalEntry",
        "VoucherNumber": "JE-2026-000001",
        "SourceDocumentType": "JournalEntry",
        "SourceDocumentID": journal_entry_id,
        "SourceLineID": None,
        "CostCenterID": None,
        "Description": description,
        "CreatedByEmployeeID": created_by_employee_id,
        "CreatedDate": "2026-01-01 08:00:00",
        "FiscalYear": int(ts.year),
        "FiscalPeriod": int(ts.month),
    }


def generate_opening_balances(context: GenerationContext) -> None:
    if context.tables["Account"].empty:
        raise ValueError("Load accounts before opening balances.")
    if not context.tables["JournalEntry"].empty or not context.tables["GLEntry"].empty:
        raise ValueError("Opening balances should be generated before other journal or GL rows.")

    approver_id = opening_balance_approver_id(context)
    posting_date = "2026-01-01"
    journal_entry_id = next_id(context, "JournalEntry")
    debit_total = sum(amount[1] for amount in OPENING_BALANCE_AMOUNTS.values())
    credit_total = sum(amount[2] for amount in OPENING_BALANCE_AMOUNTS.values())
    retained_earnings_credit = money(debit_total - credit_total)
    if retained_earnings_credit <= 0:
        raise ValueError("Opening balance retained earnings plug must be a credit.")

    journal_record = {
        "JournalEntryID": journal_entry_id,
        "EntryNumber": "JE-2026-000001",
        "PostingDate": posting_date,
        "EntryType": "Opening",
        "Description": "Opening balance entry for January 1, 2026",
        "TotalAmount": money(debit_total),
        "CreatedByEmployeeID": approver_id,
        "CreatedDate": "2026-01-01 08:00:00",
        "ApprovedByEmployeeID": approver_id,
        "ApprovedDate": "2026-01-01 09:00:00",
        "ReversesJournalEntryID": None,
    }

    gl_rows = []
    for account_number, (description, debit, credit) in OPENING_BALANCE_AMOUNTS.items():
        gl_rows.append(build_gl_row(
            context,
            journal_entry_id,
            posting_date,
            account_number,
            debit,
            credit,
            description,
            approver_id,
        ))

    gl_rows.append(build_gl_row(
        context,
        journal_entry_id,
        posting_date,
        "3030",
        0.00,
        retained_earnings_credit,
        "Retained earnings opening balance",
        approver_id,
    ))

    total_debits = round(sum(row["Debit"] for row in gl_rows), 2)
    total_credits = round(sum(row["Credit"] for row in gl_rows), 2)
    if total_debits != total_credits:
        raise ValueError(f"Opening balance is not balanced: debit={total_debits}, credit={total_credits}")

    context.tables["JournalEntry"] = pd.DataFrame([journal_record], columns=TABLE_COLUMNS["JournalEntry"])
    context.tables["GLEntry"] = pd.DataFrame(gl_rows, columns=TABLE_COLUMNS["GLEntry"])


def budget_approver_id(context: GenerationContext) -> int:
    return approver_employee_id(
        context,
        context.settings.fiscal_year_start,
        preferred_titles=["Chief Financial Officer", "Controller", "Accounting Manager"],
        fallback_cost_center_name="Administration",
    )


def generate_budgets(context: GenerationContext) -> None:
    if context.tables["CostCenter"].empty or context.tables["Account"].empty or context.tables["Employee"].empty:
        raise ValueError("Generate cost centers, accounts, and employees before budgets.")

    rng = context.rng
    approver_id = budget_approver_id(context)
    cost_centers = context.tables["CostCenter"][["CostCenterID", "CostCenterName"]]
    rows = []

    for fiscal_year in range(2026, 2031):
        growth_factor = 1.0 + ((fiscal_year - 2026) * 0.035)
        approved_date = f"{fiscal_year - 1}-12-15"
        for cost_center in cost_centers.itertuples(index=False):
            account_numbers = BUDGET_ACCOUNTS_BY_COST_CENTER[cost_center.CostCenterName]
            for account_number in account_numbers:
                account_id = account_id_by_number(context, account_number)
                base_amount = BASE_MONTHLY_BUDGET[account_number]
                for month in range(1, 13):
                    seasonality = 1.0 + (0.10 if month in [9, 10, 11] else 0.0) + (0.06 if month in [3, 4] else 0.0)
                    noise = rng.uniform(0.96, 1.04)
                    rows.append({
                        "BudgetID": next_id(context, "Budget"),
                        "FiscalYear": fiscal_year,
                        "CostCenterID": int(cost_center.CostCenterID),
                        "AccountID": account_id,
                        "Month": month,
                        "BudgetAmount": money(base_amount * growth_factor * seasonality * noise),
                        "ApprovedByEmployeeID": approver_id,
                        "ApprovedDate": approved_date,
                    })

    context.tables["Budget"] = pd.DataFrame(rows, columns=TABLE_COLUMNS["Budget"])
