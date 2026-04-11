# Excel Starter Guide

**Audience:** Students, instructors, and analysts using the Excel export for classroom analysis.  
**Purpose:** Show how to turn the generated workbook into a practical starter environment for pivots, charts, aging schedules, payroll review, and anomaly analysis.  
**What you will learn:** Which sheets matter for each analytics area, how to structure pivots, and how to separate clean analysis from anomaly-focused review.

> **Implemented in current generator:** A workbook with one sheet per table plus `AnomalyLog` and `ValidationSummary`, suitable for Excel-based starter analytics across O2C, P2P, manufacturing, payroll, and journals.

> **Planned future extension:** More advanced workbook guidance for raw punch-event detail, rotating shifts, and richer employee-level workforce-planning analysis.

## Workbook Setup

The generated workbook contains:

- one worksheet for each dataset table
- `AnomalyLog`
- `ValidationSummary`

Recommended first steps:

1. open `outputs/greenfield_2026_2030.xlsx`
2. convert the most-used sheets into Excel Tables
3. freeze the top row on large sheets
4. format date and amount columns consistently
5. add slicers or timeline filters for year and month where helpful

For anomaly-focused teaching, use the default workbook from `config/settings.yaml` and then filter pivots or tables to one fiscal year when you want a narrower lab. The default workbook already includes `AnomalyLog`.

## Financial Accounting Workflows

### Monthly revenue and gross margin

Use:

- `GLEntry`
- `Account`

Recommended pivot layout:

- rows: `FiscalYear`, `FiscalPeriod`
- columns: `AccountType` or `AccountSubType`
- values:
  - `Sum of Debit`
  - `Sum of Credit`

Recommended helper logic:

- create a net amount column such as `Debit - Credit`
- for revenue analysis, treat revenue as credit-oriented and COGS as debit-oriented

Suggested charts:

- monthly revenue trend
- monthly gross margin trend

### AR aging

Use:

- `SalesInvoice`
- `CashReceipt`
- `CashReceiptApplication`
- `CreditMemo`
- `Customer`

Recommended steps:

1. summarize cash applications by `SalesInvoiceID`
2. summarize credit memos by `OriginalSalesInvoiceID`
3. join or look up those totals to invoice rows
4. compute open amount
5. compute aging bucket from `DueDate`

Suggested outputs:

- open AR by customer
- open AR by aging bucket
- open AR by region or customer segment

### AP aging

Use:

- `PurchaseInvoice`
- `DisbursementPayment`
- `Supplier`

Recommended outputs:

- open AP by supplier
- open AP by supplier category
- overdue AP by aging bucket

### Accrued expense roll-forward and settlement timing

Use:

- `JournalEntry`
- `GLEntry`
- `PurchaseInvoice`
- `PurchaseInvoiceLine`
- `DisbursementPayment`
- `Account`
- `Supplier`
- `Item`

Recommended steps:

1. filter `JournalEntry` to `EntryType = Accrual` and `EntryType = Accrual Adjustment`
2. use `PurchaseInvoiceLine[AccrualJournalEntryID]` to identify direct service invoice lines that clear prior accruals
3. summarize accrued amount, invoiced amount, and paid amount by month and expense family
4. tie the ledger view back to `2040` in `GLEntry`

Suggested outputs:

- accrued-expense roll-forward by month
- invoice-clearing lag by expense family
- residual accrued balances still open at period end

### Payroll liability and cash-flow review

Use:

- `PayrollRegister`
- `PayrollRegisterLine`
- `PayrollPayment`
- `PayrollLiabilityRemittance`
- `GLEntry`
- `Account`

Recommended outputs:

- payroll liability by account and month
- net-pay cash by month
- liability remittances by month and liability type
- gross-to-net bridge by employee or cost center

Suggested pivot layout:

- rows: `FiscalYear`, `FiscalPeriod`
- columns: liability type or cost center
- values:
- gross pay
- withholdings
- employer taxes
- employer benefits
- net pay

### Hourly payroll hours to paid earnings bridge

Use:

- `TimeClockEntry`
- `LaborTimeEntry`
- `PayrollRegister`
- `PayrollRegisterLine`
- `PayrollPayment`
- `Employee`
- `PayrollPeriod`

Recommended outputs:

- approved regular and overtime hours by employee and pay period
- hourly earnings by employee and pay period
- first payroll payment date by register
- clock-hours-to-paid-earnings bridge for hourly employees

### Journal and close-cycle analysis

Use:

- `JournalEntry`
- `GLEntry`

Recommended outputs:

- journal counts by `EntryType`
- journal amounts by month
- close-entry review by fiscal year

If you want to exclude year-end close activity from ledger analysis:

