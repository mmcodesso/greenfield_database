---
title: Financial Analytics
description: Starter financial-accounting analysis paths using the published dataset.
sidebar_label: Financial Analytics
---

import { QueryCatalog } from "@site/src/components/QueryReference";
import { starterQueryMaps } from "@site/src/generated/queryDocCollections";

# Financial Analytics Starter Guide

## Relevant Tables

| Topic | Main tables |
|---|---|
| Balance sheet reporting | `GLEntry`, `Account`, `JournalEntry` |
| Cash flow reporting | `GLEntry`, `Account`, `JournalEntry` |
| Income statement reporting | `GLEntry`, `Account`, `JournalEntry` |
| Revenue and gross margin | `SalesInvoice`, `SalesInvoiceLine`, `ShipmentLine`, `CreditMemoLine`, `Item`, `PriceList`, `PriceListLine`, `PromotionProgram`, `GLEntry`, `Account` |
| AR and customer cash | `SalesInvoice`, `CashReceipt`, `CashReceiptApplication`, `CreditMemo`, `CustomerRefund`, `Customer` |
| AP and supplier cash | `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment`, `Supplier`, `GoodsReceipt` |
| Working capital | `GLEntry`, `Account`, `SalesInvoice`, `CashReceiptApplication`, `PurchaseInvoice`, `DisbursementPayment`, `PayrollRegister`, `PayrollLiabilityRemittance` |
| Accrued expenses | `JournalEntry`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment`, `GLEntry`, `Account`, `Supplier`, `Item` |
| Payroll liabilities and support | `PayrollPeriod`, `TimeClockEntry`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollPayment`, `PayrollLiabilityRemittance`, `Employee` |
| Manufacturing balances | `WorkOrderClose`, `ProductionCompletionLine`, `MaterialIssueLine`, `JournalEntry`, `GLEntry`, `Account` |
| Trial balance and close cycle | `GLEntry`, `JournalEntry`, `Account` |

## Starter SQL Map

<QueryCatalog items={starterQueryMaps.financial} />

## Financial Statement Reconciliation Path

- Start from `config/settings_reconciliation.yaml` when the goal is financial-integrity investigation. It keeps the full-size build, disables anomaly injection, turns off non-SQLite exports, and writes separate clean SQLite and generation-log outputs so the clean investigation run does not overwrite anomaly evidence.
- Treat the default `config/settings.yaml` build as the anomaly-enriched comparison set when `anomaly_mode` remains `standard`.
- Run `financial/39_annual_income_to_equity_bridge.sql` first to compare annual income-statement net income, the retained-earnings close to `3030`, year-end retained earnings, and the annual balance-sheet residual.
- Run `financial/40_post_close_profit_and_loss_leakage_review.sql` next to find any revenue, expense, or `8010` balances that remain open after the close.
- Run `financial/41_round_dollar_manual_journal_close_sensitivity_review.sql` only when you are using a custom close-breaking anomaly profile or a manually altered dataset that leaves unexplained residuals after close. The default `standard` anomaly profile no longer uses this anomaly because it preserves financial-statement tie-out.
- Start the account-by-account workflow with `financial/42_annual_net_revenue_bridge.sql`.
- When annual net revenue does not tie from source documents into the GL, run `financial/43_invoice_revenue_cutoff_exception_summary.sql` to isolate the invoice headers whose invoice year differs from the revenue GL fiscal year or whose revenue posting is incomplete.
- Run `financial/44_invoice_revenue_cutoff_exception_trace.sql` next to inspect the affected invoice lines, linked shipment lines, and operating-revenue GL rows.
- Keep `audit/04_cutoff_and_timing_analysis.sql` and `audit/06_potential_anomaly_review.sql` as supporting context. They provide the broader timing scan; the new financial queries narrow the population to the invoices that actually affect annual net-revenue reconciliation.
- If the clean build returns rows in `financial/43_invoice_revenue_cutoff_exception_summary.sql`, treat that as a real process defect. If the clean build stays empty and the anomaly build shows `InvoiceBeforeShipmentFlag = 1` with `InvoiceYearVsGlYearFlag = 1`, classify the result as seeded anomaly behavior rather than a statement-query defect.
- After net revenue, repeat the same source-to-GL-to-statement-to-close pattern for COGS, manufacturing variance, labor, overhead, operating expenses, other income and expense, and retained earnings.

## Recommended Case Pairings

- Use [Working Capital and Cash Conversion Case](cases/working-capital-and-cash-conversion-case.md) when you want a balance-sheet and settlement-timing exercise.
- Use [Financial Statement Bridge Case](cases/financial-statement-bridge-case.md) when you want to move from operations into `GLEntry`, control accounts, and close entries.
- Use [Product Portfolio Profitability Case](cases/product-portfolio-profitability-case.md) when you want a financial view of collection, lifecycle, and supply-mode performance.
- Use [Demand Planning and Replenishment Case](cases/demand-planning-and-replenishment-case.md) when you want forecast, replenishment, and planning-pressure analysis to sit beside working-capital and inventory timing.
- Use [Pricing and Margin Governance Case](cases/pricing-and-margin-governance-case.md) when you want list-price realization, promotions, override pressure, and net-margin dilution in one commercial analysis path.

## Interpretation Notes

- Revenue posts at invoicing. COGS posts at shipment.
- `CashReceipt` does not equal settled AR by itself. Use `CashReceiptApplication`.
- Payroll register activity records liabilities first; cash leaves through payroll payments and remittances later.
- Working-capital analysis gets stronger when students separate balances from timing.
- Forecast, policy, and replenishment tables support planning-informed working-capital and inventory-timing analysis.
- Explicit price-list, promotion, and override lineage lets students analyze revenue and margin against commercial rules.
- The richer item master now supports collection, style family, lifecycle, and supply-mode financial analysis without changing the underlying posting model.
- The richer employee master now supports job-family, job-level, and people-cost review without requiring a separate HR-history subledger.
- Customer deposits and unapplied cash analysis should start from `CashReceipt` and `CashReceiptApplication`, alongside AR.
- Accrued-expense analysis should focus on `2040`, `PurchaseInvoiceLine.AccrualJournalEntryID`, and the service-item lines that settle those estimates.
- Year-end close entries are real posted journals and should be filtered when you want raw multi-year P&L activity.
- The income-statement starter queries use pre-close P&L activity, so they exclude the year-end close journals that zero out revenue and expense accounts.
- The balance-sheet starter queries are point-in-time ending-balance statements, not monthly activity reports.
- The balance-sheet starter queries derive `Current Year Earnings` for interim periods so assets continue to tie to liabilities plus equity before the annual close moves earnings into retained earnings.
- The indirect-method cash flow starter queries reconcile from pre-close net income into operating cash, then combine that with investing and financing cash movements.
- The direct-method cash flow starter queries classify cash-ledger activity into teaching buckets such as customer receipts, supplier payments, payroll, and other operating cash.
- The cash flow starter queries treat opening journals as the `Beginning Cash` seed for the first reporting period instead of showing them as operating, investing, or financing flows.
- The published default SQLite is anomaly-enriched when `anomaly_mode` is `standard`, so it is useful for teaching comparisons but not as the clean baseline for database-integrity reconciliation.
