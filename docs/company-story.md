# Company Story

**Audience:** Students, instructors, and analysts who need business context before reading tables or SQL.  
**Purpose:** Explain who Greenfield Home Furnishings is and how the company operates.  
**What you will learn:** The company narrative, why the processes exist, and how the operating model supports accounting analytics coursework.

> **Implemented in current generator:** A hybrid manufacturer-distributor with O2C, P2P, manufacturing, payroll, recurring journals, and year-end close.

> **Planned future extension:** Routings, capacity planning, time clocks, and deeper production-planning detail.

## The Company in Plain Language

Greenfield Home Furnishings, Inc. is a fictional mid-sized U.S. company that sells home furnishings to commercial buyers, interior-design firms, and repeat regional customers.

Greenfield operates in two ways at the same time:

- it **buys** some finished goods from suppliers and resells them
- it **manufactures** a selected subset of finished goods in-house from raw materials and packaging

That hybrid model connects:

- customer demand
- supplier purchasing
- production activity
- inventory movement
- payroll and labor usage
- accounting results

## What Greenfield Sells

Greenfield sells product families that are easy to visualize and analyze:

- furniture
- lighting
- textiles
- accessories

Some of those products are purchased ready-made. Others are produced internally from raw materials and packaging. That distinction matters for costing, variance analysis, and margin analysis.

## How Greenfield Operates

Greenfield's business story has six main threads.

### 1. Sell and ship to customers

The sales team enters customer orders. Warehouse operations ship goods when inventory is available. Accounting invoices from shipment lines, not directly from order lines. Treasury records customer receipts and applies them to invoices.

### 2. Correct customer-side exceptions

Some shipments come back because of damage, order changes, or service problems. Warehouse staff receive the return, accounting issues a credit memo, and treasury refunds the customer if the original invoice had already been settled.

### 3. Buy raw materials, packaging, and finished goods

Employees create purchase requisitions. Purchasing converts them into purchase orders. Warehouses receive goods, suppliers invoice the company, and treasury pays approved invoices.

That means the same dataset supports both:

- resale purchasing for finished goods
- manufacturing replenishment for materials and packaging

### 4. Manufacture selected products

The manufacturing team plans work orders for selected finished goods. Raw materials and packaging are issued to production, finished goods are completed into inventory, and work orders are closed with material, direct-labor, and overhead variance when actual and standard amounts differ.

### 5. Run payroll and connect labor to cost

Greenfield now processes payroll operationally. Employees are paid on a biweekly cycle, payroll liabilities are remitted later, and manufacturing labor is traced into product cost through labor-time entries and reclass journals.

This matters because the same dataset can now support:

- gross-to-net payroll analysis
- payroll liability roll-forwards
- direct labor by work order
- unit-cost bridges for manufactured products

### 6. Close the books

Finance records opening balances, recurring journals, accrued-expense estimates, rare accrual adjustments, factory-overhead journals, manufacturing labor and overhead reclasses, and year-end close entries.

That gives students a full accounting environment, not only an operational database.

## Why This Story Works for Business Students

The company is intentionally realistic but still teachable.

Students can ask:

- What happened operationally?
- When did accounting recognize it?
- Which ledger accounts changed?
- Which documents and controls were involved?
- How do purchased and manufactured products behave differently?
- How does payroll connect to product cost and margin analysis?

## What Is Still Simplified

The current dataset is a teaching model, not a full ERP simulation.

The current implementation does **not** include:

- time clocks or shift scheduling
- capacity planning
- subassemblies or multi-level BOMs
- detailed labor planning beyond the payroll-period model

Those topics remain future extensions.

## Recommended Next Reading

1. Read [dataset-overview.md](dataset-overview.md) for scope and glossary.
2. Read [process-flows.md](process-flows.md) for the process map.
3. Read [database-guide.md](database-guide.md) when you are ready to navigate the tables.
