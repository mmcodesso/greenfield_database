# Dataset Overview

**Audience:** Students and instructors using the dataset in AIS, accounting analytics, and auditing analytics courses.  
**Purpose:** Explain what the dataset is, why it exists, and what kinds of analysis it supports.  
**What you will learn:** The business scenario, the scope of the database, and the main terms used throughout the project.

## What This Project Is

Greenfield Accounting Dataset Generator creates a teaching database for **Greenfield Home Furnishings, Inc.**, a fictional company that buys, stores, and sells home furnishings. The generator produces realistic business transactions and the related accounting postings so learners can connect operational activity to financial reporting.

The project is built for:

- SQL exercises
- Excel-based analysis
- financial analytics
- managerial analytics
- audit analytics
- subledger-to-ledger tracing
- business process understanding

> **Implemented in current generator:** A five-year dataset with master data, budgets, order-to-cash, procure-to-pay, opening balances, general ledger postings, validations, and planted anomalies.

> **Planned future extension:** Manufacturing tables, production transactions, and recurring manual operating journals beyond the opening balance entry.

## Business Story

Greenfield Home Furnishings, Inc. is modeled as a mid-sized distributor and light assembler. In the current implementation, the dataset behaves like a merchandising environment with perpetual inventory accounting:

- the company sells items to customers
- the company buys items from suppliers
- inventory moves through warehouses
- selected operational events create accounting entries

The company context is realistic enough for classroom analysis, but still constrained enough to stay teachable.

## What the Database Contains

The current generator produces 25 implemented tables across five areas:

| Area | Examples |
|---|---|
| Accounting core | `Account`, `JournalEntry`, `GLEntry` |
| Order-to-cash | `SalesOrder`, `Shipment`, `SalesInvoice`, `CashReceipt` |
| Procure-to-pay | `PurchaseRequisition`, `PurchaseOrder`, `GoodsReceipt`, `PurchaseInvoice`, `DisbursementPayment` |
| Master data | `Customer`, `Supplier`, `Item`, `Employee`, `Warehouse` |
| Organizational planning | `CostCenter`, `Budget` |

The generator also writes:

- a SQLite database
- an Excel workbook
- a JSON validation report
- a generation log

## What Students Can Do With It

This dataset supports three broad learning tracks.

### Financial analytics

Students can:

- build revenue, expense, and margin views
- reconcile invoices and cash receipts to receivables
- reconcile purchase invoices and payments to payables
- trace operational postings into the general ledger
- compare budget to actuals by cost center and account

### Managerial analytics

Students can:

- analyze sales mix by item, customer segment, and region
- compare planned spending to actual operational activity
- examine cost center performance
- study inventory movements using shipments and goods receipts

### Audit analytics

Students can:

- test order-to-cash and procure-to-pay process flow
- look for approval and segregation-of-duties issues
- analyze timing and cut-off behavior
- detect duplicate references and related-party indicators
- trace source documents to `GLEntry`

## What Is Not in Scope Yet

The current generator does **not** yet include:

- manufacturing orders
- bills of materials
- work centers or routings
- production completions
- recurring payroll, rent, utilities, or depreciation journals

Those items are future expansion areas, not current features.

## Glossary

| Term | Plain-language meaning |
|---|---|
| O2C | Order-to-cash. The sales cycle from customer order through cash collection. |
| P2P | Procure-to-pay. The purchasing cycle from requisition through supplier payment. |
| Subledger | Detailed operational records such as invoices, receipts, or purchase documents. |
| GL | General ledger. The accounting table used for reporting and control-account reconciliation. |
| Control account | A GL account such as AR, AP, inventory, or GRNI that summarizes subledger activity. |
| GRNI | Goods Received Not Invoiced. A liability recorded when inventory is received before the supplier invoice is approved. |
| Cost center | An organizational unit used for planning and performance analysis. |
| Anomaly | A deliberately planted exception or unusual pattern for analytics and audit exercises. |

## Where to Go Next

- Read [process-flows.md](process-flows.md) to understand O2C, P2P, and ledger traceability.
- Read [database-guide.md](database-guide.md) to learn how to navigate the tables.
- Read [instructor-guide.md](instructor-guide.md) if you are designing class activities around the dataset.
