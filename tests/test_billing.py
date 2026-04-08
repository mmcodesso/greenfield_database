from greenfield_dataset.main import build_phase4
from greenfield_dataset.o2c import generate_month_cash_receipts, generate_month_sales_invoices
from greenfield_dataset.p2p import generate_month_disbursements, generate_month_purchase_invoices
from greenfield_dataset.validations import validate_phase5


def test_generate_phase5_billing_and_payments() -> None:
    context = build_phase4()

    generate_month_sales_invoices(context, 2026, 1)
    generate_month_cash_receipts(context, 2026, 1)
    generate_month_purchase_invoices(context, 2026, 1)
    generate_month_disbursements(context, 2026, 1)
    results = validate_phase5(context)

    assert results["exceptions"] == []
    assert len(context.tables["SalesInvoice"]) > 0
    assert len(context.tables["SalesInvoiceLine"]) >= len(context.tables["SalesInvoice"])
    assert len(context.tables["CashReceipt"]) > 0
    assert len(context.tables["PurchaseInvoice"]) > 0
    assert len(context.tables["PurchaseInvoiceLine"]) >= len(context.tables["PurchaseInvoice"])
    assert context.tables["PurchaseInvoiceLine"]["GoodsReceiptLineID"].notna().all()
    assert len(context.tables["DisbursementPayment"]) > 0
    assert context.tables["SalesInvoice"]["InvoiceNumber"].is_unique
    assert context.tables["CashReceipt"]["ReceiptNumber"].is_unique
    assert context.tables["DisbursementPayment"]["PaymentNumber"].is_unique
