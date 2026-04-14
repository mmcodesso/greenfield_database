---
title: Financial Statement Bridge Case
description: Guided walkthrough for tracing operational activity into the ledger and close-cycle balances.
sidebar_label: Statement Bridge Case
---

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

1. Run [../../../queries/financial/04_trial_balance_by_period.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/04_trial_balance_by_period.sql).
2. Run [../../../queries/financial/05_journal_and_close_cycle_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/05_journal_and_close_cycle_review.sql).
3. Run [../../../queries/financial/06_control_account_reconciliation.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/06_control_account_reconciliation.sql).
4. Run [../../../queries/financial/16_retained_earnings_and_close_entry_impact.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/16_retained_earnings_and_close_entry_impact.sql).
5. Run [../../../queries/financial/17_manufacturing_cost_component_bridge.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/17_manufacturing_cost_component_bridge.sql).
6. Run [../../../queries/financial/19_working_capital_bridge_by_month.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/19_working_capital_bridge_by_month.sql).

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
