---
title: Working Capital and Cash Conversion Case
description: Inquiry-led walkthrough for monthly working-capital movement and the timing patterns that sit behind AR, AP, deposits, payroll liabilities, and accruals.
sidebar_label: Working Capital Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# Working Capital and Cash Conversion Case

## Business Scenario

The finance team is reviewing month-to-month working-capital pressure. Sales and operations still look healthy on the surface, yet cash feels tighter than expected. Management needs a clear explanation of what is happening inside receivables, inventory and WIP, AP and GRNI, customer deposits, payroll liabilities, and accrued expenses.

This is a timing case as much as a balance case. Customer cash can arrive before AR settles. Goods can be received before suppliers are paid. Payroll liabilities can build before remittances leave the bank. Accrued expenses can raise current liabilities before supplier invoices appear. Finance needs one working-capital story that connects those moving parts.

Your job is to build that story from the control accounts first, then explain the settlement timing beneath those balances.

## The Problem to Solve

You need to prove which working-capital buckets moved the most by month, which timing patterns sit behind those balances, and how AR, AP, receipt timing, payroll liabilities, customer deposits, and accrued expenses change cash pressure. You also need to explain why customer cash arrival and AR settlement are separate events.

## What You Need to Develop

- A month-by-month working-capital narrative built from the main control accounts.
- A clear explanation of the aging and settlement patterns behind the biggest balances.
- A distinction between the classic cash-conversion buckets and the additional liability buckets that still affect cash pressure.
- A short management-facing conclusion on which working-capital driver deserves follow-up first.

## Key Data Sources

