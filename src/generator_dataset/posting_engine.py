from __future__ import annotations

from collections import defaultdict
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
from generator_dataset.payroll import monthly_direct_labor_reclass_amount
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.settings import GenerationContext
from generator_dataset.utils import money, next_id


SYSTEM_EMPLOYEE_ID = 1
PAYROLL_SUMMARY_VOUCHER_TYPE = "PayrollSummary"
PAYROLL_SUMMARY_SOURCE_DOCUMENT_TYPE = "PayrollSummary"
PREFERRED_EXCEL_GLENTRY_ROW_BUDGET = 1_000_000
SALARY_ACCOUNT_BY_COST_CENTER = {
    "Executive": "6050",
    "Sales": "6010",
    "Warehouse": "6020",
    "Purchasing": "6230",
    "Administration": "6030",
    "Customer Service": "6040",
    "Research and Development": "6250",
    "Marketing": "6240",
    "Manufacturing": "1090",
}

MANUFACTURING_CLEARING_ACCOUNT_NUMBER = "1090"
MANUFACTURING_VARIANCE_ACCOUNT_NUMBER = "5080"
NONMANUFACTURING_BURDEN_ACCOUNT_NUMBER = "6060"


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


def payroll_summary_document_id(payroll_period_id: int, cost_center_id: int, summary_kind: str) -> int:
    kind_offset = 1 if str(summary_kind) == "register" else 2
    return int(kind_offset * 1_000_000 + int(payroll_period_id) * 1_000 + int(cost_center_id))


def payroll_summary_voucher_number(payroll_period_id: int, cost_center_id: int, summary_kind: str) -> str:
    prefix = "PRS" if str(summary_kind) == "register" else "PRPS"
    return f"{prefix}-{int(payroll_period_id):04d}-{int(cost_center_id):03d}"


