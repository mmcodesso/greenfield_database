# Greenfield Home Furnishings, Inc.
## Schema Specification and Posting Rules

> **Audience:** Maintainers and advanced contributors who need the original long-form blueprint.
>
> **Primary documentation now lives in `docs/`.** Start with:
>
> - `docs/dataset-overview.md`
> - `docs/process-flows.md`
> - `docs/database-guide.md`
> - `docs/code-architecture.md`
> - `docs/reference/schema.md`
> - `docs/reference/posting.md`
> - `docs/reference/row-volume.md`
>
> This file is preserved as a technical appendix and historical design document. Some sections describe future or proposed functionality and do **not** match the current generator exactly.

## 1. Purpose and design objective

This dataset is designed for a teaching book in accounting analytics. It must support SQL querying, financial statement construction, subledger-to-ledger reconciliation, audit analytics, managerial accounting analytics, and business process analysis across both the order-to-cash and procure-to-pay cycles.

The dataset will cover five fiscal years, assumed here to be fiscal years 2026 through 2030, with transaction activity generated throughout each month. The design goal is not a small illustrative dataset. It is a realistic mid-sized transactional dataset large enough to support monthly, quarterly, annual, trend, anomaly, and forensic analyses.

The accounting model will use a perpetual inventory system. Operational documents will drive accounting postings. The general ledger will be the official reporting layer, but it will be generated from source transactions plus a defined set of manual journal entries.

## 2. Business scope assumptions

Greenfield Home Furnishings, Inc. is modeled as a mid-sized distributor and light assembler of home furnishings. The company purchases finished goods, packaging, and selected materials, warehouses inventory at two locations, and sells primarily to wholesale and direct-to-business customers.

Version 3 does not include a full manufacturing module. There are no production orders, work orders, bills of materials, labor routings, or finished goods completion postings. Items classified as raw materials or packaging exist to support purchasing analytics and inventory variety, but the accounting logic remains within a merchandising-style perpetual inventory environment.

This scope keeps the dataset analytically rich while avoiding unnecessary complexity for students.

## 3. Revised dataset scale

The previous row estimates were too low for a five-year monthly transactional database. The revised design assumes sustained monthly activity across five years.

### 3.1 Expected row targets by table

| Group | Table | Revised expected rows |
|---|---:|---:|
| Accounting Core | Account | 75 to 95 |
| Accounting Core | JournalEntry | 900 to 1,500 |
| Accounting Core | GLEntry | 60,000 to 110,000 |
| O2C | Customer | 150 to 300 |
| O2C | SalesOrder | 4,500 to 9,000 |
| O2C | SalesOrderLine | 13,000 to 30,000 |
| O2C | Shipment | 4,200 to 8,500 |
| O2C | ShipmentLine | 12,000 to 28,000 |
| O2C | SalesInvoice | 4,200 to 8,500 |
| O2C | SalesInvoiceLine | 12,000 to 28,000 |
| O2C | CashReceipt | 4,000 to 9,500 |
| P2P | Supplier | 80 to 160 |
| P2P | PurchaseRequisition | 2,500 to 6,000 |
| P2P | PurchaseOrder | 2,200 to 5,500 |
| P2P | PurchaseOrderLine | 7,000 to 18,000 |
| P2P | GoodsReceipt | 2,100 to 5,000 |
| P2P | GoodsReceiptLine | 6,500 to 17,000 |
| P2P | PurchaseInvoice | 2,100 to 5,000 |
| P2P | PurchaseInvoiceLine | 6,500 to 17,000 |
| P2P | DisbursementPayment | 2,300 to 5,500 |
| Master Data | Item | 180 to 350 |
| Master Data | Warehouse | 2 to 3 |
| Master Data | Employee | 55 to 75 |
| Organizational | CostCenter | 8 to 14 |
| Organizational | Budget | 2,000 to 4,500 |

This produces a database in the broad range of approximately 150,000 to 300,000 total rows, depending on final monthly activity assumptions and anomaly settings.

## 4. Schema overview

The current implemented schema contains 25 tables.

### 4.1 Final table groups

**Accounting Core**
- Account
- JournalEntry
- GLEntry

**Order-to-Cash**
- Customer
- SalesOrder
- SalesOrderLine
- Shipment
- ShipmentLine
- SalesInvoice
- SalesInvoiceLine
- CashReceipt

**Procure-to-Pay**
- Supplier
- PurchaseRequisition
- PurchaseOrder
- PurchaseOrderLine
- GoodsReceipt
- GoodsReceiptLine
- PurchaseInvoice
- PurchaseInvoiceLine
- DisbursementPayment

**Master Data**
- Item
- Warehouse
- Employee

**Organizational**
- CostCenter
- Budget

## 5. Key revisions to the schema

### 5.1 Required new tables

#### ShipmentLine
This table is required to support shipment quantity analysis, partial shipments, cut-off testing, and item-level COGS logic.

| Column | Type | Description |
|---|---|---|
| ShipmentLineID | integer, PK | Unique identifier |
| ShipmentID | integer, FK -> Shipment | Parent shipment |
| SalesOrderLineID | integer, FK -> SalesOrderLine | Source order line |
| LineNumber | integer | Sequence within shipment |
| ItemID | integer, FK -> Item | Item shipped |
| QuantityShipped | decimal | Quantity shipped |
| ExtendedStandardCost | decimal | QuantityShipped x item standard cost at posting time |

#### GoodsReceiptLine
This table is required to support quantity-level receiving, partial receipts, over-receipts, and line-level three-way matching.

| Column | Type | Description |
|---|---|---|
| GoodsReceiptLineID | integer, PK | Unique identifier |
| GoodsReceiptID | integer, FK -> GoodsReceipt | Parent goods receipt |
| POLineID | integer, FK -> PurchaseOrderLine | Source PO line |
| LineNumber | integer | Sequence within receipt |
| ItemID | integer, FK -> Item | Item received |
| QuantityReceived | decimal | Quantity received |
| ExtendedStandardCost | decimal | QuantityReceived x item standard cost at posting time |

### 5.2 Required line-level foreign key revisions

#### SalesInvoiceLine
Add direct link to the originating sales order line.

**New column:**
- SalesOrderLineID, integer, FK -> SalesOrderLine

This enables exact order-to-invoice matching and line-level exception analysis.

#### PurchaseInvoiceLine
Add direct link to the originating purchase order line.

**New column:**
- POLineID, integer, FK -> PurchaseOrderLine

This enables exact PO-to-invoice line matching.

### 5.3 Required datatype and naming revisions

Several fields currently point to foreign keys but are typed as text. Those should be converted to integer foreign keys.

The following changes are required throughout the schema.

- GLEntry.CreatedBy -> CreatedByEmployeeID, integer, FK -> Employee
- JournalEntry.CreatedBy -> CreatedByEmployeeID, integer, FK -> Employee
- JournalEntry.ApprovedBy -> ApprovedByEmployeeID, integer, FK -> Employee
- Customer.SalesRepID -> SalesRepEmployeeID, integer, FK -> Employee
- SalesOrder.SalesRepID -> SalesRepEmployeeID, integer, FK -> Employee
- CashReceipt.RecordedBy -> RecordedByEmployeeID, integer, FK -> Employee
- PurchaseRequisition.RequestedBy -> RequestedByEmployeeID, integer, FK -> Employee
- PurchaseRequisition.ApprovedBy -> ApprovedByEmployeeID, integer, FK -> Employee
- PurchaseRequisition.Department -> CostCenterID, integer, FK -> CostCenter
- PurchaseOrder.CreatedBy -> CreatedByEmployeeID, integer, FK -> Employee
- PurchaseOrder.ApprovedBy -> ApprovedByEmployeeID, integer, FK -> Employee
- GoodsReceipt.ReceivedBy -> ReceivedByEmployeeID, integer, FK -> Employee
- PurchaseInvoice.ApprovedBy -> ApprovedByEmployeeID, integer, FK -> Employee
- DisbursementPayment.ApprovedBy -> ApprovedByEmployeeID, integer, FK -> Employee
- Employee.Department -> CostCenterID, integer, FK -> CostCenter

### 5.4 Required accounting traceability revisions

#### GLEntry
VoucherType and VoucherNumber should be retained for user readability, but they are not enough for robust data lineage. Add explicit source fields.

**New columns:**
- SourceDocumentType, text
- SourceDocumentID, integer
- SourceLineID, integer, nullable
- FiscalYear, integer
- FiscalPeriod, integer

These additions make it possible to trace each GL line directly back to a source transaction or journal entry.

#### JournalEntry
Add reversal linkage.

**New column:**
- ReversesJournalEntryID, integer, FK -> JournalEntry, nullable

This supports year-end reversal analysis.

### 5.5 Recommended item master enhancement

To support automated posting rules, the item master should include account mapping fields.

**Add these columns to Item:**
- InventoryAccountID, integer, FK -> Account
- RevenueAccountID, integer, FK -> Account, nullable
- COGSAccountID, integer, FK -> Account, nullable
- PurchaseVarianceAccountID, integer, FK -> Account, nullable
- TaxCategory, text

This avoids hardcoding account mappings in the posting engine.

### 5.6 Recommended customer and supplier segmentation fields

These are not strictly required for accounting, but they improve teaching value.

**Add to Customer:**
- CustomerSegment, text
- Industry, text
- Region, text

**Add to Supplier:**
- SupplierCategory, text
- SupplierRiskRating, text
- DefaultCurrency, text

## 6. Revised table-by-table notes

### 6.1 Accounting core

#### Account
The chart of accounts should support both financial statements and management reporting. Include assets, liabilities, equity, revenue, contra-revenue if used, COGS, operating expenses, and other income and expense accounts. Parent-child hierarchy should support roll-up reporting.

Recommended row count: 75 to 95.

#### JournalEntry
This table holds manual and system-scheduled non-subledger entries such as opening balances, payroll, rent, utilities, depreciation, accruals, year-end close, and reversals.

Recommended row count: 900 to 1,500 over five years.

#### GLEntry
This is the official reporting table and must balance by voucher and by fiscal period.

Recommended row count: 60,000 to 110,000.

### 6.2 Order-to-cash

#### Customer
A broader customer master is recommended so that revenue concentration, aging, and segment analysis are meaningful.

Recommended row count: 150 to 300.

#### SalesOrder and SalesOrderLine
Sales orders should represent monthly transaction activity across multiple customers, items, and sales reps, with seasonality and moderate annual growth.

Recommended row count:
- SalesOrder: 4,500 to 9,000
- SalesOrderLine: 13,000 to 30,000

#### Shipment and ShipmentLine
Shipments should support partial fulfillment, delayed fulfillment, returns, and cut-off anomalies.

Recommended row count:
- Shipment: 4,200 to 8,500
- ShipmentLine: 12,000 to 28,000

#### SalesInvoice and SalesInvoiceLine
Version 3 assumes one invoice references one sales order, but the invoice may bill fewer than all shipped lines if needed. The model should not support many orders to one invoice in the base version.

Recommended row count:
- SalesInvoice: 4,200 to 8,500
- SalesInvoiceLine: 12,000 to 28,000

#### CashReceipt
Allow multiple receipts against one invoice. Unapplied receipts remain allowed for anomaly design.

Recommended row count: 4,000 to 9,500.

### 6.3 Procure-to-pay

#### Supplier
A wider supplier base improves duplicate vendor and unauthorized vendor exercises.

Recommended row count: 80 to 160.

#### PurchaseRequisition
Requisitions should be generated by department and item, with approval patterns tied to employee authorization levels.

Recommended row count: 2,500 to 6,000.

#### PurchaseOrder and PurchaseOrderLine
The base design should support one supplier per PO and allow some POs without requisitions only as planted exceptions.

Recommended row count:
- PurchaseOrder: 2,200 to 5,500
- PurchaseOrderLine: 7,000 to 18,000

#### GoodsReceipt and GoodsReceiptLine
Receipts should support partial and full receipt behavior and will be central to receiving and accrual postings.

Recommended row count:
- GoodsReceipt: 2,100 to 5,000
- GoodsReceiptLine: 6,500 to 17,000

#### PurchaseInvoice and PurchaseInvoiceLine
Version 3 assumes one supplier invoice references one PO in the base design. Missing PO references remain allowed as planted anomalies.

Recommended row count:
- PurchaseInvoice: 2,100 to 5,000
- PurchaseInvoiceLine: 6,500 to 17,000

#### DisbursementPayment
Allow partial and full invoice settlement. Prepayments remain optional and rare.

Recommended row count: 2,300 to 5,500.

### 6.4 Master and organizational data

#### Item
The item table should include both sellable and purchasable goods, but the majority of teaching analytics will focus on sellable finished goods and inventory-linked purchases.

Recommended row count: 180 to 350.

#### Warehouse
Two warehouses are enough for version 3, with a third optional distribution site.

Recommended row count: 2 to 3.

#### Employee
Keep the employee count near the original business scale.

Recommended row count: 55 to 75.

#### CostCenter
Recommended row count: 8 to 14.

#### Budget
Budgets should be monthly by fiscal year, cost center, and account. Only selected revenue and expense accounts need budgets.

Recommended row count: 2,000 to 4,500.

## 7. Posting rules philosophy

The accounting engine must follow explicit event-based posting rules. Source documents create subledger activity, and the subledger activity generates GL entries.

The posting engine should follow four principles.

First, every posting event must produce balanced debits and credits.

Second, each posting must carry a source document reference, a posting date, a fiscal year, a fiscal period, and the employee or system process that created it.

Third, operational activity and manual journal entries must together produce complete financial statements.

Fourth, a small number of planted anomalies may intentionally violate expected process flow, but they should not break overall ledger balance.

## 8. Core accounting assumptions

### 8.1 Inventory method
- Perpetual inventory
- Standard cost for instructional simplicity
- COGS recognized at shipment date
- Inventory updated at goods receipt date

### 8.2 Revenue recognition
- Revenue recognized at invoice date in the normal case
- Shipment should normally occur on or before invoice date
- Selected planted exceptions may violate this for cut-off analysis

### 8.3 Accounts receivable and accounts payable
- AR recognized at sales invoice posting
- AP recognized when supplier invoice is approved and posted
- A goods-received-not-invoiced accrual account is used when goods are received before invoice posting

### 8.4 Tax treatment
- Sales tax is tracked separately and credited to Sales Tax Payable
- Purchase tax may be included in invoice total, but for simplicity it may be expensed or capitalized depending on item treatment rules defined in the generator

### 8.5 Fiscal calendar
- Calendar fiscal year ending December 31
- Monthly accounting periods 1 through 12
- Monthly and annual closing routines supported

## 9. Detailed posting rules by event

## 9.1 No-posting operational events

The following events are operational only and do not create GL entries in the base design.

- SalesOrder creation
- PurchaseRequisition creation
- PurchaseOrder creation

These events remain essential for process analytics but are non-posting documents.

## 9.2 Shipment posting

### Trigger
Shipment is posted when a shipment header and related shipment lines are finalized.

### Accounting effect
Recognize cost of goods sold and reduce inventory.

### Standard entry
- Debit COGS
- Credit Inventory

### Amount basis
Use ShipmentLine.QuantityShipped multiplied by the item standard cost effective on the shipment date.

### Source reference
- SourceDocumentType = Shipment
- SourceDocumentID = ShipmentID
- SourceLineID = ShipmentLineID

### Cost center treatment
Default cost center from the related sales order or sales rep department.

## 9.3 Sales invoice posting

### Trigger
Sales invoice is posted when status moves from Draft to Submitted or equivalent posted status.

### Accounting effect
Recognize receivable, revenue, and tax liability.

