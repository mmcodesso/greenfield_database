---
title: Audit Review Pack Case
description: Guided walkthrough for an audit review pack that uses the support workbook and the expanded workforce, approval, and master-data audit queries.
sidebar_label: Audit Review Pack
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

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
2. Then work through the SQL sequence below.

<QuerySequence items={caseQuerySequences["audit-review-pack-case"]} />

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
