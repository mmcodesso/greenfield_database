---
title: Audit Exception Lab
description: Guided audit lab focused on anomaly review and control testing in the published dataset.
sidebar_label: Audit Exception Lab
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# Audit Exception Lab


## Business Scenario

The finance and audit team receives the published five-year dataset with a moderate set of planted anomalies. This lab teaches students how to trace flagged exceptions to source documents, identify the related control, and explain the business risk in plain language. In class, you can narrow the review to one fiscal year with a filter when you want a smaller lab.

## Main Tables

- `PurchaseInvoice`
- `DisbursementPayment`
- `PayrollRegister`
- `PayrollPayment`
- `WorkOrder`
- `WorkOrderOperation`
- `WorkOrderOperationSchedule`
- `WorkCenter`
- `LaborTimeEntry`
- `TimeClockEntry`

## Recommended Query Sequence

1. Pick one payroll, AP, or manufacturing exception pattern from the query output.
2. Note the source document keys and affected periods.
3. Then work through the SQL sequence below.

<QuerySequence items={caseQuerySequences["audit-exception-lab"]} />

## Suggested Excel Sequence

1. Pick one AP exception, one payroll exception, and one manufacturing exception from the query output.
2. Use the source-document sheets to trace each exception.
3. Compare the workbook trace to the matching SQL result set.

## What Students Should Notice

- Several audit starter queries are intentionally written to surface the same anomaly family from different angles.
- The published dataset includes a moderate anomaly set that creates teachable results without turning the whole dataset into an exception dump.

## Follow-Up Questions

- Which planted anomalies represent timing issues versus approval issues versus linkage issues?
- Which audit queries surface the strongest exception evidence directly from source tables?
- How does a validation-only audit seed differ from an anomaly-log family in the way students should explain it?
- Which exception would you escalate first in a real audit discussion, and why?
