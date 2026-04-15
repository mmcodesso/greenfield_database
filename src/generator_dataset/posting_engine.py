from __future__ import annotations

from typing import Any

import pandas as pd

from generator_dataset.journals import accrual_journal_details
from generator_dataset.p2p import (
    goods_receipt_line_cost_center_map,
    purchase_invoice_line_cost_center_map,
    purchase_invoice_line_matched_basis_map,
    purchase_invoice_unique_cost_center_map,
)
from generator_dataset.o2c import credit_memo_allocation_map
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.settings import GenerationContext
from generator_dataset.utils import money, next_id


SYSTEM_EMPLOYEE_ID = 1
SALARY_ACCOUNT_BY_COST_CENTER = {
    "Executive": "6050",
    "Sales": "6010",
    "Warehouse": "6020",
    "Purchasing": "6230",
    "Administration": "6030",
    "Customer Service": "6040",
    "Research and Development": "6250",
    "Marketing": "6240",
    "Manufacturing": "6260",
}


def account_id_by_number(context: GenerationContext, account_number: str) -> int:
    accounts = context.tables["Account"]
    matches = accounts.loc[accounts["AccountNumber"].astype(str).eq(account_number), "AccountID"]
    if matches.empty:
        raise ValueError(f"Account number {account_number} is not loaded.")
    return int(matches.iloc[0])


def fiscal_fields(posting_date: str) -> tuple[int, int]:
    timestamp = pd.Timestamp(posting_date)
    return int(timestamp.year), int(timestamp.month)


def build_gl_row(
    context: GenerationContext,
    posting_date: str,
    account_id: int,
    debit: float,
    credit: float,
    voucher_type: str,
    voucher_number: str,
    source_document_type: str,
    source_document_id: int,
    source_line_id: int | None,
    cost_center_id: int | None,
    description: str,
    created_by_employee_id: int = SYSTEM_EMPLOYEE_ID,
) -> dict[str, Any]:
    fiscal_year, fiscal_period = fiscal_fields(posting_date)
    return {
        "GLEntryID": next_id(context, "GLEntry"),
        "PostingDate": posting_date,
        "AccountID": account_id,
        "Debit": money(debit),
        "Credit": money(credit),
        "VoucherType": voucher_type,
        "VoucherNumber": voucher_number,
        "SourceDocumentType": source_document_type,
        "SourceDocumentID": source_document_id,
        "SourceLineID": source_line_id,
        "CostCenterID": cost_center_id,
        "Description": description,
        "CreatedByEmployeeID": created_by_employee_id,
        "CreatedDate": f"{posting_date} 12:00:00",
        "FiscalYear": fiscal_year,
        "FiscalPeriod": fiscal_period,
    }


def assert_balanced(rows: list[dict[str, Any]], voucher_number: str) -> None:
    debit_total = round(sum(float(row["Debit"]) for row in rows), 2)
    credit_total = round(sum(float(row["Credit"]) for row in rows), 2)
    if debit_total != credit_total:
        raise ValueError(f"Unbalanced voucher {voucher_number}: debit={debit_total}, credit={credit_total}")


def payroll_account_numbers(context: GenerationContext) -> dict[str, str]:
    cost_centers = context.tables["CostCenter"].set_index("CostCenterID")["CostCenterName"].to_dict()
    return {int(cost_center_id): SALARY_ACCOUNT_BY_COST_CENTER[str(name)] for cost_center_id, name in cost_centers.items()}


def post_shipments(context: GenerationContext) -> list[dict[str, Any]]:
    shipments = context.tables["Shipment"]
    shipment_lines = context.tables["ShipmentLine"]
    if shipments.empty or shipment_lines.empty:
        return []

    items = context.tables["Item"].set_index("ItemID").to_dict("index")
    sales_orders = context.tables["SalesOrder"].set_index("SalesOrderID").to_dict("index")
    shipment_headers = shipments.set_index("ShipmentID").to_dict("index")
    rows: list[dict[str, Any]] = []

    for line in shipment_lines.itertuples(index=False):
        shipment = shipment_headers[int(line.ShipmentID)]
        item = items[int(line.ItemID)]
        sales_order = sales_orders[int(shipment["SalesOrderID"])]
        voucher_rows = [
            build_gl_row(
                context,
                shipment["ShipmentDate"],
                int(item["COGSAccountID"]),
                float(line.ExtendedStandardCost),
                0.0,
                "Shipment",
                shipment["ShipmentNumber"],
                "Shipment",
                int(line.ShipmentID),
                int(line.ShipmentLineID),
                int(sales_order["CostCenterID"]),
                "Recognize COGS on shipment",
            ),
            build_gl_row(
                context,
                shipment["ShipmentDate"],
                int(item["InventoryAccountID"]),
                0.0,
                float(line.ExtendedStandardCost),
                "Shipment",
                shipment["ShipmentNumber"],
                "Shipment",
                int(line.ShipmentID),
                int(line.ShipmentLineID),
                int(sales_order["CostCenterID"]),
                "Relieve inventory on shipment",
            ),
        ]
        assert_balanced(voucher_rows, shipment["ShipmentNumber"])
        rows.extend(voucher_rows)

    return rows


