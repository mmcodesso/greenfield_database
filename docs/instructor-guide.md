# Instructor Guide

**Audience:** Instructors designing AIS, accounting analytics, audit analytics, or SQL/Excel coursework around the dataset.  
**Purpose:** Show how the dataset can be introduced in class and how its tables support different exercise types.  
**What you will learn:** A suggested teaching sequence, how the dataset supports classroom activities, and which table families fit each analytics topic.

> **Implemented in current generator:** Five years of O2C and P2P data, opening balances, budgets, ledger postings, validations, and anomalies suitable for course exercises.

> **Planned future extension:** Manufacturing process coverage and recurring manual operating journals for broader cost accounting and closing-cycle exercises.

## How to Position the Dataset

This project works well when students need to connect:

- business process understanding
- relational data structure
- accounting logic
- analytical techniques in SQL and Excel

The dataset is especially useful when a course wants students to see that operational documents, subledgers, and financial reporting are part of one system rather than separate topics.

## Suggested Teaching Sequence

| Stage | Teaching goal | Recommended docs | Main tables |
|---|---|---|---|
| 1. Orientation | Explain the business story and scope | [dataset-overview.md](dataset-overview.md) | High-level only |
| 2. Process mapping | Show how O2C and P2P move through the system | [process-flows.md](process-flows.md) | O2C and P2P document tables |
| 3. Table navigation | Teach header-line design, joins, and master data | [database-guide.md](database-guide.md) | `Customer`, `Supplier`, `Item`, document headers and lines |
| 4. Accounting bridge | Show how operational events create ledger entries | [reference/posting.md](reference/posting.md) | `GLEntry`, `Account`, posted document tables |
| 5. Analytics modules | Run financial, managerial, and audit exercises | [database-guide.md](database-guide.md) and [reference/schema.md](reference/schema.md) | Topic-specific tables |

## How the Dataset Supports SQL and Excel

### SQL use

The dataset works well for:

- joins across header and line tables
- aggregation by month, customer, supplier, item, and cost center
- subledger-to-ledger reconciliation
- exception detection using dates, approvals, and duplicate references
- trend analysis across multiple fiscal years

### Excel use

The Excel export works well for:

- pivots by month, customer segment, supplier category, account, and cost center
- budget-versus-actual analysis
- aging-style views for receivables and payables
- charting seasonality, product mix, and anomaly patterns

## Exercise Categories

### Financial analytics

| Topic | Main tables | Example classroom use |
|---|---|---|
| Revenue and gross margin | `SalesInvoice`, `SalesInvoiceLine`, `ShipmentLine`, `GLEntry` | Compare billing activity to shipment cost and ledger postings |
| AR analysis | `SalesInvoice`, `CashReceipt`, `GLEntry` | Study collections, open items, and receivables reconciliation |
| AP analysis | `PurchaseInvoice`, `DisbursementPayment`, `GLEntry` | Study liabilities, payments, and payables reconciliation |
| Trial balance logic | `GLEntry`, `Account` | Build summarized financial views from ledger detail |

### Managerial analytics

| Topic | Main tables | Example classroom use |
|---|---|---|
| Budget vs actual | `Budget`, `CostCenter`, `GLEntry` | Compare planned spending to posted activity |
| Customer and product mix | `Customer`, `SalesOrderLine`, `SalesInvoiceLine`, `Item` | Analyze sales concentration and mix |
| Inventory movement | `GoodsReceiptLine`, `ShipmentLine`, `Item`, `Warehouse` | Analyze inbound and outbound inventory activity |
| Cost center behavior | `Employee`, `CostCenter`, `SalesOrder`, `PurchaseRequisition` | Study operational activity by organization unit |

### Audit analytics

| Topic | Main tables | Example classroom use |
|---|---|---|
| Completeness of document chains | O2C and P2P document tables | Trace missing or incomplete links across process steps |
| Approval controls | `PurchaseRequisition`, `PurchaseOrder`, `PurchaseInvoice`, `Employee` | Review approvals and segregation of duties |
| Cut-off and timing | `Shipment`, `SalesInvoice`, `GoodsReceipt`, `PurchaseInvoice` | Compare operational dates to accounting dates |
| Duplicate and unusual activity | `DisbursementPayment`, anomaly log output | Detect duplicate payment references and other planted exceptions |

## Teaching Notes

- Start with process understanding before asking students to write joins.
- Use `GLEntry` only after students understand which source events post and which do not.
- Make the distinction between clean data and planted anomalies explicit.
- If you want journal-entry-heavy exercises, note that the current implementation has only the opening balance journal header.

## Scope Boundaries to Communicate to Students

Students should not assume that the dataset already includes:

- manufacturing
- work orders
- bills of materials
- payroll journals
- recurring depreciation, rent, or utilities journals

Those are future expansion areas, not missing rows inside the current process model.

## Where to Go Next

- Read [process-flows.md](process-flows.md) when introducing business cycles.
- Read [code-architecture.md](code-architecture.md) if students or assistants need to understand how the generator was built.
