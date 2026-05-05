---
title: Master Data and Workforce Audit Case
description: Inquiry-led walkthrough for employee lifecycle, approval-role, and master-data control review.
sidebar_label: Workforce Audit Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# Master Data and Workforce Audit Case

## Business Scenario

The dataset keeps a realistic employee master. The company has one CEO, one CFO, one Controller, one Production Manager, and one Accounting Manager. Frontline roles repeat where that makes business sense. Some employees terminate during the modeled range, replacements are hired into the same operating structure, and the historical rows remain in the employee master for traceability.

The audit question is whether employee status, current ownership, approval activity, scheduling, and overtime controls still respect that lifecycle. A trustworthy employee master should support payroll, timekeeping, approvals, and organization analysis at the same time.

## The Problem to Solve

The review team needs to determine whether employee lifecycle, active-status ownership, approval roles, and downstream workforce activity line up well enough to trust the workforce-control environment.

## What You Need to Develop

- A workforce status baseline by cost center, job family, job level, and employment status.
- A post-termination activity view that separates historical traceability from invalid downstream use.
- A current-state ownership review for managers, work-center leaders, warehouse managers, and sales reps.
- An approval-role and authority-limit interpretation across operational and accounting documents.
- A workforce-control conclusion that identifies whether the next follow-up belongs in master-data cleanup, approval review, attendance-control audit, or workforce-cost interpretation.

## Before You Start

