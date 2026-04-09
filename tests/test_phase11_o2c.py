from __future__ import annotations

import pandas as pd

from greenfield_dataset.main import build_phase5
from greenfield_dataset.o2c import (
    TARGET_INVOICE_RETURN_RATE_MAX,
    TARGET_INVOICE_RETURN_RATE_MIN,
    generate_month_cash_receipts,
    generate_month_customer_refunds,
    generate_month_o2c,
    generate_month_sales_invoices,
    generate_month_sales_returns,
    generate_month_shipments,
)
from greenfield_dataset.p2p import (
    generate_month_disbursements,
    generate_month_goods_receipts,
    generate_month_p2p,
    generate_month_purchase_invoices,
)


def test_phase11_multimonth_o2c_backorders_returns_and_applications() -> None:
    context = build_phase5()

    for year, month in [(2026, 2), (2026, 3), (2026, 4)]:
        generate_month_o2c(context, year, month)
        generate_month_p2p(context, year, month)
        generate_month_goods_receipts(context, year, month)
        generate_month_shipments(context, year, month)
        generate_month_sales_invoices(context, year, month)
        generate_month_cash_receipts(context, year, month)
        generate_month_sales_returns(context, year, month)
        generate_month_customer_refunds(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_disbursements(context, year, month)

    sales_invoice_lines = context.tables["SalesInvoiceLine"]
    cash_receipts = context.tables["CashReceipt"]
    cash_applications = context.tables["CashReceiptApplication"]
    sales_returns = context.tables["SalesReturn"]
    credit_memos = context.tables["CreditMemo"]
    customer_refunds = context.tables["CustomerRefund"]
    sales_orders = context.tables["SalesOrder"]
    sales_return_lines = context.tables["SalesReturnLine"]
    sales_invoices = context.tables["SalesInvoice"]

    assert sales_invoice_lines["ShipmentLineID"].notna().all()
    assert len(cash_applications) > 0
    assert cash_receipts["SalesInvoiceID"].isna().any()
    assert cash_applications["CashReceiptID"].value_counts().gt(1).any()
    assert sales_orders["Status"].eq("Backordered").any()
    assert len(sales_returns) > 0
    assert len(credit_memos) == len(sales_returns)
    assert len(customer_refunds) > 0
    assert credit_memos["OriginalSalesInvoiceID"].astype(int).value_counts().max() == 1
    assert sales_return_lines.groupby("SalesReturnID").size().max() <= 2

    returns_with_invoice_dates = (
        sales_returns[["SalesReturnID", "ReturnDate"]]
        .merge(credit_memos[["SalesReturnID", "OriginalSalesInvoiceID"]], on="SalesReturnID", how="inner")
        .merge(sales_invoices[["SalesInvoiceID", "InvoiceDate"]], left_on="OriginalSalesInvoiceID", right_on="SalesInvoiceID", how="inner")
    )
    assert (pd.to_datetime(returns_with_invoice_dates["ReturnDate"]) > pd.to_datetime(returns_with_invoice_dates["InvoiceDate"])).all()


def test_phase11_full_dataset_clean_validation(full_dataset_artifacts: dict[str, object]) -> None:
    context = full_dataset_artifacts["context"]
    phase11 = context.validation_results["phase11"]
    row_counts = phase11["row_counts"]

    assert phase11["exceptions"] == []
    assert phase11["gl_balance"]["exception_count"] == 0
    assert phase11["trial_balance_difference"] == 0
    assert phase11["account_rollforward"]["exception_count"] == 0
    assert phase11["o2c_controls"]["exception_count"] == 0
    assert phase11["p2p_controls"]["exception_count"] == 0
    assert phase11["journal_controls"]["exception_count"] == 0
    assert row_counts["CashReceiptApplication"] > row_counts["CashReceipt"]
    assert row_counts["SalesReturn"] > 0
    assert row_counts["CreditMemo"] > 0
    assert row_counts["CustomerRefund"] > 0

    credit_memos = context.tables["CreditMemo"]
    sales_invoices = context.tables["SalesInvoice"]
    shipment_lines = context.tables["ShipmentLine"]
    sales_return_lines = context.tables["SalesReturnLine"]

    distinct_returned_invoices = int(credit_memos["OriginalSalesInvoiceID"].astype(int).nunique())
    invoice_return_incidence = distinct_returned_invoices / max(len(sales_invoices), 1)
    assert TARGET_INVOICE_RETURN_RATE_MIN <= invoice_return_incidence <= TARGET_INVOICE_RETURN_RATE_MAX
    assert len(credit_memos) == distinct_returned_invoices
    assert row_counts["SalesReturn"] == row_counts["CreditMemo"]

    returned_quantity_ratio = float(sales_return_lines["QuantityReturned"].sum()) / max(float(shipment_lines["QuantityShipped"].sum()), 1.0)
    credit_subtotal_ratio = float(credit_memos["SubTotal"].sum()) / max(float(sales_invoices["SubTotal"].sum()), 1.0)
    assert returned_quantity_ratio < 0.05
    assert credit_subtotal_ratio < 0.05