def _payroll_summary_rows(
    context: GenerationContext,
    aggregated_amounts: dict[tuple[int, int, int], dict[str, Any]],
    *,
    summary_kind: str,
    voucher_type: str,
    source_document_type: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (payroll_period_id, cost_center_id, account_id), amounts in sorted(aggregated_amounts.items()):
        debit = money(float(amounts["debit"]))
        credit = money(float(amounts["credit"]))
        if debit <= 0 and credit <= 0:
            continue
        rows.append(build_gl_row(
            context,
            str(amounts["posting_date"]),
            int(account_id),
            debit,
            credit,
            voucher_type,
            payroll_summary_voucher_number(int(payroll_period_id), int(cost_center_id), summary_kind),
            source_document_type,
            payroll_summary_document_id(int(payroll_period_id), int(cost_center_id), summary_kind),
            None,
            int(cost_center_id),
            str(amounts["description"]),
            int(amounts["created_by_employee_id"]),
        ))

    rows_by_voucher: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_voucher[str(row["VoucherNumber"])].append(row)
    for voucher_rows in rows_by_voucher.values():
        assert_balanced(voucher_rows, str(voucher_rows[0]["VoucherNumber"]))

    return rows


def post_shipments(context: GenerationContext) -> list[dict[str, Any]]:
    shipments = context.tables["Shipment"]
    shipment_lines = context.tables["ShipmentLine"]
    if shipments.empty or shipment_lines.empty:
        return []

    freight_expense_account_id = account_id_by_number(context, "5050")
    accrued_expenses_account_id = account_id_by_number(context, "2040")
    items = context.tables["Item"].set_index("ItemID").to_dict("index")
    sales_orders = context.tables["SalesOrder"].set_index("SalesOrderID").to_dict("index")
    lines_by_shipment = {int(key): value for key, value in shipment_lines.groupby("ShipmentID")}
    rows: list[dict[str, Any]] = []

    for shipment in shipments.itertuples(index=False):
        shipment_line_group = lines_by_shipment.get(int(shipment.ShipmentID))
        if shipment_line_group is None or shipment_line_group.empty:
            continue
        sales_order = sales_orders[int(shipment.SalesOrderID)]
        cost_center_id = int(sales_order["CostCenterID"])
        voucher_rows: list[dict[str, Any]] = []
        for line in shipment_line_group.itertuples(index=False):
            item = items[int(line.ItemID)]
            voucher_rows.extend([
                build_gl_row(
                    context,
                    shipment.ShipmentDate,
                    int(item["COGSAccountID"]),
                    float(line.ExtendedStandardCost),
                    0.0,
                    "Shipment",
                    shipment.ShipmentNumber,
                    "Shipment",
                    int(shipment.ShipmentID),
                    int(line.ShipmentLineID),
                    cost_center_id,
                    "Recognize COGS on shipment",
                ),
                build_gl_row(
                    context,
                    shipment.ShipmentDate,
                    int(item["InventoryAccountID"]),
                    0.0,
                    float(line.ExtendedStandardCost),
                    "Shipment",
                    shipment.ShipmentNumber,
                    "Shipment",
                    int(shipment.ShipmentID),
                    int(line.ShipmentLineID),
                    cost_center_id,
                    "Relieve inventory on shipment",
                ),
            ])

        freight_cost = 0.0 if pd.isna(shipment.FreightCost) else float(shipment.FreightCost)
        if freight_cost > 0:
            voucher_rows.extend([
                build_gl_row(
                    context,
                    shipment.ShipmentDate,
                    freight_expense_account_id,
                    freight_cost,
                    0.0,
                    "Shipment",
                    shipment.ShipmentNumber,
                    "Shipment",
                    int(shipment.ShipmentID),
                    None,
                    cost_center_id,
                    "Recognize freight-out expense on shipment",
                ),
                build_gl_row(
                    context,
                    shipment.ShipmentDate,
                    accrued_expenses_account_id,
                    0.0,
                    freight_cost,
                    "Shipment",
                    shipment.ShipmentNumber,
                    "Shipment",
                    int(shipment.ShipmentID),
                    None,
                    cost_center_id,
                    "Accrue outbound freight payable",
                ),
            ])
        assert_balanced(voucher_rows, shipment.ShipmentNumber)
        rows.extend(voucher_rows)

    return rows


def post_sales_invoices(context: GenerationContext) -> list[dict[str, Any]]:
    invoices = context.tables["SalesInvoice"]
    invoice_lines = context.tables["SalesInvoiceLine"]
    if invoices.empty or invoice_lines.empty:
        return []

    ar_account_id = account_id_by_number(context, "1020")
    freight_revenue_account_id = account_id_by_number(context, "4050")
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

        freight_amount = 0.0 if pd.isna(invoice.FreightAmount) else float(invoice.FreightAmount)
        if freight_amount > 0:
            voucher_rows.append(build_gl_row(
                context,
                invoice.InvoiceDate,
                freight_revenue_account_id,
                0.0,
                freight_amount,
                "SalesInvoice",
                invoice.InvoiceNumber,
                "SalesInvoice",
                int(invoice.SalesInvoiceID),
                None,
                int(sales_order["CostCenterID"]),
                "Recognize billed freight revenue",
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
    freight_revenue_account_id = account_id_by_number(context, "4050")
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

        freight_credit_amount = 0.0 if pd.isna(credit_memo.FreightCreditAmount) else float(credit_memo.FreightCreditAmount)
        if freight_credit_amount > 0:
            voucher_rows.append(build_gl_row(
                context,
                credit_memo.CreditMemoDate,
                freight_revenue_account_id,
                freight_credit_amount,
                0.0,
                "CreditMemo",
                credit_memo.CreditMemoNumber,
                "CreditMemo",
                int(credit_memo.CreditMemoID),
                None,
                int(sales_order["CostCenterID"]),
                "Reverse billed freight revenue",
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
    payroll_periods = context.tables["PayrollPeriod"]
    if registers.empty or register_lines.empty or employees.empty or cost_centers.empty or payroll_periods.empty:
        return []

    cost_center_names = cost_centers.set_index("CostCenterID")["CostCenterName"].to_dict()
    payroll_period_lookup = payroll_periods.set_index("PayrollPeriodID").to_dict("index")
    lines_by_register = {key: value for key, value in register_lines.groupby("PayrollRegisterID")}
    salary_accounts = payroll_account_numbers(context)
    accrued_payroll_account_id = account_id_by_number(context, "2030")
    withholdings_account_id = account_id_by_number(context, "2031")
    employer_tax_account_id = account_id_by_number(context, "2032")
    benefits_account_id = account_id_by_number(context, "2033")
    burden_expense_account_id = account_id_by_number(context, NONMANUFACTURING_BURDEN_ACCOUNT_NUMBER)
    manufacturing_clearing_account_id = account_id_by_number(context, MANUFACTURING_CLEARING_ACCOUNT_NUMBER)
    manufacturing_variance_account_id = account_id_by_number(context, MANUFACTURING_VARIANCE_ACCOUNT_NUMBER)
    aggregated_amounts: dict[tuple[int, int, int], dict[str, Any]] = {}

    direct_labor_month_flags: dict[tuple[int, int], bool] = {
        (year, month): monthly_direct_labor_reclass_amount(context, year, month) > 0
        for year, month in {
            fiscal_fields(pd.Timestamp(period["PayDate"]).strftime("%Y-%m-%d"))
            for period in payroll_period_lookup.values()
        }
    }

    def manufacturing_payroll_account_id(posting_date: str, work_order_id: object) -> int:
        fiscal_year, fiscal_period = fiscal_fields(posting_date)
        if pd.notna(work_order_id) or direct_labor_month_flags.get((fiscal_year, fiscal_period), False):
            return manufacturing_clearing_account_id
        return manufacturing_variance_account_id

    def add_summary_amount(
        payroll_period_id: int,
        cost_center_id: int,
        account_id: int,
        debit: float,
        credit: float,
        posting_date: str,
        created_by_employee_id: int,
        description: str,
    ) -> None:
        key = (int(payroll_period_id), int(cost_center_id), int(account_id))
        row = aggregated_amounts.get(key)
        if row is None:
            row = {
                "debit": 0.0,
                "credit": 0.0,
                "posting_date": str(posting_date),
                "created_by_employee_id": int(created_by_employee_id),
                "description": str(description),
            }
            aggregated_amounts[key] = row
        row["debit"] = money(float(row["debit"]) + float(debit))
        row["credit"] = money(float(row["credit"]) + float(credit))

    for register in registers.itertuples(index=False):
        period = payroll_period_lookup[int(register.PayrollPeriodID)]
        posting_date = pd.Timestamp(period["PayDate"]).strftime("%Y-%m-%d")
        cost_center_name = str(cost_center_names[int(register.CostCenterID)])
        register_line_group = lines_by_register.get(int(register.PayrollRegisterID))
        if register_line_group is None or register_line_group.empty:
            continue

        employee_tax_withholding = 0.0
        benefits_and_deductions = 0.0

        for line in register_line_group.itertuples(index=False):
            line_type = str(line.LineType)
            if line_type in {"Regular Earnings", "Overtime Earnings", "Salary Earnings", "Bonus"}:
                if cost_center_name == "Manufacturing":
                    debit_account_id = manufacturing_payroll_account_id(posting_date, line.WorkOrderID)
                else:
                    debit_account_id = account_id_by_number(context, salary_accounts[int(register.CostCenterID)])
                add_summary_amount(
                    int(register.PayrollPeriodID),
                    int(register.CostCenterID),
                    int(debit_account_id),
                    float(line.Amount),
                    0.0,
                    posting_date,
                    int(register.ApprovedByEmployeeID),
                    f"Summarize {line_type.lower()}",
                )
            elif line_type == "Employee Tax Withholding":
                employee_tax_withholding += float(line.Amount)
            elif line_type == "Benefits Deduction":
                benefits_and_deductions += float(line.Amount)
            elif line_type == "Employer Payroll Tax":
                expense_account_id = (
                    manufacturing_payroll_account_id(posting_date, None)
                    if cost_center_name == "Manufacturing"
                    else burden_expense_account_id
                )
                add_summary_amount(
                    int(register.PayrollPeriodID),
                    int(register.CostCenterID),
                    int(expense_account_id),
                    float(line.Amount),
                    0.0,
                    posting_date,
                    int(register.ApprovedByEmployeeID),
                    "Summarize employer payroll tax expense",
                )
            elif line_type == "Employer Benefits":
                expense_account_id = (
                    manufacturing_payroll_account_id(posting_date, None)
                    if cost_center_name == "Manufacturing"
                    else burden_expense_account_id
                )
                add_summary_amount(
                    int(register.PayrollPeriodID),
                    int(register.CostCenterID),
                    int(expense_account_id),
                    float(line.Amount),
                    0.0,
                    posting_date,
                    int(register.ApprovedByEmployeeID),
                    "Summarize employer benefits expense",
                )
                benefits_and_deductions += float(line.Amount)

        add_summary_amount(
            int(register.PayrollPeriodID),
            int(register.CostCenterID),
            int(accrued_payroll_account_id),
            0.0,
            float(register.NetPay),
            posting_date,
            int(register.ApprovedByEmployeeID),
            "Summarize net pay liability",
        )
        add_summary_amount(
            int(register.PayrollPeriodID),
            int(register.CostCenterID),
            int(withholdings_account_id),
            0.0,
            money(employee_tax_withholding),
            posting_date,
            int(register.ApprovedByEmployeeID),
            "Summarize payroll tax withholdings payable",
        )
        add_summary_amount(
            int(register.PayrollPeriodID),
            int(register.CostCenterID),
            int(employer_tax_account_id),
            0.0,
            float(register.EmployerPayrollTax),
            posting_date,
            int(register.ApprovedByEmployeeID),
            "Summarize employer payroll tax payable",
        )
        add_summary_amount(
            int(register.PayrollPeriodID),
            int(register.CostCenterID),
            int(benefits_account_id),
            0.0,
            money(benefits_and_deductions),
            posting_date,
            int(register.ApprovedByEmployeeID),
            "Summarize benefits and deductions payable",
        )

    return _payroll_summary_rows(
        context,
        aggregated_amounts,
        summary_kind="register",
        voucher_type=PAYROLL_SUMMARY_VOUCHER_TYPE,
        source_document_type=PAYROLL_SUMMARY_SOURCE_DOCUMENT_TYPE,
    )


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


def post_payroll_payments_summary(context: GenerationContext) -> list[dict[str, Any]]:
    payments = context.tables["PayrollPayment"]
    registers = context.tables["PayrollRegister"]
    payroll_periods = context.tables["PayrollPeriod"]
    if payments.empty or registers.empty or payroll_periods.empty:
        return []

    register_lookup = registers.set_index("PayrollRegisterID").to_dict("index")
    payroll_period_lookup = payroll_periods.set_index("PayrollPeriodID").to_dict("index")
    accrued_payroll_account_id = account_id_by_number(context, "2030")
    cash_account_id = account_id_by_number(context, "1010")
    aggregated_amounts: dict[tuple[int, int, int], dict[str, Any]] = {}

    def add_summary_amount(
        payroll_period_id: int,
        cost_center_id: int,
        account_id: int,
        debit: float,
        credit: float,
        posting_date: str,
        created_by_employee_id: int,
        description: str,
    ) -> None:
        key = (int(payroll_period_id), int(cost_center_id), int(account_id))
        row = aggregated_amounts.get(key)
        if row is None:
            row = {
                "debit": 0.0,
                "credit": 0.0,
                "posting_date": str(posting_date),
                "created_by_employee_id": int(created_by_employee_id),
                "description": str(description),
            }
            aggregated_amounts[key] = row
        row["debit"] = money(float(row["debit"]) + float(debit))
        row["credit"] = money(float(row["credit"]) + float(credit))

    for payment in payments.itertuples(index=False):
        register = register_lookup[int(payment.PayrollRegisterID)]
        payroll_period_id = int(register["PayrollPeriodID"])
        period = payroll_period_lookup[payroll_period_id]
        posting_date = pd.Timestamp(period["PayDate"]).strftime("%Y-%m-%d")
        cost_center_id = int(register["CostCenterID"])
        add_summary_amount(
            payroll_period_id,
            cost_center_id,
            int(accrued_payroll_account_id),
            float(register["NetPay"]),
            0.0,
            posting_date,
            int(payment.RecordedByEmployeeID),
            "Summarize payroll cash clearing",
        )
        add_summary_amount(
            payroll_period_id,
            cost_center_id,
            int(cash_account_id),
            0.0,
            float(register["NetPay"]),
            posting_date,
            int(payment.RecordedByEmployeeID),
            "Summarize payroll cash disbursement",
        )

    return _payroll_summary_rows(
        context,
        aggregated_amounts,
        summary_kind="payment",
        voucher_type="PayrollPayment",
        source_document_type="PayrollPayment",
    )


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

    payroll_register_rows = post_payroll_registers(context)
    payroll_payment_rows = post_payroll_payments(context)
    payroll_payment_summary_mode = "detail"

    operational_rows: list[dict[str, Any]] = []
    operational_rows.extend(post_shipments(context))
    operational_rows.extend(post_sales_invoices(context))
    operational_rows.extend(post_cash_receipts(context))
    operational_rows.extend(post_cash_receipt_applications(context))
    operational_rows.extend(post_sales_returns(context))
    operational_rows.extend(post_credit_memos(context))
    operational_rows.extend(post_customer_refunds(context))
    operational_rows.extend(payroll_register_rows)
    operational_rows.extend(post_payroll_liability_remittances(context))
    operational_rows.extend(post_material_issues(context))
    operational_rows.extend(post_production_completions(context))
    operational_rows.extend(post_work_order_closes(context))
    operational_rows.extend(post_goods_receipts(context))
    operational_rows.extend(post_purchase_invoices(context))
    operational_rows.extend(post_disbursements(context))

    projected_total_rows = len(opening_gl) + len(operational_rows) + len(payroll_payment_rows)
    if projected_total_rows > PREFERRED_EXCEL_GLENTRY_ROW_BUDGET:
        payroll_payment_rows = post_payroll_payments_summary(context)
        payroll_payment_summary_mode = "period_cost_center_account"

    operational_rows.extend(payroll_payment_rows)
    setattr(context, "payroll_gl_summary_mode", {
        "register": "period_cost_center_account",
        "payment": payroll_payment_summary_mode,
    })

    operational_gl = pd.DataFrame(operational_rows, columns=TABLE_COLUMNS["GLEntry"])
    context.tables["GLEntry"] = pd.concat([opening_gl, operational_gl], ignore_index=True)
