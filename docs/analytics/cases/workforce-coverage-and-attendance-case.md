---
title: Workforce Coverage and Attendance Case
description: Inquiry-led walkthrough for staffing coverage, approved worked hours, absence concentration, overtime response, and attendance drift.
sidebar_label: Workforce Coverage Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# Workforce Coverage and Attendance Case

## Business Scenario

Operations leaders can see production pressure building across several work centers. Scheduled load remains high, but coverage is uneven from one team and shift to the next. Some areas appear fully staffed on the roster, yet approved worked hours still fall short once absences, late arrivals, and early departures are included.

Supervisors respond with reassigned shifts and overtime, but those actions do not answer the core management question. Leaders still need to know whether workforce pressure comes from weak initial coverage, concentrated absence, recurring attendance drift, or a chronic dependence on overtime to hold throughput together.

This case treats attendance as an operating signal first. The goal is to explain coverage pressure and management response before moving into the separate audit case for formal exception testing.

## The Problem to Solve

You need to prove where planned load outpaces rostered coverage, where approved worked hours recover that gap, and where absence or attendance drift keeps work centers under pressure. You also need to show whether overtime stabilizes operations or only hides recurring staffing weakness.

## What You Need to Develop

- A work-center coverage narrative from planned load to rostered hours to approved worked hours.
- An absence interpretation that shows which workforce groups carry the most pressure.
- An overtime-response explanation tied to coverage gaps and recurring staffing strain.
- An attendance-drift interpretation by shift and department.
- A short management-facing recommendation on where planners or supervisors should act first.

## Key Data Sources

