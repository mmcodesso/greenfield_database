---
title: Financial Statement Bridge Case
description: Inquiry-led walkthrough for tying posted ledger activity into the financial statements and year-end close.
sidebar_label: Statement Bridge Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# Financial Statement Bridge Case

## Business Scenario

The finance team needs to explain how operating activity, control accounts, finance journals, and year-end close produce the reported statements. Process pages already explain where transactions begin. This case starts later. It asks whether the posted ledger ties cleanly into the trial balance, whether major control accounts reconcile to source activity, and whether annual net income closes into retained earnings the way it should.

Management and audit both care about the same question. If the statement bridge breaks, where does it break first? A clean answer must separate operating history from finance presentation logic. It must also show how a statement-level variance can be narrowed into source-level evidence instead of staying trapped inside summary totals.

Your job is to build that bridge from the ledger outward, then follow one variance path all the way into revenue cutoff detail.

## The Problem to Solve

You need to prove how posted operational and finance-controlled activity builds the trial balance, which control accounts can be reconciled from source activity, how year-end close changes presentation without changing operating history, how annual net income ties into retained earnings, and how a statement-level variance can be narrowed into annual net-revenue and cutoff evidence.

## What You Need to Develop

- A statement-level bridge from ledger activity into reported balances.
- A control-account explanation grounded in operational source documents.
- A clear separation of recurring or manual journals from close entries.
- An annual net-income to retained-earnings explanation.
- One drill-down path from statement variance into revenue cutoff evidence.

## Before You Start