### Standard entry
- Debit Accounts Receivable for GrandTotal
- Credit Sales Revenue for SubTotal
- Credit Sales Tax Payable for TaxAmount

### Source reference
- SourceDocumentType = SalesInvoice
- SourceDocumentID = SalesInvoiceID
- SourceLineID = nullable for header-level AR line and populated for revenue lines if desired

### Notes
In the normal case, the invoice date should be on or after the shipment date. Selected planted anomalies may create invoice-before-shipment exceptions.

## 9.4 Cash receipt posting

### Trigger
Cash receipt is posted when payment is recorded.

### Accounting effect
Reduce receivable and increase cash.

### Standard entry
- Debit Cash
- Credit Accounts Receivable

### Source reference
- SourceDocumentType = CashReceipt
- SourceDocumentID = CashReceiptID

### Special cases
- Unapplied cash may credit Unearned or Unapplied Cash Receipts instead of AR until matched
- Overpayments may also post excess amounts to an unapplied cash liability account if desired

## 9.5 Goods receipt posting

### Trigger
Goods receipt is posted when inventory is physically received.

### Accounting effect
Increase inventory and create accrued purchases liability pending vendor invoice.

### Standard entry
- Debit Inventory
- Credit Goods Received Not Invoiced or Accrued Purchases

### Amount basis
Use GoodsReceiptLine.QuantityReceived multiplied by item standard cost or PO unit cost, depending on final teaching preference.

### Recommended teaching choice
Use PO unit cost when available. This produces cleaner purchase accruals and easier three-way match logic.

### Source reference
- SourceDocumentType = GoodsReceipt
- SourceDocumentID = GoodsReceiptID
- SourceLineID = GoodsReceiptLineID

## 9.6 Purchase invoice posting

### Trigger
Purchase invoice is posted when approved.

### Accounting effect
Recognize or settle liability associated with vendor invoice.

### Standard entry for received goods already accrued
- Debit Goods Received Not Invoiced or Accrued Purchases for matched amount
- Debit Purchase Price Variance for unfavorable variance if invoice exceeds accrued amount
- Credit Purchase Price Variance for favorable variance if invoice is below accrued amount
- Credit Accounts Payable for GrandTotal excluding nonrecoverable tax handling differences if used

### Simplified alternative
If price variance treatment is too advanced for the main version, post:
- Debit Goods Received Not Invoiced for accrued amount
- Debit Inventory or Expense for difference
- Credit Accounts Payable for invoice total

### Source reference
- SourceDocumentType = PurchaseInvoice
- SourceDocumentID = PurchaseInvoiceID
- SourceLineID = PurchaseInvoiceLineID for line-level postings where used

### Special cases
If there is no matching goods receipt, the invoice may be posted directly to Inventory or Expense plus AP, but this should be rare and usually flagged as an anomaly.

## 9.7 Disbursement payment posting

### Trigger
Vendor payment is posted when payment is issued.

### Accounting effect
Reduce AP and reduce cash.

### Standard entry
- Debit Accounts Payable
- Credit Cash

### Source reference
- SourceDocumentType = DisbursementPayment
- SourceDocumentID = DisbursementID

### Special cases
- Prepayments may debit Vendor Advances instead of AP
- Duplicate payments remain posted normally and are detected analytically rather than prevented in the data

## 9.8 Manual operating journal entries

These entries are required so that the company has realistic financial statements beyond inventory purchases and sales.

### Payroll accrual or payroll payment
- Debit Salaries Expense
- Credit Cash or Accrued Payroll

### Rent
- Debit Rent Expense
- Credit Cash or Accounts Payable

### Utilities
- Debit Utilities Expense
- Credit Accounts Payable or Cash

### Depreciation
- Debit Depreciation Expense
- Credit Accumulated Depreciation

### Office and administrative spending
- Debit relevant operating expense
- Credit Cash or Accounts Payable

### Interest and financing entries if used
- Debit Interest Expense
- Credit Cash or Interest Payable

These entries should be generated monthly or biweekly depending on the account.

## 9.9 Period-end accruals and reversals

At month-end and especially year-end, the generator may create accruals for expenses incurred but not yet invoiced or paid.

### Example accrual
- Debit Utilities Expense
- Credit Accrued Expenses

### Reversal next period
- Debit Accrued Expenses
- Credit Utilities Expense

Reversal links should be maintained through ReversesJournalEntryID.

## 9.10 Year-end closing entries

At year-end, temporary accounts should be closed to retained earnings through an Income Summary account or directly.

### Standard conceptual flow
- Close revenues to Income Summary
- Close expenses and COGS to Income Summary
- Close Income Summary to Retained Earnings

A simplified direct close to Retained Earnings is acceptable if the teaching objective does not require separate close mechanics.

## 10. Required chart of accounts categories

The chart of accounts should include at least the following groups.

### Assets
- Cash
- Accounts Receivable
- Inventory
- Prepaid Expenses
- Fixed Assets
- Accumulated Depreciation as contra-asset

### Liabilities
- Accounts Payable
- Goods Received Not Invoiced or Accrued Purchases
- Accrued Payroll
- Accrued Expenses
- Sales Tax Payable

### Equity
- Common Stock or Paid-In Capital
- Retained Earnings
- Current Year Earnings if desired for reporting convenience

### Revenue
- Product Revenue by major channel or category
- Optional Sales Returns and Allowances as contra-revenue

### Cost of goods sold
- COGS by major product family if desired
- Purchase Price Variance if used

### Operating expenses
- Salaries Expense
- Rent Expense
- Utilities Expense
- Freight and Delivery Expense
- Warehouse Expense
- Sales and Marketing Expense
- Administrative Expense
- Depreciation Expense
- Bad Debt Expense if desired

## 11. Cost center rules

Every posting does not need a cost center, but cost center logic should be defined systematically.

### Recommended rules
- Revenue lines inherit cost center from SalesOrder
- COGS lines inherit the same sales cost center as related revenue
- Purchasing accruals and purchase invoice lines inherit requesting or owning cost center when known
- Operating manual entries are assigned to the relevant departmental cost center
- Balance sheet control accounts may carry null cost center when not meaningful

## 12. Anomaly design principles for version 3

Anomalies should be injected after a clean dataset is generated and validated.

### Core principle
The anomaly should violate an expected business control or data quality rule without causing the overall GL to go out of balance.

### Examples retained from earlier version
- Weekend journal postings
- Same creator and approver
- Missing approvals
- Invoice before shipment
- Invoice with no shipment
- Over-credit-limit orders
- Unauthorized vendors
- Duplicate payments
- Duplicate supplier invoice numbers
- Related-party address matches
- Year-end reversals
- Threshold-adjacent entries

### Scaling rule
Anomalies should remain sparse, typically well below 1 percent of total transactional volume for any single anomaly type.

## 13. Validation rules the generator must pass

Before export, the generator should run validation checks.

### Document-level validations
- Header totals equal sum of line totals
- Invoice totals equal subtotal plus tax
- Shipment lines roll to shipment quantities
- Goods receipt lines roll to receipt totals

### Accounting validations
- Every voucher balances
- Every fiscal period trial balance nets to zero
- AR subledger reconciles to AR control account by period-end
- AP subledger reconciles to AP control account by period-end
- Inventory movement reconciles to ending inventory account by period-end
- Retained earnings roll forward across fiscal years

### Process validations
- In the clean base dataset, invoice date should not precede shipment date
- Purchase invoice date should normally follow PO date
- Goods receipt date should normally not precede PO date
- Employee authorization level should support the approvals generated

## 14. Generation sequence for the Python build

The recommended generation order is as follows.

1. Create schema and reference tables
2. Generate cost centers and employees
3. Generate warehouses, accounts, and item master with account mappings
4. Generate customers and suppliers
5. Generate opening balances as of January 1, 2026
6. Generate monthly budgets
7. Generate O2C transactions month by month
8. Generate P2P transactions month by month
9. Generate recurring manual journal entries
10. Post all operational and manual entries to the GL
11. Run clean validations
12. Inject anomalies
13. Re-run validations, allowing only intended exceptions
14. Export SQLite and Excel outputs

## 15. Recommended implementation notes for the Python script

The script should use a fixed random seed so that the dataset is reproducible. The generator should be modular, with separate functions for schema creation, master data generation, transaction generation, GL posting, anomaly injection, and validation.

The script should output at least three deliverables.

- A SQLite database
- An Excel workbook with one worksheet per table
- A validation summary report showing row counts, balancing checks, and intentional anomaly counts

## 16. Immediate next drafting tasks

The next working documents to build are:

1. A detailed chart of accounts with account numbers, account types, subtypes, and normal balances
2. A posting matrix that maps each business event to debit and credit accounts
3. A row-volume model by month for fiscal years 2021 through 2025
4. A data generation blueprint for the Python script, including function sequence and validation checks

This version establishes the revised schema and the accounting logic needed to begin those next drafts.

## 17. Detailed chart of accounts draft

The chart of accounts should be broad enough to support financial statement construction, subledger reconciliation, managerial reporting by cost center, and selected anomaly analytics. At the same time, it should remain teachable. The recommended design is approximately 85 accounts.

### 17.1 Chart of accounts structure principles

The account numbering below follows a simple instructional logic.

- 1000 series: Assets
- 2000 series: Liabilities
- 3000 series: Equity
- 4000 series: Revenue and contra-revenue
- 5000 series: Cost of goods sold and purchase variances
- 6000 series: Operating expenses
- 7000 series: Other income and expense
- 8000 series: Closing and summary accounts if used

Each account should carry five core attributes.

- AccountNumber
- AccountName
- AccountType
- AccountSubType
- NormalBalance

Parent-child relationships should be used where roll-up reporting is needed.

### 17.2 Detailed chart of accounts

| AccountNumber | AccountName | AccountType | AccountSubType | NormalBalance | Notes |
|---|---|---|---|---|---|
| 1000 | Assets | Asset | Header | Debit | Parent summary account |
| 1010 | Cash and Cash Equivalents | Asset | Current Asset | Debit | Main operating cash |
| 1020 | Accounts Receivable | Asset | Current Asset | Debit | Customer receivables |
| 1030 | Allowance for Doubtful Accounts | Asset | Contra Current Asset | Credit | Optional bad debt reserve |
| 1040 | Inventory - Finished Goods | Asset | Current Asset | Debit | Primary sellable inventory |
| 1045 | Inventory - Materials and Packaging | Asset | Current Asset | Debit | Optional secondary inventory |
| 1050 | Prepaid Expenses | Asset | Current Asset | Debit | Prepaids |
| 1060 | Employee Advances | Asset | Current Asset | Debit | Optional |
| 1070 | Vendor Advances | Asset | Current Asset | Debit | Optional supplier prepayments |
| 1080 | Other Current Assets | Asset | Current Asset | Debit | Miscellaneous current assets |
| 1100 | Fixed Assets | Asset | Header | Debit | Parent summary account |
| 1110 | Furniture and Fixtures | Asset | Fixed Asset | Debit | Long-lived assets |
| 1120 | Warehouse Equipment | Asset | Fixed Asset | Debit | Material handling and warehouse assets |
| 1130 | Office Equipment | Asset | Fixed Asset | Debit | Administrative assets |
| 1140 | Leasehold Improvements | Asset | Fixed Asset | Debit | Optional |
| 1150 | Accumulated Depreciation - Furniture and Fixtures | Asset | Contra Fixed Asset | Credit | Contra asset |
| 1160 | Accumulated Depreciation - Warehouse Equipment | Asset | Contra Fixed Asset | Credit | Contra asset |
| 1170 | Accumulated Depreciation - Office Equipment | Asset | Contra Fixed Asset | Credit | Contra asset |
| 1180 | Intangible Assets | Asset | Noncurrent Asset | Debit | Optional |
| 1190 | Other Noncurrent Assets | Asset | Noncurrent Asset | Debit | Optional |
| 2000 | Liabilities | Liability | Header | Credit | Parent summary account |
| 2010 | Accounts Payable | Liability | Current Liability | Credit | Vendor payables |
| 2020 | Goods Received Not Invoiced | Liability | Current Liability | Credit | Accrued purchases or GRNI |
| 2030 | Accrued Payroll | Liability | Current Liability | Credit | Payroll accrual |
| 2040 | Accrued Expenses | Liability | Current Liability | Credit | Utilities, rent, and other accruals |
| 2050 | Sales Tax Payable | Liability | Current Liability | Credit | Tax collected on sales |
| 2060 | Customer Deposits and Unapplied Cash | Liability | Current Liability | Credit | Unapplied or advance customer cash |
| 2070 | Deferred Revenue | Liability | Current Liability | Credit | Optional |
| 2080 | Interest Payable | Liability | Current Liability | Credit | Optional |
| 2090 | Other Current Liabilities | Liability | Current Liability | Credit | Miscellaneous |
| 2100 | Long-Term Liabilities | Liability | Header | Credit | Parent summary account |
| 2110 | Notes Payable | Liability | Long-Term Liability | Credit | Optional debt |
| 2120 | Lease Liability | Liability | Long-Term Liability | Credit | Optional |
| 2130 | Other Long-Term Liabilities | Liability | Long-Term Liability | Credit | Optional |
| 3000 | Equity | Equity | Header | Credit | Parent summary account |
| 3010 | Common Stock | Equity | Equity | Credit | Paid-in capital |
| 3020 | Additional Paid-In Capital | Equity | Equity | Credit | Optional |
| 3030 | Retained Earnings | Equity | Equity | Credit | Closing balance |
| 3040 | Dividends or Owner Distributions | Equity | Contra Equity | Debit | Optional |
| 3050 | Current Year Earnings | Equity | Equity | Credit | Optional reporting convenience |
| 4000 | Revenue | Revenue | Header | Credit | Parent summary account |
| 4010 | Sales Revenue - Furniture | Revenue | Operating Revenue | Credit | Product family revenue |
| 4020 | Sales Revenue - Lighting | Revenue | Operating Revenue | Credit | Product family revenue |
| 4030 | Sales Revenue - Textiles | Revenue | Operating Revenue | Credit | Product family revenue |
| 4040 | Sales Revenue - Accessories | Revenue | Operating Revenue | Credit | Product family revenue |
| 4050 | Freight Revenue | Revenue | Operating Revenue | Credit | Optional shipping charge revenue |
| 4060 | Sales Returns and Allowances | Revenue | Contra Revenue | Debit | Optional |
| 4070 | Sales Discounts | Revenue | Contra Revenue | Debit | Optional |
| 5000 | Cost of Goods Sold | Expense | Header | Debit | Parent summary account |
| 5010 | COGS - Furniture | Expense | COGS | Debit | Product family COGS |
| 5020 | COGS - Lighting | Expense | COGS | Debit | Product family COGS |
| 5030 | COGS - Textiles | Expense | COGS | Debit | Product family COGS |
| 5040 | COGS - Accessories | Expense | COGS | Debit | Product family COGS |
| 5050 | Freight-Out Expense | Expense | COGS | Debit | Optional shipping cost |
| 5060 | Purchase Price Variance | Expense | COGS | Debit | Unfavorable variance default side |
| 5070 | Inventory Adjustments | Expense | COGS | Debit | Shrinkage, write-downs, count differences |
| 6000 | Operating Expenses | Expense | Header | Debit | Parent summary account |
| 6010 | Salaries Expense - Sales | Expense | Operating Expense | Debit | Sales payroll |
| 6020 | Salaries Expense - Warehouse | Expense | Operating Expense | Debit | Warehouse payroll |
| 6030 | Salaries Expense - Administration | Expense | Operating Expense | Debit | Administrative payroll |
| 6040 | Salaries Expense - Customer Service | Expense | Operating Expense | Debit | Customer service payroll |
| 6050 | Salaries Expense - Executive | Expense | Operating Expense | Debit | Executive payroll |
| 6060 | Payroll Taxes and Benefits | Expense | Operating Expense | Debit | Optional |
| 6070 | Rent Expense - Warehouse | Expense | Operating Expense | Debit | Facility rent |
| 6080 | Rent Expense - Office | Expense | Operating Expense | Debit | Facility rent |
| 6090 | Utilities Expense | Expense | Operating Expense | Debit | Utilities |
| 6100 | Insurance Expense | Expense | Operating Expense | Debit | Insurance |
| 6110 | Office Supplies Expense | Expense | Operating Expense | Debit | Supplies |
| 6120 | Repairs and Maintenance Expense | Expense | Operating Expense | Debit | Maintenance |
| 6130 | Depreciation Expense | Expense | Operating Expense | Debit | Depreciation |
| 6140 | IT and Software Expense | Expense | Operating Expense | Debit | Technology spend |
| 6150 | Marketing and Promotion Expense | Expense | Operating Expense | Debit | Selling expense |
| 6160 | Travel and Entertainment Expense | Expense | Operating Expense | Debit | Optional |
| 6170 | Bad Debt Expense | Expense | Operating Expense | Debit | Optional bad debt |
| 6180 | Professional Fees Expense | Expense | Operating Expense | Debit | Legal, audit, consulting |
| 6190 | Bank Fees Expense | Expense | Operating Expense | Debit | Banking charges |
| 6200 | Miscellaneous Administrative Expense | Expense | Operating Expense | Debit | Residual admin spending |
| 6210 | Warehouse Supplies Expense | Expense | Operating Expense | Debit | Warehouse consumables |
| 6220 | Research and Development Expense | Expense | Operating Expense | Debit | Optional departmental spend |
| 7000 | Other Income and Expense | Revenue | Header | Credit | Parent summary account |
| 7010 | Interest Income | Revenue | Other Income | Credit | Optional |
| 7020 | Gain or Loss on Asset Disposal | Revenue | Other Income or Expense | Credit | Optional mixed usage |
| 7030 | Interest Expense | Expense | Other Expense | Debit | Optional |
| 7040 | Foreign Exchange Gain or Loss | Revenue | Other Income or Expense | Credit | Optional mixed usage |
| 8000 | Closing and Summary | Equity | Header | Credit | Parent summary account |
| 8010 | Income Summary | Equity | Closing | Credit | Used for year-end close |
| 8020 | Suspense and Clearing | Asset | Current Asset | Debit | Optional temporary clearing account |

