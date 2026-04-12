# Greenfield Accounting Dataset

Greenfield Accounting Dataset is a synthetic business database for undergraduate and graduate accounting analytics courses. It is designed for student work in SQL, Excel, auditing analytics, business-process tracing, and source-to-ledger analysis.

The documentation website is the primary starting point:

- [Greenfield documentation site](https://greenfield.accountinganalyticshub.com/)
- [Quick Start](https://greenfield.accountinganalyticshub.com/docs/quick-start)
- [Downloads](https://greenfield.accountinganalyticshub.com/docs/downloads)
- [Instructor adoption guide](https://greenfield.accountinganalyticshub.com/docs/teach-with-greenfield/instructor-adoption)

Most students should begin with the documentation site and the packaged output files rather than the Python generator.

## What This Repository Contains

- a five-year teaching dataset covering fiscal years 2026 through 2030
- 55 implemented tables across accounting, O2C, P2P, manufacturing, payroll and time, master data, and planning
- starter SQL packs for financial, managerial, and audit analytics
- ready-to-use download files for SQLite and Excel through GitHub Releases
- local generator support for validation reporting and generation logs

Student download files:

- `greenfield_2026_2030.sqlite`
- `greenfield_2026_2030.xlsx`

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

- [Dataset Delivery and Build Setup](https://greenfield.accountinganalyticshub.com/docs/technical/dataset-delivery)

## Repository Links

- [Documentation website](https://greenfield.accountinganalyticshub.com/)
- [Contributing guide](CONTRIBUTING.md)
- [License](LICENSE)
