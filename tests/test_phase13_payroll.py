from __future__ import annotations

import pandas as pd

from generator_dataset.main import build_phase13, build_phase23
from generator_dataset.payroll import monthly_direct_labor_reclass_amount
from generator_dataset.posting_engine import (
    PAYROLL_SUMMARY_SOURCE_DOCUMENT_TYPE,
    account_id_by_number,
    payroll_account_numbers,
)
from generator_dataset.schema import TABLE_COLUMNS


def test_phase13_schema_extensions_exist() -> None:
    for table_name in [
        "PayrollPeriod",
        "LaborTimeEntry",
        "PayrollRegister",
        "PayrollRegisterLine",
        "PayrollPayment",
        "PayrollLiabilityRemittance",
    ]:
        assert table_name in TABLE_COLUMNS

    for column_name in [
        "PayClass",
        "BaseHourlyRate",
        "BaseAnnualSalary",
        "StandardHoursPerWeek",
        "OvertimeEligible",
    ]:
        assert column_name in TABLE_COLUMNS["Employee"]

    for column_name in [
        "StandardLaborHoursPerUnit",
        "StandardDirectLaborCost",
        "StandardVariableOverheadCost",
        "StandardFixedOverheadCost",
    ]:
        assert column_name in TABLE_COLUMNS["Item"]


def test_phase13_helper_generates_clean_payroll_and_costing_dataset() -> None:
    context = build_phase13()
    phase13 = context.validation_results["phase13"]

    assert phase13["exceptions"] == []
    assert phase13["payroll_controls"]["exception_count"] == 0
    assert len(context.tables["PayrollPeriod"]) > 0
    assert len(context.tables["LaborTimeEntry"]) > 0
    assert len(context.tables["PayrollRegister"]) > 0
    assert len(context.tables["PayrollRegisterLine"]) > 0
    assert len(context.tables["PayrollPayment"]) > 0
    assert len(context.tables["PayrollLiabilityRemittance"]) > 0

    processed_periods = context.tables["PayrollPeriod"][context.tables["PayrollPeriod"]["Status"].eq("Processed")]
    assert len(processed_periods) > 0
    assert pd.to_datetime(processed_periods["PeriodStartDate"]).sort_values().is_monotonic_increasing

    labor_entries = context.tables["LaborTimeEntry"]
    direct_entries = labor_entries[labor_entries["LaborType"].eq("Direct Manufacturing")].copy()
    assert len(direct_entries) > 0
    assert direct_entries["WorkOrderID"].notna().all()

    work_orders = context.tables["WorkOrder"].set_index("WorkOrderID")
    items = context.tables["Item"].set_index("ItemID")
    assert direct_entries["WorkOrderID"].astype(int).map(work_orders["ItemID"]).map(items["SupplyMode"]).eq("Manufactured").all()


def test_phase13_full_dataset_clean_validation(full_dataset_artifacts: dict[str, object]) -> None:
    context = full_dataset_artifacts["context"]
    phase13 = context.validation_results["phase13"]
    row_counts = phase13["row_counts"]

    assert phase13["exceptions"] == []
    assert phase13["gl_balance"]["exception_count"] == 0
    assert phase13["trial_balance_difference"] == 0
    assert phase13["account_rollforward"]["exception_count"] == 0
    assert phase13["o2c_controls"]["exception_count"] == 0
    assert phase13["p2p_controls"]["exception_count"] == 0
    assert phase13["journal_controls"]["exception_count"] == 0
    assert phase13["manufacturing_controls"]["exception_count"] == 0
    assert phase13["payroll_controls"]["exception_count"] == 0

    assert row_counts["PayrollPeriod"] > 100
    assert row_counts["LaborTimeEntry"] > 0
    assert row_counts["PayrollRegister"] > 0
    assert row_counts["PayrollRegisterLine"] > row_counts["PayrollRegister"]
    assert row_counts["PayrollPayment"] == row_counts["PayrollRegister"]
    assert row_counts["PayrollLiabilityRemittance"] > 0