### 17.3 Minimum required accounts for version 1 generator

Although the full chart above is recommended, the generator only needs a core subset to begin. The minimum required posting accounts are:

- 1010 Cash and Cash Equivalents
- 1020 Accounts Receivable
- 1040 Inventory - Finished Goods
- 2010 Accounts Payable
- 2020 Goods Received Not Invoiced
- 2050 Sales Tax Payable
- 2060 Customer Deposits and Unapplied Cash
- 3030 Retained Earnings
- 4010 through 4040 Sales Revenue by category
- 5010 through 5040 COGS by category
- 5060 Purchase Price Variance
- 6010 through 6050 Salaries Expense by department
- 6070 and 6080 Rent Expense
- 6090 Utilities Expense
- 6130 Depreciation Expense

## 18. Item-to-account mapping rules

To make automated postings deterministic, each item should map to a small account set.

### 18.1 Recommended item account fields

| Column | Description |
|---|---|
| InventoryAccountID | Inventory account used when goods are received and relieved |
| RevenueAccountID | Revenue account used when item is invoiced |
| COGSAccountID | COGS account used when item is shipped |
| PurchaseVarianceAccountID | Variance account used for invoice-to-receipt cost differences |
| TaxCategory | Determines sales tax handling |

### 18.2 Default mapping by item group

| ItemGroup | RevenueAccount | COGSAccount | InventoryAccount |
|---|---|---|---|
| Furniture | 4010 | 5010 | 1040 |
| Lighting | 4020 | 5020 | 1040 |
| Textiles | 4030 | 5030 | 1040 |
| Accessories | 4040 | 5040 | 1040 |
| Packaging | null | null | 1045 |
| Raw Materials | null | null | 1045 |

If packaging and raw materials are not sold directly, they do not need revenue or COGS mappings in version 1.

## 19. Posting matrix draft

The posting matrix maps each posting event to its debit and credit logic. This should drive the Python posting engine.

### 19.1 Posting matrix conventions

For each event, the script should define:

- triggering document and status condition
- posting date
- debit account logic
- credit account logic
- amount basis
- cost center rule
- source reference rule

The event code column below is optional but recommended for implementation.

### 19.2 Core posting matrix

| EventCode | Business Event | Trigger condition | Debit account logic | Credit account logic | Amount basis | Cost center rule | Source reference |
|---|---|---|---|---|---|---|---|
| SHIP_COGS | Shipment posting | Shipment finalized | Item.COGSAccountID | Item.InventoryAccountID | QuantityShipped x standard cost | SalesOrder cost center | Shipment and ShipmentLine |
| SI_AR_REV_TAX | Sales invoice posting | Invoice posted from Draft to Submitted or equivalent | 1020 Accounts Receivable for GrandTotal | RevenueAccountID for SubTotal and 2050 Sales Tax Payable for TaxAmount | SalesInvoice amounts | SalesOrder cost center on revenue lines, null or same on AR | SalesInvoice and SalesInvoiceLine |
| CR_CASH_AR | Cash receipt applied to invoice | Receipt recorded and linked to invoice | 1010 Cash | 1020 Accounts Receivable | Receipt amount up to applied amount | Usually null or customer sales cost center depending on design choice | CashReceipt |
| CR_CASH_UNAPPLIED | Unapplied customer cash receipt | Receipt recorded with no invoice link or excess over invoice | 1010 Cash | 2060 Customer Deposits and Unapplied Cash | Unapplied amount | Usually null | CashReceipt |
| GR_INV_GRNI | Goods receipt posting | Goods receipt finalized | Item.InventoryAccountID | 2020 Goods Received Not Invoiced | QuantityReceived x PO unit cost or standard cost | Requisition or owning cost center | GoodsReceipt and GoodsReceiptLine |
| PI_GRNI_AP | Purchase invoice matched to receipt | Purchase invoice approved with PO and receipt support | 2020 Goods Received Not Invoiced for matched receipt basis | 2010 Accounts Payable | Matched amount | Requisition or owning cost center | PurchaseInvoice and PurchaseInvoiceLine |
| PI_VAR_AP | Purchase price variance at invoice | Invoice approved and billed amount differs from accrued receipt amount | 5060 Purchase Price Variance for unfavorable difference or 2010 and 2020 adjusted for favorable difference | 2010 Accounts Payable for total invoice amount and 5060 as needed | Invoice versus accrued difference | Same as purchase cost center | PurchaseInvoice and PurchaseInvoiceLine |
| PI_DIRECT_AP | Purchase invoice without receipt | Invoice approved with no receipt or bypass exception | InventoryAccountID or assigned expense account | 2010 Accounts Payable | Invoice line amount | Requisition or owning cost center | PurchaseInvoice and PurchaseInvoiceLine |
| DP_AP_CASH | Vendor payment | Disbursement issued | 2010 Accounts Payable | 1010 Cash | Payment amount applied to AP | Usually null | DisbursementPayment |
| DP_ADVANCE_CASH | Vendor prepayment | Disbursement with no invoice link and tagged prepayment | 1070 Vendor Advances | 1010 Cash | Payment amount | Usually null | DisbursementPayment |
| JE_PAYROLL | Payroll entry | Payroll run or monthly payroll accrual | Departmental salary expense accounts and payroll taxes if used | 1010 Cash or 2030 Accrued Payroll | Payroll amount | Employee department cost centers | JournalEntry |
| JE_RENT | Rent entry | Monthly rent posting | 6070 or 6080 Rent Expense | 1010 Cash or 2040 Accrued Expenses or 2010 Accounts Payable | Rent amount | Warehouse or administration cost center | JournalEntry |
| JE_UTIL | Utilities entry | Monthly utilities posting | 6090 Utilities Expense | 1010 Cash or 2040 Accrued Expenses or 2010 Accounts Payable | Utility amount | Facility cost center | JournalEntry |
| JE_DEPR | Depreciation entry | Monthly depreciation posting | 6130 Depreciation Expense | 1150, 1160, or 1170 accumulated depreciation accounts | Depreciation schedule amount | Relevant owning cost center or null | JournalEntry |
| JE_BADDEBT | Bad debt reserve entry | Period-end reserve adjustment if used | 6170 Bad Debt Expense | 1030 Allowance for Doubtful Accounts | Policy-based reserve amount | Sales or administration | JournalEntry |
| JE_INV_ADJ | Inventory adjustment | Count adjustment or shrinkage event | 5070 Inventory Adjustments or InventoryAccountID depending on direction | InventoryAccountID or 5070 depending on direction | Adjustment amount | Warehouse cost center | JournalEntry or cycle count event |
| JE_ACCRUAL | Month-end expense accrual | Month-end closing routine | Expense account | 2040 Accrued Expenses | Accrued amount | Relevant department | JournalEntry |
| JE_REVERSAL | Reversing entry | First day of next period or early next period | Reverse prior-period accrual accounts | Reverse prior-period expense or liability accounts | Same as original | Same as original | JournalEntry with reversal link |
| JE_CLOSE_REV | Revenue close | Year-end close | Revenue accounts | 8010 Income Summary | Full year balances | Null | JournalEntry |
| JE_CLOSE_EXP | Expense close | Year-end close | 8010 Income Summary | Expense and COGS accounts | Full year balances | Null | JournalEntry |
| JE_CLOSE_RE | Net income close to retained earnings | After income summary close | 8010 Income Summary if income is credit balance or 3030 if loss balance treatment differs | 3030 Retained Earnings | Net income for year | Null | JournalEntry |

## 20. Posting logic narratives by event

### 20.1 Shipment posting

Shipment is the event that relieves inventory and recognizes cost of goods sold. The accounting date should normally be the shipment date, not the order date. Each shipment line should generate a debit to the mapped COGS account and a credit to the mapped inventory account based on quantity shipped multiplied by the standard cost effective on the posting date.

### 20.2 Sales invoice posting

Sales invoice is the revenue event in the base design. The invoice should debit accounts receivable for the full invoice total, credit the mapped revenue account for the subtotal, and credit sales tax payable for the tax amount. If discounts are embedded in line totals, no separate discount account entry is needed. If you later want cash discounts, those can be handled at collection.

### 20.3 Cash receipt posting

Cash receipts should normally credit accounts receivable when linked to a specific invoice. If the receipt has no invoice link, or if the receipt amount exceeds the applied invoice amount, the excess should credit customer deposits and unapplied cash. This improves teaching value because students can investigate unapplied cash rather than forcing every receipt into AR.

### 20.4 Goods receipt posting

Goods receipt is the inventory recognition event. The preferred teaching design is to debit inventory and credit goods received not invoiced using the purchase order unit cost for the quantity received. This makes receiving and accrual logic transparent and gives students a clean three-way match structure.

### 20.5 Purchase invoice posting

When the vendor invoice arrives and is approved, the system should clear the GRNI balance for the matched amount and recognize accounts payable. If the vendor invoice amount differs from the accrued amount, the difference should flow to purchase price variance in the main design. If you want a simpler introductory version, you can flow the difference directly to inventory, but that weakens the analytics for variance analysis.

### 20.6 Disbursement posting

Vendor disbursements normally debit accounts payable and credit cash. Duplicate payments, early payments, and payments to unauthorized vendors should remain valid accounting entries even if they are bad business process outcomes. That is important because anomaly analytics should find them through tests, not because the ledger fails.

### 20.7 Manual journals

Manual journals should cover the non-subledger activity needed for realistic statements. Monthly payroll, rent, utilities, depreciation, accruals, reversals, occasional inventory adjustments, and annual closing entries are sufficient for version 1.

## 21. Approval and authorization rules for posting design

The posting engine does not need to block improper approvals in the generated data, because some of those situations are intentional anomalies. However, it should know the normal policy.

### 21.1 Recommended approval policy

| AuthorizationLevel | Typical max approval amount |
|---|---:|
| Standard | 1,000 |
| Manager | 10,000 |
| Director | 50,000 |
| VP | 250,000 |

### 21.2 Policy usage in generation

Normal transactions should respect these thresholds. Planted anomalies may violate them in small numbers to support audit testing.

## 22. Budget account scope

Budgets do not need to cover every account. They should focus on accounts relevant for managerial analysis.

### 22.1 Recommended budgeted accounts

- Revenue accounts 4010 through 4040
- Salary expense accounts 6010 through 6050
- Rent expense accounts 6070 and 6080
- Utilities expense 6090
- Marketing expense 6150
- IT and software expense 6140
- Administrative and warehouse spending accounts 6110, 6120, 6210
- Depreciation expense 6130 if desired

This produces a manageable but analytically useful budget table.

## 23. Row-volume model by month for fiscal years 2026 through 2030

The generator should not treat transaction volumes as random independent draws. It should follow a structured monthly operating model with seasonality, moderate growth, and realistic document conversion rates. This section defines a practical volume model for the five-year dataset.

## 23.1 Planning assumptions

The volume model is built on five assumptions.

First, Greenfield operates continuously across all twelve months, but activity is seasonal. Demand rises in late spring and peaks in the holiday and year-end selling season. Purchasing activity leads sales activity slightly because inventory must be positioned before shipment.

Second, the company experiences moderate year-over-year growth. A reasonable base assumption is approximately 6 percent annual growth in O2C volume and approximately 5 percent annual growth in P2P volume.

Third, not every operational document converts one-for-one into the next document. Some orders are cancelled, some orders are partially shipped, some shipments produce partial invoicing, and some invoices are settled through multiple cash receipts.

Fourth, the purchasing cycle should support replenishment of expected sales activity plus general operating purchases. As a result, purchase requisitions and purchase orders should be directionally correlated with sales trends, but not perfectly proportional.

Fifth, manual journal entries should occur at regular cadence independent of transactional spikes. Payroll, rent, utilities, depreciation, accruals, reversals, and closing entries create a stable baseline of accounting volume throughout the year.

## 23.2 Annual target volumes by major table

The table below gives target values by fiscal year. The generator may randomize modestly around these values, but the totals should remain close to plan.

| FiscalYear | SalesOrder | SalesOrderLine | Shipment | ShipmentLine | SalesInvoice | SalesInvoiceLine | CashReceipt | PurchaseRequisition | PurchaseOrder | PurchaseOrderLine | GoodsReceipt | GoodsReceiptLine | PurchaseInvoice | PurchaseInvoiceLine | DisbursementPayment | JournalEntry | GLEntry target |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026 | 4,800 | 14,400 | 4,450 | 13,350 | 4,500 | 13,500 | 4,300 | 2,700 | 2,350 | 7,050 | 2,250 | 6,750 | 2,250 | 6,750 | 2,450 | 190 | 63,000 |
| 2027 | 5,100 | 15,300 | 4,750 | 14,250 | 4,800 | 14,400 | 4,600 | 2,850 | 2,500 | 7,500 | 2,400 | 7,200 | 2,400 | 7,200 | 2,600 | 195 | 67,000 |
| 2028 | 5,400 | 16,200 | 5,050 | 15,150 | 5,100 | 15,300 | 4,900 | 3,000 | 2,650 | 7,950 | 2,550 | 7,650 | 2,550 | 7,650 | 2,750 | 200 | 71,000 |
| 2029 | 5,750 | 17,250 | 5,350 | 16,050 | 5,450 | 16,350 | 5,250 | 3,150 | 2,825 | 8,475 | 2,725 | 8,175 | 2,725 | 8,175 | 2,925 | 205 | 76,000 |
| 2030 | 6,100 | 18,300 | 5,700 | 17,100 | 5,800 | 17,400 | 5,600 | 3,325 | 3,000 | 9,000 | 2,900 | 8,700 | 2,900 | 8,700 | 3,100 | 210 | 81,000 |

