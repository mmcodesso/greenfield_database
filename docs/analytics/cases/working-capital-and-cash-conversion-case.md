---
title: Working Capital and Cash Conversion Case
description: Inquiry-led walkthrough for diagnosing cross-process cash pressure through working-capital balances, settlement timing, and liability follow-up.
sidebar_label: Working Capital Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# Working Capital and Cash Conversion Case

## Business Scenario

The finance team is reviewing why cash feels tighter than expected even though sales and operations still look healthy on the surface. Management does not need another generic balance-sheet recap. It needs a cross-process explanation of where working-capital pressure is building and which timing pattern deserves action first.

That pressure does not come from one document chain. Customer receipts can arrive before AR settles. Goods can be received before suppliers are paid. Sales commissions can be accrued from invoice-line revenue before the monthly rep settlement clears the liability. Payroll liabilities can build before remittances leave the bank. Accrued expenses can rise before service invoices appear. Finance needs one working-capital story that connects those separate timing systems back to cash pressure.

Your job is to build that story from the control accounts first, then narrow it into the customer, supplier, payroll, and accrual timing patterns that actually explain the pressure.

## The Problem to Solve

You need to prove which working-capital buckets moved the most by month, which timing patterns sit behind those balances, and how AR, AP, receipt timing, sales-commission payable, payroll liabilities, customer deposits, and accrued expenses change cash pressure. You also need to decide which driver deserves management follow-up first instead of treating every variance as equally important.

## What You Need to Develop

- A month-by-month working-capital pressure map built from the control accounts.
- A customer-side explanation that separates open AR from cash already received but not yet applied.
- A supplier-side explanation that separates open AP from receipt-to-payment timing and GRNI behavior.
- A liability-layer explanation for sales commissions, payroll, and accrued expenses that sits alongside the classic cash-conversion buckets.
- A short management-facing conclusion on which driver deserves follow-up first.

## Before You Start

