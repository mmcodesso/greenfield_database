---
title: Working Capital and Cash Conversion Case
description: Guided walkthrough for control-account balances and settlement timing across AR, AP, deposits, payroll, and accruals.
sidebar_label: Working Capital Case
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# Working Capital and Cash Conversion Case

## Audience and Purpose

Use this case when students need to connect operating documents to month-end working-capital balances and cash-conversion timing.

## Business Scenario

The finance team wants to explain why working capital moves from month to month. The core question is how invoices, receipts, applications, supplier payments, payroll liabilities, customer deposits, and accrued expenses combine into a working-capital story.

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

## Recommended Query Sequence

<QuerySequence items={caseQuerySequences["working-capital-and-cash-conversion-case"]} />

## Suggested Excel Sequence

1. Build a month-by-month bridge from `GLEntry` and `Account` for AR, inventory, AP, GRNI, customer deposits, accrued expenses, and payroll liabilities.
2. Add a second view that compares invoice-to-application, invoice-to-payment, and receipt-to-payment timing.
3. Filter the workbook to one year when you want a smaller in-class discussion.

## What Students Should Notice

- Working capital is a timing story as well as a balance-sheet story.
- Customer deposits and unapplied cash can move independently from AR.
- Goods receipt to payment timing is not the same as purchase invoice to payment timing.
- Payroll liabilities and accrued expenses are part of working capital, even though they do not look like sales or inventory activity.

## Follow-Up Questions

- Which working-capital bucket moves the most across the modeled range?
- Which timing metric would you expect management to monitor most closely?
- Why can working capital tighten even when revenue is rising?
