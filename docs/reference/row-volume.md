# Row Volume Reference

**Audience:** Contributors, instructors, and advanced users who need current scale expectations for the dataset.  
**Purpose:** Compare the design-intent row ranges with the current deterministic default build.  
**What you will learn:** Which tables are already at target scale, which ones are still intentionally light, and why.

The default configuration uses:

- `config/settings.yaml`
- fiscal years `2026-01-01` through `2030-12-31`
- random seed `20260401`

> **Implemented in current generator:** A deterministic five-year dataset whose default counts are stable unless configuration or generation logic changes.

> **Planned future extension:** More recurring journal activity, more complex P2P line structures, and future manufacturing tables that would materially increase total row count.

## Current Default Build vs Design Intent

The target ranges below come from `Design.md` and represent design intent, not hard validation thresholds.

| Group | Table | Target rows | Current default rows |
|---|---|---:|---:|
| Accounting core | Account | 75 to 95 | 87 |
| Accounting core | JournalEntry | 900 to 1,500 | 1 |
| Accounting core | GLEntry | 60,000 to 110,000 | 106,355 |
| O2C | Customer | 150 to 300 | 220 |
| O2C | SalesOrder | 4,500 to 9,000 | 6,950 |
| O2C | SalesOrderLine | 13,000 to 30,000 | 24,150 |
| O2C | Shipment | 4,200 to 8,500 | 6,352 |
| O2C | ShipmentLine | 12,000 to 28,000 | 21,186 |
| O2C | SalesInvoice | 4,200 to 8,500 | 6,332 |
| O2C | SalesInvoiceLine | 12,000 to 28,000 | 21,115 |
| O2C | CashReceipt | 4,000 to 9,500 | 5,347 |
| P2P | Supplier | 80 to 160 | 110 |
| P2P | PurchaseRequisition | 2,500 to 6,000 | 4,155 |
| P2P | PurchaseOrder | 2,200 to 5,500 | 3,910 |
| P2P | PurchaseOrderLine | 7,000 to 18,000 | 3,910 |
| P2P | GoodsReceipt | 2,100 to 5,000 | 3,112 |
| P2P | GoodsReceiptLine | 6,500 to 17,000 | 3,112 |
| P2P | PurchaseInvoice | 2,100 to 5,000 | 2,768 |
| P2P | PurchaseInvoiceLine | 6,500 to 17,000 | 2,768 |
| P2P | DisbursementPayment | 2,300 to 5,500 | 2,210 |
| Master data | Item | 180 to 350 | 240 |
| Master data | Warehouse | 2 to 3 | 2 |
| Master data | Employee | 55 to 75 | 64 |
| Organizational planning | CostCenter | 8 to 14 | 8 |
| Organizational planning | Budget | 2,000 to 4,500 | 2,940 |

## What Is Already at Useful Teaching Scale

- O2C tables are already large enough for trend, concentration, cut-off, and margin exercises.
- `GLEntry` is already at the top of the current design range and supports meaningful ledger analytics.
- Budget, customer, supplier, item, employee, and cost center tables are all at reasonable teaching scale.

## Where the Current Build Is Still Intentionally Light

- `JournalEntry` is far below the historical target because the generator currently creates only the opening balance journal header.
- P2P line tables are below the original target because the current implementation mostly uses one-line purchase orders, goods receipts, and purchase invoices.
- No manufacturing tables exist yet, so total dataset size is smaller than a future expanded version would be.

## How to Read These Counts

- Treat the current default counts as the best guide for classroom planning.
- Treat the target ranges as roadmap guidance for future expansion.
- Expect counts to change if you alter settings, row-volume rules, anomaly behavior, or future extensions.