def post_sales_invoices(context: GenerationContext) -> list[dict[str, Any]]:
    invoices = context.tables["SalesInvoice"]
    invoice_lines = context.tables["SalesInvoiceLine"]
    if invoices.empty or invoice_lines.empty:
        return []

    ar_account_id = account_id_by_number(context, "1020")
    tax_account_id = account_id_by_number(context, "2050")
    items = context.tables["Item"].set_index("ItemID").to_dict("index")
    sales_orders = context.tables["SalesOrder"].set_index("SalesOrderID").to_dict("index")
    lines_by_invoice = {key: value for key, value in invoice_lines.groupby("SalesInvoiceID")}
    rows: list[dict[str, Any]] = []

    for invoice in invoices.itertuples(index=False):
        sales_order = sales_orders[int(invoice.SalesOrderID)]
        voucher_rows = [
            build_gl_row(
                context,
                invoice.InvoiceDate,
                ar_account_id,
                float(invoice.GrandTotal),
                0.0,
                "SalesInvoice",
                invoice.InvoiceNumber,
                "SalesInvoice",
                int(invoice.SalesInvoiceID),
                None,
                None,
                "Record accounts receivable",
            )
        ]
        for line in lines_by_invoice.get(invoice.SalesInvoiceID).itertuples(index=False):
            item = items[int(line.ItemID)]
            voucher_rows.append(build_gl_row(
                context,
                invoice.InvoiceDate,
                int(item["RevenueAccountID"]),
                0.0,
                float(line.LineTotal),
                "SalesInvoice",
                invoice.InvoiceNumber,
                "SalesInvoice",
                int(invoice.SalesInvoiceID),
                int(line.SalesInvoiceLineID),
                int(sales_order["CostCenterID"]),
                "Recognize sales revenue",
            ))

        if float(invoice.TaxAmount) > 0:
            voucher_rows.append(build_gl_row(
                context,
                invoice.InvoiceDate,
                tax_account_id,
                0.0,
                float(invoice.TaxAmount),
                "SalesInvoice",
                invoice.InvoiceNumber,
                "SalesInvoice",
                int(invoice.SalesInvoiceID),
                None,
                None,
                "Record sales tax payable",
            ))

        assert_balanced(voucher_rows, invoice.InvoiceNumber)
        rows.extend(voucher_rows)

    return rows


def post_cash_receipts(context: GenerationContext) -> list[dict[str, Any]]:
    receipts = context.tables["CashReceipt"]
    if receipts.empty:
        return []

    cash_account_id = account_id_by_number(context, "1010")
    unapplied_cash_account_id = account_id_by_number(context, "2060")
    rows: list[dict[str, Any]] = []
    for receipt in receipts.itertuples(index=False):
        voucher_rows = [
            build_gl_row(
                context,
                receipt.ReceiptDate,
                cash_account_id,
                float(receipt.Amount),
                0.0,
                "CashReceipt",
                receipt.ReceiptNumber,
                "CashReceipt",
                int(receipt.CashReceiptID),
                None,
                None,
                "Record cash receipt",
                int(receipt.RecordedByEmployeeID),
            ),
            build_gl_row(
                context,
                receipt.ReceiptDate,
                unapplied_cash_account_id,
                0.0,
                float(receipt.Amount),
                "CashReceipt",
                receipt.ReceiptNumber,
                "CashReceipt",
                int(receipt.CashReceiptID),
                None,
                None,
                "Record customer deposit or unapplied cash",
                int(receipt.RecordedByEmployeeID),
            ),
        ]
        assert_balanced(voucher_rows, receipt.ReceiptNumber)
        rows.extend(voucher_rows)

    return rows


def post_cash_receipt_applications(context: GenerationContext) -> list[dict[str, Any]]:
    applications = context.tables["CashReceiptApplication"]
    receipts = context.tables["CashReceipt"]
    if applications.empty or receipts.empty:
        return []

    receipt_lookup = receipts.set_index("CashReceiptID").to_dict("index")
    ar_account_id = account_id_by_number(context, "1020")
    unapplied_cash_account_id = account_id_by_number(context, "2060")
    rows: list[dict[str, Any]] = []
    for application in applications.itertuples(index=False):
        receipt = receipt_lookup[int(application.CashReceiptID)]
        voucher_number = f"{receipt['ReceiptNumber']}-APP-{int(application.CashReceiptApplicationID):06d}"
        voucher_rows = [
            build_gl_row(
                context,
                application.ApplicationDate,
                unapplied_cash_account_id,
                float(application.AppliedAmount),
                0.0,
                "CashReceiptApplication",
                voucher_number,
                "CashReceiptApplication",
                int(application.CashReceiptApplicationID),
                None,
                None,
                "Apply customer deposit or receipt",
                int(application.AppliedByEmployeeID),
            ),
            build_gl_row(
                context,
                application.ApplicationDate,
                ar_account_id,
                0.0,
                float(application.AppliedAmount),
                "CashReceiptApplication",
                voucher_number,
                "CashReceiptApplication",
                int(application.CashReceiptApplicationID),
                None,
                None,
                "Reduce accounts receivable",
                int(application.AppliedByEmployeeID),
            ),
        ]
        assert_balanced(voucher_rows, voucher_number)
        rows.extend(voucher_rows)

    return rows


def post_sales_returns(context: GenerationContext) -> list[dict[str, Any]]:
    sales_returns = context.tables["SalesReturn"]
    return_lines = context.tables["SalesReturnLine"]
    if sales_returns.empty or return_lines.empty:
        return []

    items = context.tables["Item"].set_index("ItemID").to_dict("index")
    return_headers = sales_returns.set_index("SalesReturnID").to_dict("index")
    shipment_lines = context.tables["ShipmentLine"].set_index("ShipmentLineID").to_dict("index")
    shipments = context.tables["Shipment"].set_index("ShipmentID").to_dict("index")
    sales_orders = context.tables["SalesOrder"].set_index("SalesOrderID").to_dict("index")
    rows: list[dict[str, Any]] = []

    for line in return_lines.itertuples(index=False):
        sales_return = return_headers[int(line.SalesReturnID)]
        shipment_line = shipment_lines[int(line.ShipmentLineID)]
        shipment = shipments[int(shipment_line["ShipmentID"])]
        sales_order = sales_orders[int(shipment["SalesOrderID"])]
        item = items[int(line.ItemID)]
        voucher_rows = [
            build_gl_row(
                context,
                sales_return["ReturnDate"],
                int(item["InventoryAccountID"]),
                float(line.ExtendedStandardCost),
                0.0,
                "SalesReturn",
                sales_return["ReturnNumber"],
                "SalesReturn",
                int(line.SalesReturnID),
                int(line.SalesReturnLineID),
                int(sales_order["CostCenterID"]),
                "Return inventory to stock",
                int(sales_return["ReceivedByEmployeeID"]),
            ),
            build_gl_row(
                context,
                sales_return["ReturnDate"],
                int(item["COGSAccountID"]),
                0.0,
                float(line.ExtendedStandardCost),
                "SalesReturn",
                sales_return["ReturnNumber"],
                "SalesReturn",
                int(line.SalesReturnID),
                int(line.SalesReturnLineID),
                int(sales_order["CostCenterID"]),
                "Reverse COGS for customer return",
                int(sales_return["ReceivedByEmployeeID"]),
            ),
        ]
        assert_balanced(voucher_rows, sales_return["ReturnNumber"])
        rows.extend(voucher_rows)

    return rows


