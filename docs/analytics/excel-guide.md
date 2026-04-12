---
title: Excel Guide
description: How to use the Greenfield Excel workbooks for student and classroom analysis.
sidebar_label: Excel Guide
---

# Excel Starter Guide

## Workbook Setup

The dataset workbook contains one worksheet for each dataset table. Each worksheet is already exported as a formatted Excel Table with filters and a frozen header row.

The companion support workbook contains:

- `Overview`
- `AnomalyLog`
- `ValidationStages`
- `ValidationChecks`
- `ValidationExceptions`

Recommended first steps:

1. open `greenfield.xlsx`
2. open `greenfield_support.xlsx` if the exercise is anomaly-focused
3. identify the sheets that match the query or case you are running
4. create a working sheet for pivots, formulas, and charts

## Phase 19 Workflow Pattern

For most classes, use this sequence:

1. run the starter SQL file first
2. recreate the same idea in Excel
3. compare the workbook output to the SQL result
4. use the case doc for interpretation questions

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

Best paired case:

- [Workforce Cost and Org-Control Case](cases/workforce-cost-and-org-control-case.md)

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
- `greenfield_support.xlsx`

Suggested outputs:

- post-termination activity by process area
- duplicate executive-role review
- missing item-master attributes by item group
- discontinued or pre-launch item activity
- approval concentration by expected role family

### Support-workbook-assisted review

Use:

- `AnomalyLog`
- `ValidationStages`
- `ValidationChecks`
- `ValidationExceptions`

Suggested workflow:

1. group `AnomalyLog` by anomaly type
2. choose one anomaly family
3. trace it to the matching source worksheet
4. compare the Excel trace to the SQL starter query

Best paired cases:

- [Audit Review Pack Case](cases/audit-review-pack-case.md)
- [Audit Exception Lab](cases/audit-exception-lab.md)

## Clean vs Default Build in Excel

- Use the default anomaly-enabled build for most student work.
- Use the clean build mainly for instructor prep, baseline comparison, or shorter demonstrations.
- Some anomaly-oriented workbook reviews should return no rows on a clean build. That is expected.

## Where to Go Next

- Read [SQL Guide](sql-guide.md) for the matching query workflow.
- Read [Analytics Cases](cases/index.md) for guided walkthroughs.
- Read [Instructor Adoption Guide](../instructor-guide.md) for classroom sequencing.