- Main tables: `EmployeeShiftRoster`, `WorkOrderOperationSchedule`, `TimeClockEntry`, `EmployeeAbsence`, `OvertimeApproval`, `ShiftDefinition`, `WorkCenter`, `Employee`
- Related guides: [Operations and Risk](../reports/operations-and-risk.md), [Payroll and Workforce](../reports/payroll-perspective.md)
- Related process pages: [Payroll Process](../../processes/payroll.md), [Manufacturing Process](../../processes/manufacturing.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case stays at the staffing and attendance-management level. Use the audit case for punch and approval exceptions, and use the workforce-cost case for payroll-cost interpretation.

## Recommended Query Sequence

1. `managerial/36_staffing_coverage_vs_work_center_planned_load.sql`
2. `managerial/37_rostered_vs_worked_hours_by_work_center_shift.sql`
3. `managerial/38_absence_rate_by_work_location_job_family_month.sql`
4. `managerial/39_overtime_approval_coverage_and_concentration.sql`
5. `managerial/41_late_arrival_early_departure_by_shift_department.sql`

## Step-by-Step Walkthrough

### Step 1. Define staffing coverage against planned load

Start with the operational demand side. Before you interpret absences or overtime, you need to know where planned work already exceeds planned people coverage.

**What we are trying to achieve**

Measure the daily gap between scheduled work-center load and rostered staffing hours.

Coverage pressure starts here. If planned load already exceeds rostered hours, later worked-hour and overtime results become easier to interpret.

**Suggested query**

<QueryReference
  queryKey="managerial/36_staffing_coverage_vs_work_center_planned_load.sql"
  helperText="Use this first to identify work centers where planned load exceeds rostered hours."
/>

**What this query does**

It compares daily work-center planned load from operation schedules to daily rostered hours from employee rosters and calculates the coverage gap.

**How it works**

The query aggregates `EmployeeShiftRoster` by work center and date, aggregates `WorkOrderOperationSchedule` on the same grain, and then joins the two results so both over-covered and under-covered days remain visible.

**What to look for in the result**

- work centers with repeated negative coverage gaps
- days where rostered employees look adequate in count but hours still fall short
- whether coverage gaps cluster in specific months or centers
- where the production story already signals staffing strain before attendance issues are added

### Step 2. Compare rostered hours to approved worked hours

Once the planned gap is clear, move to the execution question. A rostered day does not guarantee equivalent worked hours.

**What we are trying to achieve**

Compare planned rostered hours with approved worked hours by work center and shift.

Rostered coverage and worked coverage answer different questions. The first shows staffing intent. The second shows the hours operations actually received.

**Suggested query**

<QueryReference
  queryKey="managerial/37_rostered_vs_worked_hours_by_work_center_shift.sql"
  helperText="Use this to compare rostered hours, approved worked hours, and overtime by shift."
/>

**What this query does**

It summarizes rostered hours, approved worked hours, and overtime hours by month, work center, and shift.

**How it works**

The query builds one aggregate from `EmployeeShiftRoster` and another from `TimeClockEntry`, aligns them on month, work center, and shift, and then calculates the variance between planned and worked time.

**What to look for in the result**

- shifts where approved worked hours consistently trail rostered hours
- areas where overtime fills part of the shortfall
- shifts that appear fully rostered but still underperform on worked hours
- whether coverage pressure concentrates on one shift pattern

### Step 3. Localize absence pressure

After you understand the coverage gap, isolate the workforce groups driving attendance pressure.

**What we are trying to achieve**

Identify where absence hours concentrate across work locations and job families.

Managers cannot act on a generic absence rate. They need to know which parts of the workforce create the pressure.

**Suggested query**

<QueryReference
  queryKey="managerial/38_absence_rate_by_work_location_job_family_month.sql"
  helperText="Use this to localize absence pressure by month, location, and job family."
/>

**What this query does**

It measures rostered hours, absence hours, and absence rates by month, work location, and job family.

**How it works**

The query aggregates rostered hours from `EmployeeShiftRoster`, aggregates absence hours from `EmployeeAbsence`, joins both sets through `Employee`, and calculates paid and unpaid absence patterns on the same workforce grouping.

**What to look for in the result**

- locations with the highest absence rates
- job families with unusual absence concentration
- whether paid and unpaid absence patterns differ materially
- where absence pressure is strong enough to help explain the coverage gaps from the earlier steps

### Step 4. Evaluate overtime as the response mechanism

Now assess how operations responded once staffing pressure appeared.

**What we are trying to achieve**

Show where overtime concentrates and whether it functions as occasional support or recurring dependency.

Overtime can protect throughput in the short term. It also signals that the staffing model may already be under strain.

**Suggested query**

<QueryReference
  queryKey="managerial/39_overtime_approval_coverage_and_concentration.sql"
  helperText="Use this to measure overtime concentration and approval coverage by work center."
/>

**What this query does**

It summarizes overtime hours, approved overtime hours, and approval coverage metrics by month and work center.

**How it works**

The query starts from `TimeClockEntry`, groups overtime activity by month and work center, joins `OvertimeApproval`, and then calculates how much recorded overtime carried supporting approval.

**What to look for in the result**

- work centers with repeated overtime concentration
- months where overtime grows while coverage gaps remain negative
- whether approval coverage stays high even when overtime volume rises
- where overtime looks like a sustained operating response rather than a short-term fix

### Step 5. Translate attendance drift into management follow-up

Finish by measuring the smaller attendance patterns that reduce available time even when staffing and overtime look reasonable on the surface.

**What we are trying to achieve**

Identify shifts and departments where late arrivals or early departures reduce actual available labor time.

This is the last management step before a formal control review. Attendance drift is an operating signal. The audit case handles the exception-testing follow-through.

**Suggested query**

<QueryReference
  queryKey="managerial/41_late_arrival_early_departure_by_shift_department.sql"
  helperText="Use this to measure attendance drift by month, shift, and department."
/>

**What this query does**

It measures minutes late, minutes of early departure, and the number of affected rostered days by month, department, and shift.

**How it works**

The query compares scheduled start and end times from `EmployeeShiftRoster` to approved clock-in and clock-out times from `TimeClockEntry`, then rolls those differences up through `ShiftDefinition`.

**What to look for in the result**

- shifts with repeated late-start patterns
- departments losing significant time to early departures
- whether attendance drift appears in the same areas that already show coverage or overtime strain
- which area should move next into [Attendance Control Audit Case](attendance-control-audit-case.md) for formal exception review

## Optional Excel Follow-Through

1. Build one pivot by month and work center for planned load, rostered hours, and approved worked hours.
2. Build one absence pivot by work location and job family.
3. Build one narrower overtime pivot by work center and month.
4. Build one shift or department pivot for late-arrival and early-departure minutes.
5. Compare those views side by side instead of merging them into one oversized workbook.

## Wrap-Up Questions

- Which work center has the most persistent negative coverage gap?
- Does absence concentration or worked-hour shortfall explain more of that pressure?
- Where does overtime act like a temporary response, and where does it look like chronic dependency?
- Which shift or department shows the strongest attendance drift?
- Which management action should come first?

## Next Steps

- Use [Attendance Control Audit Case](attendance-control-audit-case.md) when you want to test punch, approval, and absence exceptions formally.
- Use [Payroll Process](../../processes/payroll.md) when you want the broader support-to-payroll flow behind approved hours and overtime.
- Use [Workforce Cost and Org-Control Case](workforce-cost-and-org-control-case.md) when you want to connect workforce structure to payroll cost and approval design.
- Use [Operations and Risk](../reports/operations-and-risk.md) when you want the broader operational reporting perspective on staffing pressure and throughput risk.
