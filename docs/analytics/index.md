---
title: Analytics Hub
description: Starter map for financial, managerial, and audit analytics using Greenfield.
slug: /analytics
sidebar_label: Analytics Hub
---

# Analytics Starter Layer

## What This Starter Layer Includes

- topic guides for financial, managerial, and audit analytics
- a SQLite-first starter SQL package in `queries/`
- Excel workflow guidance using the dataset workbook and support workbook
- richer employee and item master fields for role, lifecycle, and catalog analysis
- guided walkthrough cases that pair query packs with business scenarios

## Recommended Progression

Use this sequence for most student work:

1. read the topic page
2. run the starter SQL files in that topic
3. open the paired case
4. recreate one or two ideas in Excel

## Coverage Map

| Analytics area | Start with | Starter SQL focus | Paired Phase 19 case | Optional Excel recreation |
|---|---|---|---|---|
| Financial accounting | [Financial Analytics](financial.md) | working capital, cash conversion, close-cycle, payroll, accruals, revenue, and margin | [Working Capital and Cash Conversion Case](cases/working-capital-and-cash-conversion-case.md), [Financial Statement Bridge Case](cases/financial-statement-bridge-case.md) | control-account roll-forwards, monthly bridges, and settlement timing |
| Managerial and cost accounting | [Managerial Analytics](managerial.md) | portfolio mix, contribution margin, service levels, labor mix, manufacturing, and lifecycle analysis | [Product Portfolio Profitability Case](cases/product-portfolio-profitability-case.md) | pivots by collection, lifecycle, supply mode, and work location |
| Audit analytics | [Audit Analytics](audit.md) | document-chain controls, approval design, master-data completeness, workforce controls, and anomaly review | [Workforce Cost and Org-Control Case](cases/workforce-cost-and-org-control-case.md), [Audit Review Pack Case](cases/audit-review-pack-case.md) | support-workbook review plus source-sheet tracing |
| Cross-topic navigation | [SQL Guide](sql-guide.md), [Excel Guide](excel-guide.md) | how to run the query pack and recreate the same ideas in the workbook | [Analytics Cases](cases/index.md) | workbook-side reconstruction of SQL outputs |

## Current Focus Areas

Phase 18 and Phase 19 make the current analytics layer stronger in four ways:

- richer employee analysis through `EmployeeNumber`, `EmploymentStatus`, `JobFamily`, `JobLevel`, and `WorkLocation`
- richer product analysis through `CollectionName`, `StyleFamily`, `PrimaryMaterial`, `LifecycleStatus`, `LaunchDate`, and `SupplyMode`
- clearer working-capital, payroll-cost, and financial-statement bridge exercises
- better anomaly-enabled audit labs without requiring a separate teaching profile

## Default Build Guidance

- The default anomaly-enabled build is the main student-facing package.
- Use the clean validation build mainly for instructor prep, quick checks, or baseline comparison.
- Financial and managerial queries work well on either build.
- Audit queries are usually more informative on the default anomaly-enabled build.

## Where to Go Next

- Start with [Financial Analytics](financial.md), [Managerial Analytics](managerial.md), or [Audit Analytics](audit.md).
- Then open [Analytics Cases](cases/index.md) for guided walkthroughs.
- Use [Excel Guide](excel-guide.md) when you want to reconstruct the same ideas in the workbook.
