---
title: O2C Trace Case
description: Inquiry-led walkthrough for tracing a customer order from order entry through shipment, billing, settlement, and exception follow-up.
sidebar_label: O2C Trace Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# O2C Trace Case

## Business Scenario

Charles River Home Furnishings receives an order from a regional interior-design firm furnishing a small hospitality renovation in the Boston area. The customer wants finished goods on a tight schedule, but inventory is not evenly available across every line. Sales can confirm the order immediately, yet warehouse fulfillment, billing, and cash settlement may unfold over different dates.

This case goes beyond a simple "order paid in full" story. Shipment drives inventory relief and COGS. Invoice drives revenue, receivables, and sales-commission expense. Cash receipt records money arriving. `CashReceiptApplication` determines when open AR is actually settled. If part of the order is later returned, the trace branches again into returns, credits, and commission clawbacks.

Your job is to explain that chain as one connected business story and one connected data trail.

## The Problem to Solve

You need to prove that one O2C transaction can be traced cleanly from customer order to shipment, invoice, cash settlement, and possible exception follow-up. Confirm the document sequence. Confirm that each accounting entry follows the correct operational event.

## What You Need to Develop

- A clear trace narrative from order entry to shipment to invoice to cash application.
- A short explanation of which events are operational and which events create ledger impact.
- A timing analysis showing where backorders, invoice lag, and open AR can arise.
- An exception follow-up showing how returns and credits change the original trace.

## Before You Start

