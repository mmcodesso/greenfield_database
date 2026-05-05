---
title: Cases
description: Guided walkthroughs that connect business context, starter SQL, and classroom interpretation.
sidebar_label: Cases
---

# Cases

Cases are guided accounting analytics assignments. Each one connects business context, SQL evidence, source-table reasoning, and a short management or audit conclusion. Students should enter a case after reading the matching process page or report perspective; the case then turns that context into a structured investigation.

Every case now expects a required student output: evidence summary, accounting or business interpretation, database explanation, and a follow-up conclusion. The SQL sequence is still inquiry-led, but the deliverable is no longer open-ended.

For first undergraduate assignments, start with the Foundation cases. Intermediate cases work well after students can read source tables and interpret a report. Advanced and Capstone cases should usually come later because they combine more processes, more controls, or more query paths.

## Difficulty Labels

| Level | What it means for students |
|---|---|
| Foundation | Good first case after one process page; the trace is narrow and the expected output is concrete. |
| Intermediate | Requires comparing several measures or business lenses, but still stays inside one main topic. |
| Advanced | Requires synthesis across accounting, process timing, controls, or multiple source-table paths. |
| Capstone | Best for branch-choice review after students already know how to trace evidence and classify findings. |

## Learning Arcs

- Foundation process tracing: [O2C Trace Case](o2c-trace-case.md), [P2P Accrual Case](p2p-accrual-settlement-case.md), [Manufacturing Labor Case](manufacturing-labor-cost-case.md), and [Product Portfolio Case](product-portfolio-and-lifecycle-case.md)
- Financial interpretation: [Working Capital and Cash Conversion Case](working-capital-and-cash-conversion-case.md), [Financial Statement Bridge Case](financial-statement-bridge-case.md), [CAPEX and Fixed Asset Lifecycle Case](capex-fixed-asset-lifecycle-case.md), and [Pricing and Margin Governance Case](pricing-and-margin-governance-case.md)
- Managerial planning and performance: [Product Portfolio Profitability Case](product-portfolio-profitability-case.md), [Workforce Coverage and Attendance Case](workforce-coverage-and-attendance-case.md), and [Demand Planning and Replenishment Case](demand-planning-and-replenishment-case.md)
- Audit and controls: [Audit Review Pack Case](audit-review-pack-case.md) plus the specialized workforce, attendance, replenishment, and pricing audit cases

## Case Matrix

