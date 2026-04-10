# Analytics Starter Layer

**Audience:** Students, instructors, and analysts who want a practical starting point for using the dataset.  
**Purpose:** Organize the starter analytics materials by topic and show where to begin in SQL and Excel.  
**What you will learn:** Which documents and query packs cover financial, managerial, and audit analytics, and how to move from the generated database to classroom-ready analysis.

> **Implemented in current generator:** Starter analytics documentation, runnable SQLite query files, and Excel workflow guidance for financial accounting, managerial accounting, auditing, payroll, and manufacturing-related analysis.

> **Planned future extension:** Capacity planning, richer labor-scheduling analysis, and time-clock detail.

## What This Starter Layer Includes

- topic guides for financial, managerial, and audit analytics
- a SQLite-first starter SQL package under `queries/`
- Excel workflow guidance using the generated workbook
- instructor-facing mapping from learning goals to materials

## Coverage Map

| Analytics area | Start with | Starter SQL folder | Best paired workbook sheets |
|---|---|---|---|
| Financial accounting | [financial.md](financial.md) | [queries/financial](../../queries/financial) | `GLEntry`, `Account`, `SalesInvoice`, `CashReceiptApplication`, `CreditMemo`, `PurchaseInvoice`, `JournalEntry`, `PayrollRegister`, `PayrollLiabilityRemittance`, `WorkOrderClose` |
| Managerial accounting | [managerial.md](managerial.md) | [queries/managerial](../../queries/managerial) | `Budget`, `CostCenter`, `Item`, `BillOfMaterial`, `WorkOrder`, `MaterialIssueLine`, `ProductionCompletionLine`, `LaborTimeEntry`, `ShipmentLine`, `PurchaseOrderLine` |
| Auditing | [audit.md](audit.md) | [queries/audit](../../queries/audit) | operational document sheets, payroll sheets, `GLEntry`, `JournalEntry`, `AnomalyLog`, `ValidationSummary` |
| SQL workflow | [sql-guide.md](sql-guide.md) | All starter SQL folders | SQLite database |
| Excel workflow | [excel-guide.md](excel-guide.md) | Use SQL results as a comparison point | Excel workbook |