def post_credit_memos(context: GenerationContext) -> list[dict[str, Any]]:
    credit_memos = context.tables["CreditMemo"]
    credit_memo_lines = context.tables["CreditMemoLine"]
    if credit_memos.empty or credit_memo_lines.empty:
        return []

    contra_revenue_account_id = account_id_by_number(context, "4060")
    tax_account_id = account_id_by_number(context, "2050")
    ar_account_id = account_id_by_number(context, "1020")
    unapplied_cash_account_id = account_id_by_number(context, "2060")
    sales_orders = context.tables["SalesOrder"].set_index("SalesOrderID").to_dict("index")
    lines_by_credit_memo = {key: value for key, value in credit_memo_lines.groupby("CreditMemoID")}
    allocations = credit_memo_allocation_map(context)
    rows: list[dict[str, Any]] = []

    for credit_memo in credit_memos.itertuples(index=False):
        sales_order = sales_orders[int(credit_memo.SalesOrderID)]
        voucher_rows: list[dict[str, Any]] = []
        credit_memo_line_group = lines_by_credit_memo.get(int(credit_memo.CreditMemoID))
        if credit_memo_line_group is None or credit_memo_line_group.empty:
            continue

        for line in credit_memo_line_group.itertuples(index=False):
            voucher_rows.append(build_gl_row(
                context,
                credit_memo.CreditMemoDate,
                contra_revenue_account_id,
                float(line.LineTotal),
                0.0,
                "CreditMemo",
                credit_memo.CreditMemoNumber,
                "CreditMemo",
                int(credit_memo.CreditMemoID),
                int(line.CreditMemoLineID),
                int(sales_order["CostCenterID"]),
                "Record sales return and allowance",
                int(credit_memo.ApprovedByEmployeeID),
            ))

        if float(credit_memo.TaxAmount) > 0:
            voucher_rows.append(build_gl_row(
                context,
                credit_memo.CreditMemoDate,
                tax_account_id,
                float(credit_memo.TaxAmount),
                0.0,
                "CreditMemo",
                credit_memo.CreditMemoNumber,
                "CreditMemo",
                int(credit_memo.CreditMemoID),
                None,
                int(sales_order["CostCenterID"]),
                "Reverse sales tax payable",
                int(credit_memo.ApprovedByEmployeeID),
            ))

        allocation = allocations.get(int(credit_memo.CreditMemoID), {"ar_amount": 0.0, "customer_credit_amount": 0.0})
        if round(float(allocation["ar_amount"]), 2) > 0:
            voucher_rows.append(build_gl_row(
                context,
                credit_memo.CreditMemoDate,
                ar_account_id,
                0.0,
                float(allocation["ar_amount"]),
                "CreditMemo",
                credit_memo.CreditMemoNumber,
                "CreditMemo",
                int(credit_memo.CreditMemoID),
                None,
                int(sales_order["CostCenterID"]),
                "Reduce accounts receivable through credit memo",
                int(credit_memo.ApprovedByEmployeeID),
            ))
        if round(float(allocation["customer_credit_amount"]), 2) > 0:
            voucher_rows.append(build_gl_row(
                context,
                credit_memo.CreditMemoDate,
                unapplied_cash_account_id,
                0.0,
                float(allocation["customer_credit_amount"]),
                "CreditMemo",
                credit_memo.CreditMemoNumber,
                "CreditMemo",
                int(credit_memo.CreditMemoID),
                None,
                int(sales_order["CostCenterID"]),
                "Create customer credit balance",
                int(credit_memo.ApprovedByEmployeeID),
            ))

        assert_balanced(voucher_rows, credit_memo.CreditMemoNumber)
        rows.extend(voucher_rows)

    return rows


def post_customer_refunds(context: GenerationContext) -> list[dict[str, Any]]:
    refunds = context.tables["CustomerRefund"]
    if refunds.empty:
        return []

    cash_account_id = account_id_by_number(context, "1010")
    unapplied_cash_account_id = account_id_by_number(context, "2060")
    rows: list[dict[str, Any]] = []
    for refund in refunds.itertuples(index=False):
        voucher_rows = [
            build_gl_row(
                context,
                refund.RefundDate,
                unapplied_cash_account_id,
                float(refund.Amount),
                0.0,
                "CustomerRefund",
                refund.RefundNumber,
                "CustomerRefund",
                int(refund.CustomerRefundID),
                None,
                None,
                "Reduce customer credit balance",
                int(refund.ApprovedByEmployeeID),
            ),
            build_gl_row(
                context,
                refund.RefundDate,
                cash_account_id,
                0.0,
                float(refund.Amount),
                "CustomerRefund",
                refund.RefundNumber,
                "CustomerRefund",
                int(refund.CustomerRefundID),
                None,
                None,
                "Issue customer refund",
                int(refund.ApprovedByEmployeeID),
            ),
        ]
        assert_balanced(voucher_rows, refund.RefundNumber)
        rows.extend(voucher_rows)

    return rows