- Main tables: `SalesOrder`, `SalesOrderLine`, `Shipment`, `ShipmentLine`, `SalesInvoice`, `SalesInvoiceLine`, `CashReceipt`, `CashReceiptApplication`, `SalesReturn`, `SalesReturnLine`, `CreditMemo`, `SalesCommissionAccrual`, `SalesCommissionAdjustment`, `SalesCommissionPayment`, `GLEntry`
- Related process page: [Order-to-Cash Process](../../processes/o2c.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [GLEntry Posting Reference](../../reference/posting.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case uses both starter query packs and two case-support SQL files built specifically for document tracing.

## Step-by-Step Walkthrough

### Step 1. Define the order population and document chain

Start by identifying the order population and asking a basic control question: do the expected downstream documents appear after the order is entered?

**What we are trying to achieve**

Establish the order-level trace and see where the chain stays complete, remains partial, or branches into return activity.

If you do not define the document population first, later timing and accounting observations will be hard to interpret. This step gives you the control view of the normal O2C chain.

**Suggested query**

<QueryReference
  queryKey="audit/01_o2c_document_chain_completeness.sql"
  helperText="Use this first to identify complete, partial, and exception-style order traces."
/>

**What this query does**

It summarizes each sales order and compares ordered quantity with shipped quantity, billed quantity, cash collected, and any credited activity.

**How it works**

The query builds separate shipment, billing, cash, and return aggregates, then joins them back to `SalesOrder` and `SalesOrderLine`. That keeps incomplete orders visible instead of hiding them inside inner joins.

**What to look for in the result**

- orders with no shipment yet
- orders shipped but not billed
- billed orders that are not fully settled
- orders that later moved into the return or credit branch

### Step 2. Understand fulfillment lag and backorder pressure

Once you know which orders remain partial, move to the operational question: how much of the gap comes from fulfillment timing rather than accounting problems?

**What we are trying to achieve**

Measure where shipment timing breaks from the original order promise and where backorder quantity remains open.

Students often jump directly from order to invoice. That misses the operational reality that customer service timing and accounting timing separate at shipment.

**Suggested query**

<QueryReference
  queryKey="managerial/25_backorder_fill_rate_and_shipment_lag.sql"
  helperText="Use this to connect order demand, shipment lag, and remaining backorder quantity."
/>

**What this query does**

It groups order lines by order month and item group, then compares ordered quantity with shipped quantity and measures average days to first shipment.

**How it works**

The query aggregates `ShipmentLine` by `SalesOrderLineID`, then joins that result back to `SalesOrderLine` and `SalesOrder`. This lets partially fulfilled lines remain visible and quantifies remaining backorder quantity.

**What to look for in the result**

- item groups with lower fill rates
- months where backordered quantity stays high
- the average delay between order entry and first shipment
- evidence that shipment timing is the first place the customer experience can diverge from the original order

### Step 3. Connect shipment and invoice events to accounting impact

Now move from document completeness to posting logic. At this point, the goal is to show which event relieves inventory and which event creates revenue and receivables.

**What we are trying to achieve**

Trace one order line through shipment and invoice detail, then tie those source rows back to posted `GLEntry` activity, including the commission accrual triggered by invoice-line revenue.

This is where cutoff, occurrence, and revenue-recognition discussions become concrete. You can only answer those questions reliably if the source documents and ledger rows are connected.

**Suggested query**

<QueryReference
  queryKey="cases/01_o2c_line_trace_order_shipment_invoice.sql"
  helperText="Use this to inspect one order line across order entry, shipment, and invoice detail."
/>

<QueryReference
  queryKey="cases/02_o2c_source_to_gl_trace.sql"
  helperText="Use this follow-through query when you want to connect shipment and invoice source lines back to posted GL rows."
/>

**What this query does**

The first query lays out the document trail at the line level. The second takes shipment, invoice, and commission source records and joins them to `GLEntry` and `Account`.

**How it works**

The line-trace query starts at `SalesOrderLine`, then left joins `ShipmentLine` and `SalesInvoiceLine` so open, shipped, and billed lines all remain visible. The source-to-GL query filters `GLEntry` by `SourceDocumentType` and separates shipment-line postings, invoice header and invoice-line postings, sales-commission accruals, credit-memo clawbacks, and commission payments.

**What to look for in the result**

- shipment rows should carry inventory and COGS impact
- invoice rows should carry revenue and AR impact, even when AR is recorded at the invoice header level
- commission accrual rows should debit `6290` and credit `2034` from invoice-line revenue only
- posting dates should line up with the event that actually created the accounting entry
- lines with no downstream record should still remain visible in the trace

### Step 4. Separate cash receipt from invoice settlement

After billing, shift to the receivables question. Cash can arrive on one date. AR settles only when applications are recorded against invoices.

**What we are trying to achieve**

Separate the cash event from the settlement event and identify invoices or receipts that remain open after money has already arrived.

This is one of the most common student misunderstandings in O2C. `CashReceipt` records cash arrival. `CashReceiptApplication` records which invoice balance was actually cleared.

**Suggested query**

<QueryReference
  queryKey="financial/15_customer_deposits_and_unapplied_cash_aging.sql"
  helperText="Use this first to identify receipts that are still fully or partly unapplied."
/>

<QueryReference
  queryKey="financial/02_ar_aging_open_invoices.sql"
  helperText="Use this follow-up to see which invoices remain open after cash and credits are considered."
/>

**What this query does**

The first query ages receipts that remain unapplied or only partly applied. The second query ages invoices that remain open after cash applications and credit memos are allocated.

**How it works**

The unapplied-cash query aggregates `CashReceiptApplication` by receipt and compares receipt amount with applied amount. The AR aging query aggregates applications by invoice, allocates credit memo impact, and then computes remaining open balance and aging bucket.

**What to look for in the result**

- receipts where cash has arrived but no invoice has been settled yet
- invoices that remain open even though the customer has sent money
- timing gaps between receipt date and first application date
- why serious settlement analysis must use `CashReceiptApplication` instead of `CashReceipt.SalesInvoiceID`

### Step 5. Extend the trace into exception follow-up

Finish by looking at what changes when the normal path breaks. Returns, credits, and backorders change the meaning of the original sale.

**What we are trying to achieve**

Explain how exception activity changes the meaning of a trace that originally looked complete.

A student who can only explain the normal path has not finished the case. Audit, AR, and customer-service interpretation all depend on understanding what happened after the initial shipment and invoice.

**Suggested query**

<QueryReference
  queryKey="audit/07_backorder_and_return_review.sql"
  helperText="Use this to isolate orders that remained backordered, later returned, or were credited."
/>

**What this query does**

It highlights sales orders where shipment quantity stayed below order quantity or where return and credit activity appeared after the original billing path.

**How it works**

The query aggregates shipments and billings by order line, then overlays return and credit totals at the order level. That makes backorder pressure and later return activity visible in one result.

**What to look for in the result**

- orders where requested quantity was never fully shipped
- orders that shipped and billed normally but later moved into return activity
- credited amounts that change the final economic result of the original sale
- how customer-service interpretation and financial interpretation can diverge

## Required Student Output

Submit a short case memo or notebook note with these four artifacts:

- Evidence summary: identify the key result rows, metrics, timing patterns, or exception families that changed your diagnosis.
- Accounting or business interpretation: explain what the evidence means for the process, accounting treatment, managerial decision, or control risk.
- Database explanation: name the source tables, row grain, join keys, or trace path that make the evidence defensible.
- Management or audit conclusion: state which driver, document path, or exception family should be followed up first and why.

## Optional Excel Follow-Through

1. Filter `SalesOrder` to one customer, one month, or one order number range.
2. Use `SalesOrderLineID` to trace into `ShipmentLine` and then `SalesInvoiceLine`.
3. Use `ShipmentLineID` and `SalesInvoiceLineID` to compare operational dates with posted `GLEntry` timing, including sales-commission accruals tied to invoice lines.
4. Use `SalesInvoiceID` to trace into `CashReceiptApplication` and open-invoice analysis.
5. If the order later changed, extend the trace into `SalesReturn`, `SalesReturnLine`, and `CreditMemo`.

## Wrap-Up Questions

- Accounting/process: Which event creates revenue, which event relieves inventory, which event accrues commission expense, and where can timing diverge without an error?
- Database/source evidence: Which order, shipment, invoice, commission, cash-application, return, or GL key proves the trace?
- Analytics judgment: Which part of the order-to-cash chain carries the greatest cutoff or settlement risk?
- Escalation/next step: How should a later return or credit change the conclusion about the original sale?

## Next Steps

- Use [Order-to-Cash Process](../../processes/o2c.md) for the full business and data walkthrough of the normal and exception path.
- Use [Schema Reference](../../reference/schema.md) when you need table-level join support while working through the case.
- Use [GLEntry Posting Reference](../../reference/posting.md) when you want the exact shipment, invoice, cash, and credit posting rules.
- Use [Working Capital and Cash Conversion Case](working-capital-and-cash-conversion-case.md) when you want to extend this trace into broader AR and cash timing analysis.
