---
title: Instructor Adoption Guide
description: Course adoption guidance for instructors using this accounting dataset in analytics classes.
slug: /teach-with-data/instructor-adoption
sidebar_label: Instructor Adoption
---

# Instructor Adoption Guide

## Why instructors adopt this dataset

<DisplayName /> is ready for classroom use from the published teaching files and the documentation site. Instructors do not need to assemble a separate business case, build process notes, or create a starter query path before the first assignment. The site already connects business context, process logic, dataset navigation, references, analytics guides, and case-based activities in one teaching environment.

That structure makes adoption practical across several accounting courses. The same dataset can support AIS, business-process instruction, SQL and accounting analytics, Excel-based analysis, auditing and controls, and managerial or cost-accounting work. Instructors can begin with a clear default path and expand into cases, references, and optional customization only when the course needs it.

## What students need first

For most courses, start students with the published teaching files and the teaching-facing documentation.

- Use <FileName type="sqlite" /> when the course emphasizes SQL, joins, and query-based analysis.
- Use <FileName type="excel" /> when the course emphasizes pivots, filters, formulas, charts, and workbook-based interpretation.
- Use [Start Here](../start-here/index.md), [Company Story](../learn-the-business/company-story.md), [Process Flows](../learn-the-business/process-flows.md), and [Dataset Guide](../start-here/dataset-overview.md) before the first technical assignment.


## Where the dataset fits in the curriculum

| Course emphasis | Begin with | Then use |
|---|---|---|
| AIS and business processes | [Company Story](../learn-the-business/company-story.md), [Process Flows](../learn-the-business/process-flows.md) | source-document tracing, process mapping, and source-to-ledger explanation |
| SQL and accounting analytics | [Start Here](../start-here/index.md), [Dataset Guide](../start-here/dataset-overview.md), [SQL Guide](../analytics/sql-guide.md) | starter SQL packs, guided cases, and topic-based analysis |
| Excel analytics | [Start Here](../start-here/index.md), [Company Story](../learn-the-business/company-story.md), [Excel Guide](../analytics/excel-guide.md) | workbook-based pivots, charts, and interpretation exercises |
| Auditing and controls | [Process Flows](../learn-the-business/process-flows.md), [Audit Analytics](../analytics/audit.md) | support-workbook review, control testing, and exception-focused cases |
| Managerial and cost accounting | [Dataset Guide](../start-here/dataset-overview.md), [Managerial Analytics](../analytics/managerial.md) | portfolio, labor, variance, planning, and capacity analysis |

## Recommended teaching sequence

This sequence works well for most first-time adoptions:

1. Share the published teaching files.
2. Assign [Start Here](../start-here/index.md).
3. Assign [Company Story](../learn-the-business/company-story.md).
4. Review [Process Flows](../learn-the-business/process-flows.md).
5. Assign [Dataset Guide](../start-here/dataset-overview.md).
6. Choose the first analytics track in [Analysis Tracks](../analytics/analysis-tracks.md).
7. Use [Cases](../analytics/cases/index.md) once students understand the basic document and table flow.

This order helps students understand the business and the process logic before they move into SQL, Excel, or open-ended analysis.

## Including the Support Workbook

Include <FileName type="support" /> when you want students to:

- review anomaly families alongside source-table evidence
- compare validation exceptions to operational or accounting records
- work through audit and control cases with guided exception context
- triage issues before moving into deeper source-document review

The published default build also carries a small intentional manufacturing audit-seed set in the validation companion material. Use that set when you want a short manufacturing-control lab that is visible in source tables and in the support workbook without broadening the anomaly pack.


## How to stage assignments

Start with guided work and then widen the analytical scope.

- Use topic guides and starter queries to establish the first analytical pattern.
- Move next into [Cases](../analytics/cases/index.md) when students need structured interpretation prompts and business context.
- Use open-ended analysis only after students can explain the source documents, process flow, and ledger effect behind the result.
- Use [Schema Reference](../reference/schema.md) and [GLEntry Posting Reference](../reference/posting.md) as supporting references during assignments, not as the first reading.

This progression usually produces stronger explanations and better query design than starting with a blank-screen assignment.

## Optional customization

Most instructors can adopt <DisplayName /> successfully with the published teaching package. Use [Customize](../technical/dataset-delivery.md) only when you want a local variant, a different fiscal range, different scale settings, or a different output set for instructor preparation.

## Adoption checklist

- Decide whether the course will begin in SQL, Excel, or both.
- Download and review the published teaching files before the course begins.
- Assign the business and process pages before the first technical task.
- Choose one analytics track as the first structured module.
- Add the support workbook only when the assignment needs anomaly or validation context.
- Use guided cases before open-ended projects when students are new to integrated accounting datasets.
- Keep schema and posting references available during assignments.

## Next Steps

- Use [Start Here](../start-here/index.md) as the primary student launch page.
- Use [Analysis Tracks](../analytics/analysis-tracks.md) to choose the first topic pack.
- Use [Cases](../analytics/cases/index.md) for guided assignments.
- Use [Schema Reference](../reference/schema.md) and [GLEntry Posting Reference](../reference/posting.md) as assignment support references.
- Use [Customize](../technical/dataset-delivery.md) only when you need a locally generated variant.
