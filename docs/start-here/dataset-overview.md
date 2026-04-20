---
title: Accounting Dataset Guide
description: Guide to the synthetic accounting database, table families, key joins, and source-to-ledger paths in the published SQLite dataset.
slug: /dataset-overview
sidebar_label: Dataset Guide
---

# Dataset Guide

<DatasetStructuredData
  pagePath="/docs/dataset-overview"
  sameAsPath="/"
  description="Guide to the synthetic accounting database, table families, key joins, and source-to-ledger paths in the published SQLite dataset."
/>

This page provides the mental model for the dataset: what is in it, how the table families fit together, which paths matter most, and how operational activity reaches `GLEntry`.

If you need field-level lookup, use [Schema Reference](../reference/schema.md). If you need business narrative, use [Company Story](../learn-the-business/company-story.md) and [Process Flows](../learn-the-business/process-flows.md).

## What the Dataset Is

<DatasetName /> models one integrated business: <CompanyName />.

It connects:

- business processes
- operational source documents
- planning and support layers
- subledger logic
- posted GLEntry records

The dataset lets you move from business activity to source documents and from source documents to ledger impact.

## What the Dataset Contains

The current implementation contains **68 tables** across eight areas:

| Area | What it covers | Count |
|---|---|---:|
| Accounting core | Chart of accounts, journals, and posted ledger detail | 3 |
| Order-to-cash | Customers, commercial pricing, orders, shipments, invoices, cash, returns, credits, and refunds | 18 |
| Procure-to-pay | Requisitions, purchase orders, receipts, supplier invoices, and disbursements | 9 |
| Manufacturing | BOMs, routings, work centers, work orders, issues, completions, and close | 14 |
| Payroll and time | Shifts, rosters, absences, overtime approvals, punches, approved daily time, payroll, and remittances | 14 |
| Master data | Item, warehouse, and employee records | 3 |
| Organizational planning | Cost centers and budgets | 2 |
| Demand planning and MRP | Forecasting, inventory policy, recommendations, MRP, and rough-cut capacity | 5 |

Most classes use these ready-to-use files:

- <FileName type="sqlite" />
- <FileName type="excel" />
- <FileName type="csv" />

Download them from [Downloads](downloads.md) or use the copies already shared for your course.

## How the Data Is Organized

The easiest way to think about the model is in layers:

| Layer | What belongs here | What it adds |
|---|---|---|
| Business master data | `Customer`, `Supplier`, `Item`, `Employee`, `Warehouse`, `CostCenter` | Defines who, what, and where |
| Planning and setup | BOMs, routings, shifts, rosters, forecasts, inventory policies | Explains what should happen before execution starts |
| Execution documents | Orders, shipments, receipts, invoices, work orders, labor records, payroll records | Shows what actually happened |
| Ledger and control | `JournalEntry`, `GLEntry`, budgets, remittances | Shows the accounting effect and reporting layer |

Many document families also use a header-line pattern:

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
| `PayrollRegister` | `PayrollRegisterLine` | One payroll register can contain many earnings and deduction lines |

## The Most Important Keys

You do not need every key on day one. Start with the keys that anchor document chains:

| Key | Use it to connect |
|---|---|
| `CustomerID` | Customer to orders, invoices, receipts, returns, credits, and refunds |
| `SalesOrderID` | Sales order header to fulfillment and billing |
| `SalesOrderLineID` | Order lines to shipment lines and invoice lines |
| `ShipmentLineID` | Shipped lines to billed lines and returned lines |
| `SupplierID` | Supplier to purchase orders, invoices, and payments |
| `PurchaseOrderID` | Purchase order header to receipts and invoices |
| `POLineID` | Purchase order lines to receipt lines and invoice lines |
| `GoodsReceiptLineID` | Inventory receipt lines to supplier invoice lines |
| `AccrualJournalEntryID` | Accrued service invoice lines back to the original accrual journal |
| `WorkOrderID` | Work-order activity across issue, completion, close, and direct labor |
| `WorkOrderOperationID` | Operation-level schedules and labor to one work-order operation |
| `EmployeeShiftRosterID` | Planned roster rows to absences, overtime approvals, punches, and approved daily time |
| `TimeClockEntryID` | Approved daily time to labor entries and attendance exceptions |
| `PayrollPeriodID` | Labor entries, payroll registers, and liability remittances to a pay period |
| `PayrollRegisterID` | Payroll header to line detail and net-pay settlement |
| `SupplyPlanRecommendationID` | Planning recommendations to requisitions, work orders, MRP rows, and rough-cut capacity rows |
| `ItemID` | Product-level analysis across sales, purchasing, manufacturing, and planning |
| `AccountID` | `GLEntry` and `Budget` to the chart of accounts |
| `CostCenterID` | Operating activity, labor, budgets, and reporting by organization unit |

For exact field-level lookup, go to [Schema Reference](../reference/schema.md).

## Core Navigation Paths

These are the fastest ways to move through the model.

### O2C path

`Customer -> SalesOrder -> SalesOrderLine -> Shipment -> ShipmentLine -> SalesInvoice -> SalesInvoiceLine`

Cash settlement is tracked through:

`CashReceipt -> CashReceiptApplication -> SalesInvoice`

Returns branch from the billed shipment path:

`SalesInvoiceLine -> SalesReturn -> SalesReturnLine -> CreditMemo -> CreditMemoLine -> CustomerRefund`

Commercial pricing is resolved before shipment and billing through:

`Customer -> PriceList -> PriceListLine -> SalesOrderLine <- PromotionProgram and PriceOverrideApproval`

### P2P path

