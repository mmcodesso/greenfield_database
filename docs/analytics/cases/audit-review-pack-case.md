---
title: Audit Review Pack Case
description: Guided walkthrough for an audit review pack that uses the support workbook and the expanded Phase 20 and Phase 21 audit queries.
sidebar_label: Audit Review Pack
---

# Audit Review Pack Case

## Audience and Purpose

Use this case when students need a structured audit lab that combines the support workbook with source-table SQL review.

## Business Scenario

The internal-audit team receives the normal five-year package and needs to triage control issues quickly. The job is not to prove every issue from scratch. The job is to use the support workbook and the audit starter queries together so the team can explain what happened, where it happened, and why it matters.

## Main Tables and Worksheets

- `greenfield_support.xlsx`
- `AnomalyLog`
- `ValidationStages`
- `ValidationChecks`
- `ValidationExceptions`
- `Employee`
- `Item`
- `PurchaseInvoice`
- `DisbursementPayment`
- `PayrollRegister`
- `WorkOrder`

## Recommended Query Sequence

1. Open `greenfield_support.xlsx` and summarize `AnomalyLog` by `anomaly_type`.
2. Run [../../../queries/audit/29_executive_role_uniqueness_and_control_assignment_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/29_executive_role_uniqueness_and_control_assignment_review.sql).
3. Run [../../../queries/audit/34_current_state_employee_assignment_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/34_current_state_employee_assignment_review.sql).
4. Run [../../../queries/audit/35_approval_authority_limit_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/35_approval_authority_limit_review.sql).
5. Run [../../../queries/audit/30_item_master_completeness_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/30_item_master_completeness_review.sql).
6. Run [../../../queries/audit/36_item_status_alignment_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/36_item_status_alignment_review.sql).
7. Run [../../../queries/audit/31_discontinued_or_prelaunch_item_activity_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/31_discontinued_or_prelaunch_item_activity_review.sql).
8. Run [../../../queries/audit/32_approval_authority_review_by_expected_role_family.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/32_approval_authority_review_by_expected_role_family.sql).
9. Run [../../../queries/audit/33_terminated_employee_activity_rollup_by_process_area.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/33_terminated_employee_activity_rollup_by_process_area.sql).
10. Run [../../../queries/audit/37_scheduled_without_punch_and_punch_without_schedule_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/37_scheduled_without_punch_and_punch_without_schedule_review.sql).
11. Run [../../../queries/audit/38_overtime_without_approval_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/38_overtime_without_approval_review.sql).
12. Run [../../../queries/audit/39_absence_with_worked_time_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/39_absence_with_worked_time_review.sql).
13. Run [../../../queries/audit/40_overlapping_or_incomplete_punch_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/40_overlapping_or_incomplete_punch_review.sql).
14. Run [../../../queries/audit/41_roster_after_termination_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/41_roster_after_termination_review.sql).
15. Run [../../../queries/audit/42_forecast_approval_and_override_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/42_forecast_approval_and_override_review.sql).
16. Run [../../../queries/audit/43_inactive_or_stale_inventory_policy_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/43_inactive_or_stale_inventory_policy_review.sql).
17. Run [../../../queries/audit/44_requisitions_and_work_orders_without_planning_support.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/44_requisitions_and_work_orders_without_planning_support.sql).
18. Run [../../../queries/audit/45_recommendation_converted_after_need_by_date_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/45_recommendation_converted_after_need_by_date_review.sql).
19. Run [../../../queries/audit/46_discontinued_or_prelaunch_planning_activity_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/46_discontinued_or_prelaunch_planning_activity_review.sql).

## Suggested Excel Sequence

1. Start with the support workbook to see which anomaly families were planted.
2. Trace one workforce anomaly, one item-master anomaly, and one approval anomaly back into the dataset workbook or SQLite query results.
3. Write a short plain-language explanation of the control failure and the business risk.

## What Students Should Notice

- The support workbook is a guide, not a substitute for source-document review.
- Several audit queries now focus on master data and org structure as well as document timing.
- The audit pack now also separates roster issues, punch issues, absence issues, and overtime-approval issues.
- Current-state assignment issues and approval-limit exceptions can be reviewed separately from broader role-family questions.
- Planning-support issues can now be reviewed separately from operational execution failures.
- The same anomaly family can appear in both a summary query and a more detailed control query.
- The published dataset should remain explainable. Students should be able to trace each exception to its business context.

## Follow-Up Questions

- Which anomaly family would you escalate first and why?
- Which query gives the best starting point, and which query gives the best detail?
- How would you separate a master-data control issue from an operational processing issue?
