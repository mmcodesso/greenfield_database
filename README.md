# Greenfield Accounting Dataset Generator

Greenfield Accounting Dataset Generator creates a reproducible synthetic accounting database for teaching, audit analytics, accounting analytics, SQL practice, subledger-to-ledger reconciliation, and business process analysis.

The fictional company is **Greenfield Home Furnishings, Inc.**, a mid-sized distributor and light assembler of home furnishings. The generated dataset covers fiscal years **2026 through 2030** and includes order-to-cash, procure-to-pay, master data, budgets, general ledger postings, validation results, and planted anomalies.

## What It Generates

The generator creates a full SQLite database, an Excel workbook, and a validation/anomaly report:

```text
outputs/
|-- greenfield_2026_2030.sqlite
|-- greenfield_2026_2030.xlsx
|-- validation_report.json
`-- generation.log
```

Generated output files are ignored by Git. Regenerate them locally whenever needed.

## Dataset Scope

- Fiscal calendar: monthly periods from `2026-01-01` through `2030-12-31`
- Accounting model: perpetual inventory with standard-cost COGS at shipment
- Revenue cycle: customers, sales orders, shipments, sales invoices, and cash receipts
- Procurement cycle: suppliers, requisitions, purchase orders, goods receipts, purchase invoices, and disbursements
- Accounting core: chart of accounts, journal entry headers, and GL entries
- Planning data: monthly budgets by account and cost center
- Anomaly layer: configurable planted anomalies for analytics exercises
- Exports: SQLite, Excel, and JSON validation report

## Current Generated Scale

With the default configuration, the full five-year run currently produces approximately:

| Table | Rows |
|---|---:|
| Account | 87 |
| Customer | 220 |
| Supplier | 110 |
| Item | 240 |
| Employee | 64 |
| Budget | 2,940 |
| SalesOrder | 6,950 |
| SalesOrderLine | 24,150 |
| Shipment | 6,352 |
| ShipmentLine | 21,186 |
| SalesInvoice | 6,332 |
| SalesInvoiceLine | 21,115 |
| CashReceipt | 5,347 |
| PurchaseRequisition | 4,155 |
| PurchaseOrder | 3,910 |
| PurchaseOrderLine | 3,910 |
| GoodsReceipt | 3,112 |
| GoodsReceiptLine | 3,112 |
| PurchaseInvoice | 2,768 |
| PurchaseInvoiceLine | 2,768 |
| DisbursementPayment | 2,210 |
| GLEntry | 106,355 |

Counts may change if configuration, random seed, or generation rules are changed.

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

Run tests:

```powershell
pytest -q
```

If you do not activate the virtual environment, run the generator with:

```powershell
.\.venv\Scripts\python.exe generate_dataset.py
```

## Configuration

Primary configuration lives in [config/settings.yaml](config/settings.yaml).

Important settings:

- `random_seed`: controls deterministic generation
- `fiscal_year_start` and `fiscal_year_end`: define the month range to generate
- `employee_count`, `customer_count`, `supplier_count`, `item_count`, `warehouse_count`: master-data scale
- `tax_rate`: sales tax rate applied to sales invoices
- `anomaly_mode`: anomaly profile selector
- `sqlite_path`, `excel_path`, `validation_report_path`, `generation_log_path`: output locations

Anomaly configuration lives in [config/anomaly_profile.yaml](config/anomaly_profile.yaml). The default `standard` profile injects approval, timing, duplicate-reference, threshold, and related-party address anomalies across the fiscal years.

The chart of accounts is configured in [config/accounts.csv](config/accounts.csv).

## Database Design

The implemented schema contains 24 logical tables:

| Area | Tables |
|---|---|
| Accounting Core | `Account`, `JournalEntry`, `GLEntry` |
| Order-to-Cash | `Customer`, `SalesOrder`, `SalesOrderLine`, `Shipment`, `ShipmentLine`, `SalesInvoice`, `SalesInvoiceLine`, `CashReceipt` |
| Procure-to-Pay | `Supplier`, `PurchaseRequisition`, `PurchaseOrder`, `PurchaseOrderLine`, `GoodsReceipt`, `GoodsReceiptLine`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment` |
| Master Data | `Item`, `Warehouse`, `Employee` |
| Organizational | `CostCenter`, `Budget` |

`GLEntry` is the reporting layer. Each operational posting carries:

- `VoucherType`
- `VoucherNumber`
- `SourceDocumentType`
- `SourceDocumentID`
- `SourceLineID`
- `FiscalYear`
- `FiscalPeriod`

See [SCHEMA_SPEC.md](SCHEMA_SPEC.md) and [Design.md](Design.md) for schema details.

## Accounting Logic

The posting engine is event-based and lives in [src/greenfield_dataset/posting_engine.py](src/greenfield_dataset/posting_engine.py).

Implemented posting events:

| Event | Debit | Credit |
|---|---|---|
| Shipment | COGS | Inventory |
| Sales invoice | Accounts Receivable | Sales Revenue and Sales Tax Payable |
| Cash receipt | Cash | Accounts Receivable |
| Goods receipt | Inventory | Goods Received Not Invoiced |
| Purchase invoice | GRNI and Purchase Price Variance as needed | Accounts Payable and variance as needed |
| Disbursement | Accounts Payable | Cash |

See [POSTING_RULES.md](POSTING_RULES.md) for posting details.

## How The Code Works

The main package is [src/greenfield_dataset](src/greenfield_dataset).

| Module | Responsibility |
|---|---|
| `settings.py` | Loads YAML settings and initializes the shared generation context |
| `calendar.py` | Builds fiscal date attributes |
| `schema.py` | Defines the canonical table registry and empty DataFrames |
| `master_data.py` | Generates cost centers, employees, warehouses, items, customers, suppliers, and loads accounts |
| `budgets.py` | Generates opening balances and budgets |
| `o2c.py` | Generates sales orders, shipments, sales invoices, and cash receipts |
| `p2p.py` | Generates requisitions, purchase orders, goods receipts, purchase invoices, and disbursements |
| `posting_engine.py` | Converts operational events into balanced GL entries |
| `validations.py` | Validates schema, totals, references, voucher balance, trial balance, and roll-forwards |
| `anomalies.py` | Injects configurable anomalies and writes an anomaly log |
| `exporters.py` | Exports SQLite, Excel, and validation JSON |
| `main.py` | Orchestrates the full build |

The root script [generate_dataset.py](generate_dataset.py) adds `src` to `sys.path` and calls `greenfield_dataset.main.main()`.

## Build Flow

The full generator runs this sequence:

1. Load settings and initialize the generation context
2. Create empty tables from the schema registry
3. Load chart of accounts
4. Generate cost centers, employees, warehouses, items, customers, and suppliers
5. Generate opening balances and budgets
6. Generate monthly O2C and P2P documents for each configured fiscal month
7. Generate shipments, goods receipts, invoices, receipts, and disbursements
8. Post operational activity to `GLEntry`
9. Run validations
10. Inject configured anomalies
11. Re-run final validation
12. Export SQLite, Excel, and JSON report

## Validation

The validation layer checks:

- Schema column consistency
- Header-line total agreement
- Orphan line references
- Shipment and receipt quantity limits
- Invoice and payment total limits
- Voucher-level GL balance
- Overall trial balance equality
- AR, AP, inventory, COGS, and GRNI roll-forward checks

The final validation report is written to `outputs/validation_report.json`.

## Generation Log

Each full run writes a detailed build log to `outputs/generation.log` by default. The log includes:

- Configuration values used for the run
- Timed start and finish entries for every major generation step
- Per-month progress for all configured fiscal months
- Row-count checkpoints after schema, master data, transaction generation, posting, and final export
- Validation exception summaries by phase
- Anomaly count and export locations

Change `generation_log_path` in [config/settings.yaml](config/settings.yaml) to write the log somewhere else.

## Anomalies

The default profile logs planted exceptions such as:

- Weekend journal metadata
- Same creator and approver on purchase orders
- Missing approval on converted requisitions
- Sales invoice dated before shipment
- Duplicate vendor payment references
- Requisitions just below approval thresholds
- Supplier addresses matching employee addresses

Anomalies are designed to preserve GL balance. They are intended for detection exercises rather than to corrupt the ledger.

## Repository Notes

- Generated output files are ignored by Git.
- `.venv/` and Python cache files are ignored by Git.
- `Design.md` is the long-form design blueprint.
- `TASKS.md` documents completed implementation phases.
- `ROW_VOLUME_MODEL.md` documents expected target row volumes.
- Tests live in [tests](tests).

## License

Unless otherwise noted, this work is licensed under the
[Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).

You may share and adapt the material for any purpose, including commercial use,
provided that you give appropriate attribution and distribute adaptations under
the same license.
