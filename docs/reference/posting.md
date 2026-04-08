# Posting Reference

**Audience:** Contributors, advanced students, and instructors who need the implemented accounting logic in technical form.  
**Purpose:** Document the event-based posting rules used by the current generator.  
**What you will learn:** Which documents post, which accounts are affected, and how postings are traced back to source transactions.

Posting logic is implemented in `src/greenfield_dataset/posting_engine.py`.

> **Implemented in current generator:** Event-based postings for shipments, sales invoices, cash receipts, goods receipts, purchase invoices, and disbursements, plus an opening balance journal created earlier in the build.

> **Planned future extension:** Recurring manual operating journals and future manufacturing-related posting events.

## Non-Posting Documents

These documents are generated for process analysis but do **not** create `GLEntry` rows in the current implementation:

- `SalesOrder`
- `SalesOrderLine`
- `PurchaseRequisition`
- `PurchaseOrder`
- `PurchaseOrderLine`

## Posting Matrix

| Event | Source tables | Posting date used | Debit | Credit |
|---|---|---|---|---|
| Opening balance journal | `JournalEntry` plus seeded GL rows from `budgets.py` | `2026-01-01` | Asset accounts and selected opening balances | Liability, equity, contra-asset balances, and retained earnings plug |
| Shipment | `Shipment`, `ShipmentLine` | `ShipmentDate` | Item COGS account | Item inventory account |
| Sales invoice | `SalesInvoice`, `SalesInvoiceLine` | `InvoiceDate` | Accounts receivable | Item revenue account and sales tax payable |
| Cash receipt | `CashReceipt` | `ReceiptDate` | Cash | Accounts receivable |
| Goods receipt | `GoodsReceipt`, `GoodsReceiptLine` | `ReceiptDate` | Item inventory account | Goods Received Not Invoiced |
| Purchase invoice | `PurchaseInvoice`, `PurchaseInvoiceLine` | `ApprovedDate` | GRNI, purchase variance when needed, and nonrecoverable tax to variance | Accounts payable and purchase variance when needed |
| Disbursement | `DisbursementPayment` | `PaymentDate` | Accounts payable | Cash |

## Core Control Accounts

| Account number | Meaning |
|---|---|
| `1010` | Cash and cash equivalents |
| `1020` | Accounts receivable |
| `1040` | Inventory - finished goods |
| `1045` | Inventory - materials and packaging |
| `2010` | Accounts payable |
| `2020` | Goods Received Not Invoiced |
| `2050` | Sales tax payable |
| `3030` | Retained earnings |
| `5060` | Purchase price variance |

Item-specific posting relies on these `Item` fields:

- `InventoryAccountID`
- `RevenueAccountID`
- `COGSAccountID`
- `PurchaseVarianceAccountID`

## Source Traceability

Each operational posting written to `GLEntry` includes:

- `VoucherType`
- `VoucherNumber`
- `SourceDocumentType`
- `SourceDocumentID`
- `SourceLineID`
- `PostingDate`
- `FiscalYear`
- `FiscalPeriod`

This lets users trace both forward and backward:

- from source documents into the ledger
- from ledger detail back to the originating transaction

## Cost Center Behavior

The current implementation uses cost centers where they are operationally meaningful:

- shipment postings inherit `CostCenterID` from the related sales order
- sales revenue postings inherit `CostCenterID` from the related sales order
- many control-account rows remain at `CostCenterID = null`

This is sufficient for teaching cost center reporting without forcing every balance-sheet posting into an organizational allocation.

## Posting Guardrails

The posting engine enforces these principles:

- each voucher must balance before rows are accepted
- only implemented posting events create GL rows
- opening balance rows are preserved when operational postings are appended
- ledger traceability fields are populated on operational postings

## Validation Coverage

`src/greenfield_dataset/validations.py` checks:

- voucher-level balance
- overall trial balance equality
- AR roll-forward against sales invoices and cash receipts
- AP roll-forward against purchase invoices and disbursements
- inventory roll-forward against goods receipts and shipments
- COGS agreement with shipment standard cost
- GRNI roll-forward against goods receipts and cleared purchase invoices

## Current Implementation Notes

- `PurchaseInvoice` postings use `ApprovedDate` as the posting date in the current code.
- Purchase invoice tax is treated as nonrecoverable and posted to purchase variance in the current implementation.
- The current generator does not yet call `journals.py`; recurring manual operating journals remain a future extension.