def test_phase13_payroll_gl_is_summarized_and_ties_to_payroll_tables() -> None:
    context = build_phase23("config/settings_validation.yaml", validation_scope="full")
    gl = context.tables["GLEntry"].copy()
    registers = context.tables["PayrollRegister"].copy()
    register_lines = context.tables["PayrollRegisterLine"].copy()
    payroll_periods = context.tables["PayrollPeriod"].copy()
    cost_centers = context.tables["CostCenter"].copy()
    payroll_payments = context.tables["PayrollPayment"].copy()

    assert getattr(context, "payroll_gl_summary_mode", {}).get("register") == "period_cost_center_account"
    assert PAYROLL_SUMMARY_SOURCE_DOCUMENT_TYPE in set(gl["SourceDocumentType"].astype(str))
    assert "PayrollRegister" not in set(gl["SourceDocumentType"].astype(str))

    summary_rows = gl[gl["SourceDocumentType"].eq(PAYROLL_SUMMARY_SOURCE_DOCUMENT_TYPE)].copy()
    assert not summary_rows.empty
    assert summary_rows["VoucherType"].eq("PayrollSummary").all()
    assert summary_rows["SourceLineID"].isna().all()

    payroll_period_lookup = payroll_periods.set_index("PayrollPeriodID").to_dict("index")
    cost_center_names = cost_centers.set_index("CostCenterID")["CostCenterName"].to_dict()
    lines_by_register = {key: value for key, value in register_lines.groupby("PayrollRegisterID")}
    salary_accounts = payroll_account_numbers(context)
    accrued_payroll_account_id = account_id_by_number(context, "2030")
    withholdings_account_id = account_id_by_number(context, "2031")
    employer_tax_account_id = account_id_by_number(context, "2032")
    benefits_account_id = account_id_by_number(context, "2033")
    burden_expense_account_id = account_id_by_number(context, "6060")
    manufacturing_clearing_account_id = account_id_by_number(context, "1090")
    manufacturing_variance_account_id = account_id_by_number(context, "5080")
    cash_account_id = account_id_by_number(context, "1010")

    expected_summary: dict[tuple[str, int, int], dict[str, float]] = {}

    def add_expected(posting_date: str, cost_center_id: int, account_id: int, debit: float, credit: float) -> None:
        key = (str(posting_date), int(cost_center_id), int(account_id))
        existing = expected_summary.setdefault(key, {"Debit": 0.0, "Credit": 0.0})
        existing["Debit"] = round(float(existing["Debit"]) + float(debit), 2)
        existing["Credit"] = round(float(existing["Credit"]) + float(credit), 2)

    for register in registers.itertuples(index=False):
        pay_date = pd.Timestamp(payroll_period_lookup[int(register.PayrollPeriodID)]["PayDate"]).strftime("%Y-%m-%d")
        pay_year = pd.Timestamp(pay_date).year
        pay_month = pd.Timestamp(pay_date).month
        capitalizable_manufacturing_month = monthly_direct_labor_reclass_amount(context, pay_year, pay_month) > 0
        cost_center_id = int(register.CostCenterID)
        cost_center_name = str(cost_center_names[cost_center_id])
        register_line_group = lines_by_register.get(int(register.PayrollRegisterID))
        assert register_line_group is not None and not register_line_group.empty

        employee_tax_withholding = 0.0
        benefits_and_deductions = 0.0

        for line in register_line_group.itertuples(index=False):
            line_type = str(line.LineType)
            amount = float(line.Amount)
            if line_type in {"Regular Earnings", "Overtime Earnings", "Salary Earnings", "Bonus"}:
                if cost_center_name == "Manufacturing":
                    debit_account_id = (
                        manufacturing_clearing_account_id
                        if pd.notna(line.WorkOrderID) or capitalizable_manufacturing_month
                        else manufacturing_variance_account_id
                    )
                else:
                    debit_account_id = account_id_by_number(context, salary_accounts[cost_center_id])
                add_expected(pay_date, cost_center_id, int(debit_account_id), amount, 0.0)
            elif line_type == "Employee Tax Withholding":
                employee_tax_withholding += amount
            elif line_type == "Benefits Deduction":
                benefits_and_deductions += amount
            elif line_type == "Employer Payroll Tax":
                expense_account_id = (
                    manufacturing_clearing_account_id
                    if cost_center_name == "Manufacturing" and capitalizable_manufacturing_month
                    else manufacturing_variance_account_id
                    if cost_center_name == "Manufacturing"
                    else burden_expense_account_id
                )
                add_expected(pay_date, cost_center_id, int(expense_account_id), amount, 0.0)
            elif line_type == "Employer Benefits":
                expense_account_id = (
                    manufacturing_clearing_account_id
                    if cost_center_name == "Manufacturing" and capitalizable_manufacturing_month
                    else manufacturing_variance_account_id
                    if cost_center_name == "Manufacturing"
                    else burden_expense_account_id
                )
                add_expected(pay_date, cost_center_id, int(expense_account_id), amount, 0.0)
                benefits_and_deductions += amount

        add_expected(pay_date, cost_center_id, int(accrued_payroll_account_id), 0.0, float(register.NetPay))
        add_expected(pay_date, cost_center_id, int(withholdings_account_id), 0.0, employee_tax_withholding)
        add_expected(pay_date, cost_center_id, int(employer_tax_account_id), 0.0, float(register.EmployerPayrollTax))
        add_expected(pay_date, cost_center_id, int(benefits_account_id), 0.0, benefits_and_deductions)

    actual_summary = (
        summary_rows.groupby(["PostingDate", "CostCenterID", "AccountID"], dropna=False)[["Debit", "Credit"]]
        .sum()
        .round(2)
        .reset_index()
        .sort_values(["PostingDate", "CostCenterID", "AccountID"])
        .reset_index(drop=True)
    )
    expected_summary_df = (
        pd.DataFrame([
            {
                "PostingDate": posting_date,
                "CostCenterID": cost_center_id,
                "AccountID": account_id,
                "Debit": amounts["Debit"],
                "Credit": amounts["Credit"],
            }
            for (posting_date, cost_center_id, account_id), amounts in expected_summary.items()
        ])
        .sort_values(["PostingDate", "CostCenterID", "AccountID"])
        .reset_index(drop=True)
    )
    actual_summary = actual_summary.astype({"CostCenterID": "int64", "AccountID": "int64"})
    expected_summary_df = expected_summary_df.astype({"CostCenterID": "int64", "AccountID": "int64"})

    pd.testing.assert_frame_equal(actual_summary, expected_summary_df)

    payment_rows = gl[gl["SourceDocumentType"].eq("PayrollPayment")].copy()
    assert not payment_rows.empty
    expected_payment = (
        payroll_payments.merge(
            registers[["PayrollRegisterID", "PayrollPeriodID", "CostCenterID", "NetPay"]],
            on="PayrollRegisterID",
            how="inner",
        ).merge(
            payroll_periods[["PayrollPeriodID", "PayDate"]],
            on="PayrollPeriodID",
            how="inner",
        )
    )
    payment_expected_rows: list[dict[str, object]] = []
    for row in expected_payment.itertuples(index=False):
        payment_date = pd.Timestamp(row.PayDate).strftime("%Y-%m-%d")
        payment_expected_rows.append({
            "PostingDate": payment_date,
            "CostCenterID": int(row.CostCenterID),
            "AccountID": int(accrued_payroll_account_id),
            "Debit": round(float(row.NetPay), 2),
            "Credit": 0.0,
        })
        payment_expected_rows.append({
            "PostingDate": payment_date,
            "CostCenterID": int(row.CostCenterID),
            "AccountID": int(cash_account_id),
            "Debit": 0.0,
            "Credit": round(float(row.NetPay), 2),
        })

    expected_payment_df = (
        pd.DataFrame(payment_expected_rows)
        .groupby(["PostingDate", "CostCenterID", "AccountID"], dropna=False)[["Debit", "Credit"]]
        .sum()
        .round(2)
        .reset_index()
        .sort_values(["PostingDate", "CostCenterID", "AccountID"])
        .reset_index(drop=True)
    )
    actual_payment_df = (
        payment_rows.groupby(["PostingDate", "CostCenterID", "AccountID"], dropna=False)[["Debit", "Credit"]]
        .sum()
        .round(2)
        .reset_index()
        .sort_values(["PostingDate", "CostCenterID", "AccountID"])
        .reset_index(drop=True)
    )
    actual_payment_df = actual_payment_df.astype({"CostCenterID": "int64", "AccountID": "int64"})
    expected_payment_df = expected_payment_df.astype({"CostCenterID": "int64", "AccountID": "int64"})

    pd.testing.assert_frame_equal(actual_payment_df, expected_payment_df)
