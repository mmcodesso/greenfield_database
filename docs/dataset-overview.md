---
title: Dataset Guide
description: Student-friendly guide to what the Greenfield dataset contains and how to navigate it.
slug: /dataset-overview
sidebar_label: Dataset Guide
---

# Dataset Guide

**Audience:** Students, instructors, and analysts who want one clear guide to what the dataset is and how to use it.  
**Purpose:** Combine the former overview and database-navigation material into one student-facing reference.  
**What you will learn:** What the dataset covers, how the tables are organized, which keys matter most, and how to move from business activity to accounting analysis.

## What This Project Is

Greenfield Accounting Dataset is a teachable business database for **Greenfield Home Furnishings, Inc.**

It connects:

- business processes
- operational source documents
- subledger logic
- posted `GLEntry` records

The dataset is built for:

- SQL exercises
- Excel analysis
- financial accounting analytics
- managerial accounting analytics
- auditing and controls analytics
- document tracing and business-process understanding

## Business Context

Greenfield is a hybrid manufacturer-distributor with two warehouses and one manufacturing cost center.

The current dataset models a company that:

- sells finished goods to customers
- buys finished goods, raw materials, and packaging from suppliers
- manufactures selected finished goods internally
- ships, invoices, collects cash, processes returns, and issues credit memos and refunds
- assigns shifts, records approved daily time clocks for hourly employees, and runs payroll
- records recurring journals, manufacturing reclasses, and year-end close

Read [company-story.md](company-story.md) for the full narrative version of that operating model.

## What the Dataset Contains

The current implementation contains **55 tables** across seven areas:

| Area | Example tables | Count |
|---|---|---:|
| Accounting core | `Account`, `JournalEntry`, `GLEntry` | 3 |
| Order-to-cash | `Customer`, `SalesOrder`, `Shipment`, `SalesInvoice`, `CashReceiptApplication`, `SalesReturn`, `CreditMemo`, `CustomerRefund` | 14 |
| Procure-to-pay | `Supplier`, `PurchaseRequisition`, `PurchaseOrder`, `GoodsReceipt`, `PurchaseInvoice`, `DisbursementPayment` | 9 |
| Manufacturing | `BillOfMaterial`, `BillOfMaterialLine`, `WorkCenter`, `WorkCenterCalendar`, `Routing`, `RoutingOperation`, `WorkOrder`, `WorkOrderOperation`, `WorkOrderOperationSchedule`, `MaterialIssue`, `ProductionCompletion`, `WorkOrderClose` | 14 |
| Payroll and time | `ShiftDefinition`, `EmployeeShiftAssignment`, `TimeClockEntry`, `AttendanceException`, `PayrollPeriod`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollPayment`, `PayrollLiabilityRemittance` | 10 |
| Master data | `Item`, `Warehouse`, `Employee` | 3 |
| Organizational planning | `CostCenter`, `Budget` | 2 |

Most classes use these teaching-package files:

- `greenfield_2026_2030.sqlite`
- `greenfield_2026_2030.xlsx`
- `validation_report.json`
- `generation.log`

## How the Database Is Organized

Many business documents use a header table and a line table.

| Header table | Line table | Meaning |
|---|---|---|
| `SalesOrder` | `SalesOrderLine` | One customer order can contain many item lines |
| `Shipment` | `ShipmentLine` | One shipment can contain many shipped lines |
| `SalesInvoice` | `SalesInvoiceLine` | One invoice can contain many billed lines |
| `PurchaseOrder` | `PurchaseOrderLine` | One PO can contain many ordered lines |
| `GoodsReceipt` | `GoodsReceiptLine` | One receipt can contain many received lines |
| `PurchaseInvoice` | `PurchaseInvoiceLine` | One supplier invoice can contain many billed lines |
| `MaterialIssue` | `MaterialIssueLine` | One material issue can contain many component lines |
| `ProductionCompletion` | `ProductionCompletionLine` | One production completion can contain one or more completion lines |
| `PayrollRegister` | `PayrollRegisterLine` | One employee payroll register can contain many earnings and deduction lines |

## Most Important Keys

| Key | Use |
|---|---|
| `CustomerID` | Connect customers to orders, invoices, receipts, returns, credit memos, and refunds |
| `SupplierID` | Connect suppliers to purchase orders, invoices, and payments |
| `SalesOrderID` | Connect sales order header to shipments and invoices |
| `SalesOrderLineID` | Connect order lines to shipment lines and sales invoice lines |
| `ShipmentLineID` | Connect billed and returned lines to the exact shipped line |
| `RequisitionID` | Connect requisitions to purchase-order headers and purchase-order lines |
| `PurchaseOrderID` | Connect purchase order header to goods receipts and purchase invoices |
| `POLineID` | Connect purchase order lines to goods receipt lines and purchase invoice lines |
| `GoodsReceiptLineID` | Connect inventory purchase invoice lines to exact receipt lines |
| `AccrualJournalEntryID` | Connect accrued-service purchase invoice lines to the source accrual journal |
| `BOMID` | Connect manufactured items to their BOM headers |
| `BOMLineID` | Connect component issues back to BOM detail |
| `WorkOrderID` | Connect work-order activity across issue, completion, close, and direct labor |
| `WorkOrderOperationID` | Connect operation-level schedules and direct labor to one work-order operation |
| `ShiftDefinitionID` | Connect shift templates to employee assignments and time-clock rows |
| `TimeClockEntryID` | Connect approved time-clock support to labor allocation and attendance exceptions |
| `PayrollPeriodID` | Connect labor time, payroll registers, and liability remittances to a pay period |
| `PayrollRegisterID` | Connect payroll headers to line detail and payroll payments |
| `ItemID` | Analyze quantities, prices, standard costs, supply mode, and account mappings |
| `AccountID` | Connect `GLEntry` and `Budget` to the chart of accounts |
| `CostCenterID` | Connect operational activity, employees, payroll, and budgets to organizational reporting |

## Core Navigation Paths

### O2C path

`Customer -> SalesOrder -> SalesOrderLine -> Shipment -> ShipmentLine -> SalesInvoice -> SalesInvoiceLine`

Cash collection is tracked through:

`CashReceipt -> CashReceiptApplication -> SalesInvoice`

Returns, credits, and refunds branch from the billed shipment path:

`SalesInvoiceLine -> SalesReturn -> SalesReturnLine -> CreditMemo -> CreditMemoLine -> CustomerRefund`

### P2P path

`Supplier -> PurchaseRequisition -> PurchaseOrder -> PurchaseOrderLine -> GoodsReceipt -> GoodsReceiptLine -> PurchaseInvoice -> PurchaseInvoiceLine -> DisbursementPayment`

There is also a direct service-settlement branch:

`JournalEntry (Accrual) -> PurchaseInvoiceLine.AccrualJournalEntryID -> PurchaseInvoice -> DisbursementPayment`

### Manufacturing path

`Item -> BillOfMaterial -> BillOfMaterialLine -> WorkOrder -> WorkOrderOperation -> WorkOrderOperationSchedule -> MaterialIssue -> MaterialIssueLine -> ProductionCompletion -> ProductionCompletionLine -> WorkOrderClose`

Manufacturing also touches P2P, payroll, and O2C:

- P2P replenishes raw materials and packaging
- payroll provides direct labor and manufacturing-overhead inputs
- O2C consumes completed finished goods

### Payroll path

`ShiftDefinition -> EmployeeShiftAssignment -> TimeClockEntry -> LaborTimeEntry -> PayrollPeriod -> PayrollRegister -> PayrollRegisterLine -> PayrollPayment`

Liability clearance is tracked through:

`PayrollPeriod -> PayrollLiabilityRemittance`

### Ledger path

`GLEntry -> Account`

Then use:

- `SourceDocumentType`
- `SourceDocumentID`
- `SourceLineID`
- `VoucherType`
- `VoucherNumber`

to move back to the originating transaction.

## How to Move From Operations to Accounting

Not every operational document posts to the general ledger.

| Document family | Posts to GL? | Notes |
|---|---|---|
| Sales orders | No | Operational demand document |
| Purchase requisitions | No | Internal approval document |
| Purchase orders | No | External commitment document |
| Bills of material | No | Standard manufacturing structure |
| Work orders | No | Production planning document |
| Shift definitions and assignments | No | Workforce planning metadata |
| Time-clock entries | No | Approved daily attendance rows that support hourly payroll and labor analysis |
| Attendance exceptions | No | Control and anomaly evidence |
| Labor time entries | No | Operational labor detail that feeds payroll and costing |
| Payroll periods | No | Calendar and control structure |
| Shipments | Yes | Posts COGS and inventory relief |
| Sales invoices | Yes | Posts AR, revenue, and sales tax |
| Cash receipts | Yes | Posts cash and customer deposits or unapplied cash |
| Cash receipt applications | Yes | Clears AR from customer deposits or unapplied cash |
| Sales returns | Yes | Posts inventory back in and reverses COGS |
| Credit memos | Yes | Posts contra revenue, tax reversal, and AR or customer credit reduction |
| Customer refunds | Yes | Posts customer credit and cash |
| Goods receipts | Yes | Posts inventory and GRNI |
| Material issues | Yes | Posts WIP and materials inventory |
| Production completions | Yes | Posts finished goods, WIP, and manufacturing clearing |
| Work-order close | Yes | Posts manufacturing variance |
| Payroll registers | Yes | Posts wages and payroll liabilities |
| Payroll payments | Yes | Posts accrued payroll and cash |
| Payroll liability remittances | Yes | Posts payroll liabilities and cash |
| Purchase invoices | Yes | Posts GRNI clearing for receipt-matched lines, or clears `2040` for accrued-service lines, then posts AP |
| Disbursements | Yes | Posts AP and cash |
| Journal entries | Yes | Opening, recurring manual, manufacturing reclass, reversal, and year-end close journals |

## What Students Can Do With It

### Financial accounting

Students can:

- analyze revenue, COGS, contra revenue, and close-cycle activity
- reconcile AR using invoices, cash applications, credit memos, and refunds
- reconcile AP using purchase invoices and disbursements
- review WIP, manufacturing clearing, and manufacturing variance balances
- review payroll liabilities, gross-to-net payroll, time-clock-to-payroll support, and payroll cash flows
- trace source transactions into `GLEntry`

### Managerial accounting

Students can:

- compare budget to actual by cost center and account
- analyze sales mix by product, customer, region, and segment
- study warehouse movement and supplier concentration
- roll up BOM-based standard costs
- analyze work-order throughput, completions, production variance, and direct labor cost
- compare absorption cost and contribution margin for manufactured versus purchased items

### Auditing

Students can:

- test O2C, P2P, and manufacturing document chains
- test payroll approvals, time-clock support, time-entry linkage, and payroll-control behavior
- review approvals and segregation-of-duties patterns
- examine timing and cut-off behavior
- detect duplicate references and planted anomalies
- trace source documents to posted ledger activity

## Start Here by Analytics Topic

### Financial analytics

Start with:

- `GLEntry`
- `Account`
- `SalesInvoice`
- `CashReceiptApplication`
- `CreditMemo`
- `PurchaseInvoice`
- `DisbursementPayment`
- `PayrollRegister`
- `PayrollLiabilityRemittance`
- `WorkOrderClose`

### Managerial analytics

Start with:

- `Budget`
- `CostCenter`
- `Item`
- `BillOfMaterial`
- `WorkOrder`
- `MaterialIssueLine`
- `ProductionCompletionLine`
- `LaborTimeEntry`
- `ShipmentLine`
- `PurchaseOrderLine`

### Audit analytics

Start with:

- O2C chain tables
- P2P chain tables
- manufacturing chain tables
- payroll chain tables
- `GLEntry`
- `validation_report.json`
- the anomaly log in Excel

## Current Practical Tips

- The SQLite database is the easiest format for SQL work.
- `CashReceiptApplication` is the authoritative invoice-settlement link in O2C.
- For P2P traceability, prefer `PurchaseOrderLine.RequisitionID`, `PurchaseInvoiceLine.GoodsReceiptLineID`, and `PurchaseInvoiceLine.AccrualJournalEntryID`.
- For manufacturing traceability, start from `WorkOrderID`.
- For time-and-attendance traceability, start from `TimeClockEntryID` or `ShiftDefinitionID`.
- For payroll traceability, start from `PayrollPeriodID`, `PayrollRegisterID`, and then move back to `LaborTimeEntry` and `TimeClockEntry` for hourly earnings support.
- For raw multi-year income-statement analysis, exclude the two year-end close entry types.

## What Is Not in Scope Yet

The current model does **not** yet include:

- raw punch-event tables beneath the current approved daily time-clock rows
- rotating shift rosters or shift-level capacity calendars
- multi-level BOMs or subassemblies

Those topics are future roadmap items, not hidden functionality.

## Glossary

| Term | Plain-language meaning |
|---|---|
| O2C | Order-to-cash. The sales cycle from customer order through billing, cash application, and possible return activity. |
| P2P | Procure-to-pay. The purchasing cycle from requisition through supplier payment. |
| BOM | Bill of material. The standard list of components required to make a manufactured item. |
| WIP | Work in process. Inventory value that has been issued into production but not yet completed into finished goods. |
| GL | General ledger. The accounting table used for reporting and control-account reconciliation. |
| Control account | A GL account such as AR, AP, inventory, GRNI, customer deposits, WIP, or manufacturing clearing that summarizes detailed activity. |
| GRNI | Goods Received Not Invoiced. A liability recorded when inventory is received before the supplier invoice is approved. |
| Manufacturing variance | The difference between actual and standard manufacturing cost that is closed from work orders. |
| Absorption cost | Full product cost including direct material, direct labor, variable overhead, and fixed overhead. |
| Contribution margin | Revenue less variable product cost. In this dataset, fixed overhead is excluded from contribution-margin analysis. |
| Cost center | An organizational unit used for planning and performance analysis. |
| Anomaly | A deliberately planted exception or unusual pattern for analytics and audit exercises. |

## Where to Go Next

- Read [company-story.md](company-story.md) for the business narrative.
- Read [process-flows.md](process-flows.md) for O2C, P2P, manufacturing, journals, and ledger traceability.
- Read [analytics/index.md](analytics/index.md) for the starter analytics layer.