- Main tables: `Employee`, `CostCenter`, `PayrollRegister`, `TimeClockEntry`, `LaborTimeEntry`, `EmployeeShiftRoster`, `TimeClockPunch`, `OvertimeApproval`, `PurchaseOrder`, `JournalEntry`
- Related guide: [Audit Queries](../audit.md)
- Related process page: [Payroll](../../processes/payroll.md)
- Related case: [Workforce Cost and Org-Control Case](workforce-cost-and-org-control-case.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case audits employee-master trust across lifecycle, ownership, approval, and workforce-control layers. It does not treat employee data as static setup, and it does not replace the workforce-cost case for payroll-cost interpretation.

## Step-by-Step Walkthrough

### Step 1. Establish the workforce population and status baseline

Start with the employee population before testing exceptions. You need to know which cost centers, job families, job levels, and status groups exist before deciding whether an activity pattern is abnormal.

**What we are trying to achieve**

Build the baseline workforce view that shows how active and terminated employees are distributed across the organization.

**Why this step changes the diagnosis**

The audit does not start with exceptions. It starts with the population that later exception queries will test.

**Suggested query**

<QueryReference
  queryKey="managerial/29_headcount_by_cost_center_job_family_status.sql"
  helperText="Use this first to define the workforce population by cost center, job family, job level, and status."
/>

**What this query does**

It counts employees by cost center, job family, job level, and employment status, then adds pay-class counts, active-at-range-end counts, and average tenure.

**How it works**

The query joins `Employee` to `CostCenter`, groups the workforce attributes, and calculates active and tenure measures from the employee master.

**What to look for in the result**

- unique executive and finance roles that should not repeat
- terminated employees that remain in the master for traceability
- cost centers with heavy hourly or salaried concentration
- whether `IsActive` and `EmploymentStatus` need to be interpreted separately

### Step 2. Test post-termination downstream activity

Once the workforce baseline is clear, test whether terminated employees still appear in payroll, timekeeping, labor, purchasing, or journal approval activity after their termination date.

**What we are trying to achieve**

Separate valid historical employee retention from invalid post-termination transaction activity.

**Why this step changes the diagnosis**

Terminated employees should remain in the master table. The control issue begins when downstream activity continues after the termination date.

**Suggested query**

<QueryReference
  queryKey="audit/27_terminated_employee_activity_review.sql"
  helperText="Use this to find payroll, time, labor, purchasing, and journal activity after termination."
/>

**What this query does**

It surfaces post-termination payroll approvals, time-clock entries, labor entries, purchase-order approvals, and journal approvals.

**How it works**

The query builds a terminated-employee set from `Employee`, unions multiple downstream activity sources, and keeps only events dated after each employee's termination date.

**What to look for in the result**

- exception types that repeat for the same employee
- days after termination, especially long-running activity after departure
- whether exceptions concentrate in payroll, production labor, purchasing, or accounting approvals
- source records that need immediate owner follow-up

### Step 3. Isolate stale current-state ownership

Post-termination activity is one control question. Current-state ownership is another. A terminated or inactive employee can still be assigned as a manager or sales rep even if no transaction occurred after termination.

**What we are trying to achieve**

Identify active business assignments that still point to inactive or terminated employees.

**Why this step changes the diagnosis**

This step moves from transaction-date validity to current master-data ownership. The fix may be assignment cleanup rather than transaction reversal.

**Suggested query**

<QueryReference
  queryKey="audit/34_current_state_employee_assignment_review.sql"
  helperText="Use this to find current cost-center, warehouse, work-center, or customer ownership assigned to inactive employees."
/>

**What this query does**

It reviews current-state assignments on cost centers, warehouses, work centers, and customers where the assigned employee is inactive or terminated.

**How it works**

The query unions current assignment columns from multiple master-data tables, joins those assignments to `Employee`, and flags assignments tied to inactive or terminated employees.

**What to look for in the result**

- assignment tables with repeated stale ownership
- terminated employees still assigned to customer, warehouse, or work-center responsibility
- whether cleanup belongs to finance, operations, sales, or master-data ownership
- assignments that create approval or operational accountability risk even without a transaction exception

### Step 4. Test approval-role design and authority limits

After lifecycle and ownership are tested, move to approval design. The review needs to know who approves each document family and whether the approver's role and authority are appropriate.

**What we are trying to achieve**

Assess whether approvals concentrate in expected roles and whether approved amounts exceed authority limits.

**Why this step changes the diagnosis**

Approval risk is not only about employee status. Active employees can still approve documents outside their expected role family or above their authorization level.

**Suggested query**

<QueryReference
  queryKey="audit/28_approval_role_review_by_org_position.sql"
  helperText="Use this to summarize approval activity by document family and approver role."
/>

<QueryReference
  queryKey="audit/35_approval_authority_limit_review.sql"
  helperText="Use this to flag approval events outside expected role families or above authority limits."
/>

**What these queries do**

The first query summarizes approval activity by document type and approver role. The second query flags document-level approvals that exceed the approver's authority limit or fall outside the expected role family.

**How they work**

The role-review query unions approval activity across purchasing, credit, refund, journal, and payroll documents, then groups by approver job attributes. The authority-limit query builds the same approval universe at document level, joins approver metadata, compares document amounts to approval limits, and tests role-family expectations.

**What to look for in the result**

- document families with heavy approval concentration in a small role group
- same-person approval patterns that need explanation
- approvals above authority limit
- approvals performed by a role family that does not match the expected control owner

### Step 5. Close with workforce-control exception follow-up

Finish by testing whether the workforce-control layer reinforces the employee-master review. Scheduling after termination and overtime without proper approval turn the master-data issue into an operating-control issue.

**What we are trying to achieve**

Determine whether employee lifecycle and approval weaknesses also appear in roster and overtime controls.

**Why this step changes the diagnosis**

The audit closeout should prioritize the first control owner to act. Roster-after-termination exceptions point to scheduling cleanup; overtime exceptions point to attendance-control follow-up.

**Suggested query**

<QueryReference
  queryKey="audit/41_roster_after_termination_review.sql"
  helperText="Use this to find rostered days scheduled after an employee's termination date."
/>

<QueryReference
  queryKey="audit/38_overtime_without_approval_review.sql"
  helperText="Use this to find overtime entries missing approval or exceeding approved hours."
/>

**What these queries do**

The roster query identifies scheduled shifts after termination and shows whether worked time or punches also exist. The overtime query identifies time-clock entries with overtime that is missing approval or exceeds approved hours.

**How they work**

The roster query joins `EmployeeShiftRoster` to `Employee`, then adds time-clock and punch evidence where available. The overtime query joins `TimeClockEntry` to `OvertimeApproval`, `Employee`, and `WorkCenter`, then flags missing or insufficient approval support.

**What to look for in the result**

- rostered days after termination, especially where worked hours or punches exist
- overtime entries with no approval link
- overtime entries where approved hours are below recorded overtime
- whether the next follow-up should move into the attendance-control audit case

## Required Student Output

Submit a short case memo or notebook note with these four artifacts:

- Evidence summary: identify the key result rows, metrics, timing patterns, or exception families that changed your diagnosis.
- Accounting or business interpretation: explain what the evidence means for the process, accounting treatment, managerial decision, or control risk.
- Database explanation: name the source tables, row grain, join keys, or trace path that make the evidence defensible.
- Management or audit conclusion: state which driver, document path, or exception family should be followed up first and why.

## Optional Excel Follow-Through

1. Build one workforce baseline pivot by cost center, job family, job level, and employment status.
2. Add a post-termination activity tab that groups exceptions by employee, source table, and days after termination.
3. Add a current-state assignment tab that separates stale ownership by assignment table and assignment column.
4. Build one approval tab for role concentration and authority-limit exceptions by document family.
5. Finish with one workforce-control tab for roster-after-termination and overtime-approval exceptions, then write a short conclusion on the first follow-up owner.

## Wrap-Up Questions

- Accounting/process: Which finding most weakens trust in employee-master or approval-control design?
- Database/source evidence: Which employee status, assignment, approval, roster, or overtime source path proves the issue?
- Analytics judgment: Are exceptions driven more by lifecycle status, stale ownership, authority limits, or workforce-control behavior?
- Escalation/next step: Should the next action go to employee-master cleanup, approval review, attendance audit, or workforce-cost interpretation?

## Next Steps

- Read [Workforce Cost and Org-Control Case](workforce-cost-and-org-control-case.md) when you want the managerial and approval-concentration follow-through.
- Read [Attendance Control Audit Case](attendance-control-audit-case.md) when you want a deeper punch, absence, and overtime exception review.
- Read [Payroll](../../processes/payroll.md) when you want the operational and accounting path behind the same employee-control questions.
- Read [Audit Queries](../audit.md) for the wider workforce-control query set.