- use `XLOOKUP` from `GLEntry[VoucherNumber]` to `JournalEntry[EntryNumber]`
- bring `JournalEntry[EntryType]` into the ledger view
- filter out:
  - `Year-End Close - P&L to Income Summary`
  - `Year-End Close - Income Summary to Retained Earnings`

### Customer deposits and unapplied cash

Use:

- `CashReceipt`
- `CashReceiptApplication`
- `Customer`

Recommended outputs:

- open unapplied cash by customer
- age of open customer deposits
- days from receipt to first application

### Retained earnings and close-entry impact

Use:

- `GLEntry`
- `JournalEntry`
- `Account`

Recommended outputs:

- pre-close P&L by fiscal year
- close-entry totals by year-end close step
- retained-earnings movement from close journals

### Manufacturing cost-component bridge

Use:

- `MaterialIssueLine`
- `ProductionCompletionLine`
- `WorkOrderClose`
- `GLEntry`
- `Account`

Recommended outputs:

- material issued versus completed standard material cost
- direct labor and overhead components by month
- WIP, manufacturing clearing, and variance ledger movement by month

### Payroll expense mix by cost center and pay class

Use:

- `PayrollRegister`
- `PayrollPeriod`
- `Employee`
- `CostCenter`

Recommended outputs:

- gross pay by pay class and cost center
- employer burden by cost center
- net-pay mix by month

## Managerial Accounting Workflows

### Budget vs actual

Use:

- `Budget`
- `CostCenter`
- `Account`
- `GLEntry`
- `JournalEntry`

Recommended approach:

1. build a budget pivot by year, month, cost center, and account
2. build an actual-expense pivot from `GLEntry`
3. exclude year-end close journal rows from actual expense
4. compare the two in a summary sheet or Power Query merge

Suggested charts:

- monthly budget versus actual by cost center
- variance by account within one cost center

### Sales mix and product mix

Use:

- `SalesInvoice`
- `SalesInvoiceLine`
- `Customer`
- `Item`

Recommended pivots:

- revenue by region and item group
- revenue by customer segment and item
- billed quantity by item group

### Inventory movement

Use:

- `GoodsReceipt`
- `GoodsReceiptLine`
- `Shipment`
- `ShipmentLine`
- `SalesReturnLine`
- `ProductionCompletionLine`
- `Warehouse`
- `Item`

Suggested outputs:

- inbound quantity by warehouse and item group
- outbound quantity by warehouse and item group
- net movement by item

### Supplier and purchasing analysis

Use:

- `PurchaseOrder`
- `PurchaseOrderLine`
- `Supplier`
- `Item`

Suggested pivots:

- ordered value by supplier category
- ordered value by supplier risk rating
- item-group purchasing by month

### Product costing and labor analysis

Use:

- `Item`
- `Routing`
- `RoutingOperation`
- `WorkCenter`
- `WorkOrder`
- `WorkOrderOperation`
- `ProductionCompletionLine`
- `WorkOrderClose`
- `LaborTimeEntry`
- `Employee`

Suggested outputs:

- unit-cost bridge by manufactured item
- direct labor by work order and employee class
- operation-level labor by work center and month
- labor efficiency and rate variance by work order
- absorption margin vs contribution margin
- manufactured vs purchased product margin comparison

Suggested charts:

- contribution margin by item group
- labor-cost trend by month
- work-center activity by month
- work-order variance bridge by cost component

### Manufacturing workflows

Use:

- `Item`
- `BillOfMaterial`
- `BillOfMaterialLine`
- `Routing`
- `RoutingOperation`
- `WorkCenter`
- `WorkOrder`
- `WorkOrderOperation`
- `MaterialIssueLine`
- `ProductionCompletionLine`
- `WorkOrderClose`
- `GLEntry`
- `Account`

Suggested outputs:

- BOM cost rollup by manufactured item
- routing master review by manufactured item
- work-order throughput by month and warehouse
- operation throughput and planned-versus-actual labor by work center
- issued material versus completed output by work order
- WIP, manufacturing clearing, and manufacturing variance review by period

### Capacity and scheduling workflows

Use:

- `WorkCenter`
- `WorkCenterCalendar`
- `WorkOrderOperation`
- `WorkOrderOperationSchedule`
- `RoutingOperation`

Suggested outputs:

- daily scheduled hours versus available hours by work center
- monthly utilization by work center
- fully booked days by month
- late operations by work center and operation code
- backlog aging for open operations

Suggested charts:

- monthly utilization line chart by work center
- stacked column of scheduled versus remaining hours
- backlog-aging bar chart by work center

### Shift adherence and overtime workflows

Use:

- `ShiftDefinition`
- `EmployeeShiftAssignment`
- `TimeClockEntry`
- `WorkCenter`
- `Employee`

Suggested outputs:

