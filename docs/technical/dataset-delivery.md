---
title: Customize
description: Optional instructor guide for creating a local Charles River dataset and adjusting generation settings.
slug: /technical/dataset-delivery
sidebar_label: Customize
---

# Customize

 When you want to create a local Charles River dataset or adjust the generation settings for a specific teaching need.

Most instructors can teach directly from the published package and the documentation site. Use customization only when you need a different date range, different dataset size, different outputs, or a different validation or anomaly setting.

If you want to customize Charles River locally, use the repository workflow described on this page.

## Default Teaching Package

For most courses, start with the published teaching package:

- `CharlesRiver.sqlite`
- `CharlesRiver.xlsx`
- `CharlesRiver_csv.zip`


- `CharlesRiver_support.xlsx` 

Then point students to:

- [Start Here](../start-here/index.md)
- [Downloads](../start-here/downloads.md)
- [Dataset Guide](../start-here/dataset-overview.md)
- [Analytics Hub](../analytics/index.md)

## When Customization Is Useful

Customize the dataset when you want to:

- shorten the fiscal range for a smaller assignment
- change the number of employees, customers, suppliers, items, or warehouses
- change which outputs are exported
- produce a local validation or performance-focused run
- change anomaly behavior for instructor preparation or internal testing

The published release remains the default classroom package. Local settings files are optional tools for instructor customization and validation.

## How to Generate the Dataset Locally

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 generate_dataset.py
```

Generated files are written to `outputs/`.

By default, `generate_dataset.py` reads `config/settings.yaml`. You can also pass a settings file and validation scope explicitly:

```bash
python3 generate_dataset.py config/settings_validation.yaml core
```

The validation scope options are `core`, `operational`, and `full`.

## Settings You Can Adjust

Charles River currently exposes these instructor-facing settings in the YAML files under `config/`:

### Fiscal range

- `fiscal_year_start`
- `fiscal_year_end`

Use these when you want a shorter or longer teaching horizon.

### Entity counts

- `employee_count`
- `customer_count`
- `supplier_count`
- `item_count`
- `warehouse_count`

Use these when you want to scale the dataset up or down for course difficulty, performance, or assignment size.

### Export controls and output paths

- `export_sqlite`
- `export_excel`
- `export_support_excel`
- `export_csv_zip`
- `sqlite_path`
- `excel_path`
- `support_excel_path`
- `csv_zip_path`
- `generation_log_path`

Use these when you want to control which files are produced and where they are written.

### Anomaly behavior

- `anomaly_mode`

Use this when you need a local run with or without anomaly injection for instructor preparation or validation work.

### Other teaching parameters

- `random_seed`
- `company_name`
- `tax_rate`

Use these when you need stable reruns or limited local adjustments to the generated environment.

## Available Settings Files

The repository currently includes these settings files:

- `config/settings.yaml` as the main local generation template
- `config/settings_validation.yaml` for a smaller validation-oriented run
- `config/settings_perf.yaml` for short-horizon performance profiling

These files support local generation workflows. The published teaching package is distributed separately and should remain the normal starting point for classroom use.

## What Local Generation Produces

The generator writes:

- `outputs/CharlesRiver.sqlite`
- `outputs/CharlesRiver.xlsx`
- `outputs/CharlesRiver_support.xlsx`
- `outputs/CharlesRiver_csv.zip`
- `outputs/generation.log`

The main SQLite database and main Excel workbook are the core student-facing dataset files. Share the support workbook when the course uses exception review or validation context. Share the CSV zip when flat-file delivery is useful.

## How to Share a Customized Package

- Share the SQLite database for SQL work.
- Share the Excel workbook for pivot and chart-based analysis.
- Share the support workbook when classes need anomaly and validation companion material.
- Share the CSV zip when students or analysts need one CSV per table.
- Publish the student files through GitHub Releases or your course LMS.
- Keep `generation.log` for instructor review only.
- Ask students to start from the documentation site and the published teaching files, not from the local generation workflow.
- If you want a smaller assignment, filter to one fiscal year in SQL or Excel without creating many custom classroom variants.

## Where to Go Next

- Read [Instructor Adoption Guide](../teach-with-CharlesRiver/instructor-guide.md) for course sequencing.
- Read [SQL Guide](../analytics/sql-guide.md) if students will work primarily in SQLite.
- Read [Excel Guide](../analytics/excel-guide.md) if students will work primarily in the workbook.
