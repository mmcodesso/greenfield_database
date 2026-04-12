---
title: Audit Review Pack Case
description: Guided walkthrough for running a default anomaly-enabled audit review pack with the support workbook and the expanded Phase 20 audit queries.
sidebar_label: Audit Review Pack
---

# Audit Review Pack Case

## Audience and Purpose

Use this case when students need a structured anomaly-enabled audit lab that combines the support workbook with source-table SQL review.

## Recommended Build Mode

- Default anomaly-enabled build

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

## Suggested Excel Sequence

1. Start with the support workbook to see which anomaly families were planted.
2. Trace one workforce anomaly, one item-master anomaly, and one approval anomaly back into the dataset workbook or SQLite query results.
3. Write a short plain-language explanation of the control failure and the business risk.

## What Students Should Notice

- The support workbook is a guide, not a substitute for source-document review.
- Several audit queries now focus on master data and org structure, not only document timing.
- Current-state assignment issues and approval-limit exceptions can be reviewed separately from broader role-family questions.
- The same anomaly family can appear in both a summary query and a more detailed control query.
- An anomaly-enabled dataset should still be explainable. It should not feel random.

## Follow-Up Questions

- Which anomaly family would you escalate first and why?
- Which query gives the best starting point, and which query gives the best detail?
- How would you separate a master-data control issue from an operational processing issue?