- monthly overtime hours by work center and shift
- average start-time variance from assigned shift by work center
- late-start counts by shift and month
- employee-level shift adherence review

Suggested charts:

- overtime trend by work center
- average clock-in variance by shift

### Backorder, return, and supplier-reliability workflows

Use:

- `SalesOrder`
- `SalesOrderLine`
- `ShipmentLine`
- `CreditMemo`
- `CustomerRefund`
- `PurchaseOrder`
- `GoodsReceipt`
- `Supplier`

Suggested outputs:

- backorder quantity and fill rate by item group and month
- return and refund value by region and item group
- days to first receipt and days to full receipt by supplier

### Paid hours versus productive labor

Use:

- `TimeClockEntry`
- `LaborTimeEntry`
- `WorkOrderOperation`
- `WorkCenter`

Suggested outputs:

- approved paid hours by work center and month
- direct manufacturing hours by work center and month
- unallocated paid hours by work center
- direct productive share percentage

## Audit Analytics Workflows

### Document-chain completeness

Use:

- O2C document sheets for sales-side completeness
- P2P document sheets for purchasing-side completeness
- payroll sheets for payroll chain completeness

Recommended approach:

- build summary pivots by document status
- use Power Query or lookups for line-level completeness checks
- focus on:
  - partially shipped or billed sales activity
  - requisitions with missing later-stage activity
  - payroll registers with missing payment or remittance follow-up

### Approval and segregation-of-duties review

Use:

- `PurchaseRequisition`
- `PurchaseOrder`
- `PurchaseInvoice`
- `JournalEntry`
- `PayrollRegister`
- `Employee`

Suggested checks:

- same creator and approver
- missing approver on approved status
- concentration of approvals by one employee

### Cut-off and timing review

Use:

- `Shipment` and `SalesInvoice`
- `PurchaseRequisition`, `PurchaseOrder`, `GoodsReceipt`, and `PurchaseInvoice`
- `PayrollPeriod`, `PayrollPayment`, and `PayrollLiabilityRemittance`

Suggested measures:

- days from shipment to invoice
- days from requisition to order
- days from order to receipt
- days from receipt to invoice
- days from payroll approval to payment
- days from payroll period to liability remittance

### Anomaly review

Use:

- `AnomalyLog`
- `ValidationSummary`
- the base document sheets that the anomaly references

Suggested workflow:

1. summarize `AnomalyLog` by `anomaly_type`
2. trace one AP anomaly, one payroll anomaly, and one manufacturing anomaly to the source sheets
3. compare the sheet-level evidence to the matching SQL starter query

### Accrual cleanup review

Use:

- `JournalEntry`
- `PurchaseInvoice`
- `PurchaseInvoiceLine`
- `DisbursementPayment`

Recommended outputs:

- accruals with no linked service invoice after a long lag
- service invoices materially above or below the original accrual amount
- rare accrual-adjustment journals by month and expense family

Suggested workflow:

1. review anomaly counts by type
2. filter one anomaly type at a time
3. trace the related document back into the operational sheets
4. compare the anomaly to the clean process expectation

### Time-clock exception review

Use:

- `AttendanceException`
- `TimeClockEntry`
- `ShiftDefinition`
- `Employee`
- `WorkCenter`
- `PayrollRegisterLine`

Recommended outputs:

- exception counts by employee, supervisor, and work center
- missing clock-out review
- off-shift clocking review
- paid-without-clock and clock-without-pay review
- labor outside scheduled operation windows

### Accrued-service, customer-deposit, and bridge exception review

Use:

- `JournalEntry`
- `PurchaseInvoice`
- `PurchaseInvoiceLine`
- `DisbursementPayment`
- `CashReceipt`
- `CashReceiptApplication`
- `TimeClockEntry`
- `LaborTimeEntry`
- `PayrollRegister`

Recommended outputs:

- accrued-service invoices with large differences from their linked accrual
- open unapplied customer cash older than 30 days
- payroll hours versus approved-clock-hours mismatch review

## Clean Analysis vs Anomaly Analysis

- For clean baseline analysis, use a build with `anomaly_mode: none`.
- For controls teaching, use the default `standard` build.
- Make the distinction explicit in class, because some review sheets should be interpreted as designed exceptions rather than system errors.

## Current Scope Limits

The Excel starter layer does **not** assume:

- prebuilt pivot tables inside the exported workbook
- raw punch-event tables beneath the current approved daily time-clock rows

Those are future teaching extensions, not missing pieces of the current workbook.

## Where to Go Next

- Read [financial.md](financial.md), [managerial.md](managerial.md), or [audit.md](audit.md) for topic-specific workflows.
- Read [../instructor-guide.md](../instructor-guide.md) for how to sequence these workflows in class.
