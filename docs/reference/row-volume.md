# Row Volume Reference

**Audience:** Contributors, instructors, and advanced users who need current scale expectations for the dataset.  
**Purpose:** Compare the design-intent row ranges with the current deterministic default build.  
**What you will learn:** Which tables are already at target scale, which ones are still intentionally light, and why.

The default configuration uses:

- `config/settings.yaml`
- fiscal years `2026-01-01` through `2030-12-31`
- random seed `20260401`

> **Implemented in current generator:** A deterministic five-year dataset whose default counts are stable unless configuration or generation logic changes.

> **Planned future extension:** Manufacturing tables that would further change total row count.

## Current Default Build vs Design Intent

The target ranges below come from the project's earlier design-planning model and represent historical design intent, not hard validation thresholds.

| Group | Table | Target rows | Current default rows |
|---|---|---:|---:|
| Accounting core | Account | 75 to 95 | 90 |
| Accounting core | JournalEntry | 900 to 1,500 | 1,442 |
| Accounting core | GLEntry | 60,000 to 110,000 | 469,567 |
| O2C | Customer | 150 to 300 | 220 |
| O2C | SalesOrder | 4,500 to 9,000 | 6,903 |
| O2C | SalesOrderLine | 13,000 to 30,000 | 27,637 |
| O2C | Shipment | 4,200 to 8,500 | 25,606 |
| O2C | ShipmentLine | 12,000 to 28,000 | 36,427 |
| O2C | SalesInvoice | 4,200 to 8,500 | 33,089 |
| O2C | SalesInvoiceLine | 12,000 to 28,000 | 36,329 |
| O2C | CashReceipt | 4,000 to 9,500 | 9,113 |
| O2C | CashReceiptApplication | Not specified in original design | 17,950 |
| O2C | SalesReturn | Not specified in original design | 24,813 |
| O2C | SalesReturnLine | Not specified in original design | 24,864 |
| O2C | CreditMemo | Not specified in original design | 24,813 |
| O2C | CreditMemoLine | Not specified in original design | 24,864 |
| O2C | CustomerRefund | Not specified in original design | 13,197 |
| P2P | Supplier | 80 to 160 | 110 |
| P2P | PurchaseRequisition | 2,500 to 6,000 | 5,743 |
| P2P | PurchaseOrder | 2,200 to 5,500 | 5,384 |
| P2P | PurchaseOrderLine | 7,000 to 18,000 | 5,507 |
| P2P | GoodsReceipt | 2,100 to 5,000 | 8,992 |
| P2P | GoodsReceiptLine | 6,500 to 17,000 | 9,006 |
| P2P | PurchaseInvoice | 2,100 to 5,000 | 12,440 |
| P2P | PurchaseInvoiceLine | 6,500 to 17,000 | 12,495 |
| P2P | DisbursementPayment | 2,300 to 5,500 | 13,833 |
| Master data | Item | 180 to 350 | 240 |
| Master data | Warehouse | 2 to 3 | 2 |
| Master data | Employee | 55 to 75 | 64 |
| Organizational planning | CostCenter | 8 to 14 | 8 |
| Organizational planning | Budget | 2,000 to 4,500 | 2,940 |

## What Is Already at Useful Teaching Scale

- O2C tables are already large enough for trend, concentration, cut-off, and margin exercises.
- `GLEntry` is now well above the original design range and supports substantial ledger analytics.
- Phase 11 made O2C much denser because shipments, invoices, receipts, returns, credits, and refunds now flow across periods instead of staying close to a one-pass monthly cycle.
- Budget, customer, supplier, item, employee, and cost center tables are all at reasonable teaching scale.
- `JournalEntry` is now inside the intended design range because the generator includes recurring manual journals and year-end close entries.
- `GoodsReceiptLine` and `PurchaseInvoiceLine` are now inside their original design-intent bands after Phase 9.

## Where the Current Build Is Still Intentionally Light

- `PurchaseOrderLine` is still below its original target band even after batched PO generation.
- `GLEntry`, `Shipment`, `SalesInvoice`, `SalesReturn`, `CreditMemo`, `CustomerRefund`, `GoodsReceipt`, `PurchaseInvoice`, and `DisbursementPayment` now exceed the historical design bands or original scope because Phases 9 through 11 intentionally introduced multi-period matching, partial settlement, and returns/refund flows.
- No manufacturing tables exist yet, so total dataset size is smaller than a future expanded version would be.

## How to Read These Counts

- Treat the current default counts as the best guide for classroom planning.
- Treat the target ranges as historical design guidance, not strict quality thresholds.
- Expect counts to change if you alter settings, row-volume rules, anomaly behavior, or future extensions.
