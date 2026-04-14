---
title: Workforce Coverage and Attendance Case
description: Guided walkthrough for staffing coverage, rostered hours, attendance, overtime, and work-center load.
sidebar_label: Workforce Coverage Case
---

# Workforce Coverage and Attendance Case

## Audience and Purpose

Use this case when students need to connect planned staffing, approved worked time, and work-center demand.

## Business Scenario

Greenfield operations leaders want to understand whether work-center staffing kept pace with scheduled load, where absences concentrated, and how overtime was used to protect throughput.

## Main Tables and Worksheets

- `EmployeeShiftRoster`
- `EmployeeAbsence`
- `TimeClockEntry`
- `TimeClockPunch`
- `OvertimeApproval`
- `WorkOrderOperationSchedule`
- `WorkCenter`
- `Employee`

## Recommended Query Sequence

1. Run [../../../queries/managerial/36_staffing_coverage_vs_work_center_planned_load.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/36_staffing_coverage_vs_work_center_planned_load.sql).
2. Run [../../../queries/managerial/37_rostered_vs_worked_hours_by_work_center_shift.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/37_rostered_vs_worked_hours_by_work_center_shift.sql).
3. Run [../../../queries/managerial/38_absence_rate_by_work_location_job_family_month.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/38_absence_rate_by_work_location_job_family_month.sql).
4. Run [../../../queries/managerial/39_overtime_approval_coverage_and_concentration.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/39_overtime_approval_coverage_and_concentration.sql).
5. Run [../../../queries/managerial/41_late_arrival_early_departure_by_shift_department.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/41_late_arrival_early_departure_by_shift_department.sql).

## Suggested Excel Sequence

1. Build a pivot from `EmployeeShiftRoster` by `RosterDate`, `WorkCenterID`, and `RosterStatus`.
2. Add approved worked hours from `TimeClockEntry`.
3. Add absence hours from `EmployeeAbsence`.
4. Compare overtime by work center using `OvertimeApproval`.

## What Students Should Notice

- Staffing gaps do not always show up as zero rostered hours. They often show up as planned load outpacing rostered or worked hours.
- Absence pressure and overtime pressure are linked but not identical.
- Reassigned rosters and overtime approvals are operational responses, not necessarily control failures.
- The published dataset includes both normal operating pressure and a small number of attendance-control exceptions.

## Follow-Up Questions

- Which work centers show the largest repeated negative coverage gap?
- Does overtime concentrate where coverage gaps persist?
- Are absences more concentrated by location, job family, or shift?
- Which attendance trend would matter most to a production planner?