## 23.3 Five-year cumulative target volumes

Using the annual targets above, the cumulative five-year dataset would approximate the following row counts.

| Table | Five-year target rows |
|---|---:|
| SalesOrder | 27,150 |
| SalesOrderLine | 81,450 |
| Shipment | 25,300 |
| ShipmentLine | 75,900 |
| SalesInvoice | 25,650 |
| SalesInvoiceLine | 76,950 |
| CashReceipt | 24,650 |
| PurchaseRequisition | 15,025 |
| PurchaseOrder | 13,325 |
| PurchaseOrderLine | 39,975 |
| GoodsReceipt | 12,825 |
| GoodsReceiptLine | 38,475 |
| PurchaseInvoice | 12,825 |
| PurchaseInvoiceLine | 38,475 |
| DisbursementPayment | 13,825 |
| JournalEntry | 1,000 |
| GLEntry | 358,000 |

With master and organizational tables included, the full database should land roughly in the neighborhood of 840,000 to 860,000 total rows.

## 23.4 Monthly seasonality model

The generator should not spread annual volume evenly across the year. Instead, it should apply monthly weights.

### 23.4.1 Recommended O2C monthly weights

| Month | Weight |
|---|---:|
| January | 0.070 |
| February | 0.072 |
| March | 0.078 |
| April | 0.080 |
| May | 0.084 |
| June | 0.086 |
| July | 0.082 |
| August | 0.080 |
| September | 0.082 |
| October | 0.090 |
| November | 0.097 |
| December | 0.099 |

### 23.4.2 Recommended P2P monthly weights

| Month | Weight |
|---|---:|
| January | 0.074 |
| February | 0.075 |
| March | 0.080 |
| April | 0.082 |
| May | 0.086 |
| June | 0.088 |
| July | 0.084 |
| August | 0.082 |
| September | 0.086 |
| October | 0.091 |
| November | 0.089 |
| December | 0.083 |

### 23.4.3 Recommended manual journal cadence

Manual journal entries should follow a steadier cadence.

- Payroll-related entries: biweekly or semi-monthly
- Rent: monthly
- Utilities: monthly
- Depreciation: monthly
- Accruals: month-end
- Reversals: first few days of next month where applicable
- Year-end close: December and early January

## 23.5 Document conversion ratios

The generator should use realistic conversion relationships rather than forcing all documents to reconcile one-to-one.

### 23.5.1 Order-to-cash conversion assumptions

| Relationship | Recommended base ratio | Interpretation |
|---|---:|---|
| SalesOrder to Shipment | 0.93 | Most orders ship, some cancel or remain open |
| Shipment to SalesInvoice | 1.01 | Near one-to-one, with occasional split or catch-up invoicing |
| SalesInvoice to CashReceipt | 0.96 | Some invoices fully settle in one payment, others in multiple or late payments |
| SalesOrderLine per SalesOrder | 3.0 | Average line density |
| ShipmentLine per Shipment | 3.0 | Average shipment line density |
| SalesInvoiceLine per SalesInvoice | 3.0 | Average invoice line density |

### 23.5.2 Procure-to-pay conversion assumptions

| Relationship | Recommended base ratio | Interpretation |
|---|---:|---|
| PurchaseRequisition to PurchaseOrder | 0.87 | Some approved requisitions do not convert |
| PurchaseOrder to GoodsReceipt | 0.96 | Most POs are received, some remain open or cancel |
| GoodsReceipt to PurchaseInvoice | 1.00 | Roughly one-to-one in the base design |
| PurchaseInvoice to DisbursementPayment | 1.08 | Some invoices settled with multiple payments |
| PurchaseOrderLine per PurchaseOrder | 3.0 | Average line density |
| GoodsReceiptLine per GoodsReceipt | 3.0 | Average receipt line density |
| PurchaseInvoiceLine per PurchaseInvoice | 3.0 | Average invoice line density |

## 23.6 Monthly base counts for 2026

The 2026 plan below provides a concrete monthly blueprint. Later years should apply the annual growth assumptions while preserving similar seasonal shapes.

### 23.6.1 O2C monthly base counts for 2026

| Month | SalesOrder | SalesOrderLine | Shipment | ShipmentLine | SalesInvoice | SalesInvoiceLine | CashReceipt |
|---|---:|---:|---:|---:|---:|---:|---:|
| January | 336 | 1,008 | 312 | 936 | 315 | 945 | 301 |
| February | 346 | 1,038 | 321 | 963 | 324 | 972 | 310 |
| March | 374 | 1,122 | 347 | 1,041 | 351 | 1,053 | 335 |
| April | 384 | 1,152 | 356 | 1,068 | 360 | 1,080 | 344 |
| May | 403 | 1,209 | 374 | 1,122 | 378 | 1,134 | 361 |
| June | 413 | 1,239 | 383 | 1,149 | 387 | 1,161 | 370 |
| July | 394 | 1,182 | 365 | 1,095 | 369 | 1,107 | 353 |
| August | 384 | 1,152 | 356 | 1,068 | 360 | 1,080 | 344 |
| September | 394 | 1,182 | 365 | 1,095 | 369 | 1,107 | 353 |
| October | 432 | 1,296 | 401 | 1,203 | 405 | 1,215 | 387 |
| November | 466 | 1,398 | 432 | 1,296 | 437 | 1,311 | 417 |
| December | 474 | 1,422 | 438 | 1,314 | 445 | 1,335 | 425 |

### 23.6.2 P2P monthly base counts for 2026

| Month | PurchaseRequisition | PurchaseOrder | PurchaseOrderLine | GoodsReceipt | GoodsReceiptLine | PurchaseInvoice | PurchaseInvoiceLine | DisbursementPayment |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| January | 200 | 174 | 522 | 167 | 501 | 167 | 501 | 181 |
| February | 203 | 176 | 528 | 169 | 507 | 169 | 507 | 184 |
| March | 216 | 188 | 564 | 180 | 540 | 180 | 540 | 196 |
| April | 221 | 193 | 579 | 185 | 555 | 185 | 555 | 201 |
| May | 232 | 202 | 606 | 194 | 582 | 194 | 582 | 210 |
| June | 238 | 207 | 621 | 198 | 594 | 198 | 594 | 215 |
| July | 227 | 197 | 591 | 189 | 567 | 189 | 567 | 205 |
| August | 221 | 193 | 579 | 185 | 555 | 185 | 555 | 201 |
| September | 232 | 202 | 606 | 194 | 582 | 194 | 582 | 210 |
| October | 246 | 214 | 642 | 205 | 615 | 205 | 615 | 222 |
| November | 240 | 209 | 627 | 200 | 600 | 200 | 600 | 217 |
| December | 224 | 195 | 585 | 187 | 561 | 187 | 561 | 198 |

## 23.7 Growth rules for 2027 through 2030

The generator should not hardcode separate monthly tables for every year. Instead, it should apply controlled growth factors to the 2026 base pattern.

| FiscalYear | O2C growth factor vs prior year | P2P growth factor vs prior year | Manual journal growth factor |
|---|---:|---:|---:|
| 2027 | 1.06 | 1.05 | 1.03 |
| 2028 | 1.06 | 1.05 | 1.03 |
| 2029 | 1.065 | 1.055 | 1.025 |
| 2030 | 1.06 | 1.06 | 1.025 |

For each month in each fiscal year, the generator should start with the annual target for the relevant event, apply the monthly seasonality weight, round to an integer count, apply small bounded random noise such as plus or minus 3 percent, and then reconcile the monthly counts back to the annual total.

## 23.8 Monthly GL posting volume logic

GLEntry counts should be modeled from posting events rather than assigned arbitrarily.

| Event | Typical GL lines |
|---|---:|
| ShipmentLine posting | 2 |
| SalesInvoice posting | 2 to 3 |
| CashReceipt posting | 2 |
| GoodsReceiptLine posting | 2 |
| PurchaseInvoice posting | 2 to 4 |
| DisbursementPayment posting | 2 |
| Manual journal | 2 to 6 |

Because invoice and purchase variance logic can create extra lines, total GL volume should emerge naturally from event counts plus manual journals. The annual GLEntry targets listed earlier are therefore control totals, not independent inputs.

## 23.9 Anomaly allocation rule by year and month

Anomalies should be distributed across all five years rather than concentrated in one year. However, some anomalies should intentionally cluster near quarter-end and year-end.

Recommended pattern:

- Revenue cut-off exceptions should concentrate in March, June, September, and December, especially in the last five calendar days of those months
- Reversing entries should cluster in late December and early January
- Duplicate payments should be spread lightly across all years
- Threshold-adjacent approvals should be spread lightly across all years
- Unapproved or same-person approval anomalies should be spread lightly across all years

## 24. Python data-generation blueprint for fiscal years 2026 through 2030

This section translates the schema, posting rules, and row-volume plan into an implementation blueprint for the Python generator. The objective is not only to create rows, but to create a coherent accounting database that remains reproducible, balanced, and teachable.

## 24.1 Design objectives for the generator

The generator should satisfy seven design objectives.

First, it must be reproducible. The same seed should produce the same database.

Second, it must be modular. Each business area should be generated through separate functions or classes.

Third, it must be internally consistent. Source documents, line totals, and GL postings must reconcile.

Fourth, it must support controlled randomness. Counts, dates, prices, quantities, and customer behavior should vary, but within bounded rules.

Fifth, it must separate clean generation from anomaly injection.

Sixth, it must support export to both SQLite and Excel.

Seventh, it must produce a validation report so the dataset can be trusted for classroom use.

## 24.2 Recommended project structure

A practical folder structure for the generator is shown below.

```text
greenfield_dataset/
│
├── config/
│   ├── settings.yaml
│   ├── accounts.csv
│   ├── cost_centers.csv
│   ├── item_groups.csv
│   └── anomaly_profile.yaml
│
├── data_generator/
│   ├── __init__.py
│   ├── main.py
│   ├── schema.py
│   ├── utils.py
│   ├── calendar.py
│   ├── ids.py
│   ├── master_data.py
│   ├── budgets.py
│   ├── o2c.py
│   ├── p2p.py
│   ├── journals.py
│   ├── posting_engine.py
│   ├── anomalies.py
│   ├── validations.py
│   └── exporters.py
│
├── outputs/
│   ├── greenfield_2026_2030.sqlite
│   ├── greenfield_2026_2030.xlsx
│   └── validation_report.json
│
└── notebooks/
    ├── 01_smoke_test.ipynb
    └── 02_teaching_queries.ipynb
```

This structure keeps generation logic separate from configuration, testing, and outputs.

## 24.3 Recommended technology stack

The generator should use a conventional Python analytics stack.

| Component | Recommendation | Purpose |
|---|---|---|
| Python version | 3.11 or later | Stable modern Python |
| Dataframes | pandas | Table generation and export |
| Numeric operations | numpy | Controlled random generation |
| Fake names and addresses | Faker | Realistic customer, supplier, and employee data |
| Database write | sqlite3 or SQLAlchemy | SQLite export |
| Workbook write | pandas with openpyxl or xlsxwriter | Excel export |
| Config management | yaml | Parameterization |
| Validation output | json | Reconciliation and audit trail |

For this project, pandas plus sqlite3 is sufficient and keeps the implementation readable for students and instructors.

## 24.4 Core configuration model

The generator should be driven by a small set of configuration parameters rather than hardcoded assumptions.

### 24.4.1 Suggested settings fields

| Setting | Example value | Purpose |
|---|---|---|
| random_seed | 20260401 | Reproducibility |
| fiscal_year_start | 2026-01-01 | Base calendar |
| fiscal_year_end | 2030-12-31 | End calendar |
| warehouse_count | 2 | Warehouse generation |
| employee_count | 64 | Company size |
| customer_count | 220 | Customer master size |
| supplier_count | 110 | Supplier master size |
| item_count | 240 | Item master size |
| tax_rate | 0.065 | Sales tax logic |
| o2c_growth_profile | year-specific factors | Sales growth |
| p2p_growth_profile | year-specific factors | Purchasing growth |
| anomaly_mode | standard | Controls anomaly density |
| export_excel | true | Output control |
| export_sqlite | true | Output control |

These settings should be loaded once at runtime and passed to the major generator functions.

## 24.5 Generation order and dependency sequence

The generator must follow a strict dependency order because later tables rely on earlier master data and earlier operational documents.

### 24.5.1 Recommended execution sequence

1. Initialize seed, config, and date calendar
2. Create schema metadata and empty table containers
3. Generate cost centers
4. Generate employees
5. Generate warehouses
6. Generate accounts
7. Generate items and item-account mappings
8. Generate customers
9. Generate suppliers
10. Generate opening balances and opening journal entries as of January 1, 2026
11. Generate budgets for 2026 through 2030
12. Generate O2C transactions month by month
13. Generate P2P transactions month by month
14. Generate recurring manual journal entries
15. Post all source transactions and journals to GLEntry
16. Run clean validation suite
17. Inject anomalies
18. Recalculate affected tables and related GL where needed
19. Run post-anomaly validation suite
20. Export SQLite, Excel, and validation report

This order should not be altered casually, because many tables depend on earlier identifiers and balances.

## 24.6 Table generation architecture

A good implementation pattern is to maintain one in-memory dataframe per table until validation is complete. SQLite writing should happen only after the clean and post-anomaly checks pass.

### 24.6.1 Suggested central object model

The generator can be organized around a simple context object.

```python
class GenerationContext:
    config: dict
    rng: np.random.Generator
    calendar: pd.DataFrame
    tables: dict[str, pd.DataFrame]
    validation_results: dict
    counters: dict[str, int]
```

This context object allows each module to read from and write to a shared state without using global variables.

### 24.6.2 Identifier generation

Each table should use deterministic sequential integer IDs and formatted business document numbers.

| Table | Integer PK | Business number example |
|---|---|---|
| JournalEntry | JournalEntryID | JE-2026-000001 |
| SalesOrder | SalesOrderID | SO-2026-000001 |
| Shipment | ShipmentID | SH-2026-000001 |
| SalesInvoice | SalesInvoiceID | SI-2026-000001 |
| CashReceipt | CashReceiptID | CR-2026-000001 |
| PurchaseRequisition | RequisitionID | PR-2026-000001 |
| PurchaseOrder | PurchaseOrderID | PO-2026-000001 |
| GoodsReceipt | GoodsReceiptID | GR-2026-000001 |
| PurchaseInvoice | PurchaseInvoiceID | PI-2026-000001 |
| DisbursementPayment | DisbursementID | DP-2026-000001 |

The formatted business number is important for teaching queries and audit-style document tracing.

## 24.7 Master data generation blueprint

Master data should be generated first and should remain stable across the five-year period, with only limited deactivation where needed.

### 24.7.1 Cost centers

Generate 8 to 14 cost centers with a simple hierarchy. Example centers include Sales, Warehouse, Purchasing, Administration, Customer Service, Executive, and Research and Development.

### 24.7.2 Employees

Generate 55 to 75 employees with departments, managers, authorization levels, and approval limits. Managers should align to cost centers. Email addresses should use a company domain such as greenfieldhf.com.

### 24.7.3 Warehouses

