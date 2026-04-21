---
title: GLEntry Posting Reference
description: Student-friendly guide to how business events become posted ledger entries.
sidebar_label: GLEntry Posting
---

# GLEntry Posting Reference

This reference explains which business events post to `GLEntry`, which documents remain operational only, which accounts move, and which posting date the dataset uses.

Students can use it with the process guides and Schema Reference to understand how source documents turn into accounting results.

## Non-Posting Documents

These documents are generated for process analysis but do **not** create `GLEntry` rows:

- `SalesOrder`
- `SalesOrderLine`
- `PurchaseRequisition`
- `PurchaseOrder`
- `PurchaseOrderLine`
- `BillOfMaterial`
- `BillOfMaterialLine`
- `WorkCenter`
- `WorkCenterCalendar`
- `Routing`
- `RoutingOperation`
- `WorkOrder`
- `WorkOrderOperation`
- `WorkOrderOperationSchedule`
- `ShiftDefinition`
- `EmployeeShiftAssignment`
- `TimeClockEntry`
- `AttendanceException`
- `PayrollPeriod`
- `LaborTimeEntry`

## Posting Matrix

| Event | Source tables | Posting date used | Debit | Credit |
|---|---|---|---|---|
| Opening balance journal | `JournalEntry` plus seeded GL rows | `2026-01-01` | Asset accounts and selected opening balances | Liability, equity, contra-asset balances, and retained earnings plug |
| Rent | `JournalEntry` plus seeded GL rows | First business day of month | `6070` Warehouse Rent or `6080` Office Rent | `1010` Cash and Cash Equivalents |
| Utilities | `JournalEntry` plus seeded GL rows | Last business day of month | `6090` Utilities Expense | `1010` Cash and Cash Equivalents |
| Factory overhead | `JournalEntry` plus seeded GL rows | Last business day of month | `1090` Manufacturing Cost Clearing, or `5080` Manufacturing Variance when the month has no capitalizable direct labor | `1010` Cash and Cash Equivalents |
| Depreciation | `JournalEntry` plus seeded GL rows | Last calendar day of month | `6130` Depreciation Expense | accumulated depreciation accounts |
| Month-end accrual | `JournalEntry` plus seeded GL rows | Last business day of month | selected operating expenses | `2040` Accrued Expenses |
| Accrual adjustment | `JournalEntry` plus seeded GL rows | First business day on or after the linked invoice approval date for invoice-linked residuals, or a rare later cleanup date for stale uninvoiced accruals | `2040` Accrued Expenses | original accrued expense account |
| Freight settlement | `JournalEntry` plus seeded GL rows | First business day of month | `2040` Accrued Expenses | `1010` Cash and Cash Equivalents |
| Shipment | `Shipment`, `ShipmentLine` | `ShipmentDate` | Item COGS account and `5050` Freight-Out Expense | Item inventory account and `2040` Accrued Expenses for outbound freight |
| Sales invoice | `SalesInvoice`, `SalesInvoiceLine` | `InvoiceDate` | Accounts receivable | Item revenue account, `4050` Freight Revenue, and sales tax payable |
| Cash receipt | `CashReceipt` | `ReceiptDate` | Cash | `2060` Customer Deposits and Unapplied Cash |
| Cash receipt application | `CashReceiptApplication` | `ApplicationDate` | `2060` Customer Deposits and Unapplied Cash | Accounts receivable |
| Sales return | `SalesReturn`, `SalesReturnLine` | `ReturnDate` | Item inventory account | Item COGS account |
| Credit memo | `CreditMemo`, `CreditMemoLine` | `CreditMemoDate` | `4060` Sales Returns and Allowances, optional `4050` Freight Revenue reversal, and sales tax payable reversal | Accounts receivable or `2060` Customer Deposits and Unapplied Cash |
| Customer refund | `CustomerRefund` | `RefundDate` | `2060` Customer Deposits and Unapplied Cash | Cash |
| Goods receipt | `GoodsReceipt`, `GoodsReceiptLine` | `ReceiptDate` | Item inventory account | `2020` Goods Received Not Invoiced |
| Material issue | `MaterialIssue`, `MaterialIssueLine` | `IssueDate` | `1046` Inventory - Work in Process | `1045` Inventory - Materials and Packaging |
| Production completion | `ProductionCompletion`, `ProductionCompletionLine` | `CompletionDate` | `1040` Inventory - Finished Goods | `1046` Inventory - Work in Process and `1090` Manufacturing Cost Clearing |
| Work-order close | `WorkOrderClose` | `CloseDate` | or credit `5080` Manufacturing Variance depending on sign | offset `1046` or `1090` residual balances |
| Payroll register | `PayrollRegister`, `PayrollRegisterLine` | `ApprovedDate` | Salary and wage expense by nonmanufacturing cost center, `6060` nonmanufacturing payroll burden, `1090` capitalizable manufacturing labor plus related burden, and `5080` noncapitalizable manufacturing payroll in no-direct-labor months | `2030` Accrued Payroll, `2031` Payroll Tax Withholdings Payable, `2032` Employer Payroll Taxes Payable, `2033` Employee Benefits and Other Deductions Payable |
| Payroll payment | `PayrollPayment` | `PaymentDate` | `2030` Accrued Payroll | Cash |
| Payroll liability remittance | `PayrollLiabilityRemittance` | `RemittanceDate` | `2031`, `2032`, or `2033` | Cash |
| Purchase invoice | `PurchaseInvoice`, `PurchaseInvoiceLine` | `ApprovedDate` | For receipt-matched inventory lines: GRNI cleared at matched receipt-line basis, purchase variance when needed, and nonrecoverable tax to variance. For accrued-service lines: `2040` up to the linked accrued amount and expense for any excess above the estimate; any invoice shortfall is reversed later through a linked accrual adjustment. | Accounts payable and purchase variance when needed |
| Disbursement | `DisbursementPayment` | `PaymentDate` | Accounts payable | Cash |
| Year-end close: P&L to income summary | `JournalEntry` plus seeded GL rows | `YYYY-12-31` | Revenue or expense balances needed to close annual P&L accounts | `8010` Income Summary |
| Year-end close: income summary to retained earnings | `JournalEntry` plus seeded GL rows | `YYYY-12-31` | `8010` Income Summary or `3030` Retained Earnings depending on sign | offset retained earnings or income summary |

## Core Control Accounts

| Account number | Meaning |
|---|---|
| `1010` | Cash and cash equivalents |
| `1020` | Accounts receivable |
| `1040` | Inventory - finished goods |
| `1045` | Inventory - materials and packaging |
| `1046` | Inventory - work in process |
| `1090` | Manufacturing cost clearing |
| `2010` | Accounts payable |
| `2020` | Goods Received Not Invoiced |
| `2030` | Accrued payroll |
| `2031` | Payroll tax withholdings payable |
| `2032` | Employer payroll taxes payable |
| `2033` | Employee benefits and other deductions payable |
| `2040` | Accrued expenses |
| `2050` | Sales tax payable |
| `2060` | Customer deposits and unapplied cash |
| `4050` | Freight revenue |
| `4060` | Sales returns and allowances |
| `5050` | Freight-out expense |
| `5080` | Manufacturing variance |
| `3030` | Retained earnings |
| `5060` | Purchase price variance |
| `8010` | Income summary |

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
