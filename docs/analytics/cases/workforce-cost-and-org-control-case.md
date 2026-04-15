---
title: Workforce Cost and Org-Control Case
description: Guided walkthrough for workforce mix, payroll cost concentration, approval design, and executive-role review.
sidebar_label: Workforce Cost Case
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# Workforce Cost and Org-Control Case

## Audience and Purpose

Use this case when students need to connect people-cost analysis to workforce structure and approval design.

## Business Scenario

Leadership wants to understand where people cost sits, how workforce structure varies by location and cost center, and whether approval activity lines up with the intended organization design.

## Main Tables and Worksheets

- `Employee`
- `CostCenter`
- `PayrollRegister`
- `TimeClockEntry`
- `LaborTimeEntry`
- `PurchaseRequisition`
- `PurchaseOrder`
- `JournalEntry`
- <FileName type="support" />:
  - `AnomalyLog`
  - `ValidationChecks`

## Recommended Query Sequence

<QuerySequence items={caseQuerySequences["workforce-cost-and-org-control-case"]} />

## Suggested Excel Sequence

1. Pivot `Employee` by `WorkLocation`, `JobFamily`, `JobLevel`, and `EmploymentStatus`.
2. Add payroll totals by cost center and pay class.
3. Compare approval concentration to the intended control-owner roles.

## What Students Should Notice

- Workforce structure is easier to interpret now that executive roles are unique and frontline roles repeat only where that makes sense.
- People-cost concentration and approval concentration are related but not identical.
- Work location and cost center answer different managerial questions.
- The published dataset provides reviewable control patterns for cost and organization analysis.

## Follow-Up Questions

- Which job families drive the most payroll cost?
- Which approvals would you expect to be concentrated in finance roles?
- When does a concentrated approval pattern look efficient, and when does it look risky?