Generate two warehouses by default, for example Main Warehouse and East Distribution Center.

### 24.7.4 Accounts

Load the chart of accounts from configuration rather than randomly generating it.

### 24.7.5 Items

Generate 180 to 350 items distributed across Furniture, Lighting, Textiles, Accessories, Packaging, and Raw Materials. Each item should carry standard cost, list price, and account mappings. Sellable items should dominate the catalog.

### 24.7.6 Customers

Generate 150 to 300 customers with regions, terms, credit limits, and assigned sales reps. Customer size tiers should drive order frequency and order values.

### 24.7.7 Suppliers

Generate 80 to 160 suppliers with payment terms, approval flags, risk ratings, and address details. Certain suppliers should specialize by item group.

## 24.8 Opening balance design

The dataset should begin with an opening balance journal as of January 1, 2026. This is necessary so the company does not start from zero.

### 24.8.1 Minimum opening balance accounts

- Cash
- Accounts Receivable
- Inventory
- Fixed assets
- Accumulated depreciation
- Accounts Payable
- Accrued expenses
- Retained earnings

### 24.8.2 Opening balance principles

Opening balances should be reasonable relative to the 2026 transaction scale. For example, beginning inventory should support one to two months of expected early-year shipments. Beginning AR and AP should represent outstanding late-2025 activity. Retained earnings should balance the opening entry.

## 24.9 O2C generation blueprint

The O2C generator should create monthly transactional activity using customer tiers, product preferences, seasonality, and conversion rules.

### 24.9.1 O2C monthly generation order

For each month:

1. generate sales orders
2. generate sales order lines
3. determine which orders are cancelled, open, partial, or fulfilled
4. generate shipments and shipment lines for fulfillable quantities
5. generate sales invoices and invoice lines from shipment activity
6. generate cash receipts from invoice aging and customer payment behavior
7. update customer AR balances in the simulation layer

### 24.9.2 Sales order logic

Sales orders should be driven by customer tier and seasonality. Large customers should order more frequently and with larger baskets. Item selection should be weighted by customer segment and product family.

### 24.9.3 Shipment logic

Shipments should normally occur 1 to 10 days after order date. Partial shipments should be common enough to support realistic fulfillment analysis. Returned shipments should be rare.

### 24.9.4 Invoice logic

Invoices should normally follow shipment date on the same day or within a few days. The generator should preserve normal revenue recognition logic, then later inject selected cut-off exceptions.

### 24.9.5 Cash receipt logic

Receipt timing should depend on customer payment terms and customer behavior. Some customers should pay early, many on time, and some late. A small share of invoices should be settled in multiple receipts.

## 24.10 P2P generation blueprint

The P2P generator should create replenishment and operating purchases tied to expected demand and departmental spending.

### 24.10.1 P2P monthly generation order

For each month:

1. generate purchase requisitions by department and item need
2. convert most approved requisitions to purchase orders
3. generate purchase order lines
4. generate goods receipts and goods receipt lines from PO activity
5. generate purchase invoices and invoice lines from receipt activity
6. generate disbursement payments from AP aging and payment policy
7. update supplier AP balances in the simulation layer

### 24.10.2 Requisition logic

Requisitions should be generated from two demand streams: inventory replenishment and operating needs. Inventory replenishment should respond to expected sales volume and target coverage. Operating requisitions should support warehouse and administrative spending.

### 24.10.3 Purchase order logic

Approved requisitions should usually convert to POs within a few days. Suppliers should be selected from weighted eligible suppliers by item group. Blanket POs without requisitions should be rare and mostly reserved for planted exceptions.

### 24.10.4 Goods receipt logic

Receipts should normally occur after PO date and before invoice date. Lead time should vary by supplier type. Domestic suppliers should have shorter lead times than international suppliers.

### 24.10.5 Purchase invoice logic

Vendor invoices should generally arrive near the receipt date, with some lag. Approved invoices should create AP and clear GRNI. Small price differences should occur naturally even before anomaly injection if you want normal operational noise.

### 24.10.6 Disbursement logic

Payment timing should depend on terms, cash policy, and invoice aging. Some invoices should be split across two payments. Duplicate payments should not appear in the clean base data.

## 24.11 Manual journal blueprint

Manual journals should be generated as a separate module rather than being embedded in O2C or P2P logic.

### 24.11.1 Journal categories

- Opening balance journal
- Payroll journals
- Rent journals
- Utilities journals
- Depreciation journals
- Month-end accrual journals
- Reversing journals
- Inventory adjustment journals
- Year-end closing journals

### 24.11.2 Suggested volume rules

A reasonable pattern is 15 to 18 journal headers per month, plus year-end close and occasional correcting entries. This produces the planned annual journal totals.

## 24.12 Posting engine blueprint

The posting engine should not be scattered across modules. A centralized posting engine should read source tables and produce GLEntry rows according to the posting matrix.

### 24.12.1 Recommended posting engine interface

```python
def post_all_transactions(context: GenerationContext) -> pd.DataFrame:
    ...
```

Internally, the engine should call event-specific posting functions.

```python
def post_shipments(...):
    ...

def post_sales_invoices(...):
    ...

def post_cash_receipts(...):
    ...

def post_goods_receipts(...):
    ...

def post_purchase_invoices(...):
    ...

def post_disbursements(...):
    ...

def post_manual_journals(...):
    ...
```

### 24.12.2 Posting engine requirements

Every GL row should include at least the following:

- GLEntryID
- PostingDate
- AccountID
- Debit
- Credit
- VoucherType
- VoucherNumber
- SourceDocumentType
- SourceDocumentID
- SourceLineID
- CostCenterID
- Description
- CreatedByEmployeeID
- CreatedDate
- FiscalYear
- FiscalPeriod

### 24.12.3 Balance checks at posting time

Each voucher should be checked immediately after posting. If debits do not equal credits, the generator should raise an error before continuing.

## 24.13 Inventory simulation layer

A minimal inventory simulation layer is needed so shipments do not exceed available stock too often and purchases are directionally sensible.

### 24.13.1 Recommended approach

Maintain an inventory position by item and warehouse with these running fields:

- beginning_on_hand
- receipts
- shipments
- ending_on_hand
- reorder_point
- target_stock_days

This does not need to become a full ERP inventory engine. It only needs to keep the flows plausible and prevent obvious contradictions.

## 24.14 Pricing and quantity generation rules

The generator should use bounded distributions rather than uniform random draws.

### 24.14.1 Sales quantities

Use item-group-specific quantity ranges. Accessories and textiles may have larger quantities, while furniture may have smaller quantities with higher unit prices.

### 24.14.2 Sales pricing

Start from list price, then apply customer-tier-specific discounts. Keep realized sales prices within a reasonable band around list price.

### 24.14.3 Purchase quantities and costs

Use PO quantities large enough to support warehouse stocking logic. Purchase cost should center around standard cost, with mild natural variation.

## 24.15 Randomization strategy

The generator should be stochastic but controlled.

### 24.15.1 Recommended randomization rules

- Use one master seed at runtime
- Derive child seeds by module if needed
- Use weighted sampling rather than uniform sampling for customers, suppliers, and items
- Add bounded noise rather than unrestricted random draws
- Reconcile counts after random generation so annual targets are preserved

This approach gives variation without losing reproducibility.

## 24.16 Anomaly injection blueprint

Anomalies should be applied only after the clean dataset passes validation.

### 24.16.1 Two-phase anomaly model

Phase 1 creates a clean operational and accounting dataset.

Phase 2 copies the clean dataset in memory and modifies selected rows or inserts targeted exceptions.

### 24.16.2 Example anomaly functions

```python
def inject_weekend_journal_entries(...):
    ...

def inject_same_creator_approver(...):
    ...

def inject_invoice_before_shipment(...):
    ...

def inject_duplicate_vendor_payments(...):
    ...

def inject_threshold_adjacent_amounts(...):
    ...
```

### 24.16.3 Anomaly logging

Every injected anomaly should also be written to a control log with:

- anomaly_type
- table_name
- primary_key_value
- fiscal_year
- description
- expected_detection_test

This will be extremely useful for instructor materials.

## 24.17 Validation blueprint

Validation should be treated as a first-class module, not an afterthought.

### 24.17.1 Validation categories

| Category | Example checks |
|---|---|
| Structural | primary key uniqueness, foreign key integrity, valid status values |
| Numeric | header equals line totals, nonnegative quantities where expected |
| Accounting | voucher balance, trial balance equality, subledger reconciliation |
| Process | shipment after order, invoice after shipment in clean data, receipt after PO in clean data |
| Policy | approval amount vs employee authorization in clean data |
| Anomaly control | anomaly counts equal planned counts |

### 24.17.2 Minimum validation outputs

The validation module should produce:

- row counts by table
- count of nulls in critical fields
- duplicate key checks
- balancing exceptions by voucher
- AR to GL reconciliation by month
- AP to GL reconciliation by month
- inventory movement to GL reconciliation by month
- anomaly summary counts

## 24.18 Export blueprint

Exports should be produced only after post-anomaly validation completes.

### 24.18.1 SQLite export

Write each table to SQLite with explicit column types and indexes on major foreign keys and document numbers.

### 24.18.2 Excel export

Write one worksheet per table plus a validation summary sheet and optionally an anomaly log sheet.

### 24.18.3 Recommended indexes in SQLite

At minimum, create indexes on:

- PostingDate in GLEntry
- AccountID in GLEntry
- VoucherType and VoucherNumber in GLEntry
- CustomerID in SalesOrder, SalesInvoice, CashReceipt
- SupplierID in PurchaseOrder, PurchaseInvoice, DisbursementPayment
- SalesOrderID, PurchaseOrderID, SalesInvoiceID, PurchaseInvoiceID in their related line tables

This will keep teaching queries responsive.

## 24.19 Main orchestration pseudocode

```python
def build_dataset(config_path: str):
    config = load_config(config_path)
    context = initialize_context(config)

    create_empty_tables(context)
    generate_cost_centers(context)
    generate_employees(context)
    generate_warehouses(context)
    load_accounts(context)
    generate_items(context)
    generate_customers(context)
    generate_suppliers(context)
    generate_opening_balances(context)
    generate_budgets(context)

    for year in range(2026, 2031):
        for month in range(1, 13):
            generate_month_o2c(context, year, month)
            generate_month_p2p(context, year, month)
            generate_month_manual_journals(context, year, month)

    post_all_transactions(context)
    validate_clean_dataset(context)
    inject_anomalies(context)
    revalidate_dataset(context)
    export_sqlite(context)
    export_excel(context)
    export_validation_report(context)

    return context
```

## 25. Table-by-table field dictionary and implementation notes

This section converts the schema into an implementation-ready field dictionary. The goal is to eliminate ambiguity before coding begins. For each table, the design should specify final column names, intended Python and SQLite datatypes, nullability, key constraints, controlled vocabularies where needed, and important derivation notes.

## 25.1 Data typing conventions

The generator should use a consistent typing model across all tables.

| Logical type | Python representation | SQLite type | Notes |
|---|---|---|---|
| integer | int | INTEGER | Primary keys and most foreign keys |
| decimal money | Decimal or float rounded to 2 | NUMERIC | Round to 2 decimals before export |
| decimal quantity | float rounded to 2 or 3 | NUMERIC | Use for shipped and received quantities if partials are allowed |
| text short | str | TEXT | Codes, statuses, short descriptors |
| text long | str | TEXT | Notes and narratives |
| date | ISO string YYYY-MM-DD | TEXT | SQLite date storage |
| datetime | ISO string YYYY-MM-DD HH:MM:SS | TEXT | Created and approval timestamps |
| boolean flag | int | INTEGER | Store as 1 or 0 |

### 25.1.1 General implementation rules

- All primary keys should be integer surrogate keys generated sequentially.
- All business document numbers should be stored as text.
- All money fields should be rounded to two decimals.
- All status fields should use controlled enumerations.
- All foreign keys should use integer IDs, not free text.
- All created and approved timestamps should be plausible relative to the business event date.

## 25.2 Accounting core tables

### 25.2.1 Account

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| AccountID | integer | No | PK | Sequential surrogate key |
| AccountNumber | text short | No | Unique | Four-digit or structured code, unique |
| AccountName | text short | No |  | Descriptive account label |
| AccountType | text short | No |  | One of Asset, Liability, Equity, Revenue, Expense |
| AccountSubType | text short | No |  | Controlled subtype vocabulary |
| ParentAccountID | integer | Yes | FK -> Account | Null for top-level parents |
| NormalBalance | text short | No |  | One of Debit or Credit |
| IsActive | boolean flag | No |  | 1 or 0 |

Implementation notes: Load this table from configuration rather than generating randomly. Enforce uniqueness on AccountNumber.

### 25.2.2 JournalEntry

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| JournalEntryID | integer | No | PK | Sequential key |
| EntryNumber | text short | No | Unique | Format JE-YYYY-NNNNNN |
| PostingDate | date | No |  | Effective accounting date |
| EntryType | text short | No |  | One of Standard, Adjusting, Closing, Correcting, Reversing, Opening |
| Description | text long | No |  | Narrative reason for entry |
| TotalAmount | decimal money | No |  | Total debits equals total credits |
| CreatedByEmployeeID | integer | No | FK -> Employee | Creator of the entry |
| CreatedDate | datetime | No |  | On or before approval date if approved |
| ApprovedByEmployeeID | integer | Yes | FK -> Employee | Null only for selected anomalies or pending status designs |
| ApprovedDate | datetime | Yes |  | Null when not approved |
| ReversesJournalEntryID | integer | Yes | FK -> JournalEntry | Used for reversing entries |

Implementation notes: JournalEntry is a header only. All lines live in GLEntry. EntryType should be enforced through a small vocabulary.

### 25.2.3 GLEntry

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| GLEntryID | integer | No | PK | Sequential key |
| PostingDate | date | No |  | Accounting date |
| AccountID | integer | No | FK -> Account | Referenced account |
| Debit | decimal money | No |  | Nonnegative, 0 if credit line |
| Credit | decimal money | No |  | Nonnegative, 0 if debit line |
| VoucherType | text short | No |  | One of JournalEntry, Shipment, SalesInvoice, CashReceipt, GoodsReceipt, PurchaseInvoice, DisbursementPayment |
| VoucherNumber | text short | No |  | Business document number |
| SourceDocumentType | text short | No |  | Mirrors logical source document |
| SourceDocumentID | integer | No |  | Source header key |
| SourceLineID | integer | Yes |  | Source line key where applicable |
| CostCenterID | integer | Yes | FK -> CostCenter | Null allowed for control-account lines when needed |
| Description | text long | No |  | Posting description |
| CreatedByEmployeeID | integer | No | FK -> Employee | User or system proxy employee |
| CreatedDate | datetime | No |  | Timestamp of posting generation |
| FiscalYear | integer | No |  | 2026 to 2030 |
| FiscalPeriod | integer | No |  | 1 through 12 |

Implementation notes: Exactly one of Debit and Credit must be positive for each row. Voucher-level balancing should be enforced in validation.

## 25.3 Order-to-cash tables

### 25.3.1 Customer

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| CustomerID | integer | No | PK | Sequential key |
| CustomerName | text short | No |  | Company name |
| ContactName | text short | No |  | Primary contact |
| Address | text long | No |  | Street address |
| City | text short | No |  | City |
| State | text short | No |  | State or province |
| PostalCode | text short | No |  | Postal code |
| Country | text short | No |  | Country |
| Phone | text short | No |  | Phone |
| Email | text short | No |  | Email |
| CreditLimit | decimal money | No |  | Positive value |
| PaymentTerms | text short | No |  | One of Net 30, Net 45, Net 60, Net 90 |
| CustomerSince | date | No |  | On or before 2030 |
| SalesRepEmployeeID | integer | No | FK -> Employee | Assigned sales rep |
| CustomerSegment | text short | Yes |  | Optional segmentation field |
| Industry | text short | Yes |  | Optional field |
| Region | text short | Yes |  | Optional field |
| IsActive | boolean flag | No |  | 1 or 0 |

