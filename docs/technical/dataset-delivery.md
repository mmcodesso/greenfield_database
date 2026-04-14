---
title: Dataset Delivery and Build Setup
description: Instructor-focused guide for generating, packaging, and sharing the Greenfield teaching dataset.
slug: /technical/dataset-delivery
sidebar_label: Dataset Delivery
---

# Dataset Delivery and Build Setup


## When to Use This Page

Use this page if you are:

- preparing the SQLite and Excel files for a class
- running the generator locally for instructor prep

Students usually do **not** need this page.

## What to Share With Students

For most courses, share these files:

- `greenfield.sqlite`
- `greenfield.xlsx`
- `greenfield_support.xlsx`
- `greenfield_csv.zip`

Then point students to:

- [Start Here](../start-here/index.md)
- [Downloads](../start-here/downloads.md)
- [Dataset Guide](../start-here/dataset-overview.md)
- [Analytics Hub](../analytics/index.md)

## Recommended Local Generation Path

Use `config/settings.yaml` when you want the released five-year teaching dataset.

Additional settings files remain available for local validation and performance work, but the published teaching package follows the released teaching configuration.

## How to Generate the Dataset Locally

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 generate_dataset.py
```

Generated files are written to `outputs/`.

## What the Build Produces

The generator writes:

- `outputs/greenfield.sqlite`
- `outputs/greenfield.xlsx`
- `outputs/greenfield_support.xlsx`
- `outputs/greenfield_csv.zip`
- `outputs/generation.log`

The main SQLite database and main Excel workbook are the core student-facing dataset files. Share the support workbook when the course uses exception review or validation context. Share the CSV zip when flat-file delivery is useful.

## Packaging Guidance

- Share the SQLite database for SQL work.
- Share the Excel workbook for pivot and chart-based analysis.
- Share the support workbook when classes need anomaly and validation companion material.
- Share the CSV zip when students or analysts need one CSV per table.
- Publish the student files through GitHub Releases or your course LMS.
- Keep `generation.log` for instructor review only.
- Ask students to start from the documentation site, not from the codebase.
- If you want a smaller assignment, filter to one fiscal year in SQL or Excel without creating many custom classroom variants.

## Where to Go Next

- Read [Instructor Adoption Guide](../teach-with-greenfield/instructor-guide.md) for course sequencing.
- Read [SQL Guide](../analytics/sql-guide.md) if students will work primarily in SQLite.
- Read [Excel Guide](../analytics/excel-guide.md) if students will work primarily in the workbook.
