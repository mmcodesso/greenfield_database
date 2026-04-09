# Dataset Overview

**Audience:** Students, instructors, and analysts using the dataset in AIS, accounting analytics, and auditing analytics courses.  
**Purpose:** Explain what the dataset is, why it exists, and what kinds of work it supports.  
**What you will learn:** The scope of the database, the business context, the implemented process coverage, and the core terms used throughout the project.

## What This Project Is

Greenfield Accounting Dataset provides a teachable business database for **Greenfield Home Furnishings, Inc.** The dataset links operational activity to accounting outcomes so learners can move from business documents to subledger detail to posted `GLEntry` records.

The project is built for:

- SQL exercises
- Excel-based analysis
- financial accounting analytics
- managerial accounting analytics
- audit analytics
- document tracing and control testing
- business process understanding

> **Implemented in current generator:** A five-year dataset with 31 tables covering O2C, P2P, accounting core, master data, budgets, recurring manual journals, year-end close, validations, anomalies, and exports.

> **Planned future extension:** Manufacturing tables and production transactions.

## Business Context

Greenfield is a mid-sized home furnishings distributor with two warehouses and a finance team that closes the books each year. The current dataset behaves like a merchandising company:

- it sells finished goods to customers
- it buys inventory from suppliers
- it stores inventory in warehouses
- it bills customers and collects cash
- it processes returns, customer credits, and refunds
- it requests, orders, receives, invoices, and pays for purchased inventory
- it records recurring journals and year-end close entries

Read [company-story.md](company-story.md) for the full narrative of how the company operates.

## What the Database Contains

The current implementation contains **31 tables** across five areas:

| Area | Example tables | Count |
|---|---|---:|
| Accounting core | `Account`, `JournalEntry`, `GLEntry` | 3 |
| Order-to-cash | `Customer`, `SalesOrder`, `Shipment`, `SalesInvoice`, `CashReceiptApplication`, `SalesReturn`, `CreditMemo`, `CustomerRefund` | 14 |
| Procure-to-pay | `Supplier`, `PurchaseRequisition`, `PurchaseOrder`, `GoodsReceipt`, `PurchaseInvoice`, `DisbursementPayment` | 9 |
| Master data | `Item`, `Warehouse`, `Employee` | 3 |
| Organizational planning | `CostCenter`, `Budget` | 2 |

The project also produces four release-ready outputs:

- a SQLite database
- an Excel workbook
- a JSON validation report
- a generation log

## What Students Can Do With It

This dataset supports three broad learning tracks.

### Financial accounting

Students can:

- analyze revenue, COGS, margin, and close-cycle activity
- reconcile receivables using invoices, cash applications, credit memos, and refunds
- reconcile payables using purchase invoices and disbursements
- trace operational activity into the general ledger
- study recurring journals and year-end close entries

### Managerial accounting

Students can:

- compare budget to actual activity by cost center and account
- analyze sales mix by item, customer, segment, and region
- study purchasing volume and supplier concentration
- examine inventory movement through receipts, shipments, and returns

### Auditing

Students can:

- test O2C and P2P document chains
- review approvals and segregation-of-duties patterns
- examine timing and cut-off behavior
- detect duplicate references, customer-credit patterns, and planted anomalies
- trace source documents to `GLEntry`

## What Is Not in Scope Yet

The current generator does **not** yet include:

- manufacturing orders
- bills of materials
- work centers or routings
- work-in-process accounting
- production completions

Those items are future roadmap areas, not hidden functionality inside the current dataset.

## Glossary

| Term | Plain-language meaning |
|---|---|
| O2C | Order-to-cash. The sales cycle from customer order through billing, cash application, and possible return activity. |
| P2P | Procure-to-pay. The purchasing cycle from requisition through supplier payment. |
| Subledger | Detailed operational records such as invoices, receipts, returns, or purchase documents. |
| GL | General ledger. The accounting table used for reporting and control-account reconciliation. |
| Control account | A GL account such as AR, AP, inventory, GRNI, or customer deposits that summarizes operational activity. |
| GRNI | Goods Received Not Invoiced. A liability recorded when inventory is received before the supplier invoice is approved. |
| Cost center | An organizational unit used for planning and performance analysis. |
| Anomaly | A deliberately planted exception or unusual pattern for analytics and audit exercises. |

## Where to Go Next

- Read [company-story.md](company-story.md) for the business narrative.
- Read [process-flows.md](process-flows.md) to understand O2C, P2P, journals, and ledger traceability.
- Read [database-guide.md](database-guide.md) to learn how to navigate the tables.
- Read [instructor-guide.md](instructor-guide.md) if you are designing class activities around the dataset.