Implementation notes: Customer tiers should drive ordering frequency, average basket size, and payment behavior.

### 25.3.2 SalesOrder

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| SalesOrderID | integer | No | PK | Sequential key |
| OrderNumber | text short | No | Unique | Format SO-YYYY-NNNNNN |
| OrderDate | date | No |  | Business order date |
| CustomerID | integer | No | FK -> Customer | Customer placing order |
| RequestedDeliveryDate | date | No |  | Normally on or after OrderDate |
| Status | text short | No |  | One of Open, Partially Shipped, Shipped, Invoiced, Closed, Cancelled |
| SalesRepEmployeeID | integer | No | FK -> Employee | Responsible rep |
| CostCenterID | integer | No | FK -> CostCenter | Sales department or channel |
| OrderTotal | decimal money | No |  | Sum of line totals |
| Notes | text long | Yes |  | Optional special instructions |

Implementation notes: OrderTotal is derived from SalesOrderLine. Status should be determined after downstream fulfillment and billing generation.

### 25.3.3 SalesOrderLine

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| SalesOrderLineID | integer | No | PK | Sequential key |
| SalesOrderID | integer | No | FK -> SalesOrder | Parent order |
| LineNumber | integer | No |  | Starts at 1 within order |
| ItemID | integer | No | FK -> Item | Ordered item |
| Quantity | decimal quantity | No |  | Positive quantity |
| UnitPrice | decimal money | No |  | After price policy but before discount impact in line total formula |
| Discount | decimal quantity | No |  | 0.00 to 0.35 typical band |
| LineTotal | decimal money | No |  | Quantity x UnitPrice x (1 - Discount) |

Implementation notes: LineTotal is derived. Item mix should reflect customer preferences and item availability logic.

### 25.3.4 Shipment

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| ShipmentID | integer | No | PK | Sequential key |
| ShipmentNumber | text short | No | Unique | Format SH-YYYY-NNNNNN |
| SalesOrderID | integer | No | FK -> SalesOrder | Source order |
| ShipmentDate | date | No |  | Normally on or after OrderDate |
| WarehouseID | integer | No | FK -> Warehouse | Shipping location |
| ShippedBy | text short | No |  | Carrier or internal fleet descriptor |
| TrackingNumber | text short | Yes |  | Nullable for certain internal deliveries |
| Status | text short | No |  | One of In Transit, Delivered, Returned |
| DeliveryDate | date | Yes |  | Null if not yet delivered |

Implementation notes: One sales order may have multiple shipments. Shipment status should reflect downstream delivery outcome.

### 25.3.5 ShipmentLine

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| ShipmentLineID | integer | No | PK | Sequential key |
| ShipmentID | integer | No | FK -> Shipment | Parent shipment |
| SalesOrderLineID | integer | No | FK -> SalesOrderLine | Source order line |
| LineNumber | integer | No |  | Starts at 1 within shipment |
| ItemID | integer | No | FK -> Item | Shipped item |
| QuantityShipped | decimal quantity | No |  | Positive quantity |
| ExtendedStandardCost | decimal money | No |  | QuantityShipped x item standard cost |

Implementation notes: ShipmentLine drives shipment-based COGS postings. In the clean dataset, cumulative shipped quantity for an order line should not exceed ordered quantity.

### 25.3.6 SalesInvoice

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| SalesInvoiceID | integer | No | PK | Sequential key |
| InvoiceNumber | text short | No | Unique | Format SI-YYYY-NNNNNN |
| InvoiceDate | date | No |  | Normally on or after ShipmentDate |
| DueDate | date | No |  | Based on PaymentTerms |
| SalesOrderID | integer | No | FK -> SalesOrder | Source order |
| CustomerID | integer | No | FK -> Customer | Billed customer |
| SubTotal | decimal money | No |  | Sum of invoice line totals |
| TaxAmount | decimal money | No |  | Based on tax policy |
| GrandTotal | decimal money | No |  | SubTotal + TaxAmount |
| Status | text short | No |  | One of Draft, Submitted, Paid, Partially Paid, Overdue, Cancelled |
| PaymentDate | date | Yes |  | Full settlement date only |

Implementation notes: Status should be derived from receipt application status and due date. PaymentDate should remain null until fully paid.

### 25.3.7 SalesInvoiceLine

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| SalesInvoiceLineID | integer | No | PK | Sequential key |
| SalesInvoiceID | integer | No | FK -> SalesInvoice | Parent invoice |
| SalesOrderLineID | integer | No | FK -> SalesOrderLine | Source order line |
| LineNumber | integer | No |  | Starts at 1 within invoice |
| ItemID | integer | No | FK -> Item | Billed item |
| Quantity | decimal quantity | No |  | Positive quantity |
| UnitPrice | decimal money | No |  | Billed unit price |
| Discount | decimal quantity | No |  | Discount rate |
| LineTotal | decimal money | No |  | Quantity x UnitPrice x (1 - Discount) |

Implementation notes: In the clean data, invoice lines should usually tie to shipped quantities. Selected anomalies may break this rule.

### 25.3.8 CashReceipt

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| CashReceiptID | integer | No | PK | Sequential key |
| ReceiptNumber | text short | No | Unique | Format CR-YYYY-NNNNNN |
| ReceiptDate | date | No |  | Date cash received |
| CustomerID | integer | No | FK -> Customer | Paying customer |
| SalesInvoiceID | integer | Yes | FK -> SalesInvoice | Null for unapplied cash |
| Amount | decimal money | No |  | Positive amount |
| PaymentMethod | text short | No |  | One of Check, Wire Transfer, ACH, Credit Card |
| ReferenceNumber | text short | No |  | Check number or transaction reference |
| DepositDate | date | Yes |  | On or after ReceiptDate |
| RecordedByEmployeeID | integer | No | FK -> Employee | Recording employee |

Implementation notes: One invoice may have multiple receipts. Unapplied receipts are allowed. Overpayments should be rare and intentional.

## 25.4 Procure-to-pay tables

### 25.4.1 Supplier

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| SupplierID | integer | No | PK | Sequential key |
| SupplierName | text short | No |  | Supplier legal or trade name |
| ContactName | text short | No |  | Primary contact |
| Address | text long | No |  | Street address |
| City | text short | No |  | City |
| State | text short | No |  | State or province |
| PostalCode | text short | No |  | Postal code |
| Country | text short | No |  | Country |
| Phone | text short | No |  | Phone |
| Email | text short | No |  | Email |
| PaymentTerms | text short | No |  | One of Net 30, Net 45, Net 60 |
| IsApproved | boolean flag | No |  | 1 approved, 0 not approved |
| TaxID | text short | No |  | Masked or synthetic tax ID |
| BankAccount | text short | No |  | Masked bank account |
| SupplierCategory | text short | Yes |  | Optional segmentation |
| SupplierRiskRating | text short | Yes |  | Low, Medium, High or similar |
| DefaultCurrency | text short | Yes |  | Default USD in main version |

Implementation notes: Supplier specialization by item group should be modeled for realistic purchasing.

### 25.4.2 PurchaseRequisition

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| RequisitionID | integer | No | PK | Sequential key |
| RequisitionNumber | text short | No | Unique | Format PR-YYYY-NNNNNN |
| RequestDate | date | No |  | Date requested |
| RequestedByEmployeeID | integer | No | FK -> Employee | Requestor |
| CostCenterID | integer | No | FK -> CostCenter | Requesting department |
| ItemID | integer | No | FK -> Item | Requested item |
| Quantity | decimal quantity | No |  | Positive quantity |
| EstimatedUnitCost | decimal money | No |  | Expected cost |
| Justification | text long | No |  | Business reason |
| ApprovedByEmployeeID | integer | Yes | FK -> Employee | Null if pending or rejected without approval |
| ApprovedDate | date | Yes |  | Null if not approved |
| Status | text short | No |  | One of Pending, Approved, Rejected, Converted to PO |

Implementation notes: Requisition quantity and item should align with replenishment or operating-need logic.

### 25.4.3 PurchaseOrder

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| PurchaseOrderID | integer | No | PK | Sequential key |
| PONumber | text short | No | Unique | Format PO-YYYY-NNNNNN |
| OrderDate | date | No |  | PO date |
| SupplierID | integer | No | FK -> Supplier | Selected vendor |
| RequisitionID | integer | Yes | FK -> PurchaseRequisition | Null only for rare blanket or bypass cases |
| ExpectedDeliveryDate | date | No |  | On or after OrderDate |
| Status | text short | No |  | One of Open, Partially Received, Received, Closed, Cancelled |
| CreatedByEmployeeID | integer | No | FK -> Employee | Purchasing agent |
| ApprovedByEmployeeID | integer | No | FK -> Employee | Approver |
| OrderTotal | decimal money | No |  | Sum of PO line totals |

Implementation notes: In the clean data, supplier should generally be approved and approval should respect authorization levels.

### 25.4.4 PurchaseOrderLine

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| POLineID | integer | No | PK | Sequential key |
| PurchaseOrderID | integer | No | FK -> PurchaseOrder | Parent PO |
| LineNumber | integer | No |  | Starts at 1 within PO |
| ItemID | integer | No | FK -> Item | Ordered item |
| Quantity | decimal quantity | No |  | Positive quantity |
| UnitCost | decimal money | No |  | Agreed purchase cost |
| LineTotal | decimal money | No |  | Quantity x UnitCost |

Implementation notes: Item must be purchasable. LineTotal is derived.

### 25.4.5 GoodsReceipt

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| GoodsReceiptID | integer | No | PK | Sequential key |
| ReceiptNumber | text short | No | Unique | Format GR-YYYY-NNNNNN |
| ReceiptDate | date | No |  | Normally on or after OrderDate |
| PurchaseOrderID | integer | No | FK -> PurchaseOrder | Source PO |
| WarehouseID | integer | No | FK -> Warehouse | Receiving location |
| ReceivedByEmployeeID | integer | No | FK -> Employee | Warehouse staff |
| Status | text short | No |  | One of Received, Partially Received, Rejected |

Implementation notes: One PO may have multiple goods receipts. Receipt status should reflect actual received quantity pattern.

### 25.4.6 GoodsReceiptLine

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| GoodsReceiptLineID | integer | No | PK | Sequential key |
| GoodsReceiptID | integer | No | FK -> GoodsReceipt | Parent receipt |
| POLineID | integer | No | FK -> PurchaseOrderLine | Source PO line |
| LineNumber | integer | No |  | Starts at 1 within receipt |
| ItemID | integer | No | FK -> Item | Received item |
| QuantityReceived | decimal quantity | No |  | Positive quantity |
| ExtendedStandardCost | decimal money | No |  | QuantityReceived x unit basis chosen for posting |

Implementation notes: In the clean data, cumulative receipt quantity for a PO line should normally not exceed ordered quantity unless partial over-receipt behavior is intentionally allowed.

### 25.4.7 PurchaseInvoice

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| PurchaseInvoiceID | integer | No | PK | Sequential key |
| InvoiceNumber | text short | No |  | Vendor invoice number, not globally unique |
| InvoiceDate | date | No |  | Vendor invoice date |
| ReceivedDate | date | No |  | Company received date |
| DueDate | date | No |  | Based on payment terms |
| PurchaseOrderID | integer | Yes | FK -> PurchaseOrder | Null only for controlled anomaly cases |
| SupplierID | integer | No | FK -> Supplier | Billing vendor |
| SubTotal | decimal money | No |  | Sum of line totals |
| TaxAmount | decimal money | No |  | Usually small or zero in simplified model |
| GrandTotal | decimal money | No |  | SubTotal + TaxAmount |
| Status | text short | No |  | One of Pending Approval, Approved, Paid, Disputed, Cancelled |
| ApprovedByEmployeeID | integer | Yes | FK -> Employee | Null only if not approved |
| ApprovedDate | date | Yes |  | Null if pending |

Implementation notes: Duplicate invoice numbers from the same supplier should be allowed only in anomaly cases.

### 25.4.8 PurchaseInvoiceLine

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| PILineID | integer | No | PK | Sequential key |
| PurchaseInvoiceID | integer | No | FK -> PurchaseInvoice | Parent invoice |
| POLineID | integer | No | FK -> PurchaseOrderLine | Source PO line |
| LineNumber | integer | No |  | Starts at 1 within invoice |
| ItemID | integer | No | FK -> Item | Billed item |
| Quantity | decimal quantity | No |  | Positive quantity |
| UnitCost | decimal money | No |  | Billed unit cost |
| LineTotal | decimal money | No |  | Quantity x UnitCost |

Implementation notes: In the clean data, invoice lines should usually tie to received quantities and expected PO cost patterns.

### 25.4.9 DisbursementPayment

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| DisbursementID | integer | No | PK | Sequential key |
| PaymentNumber | text short | No | Unique | Format DP-YYYY-NNNNNN |
| PaymentDate | date | No |  | Date issued |
| SupplierID | integer | No | FK -> Supplier | Paid supplier |
| PurchaseInvoiceID | integer | Yes | FK -> PurchaseInvoice | Null for prepayments |
| Amount | decimal money | No |  | Positive amount |
| PaymentMethod | text short | No |  | One of Check, Wire Transfer, ACH |
| CheckNumber | text short | Yes |  | Null if not check |
| ApprovedByEmployeeID | integer | No | FK -> Employee | Payment approver |
| ClearedDate | date | Yes |  | On or after PaymentDate |

Implementation notes: One purchase invoice may have multiple disbursements. Duplicate payments should be injected only after clean validation.

## 25.5 Master data tables

### 25.5.1 Item

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| ItemID | integer | No | PK | Sequential key |
| ItemCode | text short | No | Unique | SKU-like code |
| ItemName | text short | No |  | Descriptive item name |
| ItemGroup | text short | No |  | One of Furniture, Lighting, Textiles, Accessories, Raw Materials, Packaging |
| ItemType | text short | No |  | One of Finished Good, Purchased Material, Both |
| StandardCost | decimal money | No |  | Positive cost |
| ListPrice | decimal money | Yes |  | Null allowed for non-sellable materials if preferred |
| UnitOfMeasure | text short | No |  | One of Each, Box, Roll, Set |
| InventoryAccountID | integer | No | FK -> Account | Inventory mapping |
| RevenueAccountID | integer | Yes | FK -> Account | Null for nonsellable items |
| COGSAccountID | integer | Yes | FK -> Account | Null for nonsellable items |
| PurchaseVarianceAccountID | integer | Yes | FK -> Account | Optional mapping |
| TaxCategory | text short | Yes |  | Taxable or Exempt style field |
| IsActive | boolean flag | No |  | 1 or 0 |

Implementation notes: Item mix should favor sellable items, with materials and packaging supporting P2P and inventory diversity.

### 25.5.2 Warehouse

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| WarehouseID | integer | No | PK | Sequential key |
| WarehouseName | text short | No |  | Descriptive warehouse name |
| Address | text long | No |  | Location address |
| City | text short | No |  | City |
| State | text short | No |  | State |
| ManagerID | integer | No | FK -> Employee | Warehouse manager |

Implementation notes: Two warehouses are sufficient for the main version.

