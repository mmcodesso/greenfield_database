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
| Payroll and time controls | `ShiftDefinition`, `EmployeeShiftAssignment`, `EmployeeShiftRoster`, `EmployeeAbsence`, `OvertimeApproval`, `TimeClockPunch`, `TimeClockEntry`, `AttendanceException`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollPayment`, `PayrollLiabilityRemittance`, `Employee` |
| Master-data controls | `Employee`, `Item`, `PriceList`, `PriceListLine`, `PromotionProgram`, `PriceOverrideApproval`, plus operational tables that reuse those masters |
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
| Current-state employee assignment review | [34_current_state_employee_assignment_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/34_current_state_employee_assignment_review.sql) |
| Approval authority-limit review | [35_approval_authority_limit_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/35_approval_authority_limit_review.sql) |
| Item status alignment review | [36_item_status_alignment_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/36_item_status_alignment_review.sql) |
| Scheduled-without-punch and punch-without-schedule review | [37_scheduled_without_punch_and_punch_without_schedule_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/37_scheduled_without_punch_and_punch_without_schedule_review.sql) |
| Overtime without approval review | [38_overtime_without_approval_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/38_overtime_without_approval_review.sql) |
| Absence with worked time review | [39_absence_with_worked_time_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/39_absence_with_worked_time_review.sql) |
| Overlapping or incomplete punch review | [40_overlapping_or_incomplete_punch_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/40_overlapping_or_incomplete_punch_review.sql) |
| Roster after termination review | [41_roster_after_termination_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/41_roster_after_termination_review.sql) |
| Forecast approval and override review | [42_forecast_approval_and_override_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/42_forecast_approval_and_override_review.sql) |
| Inactive or stale inventory policy review | [43_inactive_or_stale_inventory_policy_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/43_inactive_or_stale_inventory_policy_review.sql) |
| Requisitions and work orders without planning support | [44_requisitions_and_work_orders_without_planning_support.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/44_requisitions_and_work_orders_without_planning_support.sql) |
| Recommendation converted after need-by date review | [45_recommendation_converted_after_need_by_date_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/45_recommendation_converted_after_need_by_date_review.sql) |
| Discontinued or pre-launch planning activity review | [46_discontinued_or_prelaunch_planning_activity_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/46_discontinued_or_prelaunch_planning_activity_review.sql) |
| Sales below floor without approval | [47_sales_below_floor_without_approval.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/47_sales_below_floor_without_approval.sql) |
| Expired or overlapping price-list review | [48_expired_or_overlapping_price_list_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/48_expired_or_overlapping_price_list_review.sql) |
| Promotion scope and date mismatch review | [49_promotion_scope_and_date_mismatch_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/49_promotion_scope_and_date_mismatch_review.sql) |
| Customer-specific price-list bypass review | [50_customer_specific_price_list_bypass_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/50_customer_specific_price_list_bypass_review.sql) |
| Override approval completeness review | [51_override_approval_completeness_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/51_override_approval_completeness_review.sql) |

## Baseline Control Queries

Use these first when you want control logic without relying on planted anomalies:

- O2C and P2P completeness
- approval-role review by organization position
- executive-role uniqueness and control-assignment review
- approval-authority review by expected role family

## Exception-Oriented Queries

Use these when you want students to review the exception patterns present in the published dataset:

- duplicate payment or AP reference review
- payroll control review
- routing and operation-link review
- time-clock and labor exception review
- roster, punch, absence, and overtime-approval review
- terminated-employee activity review
- item-master completeness review
- discontinued or pre-launch item activity review
- current-state employee assignment review
- approval authority-limit review
- item status alignment review
- forecast approval and override review
- inactive or stale inventory policy review
- requisitions and work orders without planning support
- recommendation converted after need-by date review
- discontinued or pre-launch planning activity review
- sales below floor without approval
- expired or overlapping price-list review
- promotion scope and date mismatch review
- customer-specific price-list bypass review
- override approval completeness review

## Support-Workbook-Assisted Review

Use the support workbook when you want a quicker triage path:

- `AnomalyLog` for planted anomaly families and source keys
- `ValidationStages` for stage-level exception counts
- `ValidationChecks` for section-level control counts
- `ValidationExceptions` for flattened exception detail

Pair those sheets with [Audit Review Pack Case](cases/audit-review-pack-case.md) or [Audit Exception Lab](cases/audit-exception-lab.md).

## Interpretation Notes

- Exception-oriented queries are designed to return reviewable control patterns from the published dataset.
- The GL remains balanced even when the support workbook and audit queries identify exceptions.
- Employee-master review should distinguish current-state `IsActive` from historical validity driven by `HireDate` and `TerminationDate`.
- Item-master review should distinguish current-state lifecycle and launch-date logic from operational usage timing.
- Pricing-control review should distinguish price-list master-data failures from transaction-level override and promotion-use failures.
- Support-workbook review should accelerate tracing, not replace source-document review.

## Anomaly Coverage Matrix

| Query | Recommended use | Expected anomaly types | Main tables |
|---|---|---|---|
| [05_duplicate_payment_reference_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/05_duplicate_payment_reference_review.sql) | AP payment review | `duplicate_vendor_payment_reference`, `duplicate_supplier_invoice_number` | `DisbursementPayment`, `PurchaseInvoice`, `Supplier` |
| [06_potential_anomaly_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/06_potential_anomaly_review.sql) | broad control screening | `weekend_journal_entry`, `same_creator_approver`, `same_creator_approver_journal`, `missing_approval`, `invoice_before_shipment`, `duplicate_vendor_payment_reference` | `JournalEntry`, `PurchaseOrder`, `PurchaseRequisition`, `SalesInvoice`, `DisbursementPayment` |
| [11_payroll_control_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/11_payroll_control_review.sql) | payroll settlement review | `missing_payroll_payment`, `payroll_payment_before_approval` | `PayrollRegister`, `PayrollPayment`, `PayrollPeriod`, `Employee` |
| [12_labor_time_after_close_and_paid_without_time.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/12_labor_time_after_close_and_paid_without_time.sql) | labor support review | `labor_after_operation_close`, `paid_without_clock` | `LaborTimeEntry`, `TimeClockEntry`, `PayrollRegisterLine` |
| [14_missing_routing_or_operation_link_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/14_missing_routing_or_operation_link_review.sql) | manufacturing linkage review | `missing_work_order_operations`, `invalid_direct_labor_operation_link` | `WorkOrder`, `WorkOrderOperation`, `LaborTimeEntry`, `Item` |
| [15_operation_sequence_and_final_completion_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/15_operation_sequence_and_final_completion_review.sql) | operation sequence review | `overlapping_operation_sequence`, `completion_before_operation_end` | `WorkOrderOperation`, `ProductionCompletion` |
| [16_schedule_on_nonworking_day_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/16_schedule_on_nonworking_day_review.sql) | capacity-calendar review | `scheduled_on_nonworking_day` | `WorkOrderOperationSchedule`, `WorkCenterCalendar` |
| [17_over_capacity_day_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/17_over_capacity_day_review.sql) | capacity review | `overbooked_work_center_day` | `WorkOrderOperationSchedule`, `WorkCenterCalendar` |
| [18_completion_before_scheduled_operation_end.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/18_completion_before_scheduled_operation_end.sql) | schedule-completion review | `completion_before_operation_end` | `ProductionCompletion`, `WorkOrderOperation` |
| [19_time_clock_exceptions_by_employee_supervisor_work_center.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/19_time_clock_exceptions_by_employee_supervisor_work_center.sql) | attendance exception review | `missing_clock_out`, `duplicate_time_clock_day`, `off_shift_clocking` | `AttendanceException`, `TimeClockEntry`, `ShiftDefinition`, `WorkCenter` |
| [20_labor_outside_scheduled_operation_window_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/20_labor_outside_scheduled_operation_window_review.sql) | labor timing review | `labor_after_operation_close` | `LaborTimeEntry`, `TimeClockEntry`, `WorkOrderOperation` |
| [21_paid_without_clock_and_clock_without_pay_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/21_paid_without_clock_and_clock_without_pay_review.sql) | payroll-time reconciliation | `paid_without_clock`, `missing_clock_out` | `PayrollRegisterLine`, `LaborTimeEntry`, `TimeClockEntry` |
| [25_time_clock_payroll_labor_bridge_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/25_time_clock_payroll_labor_bridge_review.sql) | workforce bridge review | `paid_without_clock`, `missing_clock_out`, `labor_after_operation_close` | `TimeClockEntry`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine` |
| [26_duplicate_ap_reference_detail_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/26_duplicate_ap_reference_detail_review.sql) | AP duplicate-reference review | `duplicate_vendor_payment_reference`, `duplicate_supplier_invoice_number` | `PurchaseInvoice`, `DisbursementPayment`, `Supplier` |
| [27_terminated_employee_activity_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/27_terminated_employee_activity_review.sql) | employment validity review | `terminated_employee_on_payroll`, `terminated_employee_approval`, `inactive_employee_time_or_labor` | `Employee`, `PayrollRegister`, `TimeClockEntry`, `LaborTimeEntry`, `PurchaseOrder`, `JournalEntry` |
| [29_executive_role_uniqueness_and_control_assignment_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/29_executive_role_uniqueness_and_control_assignment_review.sql) | executive-role review | `duplicate_executive_title_assignment` | `Employee`, `CostCenter`, `Warehouse`, `WorkCenter`, approval tables |
| [30_item_master_completeness_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/30_item_master_completeness_review.sql) | item-master completeness review | `missing_item_catalog_attribute` | `Item` |
| [31_discontinued_or_prelaunch_item_activity_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/31_discontinued_or_prelaunch_item_activity_review.sql) | item-lifecycle review | `discontinued_item_in_new_activity`, `prelaunch_item_in_new_activity` | `Item`, `SalesOrderLine`, `PurchaseOrderLine`, `WorkOrder`, `ShipmentLine`, `SalesInvoiceLine` |
| [32_approval_authority_review_by_expected_role_family.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/32_approval_authority_review_by_expected_role_family.sql) | approval-role review | `unexpected_role_family_approval` | approval tables, `Employee` |
| [33_terminated_employee_activity_rollup_by_process_area.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/33_terminated_employee_activity_rollup_by_process_area.sql) | employment rollup review | `terminated_employee_on_payroll`, `terminated_employee_approval`, `inactive_employee_time_or_labor` | `Employee`, `PayrollRegister`, `TimeClockEntry`, `LaborTimeEntry`, approval tables |
| [34_current_state_employee_assignment_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/34_current_state_employee_assignment_review.sql) | assignment ownership review | `inactive_employee_current_assignment` | `CostCenter`, `Warehouse`, `WorkCenter`, `Customer`, `Employee` |
| [35_approval_authority_limit_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/35_approval_authority_limit_review.sql) | authority-limit review | `approval_above_authority_limit`, `unexpected_role_family_approval` | `PurchaseOrder`, `PurchaseInvoice`, `CreditMemo`, `CustomerRefund`, `JournalEntry`, `PayrollRegister`, `Employee` |
| [36_item_status_alignment_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/36_item_status_alignment_review.sql) | item-status alignment review | `item_status_alignment_conflict` | `Item` |
| [37_scheduled_without_punch_and_punch_without_schedule_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/37_scheduled_without_punch_and_punch_without_schedule_review.sql) | roster-punch review | `punch_without_roster`, `missing_final_punch` | `EmployeeShiftRoster`, `TimeClockEntry`, `TimeClockPunch`, `Employee` |
| [38_overtime_without_approval_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/38_overtime_without_approval_review.sql) | overtime approval review | `overtime_without_approval` | `TimeClockEntry`, `OvertimeApproval`, `Employee`, `WorkCenter` |
| [39_absence_with_worked_time_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/39_absence_with_worked_time_review.sql) | absence-time conflict review | `absence_with_worked_time` | `EmployeeAbsence`, `EmployeeShiftRoster`, `TimeClockEntry`, `TimeClockPunch` |
| [40_overlapping_or_incomplete_punch_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/40_overlapping_or_incomplete_punch_review.sql) | punch-sequence review | `missing_final_punch`, `overlapping_punch_sequence` | `TimeClockPunch`, `TimeClockEntry`, `Employee` |
| [41_roster_after_termination_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/41_roster_after_termination_review.sql) | post-termination roster review | `roster_after_termination` | `EmployeeShiftRoster`, `Employee`, `TimeClockEntry`, `TimeClockPunch` |
| [42_forecast_approval_and_override_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/42_forecast_approval_and_override_review.sql) | forecast-governance review | `missing_forecast_approval`, `forecast_override_outlier` | `DemandForecast`, `Item`, `Employee` |
| [43_inactive_or_stale_inventory_policy_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/43_inactive_or_stale_inventory_policy_review.sql) | inventory-policy review | `inactive_policy_for_active_item` | `InventoryPolicy`, `Item`, `Warehouse`, `Employee` |
| [44_requisitions_and_work_orders_without_planning_support.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/44_requisitions_and_work_orders_without_planning_support.sql) | planning-support review | `purchase_requisition_without_plan`, `work_order_without_plan` | `PurchaseRequisition`, `WorkOrder`, `SupplyPlanRecommendation`, `Item` |
| [45_recommendation_converted_after_need_by_date_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/45_recommendation_converted_after_need_by_date_review.sql) | recommendation-timing review | `late_recommendation_conversion` | `SupplyPlanRecommendation`, `PurchaseRequisition`, `WorkOrder`, `Item` |
| [46_discontinued_or_prelaunch_planning_activity_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/46_discontinued_or_prelaunch_planning_activity_review.sql) | planning-lifecycle review | `inactive_policy_for_active_item`, `missing_forecast_approval`, `forecast_override_outlier`, `late_recommendation_conversion` | `DemandForecast`, `InventoryPolicy`, `SupplyPlanRecommendation`, `PurchaseRequisition`, `WorkOrder`, `Item` |
| [47_sales_below_floor_without_approval.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/47_sales_below_floor_without_approval.sql) | price-floor review | `sale_below_price_floor_without_approval`, `missing_price_override_approval` | `SalesOrderLine`, `SalesOrder`, `PriceListLine`, `PriceOverrideApproval`, `Customer`, `Item` |
| [48_expired_or_overlapping_price_list_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/48_expired_or_overlapping_price_list_review.sql) | price-list validity review | `expired_price_list_used`, `overlapping_active_price_list` | `PriceList`, `PriceListLine`, `SalesOrderLine`, `Customer`, `Item` |
| [49_promotion_scope_and_date_mismatch_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/49_promotion_scope_and_date_mismatch_review.sql) | promotion-scope review | `promotion_outside_effective_dates` | `PromotionProgram`, `SalesOrderLine`, `SalesOrder`, `Customer`, `Item` |
| [50_customer_specific_price_list_bypass_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/50_customer_specific_price_list_bypass_review.sql) | customer-price review | `customer_specific_price_bypass` | `SalesOrderLine`, `PriceList`, `PriceListLine`, `Customer`, `Item` |
| [51_override_approval_completeness_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/audit/51_override_approval_completeness_review.sql) | override-approval review | `missing_price_override_approval`, `sale_below_price_floor_without_approval` | `PriceOverrideApproval`, `SalesOrderLine`, `PriceListLine`, `Customer`, `Employee` |
