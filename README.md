# Greenfield Accounting Dataset

Greenfield Accounting Dataset is a synthetic business database for undergraduate and graduate accounting analytics courses. It is designed for student work in SQL, Excel, auditing analytics, business-process tracing, and source-to-ledger analysis.

The documentation website is the primary starting point:

- [Greenfield documentation site](https://mmcodesso.github.io/greenfield_database/)
- [Quick Start](https://mmcodesso.github.io/greenfield_database/docs/quick-start)
- [Instructor adoption guide](https://mmcodesso.github.io/greenfield_database/docs/teach-with-greenfield/instructor-adoption)

Most students should begin with the documentation site and the packaged output files rather than the Python generator.

## What This Repository Contains

- a five-year teaching dataset covering fiscal years 2026 through 2030
- 55 implemented tables across accounting, O2C, P2P, manufacturing, payroll and time, master data, and planning
- starter SQL packs for financial, managerial, and audit analytics
- generated output support for SQLite, Excel, validation reporting, and generation logs

Core generated files:

- `outputs/greenfield_2026_2030.sqlite`
- `outputs/greenfield_2026_2030.xlsx`
- `outputs/validation_report.json`
- `outputs/generation.log`

## View the Docs Locally

```bash
npm install
npm run start
```

To build the production site:

```bash
npm run build
```

## Teaching Package Setup

If you need to generate or refresh the classroom dataset locally, use the teaching guide:

- [Dataset Delivery and Build Setup](https://mmcodesso.github.io/greenfield_database/docs/technical/dataset-delivery)

## Repository Links

- [Documentation website](https://mmcodesso.github.io/greenfield_database/)
- [Contributing guide](CONTRIBUTING.md)
- [License](LICENSE)
