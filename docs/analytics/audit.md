# Audit Analytics Starter Guide

**Audience:** Students, instructors, and analysts using the dataset for controls, exception review, and process-traceability work.  
**Purpose:** Show how to use the dataset for document-chain testing, approval review, cut-off analysis, duplicate detection, manufacturing-control exercises, and payroll-control review.  
**What you will learn:** Which document links matter most and which audit-oriented SQL files to run first.

> **Implemented in current generator:** O2C, P2P, manufacturing, payroll, and time-clock process chains; approval fields; detailed posting traceability; validation outputs; and planted anomalies in the default `standard` mode.

> **Planned future extension:** More advanced payroll and production-control anomaly packs.

## Relevant Tables

| Topic | Main tables |
|---|---|
| O2C completeness | O2C header and line tables plus `CashReceiptApplication` |
| P2P completeness | P2P header and line tables |
| Approvals and SOD | `PurchaseRequisition`, `PurchaseOrder`, `PurchaseInvoice`, `JournalEntry`, `CreditMemo`, `CustomerRefund`, `Employee`, `PayrollRegister` |
| Manufacturing controls | `Item`, `BillOfMaterial`, `BillOfMaterialLine`, `Routing`, `RoutingOperation`, `WorkCenter`, `WorkCenterCalendar`, `WorkOrder`, `WorkOrderOperation`, `WorkOrderOperationSchedule`, `MaterialIssueLine`, `ProductionCompletionLine`, `WorkOrderClose` |
| Payroll and time-clock controls | `ShiftDefinition`, `EmployeeShiftAssignment`, `TimeClockEntry`, `AttendanceException`, `PayrollPeriod`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollPayment`, `PayrollLiabilityRemittance`, `Employee` |
| Cut-off and timing | operational header and line tables plus date fields |
| Duplicate and anomaly review | `DisbursementPayment`, `PurchaseInvoice`, `JournalEntry`, `SalesInvoice`, `CreditMemo`, `PayrollPayment`, exported `AnomalyLog`, exported `ValidationSummary` |

## Starter SQL Map

| Topic | Starter SQL file |
|---|---|
| O2C completeness | [01_o2c_document_chain_completeness.sql](../../queries/audit/01_o2c_document_chain_completeness.sql) |
| P2P completeness | [02_p2p_document_chain_completeness.sql](../../queries/audit/02_p2p_document_chain_completeness.sql) |
| Approval and SOD review | [03_approval_and_sod_review.sql](../../queries/audit/03_approval_and_sod_review.sql) |
| Cut-off and timing | [04_cutoff_and_timing_analysis.sql](../../queries/audit/04_cutoff_and_timing_analysis.sql) |
| Duplicate review | [05_duplicate_payment_reference_review.sql](../../queries/audit/05_duplicate_payment_reference_review.sql) |
| Potential anomaly review | [06_potential_anomaly_review.sql](../../queries/audit/06_potential_anomaly_review.sql) |
| Backorder and return review | [07_backorder_and_return_review.sql](../../queries/audit/07_backorder_and_return_review.sql) |
| BOM and supply-mode conflicts | [08_missing_bom_or_supply_mode_conflict.sql](../../queries/audit/08_missing_bom_or_supply_mode_conflict.sql) |
| Over-issue and open WIP review | [09_over_issue_and_open_wip_review.sql](../../queries/audit/09_over_issue_and_open_wip_review.sql) |
| Work-order close timing | [10_work_order_close_timing_review.sql](../../queries/audit/10_work_order_close_timing_review.sql) |
| Payroll control review | [11_payroll_control_review.sql](../../queries/audit/11_payroll_control_review.sql) |
| Labor-time-after-close and paid-without-time review | [12_labor_time_after_close_and_paid_without_time.sql](../../queries/audit/12_labor_time_after_close_and_paid_without_time.sql) |
| Over and under accrual review | [13_over_under_accrual_review.sql](../../queries/audit/13_over_under_accrual_review.sql) |
| Missing routing or operation-link review | [14_missing_routing_or_operation_link_review.sql](../../queries/audit/14_missing_routing_or_operation_link_review.sql) |
| Operation sequence and final-completion review | [15_operation_sequence_and_final_completion_review.sql](../../queries/audit/15_operation_sequence_and_final_completion_review.sql) |
| Schedule on non-working day review | [16_schedule_on_nonworking_day_review.sql](../../queries/audit/16_schedule_on_nonworking_day_review.sql) |
| Over-capacity day review | [17_over_capacity_day_review.sql](../../queries/audit/17_over_capacity_day_review.sql) |
| Completion before scheduled operation end review | [18_completion_before_scheduled_operation_end.sql](../../queries/audit/18_completion_before_scheduled_operation_end.sql) |
| Time-clock exceptions by employee, supervisor, and work center | [19_time_clock_exceptions_by_employee_supervisor_work_center.sql](../../queries/audit/19_time_clock_exceptions_by_employee_supervisor_work_center.sql) |
| Labor outside scheduled operation window review | [20_labor_outside_scheduled_operation_window_review.sql](../../queries/audit/20_labor_outside_scheduled_operation_window_review.sql) |
| Paid-without-clock and clock-without-pay review | [21_paid_without_clock_and_clock_without_pay_review.sql](../../queries/audit/21_paid_without_clock_and_clock_without_pay_review.sql) |
| Anomaly log to source-document tie-out | [22_anomaly_log_to_source_document_tie_out.sql](../../queries/audit/22_anomaly_log_to_source_document_tie_out.sql) |
| Accrued-service settlement exception review | [23_accrued_service_settlement_exception_review.sql](../../queries/audit/23_accrued_service_settlement_exception_review.sql) |
| Customer deposits and unapplied cash exception review | [24_customer_deposits_and_unapplied_cash_exception_review.sql](../../queries/audit/24_customer_deposits_and_unapplied_cash_exception_review.sql) |
| Time-clock, payroll, and labor bridge review | [25_time_clock_payroll_labor_bridge_review.sql](../../queries/audit/25_time_clock_payroll_labor_bridge_review.sql) |
| Duplicate AP reference detail review | [26_duplicate_ap_reference_detail_review.sql](../../queries/audit/26_duplicate_ap_reference_detail_review.sql) |

## Interpretation Notes

- A clean build with `anomaly_mode: none` may return few or no exceptions from anomaly-oriented queries.
- The default `standard` build is better for controls teaching because anomalies are present while the GL remains balanced.
- O2C completeness should be checked at the line and application level.
- Manufacturing controls should now start from BOM, routing, and schedule integrity before moving to work-order close timing and ledger balances.
- Payroll-control review should distinguish between normal processing lag and true exceptions such as missing payment, time after close, or hourly pay without time.
- Time-clock review should distinguish clean scheduling variance from planted attendance anomalies such as missing clock-out or off-shift clocking.
- Accrued-expense review should distinguish receipt-matched inventory AP from direct service invoices that intentionally clear prior accruals.

## Anomaly Coverage Matrix

| Query | Best build mode | Expected anomaly types | Main tables |
|---|---|---|---|
| [05_duplicate_payment_reference_review.sql](../../queries/audit/05_duplicate_payment_reference_review.sql) | `standard` | `duplicate_vendor_payment_reference`, `duplicate_supplier_invoice_number` | `DisbursementPayment`, `PurchaseInvoice`, `Supplier` |
| [06_potential_anomaly_review.sql](../../queries/audit/06_potential_anomaly_review.sql) | `standard` | `weekend_journal_entry`, `same_creator_approver`, `same_creator_approver_journal`, `missing_approval`, `invoice_before_shipment`, `duplicate_vendor_payment_reference` | `JournalEntry`, `PurchaseOrder`, `PurchaseRequisition`, `SalesInvoice`, `DisbursementPayment` |
| [11_payroll_control_review.sql](../../queries/audit/11_payroll_control_review.sql) | `standard` | `missing_payroll_payment`, `payroll_payment_before_approval` | `PayrollRegister`, `PayrollPayment`, `PayrollPeriod`, `Employee` |
| [12_labor_time_after_close_and_paid_without_time.sql](../../queries/audit/12_labor_time_after_close_and_paid_without_time.sql) | `standard` | `labor_after_operation_close`, `paid_without_clock` | `LaborTimeEntry`, `TimeClockEntry`, `PayrollRegisterLine` |
| [14_missing_routing_or_operation_link_review.sql](../../queries/audit/14_missing_routing_or_operation_link_review.sql) | `standard` | `missing_work_order_operations`, `invalid_direct_labor_operation_link` | `WorkOrder`, `WorkOrderOperation`, `LaborTimeEntry`, `Item` |
| [15_operation_sequence_and_final_completion_review.sql](../../queries/audit/15_operation_sequence_and_final_completion_review.sql) | `standard` | `overlapping_operation_sequence`, `completion_before_operation_end` | `WorkOrderOperation`, `ProductionCompletion` |
| [16_schedule_on_nonworking_day_review.sql](../../queries/audit/16_schedule_on_nonworking_day_review.sql) | `standard` | `scheduled_on_nonworking_day` | `WorkOrderOperationSchedule`, `WorkCenterCalendar` |
| [17_over_capacity_day_review.sql](../../queries/audit/17_over_capacity_day_review.sql) | `standard` | `overbooked_work_center_day` | `WorkOrderOperationSchedule`, `WorkCenterCalendar` |
| [18_completion_before_scheduled_operation_end.sql](../../queries/audit/18_completion_before_scheduled_operation_end.sql) | `standard` | `completion_before_operation_end` | `ProductionCompletion`, `WorkOrderOperation` |
| [19_time_clock_exceptions_by_employee_supervisor_work_center.sql](../../queries/audit/19_time_clock_exceptions_by_employee_supervisor_work_center.sql) | `standard` | `missing_clock_out`, `duplicate_time_clock_day`, `off_shift_clocking` | `AttendanceException`, `TimeClockEntry`, `ShiftDefinition`, `WorkCenter` |
| [20_labor_outside_scheduled_operation_window_review.sql](../../queries/audit/20_labor_outside_scheduled_operation_window_review.sql) | `standard` | `labor_after_operation_close` | `LaborTimeEntry`, `TimeClockEntry`, `WorkOrderOperation` |
| [21_paid_without_clock_and_clock_without_pay_review.sql](../../queries/audit/21_paid_without_clock_and_clock_without_pay_review.sql) | `standard` | `paid_without_clock`, `missing_clock_out` | `PayrollRegisterLine`, `LaborTimeEntry`, `TimeClockEntry` |
| [22_anomaly_log_to_source_document_tie_out.sql](../../queries/audit/22_anomaly_log_to_source_document_tie_out.sql) | `standard` | any logged anomaly | exported `AnomalyLog` plus source tables |
| [25_time_clock_payroll_labor_bridge_review.sql](../../queries/audit/25_time_clock_payroll_labor_bridge_review.sql) | `standard` | `paid_without_clock`, `missing_clock_out`, `labor_after_operation_close` | `TimeClockEntry`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine` |
| [26_duplicate_ap_reference_detail_review.sql](../../queries/audit/26_duplicate_ap_reference_detail_review.sql) | `standard` | `duplicate_vendor_payment_reference`, `duplicate_supplier_invoice_number` | `PurchaseInvoice`, `DisbursementPayment`, `Supplier` |
