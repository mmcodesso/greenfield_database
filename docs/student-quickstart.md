---
title: Quick Start
description: Start using the Greenfield Accounting Dataset without getting stuck in technical detail.
slug: /quick-start
---

# Quick Start

Use this page if you want the shortest path from “What is this database?” to “I can answer course questions with it.”

## 1. Start With the Right Files

Most students should begin with the teaching package shared for their course.

The core files are:

- `greenfield_2026_2030.sqlite` for SQL work
- `greenfield_2026_2030.xlsx` for Excel pivots, charts, and workbook-based analysis
- `validation_report.json` for control and validation review
- `generation.log` for run diagnostics and row-volume checkpoints

If your instructor already shared those files, start there first.

## 2. Learn the Story Before the Tables

Read these pages in order:

1. [Company Story](company-story.md)
2. [Process Flows](process-flows.md)
3. [Dataset Guide](dataset-overview.md)

That sequence gives you the business context before you start writing joins or building pivots.

## 3. Choose Your Analysis Path

Use the path that matches your class:

- [Analytics Hub](analytics/index.md) for the overall starter map
- [SQL Guide](analytics/sql-guide.md) if you will query the SQLite database
- [Excel Guide](analytics/excel-guide.md) if you will work from the workbook
- [Financial Analytics](analytics/financial.md), [Managerial Analytics](analytics/managerial.md), and [Audit Analytics](analytics/audit.md) for topic-specific starting points

## 4. Know What the Dataset Covers

The current dataset includes **55 tables** across:

- accounting core
- order-to-cash
- procure-to-pay
- manufacturing
- payroll and time
- master data
- organizational planning

It is designed for accounting analytics classes where you need to connect process documents, operational data, and posted `GLEntry` activity.

## 5. Use the Guided Cases When You Need Structure

If you do not want to start from a blank page, use the guided walkthroughs in [Analytics Cases](analytics/cases/index.md). They pair process context with starter SQL and interpretation prompts.

## Use the Reference Pages While You Work

These pages are normal student resources when you need to trace a process, check a join path, or confirm what posts to the ledger:

- [Schema Reference](reference/schema.md)
- [GLEntry Posting Reference](reference/posting.md)

Use the deeper system page only when an assignment needs generator detail:

- [Technical Guide](technical-guide.md)
