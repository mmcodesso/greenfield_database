# Audit Analytics Starter Guide

**Audience:** Students, instructors, and analysts using the dataset for controls, exception review, and process-traceability work.  
**Purpose:** Show how to use the dataset for document-chain testing, approval review, cut-off analysis, duplicate detection, manufacturing-control exercises, and payroll-control review.  
**What you will learn:** Which document links matter most and which audit-oriented SQL files to run first.

> **Implemented in current generator:** O2C, P2P, manufacturing, and payroll process chains; approval fields; detailed posting traceability; validation outputs; and planted anomalies in the default `standard` mode.

> **Planned future extension:** More advanced payroll and production-control anomaly packs.

## Relevant Tables

| Topic | Main tables |
|---|---|
| O2C completeness | O2C header and line tables plus `CashReceiptApplication` |
| P2P completeness | P2P header and line tables |
| Approvals and SOD | `PurchaseRequisition`, `PurchaseOrder`, `PurchaseInvoice`, `JournalEntry`, `CreditMemo`, `CustomerRefund`, `Employee`, `PayrollRegister` |
| Manufacturing controls | `Item`, `BillOfMaterial`, `BillOfMaterialLine`, `Routing`, `RoutingOperation`, `WorkCenter`, `WorkOrder`, `WorkOrderOperation`, `MaterialIssueLine`, `ProductionCompletionLine`, `WorkOrderClose` |
| Payroll controls | `PayrollPeriod`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollPayment`, `PayrollLiabilityRemittance`, `Employee` |
| Cut-off and timing | operational header and line tables plus date fields |
| Duplicate and anomaly review | `DisbursementPayment`, `PurchaseInvoice`, `JournalEntry`, `SalesInvoice`, `CreditMemo`, `PayrollPayment`, Excel `AnomalyLog` |

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

## Interpretation Notes

- A clean build with `anomaly_mode: none` may return few or no exceptions from anomaly-oriented queries.
- The default `standard` build is better for controls teaching because anomalies are present while the GL remains balanced.
- O2C completeness should be checked at the line and application level.
- Manufacturing controls should now start from BOM and routing integrity before moving to work-order close timing and ledger balances.
- Payroll-control review should distinguish between normal processing lag and true exceptions such as missing payment, time after close, or hourly pay without time.
- Accrued-expense review should distinguish receipt-matched inventory AP from direct service invoices that intentionally clear prior accruals.
