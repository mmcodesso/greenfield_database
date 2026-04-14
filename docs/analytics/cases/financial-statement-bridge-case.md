---
title: Financial Statement Bridge Case
description: Guided walkthrough for tracing operational activity into the ledger and close-cycle balances.
sidebar_label: Statement Bridge Case
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# Financial Statement Bridge Case

## Audience and Purpose

Use this case when students need to move from subledger activity into `GLEntry`, control accounts, and year-end close entries.

## Business Scenario

The accounting team has operational evidence for sales, purchasing, payroll, manufacturing, and accruals. The question is how those flows accumulate into the financial statements, which balances are control accounts, and what changes once year-end close journals run.

## Main Tables and Worksheets

- `GLEntry`
- `JournalEntry`
- `Account`
- `SalesInvoice`
- `PurchaseInvoice`
- `WorkOrderClose`
- `PayrollRegister`
- `greenfield_support.xlsx`:
  - `ValidationStages`
  - `ValidationChecks`

## Recommended Query Sequence

<QuerySequence items={caseQuerySequences["financial-statement-bridge-case"]} />

## Suggested Excel Sequence

1. Build a trial-balance pivot by `FiscalYear`, `FiscalPeriod`, `AccountType`, and `AccountSubType`.
2. Add a lookup from `GLEntry` back to `JournalEntry[EntryType]`.
3. Compare control-account movement to the operational source tables.

## What Students Should Notice

- Not every operational table posts, but the posting flow is still traceable.
- Year-end close changes equity presentation without changing the underlying operating history.
- Manufacturing and payroll balances now have enough detail to explain both income-statement and balance-sheet movement.
- The financial-statement bridge gets stronger when students separate operating journals from close journals.

## Follow-Up Questions

- Which control account is easiest to reconcile from source documents?
- Which balances depend most on timing assumptions and which depend most on physical movement?
- How would you explain the close cycle to someone who understands operations but not accounting?
