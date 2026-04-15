---
title: Excel Guide
description: How to use the published Excel workbooks for student and classroom analysis.
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

1. open <FileName type="excel" />
2. open <FileName type="support" /> if the exercise is anomaly-focused
3. identify the sheets that match the query or case you are running
4. create a working sheet for pivots, formulas, and charts

## Recommended Workflow Pattern

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
- the support workbook

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
- [Attendance Control Audit Case](cases/attendance-control-audit-case.md)
- [Replenishment Support Audit Case](cases/replenishment-support-audit-case.md)
- [Pricing Governance Audit Case](cases/pricing-governance-audit-case.md)
- [Audit Exception Lab](cases/audit-exception-lab.md)

## Using the Workbook and Support Workbook

- <FileName type="excel" /> is the main workbook for dataset tables and Excel analysis.
- <FileName type="support" /> provides anomaly and validation context for exception-oriented review.
- Workbook exercises can start from either the published dataset tables or the support workbook, depending on the assignment.

## Where to Go Next

- Read [SQL Guide](sql-guide.md) for the matching query workflow.
- Read [Analytics Cases](cases/index.md) for guided walkthroughs.
- Read [Instructor Adoption Guide](../teach-with-data/instructor-guide.md) for classroom sequencing.
