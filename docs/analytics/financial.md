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