def post_payroll_registers(context: GenerationContext) -> list[dict[str, Any]]:
    registers = context.tables["PayrollRegister"]
    register_lines = context.tables["PayrollRegisterLine"]
    employees = context.tables["Employee"]
    cost_centers = context.tables["CostCenter"]
    if registers.empty or register_lines.empty or employees.empty or cost_centers.empty:
        return []

    employee_lookup = employees.set_index("EmployeeID").to_dict("index")
    cost_center_names = cost_centers.set_index("CostCenterID")["CostCenterName"].to_dict()
    lines_by_register = {key: value for key, value in register_lines.groupby("PayrollRegisterID")}
    salary_accounts = payroll_account_numbers(context)
    accrued_payroll_account_id = account_id_by_number(context, "2030")
    withholdings_account_id = account_id_by_number(context, "2031")
    employer_tax_account_id = account_id_by_number(context, "2032")
    benefits_account_id = account_id_by_number(context, "2033")
    burden_expense_account_id = account_id_by_number(context, "6060")
    manufacturing_overhead_account_id = account_id_by_number(context, "6270")
    rows: list[dict[str, Any]] = []

    for register in registers.itertuples(index=False):
        voucher_number = f"PR-{int(register.PayrollRegisterID):06d}"
        employee = employee_lookup[int(register.EmployeeID)]
        cost_center_name = str(cost_center_names[int(register.CostCenterID)])
        register_line_group = lines_by_register.get(int(register.PayrollRegisterID))
        if register_line_group is None or register_line_group.empty:
            continue

        voucher_rows: list[dict[str, Any]] = []
        employee_tax_withholding = 0.0
        benefits_and_deductions = 0.0

        for line in register_line_group.itertuples(index=False):
            line_type = str(line.LineType)
            if line_type in {"Regular Earnings", "Overtime Earnings", "Salary Earnings", "Bonus"}:
                if cost_center_name == "Manufacturing":
                    debit_account_id = account_id_by_number(context, "6260") if pd.notna(line.WorkOrderID) else manufacturing_overhead_account_id
                else:
                    debit_account_id = account_id_by_number(context, salary_accounts[int(register.CostCenterID)])
                voucher_rows.append(build_gl_row(
                    context,
                    register.ApprovedDate,
                    debit_account_id,
                    float(line.Amount),
                    0.0,
                    "PayrollRegister",
                    voucher_number,
                    "PayrollRegister",
                    int(register.PayrollRegisterID),
                    int(line.PayrollRegisterLineID),
                    int(register.CostCenterID),
                    f"Record {line_type.lower()}",
                    int(register.ApprovedByEmployeeID),
                ))
            elif line_type == "Employee Tax Withholding":
                employee_tax_withholding += float(line.Amount)
            elif line_type == "Benefits Deduction":
                benefits_and_deductions += float(line.Amount)
            elif line_type == "Employer Payroll Tax":
                expense_account_id = manufacturing_overhead_account_id if cost_center_name == "Manufacturing" else burden_expense_account_id
                voucher_rows.append(build_gl_row(
                    context,
                    register.ApprovedDate,
                    expense_account_id,
                    float(line.Amount),
                    0.0,
                    "PayrollRegister",
                    voucher_number,
                    "PayrollRegister",
                    int(register.PayrollRegisterID),
                    int(line.PayrollRegisterLineID),
                    int(register.CostCenterID),
                    "Record employer payroll tax expense",
                    int(register.ApprovedByEmployeeID),
                ))
            elif line_type == "Employer Benefits":
                expense_account_id = manufacturing_overhead_account_id if cost_center_name == "Manufacturing" else burden_expense_account_id
                voucher_rows.append(build_gl_row(
                    context,
                    register.ApprovedDate,
                    expense_account_id,
                    float(line.Amount),
                    0.0,
                    "PayrollRegister",
                    voucher_number,
                    "PayrollRegister",
                    int(register.PayrollRegisterID),
                    int(line.PayrollRegisterLineID),
                    int(register.CostCenterID),
                    "Record employer benefits expense",
                    int(register.ApprovedByEmployeeID),
                ))
                benefits_and_deductions += float(line.Amount)

        voucher_rows.extend([
            build_gl_row(
                context,
                register.ApprovedDate,
                accrued_payroll_account_id,
                0.0,
                float(register.NetPay),
                "PayrollRegister",
                voucher_number,
                "PayrollRegister",
                int(register.PayrollRegisterID),
                None,
                int(register.CostCenterID),
                "Record net pay liability",
                int(register.ApprovedByEmployeeID),
            ),
            build_gl_row(
                context,
                register.ApprovedDate,
                withholdings_account_id,
                0.0,
                money(employee_tax_withholding),
                "PayrollRegister",
                voucher_number,
                "PayrollRegister",
                int(register.PayrollRegisterID),
                None,
                int(register.CostCenterID),
                "Record payroll tax withholdings payable",
                int(register.ApprovedByEmployeeID),
            ),
            build_gl_row(
                context,
                register.ApprovedDate,
                employer_tax_account_id,
                0.0,
                float(register.EmployerPayrollTax),
                "PayrollRegister",
                voucher_number,
                "PayrollRegister",
                int(register.PayrollRegisterID),
                None,
                int(register.CostCenterID),
                "Record employer payroll tax payable",
                int(register.ApprovedByEmployeeID),
            ),
            build_gl_row(
                context,
                register.ApprovedDate,
                benefits_account_id,
                0.0,
                money(benefits_and_deductions),
                "PayrollRegister",
                voucher_number,
                "PayrollRegister",
                int(register.PayrollRegisterID),
                None,
                int(register.CostCenterID),
                "Record benefits and deductions payable",
                int(register.ApprovedByEmployeeID),
            ),
        ])

        assert_balanced(voucher_rows, voucher_number)
        rows.extend(voucher_rows)

    return rows