- Main tables: `GLEntry`, `Account`, `SalesInvoice`, `CashReceipt`, `CashReceiptApplication`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment`, `GoodsReceipt`, `PayrollRegister`, `PayrollPayment`, `PayrollLiabilityRemittance`, `JournalEntry`
- Related guides: [Financial Analytics](../financial.md), [Commercial and Working Capital](../reports/commercial-and-working-capital.md)
- Related process pages: [Order-to-Cash Process](../../processes/o2c.md), [Procure-to-Pay Process](../../processes/p2p.md), [Payroll Process](../../processes/payroll.md), [Manual Journals and Close Cycle](../../processes/manual-journals-and-close.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [GLEntry Posting Reference](../../reference/posting.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case focuses on balances plus timing. Use the statement bridge case when you need full statement presentation and close logic.

## Recommended Query Sequence

1. `financial/19_working_capital_bridge_by_month.sql`
2. `financial/02_ar_aging_open_invoices.sql`
3. `financial/15_customer_deposits_and_unapplied_cash_aging.sql`
4. `financial/03_ap_aging_open_invoices.sql`
5. `financial/20_cash_conversion_timing_review.sql`
6. `financial/09_payroll_liability_rollforward.sql`
7. `financial/11_payroll_cash_payments_and_remittances.sql`
8. `financial/12_accrued_expense_rollforward.sql`

## Step-by-Step Walkthrough

### Step 1. Define the monthly working-capital bridge

Start from the monthly control-account view. You need to know which buckets actually moved before you drill into settlement timing.

**What we are trying to achieve**

Establish the month-by-month movement in AR, inventory and WIP, AP, GRNI, customer deposits, accrued expenses, and payroll liabilities.

**Why this step changes the diagnosis**

This step sets the working-capital map. Without it, later timing analysis will be disconnected from the balances management is actually watching.

**Suggested query**

<QueryReference
  queryKey="financial/19_working_capital_bridge_by_month.sql"
  helperText="Use this first to identify the main monthly working-capital movements across current assets and current liabilities."
/>

**What this query does**

It builds a monthly bridge from `GLEntry` and `Account` and computes ending balances for the main working-capital buckets.

**How it works**

The query classifies posted GL movement by account number into working-capital buckets, calculates monthly net change, and then computes running ending balances by fiscal year and period.

**What to look for in the result**

- the largest monthly movements in net working capital
- whether pressure came from assets, liabilities, or both
- months where inventory and WIP moved differently from receivables
- months where deposits, payroll liabilities, or accrued expenses changed the story materially

### Step 2. Separate open receivables from customer cash and unapplied cash

Once the bridge shows AR and deposit pressure, move to the customer-side timing question. Cash arrival and invoice settlement are not the same event.

**What we are trying to achieve**

Distinguish open AR from customer cash that has already arrived but has not yet been fully applied.

**Why this step changes the diagnosis**

Students often treat receivables and customer cash as one number. That shortcut hides a real working-capital issue when receipts exist but invoice settlement still lags.

**Suggested query**

<QueryReference
  queryKey="financial/02_ar_aging_open_invoices.sql"
  helperText="Use this first to identify which customer invoices remain open and how old they are."
/>

<QueryReference
  queryKey="financial/15_customer_deposits_and_unapplied_cash_aging.sql"
  helperText="Use this follow-through query to separate customer cash receipts from actual invoice application."
/>

**What this query does**

The first query builds the open-AR aging view. The second shows receipts that remain unapplied or only partly applied.

**How it works**

The AR query starts from `SalesInvoice`, subtracts `CashReceiptApplication` and allocated `CreditMemo` activity, and computes the remaining open amount. The deposit query starts from `CashReceipt`, aggregates applications by receipt, and measures open unapplied balance plus days to first application.

**What to look for in the result**

- overdue invoices that still carry material open balance
- receipts with cash already received but not yet applied
- timing gaps between receipt date and first application date
- whether customer deposits and unapplied cash help explain the monthly bridge

### Step 3. Explain supplier-side timing through AP and receipt-to-payment lag

Now move to the supplier side. Working-capital pressure changes when invoices remain open, when receipts occur well before payment, or when GRNI timing pulls away from AP timing.

**What we are trying to achieve**

Connect open supplier invoices with invoice-to-payment timing and goods-receipt-to-payment timing.

**Why this step changes the diagnosis**

AP timing is only part of the story. Physical receipt happens earlier in the purchasing cycle and often changes how management interprets cash-conversion pressure.

**Suggested query**

<QueryReference
  queryKey="financial/03_ap_aging_open_invoices.sql"
  helperText="Use this to identify open supplier invoices and the current AP aging profile."
/>

<QueryReference
  queryKey="financial/20_cash_conversion_timing_review.sql"
  helperText="Use this follow-through query to compare invoice-to-payment timing with goods-receipt-to-payment timing."
/>

**What this query does**

The first query builds the open-AP aging listing. The second compares days to first settlement across sales invoices, purchase invoices, and goods receipts.

**How it works**

The AP query starts from `PurchaseInvoice`, subtracts `DisbursementPayment`, and computes open payable balance and aging. The timing query builds separate timing populations for invoice-to-application, purchase-invoice-to-payment, and goods-receipt-to-payment, then summarizes them by source month.

**What to look for in the result**

- open supplier invoices carrying the heaviest aging pressure
- months where receipt-to-payment lag ran longer than invoice-to-payment lag
- whether AP and GRNI move together or drift apart
- whether supplier-side timing helps offset or increase overall cash pressure

### Step 4. Explain payroll liabilities as a separate cash-pressure layer

Working capital in this dataset includes payroll liabilities. That cash pressure builds outside the sales and purchasing cycles.

**What we are trying to achieve**

Show how payroll liabilities accumulate before cash leaves through employee payments and statutory or benefit remittances.

**Why this step changes the diagnosis**

A narrow AR-inventory-AP view misses a real part of current-liability pressure. Payroll liabilities can stay material even when commercial activity looks stable.

**Suggested query**

<QueryReference
  queryKey="financial/09_payroll_liability_rollforward.sql"
  helperText="Use this first to measure payroll-liability movement by month and liability account."
/>

<QueryReference
  queryKey="financial/11_payroll_cash_payments_and_remittances.sql"
  helperText="Use this follow-through query to compare net-pay cash with payroll-liability remittance cash."
/>

**What this query does**

The first query measures monthly liability build and ending balance by payroll-liability account. The second separates employee cash payments from liability remittance cash outflows.

**How it works**

The rollforward query groups `GLEntry` by payroll-liability account and computes monthly net increase plus running ending balance. The cash-outflow query combines `PayrollPayment` and `PayrollLiabilityRemittance` by fiscal period and separates the cash streams into net pay, employee tax, employer tax, and benefits.

**What to look for in the result**

- liability accounts that build faster than they clear
- months where remittance timing lags the liability build
- whether net pay and remittances move together or separate
- how payroll liabilities affect the broader working-capital story

### Step 5. Explain accrued expenses and connect them back to cash-conversion pressure

Finish with accrued expenses. Finance creates these liabilities before supplier invoices appear, so they change the current-liability picture before AP settlement starts.

**What we are trying to achieve**

Show how accrued expenses increase current liabilities before later invoice settlement and connect that timing back to the broader cash-conversion story.

**Why this step changes the diagnosis**

Classic CCC metrics do not explain the whole cash picture in this dataset. Accrued expenses add a liability layer that finance controls directly, and that layer changes how management interprets pressure on cash.

**Suggested query**

<QueryReference
  queryKey="financial/12_accrued_expense_rollforward.sql"
  helperText="Use this first to measure accrual build, invoice clearing, adjustments, and residual liability."
/>

<QueryReference
  queryKey="financial/20_cash_conversion_timing_review.sql"
  helperText="Use this follow-through query again to keep supplier-side settlement timing in view while you interpret the accrued-expense balances."
/>

**What this query does**

The first query reconciles accrued-expense activity by month and expense family. The second provides the supplier-side settlement timing context that helps explain when those liabilities convert into cash outflow.

**How it works**

The accrual rollforward starts from `JournalEntry` rows tagged as accruals, joins them to `GLEntry`, and then compares accrued amount with later invoice clearing and any accrual adjustment activity. The timing review complements that by showing how quickly supplier-side documents moved toward first payment.

**What to look for in the result**

- months where accrued expenses grew faster than they cleared
- residual liabilities that stayed open after expected settlement windows
- expense families carrying the heaviest accrual pressure
- how accrued-expense timing changes the broader working-capital conclusion

## Optional Excel Follow-Through

1. Build a month-by-month pivot from `GLEntry` and `Account`.
2. Lay out AR, inventory and WIP, AP, GRNI, customer deposits, payroll liabilities, and accrued expenses side by side.
3. Add a second tab for AR aging, AP aging, unapplied cash, and settlement timing.
4. Compare the open-balance trends with the days-to-settlement measures.
5. Keep the workbook at the bucket and timing level instead of turning it into a full statement-reconciliation model.

## Wrap-Up Questions

- Which working-capital bucket moved the most across the modeled range?
- Which timing metric best explains the pressure?
- Where can cash tighten even while top-line activity remains strong?
- Which liability bucket is easiest to miss if you only focus on AR, inventory, and AP?
- Which bucket should management investigate first?

## Next Steps

- Use [Commercial and Working Capital](../reports/commercial-and-working-capital.md) when you want the report-level interpretation after the bridge is clear.
- Use [Financial Analytics](../financial.md) for the broader financial query set behind this case.
- Use [Financial Statement Bridge Case](financial-statement-bridge-case.md) when you want to move from working-capital balances into full statement and close-cycle interpretation.
