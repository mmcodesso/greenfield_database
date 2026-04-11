---
title: Audit Exception Lab
description: Guided audit lab focused on anomaly review and control testing in Greenfield.
sidebar_label: Audit Exception Lab
---

# Audit Exception Lab

**Audience:** Students and instructors using the anomaly-enabled build for controls and exception analysis.  
**Purpose:** Provide a guided lab that turns the `standard` anomaly build into a practical audit-review exercise.  
**What you will learn:** How to move from anomaly logs to source documents, how to interpret planted exceptions, and how to separate clean-process understanding from anomaly review.

## Business Scenario

The finance and audit team receives the standard five-year build with a moderate set of planted anomalies. The goal is not to find every issue from scratch. The goal is to learn how to trace flagged exceptions to source documents, understand which control they violate, and explain the business risk in plain language. In class, you can narrow the review to one fiscal year with a filter if you want a smaller lab.

## Recommended Build Mode

- standard anomaly-enabled teaching package

If you are preparing that package yourself, use [Dataset Delivery and Build Setup](/docs/technical/dataset-delivery).

## Main Tables and Worksheets

- `AnomalyLog`
- `ValidationSummary`
- `PurchaseInvoice`
- `DisbursementPayment`
- `PayrollRegister`
- `PayrollPayment`
- `WorkOrder`
- `WorkOrderOperation`
- `LaborTimeEntry`
- `TimeClockEntry`

## Recommended Query Sequence

1. Run [../../../queries/audit/22_anomaly_log_to_source_document_tie_out.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/22_anomaly_log_to_source_document_tie_out.sql).
2. Run [../../../queries/audit/05_duplicate_payment_reference_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/05_duplicate_payment_reference_review.sql).
3. Run [../../../queries/audit/11_payroll_control_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/11_payroll_control_review.sql).
4. Run [../../../queries/audit/14_missing_routing_or_operation_link_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/14_missing_routing_or_operation_link_review.sql).
5. Run [../../../queries/audit/15_operation_sequence_and_final_completion_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/15_operation_sequence_and_final_completion_review.sql).
6. Run [../../../queries/audit/19_time_clock_exceptions_by_employee_supervisor_work_center.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/19_time_clock_exceptions_by_employee_supervisor_work_center.sql).

## Suggested Excel Sequence

1. Open `AnomalyLog` and group by `anomaly_type`.
2. Pick one anomaly from AP, one from payroll, and one from manufacturing.
3. Use the source-document sheets to trace each exception.
4. Compare the workbook trace to the matching SQL result set.

## What Students Should Notice

- The anomaly log is a teaching aid, not a substitute for source-document review.
- Several audit starter queries are intentionally written to surface the same anomaly family from different angles.
- The `standard` profile is moderate on purpose; it should create teachable results without turning the whole dataset into an exception dump.

## Follow-Up Questions

- Which planted anomalies represent timing issues versus approval issues versus linkage issues?
- Which audit queries depend on the anomaly log, and which work directly from source tables?
- Which exception would you escalate first in a real audit discussion, and why?