def post_payroll_payments(context: GenerationContext) -> list[dict[str, Any]]:
    payments = context.tables["PayrollPayment"]
    registers = context.tables["PayrollRegister"]
    if payments.empty or registers.empty:
        return []

    register_lookup = registers.set_index("PayrollRegisterID").to_dict("index")
    accrued_payroll_account_id = account_id_by_number(context, "2030")
    cash_account_id = account_id_by_number(context, "1010")
    rows: list[dict[str, Any]] = []
    for payment in payments.itertuples(index=False):
        register = register_lookup[int(payment.PayrollRegisterID)]
        voucher_rows = [
            build_gl_row(
                context,
                payment.PaymentDate,
                accrued_payroll_account_id,
                float(register["NetPay"]),
                0.0,
                "PayrollPayment",
                payment.ReferenceNumber,
                "PayrollPayment",
                int(payment.PayrollPaymentID),
                None,
                int(register["CostCenterID"]),
                "Clear accrued payroll",
                int(payment.RecordedByEmployeeID),
            ),
            build_gl_row(
                context,
                payment.PaymentDate,
                cash_account_id,
                0.0,
                float(register["NetPay"]),
                "PayrollPayment",
                payment.ReferenceNumber,
                "PayrollPayment",
                int(payment.PayrollPaymentID),
                None,
                int(register["CostCenterID"]),
                "Disburse payroll cash",
                int(payment.RecordedByEmployeeID),
            ),
        ]
        assert_balanced(voucher_rows, payment.ReferenceNumber)
        rows.extend(voucher_rows)
    return rows


def post_payroll_liability_remittances(context: GenerationContext) -> list[dict[str, Any]]:
    remittances = context.tables["PayrollLiabilityRemittance"]
    if remittances.empty:
        return []

    liability_account_by_type = {
        "Employee Tax Withholding": account_id_by_number(context, "2031"),
        "Employer Payroll Tax": account_id_by_number(context, "2032"),
        "Benefits and Other Deductions": account_id_by_number(context, "2033"),
    }
    cash_account_id = account_id_by_number(context, "1010")
    rows: list[dict[str, Any]] = []
    for remittance in remittances.itertuples(index=False):
        voucher_rows = [
            build_gl_row(
                context,
                remittance.RemittanceDate,
                liability_account_by_type[str(remittance.LiabilityType)],
                float(remittance.Amount),
                0.0,
                "PayrollLiabilityRemittance",
                remittance.ReferenceNumber,
                "PayrollLiabilityRemittance",
                int(remittance.PayrollLiabilityRemittanceID),
                None,
                None,
                f"Clear {str(remittance.LiabilityType).lower()}",
                int(remittance.ApprovedByEmployeeID),
            ),
            build_gl_row(
                context,
                remittance.RemittanceDate,
                cash_account_id,
                0.0,
                float(remittance.Amount),
                "PayrollLiabilityRemittance",
                remittance.ReferenceNumber,
                "PayrollLiabilityRemittance",
                int(remittance.PayrollLiabilityRemittanceID),
                None,
                None,
                "Pay payroll liability",
                int(remittance.ApprovedByEmployeeID),
            ),
        ]
        assert_balanced(voucher_rows, remittance.ReferenceNumber)
        rows.extend(voucher_rows)

    return rows


def post_material_issues(context: GenerationContext) -> list[dict[str, Any]]:
    issues = context.tables["MaterialIssue"]
    issue_lines = context.tables["MaterialIssueLine"]
    work_orders = context.tables["WorkOrder"]
    if issues.empty or issue_lines.empty or work_orders.empty:
        return []

    wip_account_id = account_id_by_number(context, "1046")
    items = context.tables["Item"].set_index("ItemID").to_dict("index")
    issue_headers = issues.set_index("MaterialIssueID").to_dict("index")
    work_order_lookup = work_orders.set_index("WorkOrderID").to_dict("index")
    rows: list[dict[str, Any]] = []

    for line in issue_lines.itertuples(index=False):
        issue = issue_headers[int(line.MaterialIssueID)]
        work_order = work_order_lookup[int(issue["WorkOrderID"])]
        item = items[int(line.ItemID)]
        voucher_rows = [
            build_gl_row(
                context,
                issue["IssueDate"],
                wip_account_id,
                float(line.ExtendedStandardCost),
                0.0,
                "MaterialIssue",
                issue["IssueNumber"],
                "MaterialIssue",
                int(line.MaterialIssueID),
                int(line.MaterialIssueLineID),
                int(work_order["CostCenterID"]),
                "Issue material to work in process",
                int(issue["IssuedByEmployeeID"]),
            ),
            build_gl_row(
                context,
                issue["IssueDate"],
                int(item["InventoryAccountID"]),
                0.0,
                float(line.ExtendedStandardCost),
                "MaterialIssue",
                issue["IssueNumber"],
                "MaterialIssue",
                int(line.MaterialIssueID),
                int(line.MaterialIssueLineID),
                int(work_order["CostCenterID"]),
                "Relieve materials inventory for work order",
                int(issue["IssuedByEmployeeID"]),
            ),
        ]
        assert_balanced(voucher_rows, issue["IssueNumber"])
        rows.extend(voucher_rows)

    return rows


