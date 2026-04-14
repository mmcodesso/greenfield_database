---
title: Company Story
description: Business context for students before they move into tables, SQL, or analytics.
slug: /company-story
sidebar_label: Company Story
---

# The Company


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
- a realistic people-and-product master-data layer used for control and analytics work

## What Greenfield Sells

Greenfield sells product families that are easy to visualize and analyze:

- furniture
- lighting
- textiles
- accessories

Some of those products are purchased ready-made. Others are produced internally from raw materials and packaging. That distinction matters for costing, variance analysis, and margin analysis.

The catalog uses named collections and style families. That structure makes product-profitability and lifecycle analysis more realistic for classroom work.

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

Greenfield now processes payroll operationally. Hourly employees are assigned to shifts and receive approved daily time-clock records, employees are paid on a biweekly cycle, payroll liabilities are remitted later, and manufacturing labor is traced into product cost through labor-time entries and reclass journals.

This matters because the same dataset can now support:

- gross-to-net payroll analysis
- payroll liability roll-forwards
- direct labor by work order
- unit-cost bridges for manufactured products

The employee master is also intentionally more realistic. Greenfield has one CEO, one CFO, one Controller, one Production Manager, and one Accounting Manager. Repeatable roles such as sales reps, buyers, assemblers, machine operators, and shipping clerks can appear many times. Employees who leave the company remain in the dataset for historical traceability, which creates useful audit scenarios.

### 6. Close the books

Finance records opening balances, recurring journals, accrued-expense estimates, rare accrual adjustments, factory-overhead journals, manufacturing labor and overhead reclasses, and year-end close entries.

That gives students a full accounting environment with operational and finance activity in the same model.

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

- raw punch-event tables beneath the current approved daily time-clock rows
- rotating shift rosters or shift-level capacity calendars
- subassemblies or multi-level BOMs

Those topics remain future extensions.

## Recommended Next Reading

1. Read [Dataset Guide](../start-here/dataset-overview.md) for scope, glossary, and navigation.
2. Read [Process Flows](process-flows.md) for the process map.
3. Read [Analytics Hub](../analytics/index.md) when you are ready to start the analysis layer.
