---
title: Analytics Hub
description: Starter map for financial, managerial, and audit analytics using Greenfield.
slug: /analytics
sidebar_label: Analytics Hub
---

# Analytics Starter Layer


## What This Starter Layer Includes

- topic guides for financial, managerial, and audit analytics
- a SQLite-first starter SQL package in the repository under `queries/`
- Excel workflow guidance using the generated workbook
- instructor-facing mapping from learning goals to materials

## Coverage Map

| Analytics area | Start with | Starter SQL folder | Best paired workbook sheets |
|---|---|---|---|
| Financial accounting | [Financial Analytics](financial.md) | [queries/financial](https://github.com/mmcodesso/greenfield_database/tree/main/queries/financial) | `GLEntry`, `Account`, `SalesInvoice`, `CashReceiptApplication`, `CreditMemo`, `PurchaseInvoice`, `JournalEntry`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollLiabilityRemittance`, `TimeClockEntry`, `WorkOrderClose` |
| Managerial accounting | [Managerial Analytics](managerial.md) | [queries/managerial](https://github.com/mmcodesso/greenfield_database/tree/main/queries/managerial) | `Budget`, `CostCenter`, `Item`, `BillOfMaterial`, `WorkOrder`, `MaterialIssueLine`, `ProductionCompletionLine`, `LaborTimeEntry`, `TimeClockEntry`, `ShiftDefinition`, `WorkCenter`, `ShipmentLine`, `PurchaseOrderLine` |
| Auditing | [Audit Analytics](audit.md) | [queries/audit](https://github.com/mmcodesso/greenfield_database/tree/main/queries/audit) | operational document sheets, payroll sheets, `TimeClockEntry`, `AttendanceException`, `GLEntry`, `JournalEntry`, plus the support workbook sheets `AnomalyLog`, `ValidationStages`, `ValidationChecks`, and `ValidationExceptions` |
| SQL workflow | [SQL Guide](sql-guide.md) | All starter SQL folders | SQLite database |
| Excel workflow | [Excel Guide](excel-guide.md) | Use SQL results as a comparison point | Excel workbook |
| Guided walkthroughs | [Analytics Cases](cases/index.md) | Mix financial, managerial, and audit packs in sequence | SQLite plus workbook side-by-side |

## Recommended Starter Package

For normal student, instructor, and analyst use, start with the standard course package shared for your class.

If you are the instructor preparing that package yourself, use [Dataset Delivery and Build Setup](../teach-with-greenfield/dataset-delivery.md).