- Main tables: `GLEntry`, `Account`, `SalesInvoice`, `CashReceipt`, `CashReceiptApplication`, `SalesCommissionAccrual`, `SalesCommissionAdjustment`, `SalesCommissionPayment`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment`, `GoodsReceipt`, `PayrollRegister`, `PayrollPayment`, `PayrollLiabilityRemittance`, `JournalEntry`
- Related guides: [Financial Queries](../financial.md), [Commercial and Working Capital](../reports/commercial-and-working-capital.md)
- Related process pages: [Order-to-Cash Process](../../processes/o2c.md), [Procure-to-Pay Process](../../processes/p2p.md), [Payroll Process](../../processes/payroll.md), [Manual Journals and Close Cycle](../../processes/manual-journals-and-close.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [GLEntry Posting Reference](../../reference/posting.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case does not trace one document chain. It synthesizes customer, supplier, payroll, and finance-controlled timing into one cash-pressure diagnosis.

## Step-by-Step Walkthrough

### Step 1. Define the monthly pressure map from the control accounts

Start from the monthly bridge. Before you debate timing, you need to know which working-capital buckets actually moved and whether the pressure sits on the asset side, the liability side, or both.

**What we are trying to achieve**

Establish the month-by-month movement in AR, inventory and WIP, AP, GRNI, customer deposits, sales commission payable, accrued expenses, and payroll liabilities.

**Why this step changes the diagnosis**

This step gives you the pressure map. Without it, later timing analysis will float free of the balances management is actually watching.

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
- months where deposits, sales commission payable, payroll liabilities, or accrued expenses changed the story materially

### Step 2. Separate customer settlement timing from customer cash arrival

Once the bridge shows AR or deposit pressure, move to the customer-side timing question. Cash can arrive on one date while invoice settlement remains incomplete on another.

**What we are trying to achieve**

Distinguish open AR from customer cash that has already arrived but has not yet been fully applied.

**Why this step changes the diagnosis**

Students often collapse receivables and customer cash into one idea. That shortcut hides a real working-capital issue when receipts exist but invoice settlement still lags.

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

### Step 3. Explain supplier-side timing through AP, GRNI, and payment lag

Now move to the supplier side. Working-capital pressure changes when invoices remain open, when goods are received well before payment, or when GRNI timing pulls away from AP timing.

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

### Step 4. Bring commission, payroll, and accrued liabilities into the same cash-pressure story

At this point you know the commercial timing pattern. Now add the liability layers that sit outside the classic AR-inventory-AP triangle but still change the cash story materially.

**What we are trying to achieve**

Show how sales commissions, payroll liabilities, and accrued expenses accumulate before cash leaves through rep settlement, remittances, supplier invoicing, and payment.

**Why this step changes the diagnosis**

A narrow AR-inventory-AP view can miss a real source of current-liability pressure. Sales commission, payroll, and accrual timing can keep cash tight even when commercial activity looks stable.

**Suggested query**

<QueryReference
  queryKey="financial/58_sales_commission_payable_rollforward.sql"
  helperText="Use this first to measure commission accruals, credit-memo clawbacks, payments, and the ending payable."
/>

<QueryReference
  queryKey="financial/09_payroll_liability_rollforward.sql"
  helperText="Use this next to measure payroll-liability movement by month and liability account."
/>

<QueryReference
  queryKey="financial/11_payroll_cash_payments_and_remittances.sql"
  helperText="Use this follow-through query to compare net-pay cash with payroll-liability remittance cash."
/>

<QueryReference
  queryKey="financial/12_accrued_expense_rollforward.sql"
  helperText="Use this to measure accrual build, invoice clearing, adjustments, and residual liability."
/>

<QueryReference
  queryKey="financial/13_accrued_vs_invoiced_vs_paid_timing.sql"
  helperText="Use this follow-through query to compare accrual date, invoice date, and first payment timing."
/>

**What this query does**

The commission query shows how invoice-line commission expense builds `2034`, how credit memos reduce the payable, and how monthly rep payments clear it. The payroll queries show how payroll liabilities build and then clear through employee cash and remittance cash. The accrual queries show how accrued expenses build before supplier invoices arrive and how quickly those estimates move toward invoice and payment settlement.

**How it works**

The commission rollforward groups `GLEntry` for `2034` and separates accrual credits from clawback and payment debits. The payroll rollforward groups `GLEntry` by payroll-liability account and computes monthly net increase plus running ending balance. The payroll cash-outflow query combines `PayrollPayment` and `PayrollLiabilityRemittance` by fiscal period and separates the cash streams into net pay, employee tax, employer tax, and benefits. The accrual rollforward starts from `JournalEntry` rows tagged as accruals, joins them to `GLEntry`, and compares accrued amount with later invoice clearing and any accrual adjustment activity. The accrued-timing query joins accrual-linked invoice lines back to the originating journal and related payment summary so lag from estimate to invoice to payment stays visible.

**What to look for in the result**

- liability accounts, commission reps, or expense families that build faster than they clear
- months where remittance timing or first-payment timing lags the liability build materially
- whether commission, payroll, and accrual liabilities reinforce or offset the commercial timing story
- which liability layer looks structural versus limited to a narrower period or expense family

### Step 5. Prioritize the driver that deserves management follow-up first

Finish by forcing prioritization. Once the timing layers are visible, compare them to plan and decide which driver deserves the first management follow-up instead of ending with a long list of possible explanations.

**What we are trying to achieve**

Compare actual working-capital and cash pressure to plan, then decide which follow-up path should open first.

**Why this step changes the diagnosis**

This is the point where analysis becomes management judgment. A good working-capital answer does not stop at description. It identifies the variance that matters most and routes the next review into the right follow-up population.

**Suggested query**

<QueryReference
  queryKey="financial/53_budget_vs_actual_working_capital_and_cash_bridge.sql"
  helperText="Use this to compare budgeted and actual working-capital balances and ending cash before you choose the first follow-up path."
/>

<QueryReference
  queryKey="audit/24_customer_deposits_and_unapplied_cash_exception_review.sql"
  helperText="Use this if the customer-side story still hinges on unapplied cash, older deposits, or unusual receipt-application timing."
/>

<QueryReference
  queryKey="audit/13_over_under_accrual_review.sql"
  helperText="Use this if the accrual story still hinges on estimate accuracy, missing linked invoices, or residual accrued balances."
/>

**What this query does**

The budget bridge compares budgeted and actual ending balances for the main working-capital and cash metrics. The deposit exception review isolates receipts that remain unapplied or show unusual application timing. The accrual review isolates accrual outcomes that differ materially from the original estimate or remain uncleared.

**How it works**

The budget bridge combines `BudgetLine` with running actual balances from `GLEntry` and `Account` so planned and actual month-end positions can be compared side by side. The deposit review aggregates `CashReceiptApplication` by receipt and compares applied amount with receipt amount and age. The accrual review joins accrual journals to linked supplier invoices and later adjustment activity so estimate accuracy and residual liability can be tested directly.

**What to look for in the result**

- the metric with the largest adverse variance to plan
- whether that variance is driven mainly by customer timing, supplier timing, payroll liabilities, or accrued expenses
- whether unapplied cash or deposit aging needs the next follow-up step
- whether accrual estimate accuracy or stale accrued balances deserve the first escalation

## Required Student Output

Submit a short case memo or notebook note with these four artifacts:

- Evidence summary: identify the key result rows, metrics, timing patterns, or exception families that changed your diagnosis.
- Accounting or business interpretation: explain what the evidence means for the process, accounting treatment, managerial decision, or control risk.
- Database explanation: name the source tables, row grain, join keys, or trace path that make the evidence defensible.
- Management or audit conclusion: state which driver, document path, or exception family should be followed up first and why.

## Optional Excel Follow-Through

1. Build a month-by-month bridge tab from `GLEntry` and `Account` for the main working-capital buckets.
2. Add a customer-timing tab for AR aging, unapplied cash, and days to first application.
3. Add a supplier-timing tab for AP aging plus invoice-to-payment and receipt-to-payment timing.
4. Add a liability-layer tab for commission payable, payroll liabilities, remittances, accrual build, and accrual-to-invoice-to-payment timing.
5. Finish with a plan-versus-actual summary tab that forces one primary follow-up choice instead of a full statement-reconciliation model.

## Wrap-Up Questions

- Accounting/process: Which working-capital bucket or liability layer best explains cash pressure across the modeled range?
- Database/source evidence: Which customer, supplier, commission, payroll, accrual, budget, or GL grain supports that pressure map?
- Analytics judgment: Where can cash tighten even while top-line activity remains strong?
- Escalation/next step: Which follow-up path should open first: unapplied customer cash, supplier timing, sales-commission payable, payroll liabilities, or accrual accuracy?

## Next Steps

- Use [Commercial and Working Capital](../reports/commercial-and-working-capital.md) when you want the report-level interpretation after the bridge is clear.
- Use [Financial Queries](../financial.md) for the broader financial query set behind this case.
- Use [Financial Statement Bridge Case](financial-statement-bridge-case.md) when you want to move from working-capital balances into full statement and close-cycle interpretation.
