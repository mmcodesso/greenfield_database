---
title: SQL Guide
description: How to use the starter SQL packs against the Greenfield SQLite export.
sidebar_label: SQL Guide
---

# SQL Starter Guide

## Starter SQL Package Layout

| Folder | Coverage |
|---|---|
| [queries/financial](https://github.com/mmcodesso/greenfield_database/tree/main/queries/financial) | revenue, margin, working capital, AR, AP, accrued expenses, payroll liabilities, close-cycle, planning, and price-realization review |
| [queries/managerial](https://github.com/mmcodesso/greenfield_database/tree/main/queries/managerial) | budget, product portfolio, lifecycle mix, labor, service levels, BOMs, work orders, capacity, forecast, replenishment, pricing governance, and contribution margin |
| [queries/audit](https://github.com/mmcodesso/greenfield_database/tree/main/queries/audit) | document-chain completeness, approvals, cut-off, payroll and time controls, master-data controls, planning support, pricing governance, and anomaly-oriented review |

Each file is a single SQLite-friendly `SELECT` statement with short comment headers that explain:

- teaching objective
- main tables
- output shape
- recommended use
- interpretation notes

## Recommended Workflow

1. Open the SQLite file shared for your course or section.
2. If you are preparing the dataset yourself, use [Dataset Delivery and Build Setup](../technical/dataset-delivery.md).
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

## Using the Published Dataset

- The main SQLite export contains dataset tables only.
- Financial and managerial queries support regular analytical work across the published dataset.
- Some audit queries are designed to surface exceptions that are documented in the support workbook.
- Anomaly and validation companion content lives in the support workbook, not in SQLite.

## Suggested Sequence by Topic

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
10. price realization versus list price
11. gross-margin impact of promotions versus non-promotion sales
12. paired cases:
   - [Working Capital and Cash Conversion Case](cases/working-capital-and-cash-conversion-case.md)
   - [Financial Statement Bridge Case](cases/financial-statement-bridge-case.md)
   - [Pricing and Margin Governance Case](cases/pricing-and-margin-governance-case.md)

### Managerial

1. budget vs actual
2. product portfolio mix by collection, style, lifecycle, and supply mode
3. sales and gross margin by collection and lifecycle
4. contribution margin by collection, material, lifecycle, and supply mode
5. customer-service impact by collection and style
6. labor and headcount by work location, job family, and cost center
7. staffing coverage vs work-center planned load
8. rostered hours vs approved worked hours by work center and shift
9. absence rate by work location, job family, and month
10. overtime approval coverage and concentration
11. punch-to-pay bridge for hourly workers
12. late arrival and early departure by shift and department
13. inventory coverage and projected stockout risk
14. rough-cut capacity load versus available hours
15. expedite pressure by item family and month
16. forecast error and bias by collection and style family
17. supply-plan driver mix by collection and supply mode
18. portfolio return and refund impact by collection and lifecycle
19. sales-rep override rate and discount dispersion
20. collection revenue and margin before and after promotions
21. customer-specific pricing concentration and dependency
22. monthly price-floor pressure and override concentration
23. paired cases:
   - [Product Portfolio Profitability Case](cases/product-portfolio-profitability-case.md)
   - [Workforce Coverage and Attendance Case](cases/workforce-coverage-and-attendance-case.md)
   - [Demand Planning and Replenishment Case](cases/demand-planning-and-replenishment-case.md)
   - [Pricing and Margin Governance Case](cases/pricing-and-margin-governance-case.md)

### Audit

1. document-chain completeness
2. approval and SOD review
3. payroll and time-control review
4. executive-role uniqueness and control-assignment review
5. item-master completeness review
6. discontinued or pre-launch item activity review
7. approval-authority review by expected role family
8. terminated-employee activity detail and rollup review
9. scheduled-without-punch and punch-without-schedule review
10. overtime without approval review
11. absence-with-worked-time review
12. overlapping or incomplete punch review
13. roster-after-termination review
14. forecast approval and override review
15. inactive or stale inventory policy review
16. requisitions and work orders without planning support
17. recommendation converted after need-by date review
18. discontinued or pre-launch planning activity review
19. sales below floor without approval
20. expired or overlapping price-list review
21. promotion scope and date mismatch review
22. customer-specific price-list bypass review
23. override approval completeness review
24. paired cases:
   - [Workforce Cost and Org-Control Case](cases/workforce-cost-and-org-control-case.md)
   - [Audit Review Pack Case](cases/audit-review-pack-case.md)
   - [Attendance Control Audit Case](cases/attendance-control-audit-case.md)
   - [Replenishment Support Audit Case](cases/replenishment-support-audit-case.md)
   - [Pricing Governance Audit Case](cases/pricing-governance-audit-case.md)

## Where to Go Next

- Read [Excel Guide](excel-guide.md) to recreate similar analyses in the workbook.
- Read [Instructor Adoption Guide](../teach-with-greenfield/instructor-guide.md) for topic sequencing in class.