def post_production_completions(context: GenerationContext) -> list[dict[str, Any]]:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    work_orders = context.tables["WorkOrder"]
    if completions.empty or completion_lines.empty or work_orders.empty:
        return []

    wip_account_id = account_id_by_number(context, "1046")
    manufacturing_clearing_account_id = account_id_by_number(context, "1090")
    items = context.tables["Item"].set_index("ItemID").to_dict("index")
    completion_headers = completions.set_index("ProductionCompletionID").to_dict("index")
    work_order_lookup = work_orders.set_index("WorkOrderID").to_dict("index")
    rows: list[dict[str, Any]] = []

    for line in completion_lines.itertuples(index=False):
        completion = completion_headers[int(line.ProductionCompletionID)]
        work_order = work_order_lookup[int(completion["WorkOrderID"])]
        item = items[int(line.ItemID)]
        voucher_rows = [
            build_gl_row(
                context,
                completion["CompletionDate"],
                int(item["InventoryAccountID"]),
                float(line.ExtendedStandardTotalCost),
                0.0,
                "ProductionCompletion",
                completion["CompletionNumber"],
                "ProductionCompletion",
                int(line.ProductionCompletionID),
                int(line.ProductionCompletionLineID),
                int(work_order["CostCenterID"]),
                "Receive finished goods from production",
                int(completion["ReceivedByEmployeeID"]),
            ),
            build_gl_row(
                context,
                completion["CompletionDate"],
                wip_account_id,
                0.0,
                float(line.ExtendedStandardMaterialCost),
                "ProductionCompletion",
                completion["CompletionNumber"],
                "ProductionCompletion",
                int(line.ProductionCompletionID),
                int(line.ProductionCompletionLineID),
                int(work_order["CostCenterID"]),
                "Relieve work in process for material component",
                int(completion["ReceivedByEmployeeID"]),
            ),
            build_gl_row(
                context,
                completion["CompletionDate"],
                manufacturing_clearing_account_id,
                0.0,
                float(line.ExtendedStandardConversionCost),
                "ProductionCompletion",
                completion["CompletionNumber"],
                "ProductionCompletion",
                int(line.ProductionCompletionID),
                int(line.ProductionCompletionLineID),
                int(work_order["CostCenterID"]),
                "Relieve manufacturing conversion clearing",
                int(completion["ReceivedByEmployeeID"]),
            ),
        ]
        assert_balanced(voucher_rows, completion["CompletionNumber"])
        rows.extend(voucher_rows)

    return rows


def post_work_order_closes(context: GenerationContext) -> list[dict[str, Any]]:
    closes = context.tables["WorkOrderClose"]
    work_orders = context.tables["WorkOrder"]
    if closes.empty or work_orders.empty:
        return []

    wip_account_id = account_id_by_number(context, "1046")
    manufacturing_clearing_account_id = account_id_by_number(context, "1090")
    variance_account_id = account_id_by_number(context, "5080")
    work_order_lookup = work_orders.set_index("WorkOrderID").to_dict("index")
    rows: list[dict[str, Any]] = []

    for close in closes.itertuples(index=False):
        work_order = work_order_lookup[int(close.WorkOrderID)]
        voucher_number = f"WOCL-{int(close.WorkOrderCloseID):06d}"
        voucher_rows: list[dict[str, Any]] = []

        material_variance = round(float(close.MaterialVarianceAmount), 2)
        if material_variance > 0:
            voucher_rows.extend([
                build_gl_row(
                    context,
                    close.CloseDate,
                    variance_account_id,
                    material_variance,
                    0.0,
                    "WorkOrderClose",
                    voucher_number,
                    "WorkOrderClose",
                    int(close.WorkOrderCloseID),
                    None,
                    int(work_order["CostCenterID"]),
                    "Close unfavorable material variance",
                    int(close.ClosedByEmployeeID),
                ),
                build_gl_row(
                    context,
                    close.CloseDate,
                    wip_account_id,
                    0.0,
                    material_variance,
                    "WorkOrderClose",
                    voucher_number,
                    "WorkOrderClose",
                    int(close.WorkOrderCloseID),
                    None,
                    int(work_order["CostCenterID"]),
                    "Clear residual WIP balance",
                    int(close.ClosedByEmployeeID),
                ),
            ])
        elif material_variance < 0:
            favorable = abs(material_variance)
            voucher_rows.extend([
                build_gl_row(
                    context,
                    close.CloseDate,
                    wip_account_id,
                    favorable,
                    0.0,
                    "WorkOrderClose",
                    voucher_number,
                    "WorkOrderClose",
                    int(close.WorkOrderCloseID),
                    None,
                    int(work_order["CostCenterID"]),
                    "Clear favorable material variance from WIP",
                    int(close.ClosedByEmployeeID),
                ),
                build_gl_row(
                    context,
                    close.CloseDate,
                    variance_account_id,
                    0.0,
                    favorable,
                    "WorkOrderClose",
                    voucher_number,
                    "WorkOrderClose",
                    int(close.WorkOrderCloseID),
                    None,
                    int(work_order["CostCenterID"]),
                    "Record favorable material variance",
                    int(close.ClosedByEmployeeID),
                ),
            ])

        conversion_variance = round(float(close.ConversionVarianceAmount), 2)
        if conversion_variance > 0:
            voucher_rows.extend([
                build_gl_row(
                    context,
                    close.CloseDate,
                    variance_account_id,
                    conversion_variance,
                    0.0,
                    "WorkOrderClose",
                    voucher_number,
                    "WorkOrderClose",
                    int(close.WorkOrderCloseID),
                    None,
                    int(work_order["CostCenterID"]),
                    "Close unfavorable conversion variance",
                    int(close.ClosedByEmployeeID),
                ),
                build_gl_row(
                    context,
                    close.CloseDate,
                    manufacturing_clearing_account_id,
                    0.0,
                    conversion_variance,
                    "WorkOrderClose",
                    voucher_number,
                    "WorkOrderClose",
                    int(close.WorkOrderCloseID),
                    None,
                    int(work_order["CostCenterID"]),
                    "Clear residual manufacturing conversion balance",
                    int(close.ClosedByEmployeeID),
                ),
            ])
        elif conversion_variance < 0:
            favorable = abs(conversion_variance)
            voucher_rows.extend([
                build_gl_row(
                    context,
                    close.CloseDate,
                    manufacturing_clearing_account_id,
                    favorable,
                    0.0,
                    "WorkOrderClose",
                    voucher_number,
                    "WorkOrderClose",
                    int(close.WorkOrderCloseID),
                    None,
                    int(work_order["CostCenterID"]),
                    "Clear favorable conversion variance from manufacturing clearing",
                    int(close.ClosedByEmployeeID),
                ),
                build_gl_row(
                    context,
                    close.CloseDate,
                    variance_account_id,
                    0.0,
                    favorable,
                    "WorkOrderClose",
                    voucher_number,
                    "WorkOrderClose",
                    int(close.WorkOrderCloseID),
                    None,
                    int(work_order["CostCenterID"]),
                    "Record favorable conversion variance",
                    int(close.ClosedByEmployeeID),
                ),
            ])

        if not voucher_rows:
            continue
        assert_balanced(voucher_rows, voucher_number)
        rows.extend(voucher_rows)

    return rows


