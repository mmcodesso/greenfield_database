# Greenfield Accounting Dataset Generator

Greenfield Accounting Dataset Generator creates a reproducible synthetic accounting database for Accounting Information Systems, accounting analytics, and audit analytics courses. The dataset is designed for SQL and Excel exercises that connect business processes, subledgers, and the general ledger.

The fictional company is **Greenfield Home Furnishings, Inc.** The current generator produces five fiscal years of data from **2026-01-01** through **2030-12-31**.

## Quick Start

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Generate the full dataset:

```powershell
python generate_dataset.py
```

If you do not activate the virtual environment, run:

```powershell
.\.venv\Scripts\python.exe generate_dataset.py
```

## Outputs

Each run produces:

- `outputs/greenfield_2026_2030.sqlite`
- `outputs/greenfield_2026_2030.xlsx`
- `outputs/validation_report.json`
- `outputs/generation.log`

Generated outputs are ignored by Git and can be regenerated locally at any time.

## Read Next

| If you are a... | Start here |
|---|---|
| Student | [docs/dataset-overview.md](docs/dataset-overview.md) and [docs/process-flows.md](docs/process-flows.md) |
| Instructor | [docs/instructor-guide.md](docs/instructor-guide.md) |
| Analyst learning the tables | [docs/database-guide.md](docs/database-guide.md) |
| Contributor or maintainer | [docs/code-architecture.md](docs/code-architecture.md) |
| Looking for detailed technical reference | [docs/reference/schema.md](docs/reference/schema.md), [docs/reference/posting.md](docs/reference/posting.md), and [docs/reference/row-volume.md](docs/reference/row-volume.md) |
| Looking for the historical blueprint | [Design.md](Design.md) |

## What Is Implemented Now

| Implemented in current generator | Planned later |
|---|---|
| 25-table dataset covering O2C, P2P, master data, budgets, and ledger postings | Manufacturing process tables and production flows |
| Five-year fiscal range with monthly transaction generation | Recurring manual operating journals beyond the opening balance entry |
| Event-based postings from shipments, invoices, receipts, goods receipts, purchase invoices, and disbursements | Richer inventory simulation and more complex P2P document structures |
| SQLite, Excel, validation report, and generation log outputs | Additional dataset extensions for broader course coverage |

## Documentation Map

- [docs/index.md](docs/index.md): documentation hub and reading paths by audience
- [docs/dataset-overview.md](docs/dataset-overview.md): business story, dataset purpose, and glossary
- [docs/process-flows.md](docs/process-flows.md): O2C, P2P, and ledger traceability explained with diagrams
- [docs/database-guide.md](docs/database-guide.md): how to navigate tables and joins
- [docs/instructor-guide.md](docs/instructor-guide.md): suggested teaching path and exercise categories
- [docs/code-architecture.md](docs/code-architecture.md): how the Python generator works
- [docs/reference/schema.md](docs/reference/schema.md): executable schema reference
- [docs/reference/posting.md](docs/reference/posting.md): posting logic reference
- [docs/reference/row-volume.md](docs/reference/row-volume.md): default row counts and target ranges

## Project Snapshot

- Company: Greenfield Home Furnishings, Inc.
- Fiscal range: 2026 through 2030
- Implemented tables: 25
- Core processes: order-to-cash, procure-to-pay, opening balances, budgets, and ledger postings
- Primary teaching uses: financial analytics, managerial analytics, audit analytics, SQL practice, Excel analysis, and subledger-to-ledger reconciliation

## Notes on Scope

- The current generator models a distributor and light assembler, but it does **not** yet implement manufacturing transactions.
- `JournalEntry` currently contains the opening balance header; recurring manual operating journals are planned, not implemented.
- `Design.md` is now an appendix and historical blueprint. It contains future ideas that do not always match the current generator.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This repository is licensed under the Creative Commons Attribution-ShareAlike 4.0 International License. See [LICENSE](LICENSE).
