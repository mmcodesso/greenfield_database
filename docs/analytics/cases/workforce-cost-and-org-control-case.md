---
title: Workforce Cost and Org-Control Case
description: Inquiry-led walkthrough for workforce mix, payroll cost concentration, approval design, and executive-role review.
sidebar_label: Workforce Cost Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# Workforce Cost and Org-Control Case

## Business Scenario

Leadership wants to understand where people cost sits, how workforce structure varies by location and cost center, and whether approval activity lines up with the intended organization design.

The review should not stop at payroll totals. A useful workforce-cost case needs to connect people cost to labor utilization, then test whether the control owners behind that workforce structure still look credible.

## The Problem to Solve

Leadership needs a workforce view that connects payroll concentration, labor utilization, executive role ownership, and approval design without treating those as separate discussions.

## What You Need to Develop

- A payroll-cost concentration view by cost center, job family, job level, and pay class.
- A work-location and labor-use view that connects headcount, payroll cost, approved time, and direct labor.
- A control-owner review for key executive and management roles.
- An approval-design interpretation that compares expected role families to actual approvers.
- A management-facing conclusion on whether the first action belongs in cost management, labor utilization, executive role ownership, or approval governance.

## Before You Start

- Main tables: `Employee`, `CostCenter`, `PayrollRegister`, `TimeClockEntry`, `LaborTimeEntry`, `PurchaseRequisition`, `PurchaseOrder`, `JournalEntry`
- Related report: [Payroll and Workforce](../reports/payroll-perspective.md)
- Related process page: [Payroll](../../processes/payroll.md)
- Related case: [Master Data and Workforce Audit Case](master-data-and-workforce-audit-case.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case explains workforce cost, labor utilization, and control ownership. Use the master-data workforce audit case when the question is employee-validity exceptions rather than cost and organization-control interpretation.

## Step-by-Step Walkthrough

### Step 1. Define payroll cost concentration

Start with the cost view. Before interpreting labor hours or approval ownership, identify where gross pay, employer taxes, benefits, and total people cost concentrate.

**What we are trying to achieve**

Measure payroll cost by cost center, job family, job level, and pay class.

**Why this step changes the diagnosis**

Payroll cost concentration tells management where the workforce-cost discussion should start. It also prevents later control findings from floating without cost context.

**Suggested query**

<QueryReference
  queryKey="financial/22_payroll_and_people_cost_mix_by_cost_center_job_family_level.sql"
  helperText="Use this first to rank people cost by cost center and workforce grouping."
/>

**What this query does**

It combines payroll-register totals with employee headcount context so students can compare cost concentration with workforce structure.

**How it works**

The query builds one aggregate from `PayrollRegister` joined to `Employee`, builds a second aggregate from the employee master, aligns both on cost center, job family, job level, and pay class, then reports gross pay, employer burden, total people cost, and headcount measures.

**What to look for in the result**

- cost centers with the largest total people cost
- job families or job levels that dominate payroll spend
- differences between active headcount and employees with payroll
- whether cost pressure is driven by gross pay, employer taxes, benefits, or mix

### Step 2. Add work-location labor and headcount interpretation

After the cost baseline is clear, move from accounting cost to workforce use. A high-cost group may be expected if it also carries a large share of approved hours or direct labor.

**What we are trying to achieve**

Compare headcount, payroll cost, approved clock hours, direct labor hours, and extended labor cost by work location, cost center, and job family.

**Why this step changes the diagnosis**

This step separates cost concentration from labor utilization. Management needs to know whether high people cost is tied to actual labor activity or to organization mix.

**Suggested query**

<QueryReference
  queryKey="managerial/34_labor_and_headcount_by_work_location_job_family_cost_center.sql"
  helperText="Use this to connect headcount and payroll cost to approved time and direct labor activity."
/>

**What this query does**

It compares workforce structure, payroll cost, approved time-clock hours, direct manufacturing labor hours, and extended labor cost on a work-location and cost-center grain.

**How it works**

The query builds separate aggregates for headcount, payroll cost, approved time, and labor cost, unions the dimension keys, and joins the aggregates back together so each workforce grouping can be read across multiple lenses.

**What to look for in the result**

- locations where payroll cost is high but approved or direct labor hours are low
- job families with heavy direct labor concentration
- cost centers where headcount and labor cost tell different stories
- whether labor utilization supports or challenges the payroll-cost ranking

### Step 3. Test executive and control-owner role uniqueness

Once the workforce and cost picture is visible, test whether key control-owner roles remain unique and credible.

**What we are trying to achieve**

Review whether core executive and control-owner roles are unique and whether those role holders appear in current-state assignments and approval activity.

**Why this step changes the diagnosis**

Workforce cost is a management question, but control ownership determines whether that workforce environment is governed. Duplicate or inactive key roles weaken the control story.

**Suggested query**

<QueryReference
  queryKey="audit/29_executive_role_uniqueness_and_control_assignment_review.sql"
  helperText="Use this to test whether key executive and control-owner roles are unique and active."
/>

**What this query does**

It reviews the CEO, CFO, Controller, Production Manager, and Accounting Manager roles, then shows current-state control assignments and approval activity for those role holders.

**How it works**

The query defines the key roles, identifies role holders from `Employee`, counts role holders by title, summarizes current assignments from cost centers, warehouses, and work centers, and summarizes approval events across operating and accounting documents.

**What to look for in the result**

- duplicate holders of a role that should be unique
- inactive or terminated employees holding key roles
- key roles with no current-state control assignments
- whether approval activity is aligned with the intended executive or finance owners

### Step 4. Evaluate expected approval role families

After key roles are reviewed, test the broader approval design. This step asks whether document families are approved by the role families management expects.

**What we are trying to achieve**

Compare expected approver role families to the observed role families and job titles approving key document types.

**Why this step changes the diagnosis**

Approval design can look credible even when cost concentration is high, or it can expose governance pressure that cost analysis alone cannot show.

**Suggested query**

<QueryReference
  queryKey="audit/32_approval_authority_review_by_expected_role_family.sql"
  helperText="Use this to compare actual approvers to expected role families by document type."
/>

**What this query does**

It summarizes approval counts by document type, observed approver job family, and observed approver job title, then flags observed role families outside the expected control-owner list.

**How it works**

The query unions approval activity across purchasing, invoice, credit, refund, journal, and payroll documents, joins approver metadata, defines expected role families by document type, and compares observed role families to that expectation.

**What to look for in the result**

- document types approved outside expected role families
- role families that approve more document types than expected
- approval volume concentrated outside finance or executive leadership
- whether the issue appears to be policy design or operational workaround

### Step 5. Finish with approval concentration by organization position

Close by looking at approval concentration and same-person approval patterns. This turns the approval-design view into a management-control conclusion.

**What we are trying to achieve**

Understand who is approving operational and accounting documents by role, level, authorization, and concentration.

**Why this step changes the diagnosis**

Expected role-family design is necessary but not sufficient. A role family can be appropriate while approval volume still concentrates in too few people or same-person approval patterns.

**Suggested query**

<QueryReference
  queryKey="audit/28_approval_role_review_by_org_position.sql"
  helperText="Use this to summarize approval concentration, distinct approvers, and same-person approvals by document family."
/>

**What this query does**

It summarizes approval counts, distinct approvers, same-person approval percentage, and approval date range by document family and approver role.

**How it works**

The query unions approval events across purchasing, credit, refund, journal, and payroll documents, joins each approver to `Employee`, and groups by document type and approver job attributes.

**What to look for in the result**

- document families with high approval volume in one role or title
- low distinct-approver counts where more distribution is expected
- high same-person approval percentages
- whether approval concentration is efficient ownership or a governance risk

## Required Student Output

Submit a short case memo or notebook note with these four artifacts:

- Evidence summary: identify the key result rows, metrics, timing patterns, or exception families that changed your diagnosis.
- Accounting or business interpretation: explain what the evidence means for the process, accounting treatment, managerial decision, or control risk.
- Database explanation: name the source tables, row grain, join keys, or trace path that make the evidence defensible.
- Management or audit conclusion: state which driver, document path, or exception family should be followed up first and why.

## Optional Excel Follow-Through

1. Build one payroll-cost pivot by cost center, job family, job level, and pay class.
2. Add a work-location tab that compares headcount, total people cost, approved clock hours, direct labor hours, and extended labor cost.
3. Add a key-role tab for executive role uniqueness, control assignments, and approval counts.
4. Build one approval-design tab that separates expected role-family exceptions by document type.
5. Finish with an approval-concentration tab and a short conclusion on whether the first action belongs in cost management, labor utilization, executive role ownership, or approval governance.

## Wrap-Up Questions

- Accounting/process: Which cost center, job family, or control-owner pattern changes the workforce-cost diagnosis most?
- Database/source evidence: Which payroll, headcount, work-location, executive-role, or approval-source grain supports the conclusion?
- Analytics judgment: Does labor utilization support the payroll-cost ranking, or does control design change the priority?
- Escalation/next step: Should management act first on cost concentration, labor utilization, executive-role design, or approval concentration?

## Next Steps

- Read [Payroll and Workforce](../reports/payroll-perspective.md) when you want the report-level perspective on payroll, labor support, and control review.
- Read [Payroll](../../processes/payroll.md) when you want the business-process view behind the same workforce and approval patterns.
- Read [Master Data and Workforce Audit Case](master-data-and-workforce-audit-case.md) when you want the audit follow-through on employee validity and ownership.
