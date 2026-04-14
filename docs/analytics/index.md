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

| Analytics area | Start with | Starter SQL focus | Paired cases | Optional Excel recreation |
|---|---|---|---|---|
| Financial accounting | [Financial Analytics](financial.md) | working capital, cash conversion, close-cycle, payroll, accruals, revenue, margin, and price realization | [Working Capital and Cash Conversion Case](cases/working-capital-and-cash-conversion-case.md), [Financial Statement Bridge Case](cases/financial-statement-bridge-case.md), [Pricing and Margin Governance Case](cases/pricing-and-margin-governance-case.md) | control-account roll-forwards, monthly bridges, settlement timing, and price-realization pivots |
| Managerial and cost accounting | [Managerial Analytics](managerial.md) | portfolio mix, contribution margin, service levels, labor mix, workforce coverage, planning, replenishment, lifecycle analysis, and pricing governance | [Product Portfolio Profitability Case](cases/product-portfolio-profitability-case.md), [Workforce Coverage and Attendance Case](cases/workforce-coverage-and-attendance-case.md), [Demand Planning and Replenishment Case](cases/demand-planning-and-replenishment-case.md), [Pricing and Margin Governance Case](cases/pricing-and-margin-governance-case.md) | pivots by collection, lifecycle, supply mode, work location, shift, work center, planning week, and pricing method |
| Audit analytics | [Audit Analytics](audit.md) | document-chain controls, approval design, master-data completeness, workforce controls, roster review, planning support, pricing governance, and anomaly review | [Workforce Cost and Org-Control Case](cases/workforce-cost-and-org-control-case.md), [Audit Review Pack Case](cases/audit-review-pack-case.md), [Attendance Control Audit Case](cases/attendance-control-audit-case.md), [Replenishment Support Audit Case](cases/replenishment-support-audit-case.md), [Pricing Governance Audit Case](cases/pricing-governance-audit-case.md) | support-workbook review plus source-sheet tracing |
| Cross-topic navigation | [SQL Guide](sql-guide.md), [Excel Guide](excel-guide.md) | how to run the query pack and recreate the same ideas in the workbook | [Analytics Cases](cases/index.md) | workbook-side reconstruction of SQL outputs |

## Current Analytical Coverage

The current analytics layer is organized around these strengths:

- richer employee analysis through `EmployeeNumber`, `EmploymentStatus`, `JobFamily`, `JobLevel`, and `WorkLocation`
- richer product analysis through `CollectionName`, `StyleFamily`, `PrimaryMaterial`, `LifecycleStatus`, `LaunchDate`, and `SupplyMode`
- clearer working-capital, payroll-cost, and financial-statement bridge exercises
- stronger audit labs supported by the published dataset and the support workbook
- richer workforce-planning review through rosters, absences, raw punches, and overtime approvals
- weekly demand-planning and MRP review through forecasts, policies, recommendations, component plans, and rough-cut capacity
- formal commercial-pricing review through price lists, promotions, override approvals, and line-level pricing lineage

## Using the Published Dataset

- Financial and managerial analysis can begin directly in the SQLite database or Excel workbook.
- Audit work often benefits from `greenfield_support.xlsx` because it adds anomaly and validation context.
- Some audit queries are designed to surface exceptions that appear in the published dataset.

## Where to Go Next

- Start with [Financial Analytics](financial.md), [Managerial Analytics](managerial.md), or [Audit Analytics](audit.md).
- Then open [Analytics Cases](cases/index.md) for guided walkthroughs.
- Use [Excel Guide](excel-guide.md) when you want to reconstruct the same ideas in the workbook.
