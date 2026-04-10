# SQL Starter Guide

**Audience:** Students, instructors, and analysts running the starter analytics pack against the SQLite export.  
**Purpose:** Explain how the starter SQL files are organized, how to run them, and how to adapt them without breaking alignment to the current dataset.  
**What you will learn:** Where the starter queries live, how to execute them, and how to extend them safely for class use.

> **Implemented in current generator:** SQLite-first starter SQL files for financial accounting, managerial accounting, and auditing analytics, including payroll and manufacturing-focused starter analysis.

> **Planned future extension:** Additional advanced planning and anomaly packs built on the same starter structure.

## Starter SQL Package Layout

| Folder | Coverage |
|---|---|
| [../../queries/financial](../../queries/financial) | Revenue, margin, AR, AP, accrued expenses, payroll liabilities, trial balance, control-account work, and manufacturing balance review |
| [../../queries/managerial](../../queries/managerial) | Budgeting, cost centers, sales mix, inventory movement, purchasing, BOMs, work orders, labor, unit cost, and profitability |
| [../../queries/audit](../../queries/audit) | Document-chain completeness, approvals, cut-off, duplicate checks, anomaly review, manufacturing controls, and payroll controls |

Each file is a single SQLite-friendly `SELECT` statement with short comment headers that explain:

- teaching objective
- main tables
- output shape
- interpretation notes

## Recommended Workflow

1. Generate the SQLite output with `python generate_dataset.py`.
2. Open `outputs/greenfield_2026_2030.sqlite` in your SQLite tool of choice.
3. Start with one topic area:
   - [financial.md](financial.md)
   - [managerial.md](managerial.md)
   - [audit.md](audit.md)
4. Run the corresponding `.sql` files.
5. Export results or compare them to the Excel workbook.

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

sql = Path("queries/financial/01_monthly_revenue_and_gross_margin.sql").read_text(encoding="utf-8")
with sqlite3.connect("outputs/greenfield_2026_2030.sqlite") as connection:
    df = pd.read_sql_query(sql, connection)

print(df.head())
```

### `sqlite3` CLI

If the `sqlite3` command-line tool is installed on your system, you can also run:

```bash
sqlite3 outputs/greenfield_2026_2030.sqlite < queries/financial/01_monthly_revenue_and_gross_margin.sql
```

## Query Design Conventions

The starter pack follows these rules:

- SQLite syntax first
- one query per file
- no dependency on future schema changes
- readable CTE-based structure where it improves clarity
- no dependency on exact row counts
- current manufacturing and payroll logic is allowed where it improves teaching value

## How to Adapt the Starter Queries

Safe ways to extend the starter pack:

- add a `WHERE` filter for a fiscal year, region, supplier, cost center, or pay period
- add additional grouping columns
- convert detail listings into summarized pivots by month or year
- join `Employee`, `Customer`, or `Supplier` for descriptive fields

Changes to avoid in this phase:

- rewriting queries around future routing or capacity flows
- assuming anomaly rows will always exist
- assuming every control-account or balance-sheet line carries a cost center

## Clean Build vs Anomaly-Enabled Build

- Financial and managerial queries work well on either a clean or default build.
- Audit queries are often more interesting on the default `standard` anomaly mode.
- Some audit starter queries may return no rows on a clean build. That is expected and not a query failure.

## Suggested Starter Sequence

### Financial

1. monthly revenue and gross margin
2. AR aging
3. AP aging
4. payroll liability roll-forward
5. gross-to-net payroll review
6. accrued expense roll-forward
7. accrued versus invoiced versus paid timing
8. trial balance
9. journal and close-cycle review
10. control-account reconciliation

### Managerial

1. budget vs actual
2. sales mix
3. inventory movement
4. purchasing activity
5. cost center summary
6. basic profitability
7. BOM standard cost rollup
8. work-order throughput
9. direct labor by work order
10. unit-cost bridge
11. absorption vs contribution margin
12. labor efficiency and rate variance

### Audit

1. O2C completeness
2. P2P completeness
3. approval and SOD review
4. cut-off and timing analysis
5. duplicate review
6. potential anomaly review
7. BOM and supply-mode conflict review
8. over-issue and open WIP review
9. work-order close timing review
10. payroll control review
11. labor-time-after-close and paid-without-time review
12. over and under accrual review

## Where to Go Next

- Read [excel-guide.md](excel-guide.md) to recreate similar analyses in the workbook.
- Read [../instructor-guide.md](../instructor-guide.md) for topic sequencing in class.
