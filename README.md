# Greenfield Accounting Dataset

Greenfield Accounting Dataset is a synthetic accounting database for business students who need to connect business processes, operational documents, subledgers, and the general ledger in one teachable system.

Most users should start with the pre-generated release files, not the Python generator. The project is built for SQL work, Excel analysis, accounting analytics, AIS courses, and audit-style document tracing.

## Meet the Company

The fictional company is **Greenfield Home Furnishings, Inc.**, a mid-sized home furnishings distributor with two warehouses, a multi-department operating structure, and a finance team that books recurring journals and closes the books each year.

In the current implementation, Greenfield behaves like a merchandising business:

- customers place sales orders
- warehouses ship goods when inventory is available
- accounting invoices customers and applies cash receipts
- some sales flow into returns, credit memos, and refunds
- employees request purchases, purchasing issues POs, warehouses receive goods, suppliers invoice the company, and treasury pays the invoices
- finance also books opening balances, monthly operating journals, accrual reversals, and year-end close entries

That operating model is detailed enough for classroom analysis, but still constrained enough to remain readable for students.

## What the Database Contains

The current generator produces a five-year dataset covering fiscal years **2026 through 2030**.

Current scope:

- `31` implemented tables
- order-to-cash with backorders, invoice matching, cash applications, returns, credit memos, and refunds
- procure-to-pay with batched purchase orders, partial receipts, receipt-line invoice matching, and split payments
- chart of accounts, budgets, recurring manual journals, year-end close, and posted `GLEntry` detail
- validation outputs, anomaly logging, SQLite export, Excel export, and generation logs

Primary teaching uses:

- financial accounting analytics
- managerial accounting analytics
- auditing and controls analytics
- SQL exercises
- Excel pivot-table and chart work
- source-to-ledger traceability

## Release Files

Each generated release is intended to be usable as a standalone teaching package.

Expected artifacts:

- `greenfield_2026_2030.sqlite`: best starting point for SQL work
- `greenfield_2026_2030.xlsx`: easiest starting point for Excel work
- `validation_report.json`: structured validation results
- `generation.log`: run log with generation checkpoints and summaries

## Start Here

| If you are a... | Read this first | Then continue with |
|---|---|---|
| Student | [docs/company-story.md](docs/company-story.md) | [docs/process-flows.md](docs/process-flows.md), [docs/database-guide.md](docs/database-guide.md), [docs/analytics/index.md](docs/analytics/index.md) |
| Instructor | [docs/instructor-guide.md](docs/instructor-guide.md) | [docs/company-story.md](docs/company-story.md), [docs/process-flows.md](docs/process-flows.md), [docs/analytics/index.md](docs/analytics/index.md) |
| Analyst | [docs/database-guide.md](docs/database-guide.md) | [docs/process-flows.md](docs/process-flows.md), [docs/analytics/index.md](docs/analytics/index.md), [docs/reference/schema.md](docs/reference/schema.md) |
| Contributor | [docs/technical-guide.md](docs/technical-guide.md) | [docs/code-architecture.md](docs/code-architecture.md), [docs/reference/schema.md](docs/reference/schema.md), [docs/reference/posting.md](docs/reference/posting.md) |

## Documentation Map

- [docs/index.md](docs/index.md): documentation hub and reading paths by audience
- [docs/company-story.md](docs/company-story.md): business context for the fictional company
- [docs/dataset-overview.md](docs/dataset-overview.md): what the dataset is, what it includes, and the core glossary
- [docs/process-flows.md](docs/process-flows.md): process documentation hub and traceability overview
- [docs/processes/o2c.md](docs/processes/o2c.md): order-to-cash step by step
- [docs/processes/o2c-returns-credits-refunds.md](docs/processes/o2c-returns-credits-refunds.md): returns, credit memos, and refunds step by step
- [docs/processes/p2p.md](docs/processes/p2p.md): procure-to-pay step by step
- [docs/processes/manual-journals-and-close.md](docs/processes/manual-journals-and-close.md): recurring journals and close-cycle documentation
- [docs/database-guide.md](docs/database-guide.md): table families, keys, and navigation patterns
- [docs/analytics/index.md](docs/analytics/index.md): analytics starter hub for SQL and Excel users
- [docs/instructor-guide.md](docs/instructor-guide.md): teaching path and exercise framing
- [docs/technical-guide.md](docs/technical-guide.md): system-level technical guide for the dataset and generator
- [docs/code-architecture.md](docs/code-architecture.md): module-level explanation of the Python codebase
- [docs/reference/schema.md](docs/reference/schema.md): implemented schema reference
- [docs/reference/posting.md](docs/reference/posting.md): posting logic reference
- [docs/reference/row-volume.md](docs/reference/row-volume.md): scale expectations and current row volumes
- [docs/roadmap.md](docs/roadmap.md): future phases

## Implemented Now vs Planned Later

| Implemented in current generator | Planned future extension |
|---|---|
| Five years of O2C, P2P, budgets, recurring journals, close-cycle activity, and posted ledger data | Manufacturing tables and production flows |
| Separate customer receipt applications and customer-credit flows | Manufacturing analytics packs |
| Multi-period receiving, billing, collection, and settlement behavior | Broader production and cost-accounting coverage |
| Starter analytics docs, runnable SQL packs, and Excel workflow guidance | Additional advanced analytics packs |

## Build It Yourself

Most users do not need to run the generator locally. If you do want to regenerate the dataset, use the commands below from the repository root.

### Linux and macOS

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 generate_dataset.py
```

### Windows

```bat
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python generate_dataset.py
```

Generated files are written to `outputs/`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This repository is licensed under the Creative Commons Attribution-ShareAlike 4.0 International License. See [LICENSE](LICENSE).
