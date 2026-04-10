# Greenfield Accounting Dataset

Greenfield Accounting Dataset is a synthetic business database for AIS, accounting analytics, auditing analytics, SQL, and Excel coursework.

The repository is designed for users who mostly want the generated release artifacts:

- `greenfield_2026_2030.sqlite`
- `greenfield_2026_2030.xlsx`
- `validation_report.json`
- `generation.log`

Most students and instructors should start with those files, not the Python generator.

## Meet the Company

**Greenfield Home Furnishings, Inc.** is a fictional mid-sized U.S. company.

In the current implementation, Greenfield is a **hybrid manufacturer-distributor**:

- it sells finished goods to customers
- it buys raw materials, packaging, and some finished goods from suppliers
- it manufactures a selected subset of products in-house
- it stores inventory in two warehouses
- it ships, invoices, collects cash, processes returns, and issues credit memos and refunds
- it records recurring journals, manufacturing reclasses, and year-end close entries

That makes the dataset useful across:

- financial accounting
- managerial accounting
- auditing and controls
- business process analysis
- SQL and Excel exercises

## What the Database Contains

The current default build covers fiscal years **2026 through 2030** and contains **45 implemented tables** across:

- accounting core
- order-to-cash
- procure-to-pay
- manufacturing
- payroll
- master data
- organizational planning

Current implemented scope includes:

- O2C with backorders, shipment-to-invoice linkage, cash applications, returns, credit memos, and refunds
- P2P with requisitions, batched purchase orders, partial receipts, matched supplier invoices, and split disbursements
- manufacturing with BOMs, work orders, material issues, production completions, and work-order close
- payroll with labor time, payroll registers, payments, liability remittances, and manufacturing labor integration
- recurring manual journals, factory overhead, direct-labor reclasses, manufacturing-overhead reclasses, and year-end close
- posted `GLEntry` detail, validation reporting, anomaly logging, SQLite export, Excel export, and generation logs

## Release Files

Each release is intended to function as a ready-to-use teaching package.

| File | Best use |
|---|---|
| `greenfield_2026_2030.sqlite` | SQL exercises and database analysis |
| `greenfield_2026_2030.xlsx` | Excel pivots, charts, and classroom workbook use |
| `validation_report.json` | Validation review and control documentation |
| `generation.log` | Run diagnostics, timing, and row-volume checkpoints |

## Start Here

| If you are a... | Read this first | Then continue with |
|---|---|---|
| Student | [docs/company-story.md](docs/company-story.md) | [docs/process-flows.md](docs/process-flows.md), [docs/database-guide.md](docs/database-guide.md), [docs/analytics/index.md](docs/analytics/index.md) |
| Instructor | [docs/instructor-guide.md](docs/instructor-guide.md) | [docs/company-story.md](docs/company-story.md), [docs/process-flows.md](docs/process-flows.md), [docs/analytics/index.md](docs/analytics/index.md) |
| Analyst | [docs/database-guide.md](docs/database-guide.md) | [docs/process-flows.md](docs/process-flows.md), [docs/analytics/index.md](docs/analytics/index.md), [docs/reference/schema.md](docs/reference/schema.md) |
| Contributor | [docs/technical-guide.md](docs/technical-guide.md) | [docs/code-architecture.md](docs/code-architecture.md), [docs/reference/schema.md](docs/reference/schema.md), [docs/reference/posting.md](docs/reference/posting.md) |

## Documentation Map

- [docs/index.md](docs/index.md): documentation hub
- [docs/company-story.md](docs/company-story.md): business storyline and operating context
- [docs/dataset-overview.md](docs/dataset-overview.md): dataset scope and glossary
- [docs/process-flows.md](docs/process-flows.md): process hub and ledger traceability
- [docs/processes/o2c.md](docs/processes/o2c.md): order-to-cash
- [docs/processes/o2c-returns-credits-refunds.md](docs/processes/o2c-returns-credits-refunds.md): returns, credits, and refunds
- [docs/processes/p2p.md](docs/processes/p2p.md): procure-to-pay
- [docs/processes/manufacturing.md](docs/processes/manufacturing.md): manufacturing flow
- [docs/processes/payroll.md](docs/processes/payroll.md): payroll cycle and labor integration
- [docs/processes/manual-journals-and-close.md](docs/processes/manual-journals-and-close.md): recurring journals and close
- [docs/database-guide.md](docs/database-guide.md): table families, keys, and joins
- [docs/analytics/index.md](docs/analytics/index.md): analytics starter layer
- [docs/instructor-guide.md](docs/instructor-guide.md): teaching path
- [docs/technical-guide.md](docs/technical-guide.md): system-level technical guide
- [docs/code-architecture.md](docs/code-architecture.md): module-level code map
- [docs/reference/schema.md](docs/reference/schema.md): implemented schema reference
- [docs/reference/posting.md](docs/reference/posting.md): posting logic reference
- [docs/reference/row-volume.md](docs/reference/row-volume.md): current deterministic row volumes
- [docs/roadmap.md](docs/roadmap.md): next planned phase

## Implemented Now vs Planned Later

| Implemented in current generator | Planned future extension |
|---|---|
| Hybrid manufacturing plus distributor operations with an operational payroll subledger, routings, work centers, and operation-level labor assignment | Advanced manufacturing topics such as capacity, scheduling, and deeper production planning |
| Payroll, manufacturing, and cost analytics starter queries and process docs | More advanced payroll-control and labor-planning scenarios |
| O2C, P2P, recurring journals, close-cycle activity, and posted ledger data | Additional advanced analytics packs |
| SQLite, Excel, validation, anomaly, and log outputs | Broader process extensions beyond the current teaching core |

## Build It Yourself

Most users do not need to run the generator locally. If you do, run the commands below from the repository root.

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
