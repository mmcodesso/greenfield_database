# Charles River Accounting Dataset Release Candidate

Replace `<rc-tag>` below with your GitHub release tag, for example `v1.0.0-rc1`.

## Suggested GitHub Release Title

`Charles River Accounting Dataset <rc-tag>`

## Suggested GitHub Release Body

This release candidate packages the current Charles River Accounting Dataset for classroom and analytics use. It includes the published SQLite database, the Excel workbook, the support workbook, and the CSV export package built from the current five-year teaching dataset.

This candidate also includes the expanded financial report layer for receivables and payables aging, including month-end AR/AP detail and summary outputs, plus the related documentation, report catalog entries, and validation coverage needed for GitHub distribution.

## Download Files

- [CharlesRiver.sqlite](https://github.com/mmcodesso/greenfield_database/releases/download/<rc-tag>/CharlesRiver.sqlite)
- [CharlesRiver.xlsx](https://github.com/mmcodesso/greenfield_database/releases/download/<rc-tag>/CharlesRiver.xlsx)
- [CharlesRiver_support.xlsx](https://github.com/mmcodesso/greenfield_database/releases/download/<rc-tag>/CharlesRiver_support.xlsx)
- [CharlesRiver_csv.zip](https://github.com/mmcodesso/greenfield_database/releases/download/<rc-tag>/CharlesRiver_csv.zip)

## Documentation Links

- [Documentation site](https://charlesriver.accountinganalyticshub.com/)
- [Start Here](https://charlesriver.accountinganalyticshub.com/docs/)
- [Downloads](https://charlesriver.accountinganalyticshub.com/docs/downloads)
- [Financial Reports](https://charlesriver.accountinganalyticshub.com/docs/analytics/reports/financial)
- [Customize / Dataset Delivery](https://charlesriver.accountinganalyticshub.com/docs/technical/dataset-delivery)

## Source and File Links

- [README](https://github.com/mmcodesso/greenfield_database/blob/main/README.md)
- [Report catalog](https://github.com/mmcodesso/greenfield_database/blob/main/config/report_catalog.yaml)
- [Monthly AR Aging Detail SQL](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/45_monthly_ar_aging_detail.sql)
- [Monthly AR Aging Summary SQL](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/46_monthly_ar_aging_summary.sql)
- [Monthly AP Aging Detail SQL](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/47_monthly_ap_aging_detail.sql)
- [Monthly AP Aging Summary SQL](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/48_monthly_ap_aging_summary.sql)
- [Financial reports docs](https://github.com/mmcodesso/greenfield_database/blob/main/docs/analytics/reports/financial.md)
- [Dataset delivery docs](https://github.com/mmcodesso/greenfield_database/blob/main/docs/technical/dataset-delivery.md)
- [Report export test coverage](https://github.com/mmcodesso/greenfield_database/blob/main/tests/test_report_exports.py)
- [Monthly aging report tests](https://github.com/mmcodesso/greenfield_database/blob/main/tests/test_monthly_aging_report_queries.py)

## Optional Short Version

Charles River Accounting Dataset `<rc-tag>` is the current release candidate for the classroom package. It includes the SQLite database, Excel workbook, support workbook, and CSV zip, along with the expanded month-end AR/AP aging report set and updated documentation.

Files:

- [CharlesRiver.sqlite](https://github.com/mmcodesso/greenfield_database/releases/download/<rc-tag>/CharlesRiver.sqlite)
- [CharlesRiver.xlsx](https://github.com/mmcodesso/greenfield_database/releases/download/<rc-tag>/CharlesRiver.xlsx)
- [CharlesRiver_support.xlsx](https://github.com/mmcodesso/greenfield_database/releases/download/<rc-tag>/CharlesRiver_support.xlsx)
- [CharlesRiver_csv.zip](https://github.com/mmcodesso/greenfield_database/releases/download/<rc-tag>/CharlesRiver_csv.zip)
