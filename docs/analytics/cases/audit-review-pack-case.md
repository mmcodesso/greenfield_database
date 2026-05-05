---
title: Audit Review Pack Case
description: Inquiry-led walkthrough for broad audit triage, exception tracing, and source-evidence review.
sidebar_label: Audit Review Pack
---

import { QueryReference } from "@site/src/components/QueryReference";

# Audit Review Pack Case

## Business Scenario

The internal-audit team receives the normal three-year package covering fiscal years 2024 through 2026 with a moderate set of planted anomalies. The job is not to prove every issue from scratch. The job is to use audit starter queries, source tables, and workbook evidence together so the team can explain what happened, where it happened, and what it means.

This case consolidates the former exception lab into the broad review pack. Students still practice tracing flagged rows to source evidence, but the workflow now moves through the full audit triage stack: starter anomalies, manufacturing audit seeds, master data, workforce controls, and planning-support controls.

## The Problem to Solve

The review team needs to separate timing issues, approval failures, linkage failures, master-data issues, workforce-control failures, and planning-support exceptions without treating every flagged row as the same kind of risk.

## What You Need to Develop

- A starting exception map that distinguishes payment, payroll, manufacturing linkage, and operation-sequence issues.
- A manufacturing audit-seed follow-through from summary evidence to released work-order detail.
- A master-data and ownership triage view across employee, approver, and item controls.
- A workforce-control interpretation across terminated activity, roster, punch, absence, overtime, and time-clock exceptions.
- A planning-support conclusion that separates planning-governance issues from execution failures.
- A short audit-facing recommendation on which exception family deserves escalation first.

## Before You Start

