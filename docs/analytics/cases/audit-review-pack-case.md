---
title: Audit Review Pack Case
description: Guided walkthrough for an audit review pack that uses the expanded workforce, approval, and master-data audit queries.
sidebar_label: Audit Review Pack
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# Audit Review Pack Case

This case works as a broad audit triage exercise rather than a single-process walkthrough. It gives students a way to move from flagged query results into source evidence, compare different anomaly families, and explain what kind of control problem they are actually seeing.

## Business Scenario

The internal-audit team receives the normal three-year package covering fiscal years 2024 through 2026 and needs to triage control issues quickly. The job is not to prove every issue from scratch. The job is to use the audit starter queries and the source tables together so the team can explain what happened, where it happened, and what it means.

## The Problem to Solve

The review team needs to separate master-data issues, approval issues, workforce-control failures, and operational exceptions without treating every flagged row as the same kind of risk.

## Key Data Sources

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

## Next Steps

- Read [Audit Analytics](../audit.md) when you want the broader audit query library around these anomaly families.
- Read [Schema Reference](../../reference/schema.md) when you need the table bridges behind a flagged exception.
- Read [Audit Exception Lab](audit-exception-lab.md) when you want a narrower anomaly-tracing exercise.
