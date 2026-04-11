---
title: O2C Trace Case
description: Guided walkthrough for tracing a customer sale from order through settlement.
sidebar_label: O2C Trace Case
---

# O2C Trace Case

**Audience:** Students and instructors using the dataset to learn revenue-cycle traceability.  
**Purpose:** Walk through one customer sale from order through shipment, invoice, receipt, and cash application.  
**What you will learn:** How the O2C tables connect, where accounting happens, and how to explain timing differences between demand, fulfillment, billing, and settlement.

## Business Scenario

A customer places an order for finished goods. Greenfield ships what inventory allows, invoices from the shipped lines, records the customer payment, and applies that cash against open invoices. In some cases the customer later returns part of the billed quantity, but the core trace begins with the normal order-to-cash path.

## Recommended Build Mode

- Clean build for baseline traceability
- Default build if you also want to discuss exception-oriented follow-up

## Main Tables and Worksheets

- `SalesOrder`
- `SalesOrderLine`
- `Shipment`
- `ShipmentLine`
- `SalesInvoice`
- `SalesInvoiceLine`
- `CashReceipt`
- `CashReceiptApplication`
- `GLEntry`

## Recommended Query Sequence

1. Run [../../../queries/audit/01_o2c_document_chain_completeness.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/01_o2c_document_chain_completeness.sql).
2. Run [../../../queries/financial/01_monthly_revenue_and_gross_margin.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/01_monthly_revenue_and_gross_margin.sql).
3. Run [../../../queries/financial/02_ar_aging_open_invoices.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/02_ar_aging_open_invoices.sql).
4. If you want the exception follow-up, run [../../../queries/audit/07_backorder_and_return_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/07_backorder_and_return_review.sql).

## Suggested Excel Sequence

1. Filter `SalesOrder` to one order or one month.
2. Use `SalesOrderID` to trace into `Shipment` and `ShipmentLine`.
3. Use `ShipmentLineID` to trace into `SalesInvoiceLine`.
4. Use `SalesInvoiceID` to trace into `CashReceiptApplication`.
5. Compare the source-document dates to the posted `GLEntry` timing.

## What Students Should Notice

- Order entry does not post to the ledger.
- Shipment and invoice dates can differ.
- `CashReceipt` is not the same as AR settlement; `CashReceiptApplication` is the authoritative settlement link.
- Backorders and later billing explain why customer service timing and accounting timing are not identical.

## Follow-Up Questions

- Which step in the trace creates revenue?
- Which step reduces inventory?
- How would you identify receipts that arrived before an invoice was fully settled?
- How would the trace change if a return and credit memo followed the original sale?
