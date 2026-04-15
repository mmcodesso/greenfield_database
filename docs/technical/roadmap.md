---
title: Roadmap
description: Planned future expansion areas for the dataset and documentation.
slug: /roadmap
sidebar_label: Roadmap
---

# Roadmap

Use this page for current-versus-future scope. The rest of the documentation describes the current dataset release and teaching workflow.

## Implemented in the Current Release

### Core business processes and accounting

- five fiscal years of data from 2026 through 2030
- order-to-cash, returns, procure-to-pay, manufacturing, payroll, and close-cycle activity
- event-based postings into `GLEntry` with source-to-ledger traceability
- accrued-expense settlement, payroll cash movement, and year-end close activity

### Workforce, payroll, and time tracking

- approved daily time clocks, attendance exceptions, overtime approvals, and payroll periods
- labor allocation that connects payroll support to manufacturing activity
- richer employee master data with role, lifecycle, work location, and current-state assignment coverage
- audit coverage for employee validity, approvals, roster controls, punch controls, and overtime controls

### Planning and replenishment

- weekly demand forecasts and inventory policies
- replenishment recommendations for purchasing and manufacturing demand
- `MaterialRequirementPlan` and `RoughCutCapacityPlan` to connect planning pressure to execution
- analytics and audit queries for forecast quality, planning support, and recommendation timing

### Pricing and commercial governance

- formal price lists, promotions, and override approvals
- pricing lineage from commercial policy into O2C documents and margin analysis
- audit coverage for price-floor review, expired pricing, promotion scope, and override completeness

### Analytics, cases, and teaching materials

- starter SQL coverage across financial, managerial, audit, and cost-accounting topics
- guided walkthrough cases that connect business context, queries, and interpretation
- company, process, dataset, schema, and posting documentation that supports classroom adoption
- Excel and support-workbook guidance for workbook-based analysis and exception review

### Technical delivery and validation

- SQLite, Excel, support workbook, CSV zip, and generation log outputs
- validation scopes for `core`, `operational`, and `full` checks
- anomaly logging and validation exception reporting
- local generation settings for full release, fast validation, and performance profiling

## Future Implementations and Improvements

- deeper workforce detail, including raw punch-event tables beneath approved daily time rows
- richer schedule modeling, including rotating shift rosters and shift-level capacity calendars
- deeper manufacturing structure, including subassemblies and multi-level BOM support
- continued growth in analytics cases, teaching notes, and adoption materials as the classroom library expands
