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
- choosing between the clean and anomaly-enabled teaching packages
- running the generator locally for instructor prep

Students usually do **not** need this page.

## What to Share With Students

For most courses, share these files:

- `greenfield_2026_2030.sqlite`
- `greenfield_2026_2030.xlsx`
- `validation_report.json`
- `generation.log`

Then point students to:

- [Student Quick Start](../student-quickstart.md)
- [Dataset Guide](../dataset-overview.md)
- [Analytics Hub](../analytics/index.md)

## Recommended Build Options

### Standard teaching package

Use `config/settings.yaml` when you want the normal five-year teaching build with the standard anomaly pack enabled.

This is the best default when you want:

- SQL and Excel starter work
- audit and controls exercises
- guided cases
- anomaly-focused class discussions

### Clean baseline package

Use `config/settings_validation.yaml` when you want a faster clean baseline for prep, demos, or exercises that should minimize anomaly-driven exceptions.

This is useful when you want:

- a quick instructor preview build
- baseline process tracing before exceptions
- a cleaner first exposure to the data model

## How to Generate the Dataset Locally

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 generate_dataset.py
```

For the clean baseline profile:

```bash
python3 generate_dataset.py config/settings_validation.yaml
```

Generated files are written to `outputs/`.

## What the Build Produces

The default teaching build writes:

- `outputs/greenfield_2026_2030.sqlite`
- `outputs/greenfield_2026_2030.xlsx`
- `outputs/validation_report.json`
- `outputs/generation.log`

## Packaging Guidance

- Share the SQLite database for SQL work.
- Share the Excel workbook for pivot and chart-based analysis.
- Keep `validation_report.json` and `generation.log` available for instructor review or advanced control exercises.
- Ask students to start from the documentation site, not from the codebase.
- If you want a smaller assignment, filter to one fiscal year in SQL or Excel instead of creating many custom classroom variants.

## Clean vs Anomaly-Enabled Teaching Use

- Use the standard package when you want audit exercises to surface meaningful exceptions.
- Use the clean package when you want process learning and table navigation without anomaly-heavy results.
- Explain the difference to students before they compare outputs across sections or assignments.

## Where to Go Next

- Read [Instructor Adoption Guide](../instructor-guide.md) for course sequencing.
- Read [SQL Guide](../analytics/sql-guide.md) if students will work primarily in SQLite.
- Read [Excel Guide](../analytics/excel-guide.md) if students will work primarily in the workbook.
