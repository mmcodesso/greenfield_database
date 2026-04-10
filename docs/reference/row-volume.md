# Row Volume Reference

**Audience:** Contributors, instructors, and advanced users who need current scale expectations for the dataset.  
**Purpose:** Compare historical design-intent row ranges with the current deterministic default build.  
**What you will learn:** Which tables are already at useful teaching scale, which ones now exceed the original design bands, and how payroll and manufacturing changed total volume.

The default configuration uses:

- `config/settings.yaml`
- fiscal years `2026-01-01` through `2030-12-31`
- random seed `20260401`

> **Implemented in current generator:** A deterministic five-year hybrid manufacturer-distributor dataset with payroll, manufacturing, and posted-ledger detail whose default counts are stable unless configuration or generation logic changes.

> **Planned future extension:** Capacity planning, scheduling, and additional scenario packs that may increase operational and ledger volume further.

## Current Default Build vs Historical Design Intent

The target ranges below come from the project's earlier design-planning model. They are useful context, not strict quality thresholds.

| Group | Table | Target rows | Current default rows |
|---|---|---:|---:|
| Accounting core | Account | 75 to 95 | 98 |
| Accounting core | JournalEntry | 900 to 1,500 | 736 |
| Accounting core | GLEntry | 60,000 to 110,000 | 643,141 |
| O2C | Customer | 150 to 300 | 220 |
| O2C | SalesOrder | 4,500 to 9,000 | 6,916 |
| O2C | SalesOrderLine | 13,000 to 30,000 | 26,795 |
| O2C | Shipment | 4,200 to 8,500 | 23,440 |
| O2C | ShipmentLine | 12,000 to 28,000 | 32,942 |
| O2C | SalesInvoice | 4,200 to 8,500 | 30,008 |
| O2C | SalesInvoiceLine | 12,000 to 28,000 | 32,895 |
| O2C | CashReceipt | 4,000 to 9,500 | 9,271 |
| O2C | CashReceiptApplication | Not specified in original design | 18,106 |
| O2C | SalesReturn | Not specified in original design | 922 |
| O2C | SalesReturnLine | Not specified in original design | 929 |
| O2C | CreditMemo | Not specified in original design | 922 |
| O2C | CreditMemoLine | Not specified in original design | 929 |
| O2C | CustomerRefund | Not specified in original design | 56 |
| P2P | Supplier | 80 to 160 | 110 |
| P2P | PurchaseRequisition | 2,500 to 6,000 | 15,023 |
| P2P | PurchaseOrder | 2,200 to 5,500 | 12,133 |
| P2P | PurchaseOrderLine | 7,000 to 18,000 | 14,787 |
| P2P | GoodsReceipt | 2,100 to 5,000 | 24,355 |
| P2P | GoodsReceiptLine | 6,500 to 17,000 | 24,512 |
| P2P | PurchaseInvoice | 2,100 to 5,000 | 34,015 |
| P2P | PurchaseInvoiceLine | 6,500 to 17,000 | 34,388 |
| P2P | DisbursementPayment | 2,300 to 5,500 | 35,784 |
| Manufacturing | BillOfMaterial | Not specified in original design | 77 |
| Manufacturing | BillOfMaterialLine | Not specified in original design | 281 |
| Manufacturing | WorkCenter | Not specified in original design | 5 |
| Manufacturing | Routing | Not specified in original design | 77 |
| Manufacturing | RoutingOperation | Not specified in original design | 291 |
| Manufacturing | WorkOrder | Not specified in original design | 3,981 |
| Manufacturing | WorkOrderOperation | Not specified in original design | 15,183 |
| Manufacturing | MaterialIssue | Not specified in original design | 7,132 |
| Manufacturing | MaterialIssueLine | Not specified in original design | 26,314 |
| Manufacturing | ProductionCompletion | Not specified in original design | 6,980 |
| Manufacturing | ProductionCompletionLine | Not specified in original design | 6,980 |
| Manufacturing | WorkOrderClose | Not specified in original design | 2,943 |
| Payroll | PayrollPeriod | Not specified in original design | 131 |
| Payroll | LaborTimeEntry | Not specified in original design | 32,935 |
| Payroll | PayrollRegister | Not specified in original design | 8,320 |
| Payroll | PayrollRegisterLine | Not specified in original design | 74,145 |
| Payroll | PayrollPayment | Not specified in original design | 8,320 |
| Payroll | PayrollLiabilityRemittance | Not specified in original design | 387 |
| Master data | Item | 180 to 350 | 243 |
| Master data | Warehouse | 2 to 3 | 2 |
| Master data | Employee | 55 to 75 | 64 |
| Organizational planning | CostCenter | 8 to 14 | 9 |
| Organizational planning | Budget | 2,000 to 4,500 | 3,300 |

## What Changed in Phase 13

Phase 13 materially changed total row volume through:

- payroll periods and employee-level payroll registers
- payroll register lines for gross pay, withholdings, taxes, and benefits
- payroll payments and payroll liability remittances
- labor-time detail tied to work orders
- larger ledger volume from payroll postings
- lower recurring-journal counts because clean-build payroll is no longer simulated through payroll accrual and payroll settlement journals

## What Changed in Phase 14

Phase 14 added a planning and execution layer inside manufacturing without changing standard-cost valuation:

- `WorkCenter`, `Routing`, and `RoutingOperation` rows for manufactured items
- `WorkOrderOperation` rows at release time for each work order
- substantially more `LaborTimeEntry` rows because direct labor is now assigned at the operation level
- higher `PayrollRegisterLine` and `GLEntry` volumes because the routing-aware labor layer increased payroll and downstream posting detail

## What Changed in the Accrued-Expense Rework

The accrued-expense settlement rework changed row volume in a narrower but important way:

- `Accrual Reversal` journals were removed from the clean build
- monthly accruals now generate three separate accrual journals, one for each expense family
- a small number of `Accrual Adjustment` journals remain for rare cleanup activity
- direct service `PurchaseInvoice` and `DisbursementPayment` rows now clear most accrued expenses operationally

## How to Read These Counts

- Treat the current default counts as the best guide for classroom planning.
- Treat the target ranges as historical design guidance, not strict quality thresholds.
- Expect counts to change if you alter settings, anomaly behavior, or later phases.
- The historical journal-entry target assumed journal-mode payroll. Phase 13 moved payroll into operational tables, so `JournalEntry` is now lower while payroll tables and `GLEntry` are materially higher.
- Phase 14 added routing and operation tables plus denser labor detail, so manufacturing-planning and payroll row counts are materially above the earlier manufacturing-foundation baseline.
