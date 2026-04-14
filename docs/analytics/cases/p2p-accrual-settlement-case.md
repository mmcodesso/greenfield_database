---
title: P2P Accrual Settlement Case
description: Guided walkthrough for tracing accruals, invoices, and payment timing in the P2P cycle.
sidebar_label: P2P Accrual Case
---

# P2P and Accrued-Expense Settlement Case


## Business Scenario

Greenfield buys inventory and materials through the normal P2P process, but finance also records month-end accrued expenses for insurance, software, and professional fees. Those estimates are later cleared through direct supplier service invoices and normal disbursement payments.

## Main Tables and Worksheets

- `PurchaseRequisition`
- `PurchaseOrder`
- `PurchaseOrderLine`
- `GoodsReceipt`
- `GoodsReceiptLine`
- `PurchaseInvoice`
- `PurchaseInvoiceLine`
- `DisbursementPayment`
- `JournalEntry`
- `GLEntry`

## Recommended Query Sequence

1. Run [../../../queries/audit/02_p2p_document_chain_completeness.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/02_p2p_document_chain_completeness.sql).
2. Run [../../../queries/financial/03_ap_aging_open_invoices.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/03_ap_aging_open_invoices.sql).
3. Run [../../../queries/financial/12_accrued_expense_rollforward.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/12_accrued_expense_rollforward.sql).
4. Run [../../../queries/financial/13_accrued_vs_invoiced_vs_paid_timing.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/13_accrued_vs_invoiced_vs_paid_timing.sql).
5. For audit follow-up, run [../../../queries/audit/23_accrued_service_settlement_exception_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/23_accrued_service_settlement_exception_review.sql).

## Suggested Excel Sequence

1. Trace one requisition into `PurchaseOrderLine`.
2. Follow the matched inventory path through `GoodsReceiptLine` and `PurchaseInvoiceLine.GoodsReceiptLineID`.
3. Filter `PurchaseInvoiceLine` to rows where `AccrualJournalEntryID` is populated.
4. Tie those service-settlement lines back to `JournalEntry` and then forward to `DisbursementPayment`.

## What Students Should Notice

- Inventory AP and accrued-service settlement intentionally share the same AP tables.
- Goods receipts create GRNI, but accrued-service invoices clear `2040` instead.
- Payment can lag both receipt and invoice timing.
- Service invoices without receipt linkage are intentional in this dataset, not necessarily errors.

## Follow-Up Questions

- Which fields distinguish receipt-matched inventory invoicing from accrued-service settlement?
- Why is `PurchaseInvoiceLine.AccrualJournalEntryID` useful in both analytics and audit work?
- What would make a direct service invoice look unusual enough for audit follow-up?
