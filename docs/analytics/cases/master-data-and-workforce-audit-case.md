---
title: Master Data and Workforce Audit Case
description: Guided walkthrough for employee lifecycle, approval-role, and master-data control review.
sidebar_label: Workforce Audit Case
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# Master Data and Workforce Audit Case


## Business Scenario

The dataset keeps a more realistic employee master. The company has one CEO, one CFO, one Controller, one Production Manager, and one Accounting Manager. Frontline roles repeat where that makes business sense. Some employees terminate during the modeled range, replacements are hired into the same operating structure, and the historical rows remain in the employee master for traceability.

This case asks students to test whether operational activity, approvals, and payroll behavior still respect that workforce lifecycle.

## Main Tables and Worksheets

- `Employee`
- `CostCenter`
- `PayrollRegister`
- `TimeClockEntry`
- `LaborTimeEntry`
- `EmployeeShiftRoster`
- `EmployeeAbsence`
- `TimeClockPunch`
- `OvertimeApproval`
- `PurchaseOrder`
- `JournalEntry`
- <FileName type="support" /> sheets:
  - `AnomalyLog`
  - `ValidationChecks`
  - `ValidationExceptions`

## Recommended Query Sequence

<QuerySequence items={caseQuerySequences["master-data-and-workforce-audit-case"]} />

## Suggested Excel Sequence

1. Use `Employee` to build a pivot by `CostCenterID`, `JobFamily`, `JobLevel`, and `EmploymentStatus`.
2. Filter terminated employees and compare `TerminationDate` to any linked payroll, time-clock, or approval evidence.
3. Review current-state manager and sales-rep assignments to see whether ownership still points to active employees.
4. Use the support workbook to identify which anomalies were intentionally planted and which control expectation each one tests.

## What Students Should Notice

- `IsActive` is current-state metadata, not a replacement for historical employment dates.
- The employee master should support both org-structure analysis and transaction-date validity testing.
- Approval review becomes more meaningful when executive and finance roles are unique and stable.
- Current-state assignment ownership is a different control question from post-termination transaction activity.
- Workforce-planning controls now let students test the schedule, punch, absence, and overtime layers separately from the payroll summary.
- Terminated employees remain in the dataset for audit traceability, and operational activity should stop at the termination date.

## Follow-Up Questions

- Which roles should be unique in a company like this one, and why?
- Why is it useful to keep terminated employees in the master table for historical traceability?
- Which approvals would you expect the CFO, Controller, Accounting Manager, and Production Manager to own?