- Main tables: `Employee`, `Item`, `PurchaseInvoice`, `DisbursementPayment`, `PayrollRegister`, `PayrollPayment`, `WorkOrder`, `WorkOrderOperation`, `WorkOrderOperationSchedule`, `WorkCenter`, `LaborTimeEntry`, `TimeClockEntry`
- Related guide: [Audit Analytics](../audit.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case is the broad audit triage and source-tracing case. Use the specialized audit cases when you need deeper follow-through for workforce validity, attendance controls, replenishment support, or pricing governance.

## Step-by-Step Walkthrough

### Step 1. Build the starter exception map

Start with a cross-process scan. The goal is to separate exception families before opening detailed source evidence.

**What we are trying to achieve**

Identify whether the first visible exceptions are payment, payroll, manufacturing linkage, or operation-sequence problems.

**Why this step changes the diagnosis**

A duplicate payment reference, a payroll control issue, a missing routing link, and a sequence failure are different control failures. The audit response depends on which pattern appears first.

**Suggested query**

<QueryReference
  queryKey="audit/05_duplicate_payment_reference_review.sql"
  helperText="Use this to identify duplicate or reused payment reference patterns."
/>

<QueryReference
  queryKey="audit/11_payroll_control_review.sql"
  helperText="Use this to identify payroll control exceptions before tracing source payroll rows."
/>

<QueryReference
  queryKey="audit/14_missing_routing_or_operation_link_review.sql"
  helperText="Use this to find missing manufacturing routing or operation links."
/>

<QueryReference
  queryKey="audit/15_operation_sequence_and_final_completion_review.sql"
  helperText="Use this to review operation sequencing and final completion evidence."
/>

**What these queries do**

They surface the first layer of planted exception evidence across AP, payroll, and manufacturing operations.

**How they work**

The queries each start from source transaction tables, retain the source document keys, and flag patterns where reference reuse, payroll support, routing links, or operation status evidence does not match the expected control path.

**What to look for in the result**

- the exception family with the clearest source-document keys
- whether the issue is timing, approval, linkage, or status evidence
- affected periods or process areas that repeat across results
- which row should be traced first in the workbook or SQLite source tables

### Step 2. Trace the manufacturing audit seed from summary to detail

Next isolate the validation-only manufacturing audit-seed pattern. It is related to anomaly review, but it should be explained as a controlled teaching seed rather than a broad anomaly-log family.

**What we are trying to achieve**

Move from released-work-order summary evidence into detailed due-without-actual-start rows.

**Why this step changes the diagnosis**

The `manufacturing_audit_seeds` area teaches source tracing without implying every exception family behaves the same way. Students need to distinguish a validation seed from a broader anomaly category.

**Suggested query**

<QueryReference
  queryKey="audit/53_released_work_orders_due_without_actual_start_summary.sql"
  helperText="Use this summary first to size the released-work-order seed pattern."
/>

<QueryReference
  queryKey="audit/52_released_work_orders_due_without_actual_start_review.sql"
  helperText="Use this detail query to trace the affected released work orders."
/>

**What these queries do**

The summary query sizes the released-work-order pattern, while the detail query lists the work orders due without actual start evidence.

**How they work**

The summary aggregates the seeded manufacturing exception pattern. The detail query keeps the work-order identifiers and operational dates needed to trace the source rows.

**What to look for in the result**

- whether the summary count agrees with the detail rows
- work orders that are due but lack actual start evidence
- source keys needed for workbook tracing
- how this validation-only seed differs from anomaly-log families

### Step 3. Triage master-data and ownership controls

Once starter exceptions are mapped, move to master data. This step tests whether employee and item master controls create the conditions for downstream exceptions.

**What we are trying to achieve**

Separate employee ownership issues, approval-authority issues, and item-master issues from transaction-processing failures.

**Why this step changes the diagnosis**

Some flagged rows are not caused by a bad transaction. They are caused by stale ownership, weak approval authority, incomplete item setup, or activity against an item status that should restrict use.

**Suggested query**

<QueryReference
  queryKey="audit/29_executive_role_uniqueness_and_control_assignment_review.sql"
  helperText="Use this to review key role uniqueness and control assignments."
/>

<QueryReference
  queryKey="audit/34_current_state_employee_assignment_review.sql"
  helperText="Use this to find current assignments tied to inactive or terminated employees."
/>

<QueryReference
  queryKey="audit/35_approval_authority_limit_review.sql"
  helperText="Use this to flag approval events outside role or authority expectations."
/>

<QueryReference
  queryKey="audit/30_item_master_completeness_review.sql"
  helperText="Use this to review item-master completeness issues."
/>

<QueryReference
  queryKey="audit/36_item_status_alignment_review.sql"
  helperText="Use this to test whether item status and active flags remain aligned."
/>

<QueryReference
  queryKey="audit/31_discontinued_or_prelaunch_item_activity_review.sql"
  helperText="Use this to find activity against discontinued or prelaunch items."
/>

**What these queries do**

They review executive role ownership, stale employee assignments, approval authority, item setup completeness, item-status alignment, and activity against items that should not be used normally.

**How they work**

The queries start from master-data tables and approval events, then join to employee or item attributes that define whether the row is valid for current-state ownership, approval authority, or item lifecycle status.

**What to look for in the result**

- master-data issues that explain multiple downstream exceptions
- approval exceptions that are authority problems rather than timing problems
- item setup issues that could affect sales, manufacturing, or planning
- whether remediation belongs to master-data owners or transaction processors

### Step 4. Triage workforce-control exceptions

After master-data issues are separated, focus on workforce controls. This step keeps roster, punch, absence, overtime, and time-clock exceptions distinct.

**What we are trying to achieve**

Determine whether workforce exceptions reflect terminated activity, schedule gaps, punch gaps, absence conflicts, overtime approval failures, or supervisor/work-center concentration.

**Why this step changes the diagnosis**

Workforce-control exceptions often share employees and dates, but they do not have the same owner. A roster issue, punch issue, absence conflict, and overtime approval failure require different follow-up.

**Suggested query**

<QueryReference
  queryKey="audit/33_terminated_employee_activity_rollup_by_process_area.sql"
  helperText="Use this to summarize terminated employee activity by process area."
/>

<QueryReference
  queryKey="audit/37_scheduled_without_punch_and_punch_without_schedule_review.sql"
  helperText="Use this to find schedule and punch mismatches."
/>

<QueryReference
  queryKey="audit/38_overtime_without_approval_review.sql"
  helperText="Use this to find overtime entries missing approval or exceeding approved hours."
/>

<QueryReference
  queryKey="audit/39_absence_with_worked_time_review.sql"
  helperText="Use this to find absence records that overlap with worked time."
/>

<QueryReference
  queryKey="audit/40_overlapping_or_incomplete_punch_review.sql"
  helperText="Use this to find overlapping or incomplete raw punch evidence."
/>

<QueryReference
  queryKey="audit/41_roster_after_termination_review.sql"
  helperText="Use this to find rostered days after termination."
/>

<QueryReference
  queryKey="audit/19_time_clock_exceptions_by_employee_supervisor_work_center.sql"
  helperText="Use this to summarize time-clock exception concentration by employee, supervisor, and work center."
/>

**What these queries do**

They summarize terminated activity and expose schedule, punch, absence, overtime, roster, and time-clock exception patterns.

**How they work**

The queries join employee lifecycle, roster, punch, time-clock, absence, overtime approval, supervisor, and work-center evidence so the same employee/date can be interpreted across different control layers.

**What to look for in the result**

- exception types that share employee/date keys
- supervisor or work-center concentration
- exceptions that create payroll risk versus operational documentation risk
- when the follow-up should move into the dedicated attendance control audit case

### Step 5. Triage planning-support controls

Finish with planning support. These exceptions start before execution and show whether forecasts, policies, recommendations, requisitions, and work orders have credible planning evidence.

**What we are trying to achieve**

Separate planning-governance failures from later replenishment or manufacturing execution failures.

**Why this step changes the diagnosis**

Unsupported requisitions or work orders may look like execution problems, but the root cause can be missing forecast approval, stale policy coverage, late recommendation conversion, or lifecycle-inconsistent planning activity.

**Suggested query**

<QueryReference
  queryKey="audit/42_forecast_approval_and_override_review.sql"
  helperText="Use this to review forecast approval and override exceptions."
/>

<QueryReference
  queryKey="audit/43_inactive_or_stale_inventory_policy_review.sql"
  helperText="Use this to find inactive or stale inventory policy coverage."
/>

<QueryReference
  queryKey="audit/44_requisitions_and_work_orders_without_planning_support.sql"
  helperText="Use this to find replenishment documents without planning support."
/>

<QueryReference
  queryKey="audit/45_recommendation_converted_after_need_by_date_review.sql"
  helperText="Use this to identify late recommendation conversion."
/>

<QueryReference
  queryKey="audit/46_discontinued_or_prelaunch_planning_activity_review.sql"
  helperText="Use this to find planning activity against discontinued or prelaunch items."
/>

**What these queries do**

They review planning approval, policy coverage, unsupported replenishment documents, late recommendation conversion, and lifecycle-inconsistent planning activity.

**How they work**

The queries connect planning master data and recommendations to requisitions, work orders, item lifecycle status, and planning dates so students can see whether execution has sufficient planning support.

**What to look for in the result**

- planning failures that occur before execution starts
- unsupported documents tied to missing forecast or recommendation evidence
- late conversions that create timing-control risk
- whether the next review should move to the dedicated replenishment support audit case

## Optional Excel Follow-Through

1. Pick one AP, payroll, or manufacturing starter exception and trace it back to the source document keys.
2. Reconcile the released-work-order summary to the detailed `manufacturing_audit_seeds` rows.
3. Build one master-data tab for employee, approver, and item-control issues.
4. Build one workforce-control tab for terminated activity, roster, punch, absence, overtime, and time-clock exceptions.
5. Build one planning-support tab for forecast approval, inventory policy, recommendation conversion, and unsupported documents.
6. Write a short escalation memo that classifies the strongest finding as timing, approval, linkage, master-data, workforce-control, or planning-governance risk.

## Wrap-Up Questions

- Which exception family would you escalate first, and why?
- Which query gives the best starting point, and which query gives the best source-level detail?
- Which planted anomalies represent timing issues versus approval issues versus linkage issues?
- How does a validation-only `manufacturing_audit_seeds` pattern differ from a broader anomaly-log family?
- Which issues belong in a specialized follow-up case instead of the broad audit review pack?

## Next Steps

- Read [Audit Analytics](../audit.md) when you want the broader audit query library around these anomaly families.
- Read [Schema Reference](../../reference/schema.md) when you need the table bridges behind a flagged exception.
- Read [Attendance Control Audit Case](attendance-control-audit-case.md), [Replenishment Support Audit Case](replenishment-support-audit-case.md), or [Pricing Governance Audit Case](pricing-governance-audit-case.md) when the broad triage points to a specialized control area.
