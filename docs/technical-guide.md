---
title: Technical Guide
description: System-level guide for contributors and advanced users working with the generator.
sidebar_label: Technical Guide
---

# Technical Guide

## What This Guide Covers

Use this page when you need the current design view of:

- what the dataset contains
- how the generator builds it
- how processes map to postings
- how validations and exports fit together

Use [Code Architecture](code-architecture.md) for a more code-centric, module-by-module explanation.

## Current System at a Glance

The current implementation has seven layers:

| Layer | Main content |
|---|---|
| Business context | Greenfield Home Furnishings, company story, and operating processes |
| Operational tables | O2C, P2P, and manufacturing documents plus master data |
| Payroll layer | Shift definitions, shift assignments, time clocks, payroll periods, labor time, payroll registers, payments, and remittances |
| Accounting layer | `JournalEntry`, `GLEntry`, and the chart of accounts |
| Planning layer | Budgets, cost centers, payroll periods, and manufacturing standard structures |
| Control layer | Validations, anomaly injection, and reporting |
| Delivery layer | SQLite, Excel, JSON, and generation-log outputs |

## Table Families

The implemented schema is organized into seven groups:

| Group | Coverage |
|---|---|
| Accounting core | `Account`, `JournalEntry`, `GLEntry` |
| O2C | Orders, shipments, billing, receipt applications, returns, credits, refunds |
| P2P | Requisitions, purchase orders, receipts, supplier invoices, disbursements |
| Manufacturing | BOMs, work centers, capacity calendars, routings, work-order schedules, material issues, completions, and work-order close |
| Payroll | Payroll periods, labor time, payroll registers, payments, remittances |
| Master data | Customers, suppliers, items, employees, warehouses |
| Organizational planning | Cost centers and budgets |

The canonical column definitions live in `src/greenfield_dataset/schema.py`.

## End-to-End Build Flow

```mermaid
flowchart LR
    S[Load Settings]
    C[Initialize Context]
    E[Create Empty Tables]
    M[Generate Master Data]
    B[Generate Opening Balances and Budgets]
    T[Generate Monthly O2C Demand]
    R[Generate Monthly P2P Demand]
    F[Generate Manufacturing Demand and Activity]
    L[Generate Payroll and Labor Activity]
    J[Generate Recurring Manual Journals]
    S1[Generate Accrued-Service Settlements]
    A1[Generate Rare Accrual Adjustments]
    P[Post Operational Events]
    Y[Generate Year-End Close]
    V[Validate]
    A[Inject Anomalies]
    X[Export]

    S --> C --> E --> M --> B --> T --> R --> F --> L --> J --> S1 --> A1 --> P --> Y --> V --> A --> X
```

In plain language, the build works like this:

1. load settings and initialize the shared generation context
2. create empty DataFrames for all implemented tables
3. generate master data such as accounts, cost centers, employees, warehouses, items, customers, suppliers, BOMs, work centers, routings, and work-center calendars
4. generate opening balances and budget rows
5. generate monthly O2C demand
6. generate monthly P2P demand and manufacturing-driven requisitions
7. generate monthly receiving and manufacturing activity
8. generate payroll periods, labor time, payroll registers, payments, remittances, and work-order close inputs
9. generate shipments, billing, collections, returns, supplier invoicing, and disbursements
10. generate recurring manual journals
11. generate direct service supplier invoices and payments that settle prior accrued expenses
12. generate rare accrual-adjustment journals for residual over-accrual cleanup
13. post operational and payroll events into `GLEntry`
14. generate year-end close journals after operational posting is complete
15. validate the clean dataset, inject anomalies, revalidate, and export

## Module Responsibilities

| Module | Current role |
|---|---|
| `settings.py` | Load YAML configuration and initialize the shared runtime context |
| `calendar.py` | Build the fiscal calendar |
| `schema.py` | Define `TABLE_COLUMNS` and create empty tables |
| `master_data.py` | Generate accounts, cost centers, employees, warehouses, items, customers, and suppliers |
| `manufacturing.py` | Generate BOMs, work centers, work-center calendars, routings, operation schedules, manufacturing-driven requisitions, work orders, material issues, completions, and work-order close |
| `payroll.py` | Generate shift definitions, shift assignments, time clocks, labor time, payroll periods, payroll registers, payroll payments, liability remittances, and manufacturing labor helpers |
| `budgets.py` | Generate opening balances and budgets |
| `o2c.py` | Generate orders, shipments, invoices, receipts, applications, returns, credits, and refunds |
| `p2p.py` | Generate requisitions, purchase orders, receipts, supplier invoices, and disbursements |
| `journals.py` | Generate recurring journals, accrued-expense estimates, rare accrual adjustments, factory overhead, manufacturing labor / overhead reclasses, and year-end close |
| `posting_engine.py` | Convert source events into balanced GL entries |
| `validations.py` | Run document, accounting, payroll, manufacturing, and roll-forward checks |
| `anomalies.py` | Inject configured anomalies and log them |
| `state_cache.py` | Provide shared lazy-build cache helpers used by generation and validation |
| `exporters.py` | Write SQLite, Excel, and JSON outputs |
| `main.py` | Orchestrate the full build and write the generation log |

## Process and Posting Design

The generator uses event-based accounting.

Major posting triggers:

- `Shipment`
- `SalesInvoice`
- `CashReceipt`
- `CashReceiptApplication`
- `SalesReturn`
- `CreditMemo`
- `CustomerRefund`
- `GoodsReceipt`
- `PurchaseInvoice`
- `DisbursementPayment`
- `MaterialIssue`
- `ProductionCompletion`
- `WorkOrderClose`
- `PayrollRegister`
- `PayrollPayment`
- `PayrollLiabilityRemittance`
- `JournalEntry`

The detailed posting reference lives in [Posting Reference](reference/posting.md).

## Validation and Control Model

Clean-build validations cover:

- schema consistency
- header-to-line totals
- orphan-row detection
- over-shipment, over-receipt, over-invoicing, overpayment, and over-return checks
- receipt-application and refund integrity
- payroll gross-to-net, payment, remittance, and labor-linkage integrity
- hourly payroll support from approved time clocks
- status consistency checks
- voucher balance and trial balance
- control-account roll-forwards for AR, AP, inventory, GRNI, sales tax, customer deposits, payroll liabilities, WIP, manufacturing clearing, and manufacturing variance
- journal header-to-GL agreement and close-cycle coverage
- manufacturing checks for BOM structure, work-order flow, issue tolerance, completion limits, close timing, and shadow inventory
- time-and-attendance checks for shift alignment, approved clock coverage, operation-window timing, and post-close labor

## Runtime Profiles and Validation Scopes

The current implementation supports three useful execution profiles:

- `config/settings.yaml` for release-grade full builds
- `config/settings_validation.yaml` for one-year fast validation
- `config/settings_perf.yaml` for short-horizon profiling runs

The main entrypoint also supports validation scopes:

- `core`
- `operational`
- `full`

That split came from Phase 15.2 and helps contributors shorten development feedback loops without changing the clean release build.

## Outputs

The current generator writes:

- SQLite database for SQL work
- Excel workbook with one worksheet per table plus anomaly and validation summary sheets
- JSON validation report
- text generation log

Most course users should start with those generated files rather than the Python code.

## Extension Point

The next clean extension points are deeper workforce planning and richer attendance detail.

Likely next additions:

- raw punch-event detail beneath the current daily time-clock row
- rotating shift rosters and richer attendance planning
- shift-level capacity and labor-availability analysis