| Seq. | Case | Level | Primary accounting concept | Primary database skill | Best prerequisite |
|---:|---|---|---|---|---|
| 1 | [O2C Trace Case](o2c-trace-case.md) | Foundation | revenue, inventory relief, AR settlement | document-chain joins from order to cash | [Order-to-Cash Process](../../processes/o2c.md) |
| 2 | [P2P Accrual Case](p2p-accrual-settlement-case.md) | Foundation | AP, GRNI, accrued-service settlement | receipt-matched versus accrual-linked trace paths | [Procure-to-Pay Process](../../processes/p2p.md) |
| 3 | [Manufacturing Labor Case](manufacturing-labor-cost-case.md) | Foundation | standard cost, direct labor, WIP close | work-order operation and labor-support tracing | [Manufacturing Process](../../processes/manufacturing.md) |
| 4 | [Product Portfolio Case](product-portfolio-and-lifecycle-case.md) | Foundation | item lifecycle and portfolio activity | item-master attributes joined to operating activity | [Managerial Queries](../managerial.md) |
| 5 | [Working Capital and Cash Conversion Case](working-capital-and-cash-conversion-case.md) | Advanced synthesis | AR, AP, payroll, accruals, and cash pressure | monthly timing synthesis across multiple systems | [Commercial and Working Capital](../reports/commercial-and-working-capital.md) |
| 6 | [Financial Statement Bridge Case](financial-statement-bridge-case.md) | Advanced | trial balance, control accounts, close, cutoff | ledger-to-statement bridge with source drilldown | [Executive Overview](../reports/executive-overview.md) |
| 7 | [CAPEX and Fixed Asset Lifecycle Case](capex-fixed-asset-lifecycle-case.md) | Intermediate | capitalization, depreciation, financing, disposal | asset event trace to financing, GL, and cash flow | [Financial Queries](../financial.md) |
| 8 | [Pricing and Margin Governance Case](pricing-and-margin-governance-case.md) | Intermediate | price realization and margin dilution | pricing outcome aggregation by customer and portfolio | [Commercial and Working Capital](../reports/commercial-and-working-capital.md) |
| 9 | [Product Portfolio Profitability Case](product-portfolio-profitability-case.md) | Intermediate | gross margin, contribution, service, returns | comparing portfolio grains across performance lenses | [Operations and Risk](../reports/operations-and-risk.md) |
| 10 | [Workforce Coverage and Attendance Case](workforce-coverage-and-attendance-case.md) | Intermediate | labor coverage, absence, overtime response | roster, worked-hour, absence, and shift grains | [Payroll Perspective](../reports/payroll-perspective.md) |
| 11 | [Demand Planning and Replenishment Case](demand-planning-and-replenishment-case.md) | Intermediate | forecast quality, replenishment, capacity pressure | weekly item, recommendation, and work-center joins | [Operations and Risk](../reports/operations-and-risk.md) |
| 12 | [Workforce Audit Case](master-data-and-workforce-audit-case.md) | Advanced | employee lifecycle and approval-control trust | employee status, assignment, approval, and roster traces | [Payroll Process](../../processes/payroll.md) |
| 13 | [Workforce Cost and Org-Control Case](workforce-cost-and-org-control-case.md) | Advanced | payroll cost, labor utilization, control ownership | payroll, headcount, location, and approval grains | [Payroll Perspective](../reports/payroll-perspective.md) |
| 14 | [Audit Review Pack Case](audit-review-pack-case.md) | Capstone | cross-process exception triage | branch-choice source evidence across audit families | [Audit Queries](../audit.md) |
| 15 | [Attendance Control Audit Case](attendance-control-audit-case.md) | Advanced | attendance and payroll-control exceptions | employee-date exception tracing | [Payroll Process](../../processes/payroll.md) |
| 16 | [Replenishment Support Audit Case](replenishment-support-audit-case.md) | Advanced | planning-support control evidence | forecast, policy, recommendation, and document trace | [Audit Queries](../audit.md) |
| 17 | [Pricing Governance Audit Case](pricing-governance-audit-case.md) | Advanced | price-list, promotion, floor, and override controls | price-list, promotion, and approval source tracing | [Audit Queries](../audit.md) |

## How Cases Fit the Learning Path

Read the case library as a deeper layer beneath the process, report, and analytics-guide pages:

1. Start with the company story and the process page for the cycle.
2. Move into the matching report perspective or topic guide.
3. Run the case SQL in sequence and keep notes on what each step changes.
4. Submit the required student output: evidence, interpretation, database explanation, and conclusion.
5. Recreate one part of the evidence in Excel when the class needs workbook-side reinforcement.

## Suggested Case Sequence

Start with the foundation cases when students are still learning the database and business process flow. Move to the financial and managerial cases when they can explain source rows and ledgers together. Use the specialized audit cases after students understand the related business process, because those pages assume they can tell the difference between operational pressure and control failure.

The [Audit Review Pack Case](audit-review-pack-case.md) is a capstone and branch-choice assignment. It has many query references by design, so instructors should assign one or two exception families unless the class is ready for a broad review.

The [Working Capital and Cash Conversion Case](working-capital-and-cash-conversion-case.md) is an advanced synthesis assignment. It intentionally combines customer, supplier, payroll, accrual, and budget timing rather than tracing one document chain.

## Next Steps

1. Start from [Analyze the Data](../index.md), [Query Library](../analysis-tracks.md), or [Reports Hub](../reports/index.md) when you need the broader business context first.
2. Pick the case that matches the process you want to investigate.
3. Use [SQL Guide](../sql-guide.md) for query-running workflow and [Excel Guide](../excel-guide.md) for workbook-side reconstruction.
