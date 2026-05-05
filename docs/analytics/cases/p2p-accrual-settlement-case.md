---
title: P2P Accrual Settlement Case
description: Inquiry-led walkthrough for tracing receipt-matched purchasing, accrual-linked service settlement, and AP timing in the P2P cycle.
sidebar_label: P2P Accrual Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# P2P Accrual Settlement Case

## Business Scenario

Month-end close is approaching at Charles River Home Furnishings. Some recent purchases followed the normal materials path: requisition, purchase order, goods receipt, supplier invoice, and later payment. At the same time, finance recorded accrued expenses for insurance, software, and professional services that had been consumed before the supplier invoices arrived.

That creates a real control question for AP and finance. Some `PurchaseInvoiceLine` rows match `GoodsReceiptLineID`, which means the invoice is clearing the normal receipt-based path. Other lines point to `AccrualJournalEntryID`, which means the invoice is settling a finance-booked estimate with no goods receipt behind it.

Your job is to explain both paths as one connected P2P story, then show why the difference matters for AP aging, liability completeness, expense cutoff, and audit interpretation.

## The Problem to Solve

You need to prove that supplier activity can be traced cleanly through the normal P2P path and the accrued-service settlement path. Confirm the support path. Confirm that the accounting effect matches the kind of purchase being settled.

## What You Need to Develop

- A clear trace of the normal receipt-matched P2P path from requisition through PO, receipt, invoice, and payment.
- A clear trace of the accrual-linked service-settlement path from month-end journal estimate to supplier invoice and disbursement.
- A short explanation of which events are operational and which events create ledger impact.
- A timing analysis showing how accrual date, invoice date, and payment date can diverge.
- An exception follow-up showing what makes an accrued-service settlement unusual enough for audit review.

## Before You Start

