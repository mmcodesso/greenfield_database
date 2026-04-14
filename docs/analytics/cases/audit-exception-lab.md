---
title: Audit Exception Lab
description: Guided audit lab focused on anomaly review and control testing in Greenfield.
sidebar_label: Audit Exception Lab
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# Audit Exception Lab


## Business Scenario

The finance and audit team receives the published five-year dataset with a moderate set of planted anomalies. This lab teaches students how to trace flagged exceptions to source documents, identify the related control, and explain the business risk in plain language. In class, you can narrow the review to one fiscal year with a filter when you want a smaller lab.

Use `greenfield_support.xlsx` with the published dataset. If you are preparing the files yourself, use [Customize](../../technical/dataset-delivery.md).

## Main Tables and Worksheets

- `greenfield_support.xlsx`
- `AnomalyLog`
- `ValidationStages`
- `ValidationChecks`
- `ValidationExceptions`
- `PurchaseInvoice`
- `DisbursementPayment`
- `PayrollRegister`
- `PayrollPayment`
- `WorkOrder`
- `WorkOrderOperation`
- `LaborTimeEntry`
- `TimeClockEntry`

## Recommended Query Sequence

1. Open `greenfield_support.xlsx` and review `AnomalyLog`.
2. Pick one anomaly row and note the source document keys shown in the workbook.
3. Then work through the SQL sequence below.

<QuerySequence items={caseQuerySequences["audit-exception-lab"]} />

## Suggested Excel Sequence

1. Open `greenfield_support.xlsx`.
2. Open `AnomalyLog` and group by `anomaly_type`.
3. Pick one anomaly from AP, one from payroll, and one from manufacturing.
4. Use the source-document sheets to trace each exception.
5. Compare the workbook trace to the matching SQL result set.

## What Students Should Notice

- The anomaly log is a teaching aid, not a substitute for source-document review.
- Several audit starter queries are intentionally written to surface the same anomaly family from different angles.
- The published dataset includes a moderate anomaly set that creates teachable results without turning the whole dataset into an exception dump.

## Follow-Up Questions

- Which planted anomalies represent timing issues versus approval issues versus linkage issues?
- Which audit queries depend on the anomaly log, and which work directly from source tables?
- Which exception would you escalate first in a real audit discussion, and why?
