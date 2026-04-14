---
title: Master Data and Workforce Audit Case
description: Guided walkthrough for employee lifecycle, approval-role, and master-data control review.
sidebar_label: Workforce Audit Case
---

# Master Data and Workforce Audit Case


## Business Scenario

Greenfield now keeps a more realistic employee master. The company has one CEO, one CFO, one Controller, one Production Manager, and one Accounting Manager. Frontline roles repeat where that makes business sense. Some employees terminate during the modeled range, replacements are hired into the same operating structure, and the historical rows remain in the employee master for traceability.

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
- `greenfield_support.xlsx` sheets:
  - `AnomalyLog`
  - `ValidationChecks`
  - `ValidationExceptions`

## Recommended Query Sequence

1. Run [../../../queries/managerial/29_headcount_by_cost_center_job_family_status.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/29_headcount_by_cost_center_job_family_status.sql).
2. Run [../../../queries/audit/27_terminated_employee_activity_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/27_terminated_employee_activity_review.sql).
3. Run [../../../queries/audit/34_current_state_employee_assignment_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/34_current_state_employee_assignment_review.sql).
4. Run [../../../queries/audit/28_approval_role_review_by_org_position.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/28_approval_role_review_by_org_position.sql).
5. Run [../../../queries/audit/35_approval_authority_limit_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/35_approval_authority_limit_review.sql).
6. Run [../../../queries/audit/41_roster_after_termination_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/41_roster_after_termination_review.sql).
7. Run [../../../queries/audit/38_overtime_without_approval_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/38_overtime_without_approval_review.sql).
8. Open `greenfield_support.xlsx` and filter `AnomalyLog` to the workforce-related anomaly types.

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

- Which roles should be unique in a company like Greenfield, and why?
- Why is it useful to keep terminated employees in the master table for historical traceability?
- Which approvals would you expect the CFO, Controller, Accounting Manager, and Production Manager to own?