- Main tables: `PurchaseRequisition`, `PurchaseOrder`, `PurchaseOrderLine`, `GoodsReceipt`, `GoodsReceiptLine`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment`, `JournalEntry`, `GLEntry`
- Related process pages: [Procure-to-Pay Process](../../processes/p2p.md), [Manual Journals and Close Cycle](../../processes/manual-journals-and-close.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [GLEntry Posting Reference](../../reference/posting.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case uses both starter query packs and two case-support SQL files built specifically to separate receipt-matched AP from accrual-linked AP settlement.

## Step-by-Step Walkthrough

### Step 1. Define the normal P2P document chain

Start with the normal path. Before you analyze accrual-linked exceptions, you need a baseline view of how requisitions, purchase orders, receipts, invoices, and payments connect when P2P works as expected.

**What we are trying to achieve**

Establish the requisition-level document chain and see where the normal P2P path stays complete, remains partial, or stalls before payment.

If you skip the normal path, it becomes too easy to label every missing receipt as a control failure. This step gives you the control baseline for normal purchased materials and inventory activity.

**Suggested query**

<QueryReference
  queryKey="audit/02_p2p_document_chain_completeness.sql"
  helperText="Use this first to establish which requisitions progressed through PO, receipt, invoice, and payment."
/>

**What this query does**

It summarizes each purchase requisition and compares requested demand with downstream PO lines, receipt activity, supplier invoicing, and payment.

**How it works**

The query builds separate aggregates for PO lines, receipts, invoices, and payments, then joins them back to `PurchaseRequisition`. That keeps incomplete requisitions visible instead of hiding them inside inner joins.

**What to look for in the result**

- requisitions with no PO line yet
- requisitions ordered but not received
- received requisitions that have not been invoiced
- invoiced requisitions that remain unpaid or only partly paid

### Step 2. Separate receipt-matched invoice lines from accrual-linked service lines

Once the normal chain is visible, move to the line-level distinction that makes this case worth doing. Supplier invoice lines follow two different support paths.

**What we are trying to achieve**

Show how `PurchaseInvoiceLine.GoodsReceiptLineID` and `PurchaseInvoiceLine.AccrualJournalEntryID` create two different invoice-settlement paths inside the same AP system.

Students often assume that every supplier invoice must point to a receipt. In this dataset, some service invoices intentionally clear finance-booked accruals. That pattern can be valid.

**Suggested query**

<QueryReference
  queryKey="cases/03_p2p_invoice_line_trace_receipt_vs_accrual.sql"
  helperText="Use this to classify invoice lines as receipt matched, accrual settled, or follow-up items that need more review."
/>

**What this query does**

It lays out one row per `PurchaseInvoiceLine` and shows the supplier invoice line alongside any linked requisition, PO line, receipt line, or accrual journal.

**How it works**

The query starts at `PurchaseInvoiceLine`, then left joins into `PurchaseOrderLine`, `PurchaseRequisition`, `GoodsReceiptLine`, and `JournalEntry`. A `CASE` expression uses `GoodsReceiptLineID` and `AccrualJournalEntryID` to label the matched basis.

**What to look for in the result**

- lines labeled `Receipt matched`
- lines labeled `Accrual settled`
- invoice lines with neither receipt linkage nor accrual linkage
- how requisition and PO context stays visible on the materials path and drops away on the service-accrual path

### Step 3. Explain the accounting bridge from accrual estimate to supplier invoice

Now move from document traceability into posting logic. At this point, the goal is to show how a finance-booked accrual becomes an AP-clearing supplier invoice rather than a receipt-matched inventory invoice.

**What we are trying to achieve**

Connect the original accrual estimate to the later supplier invoice and the related `GLEntry` activity.

This is the core accounting distinction in the case. Receipt-based invoicing clears `2020` GRNI. Accrual-linked service invoicing clears `2040` accrued expenses up to the estimate, books any excess to expense, and leaves any shortfall to be reversed through a linked accrual adjustment.

**Suggested query**

<QueryReference
  queryKey="financial/12_accrued_expense_rollforward.sql"
  helperText="Use this first to see the month-level roll-forward of accrual creation, invoice clearing, and adjustment activity."
/>

<QueryReference
  queryKey="cases/04_p2p_accrual_journal_invoice_payment_gl_trace.sql"
  helperText="Use this follow-through query to connect one accrual-linked invoice line to the accrual journal, invoice clearing entries, and payment postings."
/>

**What this query does**

The first query summarizes accrued-expense activity by period and expense family. The second drills into one accrual-linked invoice line and shows the accrual amount, invoice amount, AP posting, and payment-clearing effect.

**How it works**

The roll-forward query groups `JournalEntry` and `GLEntry` activity at the month-and-account level. The trace query starts at `PurchaseInvoiceLine.AccrualJournalEntryID`, then joins to `JournalEntry`, `PurchaseInvoice`, `DisbursementPayment`, `GLEntry`, and `Account` to summarize the accounts hit by the invoice-clearing and payment steps.

**What to look for in the result**

- accrual journals that debit expense and credit `2040`
- supplier invoices that debit `2040` up to the estimate
- invoice amounts above the estimate that push additional expense
- invoice amounts below the estimate that lead to a later linked accrual adjustment
- AP created at invoice approval and cleared later by disbursement

### Step 4. Measure invoice and payment timing, then identify what remains open

Once the accounting bridge is clear, shift to timing. Accrual date, invoice date, and payment date answer different questions and often fall in different periods.

**What we are trying to achieve**

Measure lag from accrual date to invoice date to payment date and identify which supplier invoices still remain open.

This is where AP aging and expense-cutoff questions become concrete. A liability can be estimated at month-end, invoiced later, and paid later still.

**Suggested query**

<QueryReference
  queryKey="financial/13_accrued_vs_invoiced_vs_paid_timing.sql"
  helperText="Use this first to compare accrual date, invoice date, payment timing, and over-under accrual differences."
/>

<QueryReference
  queryKey="financial/03_ap_aging_open_invoices.sql"
  helperText="Use this follow-up to see which supplier invoices remain open after payment activity is considered."
/>

**What this query does**

The timing query shows one row per accrual-linked service invoice with days-to-invoice, days-to-payment, and over-under-accrual amounts. The AP aging query shows which supplier invoices still carry open payable balances.

**How it works**

The timing query joins `PurchaseInvoiceLine` back to the accrual journal and payment summary. The AP aging query aggregates payments by invoice and compares cash paid with invoice grand total to calculate open amount and aging bucket.

**What to look for in the result**

- invoices that arrive materially after the accrual date
- invoices that remain unpaid even after the accrual was cleared operationally
- open AP balances tied to service invoices versus normal receipt-based invoices
- why invoice timing and payment timing answer different analytical questions

### Step 5. Extend the case into audit follow-up

Finish by asking which accrual-linked service settlements are merely different and which ones are unusual enough to justify audit attention.

**What we are trying to achieve**

Explain what makes an accrued-service settlement look valid, suspicious, or incomplete.

You have not finished the case until you explain whether the timing, amount, and settlement behavior still make sense after the invoice appears.

**Suggested query**

<QueryReference
  queryKey="audit/23_accrued_service_settlement_exception_review.sql"
  helperText="Use this to isolate dated-before-accrual, amount-difference, and long-unpaid accrued-service invoices."
/>

**What this query does**

It highlights accrual-linked supplier invoice lines with amount mismatches, invoice dates that precede the linked accrual, or invoices that remain unpaid beyond the review window.

**How it works**

The query starts with accrual headers, joins to `PurchaseInvoiceLine` where `AccrualJournalEntryID` is populated, then overlays supplier, item, and payment timing information to create a review-oriented result set.

**What to look for in the result**

- invoices dated before the linked accrual
- invoice amounts that differ meaningfully from the estimate
- accrued-service invoices that remain unpaid well after invoice date
- whether the exception still has a reasonable explanation or needs deeper follow-up

## Required Student Output

Submit a short case memo or notebook note with these four artifacts:

- Evidence summary: identify the key result rows, metrics, timing patterns, or exception families that changed your diagnosis.
- Accounting or business interpretation: explain what the evidence means for the process, accounting treatment, managerial decision, or control risk.
- Database explanation: name the source tables, row grain, join keys, or trace path that make the evidence defensible.
- Management or audit conclusion: state which driver, document path, or exception family should be followed up first and why.

## Optional Excel Follow-Through

1. Filter `PurchaseRequisition` to one month, cost center, or item group to define the normal purchasing population.
2. Use `RequisitionID` to trace into `PurchaseOrderLine`, then into `GoodsReceiptLine`.
3. Use `PurchaseInvoiceLine` to separate rows with `GoodsReceiptLineID` from rows with `AccrualJournalEntryID`.
4. Use `AccrualJournalEntryID` to tie service-settlement invoice lines back to `JournalEntry`.
5. Use `PurchaseInvoiceID` to trace into `DisbursementPayment` and open-AP analysis.

## Wrap-Up Questions

- Accounting/process: Which event creates AP, and which event only estimates a liability before AP exists?
- Database/source evidence: Which receipt, invoice-line, accrual-journal, payment, or GL key distinguishes the settlement path?
- Analytics judgment: When is a missing goods receipt valid accrual settlement evidence rather than a process break?
- Escalation/next step: What timing or amount pattern would make an accrued-service settlement worth audit follow-up?

## Next Steps

- Use [Procure-to-Pay Process](../../processes/p2p.md) for the full business and data walkthrough of the normal receipt-matched path and the accrued-service distinction.
- Use [Manual Journals and Close Cycle](../../processes/manual-journals-and-close.md) when you want the finance-controlled side of accruals, adjustments, and boundary entries.
- Use [Schema Reference](../../reference/schema.md) when you need table-level join support while working through the case.
- Use [GLEntry Posting Reference](../../reference/posting.md) when you want the exact receipt, invoice, accrual, and disbursement posting rules.
- Use [Working Capital and Cash Conversion Case](working-capital-and-cash-conversion-case.md) when you want to extend this analysis into broader AP timing and working-capital discussion.
