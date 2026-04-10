# Financial Analytics Starter Guide

**Audience:** Students, instructors, and analysts starting with financial accounting questions in the dataset.  
**Purpose:** Show how to study revenue, COGS, receivables, payables, payroll liabilities, manufacturing balances, and journal activity.  
**What you will learn:** Which tables matter most, which joins are common, which starter SQL files to run, and how to reproduce the same ideas in Excel.

> **Implemented in current generator:** Revenue-cycle postings, receipt applications, customer deposits, returns and refunds, P2P liability postings, payroll liability postings, recurring manual journals, manufacturing balance flows, and a full `GLEntry` ledger suitable for multi-period analysis.

> **Planned future extension:** More advanced cash-flow, planning, and payroll-anomaly packs.

## Relevant Tables

| Topic | Main tables |
|---|---|
| Revenue and margin | `GLEntry`, `Account`, `SalesInvoice`, `SalesInvoiceLine`, `ShipmentLine`, `CreditMemo` |
| AR | `SalesInvoice`, `CashReceipt`, `CashReceiptApplication`, `CreditMemo`, `CustomerRefund`, `Customer`, `GLEntry` |
| AP | `PurchaseInvoice`, `DisbursementPayment`, `Supplier`, `GLEntry` |
| Accrued expenses | `JournalEntry`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment`, `GLEntry`, `Account`, `Supplier`, `Item` |
| Payroll liabilities | `PayrollPeriod`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollPayment`, `PayrollLiabilityRemittance`, `GLEntry`, `Account` |
| Manufacturing balances | `WorkOrderClose`, `ProductionCompletionLine`, `MaterialIssueLine`, `JournalEntry`, `GLEntry`, `Account` |
| Trial balance and journals | `GLEntry`, `JournalEntry`, `Account` |

## Starter SQL Map

| Topic | Starter SQL file |
|---|---|
| Monthly revenue and margin | [01_monthly_revenue_and_gross_margin.sql](../../queries/financial/01_monthly_revenue_and_gross_margin.sql) |
| AR aging | [02_ar_aging_open_invoices.sql](../../queries/financial/02_ar_aging_open_invoices.sql) |
| AP aging | [03_ap_aging_open_invoices.sql](../../queries/financial/03_ap_aging_open_invoices.sql) |
| Trial balance | [04_trial_balance_by_period.sql](../../queries/financial/04_trial_balance_by_period.sql) |
| Journal and close review | [05_journal_and_close_cycle_review.sql](../../queries/financial/05_journal_and_close_cycle_review.sql) |
| Control-account reconciliation | [06_control_account_reconciliation.sql](../../queries/financial/06_control_account_reconciliation.sql) |
| Customer credit and refunds | [07_customer_credit_and_refunds.sql](../../queries/financial/07_customer_credit_and_refunds.sql) |
| Manufacturing balances | [08_manufacturing_wip_clearing_variance.sql](../../queries/financial/08_manufacturing_wip_clearing_variance.sql) |
| Payroll liability roll-forward | [09_payroll_liability_rollforward.sql](../../queries/financial/09_payroll_liability_rollforward.sql) |
| Gross-to-net payroll review | [10_gross_to_net_payroll_review.sql](../../queries/financial/10_gross_to_net_payroll_review.sql) |
| Payroll cash payments and remittances | [11_payroll_cash_payments_and_remittances.sql](../../queries/financial/11_payroll_cash_payments_and_remittances.sql) |
| Accrued expense roll-forward | [12_accrued_expense_rollforward.sql](../../queries/financial/12_accrued_expense_rollforward.sql) |
| Accrual versus invoice versus payment timing | [13_accrued_vs_invoiced_vs_paid_timing.sql](../../queries/financial/13_accrued_vs_invoiced_vs_paid_timing.sql) |

## Interpretation Notes

- Revenue posts at invoicing. COGS posts at shipment.
- `CashReceipt` does not equal settled AR by itself. Use `CashReceiptApplication`.
- Payroll register activity records liabilities first; cash leaves through payroll payments and remittances later.
- Manufacturing balance analysis should focus on `1046`, `1090`, and `5080`.
- Accrued-expense analysis should focus on `2040`, `PurchaseInvoiceLine.AccrualJournalEntryID`, and the service-item lines that settle those estimates.
- Year-end close entries are real posted journals and should be filtered when you want raw multi-year P&L activity.
