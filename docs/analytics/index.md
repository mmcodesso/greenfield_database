# Analytics Starter Layer

**Audience:** Students, instructors, and analysts who want a practical starting point for using the dataset.  
**Purpose:** Organize the starter analytics materials by topic and show where to begin in SQL and Excel.  
**What you will learn:** Which documents and query packs cover financial, managerial, and audit analytics, and how to move from the generated database to classroom-ready analysis.

> **Implemented in current generator:** Starter analytics documentation, runnable SQLite query files, and Excel workflow guidance for financial accounting, managerial accounting, and auditing analytics.

> **Planned future extension:** Manufacturing analytics packs after Phase 12.

## What This Starter Layer Includes

- topic guides for financial, managerial, and audit analytics
- a SQLite-first starter SQL package under `queries/`
- Excel workflow guidance using the generated workbook
- instructor-facing mapping from learning goals to materials

This layer is designed for the current stable dataset. It does not assume future manufacturing tables or work-in-process accounting.

## Recommended Starting Path

1. Start with the release SQLite and Excel files, or generate them locally if needed.
2. Read [../company-story.md](../company-story.md) and [../process-flows.md](../process-flows.md) if you need the business context first.
3. Read [sql-guide.md](sql-guide.md) to understand how the query pack is organized.
4. Pick an analytics area below.
5. Use the matching SQL files first.
6. Use [excel-guide.md](excel-guide.md) to build the same ideas in Excel pivots.

## Coverage Map

| Analytics area | Start with | Starter SQL folder | Best paired workbook sheets |
|---|---|---|---|
| Financial accounting | [financial.md](financial.md) | [queries/financial](../../queries/financial) | `GLEntry`, `Account`, `SalesInvoice`, `CashReceiptApplication`, `CreditMemo`, `CustomerRefund`, `PurchaseInvoice`, `DisbursementPayment`, `JournalEntry` |
| Managerial accounting | [managerial.md](managerial.md) | [queries/managerial](../../queries/managerial) | `Budget`, `CostCenter`, `Item`, `SalesInvoiceLine`, `ShipmentLine`, `GoodsReceiptLine`, `PurchaseOrderLine`, `PurchaseInvoiceLine` |
| Auditing | [audit.md](audit.md) | [queries/audit](../../queries/audit) | operational document sheets, `GLEntry`, `JournalEntry`, `AnomalyLog`, `ValidationSummary` |
| SQL workflow | [sql-guide.md](sql-guide.md) | All starter SQL folders | SQLite database |
| Excel workflow | [excel-guide.md](excel-guide.md) | Use SQL results as a comparison point | Excel workbook |

## Suggested Use by Audience

### Student path

1. Read [../company-story.md](../company-story.md) and [../process-flows.md](../process-flows.md).
2. Read [../database-guide.md](../database-guide.md).
3. Start with one area guide:
   - [financial.md](financial.md)
   - [managerial.md](managerial.md)
   - [audit.md](audit.md)
4. Run the linked SQL files and compare the results to Excel pivots.

### Instructor path

1. Read [../instructor-guide.md](../instructor-guide.md).
2. Use this starter layer to map topics to class sessions.
3. Decide whether to teach on:
   - a clean run with `anomaly_mode: none`
   - the default `standard` run with planted exceptions

### Analyst path

1. Open the SQLite export.
2. Use [sql-guide.md](sql-guide.md) and the query folders.
3. Use the topic guides only as interpretation support.

## Clean Dataset vs Anomaly-Enabled Dataset

- The starter SQL files run against the current implemented schema.
- Some audit-oriented queries may return no rows on a clean build.
- The default `standard` anomaly mode is useful for control-testing and exception-oriented exercises.
- The Excel workbook includes `AnomalyLog` and `ValidationSummary`, but those are export artifacts, not schema tables in SQLite.

## Scope Boundaries

The current starter layer is intentionally built around the current dataset only. It does **not** assume:

- manufacturing tables
- work orders or bills of materials
- WIP accounting
- payroll subledgers or tax-withholding detail

Those are future expansions, not missing rows inside the current starter package.

## Where to Go Next

- Read [sql-guide.md](sql-guide.md) for the query-running workflow.
- Read [excel-guide.md](excel-guide.md) for workbook setup and pivot guidance.
- Read [../instructor-guide.md](../instructor-guide.md) for the teaching sequence that uses these materials.
