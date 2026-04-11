---
title: Instructor Adoption Guide
description: Course adoption guidance for instructors using the Greenfield Accounting Dataset in accounting analytics classes.
slug: /teach-with-greenfield/instructor-adoption
sidebar_label: Instructor Adoption
---

# Instructor Adoption Guide

**Audience:** Instructors, course designers, and teaching assistants adopting the dataset for AIS, accounting analytics, auditing analytics, SQL, or Excel-based coursework.  
**Purpose:** Show how to adopt Greenfield as a teaching package without forcing students to learn implementation details before they learn the business.  
**What you will learn:** How to package the database for students, how to stage the material in a course, and how to choose the right starter analytics path.


## Adopt Greenfield in 4 Steps

### 1. Choose the student entry point

For most classes, students should start with the teaching files and the website, not the codebase.

Give students:

- the SQLite database for SQL work
- the Excel workbook for spreadsheet-based analysis
- the documentation site for orientation and guided reading

Use the generator itself mainly for instructor prep, custom builds, or contribution work.
Use [Dataset Delivery and Build Setup](/docs/technical/dataset-delivery) when you need to produce or package those files locally.

### 2. Pick the course emphasis

| If your course emphasizes... | Start with | Then assign |
|---|---|---|
| AIS or business processes | [Company Story](company-story.md), [Process Flows](process-flows.md) | document tracing, process mapping, source-to-ledger explanations |
| SQL and accounting analytics | [Student Quick Start](student-quickstart.md), [SQL Guide](analytics/sql-guide.md) | starter SQL packs and guided cases |
| Excel-based analytics | [Student Quick Start](student-quickstart.md), [Excel Guide](analytics/excel-guide.md) | workbook-based pivots, charts, and interpretation work |
| Auditing and controls | [Audit Analytics](analytics/audit.md) | anomaly-focused labs and control-review exercises |
| Managerial or cost accounting | [Managerial Analytics](analytics/managerial.md) | BOM, labor, variance, cost-center, and capacity analysis |

### 3. Sequence the material from business to analysis

The recommended rule is simple: process understanding first, analytics second.

Suggested student sequence:

1. [Student Quick Start](student-quickstart.md)
2. [Company Story](company-story.md)
3. [Process Flows](process-flows.md)
4. [Dataset Guide](dataset-overview.md)
5. [Analytics Hub](analytics/index.md)
6. topic-specific analytics pages and cases

### 4. Decide whether you want a clean or anomaly-enabled experience

- Use the standard teaching package when you want the normal five-year anomaly-enabled build.
- Use the clean baseline package when you want a faster, cleaner setup for prep or demonstration.
- Make the distinction explicit to students. Some audit queries are supposed to return exceptions only when the anomaly-enabled build is used.
- Use [Dataset Delivery and Build Setup](/docs/technical/dataset-delivery) for the exact local build commands and profile choices.

## What to Share With Students vs Keep as Instructor Reference

### Student-ready material

Share these directly with students:

- [Student Quick Start](student-quickstart.md)
- [Company Story](company-story.md)
- [Dataset Guide](dataset-overview.md)
- [Process Flows](process-flows.md)
- [Analytics Hub](analytics/index.md)
- [Financial Analytics](analytics/financial.md)
- [Managerial Analytics](analytics/managerial.md)
- [Audit Analytics](analytics/audit.md)
- [SQL Guide](analytics/sql-guide.md)
- [Excel Guide](analytics/excel-guide.md)
- [Analytics Cases](analytics/cases/index.md)

### Instructor and advanced-reference material

Use these when you need implementation detail, schema precision, or generator context:

- [Dataset Delivery and Build Setup](/docs/technical/dataset-delivery)
- [Schema Reference](reference/schema.md)
- [Posting Reference](reference/posting.md)
- [Row Counts and Volume](reference/row-volume.md)
- [Technical Guide](technical-guide.md)
- [Code Architecture](code-architecture.md)
- [Roadmap](roadmap.md)

## Recommended Course Delivery Pattern

| Week or module | Teaching goal | Main docs | Main starter assets |
|---|---|---|---|
| 1. Orientation | Explain the company, dataset purpose, and student workflow | [Student Quick Start](student-quickstart.md), [Company Story](company-story.md), [Dataset Guide](dataset-overview.md) | SQLite or Excel teaching package |
| 2. Process mapping | Show O2C, P2P, manufacturing, payroll, and close-cycle flow | [Process Flows](process-flows.md) and process guides | None yet |
| 3. Table navigation | Teach keys, joins, and traceability | [Dataset Guide](dataset-overview.md) | Introductory ad hoc joins |
| 4. Financial analytics | Connect operational activity to accounting review | [Financial Analytics](analytics/financial.md) | `queries/financial/` |
| 5. Managerial analytics | Analyze costs, labor, inventory, and operations | [Managerial Analytics](analytics/managerial.md) | `queries/managerial/` |
| 6. Audit analytics | Review completeness, controls, cut-off, and anomalies | [Audit Analytics](analytics/audit.md) | `queries/audit/` |
| 7. Guided assignments | Use structured walkthroughs before open-ended work | [Analytics Cases](analytics/cases/index.md) | case docs plus starter SQL |

This sequence compresses cleanly into fewer modules or expands into a full semester.

## Adoption Checklist

- Decide whether students will work primarily in SQL, Excel, or both.
- Share the packaged output files before asking students to inspect code.
- Use [Dataset Delivery and Build Setup](/docs/technical/dataset-delivery) when you need to build or refresh the package locally.
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

## Where to Go Next

- Use [Student Quick Start](student-quickstart.md) as the student-facing launch page.
- Use [Analytics Hub](analytics/index.md) to choose the first topic pack.
- Use [Schema Reference](reference/schema.md) when you need exact table-level detail.
