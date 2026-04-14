---
title: Workforce Coverage and Attendance Case
description: Guided walkthrough for staffing coverage, rostered hours, attendance, overtime, and work-center load.
sidebar_label: Workforce Coverage Case
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

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

<QuerySequence items={caseQuerySequences["workforce-coverage-and-attendance-case"]} />

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
