---
title: Analytics Guides
description: Starter map for financial, managerial, and audit analytics using the published dataset.
slug: /analytics
sidebar_label: Analytics Guides
---

# Analytics Guides

Once the company story and the business cycles are clear, the analytics layer becomes the place where students interpret what those cycles mean. The goal is not to leave the process behind. The goal is to follow the process forward into reporting, statements, working capital, payroll, planning, controls, and business judgment.

The analytics layer is the bridge from process understanding into analytical interpretation. It is the point where operational evidence becomes management questions, control questions, and accounting explanations.

## From Process to Analysis

| Process backbone | Main analytical destinations |
|---|---|
| `O2C` | [Commercial and Working Capital](reports/commercial-and-working-capital.md), [Financial Analytics](financial.md), [O2C Trace Case](cases/o2c-trace-case.md) |
| `P2P` | [Commercial and Working Capital](reports/commercial-and-working-capital.md), [Financial Analytics](financial.md), [P2P Accrual Case](cases/p2p-accrual-settlement-case.md) |
| `Manufacturing` | [Operations and Risk](reports/operations-and-risk.md), [Managerial Analytics](managerial.md), [Manufacturing Labor Case](cases/manufacturing-labor-cost-case.md) |
| `Payroll` | [Payroll and Workforce](reports/payroll-perspective.md), [Financial Analytics](financial.md), [Audit Analytics](audit.md) |
| `Close and statement presentation` | [Executive Overview](reports/executive-overview.md), [Financial Analytics](financial.md), [Financial Statement Bridge Case](cases/financial-statement-bridge-case.md) |

## What This Layer Includes

- topic guides for financial, managerial, and audit analytics
- student-first report pages with preview and download artifacts
- business perspectives that interpret the company from a management viewpoint
- guided SQL paths for tracing the same business logic directly in SQLite
- Excel workflow guidance using the published dataset workbook
- guided walkthrough cases that pair business process, query work, and interpretation

## Coverage Map

| Analytics area | Start with | Starter SQL focus | Paired cases | Optional Excel recreation |
|---|---|---|---|---|
| Financial accounting | [Financial Analytics](financial.md) | working capital, cash conversion, close-cycle, payroll, accruals, revenue, margin, and price realization | [Working Capital and Cash Conversion Case](cases/working-capital-and-cash-conversion-case.md), [Financial Statement Bridge Case](cases/financial-statement-bridge-case.md), [Pricing and Margin Governance Case](cases/pricing-and-margin-governance-case.md) | control-account roll-forwards, monthly bridges, settlement timing, and price-realization pivots |
| Managerial and cost accounting | [Managerial Analytics](managerial.md) | portfolio mix, contribution margin, service levels, labor mix, workforce coverage, planning, replenishment, lifecycle analysis, and pricing governance | [Product Portfolio Profitability Case](cases/product-portfolio-profitability-case.md), [Workforce Coverage and Attendance Case](cases/workforce-coverage-and-attendance-case.md), [Demand Planning and Replenishment Case](cases/demand-planning-and-replenishment-case.md), [Pricing and Margin Governance Case](cases/pricing-and-margin-governance-case.md) | pivots by collection, lifecycle, supply mode, work location, shift, work center, planning week, and pricing method |
| Audit analytics | [Audit Analytics](audit.md) | document-chain controls, approval design, master-data completeness, workforce controls, roster review, planning support, pricing governance, and anomaly review | [Workforce Cost and Org-Control Case](cases/workforce-cost-and-org-control-case.md), [Audit Review Pack Case](cases/audit-review-pack-case.md), [Attendance Control Audit Case](cases/attendance-control-audit-case.md), [Replenishment Support Audit Case](cases/replenishment-support-audit-case.md), [Pricing Governance Audit Case](cases/pricing-governance-audit-case.md) | source-table tracing and control review |
| Curated report packs | [Reports Hub](reports/index.md) | guided business perspectives plus preview-first Excel and CSV outputs for standard financial, managerial, and audit reporting | [Business Perspectives Hub](reports/lens-packs.md), [Financial Reports](reports/financial.md), [Managerial Reports](reports/managerial.md), [Audit Reports](reports/audit.md) | sample-table preview before download |
| Cross-topic navigation | [SQL Guide](sql-guide.md), [Excel Guide](excel-guide.md) | how to open the SQLite dataset, run starter SQL, and recreate the same ideas in the workbook | [Analytics Cases](cases/index.md) | workbook-side reconstruction of SQL outputs |

## Current Analytical Coverage

The current analytics layer is organized around these strengths:

- richer employee analysis through `EmployeeNumber`, `EmploymentStatus`, `JobFamily`, `JobLevel`, and `WorkLocation`
- richer product analysis through `CollectionName`, `StyleFamily`, `PrimaryMaterial`, `LifecycleStatus`, `LaunchDate`, and `SupplyMode`
- clearer working-capital, payroll-cost, and financial-statement bridge exercises
- stronger audit labs supported by the published dataset and source-table review
- richer workforce-planning review through rosters, absences, raw punches, and overtime approvals
- weekly demand-planning and MRP review through forecasts, policies, recommendations, component plans, and rough-cut capacity
- formal commercial-pricing review through price lists, promotions, override approvals, and line-level pricing lineage

## Next Steps

1. Start with the topic page that matches the business cycle you are following.
2. Move into [Reports Hub](reports/index.md) when you want a perspective-led or report-led reading of the same process.
3. Run the starter SQL in [SQL Guide](sql-guide.md) when you want to trace the logic directly.
4. Open [Analytics Cases](cases/index.md) when you want a guided process-to-analysis walkthrough.
5. Use [Excel Guide](excel-guide.md) when you want to reconstruct the same ideas in the workbook.
