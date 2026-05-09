from __future__ import annotations

import pandas as pd

from generator_dataset.main import build_phase5
from generator_dataset.o2c import (
    TARGET_INVOICE_RETURN_RATE_MAX,
    TARGET_INVOICE_RETURN_RATE_MIN,
    generate_month_cash_receipts,
    generate_month_customer_refunds,
    generate_month_o2c,
    generate_month_sales_commissions,
    generate_month_sales_invoices,
    generate_month_sales_returns,
    generate_month_shipments,
)
from generator_dataset.p2p import (
    generate_month_disbursements,
    generate_month_goods_receipts,
    generate_month_p2p,
    generate_month_purchase_invoices,
)
from generator_dataset.utils import money


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
        generate_month_sales_commissions(context, year, month)
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
    service_engagements = context.tables["ServiceEngagement"]
    service_assignments = context.tables["ServiceEngagementAssignment"]
    service_time_entries = context.tables["ServiceTimeEntry"]
    service_billing_lines = context.tables["ServiceBillingLine"]

    goods_invoice_lines = sales_invoice_lines[sales_invoice_lines["ShipmentLineID"].notna()].copy()
    service_invoice_lines = sales_invoice_lines[sales_invoice_lines["ShipmentLineID"].isna()].copy()

    assert not goods_invoice_lines.empty
    assert goods_invoice_lines["ShipmentLineID"].notna().all()
    assert not service_engagements.empty
    assert not service_assignments.empty
    assert not service_time_entries.empty
    assert not service_billing_lines.empty
    assert not service_invoice_lines.empty
    assert service_invoice_lines["ShipmentLineID"].isna().all()
    assert len(cash_applications) > 0
    assert cash_receipts["SalesInvoiceID"].isna().any()
    assert cash_applications["CashReceiptID"].value_counts().gt(1).any()
    assert sales_orders["Status"].eq("Backordered").any()
    assert len(sales_returns) > 0
    assert len(credit_memos) == len(sales_returns)
    assert len(customer_refunds) > 0
    assert credit_memos["OriginalSalesInvoiceID"].astype(int).value_counts().max() == 1
    assert sales_return_lines.groupby("SalesReturnID").size().max() <= 2
    assert service_assignments.groupby("ServiceEngagementID").size().ge(2).any()

    approved_billable_by_engagement = service_time_entries.groupby("ServiceEngagementID")["BillableHours"].sum().round(2)
    billed_by_engagement = service_billing_lines.groupby("ServiceEngagementID")["BilledHours"].sum().round(2)
    assert approved_billable_by_engagement.ge(billed_by_engagement).all()

    billed_service_lines = service_billing_lines.merge(
        service_invoice_lines[["SalesInvoiceLineID", "Quantity", "LineTotal"]],
        on="SalesInvoiceLineID",
        how="inner",
    )
    assert len(billed_service_lines) == len(service_billing_lines)
    assert billed_service_lines["BilledHours"].astype(float).round(2).eq(
        billed_service_lines["Quantity"].astype(float).round(2)
    ).all()
    assert billed_service_lines["LineAmount"].astype(float).round(2).eq(
        billed_service_lines["LineTotal"].astype(float).round(2)
    ).all()

    returns_with_invoice_dates = (
        sales_returns[["SalesReturnID", "ReturnDate"]]
        .merge(credit_memos[["SalesReturnID", "OriginalSalesInvoiceID"]], on="SalesReturnID", how="inner")
        .merge(sales_invoices[["SalesInvoiceID", "InvoiceDate"]], left_on="OriginalSalesInvoiceID", right_on="SalesInvoiceID", how="inner")
    )
    assert (pd.to_datetime(returns_with_invoice_dates["ReturnDate"]) > pd.to_datetime(returns_with_invoice_dates["InvoiceDate"])).all()