### 25.5.3 Employee

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| EmployeeID | integer | No | PK | Sequential key |
| EmployeeName | text short | No |  | Full name |
| CostCenterID | integer | No | FK -> CostCenter | Department assignment |
| JobTitle | text short | No |  | Job title |
| Email | text short | No | Unique | Company email |
| Address | text long | No |  | Home address |
| City | text short | No |  | City |
| State | text short | No |  | State |
| HireDate | date | No |  | Hire date |
| ManagerID | integer | Yes | FK -> Employee | Null for top executive |
| IsActive | boolean flag | No |  | 1 or 0 |
| AuthorizationLevel | text short | No |  | One of Standard, Manager, Director, VP |
| MaxApprovalAmount | decimal money | No |  | Positive amount tied to authorization level |

Implementation notes: Address matches with suppliers or customers should be added only through anomaly injection or controlled master-data overrides.

## 25.6 Organizational tables

### 25.6.1 CostCenter

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| CostCenterID | integer | No | PK | Sequential key |
| CostCenterName | text short | No | Unique | Department name |
| ParentCostCenterID | integer | Yes | FK -> CostCenter | Null for top-level centers |
| ManagerID | integer | Yes | FK -> Employee | May be backfilled after employee generation |
| IsActive | boolean flag | No |  | 1 or 0 |

Implementation notes: Because Employee depends on CostCenter and CostCenter references Employee, ManagerID can be backfilled after employees are created.

### 25.6.2 Budget

| Column | Type | Null | Key | Rules and implementation notes |
|---|---|---|---|---|
| BudgetID | integer | No | PK | Sequential key |
| FiscalYear | integer | No |  | 2026 through 2030 |
| CostCenterID | integer | No | FK -> CostCenter | Department |
| AccountID | integer | No | FK -> Account | Budgeted revenue or expense account |
| Month | integer | No |  | 1 through 12 |
| BudgetAmount | decimal money | No |  | Positive for expenses and revenues in planning table |
| ApprovedByEmployeeID | integer | No | FK -> Employee | Budget approver |
| ApprovedDate | date | No |  | Plausible approval date before or near fiscal year start |

Implementation notes: Budget rows should be limited to selected revenue and expense accounts rather than the full chart.

## 25.7 Controlled vocabularies summary

The generator should centralize controlled values to avoid drift.

### 25.7.1 Status vocabularies

| Field | Allowed values |
|---|---|
| JournalEntry.EntryType | Standard, Adjusting, Closing, Correcting, Reversing, Opening |
| SalesOrder.Status | Open, Partially Shipped, Shipped, Invoiced, Closed, Cancelled |
| Shipment.Status | In Transit, Delivered, Returned |
| SalesInvoice.Status | Draft, Submitted, Paid, Partially Paid, Overdue, Cancelled |
| PurchaseRequisition.Status | Pending, Approved, Rejected, Converted to PO |
| PurchaseOrder.Status | Open, Partially Received, Received, Closed, Cancelled |
| GoodsReceipt.Status | Received, Partially Received, Rejected |
| PurchaseInvoice.Status | Pending Approval, Approved, Paid, Disputed, Cancelled |
| Employee.AuthorizationLevel | Standard, Manager, Director, VP |

### 25.7.2 Other controlled fields

| Field | Allowed values |
|---|---|
| Account.AccountType | Asset, Liability, Equity, Revenue, Expense |
| Account.NormalBalance | Debit, Credit |
| Customer.PaymentTerms | Net 30, Net 45, Net 60, Net 90 |
| Supplier.PaymentTerms | Net 30, Net 45, Net 60 |
| CashReceipt.PaymentMethod | Check, Wire Transfer, ACH, Credit Card |
| DisbursementPayment.PaymentMethod | Check, Wire Transfer, ACH |
| Item.ItemGroup | Furniture, Lighting, Textiles, Accessories, Raw Materials, Packaging |
| Item.ItemType | Finished Good, Purchased Material, Both |
| Item.UnitOfMeasure | Each, Box, Roll, Set |

## 25.8 Derived-field formulas summary

The Python generator should compute derived fields consistently through centralized helper functions.

| Table | Field | Formula or rule |
|---|---|---|
| SalesOrderLine | LineTotal | round(Quantity x UnitPrice x (1 - Discount), 2) |
| SalesOrder | OrderTotal | sum of related SalesOrderLine.LineTotal |
| ShipmentLine | ExtendedStandardCost | round(QuantityShipped x item standard cost, 2) |
| SalesInvoiceLine | LineTotal | round(Quantity x UnitPrice x (1 - Discount), 2) |
| SalesInvoice | SubTotal | sum of related SalesInvoiceLine.LineTotal |
| SalesInvoice | TaxAmount | round(SubTotal x applicable tax rate, 2) unless exempt |
| SalesInvoice | GrandTotal | SubTotal + TaxAmount |
| PurchaseOrderLine | LineTotal | round(Quantity x UnitCost, 2) |
| PurchaseOrder | OrderTotal | sum of related PurchaseOrderLine.LineTotal |
| GoodsReceiptLine | ExtendedStandardCost | round(QuantityReceived x posting cost basis, 2) |
| PurchaseInvoiceLine | LineTotal | round(Quantity x UnitCost, 2) |
| PurchaseInvoice | SubTotal | sum of related PurchaseInvoiceLine.LineTotal |
| PurchaseInvoice | GrandTotal | SubTotal + TaxAmount |
| GLEntry | FiscalYear | year(PostingDate) |
| GLEntry | FiscalPeriod | month(PostingDate) |

## 25.9 Nullability rules that matter most

The following nullability rules should be enforced carefully because they affect analytics and joins.

- SalesInvoiceID in CashReceipt may be null for unapplied cash.
- PurchaseInvoiceID in DisbursementPayment may be null for vendor advances.
- RequisitionID in PurchaseOrder should normally be non-null in clean data but may be null for rare exceptions.
- PurchaseOrderID in PurchaseInvoice should normally be non-null in clean data but may be null for anomaly cases.
- ApprovedByEmployeeID and ApprovedDate should move together. One should not be populated without the other.
- DeliveryDate may be null for in-transit shipments.
- PaymentDate in SalesInvoice should be populated only when the invoice is fully settled.
- CheckNumber in DisbursementPayment may be null when payment method is wire or ACH.

## 25.10 Referential sequencing notes for coding

Because some tables reference each other recursively or cyclically, the generator should handle sequencing carefully.

### 25.10.1 CostCenter and Employee cycle

Create CostCenter first with null ManagerID values. Then create Employee. Then backfill CostCenter.ManagerID once managers are assigned.

### 25.10.2 Parent-child account hierarchy

Load parent accounts first, then child accounts, or simply load the entire configured table and validate ParentAccountID references afterward.

### 25.10.3 Operational header and line tables

Always create headers first, then lines, then recompute header totals and statuses.

## 25.11 Implementation guardrails for the Python script

The script should enforce a small set of hard-stop rules during generation.

- Do not allow duplicate business document numbers.
- Do not allow orphan line rows.
- Do not allow negative monetary values in line totals unless a table is explicitly designed for credits or returns, which this version is not.
- Do not allow null foreign keys in core clean-data relationships except where explicitly permitted.
- Do not allow unbalanced vouchers into GLEntry.
- Do not allow final export if validation fails outside the planned anomaly allowances.

## 26. Python script skeleton and starter implementation structure

This section provides a practical script skeleton for building the Greenfield dataset generator. The objective is not to fully implement every function here, but to define a clean and scalable structure that can be coded directly.

## 26.1 Recommended implementation style

The generator should be implemented as a standard Python package with a main entry point. The package should separate configuration, schema creation, master data generation, transactional generation, posting logic, anomaly injection, validation, and export.

A functional style with a shared context object is appropriate for this project because it keeps state visible and easier to debug. A heavy object-oriented design is not necessary.

## 26.2 Core dataclasses and context model

The following starter dataclasses are recommended.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class Settings:
    random_seed: int
    fiscal_year_start: str
    fiscal_year_end: str
    company_name: str
    tax_rate: float
    employee_count: int
    customer_count: int
    supplier_count: int
    item_count: int
    warehouse_count: int
    export_sqlite: bool = True
    export_excel: bool = True
    anomaly_mode: str = "standard"
    sqlite_path: str = "outputs/greenfield_2026_2030.sqlite"
    excel_path: str = "outputs/greenfield_2026_2030.xlsx"
    validation_report_path: str = "outputs/validation_report.json"


@dataclass
class GenerationContext:
    settings: Settings
    rng: np.random.Generator
    calendar: pd.DataFrame
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    validation_results: dict[str, Any] = field(default_factory=dict)
    anomaly_log: list[dict[str, Any]] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)
    reference: dict[str, Any] = field(default_factory=dict)
```

Implementation notes: The reference dictionary can hold reusable lookup objects such as account maps, customer tiers, item group mappings, monthly target tables, and employee authorization matrices.

## 26.3 Minimal configuration loader

A small configuration loader should create the Settings object from YAML or a Python dictionary.

```python
import yaml


def load_settings(config_path: str | Path) -> Settings:
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Settings(**raw)
```

## 26.4 Context initialization and calendar build

The context should be initialized once at runtime.

```python

def build_calendar(start_date: str, end_date: str) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    cal = pd.DataFrame({"Date": dates})
    cal["FiscalYear"] = cal["Date"].dt.year
    cal["FiscalPeriod"] = cal["Date"].dt.month
    cal["Quarter"] = cal["Date"].dt.quarter
    cal["MonthName"] = cal["Date"].dt.month_name()
    cal["Weekday"] = cal["Date"].dt.day_name()
    cal["IsWeekend"] = cal["Weekday"].isin(["Saturday", "Sunday"]).astype(int)
    cal["Date"] = cal["Date"].dt.strftime("%Y-%m-%d")
    return cal


def initialize_context(settings: Settings) -> GenerationContext:
    rng = np.random.default_rng(settings.random_seed)
    calendar = build_calendar(settings.fiscal_year_start, settings.fiscal_year_end)
    return GenerationContext(settings=settings, rng=rng, calendar=calendar)
```

## 26.5 Table registry and empty-table creation

The generator should explicitly create empty dataframes for each table with the correct columns before any data are added.

```python
TABLE_COLUMNS = {
    "Account": [
        "AccountID", "AccountNumber", "AccountName", "AccountType", "AccountSubType",
        "ParentAccountID", "NormalBalance", "IsActive"
    ],
    "JournalEntry": [
        "JournalEntryID", "EntryNumber", "PostingDate", "EntryType", "Description",
        "TotalAmount", "CreatedByEmployeeID", "CreatedDate", "ApprovedByEmployeeID",
        "ApprovedDate", "ReversesJournalEntryID"
    ],
    "GLEntry": [
        "GLEntryID", "PostingDate", "AccountID", "Debit", "Credit", "VoucherType",
        "VoucherNumber", "SourceDocumentType", "SourceDocumentID", "SourceLineID",
        "CostCenterID", "Description", "CreatedByEmployeeID", "CreatedDate",
        "FiscalYear", "FiscalPeriod"
    ],
    "Customer": [
        "CustomerID", "CustomerName", "ContactName", "Address", "City", "State",
        "PostalCode", "Country", "Phone", "Email", "CreditLimit", "PaymentTerms",
        "CustomerSince", "SalesRepEmployeeID", "CustomerSegment", "Industry", "Region",
        "IsActive"
    ],
    "SalesOrder": [
        "SalesOrderID", "OrderNumber", "OrderDate", "CustomerID", "RequestedDeliveryDate",
        "Status", "SalesRepEmployeeID", "CostCenterID", "OrderTotal", "Notes"
    ],
    "SalesOrderLine": [
        "SalesOrderLineID", "SalesOrderID", "LineNumber", "ItemID", "Quantity",
        "UnitPrice", "Discount", "LineTotal"
    ],
    "Shipment": [
        "ShipmentID", "ShipmentNumber", "SalesOrderID", "ShipmentDate", "WarehouseID",
        "ShippedBy", "TrackingNumber", "Status", "DeliveryDate"
    ],
    "ShipmentLine": [
        "ShipmentLineID", "ShipmentID", "SalesOrderLineID", "LineNumber", "ItemID",
        "QuantityShipped", "ExtendedStandardCost"
    ],
    "SalesInvoice": [
        "SalesInvoiceID", "InvoiceNumber", "InvoiceDate", "DueDate", "SalesOrderID",
        "CustomerID", "SubTotal", "TaxAmount", "GrandTotal", "Status", "PaymentDate"
    ],
    "SalesInvoiceLine": [
        "SalesInvoiceLineID", "SalesInvoiceID", "SalesOrderLineID", "LineNumber",
        "ItemID", "Quantity", "UnitPrice", "Discount", "LineTotal"
    ],
    "CashReceipt": [
        "CashReceiptID", "ReceiptNumber", "ReceiptDate", "CustomerID", "SalesInvoiceID",
        "Amount", "PaymentMethod", "ReferenceNumber", "DepositDate", "RecordedByEmployeeID"
    ],
    "Supplier": [
        "SupplierID", "SupplierName", "ContactName", "Address", "City", "State",
        "PostalCode", "Country", "Phone", "Email", "PaymentTerms", "IsApproved",
        "TaxID", "BankAccount", "SupplierCategory", "SupplierRiskRating", "DefaultCurrency"
    ],
    "PurchaseRequisition": [
        "RequisitionID", "RequisitionNumber", "RequestDate", "RequestedByEmployeeID",
        "CostCenterID", "ItemID", "Quantity", "EstimatedUnitCost", "Justification",
        "ApprovedByEmployeeID", "ApprovedDate", "Status"
    ],
    "PurchaseOrder": [
        "PurchaseOrderID", "PONumber", "OrderDate", "SupplierID", "RequisitionID",
        "ExpectedDeliveryDate", "Status", "CreatedByEmployeeID", "ApprovedByEmployeeID",
        "OrderTotal"
    ],
    "PurchaseOrderLine": [
        "POLineID", "PurchaseOrderID", "LineNumber", "ItemID", "Quantity", "UnitCost",
        "LineTotal"
    ],
    "GoodsReceipt": [
        "GoodsReceiptID", "ReceiptNumber", "ReceiptDate", "PurchaseOrderID", "WarehouseID",
        "ReceivedByEmployeeID", "Status"
    ],
    "GoodsReceiptLine": [
        "GoodsReceiptLineID", "GoodsReceiptID", "POLineID", "LineNumber", "ItemID",
        "QuantityReceived", "ExtendedStandardCost"
    ],
    "PurchaseInvoice": [
        "PurchaseInvoiceID", "InvoiceNumber", "InvoiceDate", "ReceivedDate", "DueDate",
        "PurchaseOrderID", "SupplierID", "SubTotal", "TaxAmount", "GrandTotal", "Status",
        "ApprovedByEmployeeID", "ApprovedDate"
    ],
    "PurchaseInvoiceLine": [
        "PILineID", "PurchaseInvoiceID", "POLineID", "LineNumber", "ItemID", "Quantity",
        "UnitCost", "LineTotal"
    ],
    "DisbursementPayment": [
        "DisbursementID", "PaymentNumber", "PaymentDate", "SupplierID",
        "PurchaseInvoiceID", "Amount", "PaymentMethod", "CheckNumber",
        "ApprovedByEmployeeID", "ClearedDate"
    ],
    "Item": [
        "ItemID", "ItemCode", "ItemName", "ItemGroup", "ItemType", "StandardCost",
        "ListPrice", "UnitOfMeasure", "InventoryAccountID", "RevenueAccountID",
        "COGSAccountID", "PurchaseVarianceAccountID", "TaxCategory", "IsActive"
    ],
    "Warehouse": [
        "WarehouseID", "WarehouseName", "Address", "City", "State", "ManagerID"
    ],
    "Employee": [
        "EmployeeID", "EmployeeName", "CostCenterID", "JobTitle", "Email", "Address",
        "City", "State", "HireDate", "ManagerID", "IsActive", "AuthorizationLevel",
        "MaxApprovalAmount"
    ],
    "CostCenter": [
        "CostCenterID", "CostCenterName", "ParentCostCenterID", "ManagerID", "IsActive"
    ],
    "Budget": [
        "BudgetID", "FiscalYear", "CostCenterID", "AccountID", "Month", "BudgetAmount",
        "ApprovedByEmployeeID", "ApprovedDate"
    ],
}


