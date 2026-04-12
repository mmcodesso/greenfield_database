---
title: Financial Analytics
description: Starter financial-accounting analysis paths using the Greenfield dataset.
sidebar_label: Financial Analytics
---

# Financial Analytics Starter Guide

## Relevant Tables

| Topic | Main tables |
|---|---|
| Revenue and gross margin | `SalesInvoice`, `SalesInvoiceLine`, `ShipmentLine`, `CreditMemoLine`, `Item`, `GLEntry`, `Account` |
| AR and customer cash | `SalesInvoice`, `CashReceipt`, `CashReceiptApplication`, `CreditMemo`, `CustomerRefund`, `Customer` |
| AP and supplier cash | `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment`, `Supplier`, `GoodsReceipt` |
| Working capital | `GLEntry`, `Account`, `SalesInvoice`, `CashReceiptApplication`, `PurchaseInvoice`, `DisbursementPayment`, `PayrollRegister`, `PayrollLiabilityRemittance` |
| Accrued expenses | `JournalEntry`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment`, `GLEntry`, `Account`, `Supplier`, `Item` |
| Payroll liabilities and support | `PayrollPeriod`, `TimeClockEntry`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollPayment`, `PayrollLiabilityRemittance`, `Employee` |
| Manufacturing balances | `WorkOrderClose`, `ProductionCompletionLine`, `MaterialIssueLine`, `JournalEntry`, `GLEntry`, `Account` |
| Trial balance and close cycle | `GLEntry`, `JournalEntry`, `Account` |

## Starter SQL Map

| Topic | Starter SQL file |
|---|---|
| Monthly revenue and margin | [01_monthly_revenue_and_gross_margin.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/01_monthly_revenue_and_gross_margin.sql) |
| AR aging | [02_ar_aging_open_invoices.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/02_ar_aging_open_invoices.sql) |
| AP aging | [03_ap_aging_open_invoices.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/03_ap_aging_open_invoices.sql) |
| Trial balance | [04_trial_balance_by_period.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/04_trial_balance_by_period.sql) |
| Journal and close review | [05_journal_and_close_cycle_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/05_journal_and_close_cycle_review.sql) |
| Control-account reconciliation | [06_control_account_reconciliation.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/06_control_account_reconciliation.sql) |
| Customer credit and refunds | [07_customer_credit_and_refunds.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/07_customer_credit_and_refunds.sql) |
| Manufacturing balances | [08_manufacturing_wip_clearing_variance.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/08_manufacturing_wip_clearing_variance.sql) |
| Payroll liability roll-forward | [09_payroll_liability_rollforward.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/09_payroll_liability_rollforward.sql) |
| Gross-to-net payroll review | [10_gross_to_net_payroll_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/10_gross_to_net_payroll_review.sql) |
| Payroll cash payments and remittances | [11_payroll_cash_payments_and_remittances.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/11_payroll_cash_payments_and_remittances.sql) |
| Accrued expense roll-forward | [12_accrued_expense_rollforward.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/12_accrued_expense_rollforward.sql) |
| Accrual versus invoice versus payment timing | [13_accrued_vs_invoiced_vs_paid_timing.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/13_accrued_vs_invoiced_vs_paid_timing.sql) |
| Hourly payroll hours to paid earnings bridge | [14_hourly_payroll_hours_to_paid_earnings_bridge.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/14_hourly_payroll_hours_to_paid_earnings_bridge.sql) |
| Customer deposits and unapplied cash aging | [15_customer_deposits_and_unapplied_cash_aging.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/15_customer_deposits_and_unapplied_cash_aging.sql) |
| Retained earnings and close-entry impact | [16_retained_earnings_and_close_entry_impact.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/16_retained_earnings_and_close_entry_impact.sql) |
| Manufacturing cost-component bridge | [17_manufacturing_cost_component_bridge.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/17_manufacturing_cost_component_bridge.sql) |
| Payroll expense mix by cost center and pay class | [18_payroll_expense_mix_by_cost_center_and_pay_class.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/18_payroll_expense_mix_by_cost_center_and_pay_class.sql) |
| Working-capital bridge by month | [19_working_capital_bridge_by_month.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/19_working_capital_bridge_by_month.sql) |
| Cash-conversion timing review | [20_cash_conversion_timing_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/20_cash_conversion_timing_review.sql) |
| Revenue and gross margin by collection, style, lifecycle, and supply mode | [21_revenue_and_gross_margin_by_collection_style_lifecycle_supply_mode.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/21_revenue_and_gross_margin_by_collection_style_lifecycle_supply_mode.sql) |
| Payroll and people-cost mix by cost center, job family, and job level | [22_payroll_and_people_cost_mix_by_cost_center_job_family_level.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/22_payroll_and_people_cost_mix_by_cost_center_job_family_level.sql) |

## Phase 19 Pairings

- Use [Working Capital and Cash Conversion Case](cases/working-capital-and-cash-conversion-case.md) when you want a balance-sheet and settlement-timing exercise.
- Use [Financial Statement Bridge Case](cases/financial-statement-bridge-case.md) when you want to move from operations into `GLEntry`, control accounts, and close entries.
- Use [Product Portfolio Profitability Case](cases/product-portfolio-profitability-case.md) when you want a financial view of collection, lifecycle, and supply-mode performance.

## Interpretation Notes

- Revenue posts at invoicing. COGS posts at shipment.
- `CashReceipt` does not equal settled AR by itself. Use `CashReceiptApplication`.
- Payroll register activity records liabilities first; cash leaves through payroll payments and remittances later.
- Working-capital analysis gets stronger when students separate balances from timing.
- The richer item master now supports collection, style family, lifecycle, and supply-mode financial analysis without changing the underlying posting model.
- The richer employee master now supports job-family, job-level, and people-cost review without requiring a separate HR-history subledger.
- Customer deposits and unapplied cash analysis should start from `CashReceipt` and `CashReceiptApplication`, not only from AR.
- Accrued-expense analysis should focus on `2040`, `PurchaseInvoiceLine.AccrualJournalEntryID`, and the service-item lines that settle those estimates.
- Year-end close entries are real posted journals and should be filtered when you want raw multi-year P&L activity.
