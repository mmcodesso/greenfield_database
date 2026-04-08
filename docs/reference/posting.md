# Posting Reference

**Audience:** Contributors, advanced students, and instructors who need the implemented accounting logic in technical form.  
**Purpose:** Document the event-based posting rules used by the current generator.  
**What you will learn:** Which documents post, which accounts are affected, and how postings are traced back to source transactions.

Posting logic is implemented across `src/greenfield_dataset/budgets.py`, `src/greenfield_dataset/journals.py`, and `src/greenfield_dataset/posting_engine.py`.

> **Implemented in current generator:** Event-based postings for shipments, sales invoices, cash receipts, goods receipts, purchase invoices, and disbursements, plus opening, recurring manual, reversal, and year-end close journals.

> **Planned future extension:** Future manufacturing-related posting events.

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
| Payroll accrual | `JournalEntry` plus seeded GL rows from `journals.py` | Last calendar day of month | Salary expense by cost center and `6060` Payroll Taxes and Benefits | `2030` Accrued Payroll |
| Payroll settlement | `JournalEntry` plus seeded GL rows from `journals.py` | First business day of following month | `2030` Accrued Payroll | `1010` Cash and Cash Equivalents |
| Rent | `JournalEntry` plus seeded GL rows from `journals.py` | First business day of month | `6070` Warehouse Rent or `6080` Office Rent | `1010` Cash and Cash Equivalents |
| Utilities | `JournalEntry` plus seeded GL rows from `journals.py` | Last business day of month | `6090` Utilities Expense | `1010` Cash and Cash Equivalents |
| Depreciation | `JournalEntry` plus seeded GL rows from `journals.py` | Last calendar day of month | `6130` Depreciation Expense | `1150`, `1160`, or `1170` accumulated depreciation |
| Month-end accrual | `JournalEntry` plus seeded GL rows from `journals.py` | Last business day of month | `6100`, `6140`, and `6180` operating expenses | `2040` Accrued Expenses |
| Accrual reversal | `JournalEntry` plus seeded GL rows from `journals.py` | First business day of following month | Reverse prior accrual liability and expense lines | Reverse prior accrual liability and expense lines |
| Shipment | `Shipment`, `ShipmentLine` | `ShipmentDate` | Item COGS account | Item inventory account |
| Sales invoice | `SalesInvoice`, `SalesInvoiceLine` | `InvoiceDate` | Accounts receivable | Item revenue account and sales tax payable |
| Cash receipt | `CashReceipt` | `ReceiptDate` | Cash | Accounts receivable |
| Goods receipt | `GoodsReceipt`, `GoodsReceiptLine` | `ReceiptDate` | Item inventory account using receipt-line posting basis | Goods Received Not Invoiced |
| Purchase invoice | `PurchaseInvoice`, `PurchaseInvoiceLine` | `ApprovedDate` | GRNI cleared at matched receipt-line basis, purchase variance when needed, and nonrecoverable tax to variance | Accounts payable and purchase variance when needed |
| Disbursement | `DisbursementPayment` | `PaymentDate` | Accounts payable | Cash |
| Year-end close: P&L to income summary | `JournalEntry` plus seeded GL rows from `journals.py` | `YYYY-12-31` | Revenue or expense balances needed to close annual P&L accounts | Offset to `8010` Income Summary |
| Year-end close: income summary to retained earnings | `JournalEntry` plus seeded GL rows from `journals.py` | `YYYY-12-31` | `8010` Income Summary for profitable years or `3030` Retained Earnings for loss years | `3030` Retained Earnings for profitable years or `8010` Income Summary for loss years |

## Core Control Accounts

| Account number | Meaning |
|---|---|
| `1010` | Cash and cash equivalents |
| `1020` | Accounts receivable |
| `1040` | Inventory - finished goods |
| `1045` | Inventory - materials and packaging |
| `2010` | Accounts payable |
| `2020` | Goods Received Not Invoiced |
| `2030` | Accrued payroll |
| `2040` | Accrued expenses |
| `2050` | Sales tax payable |
| `3030` | Retained earnings |
| `5060` | Purchase price variance |
| `8010` | Income summary |

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
- goods receipt postings inherit `CostCenterID` from the originating requisition through `PurchaseOrderLine.RequisitionID` when available
- purchase invoice postings inherit `CostCenterID` from the matched receipt or purchase-order line when available
- disbursements inherit a cost center only when the related purchase invoice resolves cleanly to one cost center
- some control-account rows still remain at `CostCenterID = null`

This is sufficient for teaching cost center reporting without forcing every balance-sheet posting into an organizational allocation.

## Posting Guardrails

The posting engine enforces these principles:

- each voucher must balance before rows are accepted
- only implemented posting events create GL rows
- opening balance and manual journal rows are preserved when operational postings are appended
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
- journal header-to-GL agreement
- accrual reversal linkage and timing
- year-end close completeness and annual P&L closure

## Current Implementation Notes

- `PurchaseInvoice` postings use `ApprovedDate` as the posting date in the current code.
- Clean P2P matching uses `PurchaseInvoiceLine.GoodsReceiptLineID` first and falls back to `POLineID` only for legacy or exceptional rows.
- Purchase invoice tax is treated as nonrecoverable and posted to purchase variance in the current implementation.
- Year-end close entries are real posted journals in every fiscal year of the default range.
- For raw multi-year income statement analytics, exclude `Year-End Close - P&L to Income Summary` and `Year-End Close - Income Summary to Retained Earnings`.
