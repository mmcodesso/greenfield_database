---
title: SQL Guide
description: How to open the SQLite dataset, run starter queries, and move into topic analysis.
sidebar_label: SQL Guide
---

# SQL Guide

## What This Page Helps You Do

Use this page when you are opening the SQLite dataset for the first time. It shows you which file to open, which tool to use first, how to run a starter query, and how to move from a result set into the topic pages and cases.

## What File to Open

For SQL work, start with <FileName type="sqlite" />.

This file contains the dataset tables you need for joins, filters, summaries, and document tracing.

## Recommended Tool: DB Browser for SQLite

The recommended starting tool is [DB Browser for SQLite](https://sqlitebrowser.org/dl/).

It works well for first-time SQLite work because it gives you:

- a simple install path
- a direct file-open workflow
- a visible table browser
- a built-in SQL editor
- a result grid that is easy to review and export

If you are new to SQLite, start here before moving to a more advanced tool.

## How to Open the Dataset in DB Browser

1. Download and install [DB Browser for SQLite](https://sqlitebrowser.org/dl/).
2. Open DB Browser and choose `Open Database`.
3. Select <FileName type="sqlite" /> from the files shared for your course.
4. Open the `Browse Data` tab and inspect a few tables such as `Customer`, `SalesInvoice`, or `GLEntry`.
5. Open the `Execute SQL` tab so you are ready to paste a starter query.

At this point, you are ready to copy SQL from the analytics pages in the docs and run it against the dataset.

## How to Run Your First Query

Use this first-pass workflow:

1. Open [Financial Analytics](financial.md).
2. In the starter SQL list, expand `Working-capital bridge by month`.
3. Copy the SQL from the code block.
4. Paste it into the `Execute SQL` tab in DB Browser.
5. Run the query.
6. Review the result grid and column names before you move on.

This gives you a complete first-use path: open the file, copy a real starter query, run it, and review a business result that already connects to a guided case.

## How to Read the Result and Keep Going

After your first query runs, check four things before you write another one:

- the row grain: what one row represents
- the main dimensions: month, customer, item, cost center, or document
- the main measures: amount, quantity, hours, or count
- the business question: what the result explains

Then move to the next layer:

1. stay on the topic page and run a second query in the same area
2. open the paired case in [Analytics Cases](cases/index.md)
3. use [Schema Reference](../reference/schema.md) when you need table and key help
4. use [GLEntry Posting Reference](../reference/posting.md) when the question reaches the ledger

The starter SQL is organized into three compact topic groups:

| Folder | What it covers |
|---|---|
| `queries/financial` | revenue, margin, working capital, accruals, payroll, close-cycle, and pricing review |
| `queries/managerial` | budget, portfolio mix, labor, service levels, planning, replenishment, and pricing governance |
| `queries/audit` | document-chain review, approvals, workforce controls, planning support, pricing governance, and anomaly review |

The topic pages surface these queries directly in the docs, so most students can work from the website without opening the repository folders.

## Other Tools You Can Use

If you already use another SQL tool, the same workflow still works:

- `DBeaver`
- `SQLiteStudio`
- `VS Code` with a SQLite extension

Open <FileName type="sqlite" />, copy a starter query from the docs, run it, and review the result. DB Browser remains the recommended first tool because it is the simplest path for most students.

### Secondary Workflows

If you prefer code-first work, you can also run the same starter SQL through Python or the `sqlite3` command-line tool.

#### Python

```python
from pathlib import Path
import sqlite3
import pandas as pd

sql = Path("queries/financial/19_working_capital_bridge_by_month.sql").read_text(encoding="utf-8")
with sqlite3.connect("downloaded_dataset.sqlite") as connection:
    df = pd.read_sql_query(sql, connection)

print(df.head())
```

#### `sqlite3` CLI

```bash
sqlite3 downloaded_dataset.sqlite < queries/financial/19_working_capital_bridge_by_month.sql
```

## Where to Go Next

- Use [Financial Analytics](financial.md), [Managerial Analytics](managerial.md), or [Audit Analytics](audit.md) to choose your next topic.
- Use [Analytics Cases](cases/index.md) when you want a guided business question after the first query.
- Use [Excel Guide](excel-guide.md) when you want to recreate a SQL result in the workbook.
