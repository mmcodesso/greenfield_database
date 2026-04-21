---
title: Financial Analytics
description: Starter financial-accounting analysis paths using the published dataset.
sidebar_label: Financial Analytics
---

import { QueryCatalog, QuerySequence } from "@site/src/components/QueryReference";
import { starterQueryMaps } from "@site/src/generated/queryDocCollections";

# Financial Analytics Starter Guide

## Relevant Tables

| Topic | Main tables |
|---|---|
| Balance sheet reporting | `GLEntry`, `Account`, `JournalEntry` |
| Cash flow reporting | `GLEntry`, `Account`, `JournalEntry` |
| Income statement reporting | `GLEntry`, `Account`, `JournalEntry` |
| Revenue and gross margin | `SalesInvoice`, `SalesInvoiceLine`, `Shipment`, `ShipmentLine`, `CreditMemo`, `CreditMemoLine`, `Item`, `PriceList`, `PriceListLine`, `PromotionProgram`, `GLEntry`, `Account` |
| AR and customer cash | `SalesInvoice`, `CashReceipt`, `CashReceiptApplication`, `CreditMemo`, `CustomerRefund`, `Customer` |
| AP and supplier cash | `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment`, `Supplier`, `GoodsReceipt` |
| Working capital | `GLEntry`, `Account`, `SalesInvoice`, `CashReceiptApplication`, `PurchaseInvoice`, `DisbursementPayment`, `PayrollRegister`, `PayrollLiabilityRemittance` |
| Accrued expenses | `JournalEntry`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `Shipment`, `GLEntry`, `Account`, `Supplier`, `Item` |
| Payroll liabilities and support | `PayrollPeriod`, `TimeClockEntry`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollPayment`, `PayrollLiabilityRemittance`, `Employee` |
| Manufacturing balances | `WorkOrderClose`, `ProductionCompletionLine`, `MaterialIssueLine`, `JournalEntry`, `GLEntry`, `Account` |
| Trial balance and close cycle | `GLEntry`, `JournalEntry`, `Account` |

## Starter SQL Map

<QueryCatalog items={starterQueryMaps.financial} />

## Financial Statement Reconciliation Path

This sequence follows the statement tie from annual net income into retained earnings, then narrows into revenue reconciliation when the statement view and the operational view stop matching. Work through the queries in order so the bridge stays connected from statement to ledger to source document.

<QuerySequence
  items={[
    {
      queryKey: "financial/39_annual_income_to_equity_bridge.sql",
      lead: "Start with the annual statement tie between net income, retained earnings, and the balance-sheet residual.",
    },
    {
      queryKey: "financial/40_post_close_profit_and_loss_leakage_review.sql",
      lead: "Then confirm that no revenue, expense, or `8010` balances remain open after the close.",
    },
    {
      queryKey: "financial/41_round_dollar_manual_journal_close_sensitivity_review.sql",
      lead: "Use this sensitivity review only when a custom anomaly profile or manual edit leaves unexplained residuals after close.",
    },
    {
      queryKey: "financial/42_annual_net_revenue_bridge.sql",
      lead: "Then move account by account into annual net revenue.",
    },
    {
      queryKey: "financial/43_invoice_revenue_cutoff_exception_summary.sql",
      lead: "Open the cutoff summary when annual net revenue does not tie from source documents into the GL.",
    },
    {
      queryKey: "financial/44_invoice_revenue_cutoff_exception_trace.sql",
      lead: "Then inspect the affected invoice lines, shipment lines, and revenue GL rows in detail.",
    },
  ]}
  helperText="Open each query from the guide and work through the sequence from statement tie-out into revenue cutoff detail."
/>

- Keep the broader timing scan in view through [Audit Analytics](audit.md), especially `Cutoff and timing analysis` and `Potential anomaly review`. Those queries show the wider timing population, while the reconciliation sequence narrows the investigation to the invoices that actually affect annual net-revenue tie-out.
- If the cutoff summary shows invoices with `InvoiceBeforeShipmentFlag = 1` and `InvoiceYearVsGlYearFlag = 1`, treat that pattern as seeded anomaly behavior inside the published teaching dataset rather than a defect in the statement logic.
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
- Accrued-expense analysis should focus on `2040`, `PurchaseInvoiceLine.AccrualJournalEntryID`, the service-item lines that settle finance-managed estimates, and the outbound-freight accrual and settlement pattern created from `Shipment.FreightCost`.
- Year-end close entries are real posted journals and should be filtered when you want raw multi-year P&L activity.
- The income-statement starter queries use pre-close P&L activity, so they exclude the year-end close journals that zero out revenue and expense accounts.
- The balance-sheet starter queries are point-in-time ending-balance statements, not monthly activity reports.
- The balance-sheet starter queries derive `Current Year Earnings` for interim periods so assets continue to tie to liabilities plus equity before the annual close moves earnings into retained earnings.
- The indirect-method cash flow starter queries reconcile from pre-close net income into operating cash, then combine that with investing and financing cash movements.
- The direct-method cash flow starter queries classify cash-ledger activity into teaching buckets such as customer receipts, supplier payments, payroll, and other operating cash.
- The cash flow starter queries treat opening journals as the `Beginning Cash` seed for the first reporting period instead of showing them as operating, investing, or financing flows.
- The published default SQLite is anomaly-enriched when `anomaly_mode` is `standard`, so it is useful for teaching comparisons but not as the clean baseline for database-integrity reconciliation.
