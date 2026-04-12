---
title: SQL Guide
description: How to use the starter SQL packs against the Greenfield SQLite export.
sidebar_label: SQL Guide
---

# SQL Starter Guide

## Starter SQL Package Layout

| Folder | Coverage |
|---|---|
| [queries/financial](https://github.com/mmcodesso/greenfield_database/tree/main/queries/financial) | revenue, margin, working capital, AR, AP, accrued expenses, payroll liabilities, close-cycle, and control-account review |
| [queries/managerial](https://github.com/mmcodesso/greenfield_database/tree/main/queries/managerial) | budget, product portfolio, lifecycle mix, labor, service levels, BOMs, work orders, capacity, and contribution margin |
| [queries/audit](https://github.com/mmcodesso/greenfield_database/tree/main/queries/audit) | document-chain completeness, approvals, cut-off, payroll and time controls, master-data controls, and anomaly-oriented review |

Each file is a single SQLite-friendly `SELECT` statement with short comment headers that explain:

- teaching objective
- main tables
- output shape
- recommended build mode
- interpretation notes

## Recommended Workflow

1. Open the SQLite file shared for your course or section.
2. If you are preparing the dataset yourself, use [Dataset Delivery and Build Setup](../teach-with-greenfield/dataset-delivery.md).
3. Start with one topic page:
   - [Financial Analytics](financial.md)
   - [Managerial Analytics](managerial.md)
   - [Audit Analytics](audit.md)
4. Run the corresponding SQL files.
5. Then open the paired case in [Analytics Cases](cases/index.md).
6. Recreate one result in Excel when you want students to move from SQL to workbook interpretation.

## Ways to Run the Queries

### SQLite GUI tools

The easiest workflow for most users is:

- DB Browser for SQLite
- DBeaver
- SQLiteStudio
- VS Code with a SQLite extension

Open the database, open the `.sql` file, and run it as a normal query tab.

### Python workflow

If you prefer Python, the starter SQL files can be read directly:

```python
from pathlib import Path
import sqlite3
import pandas as pd

sql = Path("queries/financial/19_working_capital_bridge_by_month.sql").read_text(encoding="utf-8")
with sqlite3.connect("greenfield.sqlite") as connection:
    df = pd.read_sql_query(sql, connection)

print(df.head())
```

### `sqlite3` CLI

If the `sqlite3` command-line tool is installed on your system, you can also run:

```bash
sqlite3 greenfield.sqlite < queries/financial/19_working_capital_bridge_by_month.sql
```

## Clean Build vs Default Build

- The default anomaly-enabled build is the main student-facing package.
- Financial and managerial queries work well on either build.
- Audit queries are usually more informative on the default build.
- The main SQLite export contains dataset tables only.
- Anomaly and validation companion content lives in the support workbook, not in SQLite.

## Suggested Phase 19 Sequence

### Financial

1. monthly revenue and gross margin
2. AR aging
3. AP aging
4. working-capital bridge by month
5. cash-conversion timing review
6. payroll liability roll-forward
7. accrued expense roll-forward
8. retained earnings and close-entry impact
9. payroll and people-cost mix
10. paired cases:
   - [Working Capital and Cash Conversion Case](cases/working-capital-and-cash-conversion-case.md)
   - [Financial Statement Bridge Case](cases/financial-statement-bridge-case.md)

### Managerial

1. budget vs actual
2. product portfolio mix by collection, style, lifecycle, and supply mode
3. sales and gross margin by collection and lifecycle
4. contribution margin by collection, material, lifecycle, and supply mode
5. customer-service impact by collection and style
6. labor and headcount by work location, job family, and cost center
7. portfolio return and refund impact by collection and lifecycle
8. paired case:
   - [Product Portfolio Profitability Case](cases/product-portfolio-profitability-case.md)

### Audit

1. document-chain completeness
2. approval and SOD review
3. payroll and time-control review
4. executive-role uniqueness and control-assignment review
5. item-master completeness review
6. discontinued or pre-launch item activity review
7. approval-authority review by expected role family
8. terminated-employee activity detail and rollup review
9. paired cases:
   - [Workforce Cost and Org-Control Case](cases/workforce-cost-and-org-control-case.md)
   - [Audit Review Pack Case](cases/audit-review-pack-case.md)

## Where to Go Next

- Read [Excel Guide](excel-guide.md) to recreate similar analyses in the workbook.
- Read [Instructor Adoption Guide](../instructor-guide.md) for topic sequencing in class.
