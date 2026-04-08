from __future__ import annotations

from typing import Any

import pandas as pd

from greenfield_dataset.p2p import (
    goods_receipt_line_cost_center_map,
    purchase_invoice_line_cost_center_map,
    purchase_invoice_line_matched_basis_map,
    purchase_invoice_unique_cost_center_map,
)
from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.settings import GenerationContext
from greenfield_dataset.utils import money, next_id


SYSTEM_EMPLOYEE_ID = 1


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
    ar_account_id = account_id_by_number(context, "1020")
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
                ar_account_id,
                0.0,
                float(receipt.Amount),
                "CashReceipt",
                receipt.ReceiptNumber,
                "CashReceipt",
                int(receipt.CashReceiptID),
                None,
                None,
                "Apply cash receipt to receivable",
                int(receipt.RecordedByEmployeeID),
            ),
        ]
        assert_balanced(voucher_rows, receipt.ReceiptNumber)
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
    grni_account_id = account_id_by_number(context, "2020")
    variance_account_id = account_id_by_number(context, "5060")
    matched_basis_by_invoice_line = purchase_invoice_line_matched_basis_map(context)
    invoice_line_cost_centers = purchase_invoice_line_cost_center_map(context)
    invoice_header_cost_centers = purchase_invoice_unique_cost_center_map(context)
    lines_by_invoice = {key: value for key, value in invoice_lines.groupby("PurchaseInvoiceID")}
    rows: list[dict[str, Any]] = []

    for invoice in invoices.itertuples(index=False):
        voucher_rows: list[dict[str, Any]] = []
        invoice_lines_for_header = lines_by_invoice.get(invoice.PurchaseInvoiceID)
        if invoice_lines_for_header is None:
            continue

        header_cost_center_id = invoice_header_cost_centers.get(int(invoice.PurchaseInvoiceID))
        for line in invoice_lines_for_header.itertuples(index=False):
            accrued_amount = money(float(matched_basis_by_invoice_line.get(int(line.PILineID), line.LineTotal)))
            line_cost_center_id = invoice_line_cost_centers.get(int(line.PILineID))
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
    operational_rows.extend(post_goods_receipts(context))
    operational_rows.extend(post_purchase_invoices(context))
    operational_rows.extend(post_disbursements(context))

    operational_gl = pd.DataFrame(operational_rows, columns=TABLE_COLUMNS["GLEntry"])
    context.tables["GLEntry"] = pd.concat([opening_gl, operational_gl], ignore_index=True)
