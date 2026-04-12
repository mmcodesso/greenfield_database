---
title: Workforce Cost and Org-Control Case
description: Guided walkthrough for workforce mix, payroll cost concentration, approval design, and executive-role review.
sidebar_label: Workforce Cost Case
---

# Workforce Cost and Org-Control Case

## Audience and Purpose

Use this case when students need to connect people-cost analysis to workforce structure and approval design.

## Recommended Build Mode

- Default anomaly-enabled build

## Business Scenario

Greenfield’s leadership wants to understand where people cost sits, how workforce structure varies by location and cost center, and whether approval activity lines up with the intended organization design.

## Main Tables and Worksheets

- `Employee`
- `CostCenter`
- `PayrollRegister`
- `TimeClockEntry`
- `LaborTimeEntry`
- `PurchaseRequisition`
- `PurchaseOrder`
- `JournalEntry`
- `greenfield_support.xlsx`:
  - `AnomalyLog`
  - `ValidationChecks`

## Recommended Query Sequence

1. Run [../../../queries/financial/22_payroll_and_people_cost_mix_by_cost_center_job_family_level.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/22_payroll_and_people_cost_mix_by_cost_center_job_family_level.sql).
2. Run [../../../queries/managerial/34_labor_and_headcount_by_work_location_job_family_cost_center.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/34_labor_and_headcount_by_work_location_job_family_cost_center.sql).
3. Run [../../../queries/audit/29_executive_role_uniqueness_and_control_assignment_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/29_executive_role_uniqueness_and_control_assignment_review.sql).
4. Run [../../../queries/audit/32_approval_authority_review_by_expected_role_family.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/32_approval_authority_review_by_expected_role_family.sql).
5. Run [../../../queries/audit/28_approval_role_review_by_org_position.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/28_approval_role_review_by_org_position.sql).

## Suggested Excel Sequence

1. Pivot `Employee` by `WorkLocation`, `JobFamily`, `JobLevel`, and `EmploymentStatus`.
2. Add payroll totals by cost center and pay class.
3. Compare approval concentration to the intended control-owner roles.

## What Students Should Notice

- Workforce structure is easier to interpret now that executive roles are unique and frontline roles repeat only where that makes sense.
- People-cost concentration and approval concentration are related but not identical.
- Work location and cost center answer different managerial questions.
- The default anomaly-enabled build is better for this case because it creates more reviewable control patterns.

## Follow-Up Questions

- Which job families drive the most payroll cost?
- Which approvals would you expect to be concentrated in finance roles?
- When does a concentrated approval pattern look efficient, and when does it look risky?