def test_phase11_multimonth_o2c_freight_modeling() -> None:
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
        generate_month_sales_commissions(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_disbursements(context, year, month)

    sales_orders = context.tables["SalesOrder"]
    shipments = context.tables["Shipment"]
    shipment_lines = context.tables["ShipmentLine"]
    sales_invoices = context.tables["SalesInvoice"]
    sales_invoice_lines = context.tables["SalesInvoiceLine"]
    sales_returns = context.tables["SalesReturn"]
    credit_memos = context.tables["CreditMemo"]

    assert sales_orders["FreightTerms"].isin(["Prepaid", "Prepaid and Add"]).all()
    assert set(sales_orders["FreightTerms"].dropna().unique()) == {"Prepaid", "Prepaid and Add"}
    assert shipments["FreightCost"].fillna(0.0).astype(float).gt(0).any()
    assert shipments["BillableFreightAmount"].fillna(0.0).astype(float).gt(0).any()
    assert shipments["BillableFreightAmount"].fillna(0.0).astype(float).eq(0).any()
    assert sales_invoices["FreightAmount"].fillna(0.0).astype(float).gt(0).any()
    assert sales_invoices["FreightAmount"].fillna(0.0).astype(float).eq(0).any()
    assert ((
        sales_invoices["SubTotal"].astype(float)
        + sales_invoices["FreightAmount"].fillna(0.0).astype(float)
        + sales_invoices["TaxAmount"].astype(float)
    ).round(2) == sales_invoices["GrandTotal"].astype(float).round(2)).all()
    assert ((
        credit_memos["SubTotal"].astype(float)
        + credit_memos["FreightCreditAmount"].fillna(0.0).astype(float)
        + credit_memos["TaxAmount"].astype(float)
    ).round(2) == credit_memos["GrandTotal"].astype(float).round(2)).all()

    invoiced_shipment_ids = set(
        sales_invoice_lines[["ShipmentLineID"]]
        .merge(shipment_lines[["ShipmentLineID", "ShipmentID"]], on="ShipmentLineID", how="left")["ShipmentID"]
        .dropna()
        .astype(int)
        .tolist()
    )
    expected_freight_billed_total = round(
        float(
            shipments.loc[
                shipments["ShipmentID"].astype(int).isin(invoiced_shipment_ids),
                "BillableFreightAmount",
            ].fillna(0.0).astype(float).sum()
        ),
        2,
    )
    assert round(float(sales_invoices["FreightAmount"].fillna(0.0).astype(float).sum()), 2) == expected_freight_billed_total

    remorse_freight_credits = (
        sales_returns[sales_returns["ReasonCode"].eq("Customer Remorse")][["SalesReturnID"]]
        .merge(credit_memos[["SalesReturnID", "FreightCreditAmount"]], on="SalesReturnID", how="inner")
    )
    if not remorse_freight_credits.empty:
        assert remorse_freight_credits["FreightCreditAmount"].fillna(0.0).astype(float).eq(0.0).all()


def test_phase11_full_dataset_clean_validation(full_dataset_artifacts: dict[str, object]) -> None:
    context = full_dataset_artifacts["context"]
    phase11 = context.validation_results["phase11"]
    row_counts = phase11["row_counts"]
    o2c_controls = phase11["o2c_controls"]

    assert phase11["exceptions"] == []
    assert phase11["gl_balance"]["exception_count"] == 0
    assert phase11["trial_balance_difference"] == 0
    assert phase11["account_rollforward"]["exception_count"] == 0
    assert o2c_controls["exception_count"] == 0
    assert phase11["p2p_controls"]["exception_count"] == 0
    assert phase11["journal_controls"]["exception_count"] == 0
    assert o2c_controls["invoice_before_shipment_count"] == 0
    assert o2c_controls["invoice_gl_year_mismatch_count"] == 0
    assert float(o2c_controls["invoice_gl_year_mismatch_amount"]) == 0.0
    assert o2c_controls["invoice_gl_year_mismatch_by_pair"] == []
    assert row_counts["CashReceiptApplication"] > row_counts["CashReceipt"]
    assert row_counts["SalesReturn"] > 0
    assert row_counts["CreditMemo"] > 0
    assert row_counts["CustomerRefund"] > 0
    assert row_counts["ServiceEngagement"] > 0
    assert row_counts["ServiceEngagementAssignment"] > row_counts["ServiceEngagement"]
    assert row_counts["ServiceTimeEntry"] > 0
    assert row_counts["ServiceBillingLine"] > 0

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


def test_phase11_full_dataset_design_service_invoice_posting(full_dataset_artifacts: dict[str, object]) -> None:
    context = full_dataset_artifacts["context"]
    service_billing_lines = context.tables["ServiceBillingLine"]
    sales_invoice_lines = context.tables["SalesInvoiceLine"]
    shipment_lines = context.tables["ShipmentLine"]
    gl_entries = context.tables["GLEntry"]
    accounts = context.tables["Account"][["AccountID", "AccountNumber", "AccountSubType"]]

    assert not service_billing_lines.empty

    service_invoice_line_ids = set(service_billing_lines["SalesInvoiceLineID"].astype(int).tolist())
    service_invoice_lines = sales_invoice_lines[
        sales_invoice_lines["SalesInvoiceLineID"].astype(int).isin(service_invoice_line_ids)
    ].copy()
    assert not service_invoice_lines.empty
    assert service_invoice_lines["ShipmentLineID"].isna().all()

    line_gl_entries = gl_entries.loc[gl_entries["SourceLineID"].notna()].copy()
    posted_service_rows = line_gl_entries[
        line_gl_entries["SourceDocumentType"].eq("SalesInvoice")
        & line_gl_entries["SourceLineID"].astype(int).isin(service_invoice_line_ids)
    ].merge(accounts, on="AccountID", how="left")
    revenue_rows = posted_service_rows[posted_service_rows["AccountNumber"].astype(str).eq("4080")].copy()

    assert not revenue_rows.empty
    assert revenue_rows["Debit"].astype(float).eq(0.0).all()
    assert round(float(revenue_rows["Credit"].astype(float).sum()), 2) == round(
        float(service_billing_lines["LineAmount"].astype(float).sum()),
        2,
    )
    assert not posted_service_rows["AccountSubType"].astype(str).eq("COGS").any()

    shipped_service_lines = shipment_lines[
        shipment_lines["SalesOrderLineID"].astype(int).isin(service_invoice_lines["SalesOrderLineID"].astype(int))
    ]
    assert shipped_service_lines.empty


def test_phase11_full_dataset_sales_commissions_accrue_adjust_and_settle(
    full_dataset_artifacts: dict[str, object],
) -> None:
    context = full_dataset_artifacts["context"]
    rates = context.tables["SalesCommissionRate"]
    accruals = context.tables["SalesCommissionAccrual"]
    adjustments = context.tables["SalesCommissionAdjustment"]
    payments = context.tables["SalesCommissionPayment"]
    payment_lines = context.tables["SalesCommissionPaymentLine"]
    invoice_lines = context.tables["SalesInvoiceLine"]
    credit_memo_lines = context.tables["CreditMemoLine"]
    gl_entries = context.tables["GLEntry"]
    accounts = context.tables["Account"][["AccountID", "AccountNumber"]]

    assert len(rates) >= 8
    assert not accruals.empty
    assert not payments.empty
    assert not payment_lines.empty
    assert accruals["SalesInvoiceLineID"].is_unique
    assert set(accruals["RevenueType"].astype(str)).issubset({"Merchandise", "Design Service"})

    commissioned_invoice_line_ids = set(invoice_lines.loc[
        invoice_lines["LineTotal"].astype(float).gt(0),
        "SalesInvoiceLineID",
    ].astype(int))
    assert set(accruals["SalesInvoiceLineID"].astype(int)) == commissioned_invoice_line_ids

    accrual_check = accruals.merge(
        invoice_lines[["SalesInvoiceLineID", "LineTotal"]],
        on="SalesInvoiceLineID",
        how="left",
    )
    assert (
        accrual_check["CommissionBaseAmount"].astype(float).round(2)
        == accrual_check["LineTotal"].astype(float).round(2)
    ).all()
    expected_accrual = accrual_check.apply(
        lambda row: money(float(row["CommissionBaseAmount"]) * float(row["CommissionRatePct"])),
        axis=1,
    )
    assert (expected_accrual == accrual_check["CommissionAmount"].astype(float).round(2)).all()

    if not credit_memo_lines.empty:
        assert not adjustments.empty
        assert adjustments["CreditMemoLineID"].is_unique
        adjustment_check = adjustments.merge(
            accruals[["SalesCommissionAccrualID", "CommissionRatePct"]],
            on="SalesCommissionAccrualID",
            how="left",
            suffixes=("", "_Accrual"),
        )
        expected_adjustment = adjustment_check.apply(
            lambda row: money(float(row["CommissionBaseReductionAmount"]) * float(row["CommissionRatePct_Accrual"])),
            axis=1,
        )
        assert (expected_adjustment == adjustment_check["CommissionAdjustmentAmount"].astype(float).round(2)).all()

    payment_detail = payment_lines.groupby("SalesCommissionPaymentID", as_index=False, dropna=False)["Amount"].sum()
    payment_check = payments.merge(payment_detail, on="SalesCommissionPaymentID", how="left")
    assert (
        payment_check["Amount"].astype(float).round(2)
        == payment_check["NetPaymentAmount"].astype(float).round(2)
    ).all()

    commission_gl = gl_entries[gl_entries["SourceDocumentType"].astype(str).isin([
        "SalesCommissionAccrual",
        "SalesCommissionAdjustment",
        "SalesCommissionPayment",
    ])].copy()
    assert not commission_gl.empty
    voucher_balance = commission_gl.groupby(["VoucherType", "VoucherNumber"], dropna=False)[["Debit", "Credit"]].sum()
    assert (voucher_balance["Debit"].round(2) == voucher_balance["Credit"].round(2)).all()

    commission_gl = commission_gl.merge(accounts, on="AccountID", how="left")
    payable_activity = commission_gl[commission_gl["AccountNumber"].astype(str).eq("2034")]
    assert round(float(payable_activity["Credit"].sum() - payable_activity["Debit"].sum()), 2) == round(
        float(accruals["CommissionAmount"].sum())
        - float(adjustments["CommissionAdjustmentAmount"].sum() if not adjustments.empty else 0.0)
        - float(payments["NetPaymentAmount"].sum()),
        2,
    )


def test_phase11_full_dataset_receivables_realism(full_dataset_artifacts: dict[str, object]) -> None:
    context = full_dataset_artifacts["context"]
    phase23 = context.validation_results["phase23"]
    receivables_metrics = phase23["o2c_controls"]["receivables_metrics"]
    year_end_dso_series = phase23["o2c_controls"]["year_end_dso_series"]

    assert receivables_metrics["implied_dso"] <= 90.0
    assert receivables_metrics["aging_90_plus_share"] <= 0.15
    assert receivables_metrics["aging_current_to_60_share"] >= 0.75
    assert receivables_metrics["open_invoices_gt_365_count"] <= max(
        5,
        int(receivables_metrics["open_invoice_count"] * 0.01),
    )
    if len(year_end_dso_series) >= 3:
        dso_values = [float(row["implied_dso"]) for row in year_end_dso_series]
        assert not (
            all(later > earlier + 7.0 for earlier, later in zip(dso_values, dso_values[1:]))
            and dso_values[-1] > dso_values[0] + 35.0
        )

    generation_log_text = full_dataset_artifacts["generation_log_path"].read_text(encoding="utf-8")
    assert "implied_dso=" in generation_log_text
    assert "aging_90_plus_share=" in generation_log_text
    assert "invoice_before_shipment_count=0" in generation_log_text
    assert "invoice_gl_year_mismatch_count=0" in generation_log_text
    assert "invoice_gl_year_mismatch_by_pair=[]" in generation_log_text


def test_phase11_default_anomaly_dataset_surfaces_invoice_cutoff_guardrails(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    context = default_anomaly_dataset_artifacts["context"]
    o2c_controls = context.validation_results["phase8"]["o2c_controls"]

    assert o2c_controls["invoice_before_shipment_count"] > 0
    assert o2c_controls["invoice_gl_year_mismatch_count"] > 0
    assert round(float(o2c_controls["invoice_gl_year_mismatch_amount"]), 2) > 0.0
    assert o2c_controls["invoice_gl_year_mismatch_by_pair"]

    generation_log_text = default_anomaly_dataset_artifacts["generation_log_path"].read_text(encoding="utf-8")
    assert f"invoice_before_shipment_count={o2c_controls['invoice_before_shipment_count']}" in generation_log_text
    assert f"invoice_gl_year_mismatch_count={o2c_controls['invoice_gl_year_mismatch_count']}" in generation_log_text
    assert f"invoice_gl_year_mismatch_amount={o2c_controls['invoice_gl_year_mismatch_amount']}" in generation_log_text
    assert "invoice_gl_year_mismatch_by_pair=" in generation_log_text
