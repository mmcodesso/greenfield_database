---
title: Excel Guide
description: How to use the published Excel workbooks for student and classroom analysis.
sidebar_label: Excel Guide
---

# Excel Starter Guide

## Workbook Setup

The dataset workbook contains one worksheet for each dataset table. Each worksheet is already exported as a formatted Excel Table with filters and a frozen header row.

## Recommended Excel Setup

The recommended workflow is to treat the published workbook as a source file, not as the place where you build every exercise.

For each new exercise:

1. create a new blank worksheet in your working Excel file
2. use `Data -> Get Data -> From File -> From Workbook`
3. select <FileName type="excel" />
4. import only the tables required for that exercise through Power Query
5. load those tables into the current workbook
6. build pivots, formulas, charts, or summary tabs from the imported tables

This approach keeps each exercise cleaner, reduces workbook clutter, and makes it easier to control row counts, joins, and refresh steps.

## Recommended Workflow Pattern

For most classes, use this sequence:

1. run the starter SQL file first when a matching SQL path exists
2. identify the few tables needed for the Excel version of the exercise
3. import only those tables with `Get Data` and Power Query
4. recreate the same idea in Excel
5. compare the workbook output to the SQL result
6. use the case doc for interpretation questions

## Power Query Import Pattern

Use Power Query as the default import path for Excel analysis.

It works well because it lets you:

- bring in only the tables required for one exercise
- keep the original published workbook unchanged
- filter or reshape data before loading it into the workbook
- refresh the imported tables if the source file changes

For most student work, import a small set of related tables instead of loading the full dataset workbook into the exercise file.

Typical examples:

- financial exercise: `GLEntry`, `Account`, `SalesInvoice`, `CashReceiptApplication`
- managerial exercise: `Item`, `SalesInvoiceLine`, `Employee`, `CostCenter`
- audit exercise: `Employee`, `PurchaseOrder`, `JournalEntry`, `TimeClockEntry`

## Financial Workflows

### Working capital and cash conversion

Use:

- `GLEntry`
- `Account`
- `SalesInvoice`
- `CashReceiptApplication`
- `PurchaseInvoice`
- `DisbursementPayment`
- `PayrollRegister`
- `PayrollLiabilityRemittance`

Suggested outputs:

- month-end working-capital bridge
- invoice-to-application timing
- invoice-to-payment timing
- receipt-to-payment timing

Best paired case:

- [Working Capital and Cash Conversion Case](cases/working-capital-and-cash-conversion-case.md)

### Financial-statement bridge

Use:

- `GLEntry`
- `JournalEntry`
- `Account`
- `WorkOrderClose`
- `PayrollRegister`

Suggested outputs:

- trial balance by month
- journal-entry type mix
- control-account bridge
- retained-earnings and close-entry review

Best paired case:

- [Financial Statement Bridge Case](cases/financial-statement-bridge-case.md)

### Revenue, margin, and payroll mix

Use:

- `SalesInvoiceLine`
- `CreditMemoLine`
- `ShipmentLine`
- `Item`
- `PayrollRegister`
- `Employee`
- `CostCenter`

Suggested outputs:

- revenue and gross margin by collection, style, lifecycle, and supply mode
- payroll and people-cost mix by cost center, job family, and job level
- customer deposits and unapplied cash aging
- price realization versus list price by segment and customer
- gross-margin comparison for promotion versus non-promotion sales

Best paired case:

- [Pricing and Margin Governance Case](cases/pricing-and-margin-governance-case.md)

## Managerial and Cost-Accounting Workflows

### Product portfolio profitability

Use:

- `Item`
- `SalesInvoiceLine`
- `CreditMemoLine`
- `CustomerRefund`
- `SalesOrderLine`
- `ShipmentLine`

Suggested outputs:

- SKU mix by collection, style, lifecycle, and supply mode
- contribution margin by collection and material
- return and refund impact by lifecycle status
- shipment lag and fill rate by collection and style

Best paired case:

- [Product Portfolio Profitability Case](cases/product-portfolio-profitability-case.md)

### Labor and workforce mix

Use:

- `Employee`
- `CostCenter`
- `PayrollRegister`
- `TimeClockEntry`
- `LaborTimeEntry`
- `WorkCenter`

Suggested outputs:

- headcount by work location and job family
- payroll cost by cost center and job level
- approved clock hours versus direct labor usage
- workforce mix by employment status
- staffing coverage versus planned work-center load
- rostered hours versus approved worked hours by shift
- absence rate by work location and job family
- overtime approval coverage and punch-to-pay bridges

Best paired case:

- [Workforce Cost and Org-Control Case](cases/workforce-cost-and-org-control-case.md)
- [Workforce Coverage and Attendance Case](cases/workforce-coverage-and-attendance-case.md)

### Manufacturing, routing, and capacity

Use:

- `BillOfMaterial`
- `Routing`
- `RoutingOperation`
- `WorkCenterCalendar`
- `WorkOrder`
- `WorkOrderOperation`
- `WorkOrderOperationSchedule`
- `MaterialIssueLine`
- `ProductionCompletionLine`
- `WorkOrderClose`

Suggested outputs:

- BOM cost rollup
- operation throughput and planned-versus-actual labor
- daily load versus capacity
- backlog aging and late-operation review
- weekly forecast versus actual demand by item family
- recommendation mix by priority and planner
- rough-cut capacity pressure by work center and planning week
- collection revenue and margin before and after promotions
- customer-specific pricing concentration and override pressure

Best paired case:

- [Demand Planning and Replenishment Case](cases/demand-planning-and-replenishment-case.md)

## Audit Workflows

### Master-data and workforce controls

Use:

- `Employee`
- `Item`
- `PayrollRegister`
- `TimeClockEntry`
- `LaborTimeEntry`
- `PurchaseOrder`
- `JournalEntry`

Suggested outputs:

- post-termination activity by process area
- duplicate executive-role review
- missing item-master attributes by item group
- discontinued or pre-launch item activity
- approval concentration by expected role family
- scheduled-without-punch and punch-without-schedule review
- overtime without approval review
- absence with worked time review
- overlapping or incomplete punch review
- roster after termination review
- forecast approval and override review
- inactive or stale inventory policy review
- requisitions and work orders without planning support
- recommendation converted after need-by date review
- discontinued or pre-launch planning activity review
- sales below floor without approval
- expired or overlapping price-list review
- promotion scope and date mismatch review
- customer-specific price-list bypass review
- override approval completeness review

## Using the Workbook

- <FileName type="excel" /> is the main source workbook for dataset tables.
- For most new exercises, create a fresh working sheet and import only the required tables with Power Query.
- Open the published workbook when you need to inspect source sheets directly, but do the exercise work in your imported tables and analysis sheets.

## Where to Go Next

- Read [SQL Guide](sql-guide.md) for the matching query workflow.
- Read [Analytics Cases](cases/index.md) for guided walkthroughs.
- Read [Instructor Adoption Guide](../teach-with-data/instructor-guide.md) for classroom sequencing.