def post_goods_receipts(context: GenerationContext) -> list[dict[str, Any]]:
    receipts = context.tables["GoodsReceipt"]
    receipt_lines = context.tables["GoodsReceiptLine"]
    if receipts.empty or receipt_lines.empty:
        return []

    grni_account_id = account_id_by_number(context, "2020")
    items = context.tables["Item"].set_index("ItemID").to_dict("index")
    receipt_headers = receipts.set_index("GoodsReceiptID").to_dict("index")
    receipt_line_cost_centers = goods_receipt_line_cost_center_map(context)
    rows: list[dict[str, Any]] = []

    for line in receipt_lines.itertuples(index=False):
        receipt = receipt_headers[int(line.GoodsReceiptID)]
        item = items[int(line.ItemID)]
        line_cost_center_id = receipt_line_cost_centers.get(int(line.GoodsReceiptLineID))
        voucher_rows = [
            build_gl_row(
                context,
                receipt["ReceiptDate"],
                int(item["InventoryAccountID"]),
                float(line.ExtendedStandardCost),
                0.0,
                "GoodsReceipt",
                receipt["ReceiptNumber"],
                "GoodsReceipt",
                int(line.GoodsReceiptID),
                int(line.GoodsReceiptLineID),
                line_cost_center_id,
                "Receive inventory",
                int(receipt["ReceivedByEmployeeID"]),
            ),
            build_gl_row(
                context,
                receipt["ReceiptDate"],
                grni_account_id,
                0.0,
                float(line.ExtendedStandardCost),
                "GoodsReceipt",
                receipt["ReceiptNumber"],
                "GoodsReceipt",
                int(line.GoodsReceiptID),
                int(line.GoodsReceiptLineID),
                line_cost_center_id,
                "Record goods received not invoiced",
                int(receipt["ReceivedByEmployeeID"]),
            ),
        ]
        assert_balanced(voucher_rows, receipt["ReceiptNumber"])
        rows.extend(voucher_rows)

    return rows


def post_purchase_invoices(context: GenerationContext) -> list[dict[str, Any]]:
    invoices = context.tables["PurchaseInvoice"]
    invoice_lines = context.tables["PurchaseInvoiceLine"]
    if invoices.empty or invoice_lines.empty:
        return []

    ap_account_id = account_id_by_number(context, "2010")
    accrued_expenses_account_id = account_id_by_number(context, "2040")
    grni_account_id = account_id_by_number(context, "2020")
    variance_account_id = account_id_by_number(context, "5060")
    matched_basis_by_invoice_line = purchase_invoice_line_matched_basis_map(context)
    invoice_line_cost_centers = purchase_invoice_line_cost_center_map(context)
    invoice_header_cost_centers = purchase_invoice_unique_cost_center_map(context)
    accrual_by_journal_id = {
        int(entry["JournalEntryID"]): entry
        for entry in accrual_journal_details(context)
    }
    accrued_expense_cleared_by_journal: dict[int, float] = {}
    lines_by_invoice = {key: value for key, value in invoice_lines.groupby("PurchaseInvoiceID")}
    rows: list[dict[str, Any]] = []

    for invoice in invoices.itertuples(index=False):
        voucher_rows: list[dict[str, Any]] = []
        invoice_lines_for_header = lines_by_invoice.get(invoice.PurchaseInvoiceID)
        if invoice_lines_for_header is None:
            continue

        header_cost_center_id = invoice_header_cost_centers.get(int(invoice.PurchaseInvoiceID))
        for line in invoice_lines_for_header.itertuples(index=False):
            line_cost_center_id = invoice_line_cost_centers.get(int(line.PILineID))
            accrual_journal_entry_id = None if pd.isna(line.AccrualJournalEntryID) else int(line.AccrualJournalEntryID)
            if accrual_journal_entry_id is not None:
                accrual_detail = accrual_by_journal_id.get(accrual_journal_entry_id)
                if accrual_detail is None:
                    raise ValueError(
                        f"Purchase invoice line {int(line.PILineID)} references missing accrual journal {accrual_journal_entry_id}."
                    )

                remaining_accrual = float(accrual_detail["Amount"]) - float(
                    accrued_expense_cleared_by_journal.get(accrual_journal_entry_id, 0.0)
                )
                clear_amount = money(max(0.0, min(float(line.LineTotal), remaining_accrual)))
                if clear_amount > 0:
                    voucher_rows.append(build_gl_row(
                        context,
                        invoice.ApprovedDate,
                        accrued_expenses_account_id,
                        clear_amount,
                        0.0,
                        "PurchaseInvoice",
                        invoice.InvoiceNumber,
                        "PurchaseInvoice",
                        int(invoice.PurchaseInvoiceID),
                        int(line.PILineID),
                        line_cost_center_id,
                        "Clear accrued expenses on supplier invoice",
                        int(invoice.ApprovedByEmployeeID),
                    ))
                    accrued_expense_cleared_by_journal[accrual_journal_entry_id] = money(
                        float(accrued_expense_cleared_by_journal.get(accrual_journal_entry_id, 0.0)) + clear_amount
                    )

                excess_amount = money(float(line.LineTotal) - clear_amount)
                if excess_amount > 0:
                    voucher_rows.append(build_gl_row(
                        context,
                        invoice.ApprovedDate,
                        account_id_by_number(context, str(accrual_detail["ExpenseAccountNumber"])),
                        excess_amount,
                        0.0,
                        "PurchaseInvoice",
                        invoice.InvoiceNumber,
                        "PurchaseInvoice",
                        int(invoice.PurchaseInvoiceID),
                        int(line.PILineID),
                        line_cost_center_id,
                        "Record supplier invoice amount above accrued estimate",
                        int(invoice.ApprovedByEmployeeID),
                    ))
                continue

            accrued_amount = money(float(matched_basis_by_invoice_line.get(int(line.PILineID), line.LineTotal)))
            voucher_rows.append(build_gl_row(
                context,
                invoice.ApprovedDate,
                grni_account_id,
                accrued_amount,
                0.0,
                "PurchaseInvoice",
                invoice.InvoiceNumber,
                "PurchaseInvoice",
                int(invoice.PurchaseInvoiceID),
                int(line.PILineID),
                line_cost_center_id,
                "Clear GRNI on supplier invoice",
                int(invoice.ApprovedByEmployeeID),
            ))

            variance = money(float(line.LineTotal) - accrued_amount)
            if variance > 0:
                voucher_rows.append(build_gl_row(
                    context,
                    invoice.ApprovedDate,
                    variance_account_id,
                    variance,
                    0.0,
                    "PurchaseInvoice",
                    invoice.InvoiceNumber,
                    "PurchaseInvoice",
                    int(invoice.PurchaseInvoiceID),
                    int(line.PILineID),
                    line_cost_center_id,
                    "Record unfavorable purchase variance",
                    int(invoice.ApprovedByEmployeeID),
                ))
            elif variance < 0:
                voucher_rows.append(build_gl_row(
                    context,
                    invoice.ApprovedDate,
                    variance_account_id,
                    0.0,
                    abs(variance),
                    "PurchaseInvoice",
                    invoice.InvoiceNumber,
                    "PurchaseInvoice",
                    int(invoice.PurchaseInvoiceID),
                    int(line.PILineID),
                    line_cost_center_id,
                    "Record favorable purchase variance",
                    int(invoice.ApprovedByEmployeeID),
                ))

        if float(invoice.TaxAmount) > 0:
            voucher_rows.append(build_gl_row(
                context,
                invoice.ApprovedDate,
                variance_account_id,
                float(invoice.TaxAmount),
                0.0,
                "PurchaseInvoice",
                invoice.InvoiceNumber,
                "PurchaseInvoice",
                int(invoice.PurchaseInvoiceID),
                None,
                header_cost_center_id,
                "Record nonrecoverable purchase tax",
                int(invoice.ApprovedByEmployeeID),
            ))

        voucher_rows.append(build_gl_row(
            context,
            invoice.ApprovedDate,
            ap_account_id,
            0.0,
            float(invoice.GrandTotal),
            "PurchaseInvoice",
            invoice.InvoiceNumber,
            "PurchaseInvoice",
            int(invoice.PurchaseInvoiceID),
            None,
            header_cost_center_id,
            "Record accounts payable",
            int(invoice.ApprovedByEmployeeID),
        ))

        assert_balanced(voucher_rows, invoice.InvoiceNumber)
        rows.extend(voucher_rows)

    return rows


