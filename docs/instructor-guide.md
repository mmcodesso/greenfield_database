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
Use [Dataset Delivery and Build Setup](teach-with-greenfield/dataset-delivery.md) when you need to produce or package those files locally.

### 2. Pick the course emphasis

| If your course emphasizes... | Start with | Then assign |
|---|---|---|
| AIS or business processes | [Company Story](company-story.md), [Process Flows](process-flows.md) | document tracing, process mapping, source-to-ledger explanations |
| SQL and accounting analytics | [Quick Start](student-quickstart.md), [SQL Guide](analytics/sql-guide.md) | starter SQL packs and guided cases |
| Excel-based analytics | [Quick Start](student-quickstart.md), [Excel Guide](analytics/excel-guide.md) | workbook-based pivots, charts, and interpretation work |
| Auditing and controls | [Audit Analytics](analytics/audit.md) | anomaly-focused labs and control-review exercises |
| Managerial or cost accounting | [Managerial Analytics](analytics/managerial.md) | BOM, labor, variance, cost-center, and capacity analysis |

### 3. Sequence the material from business to analysis

The recommended rule is simple: process understanding first, analytics second.

Suggested student sequence:

1. [Quick Start](student-quickstart.md)
2. [Company Story](company-story.md)
3. [Process Flows](process-flows.md)
4. [Dataset Guide](dataset-overview.md)
5. [Analytics Hub](analytics/index.md)
6. topic-specific analytics pages and cases

### 4. Decide how you will use the default versus clean build

- Use the default five-year anomaly-enabled package as the main student path.
- Use the clean baseline package mainly for instructor prep, quick demonstrations, or contrast.
- Make the distinction explicit to students. Some audit queries are supposed to return exceptions only on the default anomaly-enabled build.
- Use [Dataset Delivery and Build Setup](teach-with-greenfield/dataset-delivery.md) for the exact local build commands and profile choices.

## What to Share With Students vs Keep for Teaching Setup

### Student-ready material

Share these directly with students:

- [Quick Start](student-quickstart.md)
- [Company Story](company-story.md)
- [Dataset Guide](dataset-overview.md)
- [Process Flows](process-flows.md)
- [Schema Reference](reference/schema.md)
- [GLEntry Posting Reference](reference/posting.md)
- [Analytics Hub](analytics/index.md)
- [Financial Analytics](analytics/financial.md)
- [Managerial Analytics](analytics/managerial.md)
- [Audit Analytics](analytics/audit.md)
- [SQL Guide](analytics/sql-guide.md)
- [Excel Guide](analytics/excel-guide.md)
- [Analytics Cases](analytics/cases/index.md)

### Instructor-only or setup-focused material

Use these when you need local build setup, generator context, or release-planning detail:

- [Dataset Delivery and Build Setup](teach-with-greenfield/dataset-delivery.md)
- [Technical Guide](technical-guide.md)
- [Roadmap](roadmap.md)

## Recommended Course Delivery Pattern

| Week or module | Teaching goal | Main docs | Main starter assets |
|---|---|---|---|
| 1. Orientation | Explain the company, dataset purpose, and student workflow | [Quick Start](student-quickstart.md), [Company Story](company-story.md), [Dataset Guide](dataset-overview.md) | SQLite or Excel teaching package |
| 2. Process mapping | Show O2C, P2P, manufacturing, payroll, and close-cycle flow | [Process Flows](process-flows.md) and process guides | None yet |
| 3. Table navigation | Teach keys, joins, and traceability | [Dataset Guide](dataset-overview.md) | Introductory ad hoc joins |
| 4. Financial analytics | Connect operational activity to accounting review | [Financial Analytics](analytics/financial.md) | `queries/financial/` |
| 5. Working-capital and statement bridge | Connect subledgers to control accounts and close | [Financial Analytics](analytics/financial.md), [Analytics Cases](analytics/cases/index.md) | financial starter SQL plus the working-capital and statement-bridge cases |
| 6. Managerial analytics | Analyze portfolio mix, costs, labor, inventory, and operations | [Managerial Analytics](analytics/managerial.md) | `queries/managerial/` plus the portfolio-profitability case |
| 7. Audit analytics | Review completeness, controls, master data, and anomalies | [Audit Analytics](analytics/audit.md) | `queries/audit/` plus the workforce and audit-review-pack cases |
| 8. Guided assignments | Use structured walkthroughs before open-ended work | [Analytics Cases](analytics/cases/index.md) | case docs plus starter SQL |

This sequence compresses cleanly into fewer modules or expands into a full semester.

## Adoption Checklist

- Decide whether students will work primarily in SQL, Excel, or both.
- Share the packaged output files before asking students to inspect code.
- Use [Dataset Delivery and Build Setup](teach-with-greenfield/dataset-delivery.md) when you need to build or refresh the package locally.
- Assign the company and process reading before the first query exercise.
- Pick one analytics track first: financial, managerial, or audit.
- Use guided cases before open-ended student prompts if the class is new to integrated business datasets.
- Reserve schema, posting, and architecture references for advanced work or instructor prep.

## Teaching Notes

- Start with why each document exists before discussing table structure.
- Use `GLEntry` only after students understand which source events post and which do not.
- For auditing classes, explain the clean-vs-anomaly distinction early.
- For beginner SQL classes, start from the provided queries before moving to blank-screen assignments.
- For Excel-heavy classes, use the workbook and process docs together so students can interpret patterns instead of only producing pivots.

## Recommended Phase 19 Classroom Sequence

1. Use the default anomaly-enabled package as the standard student file set.
2. Start financial classes with the working-capital and statement-bridge cases.
3. Start managerial classes with the product-portfolio profitability case.
4. Start audit classes with the workforce cost and org-control case, then move to the audit review pack.
5. Use the clean build only when you want a baseline comparison after students understand the default dataset.

## Where to Go Next

- Use [Quick Start](student-quickstart.md) as the primary student launch page.
- Use [Analytics Hub](analytics/index.md) to choose the first topic pack.
- Use [Schema Reference](reference/schema.md) and [GLEntry Posting Reference](reference/posting.md) as shared student and instructor references during assignments.
