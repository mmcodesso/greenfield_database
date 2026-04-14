---
title: Attendance Control Audit Case
description: Guided walkthrough for roster, punch, overtime-approval, and absence-control review.
sidebar_label: Attendance Control Case
---

# Attendance Control Audit Case

## Audience and Purpose

Use this case when students need a focused audit lab around workforce-planning controls and timekeeping exceptions.

## Business Scenario

Internal audit has been asked to review whether scheduled work, raw punches, approved time, absences, and overtime approvals stay aligned. The objective is to identify attendance-control failures without losing the operational context behind them.

## Main Tables and Worksheets

- `EmployeeShiftRoster`
- `EmployeeAbsence`
- `TimeClockPunch`
- `TimeClockEntry`
- `OvertimeApproval`
- `AttendanceException`
- `Employee`
- `greenfield_support.xlsx`
  - `AnomalyLog`
  - `ValidationChecks`
  - `ValidationExceptions`

## Recommended Query Sequence

1. Run [../../../queries/audit/37_scheduled_without_punch_and_punch_without_schedule_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/37_scheduled_without_punch_and_punch_without_schedule_review.sql).
2. Run [../../../queries/audit/38_overtime_without_approval_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/38_overtime_without_approval_review.sql).
3. Run [../../../queries/audit/39_absence_with_worked_time_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/39_absence_with_worked_time_review.sql).
4. Run [../../../queries/audit/40_overlapping_or_incomplete_punch_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/40_overlapping_or_incomplete_punch_review.sql).
5. Run [../../../queries/audit/41_roster_after_termination_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/41_roster_after_termination_review.sql).

## Suggested Excel Sequence

1. Filter `AnomalyLog` to Phase 21 workforce anomaly families.
2. Trace the affected employee/date combinations into `EmployeeShiftRoster`, `TimeClockPunch`, and `TimeClockEntry`.
3. Use `ValidationExceptions` to compare planted anomalies with the control failures identified by the validation workflow.

## What Students Should Notice

- Roster failures, punch failures, and approval failures are different control problems even when they occur on the same day.
- A missing final punch can create both attendance and payroll review consequences.
- Absence rows and worked time should rarely coexist for the same planned shift.
- Workforce-planning exceptions are more meaningful when students trace them back to the planned roster row and the approved daily time summary.

## Follow-Up Questions

- Which anomaly type is easiest to detect with a simple query, and which requires a multi-table review?
- When should auditors start from the support workbook and when should they move directly to the raw attendance tables?
- Which attendance exception would create the greatest payroll overstatement risk?
- Which attendance exception is operationally serious even if the payroll impact is small?
