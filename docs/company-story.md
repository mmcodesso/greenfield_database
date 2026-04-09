# Company Story

**Audience:** Students, instructors, and analysts who need business context before reading tables or SQL.  
**Purpose:** Explain who Greenfield Home Furnishings is and how the business operates.  
**What you will learn:** The company narrative, its operating model, and why the current process design is useful for accounting and analytics coursework.

> **Implemented in current generator:** A merchandising-style company story with O2C, P2P, returns, recurring journals, and year-end close.

> **Planned future extension:** Manufacturing activity that would move Greenfield from a light-assembler story into a fuller production setting.

## The Company in Plain Language

Greenfield Home Furnishings, Inc. is a fictional mid-sized home furnishings company. It buys inventory from suppliers, stores it in two warehouses, sells finished goods to customers, and runs a finance function that records recurring journals and closes the books each year.

For teaching purposes, Greenfield is large enough to create realistic document volume and control questions, but simple enough that students can still understand the full business cycle.

## What Greenfield Sells and Who It Serves

Greenfield sells home furnishings and related product lines that are easy for business students to picture:

- furniture and decor items
- inventory-managed finished goods
- products sold to different customer types and regions

The dataset supports customer, item, region, and cost-center analysis, so students can ask both business and accounting questions from the same data.

## How the Business Operates

Greenfield's business story has four main parts.

### 1. Selling to customers

The sales team takes customer orders. Warehouse operations ship items when inventory is available. Accounting bills customers from the actual shipment lines, and treasury records and applies cash receipts.

Some customers pay one invoice at a time. Others send larger payments that must be applied across several invoices. Some receipts arrive before the related invoice is fully settled, which creates temporary customer deposits or unapplied cash.

### 2. Correcting sales activity

Not every sale ends cleanly. Some goods come back because of damage, wrong-item shipments, or customer changes in demand. In those cases, warehouse staff receive the return, accounting issues a credit memo, and treasury may refund the customer if the original invoice was already paid.

That gives students a realistic revenue-side exception path instead of a perfect one-way sales cycle.

### 3. Buying and receiving inventory

The purchasing cycle starts inside the company. Employees request items through requisitions. Purchasing groups those needs into purchase orders. Warehouses receive inventory over time, suppliers invoice the company, and finance pays approved invoices.

Because receiving, invoicing, and payment do not always happen in the same month, students can study timing, matching, and open-balance behavior.

### 4. Closing the books

Greenfield is not only an operational database. The finance team also books recurring monthly journals for payroll, rent, utilities, depreciation, and accruals. Some accruals reverse in the following month. At year end, the company posts closing entries so students can work with a realistic annual reporting cycle.

## Why This Story Works for Business Students

This company story is useful because it creates one connected learning environment:

- operations students can understand why a document exists
- accounting students can see when a transaction posts
- analytics students can aggregate and compare trends
- audit students can test completeness, approval, timing, and exception patterns

The goal is not to simulate every ERP feature. The goal is to give students one business they can understand deeply enough to analyze from several perspectives.

## What Is Intentionally Simplified

The current story is still a teaching model, not a full corporate simulation.

The dataset currently does **not** include:

- manufacturing orders
- bills of materials
- work-in-process accounting
- production completions
- detailed payroll subledgers

Those topics remain future expansions.

## Recommended Next Reading

1. Read [dataset-overview.md](dataset-overview.md) for the database scope and glossary.
2. Read [process-flows.md](process-flows.md) for the detailed process map.
3. Read [database-guide.md](database-guide.md) when you are ready to navigate the tables.
