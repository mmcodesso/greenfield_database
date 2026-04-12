---
title: Audit Analytics
description: Starter auditing and controls analytics paths using the Greenfield dataset.
sidebar_label: Audit Analytics
---

# Audit Analytics Starter Guide

## Relevant Tables

| Topic | Main tables |
|---|---|
| O2C and P2P completeness | O2C and P2P header and line tables plus `CashReceiptApplication` |
| Approvals and segregation of duties | `PurchaseRequisition`, `PurchaseOrder`, `PurchaseInvoice`, `JournalEntry`, `CreditMemo`, `CustomerRefund`, `PayrollRegister`, `Employee` |
| Manufacturing controls | `Item`, `BillOfMaterial`, `Routing`, `WorkCenter`, `WorkOrder`, `WorkOrderOperation`, `WorkOrderOperationSchedule`, `MaterialIssueLine`, `ProductionCompletionLine`, `WorkOrderClose` |
| Payroll and time controls | `ShiftDefinition`, `EmployeeShiftAssignment`, `TimeClockEntry`, `AttendanceException`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollPayment`, `PayrollLiabilityRemittance`, `Employee` |
| Master-data controls | `Employee`, `Item`, plus operational tables that reuse those masters |
| Support-workbook-assisted review | `greenfield_support.xlsx` sheets `AnomalyLog`, `ValidationStages`, `ValidationChecks`, and `ValidationExceptions` |

## Starter SQL Map

| Topic | Starter SQL file |
|---|---|
| O2C completeness | [01_o2c_document_chain_completeness.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/01_o2c_document_chain_completeness.sql) |
| P2P completeness | [02_p2p_document_chain_completeness.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/02_p2p_document_chain_completeness.sql) |
| Approval and SOD review | [03_approval_and_sod_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/03_approval_and_sod_review.sql) |
| Cut-off and timing | [04_cutoff_and_timing_analysis.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/04_cutoff_and_timing_analysis.sql) |
| Duplicate review | [05_duplicate_payment_reference_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/05_duplicate_payment_reference_review.sql) |
| Potential anomaly review | [06_potential_anomaly_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/06_potential_anomaly_review.sql) |
| Backorder and return review | [07_backorder_and_return_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/07_backorder_and_return_review.sql) |
| BOM and supply-mode conflicts | [08_missing_bom_or_supply_mode_conflict.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/08_missing_bom_or_supply_mode_conflict.sql) |
| Over-issue and open WIP review | [09_over_issue_and_open_wip_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/09_over_issue_and_open_wip_review.sql) |
| Work-order close timing | [10_work_order_close_timing_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/10_work_order_close_timing_review.sql) |
| Payroll control review | [11_payroll_control_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/11_payroll_control_review.sql) |
| Labor-time-after-close and paid-without-time review | [12_labor_time_after_close_and_paid_without_time.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/12_labor_time_after_close_and_paid_without_time.sql) |
| Over and under accrual review | [13_over_under_accrual_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/13_over_under_accrual_review.sql) |
| Missing routing or operation-link review | [14_missing_routing_or_operation_link_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/14_missing_routing_or_operation_link_review.sql) |
| Operation sequence and final-completion review | [15_operation_sequence_and_final_completion_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/15_operation_sequence_and_final_completion_review.sql) |
| Schedule on non-working day review | [16_schedule_on_nonworking_day_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/16_schedule_on_nonworking_day_review.sql) |
| Over-capacity day review | [17_over_capacity_day_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/17_over_capacity_day_review.sql) |
| Completion before scheduled operation end review | [18_completion_before_scheduled_operation_end.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/18_completion_before_scheduled_operation_end.sql) |
| Time-clock exceptions by employee, supervisor, and work center | [19_time_clock_exceptions_by_employee_supervisor_work_center.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/19_time_clock_exceptions_by_employee_supervisor_work_center.sql) |
| Labor outside scheduled operation window review | [20_labor_outside_scheduled_operation_window_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/20_labor_outside_scheduled_operation_window_review.sql) |
| Paid-without-clock and clock-without-pay review | [21_paid_without_clock_and_clock_without_pay_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/21_paid_without_clock_and_clock_without_pay_review.sql) |
| Accrued-service settlement exception review | [23_accrued_service_settlement_exception_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/23_accrued_service_settlement_exception_review.sql) |
| Customer deposits and unapplied cash exception review | [24_customer_deposits_and_unapplied_cash_exception_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/24_customer_deposits_and_unapplied_cash_exception_review.sql) |
| Time-clock, payroll, and labor bridge review | [25_time_clock_payroll_labor_bridge_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/25_time_clock_payroll_labor_bridge_review.sql) |
| Duplicate AP reference detail review | [26_duplicate_ap_reference_detail_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/26_duplicate_ap_reference_detail_review.sql) |
| Terminated-employee activity review | [27_terminated_employee_activity_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/27_terminated_employee_activity_review.sql) |
| Approval-role review by organization position | [28_approval_role_review_by_org_position.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/28_approval_role_review_by_org_position.sql) |
| Executive-role uniqueness and control-assignment review | [29_executive_role_uniqueness_and_control_assignment_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/29_executive_role_uniqueness_and_control_assignment_review.sql) |
| Item-master completeness review | [30_item_master_completeness_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/30_item_master_completeness_review.sql) |
| Discontinued or pre-launch item activity review | [31_discontinued_or_prelaunch_item_activity_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/31_discontinued_or_prelaunch_item_activity_review.sql) |
| Approval-authority review by expected role family | [32_approval_authority_review_by_expected_role_family.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/32_approval_authority_review_by_expected_role_family.sql) |
| Terminated-employee activity rollup by process area | [33_terminated_employee_activity_rollup_by_process_area.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/33_terminated_employee_activity_rollup_by_process_area.sql) |

## Baseline Control Queries

Use these first when you want control logic without relying on planted anomalies:

- O2C and P2P completeness
- approval-role review by organization position
- executive-role uniqueness and control-assignment review
- approval-authority review by expected role family

## Anomaly-Oriented Queries

Use these when you want the default anomaly-enabled build to surface teachable exceptions:

- duplicate payment or AP reference review
- payroll control review
- routing and operation-link review
- time-clock and labor exception review
- terminated-employee activity review
- item-master completeness review
- discontinued or pre-launch item activity review

## Support-Workbook-Assisted Review

Use the support workbook when you want a quicker triage path:

- `AnomalyLog` for planted anomaly families and source keys
- `ValidationStages` for stage-level exception counts
- `ValidationChecks` for section-level control counts
- `ValidationExceptions` for flattened exception detail

Pair those sheets with [Audit Review Pack Case](cases/audit-review-pack-case.md) or [Audit Exception Lab](cases/audit-exception-lab.md).

## Interpretation Notes

- A clean build with `anomaly_mode: none` may return few or no rows from anomaly-oriented queries.
- The default `standard` build is better for controls teaching because anomalies are present while the GL remains balanced.
- Employee-master review should distinguish current-state `IsActive` from historical validity driven by `HireDate` and `TerminationDate`.
- Item-master review should distinguish current-state lifecycle and launch-date logic from operational usage timing.
- Support-workbook review should accelerate tracing, not replace source-document review.

## Anomaly Coverage Matrix

| Query | Best build mode | Expected anomaly types | Main tables |
|---|---|---|---|
| [05_duplicate_payment_reference_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/05_duplicate_payment_reference_review.sql) | `standard` | `duplicate_vendor_payment_reference`, `duplicate_supplier_invoice_number` | `DisbursementPayment`, `PurchaseInvoice`, `Supplier` |
| [06_potential_anomaly_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/06_potential_anomaly_review.sql) | `standard` | `weekend_journal_entry`, `same_creator_approver`, `same_creator_approver_journal`, `missing_approval`, `invoice_before_shipment`, `duplicate_vendor_payment_reference` | `JournalEntry`, `PurchaseOrder`, `PurchaseRequisition`, `SalesInvoice`, `DisbursementPayment` |
| [11_payroll_control_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/11_payroll_control_review.sql) | `standard` | `missing_payroll_payment`, `payroll_payment_before_approval` | `PayrollRegister`, `PayrollPayment`, `PayrollPeriod`, `Employee` |
| [12_labor_time_after_close_and_paid_without_time.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/12_labor_time_after_close_and_paid_without_time.sql) | `standard` | `labor_after_operation_close`, `paid_without_clock` | `LaborTimeEntry`, `TimeClockEntry`, `PayrollRegisterLine` |
| [14_missing_routing_or_operation_link_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/14_missing_routing_or_operation_link_review.sql) | `standard` | `missing_work_order_operations`, `invalid_direct_labor_operation_link` | `WorkOrder`, `WorkOrderOperation`, `LaborTimeEntry`, `Item` |
| [15_operation_sequence_and_final_completion_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/15_operation_sequence_and_final_completion_review.sql) | `standard` | `overlapping_operation_sequence`, `completion_before_operation_end` | `WorkOrderOperation`, `ProductionCompletion` |
| [16_schedule_on_nonworking_day_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/16_schedule_on_nonworking_day_review.sql) | `standard` | `scheduled_on_nonworking_day` | `WorkOrderOperationSchedule`, `WorkCenterCalendar` |
| [17_over_capacity_day_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/17_over_capacity_day_review.sql) | `standard` | `overbooked_work_center_day` | `WorkOrderOperationSchedule`, `WorkCenterCalendar` |
| [18_completion_before_scheduled_operation_end.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/18_completion_before_scheduled_operation_end.sql) | `standard` | `completion_before_operation_end` | `ProductionCompletion`, `WorkOrderOperation` |
| [19_time_clock_exceptions_by_employee_supervisor_work_center.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/19_time_clock_exceptions_by_employee_supervisor_work_center.sql) | `standard` | `missing_clock_out`, `duplicate_time_clock_day`, `off_shift_clocking` | `AttendanceException`, `TimeClockEntry`, `ShiftDefinition`, `WorkCenter` |
| [20_labor_outside_scheduled_operation_window_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/20_labor_outside_scheduled_operation_window_review.sql) | `standard` | `labor_after_operation_close` | `LaborTimeEntry`, `TimeClockEntry`, `WorkOrderOperation` |
| [21_paid_without_clock_and_clock_without_pay_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/21_paid_without_clock_and_clock_without_pay_review.sql) | `standard` | `paid_without_clock`, `missing_clock_out` | `PayrollRegisterLine`, `LaborTimeEntry`, `TimeClockEntry` |
| [25_time_clock_payroll_labor_bridge_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/25_time_clock_payroll_labor_bridge_review.sql) | `standard` | `paid_without_clock`, `missing_clock_out`, `labor_after_operation_close` | `TimeClockEntry`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine` |
| [26_duplicate_ap_reference_detail_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/26_duplicate_ap_reference_detail_review.sql) | `standard` | `duplicate_vendor_payment_reference`, `duplicate_supplier_invoice_number` | `PurchaseInvoice`, `DisbursementPayment`, `Supplier` |
| [27_terminated_employee_activity_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/27_terminated_employee_activity_review.sql) | `standard` | `terminated_employee_on_payroll`, `terminated_employee_approval`, `inactive_employee_time_or_labor` | `Employee`, `PayrollRegister`, `TimeClockEntry`, `LaborTimeEntry`, `PurchaseOrder`, `JournalEntry` |
| [29_executive_role_uniqueness_and_control_assignment_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/29_executive_role_uniqueness_and_control_assignment_review.sql) | `standard` | `duplicate_executive_title_assignment` | `Employee`, `CostCenter`, `Warehouse`, `WorkCenter`, approval tables |
| [30_item_master_completeness_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/30_item_master_completeness_review.sql) | `standard` | `missing_item_catalog_attribute` | `Item` |
| [31_discontinued_or_prelaunch_item_activity_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/31_discontinued_or_prelaunch_item_activity_review.sql) | `standard` | `discontinued_item_in_new_activity` | `Item`, `SalesOrderLine`, `PurchaseOrderLine`, `WorkOrder`, `ShipmentLine`, `SalesInvoiceLine` |
| [33_terminated_employee_activity_rollup_by_process_area.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/33_terminated_employee_activity_rollup_by_process_area.sql) | `standard` | `terminated_employee_on_payroll`, `terminated_employee_approval`, `inactive_employee_time_or_labor` | `Employee`, `PayrollRegister`, `TimeClockEntry`, `LaborTimeEntry`, approval tables |