def create_empty_tables(context: GenerationContext) -> None:
    context.tables = {
        name: pd.DataFrame(columns=cols)
        for name, cols in TABLE_COLUMNS.items()
    }
    context.counters = {name: 1 for name in TABLE_COLUMNS}
```

## 26.6 Identifier helpers and business document numbering

All primary keys and business document numbers should be generated through reusable helpers.

```python

def next_id(context: GenerationContext, table_name: str) -> int:
    current = context.counters[table_name]
    context.counters[table_name] += 1
    return current


def format_doc_number(prefix: str, year: int, sequence: int) -> str:
    return f"{prefix}-{year}-{sequence:06d}"
```

Recommended prefixes:

- JE for JournalEntry
- SO for SalesOrder
- SH for Shipment
- SI for SalesInvoice
- CR for CashReceipt
- PR for PurchaseRequisition
- PO for PurchaseOrder
- GR for GoodsReceipt
- PI for PurchaseInvoice
- DP for DisbursementPayment

## 26.7 Utility functions for dates, rounding, and weighted sampling

A small utility layer will keep the main generator readable.

```python
from decimal import Decimal, ROUND_HALF_UP


def money(value: float | Decimal) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def qty(value: float | Decimal, places: str = "0.01") -> float:
    return float(Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP))


def random_date_in_month(rng: np.random.Generator, year: int, month: int) -> pd.Timestamp:
    start = pd.Timestamp(year=year, month=month, day=1)
    end = start + pd.offsets.MonthEnd(1)
    days = (end - start).days
    return start + pd.Timedelta(days=int(rng.integers(0, days + 1)))


def weighted_choice(rng: np.random.Generator, values: list[Any], weights: list[float]) -> Any:
    probs = np.array(weights, dtype=float)
    probs = probs / probs.sum()
    return rng.choice(values, p=probs)
```

## 26.8 Starter master-data function signatures

The following function signatures are sufficient for the first implementation pass.

```python

def generate_cost_centers(context: GenerationContext) -> None:
    ...


def generate_employees(context: GenerationContext) -> None:
    ...


def backfill_cost_center_managers(context: GenerationContext) -> None:
    ...


def generate_warehouses(context: GenerationContext) -> None:
    ...


def load_accounts(context: GenerationContext, accounts_path: str | Path) -> None:
    ...


def generate_items(context: GenerationContext) -> None:
    ...


def generate_customers(context: GenerationContext) -> None:
    ...


def generate_suppliers(context: GenerationContext) -> None:
    ...


def generate_opening_balances(context: GenerationContext) -> None:
    ...


def generate_budgets(context: GenerationContext) -> None:
    ...
```

### 26.8.1 Example starter implementation for cost centers

```python

def generate_cost_centers(context: GenerationContext) -> None:
    rows = [
        ("Executive", None, 1),
        ("Sales", None, 1),
        ("Warehouse", None, 1),
        ("Purchasing", None, 1),
        ("Administration", None, 1),
        ("Customer Service", None, 1),
        ("Research and Development", None, 1),
        ("Marketing", None, 1),
    ]

    records = []
    for name, parent_id, is_active in rows:
        records.append({
            "CostCenterID": next_id(context, "CostCenter"),
            "CostCenterName": name,
            "ParentCostCenterID": parent_id,
            "ManagerID": None,
            "IsActive": is_active,
        })

    context.tables["CostCenter"] = pd.DataFrame(records, columns=TABLE_COLUMNS["CostCenter"])
```

## 26.9 Starter transaction-generation function signatures

The transaction generation should be month-driven.

```python

def generate_month_o2c(context: GenerationContext, year: int, month: int) -> None:
    ...


def generate_month_sales_orders(context: GenerationContext, year: int, month: int) -> None:
    ...


def generate_month_shipments(context: GenerationContext, year: int, month: int) -> None:
    ...


def generate_month_sales_invoices(context: GenerationContext, year: int, month: int) -> None:
    ...


def generate_month_cash_receipts(context: GenerationContext, year: int, month: int) -> None:
    ...


def generate_month_p2p(context: GenerationContext, year: int, month: int) -> None:
    ...


def generate_month_requisitions(context: GenerationContext, year: int, month: int) -> None:
    ...


def generate_month_purchase_orders(context: GenerationContext, year: int, month: int) -> None:
    ...


def generate_month_goods_receipts(context: GenerationContext, year: int, month: int) -> None:
    ...


def generate_month_purchase_invoices(context: GenerationContext, year: int, month: int) -> None:
    ...


def generate_month_disbursements(context: GenerationContext, year: int, month: int) -> None:
    ...


def generate_month_manual_journals(context: GenerationContext, year: int, month: int) -> None:
    ...
```

### 26.9.1 Recommended orchestration inside O2C and P2P wrappers

```python

def generate_month_o2c(context: GenerationContext, year: int, month: int) -> None:
    generate_month_sales_orders(context, year, month)
    generate_month_shipments(context, year, month)
    generate_month_sales_invoices(context, year, month)
    generate_month_cash_receipts(context, year, month)


def generate_month_p2p(context: GenerationContext, year: int, month: int) -> None:
    generate_month_requisitions(context, year, month)
    generate_month_purchase_orders(context, year, month)
    generate_month_goods_receipts(context, year, month)
    generate_month_purchase_invoices(context, year, month)
    generate_month_disbursements(context, year, month)
```

## 26.10 Posting engine starter structure

The posting engine should be centralized and event-based.

```python

def post_all_transactions(context: GenerationContext) -> None:
    gl_rows: list[dict[str, Any]] = []
    gl_rows.extend(post_shipments(context))
    gl_rows.extend(post_sales_invoices(context))
    gl_rows.extend(post_cash_receipts(context))
    gl_rows.extend(post_goods_receipts(context))
    gl_rows.extend(post_purchase_invoices(context))
    gl_rows.extend(post_disbursements(context))
    gl_rows.extend(post_manual_journals(context))

    gl_df = pd.DataFrame(gl_rows, columns=TABLE_COLUMNS["GLEntry"])
    context.tables["GLEntry"] = gl_df
```

### 26.10.1 GL row builder helper

```python

def build_gl_row(
    context: GenerationContext,
    posting_date: str,
    account_id: int,
    debit: float,
    credit: float,
    voucher_type: str,
    voucher_number: str,
    source_document_type: str,
    source_document_id: int,
    source_line_id: int | None,
    cost_center_id: int | None,
    description: str,
    created_by_employee_id: int,
) -> dict[str, Any]:
    ts = pd.Timestamp(posting_date)
    return {
        "GLEntryID": next_id(context, "GLEntry"),
        "PostingDate": posting_date,
        "AccountID": account_id,
        "Debit": money(debit),
        "Credit": money(credit),
        "VoucherType": voucher_type,
        "VoucherNumber": voucher_number,
        "SourceDocumentType": source_document_type,
        "SourceDocumentID": source_document_id,
        "SourceLineID": source_line_id,
        "CostCenterID": cost_center_id,
        "Description": description,
        "CreatedByEmployeeID": created_by_employee_id,
        "CreatedDate": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "FiscalYear": int(ts.year),
        "FiscalPeriod": int(ts.month),
    }
```

### 26.10.2 Voucher balancing helper

```python

def assert_balanced(rows: list[dict[str, Any]], voucher_number: str) -> None:
    debit_total = round(sum(r["Debit"] for r in rows), 2)
    credit_total = round(sum(r["Credit"] for r in rows), 2)
    if debit_total != credit_total:
        raise ValueError(
            f"Unbalanced voucher {voucher_number}: debit={debit_total}, credit={credit_total}"
        )
```

## 26.11 Example posting function skeleton

Shipment posting is a good first event to implement because it is line-driven and conceptually simple.

```python

def post_shipments(context: GenerationContext) -> list[dict[str, Any]]:
    shipment_df = context.tables["Shipment"]
    shipment_line_df = context.tables["ShipmentLine"]
    item_df = context.tables["Item"]
    so_df = context.tables["SalesOrder"][["SalesOrderID", "CostCenterID"]]

    item_map = item_df.set_index("ItemID")[["InventoryAccountID", "COGSAccountID"]].to_dict("index")
    cost_center_map = so_df.set_index("SalesOrderID")["CostCenterID"].to_dict()

    all_rows: list[dict[str, Any]] = []

    merged = shipment_line_df.merge(
        shipment_df[["ShipmentID", "ShipmentNumber", "SalesOrderID", "ShipmentDate"]],
        on="ShipmentID",
        how="left",
    )

    for row in merged.itertuples(index=False):
        item_accounts = item_map[row.ItemID]
        cost_center_id = cost_center_map.get(row.SalesOrderID)
        voucher_rows = [
            build_gl_row(
                context=context,
                posting_date=row.ShipmentDate,
                account_id=item_accounts["COGSAccountID"],
                debit=row.ExtendedStandardCost,
                credit=0.0,
                voucher_type="Shipment",
                voucher_number=row.ShipmentNumber,
                source_document_type="Shipment",
                source_document_id=row.ShipmentID,
                source_line_id=row.ShipmentLineID,
                cost_center_id=cost_center_id,
                description="Recognize COGS on shipment",
                created_by_employee_id=1,
            ),
            build_gl_row(
                context=context,
                posting_date=row.ShipmentDate,
                account_id=item_accounts["InventoryAccountID"],
                debit=0.0,
                credit=row.ExtendedStandardCost,
                voucher_type="Shipment",
                voucher_number=row.ShipmentNumber,
                source_document_type="Shipment",
                source_document_id=row.ShipmentID,
                source_line_id=row.ShipmentLineID,
                cost_center_id=cost_center_id,
                description="Relieve inventory on shipment",
                created_by_employee_id=1,
            ),
        ]
        assert_balanced(voucher_rows, row.ShipmentNumber)
        all_rows.extend(voucher_rows)

    return all_rows
```

## 26.12 Validation function skeleton

Validation should be callable both before and after anomaly injection.

```python

def validate_dataset(context: GenerationContext, stage: str = "clean") -> dict[str, Any]:
    results: dict[str, Any] = {}
    results["stage"] = stage
    results["row_counts"] = {
        table: int(len(df)) for table, df in context.tables.items()
    }
    results["gl_balanced"] = validate_gl_balance(context)
    results["header_line_checks"] = validate_header_line_totals(context)
    results["ar_reconciliation"] = validate_ar_reconciliation(context)
    results["ap_reconciliation"] = validate_ap_reconciliation(context)
    results["inventory_reconciliation"] = validate_inventory_reconciliation(context)
    context.validation_results[stage] = results
    return results
```

### 26.12.1 Example GL validation helper

```python

def validate_gl_balance(context: GenerationContext) -> dict[str, Any]:
    gl = context.tables["GLEntry"].copy()
    grouped = gl.groupby(["VoucherType", "VoucherNumber"], dropna=False)[["Debit", "Credit"]].sum()
    grouped["difference"] = (grouped["Debit"] - grouped["Credit"]).round(2)
    exceptions = grouped[grouped["difference"] != 0].reset_index()
    return {
        "exception_count": int(len(exceptions)),
        "exceptions": exceptions.to_dict(orient="records"),
    }
```

## 26.13 Anomaly injection starter signatures

The anomaly layer should be modular and driven by configuration.

```python

def inject_anomalies(context: GenerationContext) -> None:
    inject_weekend_journal_entries(context)
    inject_same_creator_approver(context)
    inject_missing_approvals(context)
    inject_invoice_before_shipment(context)
    inject_duplicate_vendor_payments(context)
    inject_threshold_adjacent_entries(context)
    inject_related_party_address_matches(context)
```

### 26.13.1 Anomaly logger helper

```python

def log_anomaly(
    context: GenerationContext,
    anomaly_type: str,
    table_name: str,
    primary_key_value: int,
    fiscal_year: int,
    description: str,
    expected_detection_test: str,
) -> None:
    context.anomaly_log.append(
        {
            "anomaly_type": anomaly_type,
            "table_name": table_name,
            "primary_key_value": primary_key_value,
            "fiscal_year": fiscal_year,
            "description": description,
            "expected_detection_test": expected_detection_test,
        }
    )
```

## 26.14 Export function skeleton

```python
import json
import sqlite3


def export_sqlite(context: GenerationContext) -> None:
    path = Path(context.settings.sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        for table_name, df in context.tables.items():
            df.to_sql(table_name, conn, if_exists="replace", index=False)


def export_excel(context: GenerationContext) -> None:
    path = Path(context.settings.excel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for table_name, df in context.tables.items():
            df.to_excel(writer, sheet_name=table_name[:31], index=False)
        if context.anomaly_log:
            pd.DataFrame(context.anomaly_log).to_excel(writer, sheet_name="AnomalyLog", index=False)
        pd.DataFrame([
            {"stage": k, "details": str(v)} for k, v in context.validation_results.items()
        ]).to_excel(writer, sheet_name="ValidationSummary", index=False)


def export_validation_report(context: GenerationContext) -> None:
    path = Path(context.settings.validation_report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "validation_results": context.validation_results,
        "anomaly_log": context.anomaly_log,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
```

## 26.15 Main orchestration script skeleton

The main entry point should be simple and deterministic.

```python

def build_dataset(config_path: str) -> GenerationContext:
    settings = load_settings(config_path)
    context = initialize_context(settings)

    create_empty_tables(context)

    generate_cost_centers(context)
    generate_employees(context)
    backfill_cost_center_managers(context)
    generate_warehouses(context)
    load_accounts(context, accounts_path="config/accounts.csv")
    generate_items(context)
    generate_customers(context)
    generate_suppliers(context)
    generate_opening_balances(context)
    generate_budgets(context)

    for year in range(2026, 2031):
        for month in range(1, 13):
            generate_month_o2c(context, year, month)
            generate_month_p2p(context, year, month)
            generate_month_manual_journals(context, year, month)

    post_all_transactions(context)
    validate_dataset(context, stage="clean")
    inject_anomalies(context)
    validate_dataset(context, stage="post_anomaly")

    if settings.export_sqlite:
        export_sqlite(context)
    if settings.export_excel:
        export_excel(context)
    export_validation_report(context)

    return context


if __name__ == "__main__":
    build_dataset("config/settings.yaml")
```

## 26.16 Recommended implementation order for coding

The script should be coded in manageable phases rather than all at once.

### Phase 1

- settings loader
- context initialization
- empty table creation
- chart of accounts load
- cost center, employee, warehouse generation

### Phase 2

- item, customer, supplier generation
- opening balances
- budgets

### Phase 3

- sales orders and sales order lines
- purchase requisitions and purchase orders

### Phase 4

- shipments and shipment lines
- goods receipts and goods receipt lines

### Phase 5

- sales invoices and cash receipts
- purchase invoices and disbursements

### Phase 6

- manual journals
- posting engine
- validation layer

### Phase 7

- anomaly injection
- SQLite and Excel export

This phased approach reduces debugging complexity.

## 26.17 Recommended next drafting task

The next document to draft should be the first runnable implementation package, beginning with the config files, accounts table, context setup, empty-schema creation, and master-data generators. That will convert this blueprint into executable code.