`Supplier -> PurchaseRequisition -> PurchaseOrder -> PurchaseOrderLine -> GoodsReceipt -> GoodsReceiptLine -> PurchaseInvoice -> PurchaseInvoiceLine -> DisbursementPayment`

The accrued-service branch is:

`JournalEntry (Accrual) -> PurchaseInvoiceLine.AccrualJournalEntryID -> PurchaseInvoice -> DisbursementPayment`

### Manufacturing path

`Item -> BillOfMaterial -> BillOfMaterialLine -> WorkOrder -> WorkOrderOperation -> WorkOrderOperationSchedule -> MaterialIssue -> MaterialIssueLine -> ProductionCompletion -> ProductionCompletionLine -> WorkOrderClose`

Manufacturing also depends on:

- P2P for raw materials and packaging
- time and payroll for labor support
- O2C for finished-goods demand and shipment

### Demand-planning path

`Item -> InventoryPolicy -> DemandForecast -> SupplyPlanRecommendation -> MaterialRequirementPlan -> PurchaseRequisition or WorkOrder`

Capacity tieout is tracked through:

`SupplyPlanRecommendation -> RoughCutCapacityPlan -> WorkCenterCalendar`

### Payroll and time path

`ShiftDefinition -> EmployeeShiftAssignment -> EmployeeShiftRoster -> TimeClockPunch -> TimeClockEntry -> LaborTimeEntry -> PayrollPeriod -> PayrollRegister -> PayrollRegisterLine -> PayrollPayment`

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

to move back to the originating event.

## How Operational Activity Reaches the Ledger

The most important mental rule is simple: planning and setup tables usually do **not** post; execution and finance events often do.

| Type of activity | Usually posts to GL? | Examples |
|---|---|---|
| Master data and planning | No | `Item`, `Employee`, `Budget`, BOMs, routings, forecasts, inventory policies |
| Operational commitments | No | `SalesOrder`, `PurchaseRequisition`, `PurchaseOrder`, `WorkOrder` |
| Operational execution with accounting effect | Yes | `Shipment`, `SalesInvoice`, `GoodsReceipt`, `MaterialIssue`, `ProductionCompletion`, `PayrollRegister` |
| Settlements and clearances | Yes | `CashReceipt`, `CashReceiptApplication`, `DisbursementPayment`, `PayrollPayment`, `PayrollLiabilityRemittance`, `CustomerRefund` |
| Finance-controlled entries | Yes | `JournalEntry`, `WorkOrderClose`, accruals, reclasses, year-end close |

When you want the exact posting rules behind one event, use [GLEntry Posting Reference](../reference/posting.md).

## How to Start Navigating by Topic

### Financial accounting

Start with:

- `GLEntry`
- `Account`
- `SalesInvoice`
- `CashReceiptApplication`
- `PurchaseInvoice`
- `DisbursementPayment`
- `PayrollRegister`
- `WorkOrderClose`

### Managerial accounting

Start with:

- `Item`
- `PriceList`
- `PriceListLine`
- `PromotionProgram`
- `PriceOverrideApproval`
- `Budget`
- `CostCenter`
- `BillOfMaterial`
- `WorkOrder`
- `MaterialIssueLine`
- `ProductionCompletionLine`
- `LaborTimeEntry`
- `DemandForecast`
- `SupplyPlanRecommendation`

### Auditing and controls

Start with:

- O2C chain tables
- P2P chain tables
- manufacturing chain tables
- payroll and time chain tables
- GLEntry
- the transaction chains in [Process Flows](../learn-the-business/process-flows.md)

## Practical Starting Tips

- `CashReceiptApplication` is the authoritative invoice-settlement link in O2C.
- For P2P traceability, start with `PurchaseOrderLine.RequisitionID`, `PurchaseInvoiceLine.GoodsReceiptLineID`, and `PurchaseInvoiceLine.AccrualJournalEntryID`.
- For manufacturing, start from `WorkOrderID` and then move outward to issues, completions, close, and labor.
- For time and attendance, start from `EmployeeShiftRosterID`, `TimeClockEntryID`, or `ShiftDefinitionID`.
- For payroll, start from `PayrollPeriodID` or `PayrollRegisterID` and then move back to `LaborTimeEntry` and `TimeClockEntry`.
- For raw multi-year income-statement analysis, exclude the year-end close entry types.

## Glossary

| Term | Plain-language meaning |
|---|---|
| O2C | Order-to-cash. The sales cycle from customer order through billing, cash application, and possible return activity. |
| P2P | Procure-to-pay. The purchasing cycle from requisition through supplier payment. |
| BOM | Bill of material. The standard list of components required to make a manufactured item. |
| WIP | Work in process. Inventory value that has been issued into production but not yet completed into finished goods. |
| GL | General ledger. The accounting table used for reporting and control-account reconciliation. |
| GRNI | Goods received not invoiced. A liability recorded when inventory is received before the supplier invoice is approved. |
| Control account | A GL account such as AR, AP, inventory, GRNI, customer deposits, WIP, or manufacturing clearing that summarizes detailed activity. |
| Manufacturing variance | The difference between actual and standard manufacturing cost that is closed from work orders. |
| Contribution margin | Revenue less variable product cost. In this dataset, fixed overhead is excluded from contribution-margin analysis. |

## Next Steps

- Read [Schema Reference](../reference/schema.md) for table-level lookup and high-value fields.
- Read [Process Flows](../learn-the-business/process-flows.md) for the business-cycle reading path.
- Read [GLEntry Posting Reference](../reference/posting.md) when you need event-to-ledger rules.
- Read [Analytics Guides](../analytics/index.md) when you are ready to move into the analysis layer.