def post_disbursements(context: GenerationContext) -> list[dict[str, Any]]:
    payments = context.tables["DisbursementPayment"]
    if payments.empty:
        return []

    ap_account_id = account_id_by_number(context, "2010")
    cash_account_id = account_id_by_number(context, "1010")
    invoice_cost_centers = purchase_invoice_unique_cost_center_map(context)
    rows: list[dict[str, Any]] = []
    for payment in payments.itertuples(index=False):
        cost_center_id = invoice_cost_centers.get(int(payment.PurchaseInvoiceID))
        voucher_rows = [
            build_gl_row(
                context,
                payment.PaymentDate,
                ap_account_id,
                float(payment.Amount),
                0.0,
                "DisbursementPayment",
                payment.PaymentNumber,
                "DisbursementPayment",
                int(payment.DisbursementID),
                None,
                cost_center_id,
                "Reduce accounts payable",
                int(payment.ApprovedByEmployeeID),
            ),
            build_gl_row(
                context,
                payment.PaymentDate,
                cash_account_id,
                0.0,
                float(payment.Amount),
                "DisbursementPayment",
                payment.PaymentNumber,
                "DisbursementPayment",
                int(payment.DisbursementID),
                None,
                cost_center_id,
                "Record vendor payment",
                int(payment.ApprovedByEmployeeID),
            ),
        ]
        assert_balanced(voucher_rows, payment.PaymentNumber)
        rows.extend(voucher_rows)

    return rows


def post_all_transactions(context: GenerationContext) -> None:
    opening_gl = context.tables["GLEntry"][
        context.tables["GLEntry"]["VoucherType"].eq("JournalEntry")
    ].copy()

    operational_rows: list[dict[str, Any]] = []
    operational_rows.extend(post_shipments(context))
    operational_rows.extend(post_sales_invoices(context))
    operational_rows.extend(post_cash_receipts(context))
    operational_rows.extend(post_cash_receipt_applications(context))
    operational_rows.extend(post_sales_returns(context))
    operational_rows.extend(post_credit_memos(context))
    operational_rows.extend(post_customer_refunds(context))
    operational_rows.extend(post_payroll_registers(context))
    operational_rows.extend(post_payroll_payments(context))
    operational_rows.extend(post_payroll_liability_remittances(context))
    operational_rows.extend(post_material_issues(context))
    operational_rows.extend(post_production_completions(context))
    operational_rows.extend(post_work_order_closes(context))
    operational_rows.extend(post_goods_receipts(context))
    operational_rows.extend(post_purchase_invoices(context))
    operational_rows.extend(post_disbursements(context))

    operational_gl = pd.DataFrame(operational_rows, columns=TABLE_COLUMNS["GLEntry"])
    context.tables["GLEntry"] = pd.concat([opening_gl, operational_gl], ignore_index=True)
