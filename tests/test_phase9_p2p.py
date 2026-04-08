from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from greenfield_dataset.main import build_full_dataset, build_phase5
from greenfield_dataset.p2p import (
    generate_month_disbursements,
    generate_month_goods_receipts,
    generate_month_p2p,
    generate_month_purchase_invoices,
)
from greenfield_dataset.settings import load_settings


def test_phase9_multimonth_p2p_partial_and_linked_flows() -> None:
    context = build_phase5()

    for year, month in [(2026, 2), (2026, 3), (2026, 4)]:
        generate_month_p2p(context, year, month)
        generate_month_goods_receipts(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_disbursements(context, year, month)

    purchase_orders = context.tables["PurchaseOrder"]
    purchase_order_lines = context.tables["PurchaseOrderLine"]
    goods_receipts = context.tables["GoodsReceipt"]
    goods_receipt_lines = context.tables["GoodsReceiptLine"]
    purchase_invoices = context.tables["PurchaseInvoice"]
    purchase_invoice_lines = context.tables["PurchaseInvoiceLine"]
    disbursements = context.tables["DisbursementPayment"]

    assert len(purchase_order_lines) > len(purchase_orders)
    assert purchase_order_lines["RequisitionID"].notna().all()
    assert purchase_orders["RequisitionID"].isna().any()

    assert len(goods_receipt_lines) > len(goods_receipts)
    assert goods_receipt_lines["POLineID"].value_counts().gt(1).any()

    receipt_dates = goods_receipt_lines.merge(
        goods_receipts[["GoodsReceiptID", "ReceiptDate"]],
        on="GoodsReceiptID",
        how="left",
    )
    repeated_receipt_months = (
        pd.to_datetime(receipt_dates["ReceiptDate"]).dt.to_period("M").groupby(receipt_dates["POLineID"]).nunique()
    )
    assert repeated_receipt_months.gt(1).any()

    assert len(purchase_invoice_lines) > len(purchase_invoices)
    assert purchase_invoice_lines["GoodsReceiptLineID"].notna().all()

    invoice_dates = purchase_invoice_lines.merge(
        purchase_invoices[["PurchaseInvoiceID", "InvoiceDate"]],
        on="PurchaseInvoiceID",
        how="left",
    ).merge(
        goods_receipt_lines[["GoodsReceiptLineID", "GoodsReceiptID"]],
        on="GoodsReceiptLineID",
        how="left",
    ).merge(
        goods_receipts[["GoodsReceiptID", "ReceiptDate"]],
        on="GoodsReceiptID",
        how="left",
    )
    assert (
        pd.to_datetime(invoice_dates["InvoiceDate"]).dt.to_period("M")
        > pd.to_datetime(invoice_dates["ReceiptDate"]).dt.to_period("M")
    ).any()

    assert len(disbursements) > 0
    assert disbursements["PurchaseInvoiceID"].value_counts().gt(1).any()
    assert purchase_invoices["Status"].eq("Partially Paid").any()


def test_phase9_full_dataset_p2p_volume_regression(tmp_path: Path) -> None:
    settings = load_settings("config/settings.yaml")
    payload = dict(vars(settings))
    payload.update({
        "anomaly_mode": "none",
        "export_sqlite": False,
        "export_excel": False,
        "sqlite_path": str(tmp_path / "greenfield.sqlite"),
        "excel_path": str(tmp_path / "greenfield.xlsx"),
        "validation_report_path": str(tmp_path / "validation_report.json"),
        "generation_log_path": str(tmp_path / "generation.log"),
    })

    config_path = tmp_path / "settings.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    context = build_full_dataset(config_path)
    phase9 = context.validation_results["phase9"]
    row_counts = phase9["row_counts"]

    assert phase9["exceptions"] == []
    assert row_counts["PurchaseOrderLine"] > 4500
    assert row_counts["GoodsReceiptLine"] > 4500
    assert row_counts["PurchaseInvoiceLine"] > 4000
    assert row_counts["DisbursementPayment"] > 2300
    assert (tmp_path / "validation_report.json").exists()
    assert (tmp_path / "generation.log").exists()
