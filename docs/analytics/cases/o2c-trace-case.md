---
title: O2C Trace Case
description: Guided walkthrough for tracing a customer sale from order through settlement.
sidebar_label: O2C Trace Case
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# O2C Trace Case


## Business Scenario

A customer places an order for finished goods. Charles River ships what inventory allows, invoices from the shipped lines, records the customer payment, and applies that cash against open invoices. In some cases the customer later returns part of the billed quantity, but the core trace begins with the normal order-to-cash path.

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

<QuerySequence items={caseQuerySequences["o2c-trace-case"]} />

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