- Main tables: `GLEntry`, `Account`, `JournalEntry`, `SalesInvoice`, `SalesInvoiceLine`, `CreditMemo`, `CreditMemoLine`, `PurchaseInvoice`, `DisbursementPayment`, `GoodsReceiptLine`, `ShipmentLine`, `PayrollRegister`, `WorkOrderClose`
- Related guides: [Financial Analytics](../financial.md), [Executive Overview](../reports/executive-overview.md)
- Related process pages: [Manual Journals and Close Cycle](../../processes/manual-journals-and-close.md), [Order-to-Cash Process](../../processes/o2c.md), [Procure-to-Pay Process](../../processes/p2p.md), [Manufacturing Process](../../processes/manufacturing.md), [Payroll Process](../../processes/payroll.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [GLEntry Posting Reference](../../reference/posting.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case focuses on statement tie, control accounts, and close. Use the working-capital case when you need settlement timing and current-liability pressure.

## Step-by-Step Walkthrough

### Step 1. Define the statement scaffold from the trial balance

Start with the posted ledger structure. Before you reconcile anything, you need to see the period-by-period account scaffold that supports the statements.

**What we are trying to achieve**

Establish the posted trial-balance structure by fiscal period, account type, and account subtype.

**Why this matters**

This step gives you the statement frame. Without it, later reconciliation and close analysis will not have a stable ledger baseline.

**Suggested query**

<QueryReference
  queryKey="financial/04_trial_balance_by_period.sql"
  helperText="Use this first to build the ledger-level statement scaffold by fiscal period and account classification."
/>

**What this query does**

It summarizes posted `GLEntry` activity by fiscal year, fiscal period, and non-header account.

**How it works**

The query joins `GLEntry` to `Account`, groups by period and account attributes, and returns debit, credit, and net debit-less-credit balances for each active account.

**What to look for in the result**

- the main asset, liability, equity, revenue, and expense categories
- the accounts carrying the largest balances by period
- whether the ledger structure already suggests where major statement movement sits
- which control-account families deserve deeper reconciliation

### Step 2. Reconcile key control accounts back to operational source activity

Once the trial balance is clear, test whether the major control accounts can be supported by source logic.

**What we are trying to achieve**

Prove that major control-account balances can be tied back to expected subledger and operational activity.

**Why this matters**

Statement trust starts with control-account trust. If a control account does not reconcile, the statement bridge is already under pressure before close logic enters the discussion.

**Suggested query**

<QueryReference
  queryKey="financial/06_control_account_reconciliation.sql"
  helperText="Use this to compare key control-account balances with expected source-derived balances."
/>

**What this query does**

It compares expected source-driven balances with actual posted balances for major control areas such as AR, AP, GRNI, inventory, customer deposits, sales tax payable, and sales returns.

**How it works**

The query builds expected balances from operational tables, builds actual balances from non-`JournalEntry` GL rows, and then compares the two at the control-area level.

**What to look for in the result**

- control areas with the smallest and largest differences
- whether the mismatch sits in an operational account or a finance-controlled account
- which control area is easiest to support from process evidence
- where you would need process-specific follow-up from the process pages or posting reference

### Step 3. Separate recurring journals, finance-controlled activity, and close-cycle volume

Now move from control accounts to finance activity. The ledger carries both operating history and finance-controlled journals. They must be separated.

**What we are trying to achieve**

Show how finance-controlled journal activity differs from year-end close and how close entries affect retained earnings presentation.

**Why this matters**

Students often mix recurring journals with close entries. That makes it hard to explain why reported balances change while the underlying operating history stays the same.

**Suggested query**

<QueryReference
  queryKey="financial/05_journal_and_close_cycle_review.sql"
  helperText="Use this first to measure journal-entry volume by posting month and entry type."
/>

<QueryReference
  queryKey="financial/16_retained_earnings_and_close_entry_impact.sql"
  helperText="Use this follow-through query to separate pre-close P&L activity from retained-earnings close impact."
/>

**What this query does**

The first query summarizes journal-entry activity by entry type and month. The second separates raw P&L activity from year-end close impact on retained earnings.

**How it works**

The journal review reads `JournalEntry` directly and groups volume by posting month and `EntryType`. The retained-earnings query filters close-step journal logic through `GLEntry`, `Account`, and `JournalEntry` to compare pre-close net income, statement net income, and retained-earnings close impact.

**What to look for in the result**

- recurring journal families versus year-end close volume
- whether close activity is concentrated where expected
- whether pre-close income and retained-earnings close already appear aligned
- where finance presentation logic starts changing the statement view

### Step 4. Tie annual net income into retained earnings and test the close

This is the core statement-bridge step. You are now validating the annual close itself.

**What we are trying to achieve**

Prove that annual net income, close entries, retained earnings, and the post-close statement state line up correctly.

**Why this matters**

This is the decisive statement test. If annual net income does not tie into retained earnings or if P&L accounts leak after close, the financial-statement bridge is incomplete.

**Suggested query**

<QueryReference
  queryKey="financial/39_annual_income_to_equity_bridge.sql"
  helperText="Use this first to reconcile annual net income, retained-earnings close, and the annual balance-sheet residual."
/>

<QueryReference
  queryKey="financial/40_post_close_profit_and_loss_leakage_review.sql"
  helperText="Use this follow-through query to identify revenue, expense, or income-summary balances that remain after close."
/>

**What this query does**

The first query bridges annual income-statement net income into retained earnings and the year-end balance-sheet presentation. The second flags revenue, expense, or income-summary accounts that still carry a balance after close.

**How it works**

The income-to-equity bridge computes pre-close income, statement income, retained-earnings close amounts, and balance-sheet residual logic by closed fiscal year. The leakage review scans closed years for non-zero ending balances in P&L and income-summary accounts.

**What to look for in the result**

- whether annual net income ties into retained earnings cleanly
- whether the balance sheet still carries residual current-year earnings after close
- whether any P&L or income-summary accounts leak past close
- whether a problem looks like close-process logic or earlier posting logic

### Step 5. Drill from statement variance into annual net revenue and cutoff exceptions

Finish the case by taking one statement-level variance path into source-level evidence. Revenue is the cleanest drill-down path because the repo already provides a summary and trace pair.

**What we are trying to achieve**

Show how a statement-level variance can be narrowed from annual net-revenue mismatch into invoice-level cutoff evidence.

**Why this matters**

A statement bridge is only complete when it ends in source-level proof. Summary reconciliation alone does not show whether the problem sits in statement logic, posting logic, or source timing.

**Suggested query**

<QueryReference
  queryKey="financial/42_annual_net_revenue_bridge.sql"
  helperText="Use this first to reconcile operational net revenue, pre-close GL net revenue, and annual income-statement net revenue."
/>

<QueryReference
  queryKey="financial/43_invoice_revenue_cutoff_exception_summary.sql"
  helperText="Use this summary to isolate invoice-level revenue cutoff exceptions that affect annual reconciliation."
/>

<QueryReference
  queryKey="financial/44_invoice_revenue_cutoff_exception_trace.sql"
  helperText="Use this trace when you need line-level order, shipment, invoice, and revenue-GL evidence for the cutoff exceptions."
/>

**What this query does**

The first query reconciles annual net revenue from operational source documents into pre-close GL and the annual income statement. The second narrows the problem to invoice-level exceptions. The third traces those exceptions down to invoice lines and related operating-revenue GL rows.

**How it works**

The annual bridge compares invoice-line and credit-memo totals with pre-close revenue GL and the income-statement view. The cutoff summary identifies invoice headers where invoice year, shipment timing, or revenue GL fiscal year diverge. The trace query expands those exception invoices into detailed order, shipment, invoice-line, and GL evidence.

**What to look for in the result**

- whether operational net revenue ties to pre-close GL
- whether the remaining variance is summary-level or invoice-specific
- invoices whose revenue GL fiscal year differs from the invoice year
- whether the root cause is a seeded timing anomaly, a posting defect, or a broader statement-query issue

## Optional Excel Follow-Through

1. Build a period-by-period trial-balance pivot by `FiscalYear`, `FiscalPeriod`, `AccountType`, and `AccountSubType`.
2. Add a lookup from `GLEntry` into `JournalEntry[EntryType]` where the source row is journal-driven.
3. Build one annual bridge that compares pre-close net income, retained-earnings close, and post-close leakage.
4. Add one narrow revenue drill-down tab for annual net revenue and cutoff exceptions.
5. Keep the workbook focused on the statement bridge instead of turning it into a broad process workbook.

## Wrap-Up Questions

- Which control account is easiest to reconcile and why?
- Where does the close process change presentation without changing operating history?
- Which variance belongs to statement logic and which variance belongs to source-document logic?
- Why is retained earnings the decisive tie point for annual close validation?
- When should you stop at the summary query and when should you open the line-level cutoff trace?

## Where to Go Next

- Use [Manual Journals and Close Cycle](../../processes/manual-journals-and-close.md) when you want the process-level view of recurring journals, accrual settlement, and boundary entries.
- Use [Executive Overview](../reports/executive-overview.md) when you want the report-level interpretation after the statement bridge is clear.
- Use [Working Capital and Cash Conversion Case](working-capital-and-cash-conversion-case.md) when you want settlement timing and current-liability pressure instead of statement tie-out.
