---
title: Audit Review Pack Case
description: Guided walkthrough for an audit review pack that uses the expanded workforce, approval, and master-data audit queries.
sidebar_label: Audit Review Pack
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# Audit Review Pack Case

## Audience and Purpose

Use this case when students need a structured audit lab that combines source-table SQL review with follow-up tracing.

## Business Scenario

The internal-audit team receives the normal five-year package and needs to triage control issues quickly. The job is not to prove every issue from scratch. The job is to use the audit starter queries and the source tables together so the team can explain what happened, where it happened, and why it matters.

## Main Tables

- `Employee`
- `Item`
- `PurchaseInvoice`
- `DisbursementPayment`
- `PayrollRegister`
- `WorkOrder`

## Recommended Query Sequence

Work through the SQL sequence below, then trace the flagged rows back into the source tables.

<QuerySequence items={caseQuerySequences["audit-review-pack-case"]} />

## Suggested Excel Sequence

1. Trace one workforce anomaly, one item-master anomaly, and one approval anomaly back into the dataset workbook or SQLite query results.
2. Write a short plain-language explanation of the control failure and the business risk.

## What Students Should Notice

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
