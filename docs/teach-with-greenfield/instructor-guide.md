---
title: Instructor Adoption Guide
description: Course adoption guidance for instructors using the Greenfield Accounting Dataset in accounting analytics classes.
slug: /teach-with-greenfield/instructor-adoption
sidebar_label: Instructor Adoption
---

# Instructor Adoption Guide

## Adopt Greenfield in 4 Steps

### 1. Choose the student entry point

For most classes, students should start with the teaching files and the website, not the codebase.

Give students:

- the SQLite database for SQL work
- the Excel workbook for spreadsheet-based analysis
- the documentation site for orientation and guided reading

Use the generator itself mainly for instructor prep, custom builds, or contribution work.
Use [Dataset Delivery and Build Setup](../technical/dataset-delivery.md) when you need to produce or package those files locally.

### 2. Pick the course emphasis

| If your course emphasizes... | Start with | Then assign |
|---|---|---|
| AIS or business processes | [Company Story](../learn-the-business/company-story.md), [Process Flows](../learn-the-business/process-flows.md) | document tracing, process mapping, source-to-ledger explanations |
| SQL and accounting analytics | [Start Here](../start-here/index.md), [SQL Guide](../analytics/sql-guide.md) | starter SQL packs and guided cases |
| Excel-based analytics | [Start Here](../start-here/index.md), [Excel Guide](../analytics/excel-guide.md) | workbook-based pivots, charts, and interpretation work |
| Auditing and controls | [Audit Analytics](../analytics/audit.md) | anomaly-focused labs and control-review exercises |
| Managerial or cost accounting | [Managerial Analytics](../analytics/managerial.md) | BOM, labor, variance, cost-center, and capacity analysis |

### 3. Sequence the material from business to analysis

The recommended rule is simple: process understanding first, analytics second.

Suggested student sequence:

1. [Start Here](../start-here/index.md)
2. [Company Story](../learn-the-business/company-story.md)
3. [Process Flows](../learn-the-business/process-flows.md)
4. [Dataset Guide](../start-here/dataset-overview.md)
5. [Analytics Hub](../analytics/index.md)
6. topic-specific analytics pages and cases

### 4. Decide how you will deliver the published dataset

- Use the published SQLite database and Excel workbook as the core student file set.
- Share `greenfield_support.xlsx` when the course includes exception review, audit exercises, or validation context.
- Use [Dataset Delivery and Build Setup](../technical/dataset-delivery.md) when you need local generation commands or release preparation details.

## What to Share With Students vs Keep for Teaching Setup

### Student-ready material

Share these directly with students:

- [Start Here](../start-here/index.md)
- [Company Story](../learn-the-business/company-story.md)
- [Dataset Guide](../start-here/dataset-overview.md)
- [Process Flows](../learn-the-business/process-flows.md)
- [Schema Reference](../reference/schema.md)
- [GLEntry Posting Reference](../reference/posting.md)
- [Analytics Hub](../analytics/index.md)
- [Financial Analytics](../analytics/financial.md)
- [Managerial Analytics](../analytics/managerial.md)
- [Audit Analytics](../analytics/audit.md)
- [SQL Guide](../analytics/sql-guide.md)
- [Excel Guide](../analytics/excel-guide.md)
- [Analytics Cases](../analytics/cases/index.md)

### Instructor-only or setup-focused material

Use these when you need local build setup, generator context, or release-planning detail:

- [Dataset Delivery and Build Setup](../technical/dataset-delivery.md)
- [Technical Guide](../technical/technical-guide.md)
- [Roadmap](../technical/roadmap.md)

## Recommended Course Delivery Pattern

| Week or module | Teaching goal | Main docs | Main starter assets |
|---|---|---|---|
| 1. Orientation | Explain the company, dataset purpose, and student workflow | [Start Here](../start-here/index.md), [Company Story](../learn-the-business/company-story.md), [Dataset Guide](../start-here/dataset-overview.md) | SQLite or Excel teaching package |
| 2. Process mapping | Show O2C, P2P, manufacturing, payroll, and close-cycle flow | [Process Flows](../learn-the-business/process-flows.md) and process guides | None yet |
| 3. Table navigation | Teach keys, joins, and traceability | [Dataset Guide](../start-here/dataset-overview.md) | Introductory ad hoc joins |
| 4. Financial analytics | Connect operational activity to accounting review | [Financial Analytics](../analytics/financial.md) | `queries/financial/` |
| 5. Working-capital and statement bridge | Connect subledgers to control accounts and close | [Financial Analytics](../analytics/financial.md), [Analytics Cases](../analytics/cases/index.md) | financial starter SQL plus the working-capital and statement-bridge cases |
| 6. Managerial analytics | Analyze portfolio mix, costs, labor, inventory, and operations | [Managerial Analytics](../analytics/managerial.md) | `queries/managerial/` plus the portfolio-profitability case |
| 7. Audit analytics | Review completeness, controls, master data, and anomalies | [Audit Analytics](../analytics/audit.md) | `queries/audit/` plus the workforce and audit-review-pack cases |
| 8. Guided assignments | Use structured walkthroughs before open-ended work | [Analytics Cases](../analytics/cases/index.md) | case docs plus starter SQL |

This sequence compresses cleanly into fewer modules or expands into a full semester.

## Adoption Checklist

- Decide whether students will work primarily in SQL, Excel, or both.
- Share the packaged output files before asking students to inspect code.
- Use [Dataset Delivery and Build Setup](../technical/dataset-delivery.md) when you need to build or refresh the package locally.
- Assign the company and process reading before the first query exercise.
- Pick one analytics track first: financial, managerial, or audit.
- Use guided cases before open-ended student prompts if the class is new to integrated business datasets.
- Reserve schema, posting, and architecture references for advanced work or instructor prep.

## Teaching Notes

- Start with why each document exists before discussing table structure.
- Use `GLEntry` only after students understand which source events post and which do not.
- For auditing classes, explain how the published dataset and support workbook work together.
- For beginner SQL classes, start from the provided queries before moving to blank-screen assignments.
- For Excel-heavy classes, use the workbook and process docs together so students can interpret patterns while they build pivots.

## Recommended Classroom Sequence

1. Use the published dataset package as the core student file set.
2. Start financial classes with the working-capital and statement-bridge cases.
3. Start managerial classes with the product-portfolio profitability case.
4. Start audit classes with the workforce cost and org-control case, then move to the audit review pack.
5. Use the expanded audit queries to separate role-family issues, approval-limit issues, current-state assignment issues, and item-status issues within the published dataset.
6. Add the workforce coverage case when students are ready to compare rostered hours, worked hours, absences, and overtime.
7. Add the attendance control audit case when students need a deeper roster, punch, and overtime-control lab.
8. Add the demand-planning case when students are ready to connect forecast, replenishment, MRP, and rough-cut capacity.
9. Add the replenishment-support audit case when students need to test forecast approval, policy status, and recommendation conversion support.
10. Add the pricing and margin case when students are ready to connect list price, promotions, overrides, and realized margin.
11. Add the pricing-governance audit case when students need a commercial-controls lab around expired pricing, price-floor breaches, and override completeness.
12. Use guided comparisons across years, processes, or topic packs after students understand the core dataset.

## Where to Go Next

- Use [Start Here](../start-here/index.md) as the primary student launch page.
- Use [Analytics Hub](../analytics/index.md) to choose the first topic pack.
- Use [Schema Reference](../reference/schema.md) and [GLEntry Posting Reference](../reference/posting.md) as shared student and instructor references during assignments.
