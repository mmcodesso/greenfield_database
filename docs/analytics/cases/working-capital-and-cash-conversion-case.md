---
title: Working Capital and Cash Conversion Case
description: Guided walkthrough for control-account balances and settlement timing across AR, AP, deposits, payroll, and accruals.
sidebar_label: Working Capital Case
---

# Working Capital and Cash Conversion Case

## Audience and Purpose

Use this case when students need to connect operating documents to month-end working-capital balances and cash-conversion timing.

## Recommended Build Mode

- Clean or default build

## Business Scenario

Greenfield’s finance team wants to explain why working capital moves from month to month. The question is not only whether AR or AP went up. The question is how invoices, receipts, applications, supplier payments, payroll liabilities, customer deposits, and accrued expenses combine into a working-capital story.

## Main Tables and Worksheets

- `GLEntry`
- `Account`
- `SalesInvoice`
- `CashReceiptApplication`
- `PurchaseInvoice`
- `DisbursementPayment`
- `GoodsReceipt`
- `PayrollRegister`
- `PayrollLiabilityRemittance`
- `greenfield_support.xlsx`:
  - `ValidationChecks`

## Recommended Query Sequence

1. Run [../../../queries/financial/19_working_capital_bridge_by_month.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/19_working_capital_bridge_by_month.sql).
2. Run [../../../queries/financial/20_cash_conversion_timing_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/20_cash_conversion_timing_review.sql).
3. Run [../../../queries/financial/02_ar_aging_open_invoices.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/02_ar_aging_open_invoices.sql).
4. Run [../../../queries/financial/03_ap_aging_open_invoices.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/03_ap_aging_open_invoices.sql).
5. Run [../../../queries/financial/12_accrued_expense_rollforward.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/12_accrued_expense_rollforward.sql).
6. Run [../../../queries/financial/15_customer_deposits_and_unapplied_cash_aging.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/15_customer_deposits_and_unapplied_cash_aging.sql).

## Suggested Excel Sequence

1. Build a month-by-month bridge from `GLEntry` and `Account` for AR, inventory, AP, GRNI, customer deposits, accrued expenses, and payroll liabilities.
2. Add a second view that compares invoice-to-application, invoice-to-payment, and receipt-to-payment timing.
3. Filter the workbook to one year when you want a smaller in-class discussion.

## What Students Should Notice

- Working capital is a timing story, not only a balance-sheet story.
- Customer deposits and unapplied cash can move independently from AR.
- Goods receipt to payment timing is not the same as purchase invoice to payment timing.
- Payroll liabilities and accrued expenses are part of working capital, even though they do not look like sales or inventory activity.

## Follow-Up Questions

- Which working-capital bucket moves the most across the modeled range?
- Which timing metric would you expect management to monitor most closely?
- Why can working capital tighten even when revenue is rising?
