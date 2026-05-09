const queryManifest = {
  "audit/01_o2c_document_chain_completeness.sql": {
    "category": "audit",
    "filename": "01_o2c_document_chain_completeness.sql",
    "publicPath": "/audit/01_o2c_document_chain_completeness.sql",
    "teachingObjective": "Trace sales orders through shipment, billing, cash application, and return activity to review document-chain completeness.",
    "mainTables": "SalesOrder, SalesOrderLine, Shipment, ShipmentLine, SalesInvoice, SalesInvoiceLine, CashReceiptApplication, SalesReturnLine, CreditMemo.",
    "outputShape": "One row per sales order with quantity and document-chain completion indicators."
  },
  "audit/02_p2p_document_chain_completeness.sql": {
    "category": "audit",
    "filename": "02_p2p_document_chain_completeness.sql",
    "publicPath": "/audit/02_p2p_document_chain_completeness.sql",
    "teachingObjective": "Trace requisitions through PO lines, receipts, supplier invoices, and payments to review P2P completeness.",
    "mainTables": "PurchaseRequisition, PurchaseOrderLine, PurchaseOrder, GoodsReceiptLine, PurchaseInvoiceLine, PurchaseInvoice, DisbursementPayment.",
    "outputShape": "One row per purchase requisition."
  },
  "audit/03_approval_and_sod_review.sql": {
    "category": "audit",
    "filename": "03_approval_and_sod_review.sql",
    "publicPath": "/audit/03_approval_and_sod_review.sql",
    "teachingObjective": "Review basic approval and segregation-of-duties conditions across major document types.",
    "mainTables": "PurchaseRequisition, PurchaseOrder, PurchaseInvoice, JournalEntry, Employee.",
    "outputShape": "One row per potentially suspicious document."
  },
  "audit/04_cutoff_and_timing_analysis.sql": {
    "category": "audit",
    "filename": "04_cutoff_and_timing_analysis.sql",
    "publicPath": "/audit/04_cutoff_and_timing_analysis.sql",
    "teachingObjective": "Summarize timing gaps across key O2C and P2P process transitions.",
    "mainTables": "SalesInvoice, SalesInvoiceLine, Shipment, ShipmentLine, PurchaseRequisition, PurchaseOrderLine, PurchaseOrder, GoodsReceipt, GoodsReceiptLine, PurchaseInvoice, PurchaseInvoiceLine.",
    "outputShape": "One row per timing metric with average, minimum, maximum, and negative-gap counts."
  },
  "audit/05_duplicate_payment_reference_review.sql": {
    "category": "audit",
    "filename": "05_duplicate_payment_reference_review.sql",
    "publicPath": "/audit/05_duplicate_payment_reference_review.sql",
    "teachingObjective": "Search for duplicate disbursement references and duplicate supplier invoice numbers.",
    "mainTables": "DisbursementPayment, PurchaseInvoice, Supplier.",
    "outputShape": "One row per duplicate-pattern candidate."
  },
  "audit/06_potential_anomaly_review.sql": {
    "category": "audit",
    "filename": "06_potential_anomaly_review.sql",
    "publicPath": "/audit/06_potential_anomaly_review.sql",
    "teachingObjective": "Run heuristic anomaly checks using currently implemented tables and fields.",
    "mainTables": "JournalEntry, PurchaseOrder, PurchaseRequisition, SalesInvoice, Shipment, DisbursementPayment.",
    "outputShape": "One row per potential anomaly candidate with a type, document reference, and explanatory detail."
  },
  "audit/07_backorder_and_return_review.sql": {
    "category": "audit",
    "filename": "07_backorder_and_return_review.sql",
    "publicPath": "/audit/07_backorder_and_return_review.sql",
    "teachingObjective": "Identify backordered orders and orders that later experienced returns or credit memos.",
    "mainTables": "SalesOrder, SalesOrderLine, ShipmentLine, SalesInvoiceLine, SalesReturn, SalesReturnLine, CreditMemo.",
    "outputShape": "One row per sales order with backorder and return indicators."
  },
  "audit/08_missing_bom_or_supply_mode_conflict.sql": {
    "category": "audit",
    "filename": "08_missing_bom_or_supply_mode_conflict.sql",
    "publicPath": "/audit/08_missing_bom_or_supply_mode_conflict.sql",
    "teachingObjective": "Identify supply-mode and BOM-structure conflicts.",
    "mainTables": "Item, BillOfMaterial.",
    "outputShape": "One row per item with a potential BOM or supply-mode issue."
  },
  "audit/09_over_issue_and_open_wip_review.sql": {
    "category": "audit",
    "filename": "09_over_issue_and_open_wip_review.sql",
    "publicPath": "/audit/09_over_issue_and_open_wip_review.sql",
    "teachingObjective": "Review work orders with possible material over-issue or unusually old open WIP.",
    "mainTables": "WorkOrder, BillOfMaterialLine, MaterialIssue, MaterialIssueLine, ProductionCompletionLine, WorkOrderClose.",
    "outputShape": "One row per work order needing review."
  },
  "audit/10_work_order_close_timing_review.sql": {
    "category": "audit",
    "filename": "10_work_order_close_timing_review.sql",
    "publicPath": "/audit/10_work_order_close_timing_review.sql",
    "teachingObjective": "Review the timing between the last production activity and work-order close.",
    "mainTables": "WorkOrder, MaterialIssue, ProductionCompletion, WorkOrderClose.",
    "outputShape": "One row per work order with delayed or missing close behavior."
  },
  "audit/11_payroll_control_review.sql": {
    "category": "audit",
    "filename": "11_payroll_control_review.sql",
    "publicPath": "/audit/11_payroll_control_review.sql",
    "teachingObjective": "Review common payroll-control exceptions around approvals, payments, and liabilities.",
    "mainTables": "PayrollRegister, PayrollPayment, PayrollPeriod, Employee.",
    "outputShape": "One row per potential payroll-control issue."
  },
  "audit/12_labor_time_after_close_and_paid_without_time.sql": {
    "category": "audit",
    "filename": "12_labor_time_after_close_and_paid_without_time.sql",
    "publicPath": "/audit/12_labor_time_after_close_and_paid_without_time.sql",
    "teachingObjective": "Review labor-control exceptions around time posted after work-order close and hourly employees paid without time.",
    "mainTables": "LaborTimeEntry, WorkOrder, PayrollRegister, PayrollPeriod, Employee.",
    "outputShape": "One row per potential control issue."
  },
  "audit/13_over_under_accrual_review.sql": {
    "category": "audit",
    "filename": "13_over_under_accrual_review.sql",
    "publicPath": "/audit/13_over_under_accrual_review.sql",
    "teachingObjective": "Flag accrued-expense settlements that materially differ from the original estimate or remain uncleared.",
    "mainTables": "JournalEntry, GLEntry, Account, PurchaseInvoiceLine, PurchaseInvoice.",
    "outputShape": "One row per potentially unusual accrual outcome."
  },
  "audit/14_missing_routing_or_operation_link_review.sql": {
    "category": "audit",
    "filename": "14_missing_routing_or_operation_link_review.sql",
    "publicPath": "/audit/14_missing_routing_or_operation_link_review.sql",
    "teachingObjective": "Review routing, work-order operation, and direct-labor linkage completeness.",
    "mainTables": "Item, Routing, WorkOrder, WorkOrderOperation, LaborTimeEntry.",
    "outputShape": "One row per potential routing or operation-link exception."
  },
  "audit/15_operation_sequence_and_final_completion_review.sql": {
    "category": "audit",
    "filename": "15_operation_sequence_and_final_completion_review.sql",
    "publicPath": "/audit/15_operation_sequence_and_final_completion_review.sql",
    "teachingObjective": "Review operation sequencing and final completion timing for manufactured work orders.",
    "mainTables": "WorkOrder, WorkOrderOperation, RoutingOperation.",
    "outputShape": "One row per potential sequencing or completion-timing exception."
  },
  "audit/16_schedule_on_nonworking_day_review.sql": {
    "category": "audit",
    "filename": "16_schedule_on_nonworking_day_review.sql",
    "publicPath": "/audit/16_schedule_on_nonworking_day_review.sql",
    "teachingObjective": "Detect work-center schedule rows that fall on non-working days.",
    "mainTables": "WorkOrderOperationSchedule, WorkCenterCalendar, WorkCenter, WorkOrderOperation, WorkOrder.",
    "outputShape": "One row per suspicious schedule row."
  },
  "audit/17_over_capacity_day_review.sql": {
    "category": "audit",
    "filename": "17_over_capacity_day_review.sql",
    "publicPath": "/audit/17_over_capacity_day_review.sql",
    "teachingObjective": "Detect work-center days where scheduled hours exceed available capacity.",
    "mainTables": "WorkOrderOperationSchedule, WorkCenterCalendar, WorkCenter.",
    "outputShape": "One row per over-capacity work-center day."
  },
  "audit/18_completion_before_scheduled_operation_end.sql": {
    "category": "audit",
    "filename": "18_completion_before_scheduled_operation_end.sql",
    "publicPath": "/audit/18_completion_before_scheduled_operation_end.sql",
    "teachingObjective": "Detect work orders completed before their final scheduled operation window ends.",
    "mainTables": "WorkOrder, WorkOrderOperation, RoutingOperation.",
    "outputShape": "One row per suspicious work order."
  },
  "audit/19_time_clock_exceptions_by_employee_supervisor_work_center.sql": {
    "category": "audit",
    "filename": "19_time_clock_exceptions_by_employee_supervisor_work_center.sql",
    "publicPath": "/audit/19_time_clock_exceptions_by_employee_supervisor_work_center.sql",
    "teachingObjective": "Review time-clock and attendance exceptions by employee, supervisor, and work center.",
    "mainTables": "AttendanceException, TimeClockEntry, ShiftDefinition, Employee, WorkCenter.",
    "outputShape": "One row per attendance exception."
  },
  "audit/20_labor_outside_scheduled_operation_window_review.sql": {
    "category": "audit",
    "filename": "20_labor_outside_scheduled_operation_window_review.sql",
    "publicPath": "/audit/20_labor_outside_scheduled_operation_window_review.sql",
    "teachingObjective": "Find direct labor booked outside the scheduled or actual operation window.",
    "mainTables": "LaborTimeEntry, TimeClockEntry, WorkOrderOperation, WorkOrder, RoutingOperation, Employee.",
    "outputShape": "One row per potential labor-window exception."
  },
  "audit/21_paid_without_clock_and_clock_without_pay_review.sql": {
    "category": "audit",
    "filename": "21_paid_without_clock_and_clock_without_pay_review.sql",
    "publicPath": "/audit/21_paid_without_clock_and_clock_without_pay_review.sql",
    "teachingObjective": "Review hourly payroll lines without approved time-clock support and approved time clocks that do not feed hourly pay.",
    "mainTables": "PayrollRegister, PayrollRegisterLine, LaborTimeEntry, TimeClockEntry, PayrollPeriod, Employee.",
    "outputShape": "One row per potential payroll-support exception."
  },
  "audit/23_accrued_service_settlement_exception_review.sql": {
    "category": "audit",
    "filename": "23_accrued_service_settlement_exception_review.sql",
    "publicPath": "/audit/23_accrued_service_settlement_exception_review.sql",
    "teachingObjective": "Review direct service invoices that clear prior accruals and identify timing or amount exceptions.",
    "mainTables": "JournalEntry, PurchaseInvoice, PurchaseInvoiceLine, DisbursementPayment, Supplier, Item.",
    "outputShape": "One row per accrued-service invoice line with timing, payment, and amount-difference flags."
  },
  "audit/24_customer_deposits_and_unapplied_cash_exception_review.sql": {
    "category": "audit",
    "filename": "24_customer_deposits_and_unapplied_cash_exception_review.sql",
    "publicPath": "/audit/24_customer_deposits_and_unapplied_cash_exception_review.sql",
    "teachingObjective": "Review customer receipts that remain unapplied or show unusual application timing.",
    "mainTables": "CashReceipt, CashReceiptApplication, Customer.",
    "outputShape": "One row per customer receipt flagged for deposit or unapplied-cash review."
  },
  "audit/25_time_clock_payroll_labor_bridge_review.sql": {
    "category": "audit",
    "filename": "25_time_clock_payroll_labor_bridge_review.sql",
    "publicPath": "/audit/25_time_clock_payroll_labor_bridge_review.sql",
    "teachingObjective": "Reconcile approved time clocks, labor allocation, and hourly payroll hours.",
    "mainTables": "TimeClockEntry, LaborTimeEntry, PayrollRegister, PayrollRegisterLine, PayrollPeriod, Employee.",
    "outputShape": "One row per employee and payroll period with an exception-oriented bridge result."
  },
  "audit/26_duplicate_ap_reference_detail_review.sql": {
    "category": "audit",
    "filename": "26_duplicate_ap_reference_detail_review.sql",
    "publicPath": "/audit/26_duplicate_ap_reference_detail_review.sql",
    "teachingObjective": "Review detailed duplicate AP reference patterns by supplier, document, and amount.",
    "mainTables": "PurchaseInvoice, DisbursementPayment, Supplier.",
    "outputShape": "One row per duplicated AP document reference."
  },
  "audit/27_terminated_employee_activity_review.sql": {
    "category": "audit",
    "filename": "27_terminated_employee_activity_review.sql",
    "publicPath": "/audit/27_terminated_employee_activity_review.sql",
    "teachingObjective": "Detect post-termination payroll, approval, and labor activity.",
    "mainTables": "Employee, PayrollRegister, TimeClockEntry, LaborTimeEntry, PurchaseOrder, JournalEntry.",
    "outputShape": "One row per employee activity that occurs after the employee's termination date."
  },
  "audit/28_approval_role_review_by_org_position.sql": {
    "category": "audit",
    "filename": "28_approval_role_review_by_org_position.sql",
    "publicPath": "/audit/28_approval_role_review_by_org_position.sql",
    "teachingObjective": "Review who is approving operational and accounting documents by role and organization position.",
    "mainTables": "Employee, PurchaseRequisition, PurchaseOrder, PurchaseInvoice, CreditMemo, CustomerRefund, JournalEntry, PayrollRegister.",
    "outputShape": "One row per document family and approver role."
  },
  "audit/29_executive_role_uniqueness_and_control_assignment_review.sql": {
    "category": "audit",
    "filename": "29_executive_role_uniqueness_and_control_assignment_review.sql",
    "publicPath": "/audit/29_executive_role_uniqueness_and_control_assignment_review.sql",
    "teachingObjective": "Review whether key executive and control-owner roles are unique and where those role holders appear in current-state assignments and approvals.",
    "mainTables": "Employee, CostCenter, Warehouse, WorkCenter, PurchaseOrder, PurchaseInvoice, CreditMemo, CustomerRefund, JournalEntry, PayrollRegister.",
    "outputShape": "One row per key role holder, with role counts and control-assignment evidence."
  },
  "audit/30_item_master_completeness_review.sql": {
    "category": "audit",
    "filename": "30_item_master_completeness_review.sql",
    "publicPath": "/audit/30_item_master_completeness_review.sql",
    "teachingObjective": "Review whether item-master rows carry the expected catalog attributes for their item group.",
    "mainTables": "Item.",
    "outputShape": "One row per item with one or more missing expected attributes."
  },
  "audit/31_discontinued_or_prelaunch_item_activity_review.sql": {
    "category": "audit",
    "filename": "31_discontinued_or_prelaunch_item_activity_review.sql",
    "publicPath": "/audit/31_discontinued_or_prelaunch_item_activity_review.sql",
    "teachingObjective": "Review operational activity that uses items before launch or after they are discontinued from the active catalog.",
    "mainTables": "Item, SalesOrder, SalesOrderLine, PurchaseOrder, PurchaseOrderLine, WorkOrder, Shipment, ShipmentLine, SalesInvoice, SalesInvoiceLine.",
    "outputShape": "One row per flagged activity line or work order."
  },
  "audit/32_approval_authority_review_by_expected_role_family.sql": {
    "category": "audit",
    "filename": "32_approval_authority_review_by_expected_role_family.sql",
    "publicPath": "/audit/32_approval_authority_review_by_expected_role_family.sql",
    "teachingObjective": "Compare expected approver role families to the roles that actually approve key document families.",
    "mainTables": "Employee, PurchaseRequisition, PurchaseOrder, PurchaseInvoice, CreditMemo, CustomerRefund, JournalEntry, PayrollRegister.",
    "outputShape": "One row per document type and observed approver role family."
  },
  "audit/33_terminated_employee_activity_rollup_by_process_area.sql": {
    "category": "audit",
    "filename": "33_terminated_employee_activity_rollup_by_process_area.sql",
    "publicPath": "/audit/33_terminated_employee_activity_rollup_by_process_area.sql",
    "teachingObjective": "Roll up post-termination activity by process area so students can see where workforce-control failures appear.",
    "mainTables": "Employee, PayrollRegister, TimeClockEntry, LaborTimeEntry, PurchaseRequisition, PurchaseOrder, PurchaseInvoice, CreditMemo, CustomerRefund, JournalEntry.",
    "outputShape": "One row per process area and source table with counts of post-termination activity."
  },
  "audit/34_current_state_employee_assignment_review.sql": {
    "category": "audit",
    "filename": "34_current_state_employee_assignment_review.sql",
    "publicPath": "/audit/34_current_state_employee_assignment_review.sql",
    "teachingObjective": "Review current-state master assignments that still point to inactive or terminated employees.",
    "mainTables": "CostCenter, Warehouse, WorkCenter, Customer, Employee.",
    "outputShape": "One row per current-state assignment linked to an inactive or terminated employee."
  },
  "audit/35_approval_authority_limit_review.sql": {
    "category": "audit",
    "filename": "35_approval_authority_limit_review.sql",
    "publicPath": "/audit/35_approval_authority_limit_review.sql",
    "teachingObjective": "Compare document approval amounts to approver limits and expected approver role families.",
    "mainTables": "PurchaseOrder, PurchaseInvoice, CreditMemo, CustomerRefund, JournalEntry, PayrollRegister, Employee.",
    "outputShape": "One row per flagged approval event."
  },
  "audit/36_item_status_alignment_review.sql": {
    "category": "audit",
    "filename": "36_item_status_alignment_review.sql",
    "publicPath": "/audit/36_item_status_alignment_review.sql",
    "teachingObjective": "Review current-state item master conflicts between lifecycle status and active-flag logic.",
    "mainTables": "Item.",
    "outputShape": "One row per item with a current-state lifecycle or active-status conflict."
  },
  "audit/37_scheduled_without_punch_and_punch_without_schedule_review.sql": {
    "category": "audit",
    "filename": "37_scheduled_without_punch_and_punch_without_schedule_review.sql",
    "publicPath": "/audit/37_scheduled_without_punch_and_punch_without_schedule_review.sql",
    "teachingObjective": "Find rostered days with no punch activity and punch activity without a valid roster assignment.",
    "mainTables": "EmployeeShiftRoster, TimeClockEntry, TimeClockPunch, Employee.",
    "outputShape": "One row per flagged roster or punch event."
  },
  "audit/38_overtime_without_approval_review.sql": {
    "category": "audit",
    "filename": "38_overtime_without_approval_review.sql",
    "publicPath": "/audit/38_overtime_without_approval_review.sql",
    "teachingObjective": "Identify approved worked overtime that is missing a linked overtime approval or exceeds the approved amount.",
    "mainTables": "TimeClockEntry, OvertimeApproval, Employee, WorkCenter.",
    "outputShape": "One row per flagged time-clock entry."
  },
  "audit/39_absence_with_worked_time_review.sql": {
    "category": "audit",
    "filename": "39_absence_with_worked_time_review.sql",
    "publicPath": "/audit/39_absence_with_worked_time_review.sql",
    "teachingObjective": "Find rostered absences that still carry time summaries or raw punch activity.",
    "mainTables": "EmployeeAbsence, EmployeeShiftRoster, TimeClockEntry, TimeClockPunch, Employee.",
    "outputShape": "One row per conflicting absence record."
  },
  "audit/40_overlapping_or_incomplete_punch_review.sql": {
    "category": "audit",
    "filename": "40_overlapping_or_incomplete_punch_review.sql",
    "publicPath": "/audit/40_overlapping_or_incomplete_punch_review.sql",
    "teachingObjective": "Detect incomplete punch sets and punch sequences with invalid ordering.",
    "mainTables": "TimeClockPunch, TimeClockEntry, Employee.",
    "outputShape": "One row per flagged time-clock entry."
  },
  "audit/41_roster_after_termination_review.sql": {
    "category": "audit",
    "filename": "41_roster_after_termination_review.sql",
    "publicPath": "/audit/41_roster_after_termination_review.sql",
    "teachingObjective": "Review roster rows scheduled after an employee's termination date.",
    "mainTables": "EmployeeShiftRoster, Employee, TimeClockEntry, TimeClockPunch.",
    "outputShape": "One row per invalid rostered day."
  },
  "audit/42_forecast_approval_and_override_review.sql": {
    "category": "audit",
    "filename": "42_forecast_approval_and_override_review.sql",
    "publicPath": "/audit/42_forecast_approval_and_override_review.sql",
    "teachingObjective": "Review weekly forecasts that lack approval or show unusually large overrides.",
    "mainTables": "DemandForecast, Item, Employee.",
    "outputShape": "One row per flagged forecast row."
  },
  "audit/43_inactive_or_stale_inventory_policy_review.sql": {
    "category": "audit",
    "filename": "43_inactive_or_stale_inventory_policy_review.sql",
    "publicPath": "/audit/43_inactive_or_stale_inventory_policy_review.sql",
    "teachingObjective": "Review active inventory items that lack a current active policy or carry inactive policy rows.",
    "mainTables": "InventoryPolicy, Item, Warehouse, Employee.",
    "outputShape": "One row per policy exception."
  },
  "audit/44_requisitions_and_work_orders_without_planning_support.sql": {
    "category": "audit",
    "filename": "44_requisitions_and_work_orders_without_planning_support.sql",
    "publicPath": "/audit/44_requisitions_and_work_orders_without_planning_support.sql",
    "teachingObjective": "Review replenishment documents that lack planning support.",
    "mainTables": "PurchaseRequisition, WorkOrder, Item.",
    "outputShape": "One row per unsupported requisition or work order."
  },
  "audit/45_recommendation_converted_after_need_by_date_review.sql": {
    "category": "audit",
    "filename": "45_recommendation_converted_after_need_by_date_review.sql",
    "publicPath": "/audit/45_recommendation_converted_after_need_by_date_review.sql",
    "teachingObjective": "Review planning recommendations that converted after their need-by date.",
    "mainTables": "SupplyPlanRecommendation, PurchaseRequisition, WorkOrder, Item.",
    "outputShape": "One row per late conversion."
  },
  "audit/46_discontinued_or_prelaunch_planning_activity_review.sql": {
    "category": "audit",
    "filename": "46_discontinued_or_prelaunch_planning_activity_review.sql",
    "publicPath": "/audit/46_discontinued_or_prelaunch_planning_activity_review.sql",
    "teachingObjective": "Review planning activity that occurs before launch or against discontinued inactive items.",
    "mainTables": "DemandForecast, SupplyPlanRecommendation, PurchaseRequisition, WorkOrder, Item.",
    "outputShape": "One row per planning-timing exception."
  },
  "audit/47_sales_below_floor_without_approval.sql": {
    "category": "audit",
    "filename": "47_sales_below_floor_without_approval.sql",
    "publicPath": "/audit/47_sales_below_floor_without_approval.sql",
    "teachingObjective": "Identify sales lines priced below the configured floor without a valid override approval.",
    "mainTables": "SalesOrder, SalesOrderLine, PriceListLine, Customer, Item.",
    "outputShape": "One row per offending sales order line."
  },
  "audit/48_expired_or_overlapping_price_list_review.sql": {
    "category": "audit",
    "filename": "48_expired_or_overlapping_price_list_review.sql",
    "publicPath": "/audit/48_expired_or_overlapping_price_list_review.sql",
    "teachingObjective": "Review price lists that are used after expiry or overlap another active list for the same scope.",
    "mainTables": "PriceList, PriceListLine, SalesOrder, SalesOrderLine.",
    "outputShape": "One row per expired-use or overlapping-scope exception."
  },
  "audit/49_promotion_scope_and_date_mismatch_review.sql": {
    "category": "audit",
    "filename": "49_promotion_scope_and_date_mismatch_review.sql",
    "publicPath": "/audit/49_promotion_scope_and_date_mismatch_review.sql",
    "teachingObjective": "Find sales lines that use a promotion outside the allowed date window or scope.",
    "mainTables": "SalesOrder, SalesOrderLine, PromotionProgram, Customer, Item.",
    "outputShape": "One row per mismatched promoted sales line."
  },
  "audit/50_customer_specific_price_list_bypass_review.sql": {
    "category": "audit",
    "filename": "50_customer_specific_price_list_bypass_review.sql",
    "publicPath": "/audit/50_customer_specific_price_list_bypass_review.sql",
    "teachingObjective": "Identify customer orders that bypass an available customer-specific price list.",
    "mainTables": "SalesOrder, SalesOrderLine, Customer, PriceList, PriceListLine.",
    "outputShape": "One row per bypassed sales order line."
  },
  "audit/51_override_approval_completeness_review.sql": {
    "category": "audit",
    "filename": "51_override_approval_completeness_review.sql",
    "publicPath": "/audit/51_override_approval_completeness_review.sql",
    "teachingObjective": "Review override approvals that are incomplete or missing from override-priced sales lines.",
    "mainTables": "PriceOverrideApproval, SalesOrderLine, SalesOrder, Customer, Item, PriceListLine.",
    "outputShape": "One row per incomplete approval or missing linked approval."
  },
  "audit/52_released_work_orders_due_without_actual_start_review.sql": {
    "category": "audit",
    "filename": "52_released_work_orders_due_without_actual_start_review.sql",
    "publicPath": "/audit/52_released_work_orders_due_without_actual_start_review.sql",
    "teachingObjective": "Review released work orders that are already due in-horizon but still have no actual start recorded.",
    "mainTables": "WorkOrder, WorkOrderOperation, WorkOrderOperationSchedule, WorkCenter, Item.",
    "outputShape": "One row per released work order with no actual start."
  },
  "audit/53_released_work_orders_due_without_actual_start_summary.sql": {
    "category": "audit",
    "filename": "53_released_work_orders_due_without_actual_start_summary.sql",
    "publicPath": "/audit/53_released_work_orders_due_without_actual_start_summary.sql",
    "teachingObjective": "Summarize the released-work-order-without-actual-start pattern by release month, due month, and first scheduled work center.",
    "mainTables": "WorkOrder, WorkOrderOperation, WorkOrderOperationSchedule, WorkCenter.",
    "outputShape": "Aggregated rows by due month, release month, and first scheduled work center."
  },
  "audit/54_design_service_approved_vs_billed_hours_review.sql": {
    "category": "audit",
    "filename": "54_design_service_approved_vs_billed_hours_review.sql",
    "publicPath": "/audit/54_design_service_approved_vs_billed_hours_review.sql",
    "teachingObjective": "Review whether approved design-service hours, billed hours, and invoice coverage stay aligned by engagement.",
    "mainTables": "ServiceEngagement, ServiceEngagementAssignment, ServiceTimeEntry, ServiceBillingLine, Customer.",
    "outputShape": "One row per service engagement."
  },
  "cases/01_o2c_line_trace_order_shipment_invoice.sql": {
    "category": "cases",
    "filename": "01_o2c_line_trace_order_shipment_invoice.sql",
    "publicPath": "/cases/01_o2c_line_trace_order_shipment_invoice.sql",
    "teachingObjective": "Trace one O2C line from order entry through shipment and invoice detail.",
    "mainTables": "SalesOrder, SalesOrderLine, Shipment, ShipmentLine, SalesInvoice, SalesInvoiceLine, Customer.",
    "outputShape": "One row per order-line-to-shipment-line-to-invoice-line trace."
  },
  "cases/02_o2c_source_to_gl_trace.sql": {
    "category": "cases",
    "filename": "02_o2c_source_to_gl_trace.sql",
    "publicPath": "/cases/02_o2c_source_to_gl_trace.sql",
    "teachingObjective": "Tie shipment, invoice, and commission source rows back to posted GL activity.",
    "mainTables": "Shipment, ShipmentLine, SalesInvoice, SalesInvoiceLine, SalesCommissionAccrual, SalesCommissionAdjustment, SalesCommissionPayment, GLEntry, Account, SalesOrder, Customer.",
    "outputShape": "One row per shipment or invoice source line and related GL posting row."
  },
  "cases/03_p2p_invoice_line_trace_receipt_vs_accrual.sql": {
    "category": "cases",
    "filename": "03_p2p_invoice_line_trace_receipt_vs_accrual.sql",
    "publicPath": "/cases/03_p2p_invoice_line_trace_receipt_vs_accrual.sql",
    "teachingObjective": "Separate receipt-matched supplier invoice lines from accrual-linked service-settlement lines.",
    "mainTables": "PurchaseInvoiceLine, PurchaseInvoice, PurchaseOrderLine, PurchaseRequisition, GoodsReceiptLine, JournalEntry, Supplier, Item.",
    "outputShape": "One row per purchase invoice line."
  },
  "cases/04_p2p_accrual_journal_invoice_payment_gl_trace.sql": {
    "category": "cases",
    "filename": "04_p2p_accrual_journal_invoice_payment_gl_trace.sql",
    "publicPath": "/cases/04_p2p_accrual_journal_invoice_payment_gl_trace.sql",
    "teachingObjective": "Trace an accrual-linked supplier invoice line from accrual journal through invoice clearing and disbursement postings.",
    "mainTables": "JournalEntry, PurchaseInvoiceLine, PurchaseInvoice, DisbursementPayment, GLEntry, Account, Supplier, Item.",
    "outputShape": "One row per accrual-linked purchase invoice line."
  },
  "cases/05_manufacturing_work_order_operation_trace.sql": {
    "category": "cases",
    "filename": "05_manufacturing_work_order_operation_trace.sql",
    "publicPath": "/cases/05_manufacturing_work_order_operation_trace.sql",
    "teachingObjective": "Trace one work order through operation sequence, schedule rows, approved clocks, and direct labor support.",
    "mainTables": "WorkOrderOperation, WorkOrder, Item, RoutingOperation, WorkCenter, WorkOrderOperationSchedule, TimeClockEntry, LaborTimeEntry.",
    "outputShape": "One row per work-order operation."
  },
  "cases/06_manufacturing_work_order_close_gl_trace.sql": {
    "category": "cases",
    "filename": "06_manufacturing_work_order_close_gl_trace.sql",
    "publicPath": "/cases/06_manufacturing_work_order_close_gl_trace.sql",
    "teachingObjective": "Trace one work order from material issue through completion, close variance, and supporting GL postings.",
    "mainTables": "WorkOrder, MaterialIssue, MaterialIssueLine, ProductionCompletion, ProductionCompletionLine, WorkOrderClose, GLEntry, Account, Item.",
    "outputShape": "One row per work order."
  },
  "financial/01_monthly_revenue_and_gross_margin.sql": {
    "category": "financial",
    "filename": "01_monthly_revenue_and_gross_margin.sql",
    "publicPath": "/financial/01_monthly_revenue_and_gross_margin.sql",
    "teachingObjective": "Review monthly revenue, COGS, and gross margin from posted accounting activity.",
    "mainTables": "GLEntry, Account.",
    "outputShape": "One row per fiscal year and fiscal period."
  },
  "financial/02_ar_aging_open_invoices.sql": {
    "category": "financial",
    "filename": "02_ar_aging_open_invoices.sql",
    "publicPath": "/financial/02_ar_aging_open_invoices.sql",
    "teachingObjective": "Build an accounts receivable aging listing from invoices, cash applications, and credit memos.",
    "mainTables": "SalesInvoice, CashReceiptApplication, CreditMemo, Customer.",
    "outputShape": "One row per open sales invoice."
  },
  "financial/03_ap_aging_open_invoices.sql": {
    "category": "financial",
    "filename": "03_ap_aging_open_invoices.sql",
    "publicPath": "/financial/03_ap_aging_open_invoices.sql",
    "teachingObjective": "Build an accounts payable aging listing from supplier invoices and disbursements.",
    "mainTables": "PurchaseInvoice, DisbursementPayment, Supplier.",
    "outputShape": "One row per open supplier invoice."
  },
  "financial/04_trial_balance_by_period.sql": {
    "category": "financial",
    "filename": "04_trial_balance_by_period.sql",
    "publicPath": "/financial/04_trial_balance_by_period.sql",
    "teachingObjective": "Produce a period-by-period trial balance from the posted general ledger.",
    "mainTables": "GLEntry, Account.",
    "outputShape": "One row per fiscal period and non-header account."
  },
  "financial/05_journal_and_close_cycle_review.sql": {
    "category": "financial",
    "filename": "05_journal_and_close_cycle_review.sql",
    "publicPath": "/financial/05_journal_and_close_cycle_review.sql",
    "teachingObjective": "Review journal-entry activity, recurring journals, reversals, and year-end close volume.",
    "mainTables": "JournalEntry.",
    "outputShape": "One row per posting month and journal entry type."
  },
  "financial/06_control_account_reconciliation.sql": {
    "category": "financial",
    "filename": "06_control_account_reconciliation.sql",
    "publicPath": "/financial/06_control_account_reconciliation.sql",
    "teachingObjective": "Compare key control-account balances to expected subledger balances.",
    "mainTables": "GLEntry, Account, SalesInvoice, CashReceipt, CashReceiptApplication, CreditMemo, CustomerRefund, PurchaseInvoice, PurchaseInvoiceLine, PurchaseOrderLine, DisbursementPayment, GoodsReceiptLine, ShipmentLine, SalesReturnLine.",
    "outputShape": "One row per control area with expected, actual, and difference amounts."
  },
  "financial/07_customer_credit_and_refunds.sql": {
    "category": "financial",
    "filename": "07_customer_credit_and_refunds.sql",
    "publicPath": "/financial/07_customer_credit_and_refunds.sql",
    "teachingObjective": "Review customer credit balances created by credit memos and cleared by refunds.",
    "mainTables": "CreditMemo, CustomerRefund, SalesInvoice, Customer.",
    "outputShape": "One row per credit memo with customer-credit and refund activity."
  },
  "financial/08_manufacturing_wip_clearing_variance.sql": {
    "category": "financial",
    "filename": "08_manufacturing_wip_clearing_variance.sql",
    "publicPath": "/financial/08_manufacturing_wip_clearing_variance.sql",
    "teachingObjective": "Review manufacturing-related ledger movement by period.",
    "mainTables": "GLEntry, Account, WorkOrderClose.",
    "outputShape": "One row per fiscal period."
  },
  "financial/09_payroll_liability_rollforward.sql": {
    "category": "financial",
    "filename": "09_payroll_liability_rollforward.sql",
    "publicPath": "/financial/09_payroll_liability_rollforward.sql",
    "teachingObjective": "Review payroll-liability movement by month and liability account.",
    "mainTables": "GLEntry, Account.",
    "outputShape": "One row per fiscal period and payroll-liability account."
  },
  "financial/10_gross_to_net_payroll_review.sql": {
    "category": "financial",
    "filename": "10_gross_to_net_payroll_review.sql",
    "publicPath": "/financial/10_gross_to_net_payroll_review.sql",
    "teachingObjective": "Review the gross-to-net payroll bridge by employee and pay period.",
    "mainTables": "PayrollPeriod, PayrollRegister, Employee, CostCenter.",
    "outputShape": "One row per employee payroll register."
  },
  "financial/11_payroll_cash_payments_and_remittances.sql": {
    "category": "financial",
    "filename": "11_payroll_cash_payments_and_remittances.sql",
    "publicPath": "/financial/11_payroll_cash_payments_and_remittances.sql",
    "teachingObjective": "Compare payroll cash outflows between employee payments and liability remittances.",
    "mainTables": "PayrollPayment, PayrollRegister, PayrollPeriod, PayrollLiabilityRemittance.",
    "outputShape": "One row per fiscal period."
  },
  "financial/12_accrued_expense_rollforward.sql": {
    "category": "financial",
    "filename": "12_accrued_expense_rollforward.sql",
    "publicPath": "/financial/12_accrued_expense_rollforward.sql",
    "teachingObjective": "Roll forward accrued-expense activity by month and accrual source.",
    "mainTables": "JournalEntry, GLEntry, Account, PurchaseInvoice, PurchaseInvoiceLine, Shipment.",
    "outputShape": "One row per fiscal year, fiscal period, accrual source, and expense family."
  },
  "financial/13_accrued_vs_invoiced_vs_paid_timing.sql": {
    "category": "financial",
    "filename": "13_accrued_vs_invoiced_vs_paid_timing.sql",
    "publicPath": "/financial/13_accrued_vs_invoiced_vs_paid_timing.sql",
    "teachingObjective": "Compare accrued-expense recognition timing to later invoicing and payment timing.",
    "mainTables": "JournalEntry, GLEntry, Account, PurchaseInvoice, PurchaseInvoiceLine, DisbursementPayment, Supplier.",
    "outputShape": "One row per accrual-linked service invoice."
  },
  "financial/14_hourly_payroll_hours_to_paid_earnings_bridge.sql": {
    "category": "financial",
    "filename": "14_hourly_payroll_hours_to_paid_earnings_bridge.sql",
    "publicPath": "/financial/14_hourly_payroll_hours_to_paid_earnings_bridge.sql",
    "teachingObjective": "Bridge approved hourly time-clock hours to payroll earnings and payment timing.",
    "mainTables": "TimeClockEntry, LaborTimeEntry, PayrollRegister, PayrollRegisterLine, PayrollPayment, PayrollPeriod, Employee.",
    "outputShape": "One row per hourly employee payroll register."
  },
  "financial/15_customer_deposits_and_unapplied_cash_aging.sql": {
    "category": "financial",
    "filename": "15_customer_deposits_and_unapplied_cash_aging.sql",
    "publicPath": "/financial/15_customer_deposits_and_unapplied_cash_aging.sql",
    "teachingObjective": "Review customer deposits, unapplied cash, and receipt-application timing after receipt.",
    "mainTables": "CashReceipt, CashReceiptApplication, Customer.",
    "outputShape": "One row per cash receipt with application timing and open unapplied balance."
  },
  "financial/16_retained_earnings_and_close_entry_impact.sql": {
    "category": "financial",
    "filename": "16_retained_earnings_and_close_entry_impact.sql",
    "publicPath": "/financial/16_retained_earnings_and_close_entry_impact.sql",
    "teachingObjective": "Separate raw P&L activity from year-end close impact on retained earnings.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal year with pre-close net income, statement net income, close-step amounts, and retained-earnings impact."
  },
  "financial/17_manufacturing_cost_component_bridge.sql": {
    "category": "financial",
    "filename": "17_manufacturing_cost_component_bridge.sql",
    "publicPath": "/financial/17_manufacturing_cost_component_bridge.sql",
    "teachingObjective": "Bridge manufacturing material, conversion, and variance activity by period.",
    "mainTables": "MaterialIssue, MaterialIssueLine, ProductionCompletion, ProductionCompletionLine, WorkOrderClose, GLEntry, Account.",
    "outputShape": "One row per month with operational cost components and ledger-account impact."
  },
  "financial/18_payroll_expense_mix_by_cost_center_and_pay_class.sql": {
    "category": "financial",
    "filename": "18_payroll_expense_mix_by_cost_center_and_pay_class.sql",
    "publicPath": "/financial/18_payroll_expense_mix_by_cost_center_and_pay_class.sql",
    "teachingObjective": "Review payroll expense mix by cost center and pay class.",
    "mainTables": "PayrollRegister, PayrollPeriod, Employee, CostCenter.",
    "outputShape": "One row per pay month, cost center, and pay class."
  },
  "financial/19_working_capital_bridge_by_month.sql": {
    "category": "financial",
    "filename": "19_working_capital_bridge_by_month.sql",
    "publicPath": "/financial/19_working_capital_bridge_by_month.sql",
    "teachingObjective": "Review the month-end working-capital bridge across the main current-asset and current-liability control accounts.",
    "mainTables": "GLEntry, Account.",
    "outputShape": "One row per fiscal month with ending balances for key working-capital buckets."
  },
  "financial/20_cash_conversion_timing_review.sql": {
    "category": "financial",
    "filename": "20_cash_conversion_timing_review.sql",
    "publicPath": "/financial/20_cash_conversion_timing_review.sql",
    "teachingObjective": "Compare how quickly Charles River turns sales invoices, purchase invoices, and goods receipts into cash settlement events.",
    "mainTables": "SalesInvoice, CashReceiptApplication, PurchaseInvoice, DisbursementPayment, GoodsReceipt, GoodsReceiptLine, PurchaseInvoiceLine.",
    "outputShape": "One row per source-month and timing metric family."
  },
  "financial/21_revenue_and_gross_margin_by_collection_style_lifecycle_supply_mode.sql": {
    "category": "financial",
    "filename": "21_revenue_and_gross_margin_by_collection_style_lifecycle_supply_mode.sql",
    "publicPath": "/financial/21_revenue_and_gross_margin_by_collection_style_lifecycle_supply_mode.sql",
    "teachingObjective": "Compare billed sales, credits, net sales, standard cost, and gross margin by collection, style family, lifecycle, and supply mode.",
    "mainTables": "SalesInvoiceLine, ShipmentLine, CreditMemoLine, SalesReturnLine, Item.",
    "outputShape": "One row per item group, collection, style family, lifecycle status, and supply mode."
  },
  "financial/22_payroll_and_people_cost_mix_by_cost_center_job_family_level.sql": {
    "category": "financial",
    "filename": "22_payroll_and_people_cost_mix_by_cost_center_job_family_level.sql",
    "publicPath": "/financial/22_payroll_and_people_cost_mix_by_cost_center_job_family_level.sql",
    "teachingObjective": "Review payroll cost mix by cost center, job family, job level, and pay class.",
    "mainTables": "PayrollRegister, Employee, CostCenter.",
    "outputShape": "One row per cost center and workforce grouping."
  },
  "financial/23_forecast_vs_actual_demand_by_week_item_group_collection_lifecycle.sql": {
    "category": "financial",
    "filename": "23_forecast_vs_actual_demand_by_week_item_group_collection_lifecycle.sql",
    "publicPath": "/financial/23_forecast_vs_actual_demand_by_week_item_group_collection_lifecycle.sql",
    "teachingObjective": "Compare weekly forecast demand to realized sales-order demand by item family.",
    "mainTables": "DemandForecast, SalesOrder, SalesOrderLine, Item.",
    "outputShape": "One row per week and item-family slice."
  },
  "financial/24_recommendation_conversion_by_type_priority_planner.sql": {
    "category": "financial",
    "filename": "24_recommendation_conversion_by_type_priority_planner.sql",
    "publicPath": "/financial/24_recommendation_conversion_by_type_priority_planner.sql",
    "teachingObjective": "Review how planning recommendations convert into requisitions and work orders by planner and priority.",
    "mainTables": "SupplyPlanRecommendation, Employee.",
    "outputShape": "One row per recommendation grouping."
  },
  "financial/25_price_realization_vs_list_by_segment_customer_region_collection_style.sql": {
    "category": "financial",
    "filename": "25_price_realization_vs_list_by_segment_customer_region_collection_style.sql",
    "publicPath": "/financial/25_price_realization_vs_list_by_segment_customer_region_collection_style.sql",
    "teachingObjective": "Compare realized billed pricing to base list price by customer, segment, region, and product portfolio.",
    "mainTables": "SalesInvoice, SalesInvoiceLine, Customer, Item.",
    "outputShape": "One row per month, region, customer segment, customer, collection, and style family."
  },
  "financial/26_gross_margin_impact_of_promotions_vs_nonpromotion_sales.sql": {
    "category": "financial",
    "filename": "26_gross_margin_impact_of_promotions_vs_nonpromotion_sales.sql",
    "publicPath": "/financial/26_gross_margin_impact_of_promotions_vs_nonpromotion_sales.sql",
    "teachingObjective": "Compare revenue and gross margin for promoted versus non-promoted sales.",
    "mainTables": "SalesInvoiceLine, ShipmentLine, SalesInvoice, Item.",
    "outputShape": "One row per month, collection, and promotion flag."
  },
  "financial/27_income_statement_monthly.sql": {
    "category": "financial",
    "filename": "27_income_statement_monthly.sql",
    "publicPath": "/financial/27_income_statement_monthly.sql",
    "teachingObjective": "Produce a detailed monthly income statement from posted general-ledger activity.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal month and income-statement line."
  },
  "financial/28_income_statement_quarterly.sql": {
    "category": "financial",
    "filename": "28_income_statement_quarterly.sql",
    "publicPath": "/financial/28_income_statement_quarterly.sql",
    "teachingObjective": "Produce a detailed quarterly income statement from posted general-ledger activity.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal quarter and income-statement line."
  },
  "financial/29_income_statement_annual.sql": {
    "category": "financial",
    "filename": "29_income_statement_annual.sql",
    "publicPath": "/financial/29_income_statement_annual.sql",
    "teachingObjective": "Produce a detailed annual income statement from posted general-ledger activity.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal year and income-statement line."
  },
  "financial/30_balance_sheet_monthly.sql": {
    "category": "financial",
    "filename": "30_balance_sheet_monthly.sql",
    "publicPath": "/financial/30_balance_sheet_monthly.sql",
    "teachingObjective": "Produce a detailed monthly classified balance sheet from posted general-ledger activity.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal month and balance-sheet line."
  },
  "financial/31_balance_sheet_quarterly.sql": {
    "category": "financial",
    "filename": "31_balance_sheet_quarterly.sql",
    "publicPath": "/financial/31_balance_sheet_quarterly.sql",
    "teachingObjective": "Produce a detailed quarterly classified balance sheet from posted general-ledger activity.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal quarter and balance-sheet line."
  },
  "financial/32_balance_sheet_annual.sql": {
    "category": "financial",
    "filename": "32_balance_sheet_annual.sql",
    "publicPath": "/financial/32_balance_sheet_annual.sql",
    "teachingObjective": "Produce a detailed annual classified balance sheet from posted general-ledger activity.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal year and balance-sheet line."
  },
  "financial/33_cash_flow_statement_indirect_monthly.sql": {
    "category": "financial",
    "filename": "33_cash_flow_statement_indirect_monthly.sql",
    "publicPath": "/financial/33_cash_flow_statement_indirect_monthly.sql",
    "teachingObjective": "Produce a detailed monthly indirect-method cash flow statement from posted ledger activity.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal month and cash-flow statement line."
  },
  "financial/34_cash_flow_statement_indirect_quarterly.sql": {
    "category": "financial",
    "filename": "34_cash_flow_statement_indirect_quarterly.sql",
    "publicPath": "/financial/34_cash_flow_statement_indirect_quarterly.sql",
    "teachingObjective": "Produce a detailed quarterly indirect-method cash flow statement from posted ledger activity.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal quarter and cash-flow statement line."
  },
  "financial/35_cash_flow_statement_indirect_annual.sql": {
    "category": "financial",
    "filename": "35_cash_flow_statement_indirect_annual.sql",
    "publicPath": "/financial/35_cash_flow_statement_indirect_annual.sql",
    "teachingObjective": "Produce a detailed annual indirect-method cash flow statement from posted ledger activity.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal year and cash-flow statement line."
  },
  "financial/36_cash_flow_statement_direct_monthly.sql": {
    "category": "financial",
    "filename": "36_cash_flow_statement_direct_monthly.sql",
    "publicPath": "/financial/36_cash_flow_statement_direct_monthly.sql",
    "teachingObjective": "Produce a detailed monthly direct-method cash flow statement from posted cash-ledger activity.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal month and cash-flow statement line."
  },
  "financial/37_cash_flow_statement_direct_quarterly.sql": {
    "category": "financial",
    "filename": "37_cash_flow_statement_direct_quarterly.sql",
    "publicPath": "/financial/37_cash_flow_statement_direct_quarterly.sql",
    "teachingObjective": "Produce a detailed quarterly direct-method cash flow statement from posted cash-ledger activity.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal quarter and cash-flow statement line."
  },
  "financial/38_cash_flow_statement_direct_annual.sql": {
    "category": "financial",
    "filename": "38_cash_flow_statement_direct_annual.sql",
    "publicPath": "/financial/38_cash_flow_statement_direct_annual.sql",
    "teachingObjective": "Produce a detailed annual direct-method cash flow statement from posted cash-ledger activity.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal year and cash-flow statement line."
  },
  "financial/39_annual_income_to_equity_bridge.sql": {
    "category": "financial",
    "filename": "39_annual_income_to_equity_bridge.sql",
    "publicPath": "/financial/39_annual_income_to_equity_bridge.sql",
    "teachingObjective": "Reconcile annual net income to the retained-earnings close and year-end balance-sheet residuals.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per closed fiscal year with income-statement, close-process, retained-earnings, and balance-sheet bridge columns."
  },
  "financial/40_post_close_profit_and_loss_leakage_review.sql": {
    "category": "financial",
    "filename": "40_post_close_profit_and_loss_leakage_review.sql",
    "publicPath": "/financial/40_post_close_profit_and_loss_leakage_review.sql",
    "teachingObjective": "Surface any P&L or income-summary accounts that still carry a balance after the annual close.",
    "mainTables": "GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal year and leaked account with a non-zero ending balance."
  },
  "financial/41_round_dollar_manual_journal_close_sensitivity_review.sql": {
    "category": "financial",
    "filename": "41_round_dollar_manual_journal_close_sensitivity_review.sql",
    "publicPath": "/financial/41_round_dollar_manual_journal_close_sensitivity_review.sql",
    "teachingObjective": "Highlight rounded manual journals that are likely to affect annual close and statement reconciliation.",
    "mainTables": "JournalEntry, GLEntry, Account.",
    "outputShape": "One row per close-sensitive manual journal with whole-dollar and two-line diagnostics."
  },
  "financial/42_annual_net_revenue_bridge.sql": {
    "category": "financial",
    "filename": "42_annual_net_revenue_bridge.sql",
    "publicPath": "/financial/42_annual_net_revenue_bridge.sql",
    "teachingObjective": "Trace annual net revenue from operational source documents into posted GL activity and the annual income statement.",
    "mainTables": "SalesInvoice, SalesInvoiceLine, CreditMemo, CreditMemoLine, GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal year with operational, pre-close GL, and statement net-revenue totals plus variances."
  },
  "financial/43_invoice_revenue_cutoff_exception_summary.sql": {
    "category": "financial",
    "filename": "43_invoice_revenue_cutoff_exception_summary.sql",
    "publicPath": "/financial/43_invoice_revenue_cutoff_exception_summary.sql",
    "teachingObjective": "Isolate invoice-level revenue cutoff exceptions that move operational invoice revenue into a different GL fiscal year.",
    "mainTables": "SalesInvoice, SalesInvoiceLine, Shipment, ShipmentLine, GLEntry, Account, SalesOrder, Customer.",
    "outputShape": "One row per exception invoice header with shipment timing, revenue GL posting year, and root-cause classification fields."
  },
  "financial/44_invoice_revenue_cutoff_exception_trace.sql": {
    "category": "financial",
    "filename": "44_invoice_revenue_cutoff_exception_trace.sql",
    "publicPath": "/financial/44_invoice_revenue_cutoff_exception_trace.sql",
    "teachingObjective": "Trace invoice-level revenue cutoff exceptions from order and shipment source lines into the posted revenue GL rows.",
    "mainTables": "SalesOrder, SalesOrderLine, Shipment, ShipmentLine, SalesInvoice, SalesInvoiceLine, GLEntry, Account, Item, Customer.",
    "outputShape": "One row per exception invoice line and related operating-revenue GL row, including trace classifications and line-to-GL variances."
  },
  "financial/45_monthly_ar_aging_detail.sql": {
    "category": "financial",
    "filename": "45_monthly_ar_aging_detail.sql",
    "publicPath": "/financial/45_monthly_ar_aging_detail.sql",
    "teachingObjective": "Reconstruct month-end accounts receivable aging positions across the full dataset timeline.",
    "mainTables": "SalesInvoice, CashReceiptApplication, CreditMemo, Customer.",
    "outputShape": "One row per open sales invoice per month-end."
  },
  "financial/46_monthly_ar_aging_summary.sql": {
    "category": "financial",
    "filename": "46_monthly_ar_aging_summary.sql",
    "publicPath": "/financial/46_monthly_ar_aging_summary.sql",
    "teachingObjective": "Summarize month-end accounts receivable aging positions by customer across the full dataset timeline.",
    "mainTables": "SalesInvoice, CashReceiptApplication, CreditMemo, Customer.",
    "outputShape": "One row per month-end and customer."
  },
  "financial/47_monthly_ap_aging_detail.sql": {
    "category": "financial",
    "filename": "47_monthly_ap_aging_detail.sql",
    "publicPath": "/financial/47_monthly_ap_aging_detail.sql",
    "teachingObjective": "Reconstruct month-end accounts payable aging positions across the full dataset timeline.",
    "mainTables": "PurchaseInvoice, DisbursementPayment, Supplier.",
    "outputShape": "One row per open supplier invoice per month-end."
  },
  "financial/48_monthly_ap_aging_summary.sql": {
    "category": "financial",
    "filename": "48_monthly_ap_aging_summary.sql",
    "publicPath": "/financial/48_monthly_ap_aging_summary.sql",
    "teachingObjective": "Summarize month-end accounts payable aging positions by supplier across the full dataset timeline.",
    "mainTables": "PurchaseInvoice, DisbursementPayment, Supplier.",
    "outputShape": "One row per month-end and supplier."
  },
  "financial/49_pro_forma_income_statement_monthly.sql": {
    "category": "financial",
    "filename": "49_pro_forma_income_statement_monthly.sql",
    "publicPath": "/financial/49_pro_forma_income_statement_monthly.sql",
    "teachingObjective": "Produce a monthly pro forma income statement from driver-based budget detail.",
    "mainTables": "BudgetLine, Account.",
    "outputShape": "One row per fiscal month and income-statement line."
  },
  "financial/50_pro_forma_balance_sheet_monthly.sql": {
    "category": "financial",
    "filename": "50_pro_forma_balance_sheet_monthly.sql",
    "publicPath": "/financial/50_pro_forma_balance_sheet_monthly.sql",
    "teachingObjective": "Produce a monthly pro forma classified balance sheet from the driver-based budget roll-forward.",
    "mainTables": "BudgetLine, Account.",
    "outputShape": "One row per fiscal month and balance-sheet line."
  },
  "financial/51_pro_forma_cash_flow_indirect_monthly.sql": {
    "category": "financial",
    "filename": "51_pro_forma_cash_flow_indirect_monthly.sql",
    "publicPath": "/financial/51_pro_forma_cash_flow_indirect_monthly.sql",
    "teachingObjective": "Produce a monthly pro forma indirect-method cash flow statement from the driver-based budget roll-forward.",
    "mainTables": "BudgetLine, Account, GLEntry, JournalEntry.",
    "outputShape": "One row per fiscal month and cash-flow statement line."
  },
  "financial/52_budget_vs_actual_statement_bridge_monthly.sql": {
    "category": "financial",
    "filename": "52_budget_vs_actual_statement_bridge_monthly.sql",
    "publicPath": "/financial/52_budget_vs_actual_statement_bridge_monthly.sql",
    "teachingObjective": "Compare monthly pro forma statement lines to posted actual statement lines across performance, position, and cash.",
    "mainTables": "BudgetLine, GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal month and bridged statement line."
  },
  "financial/53_budget_vs_actual_working_capital_and_cash_bridge.sql": {
    "category": "financial",
    "filename": "53_budget_vs_actual_working_capital_and_cash_bridge.sql",
    "publicPath": "/financial/53_budget_vs_actual_working_capital_and_cash_bridge.sql",
    "teachingObjective": "Compare budgeted and actual month-end working-capital balances and cash on one bridge.",
    "mainTables": "BudgetLine, GLEntry, Account, JournalEntry.",
    "outputShape": "One row per fiscal month and working-capital or cash metric."
  },
  "financial/54_fixed_asset_rollforward_by_behavior_group.sql": {
    "category": "financial",
    "filename": "54_fixed_asset_rollforward_by_behavior_group.sql",
    "publicPath": "/financial/54_fixed_asset_rollforward_by_behavior_group.sql",
    "teachingObjective": "Roll forward fixed-asset gross cost, accumulated depreciation, and net book value by behavior group.",
    "mainTables": "FixedAsset, FixedAssetEvent, JournalEntry.",
    "outputShape": "One row per fiscal month and asset behavior group."
  },
  "financial/55_capex_acquisitions_financing_and_disposals.sql": {
    "category": "financial",
    "filename": "55_capex_acquisitions_financing_and_disposals.sql",
    "publicPath": "/financial/55_capex_acquisitions_financing_and_disposals.sql",
    "teachingObjective": "Trace CAPEX additions, financing, and disposals across the asset lifecycle.",
    "mainTables": "FixedAssetEvent, FixedAsset, PurchaseInvoice, DisbursementPayment, DebtAgreement, JournalEntry.",
    "outputShape": "One row per fixed-asset event excluding opening balances."
  },
  "financial/56_debt_amortization_and_cash_impact.sql": {
    "category": "financial",
    "filename": "56_debt_amortization_and_cash_impact.sql",
    "publicPath": "/financial/56_debt_amortization_and_cash_impact.sql",
    "teachingObjective": "Show the note-payable amortization schedule and cash impact tied to CAPEX financing.",
    "mainTables": "DebtAgreement, DebtScheduleLine, FixedAsset.",
    "outputShape": "One row per scheduled debt payment line."
  },
  "financial/57_design_service_revenue_and_billed_hours_by_customer_month.sql": {
    "category": "financial",
    "filename": "57_design_service_revenue_and_billed_hours_by_customer_month.sql",
    "publicPath": "/financial/57_design_service_revenue_and_billed_hours_by_customer_month.sql",
    "teachingObjective": "Review monthly billed design-service hours and posted service revenue by customer.",
    "mainTables": "ServiceBillingLine, SalesInvoice, SalesInvoiceLine, Customer, GLEntry, Account.",
    "outputShape": "One row per invoice month and customer."
  },
  "financial/58_sales_commission_payable_rollforward.sql": {
    "category": "financial",
    "filename": "58_sales_commission_payable_rollforward.sql",
    "publicPath": "/financial/58_sales_commission_payable_rollforward.sql",
    "teachingObjective": "Reconcile sales commission payable activity from invoice accrual through clawback and payment.",
    "mainTables": "GLEntry, Account, SalesCommissionAccrual, SalesCommissionAdjustment, SalesCommissionPayment.",
    "outputShape": "One row per fiscal period with sales commission payable activity and ending balance."
  },
  "managerial/01_budget_vs_actual_by_cost_center.sql": {
    "category": "managerial",
    "filename": "01_budget_vs_actual_by_cost_center.sql",
    "publicPath": "/managerial/01_budget_vs_actual_by_cost_center.sql",
    "teachingObjective": "Compare monthly budget to posted operating expense by cost center and account.",
    "mainTables": "Budget, CostCenter, Account, GLEntry, JournalEntry.",
    "outputShape": "One row per fiscal year, month, cost center, and budgeted account."
  },
  "managerial/02_sales_mix_by_customer_region_item_group.sql": {
    "category": "managerial",
    "filename": "02_sales_mix_by_customer_region_item_group.sql",
    "publicPath": "/managerial/02_sales_mix_by_customer_region_item_group.sql",
    "teachingObjective": "Analyze billed sales mix by customer geography, customer segment, and product family.",
    "mainTables": "SalesInvoice, SalesInvoiceLine, Customer, Item.",
    "outputShape": "One row per invoice month, region, customer segment, item group, and item."
  },
  "managerial/03_inventory_movement_by_item_and_warehouse.sql": {
    "category": "managerial",
    "filename": "03_inventory_movement_by_item_and_warehouse.sql",
    "publicPath": "/managerial/03_inventory_movement_by_item_and_warehouse.sql",
    "teachingObjective": "Compare inbound and outbound inventory movement by month, warehouse, and item.",
    "mainTables": "GoodsReceipt, GoodsReceiptLine, Shipment, ShipmentLine, Warehouse, Item.",
    "outputShape": "One row per activity month, warehouse, and item."
  },
  "managerial/04_purchasing_activity_by_supplier_category.sql": {
    "category": "managerial",
    "filename": "04_purchasing_activity_by_supplier_category.sql",
    "publicPath": "/managerial/04_purchasing_activity_by_supplier_category.sql",
    "teachingObjective": "Review purchasing volume by supplier, supplier category, and item group.",
    "mainTables": "PurchaseOrder, PurchaseOrderLine, Supplier, Item.",
    "outputShape": "One row per order month, supplier, and item group."
  },
  "managerial/05_cost_center_activity_summary.sql": {
    "category": "managerial",
    "filename": "05_cost_center_activity_summary.sql",
    "publicPath": "/managerial/05_cost_center_activity_summary.sql",
    "teachingObjective": "Summarize operational volume and posted operating expense by cost center and month.",
    "mainTables": "SalesOrder, PurchaseRequisition, GLEntry, Account, JournalEntry, CostCenter.",
    "outputShape": "One row per activity month and cost center."
  },
  "managerial/06_basic_product_profitability.sql": {
    "category": "managerial",
    "filename": "06_basic_product_profitability.sql",
    "publicPath": "/managerial/06_basic_product_profitability.sql",
    "teachingObjective": "Estimate product-level profitability from billed revenue and shipped cost.",
    "mainTables": "SalesOrderLine, SalesInvoiceLine, ShipmentLine, Item.",
    "outputShape": "One row per item."
  },
  "managerial/07_bom_standard_cost_rollup.sql": {
    "category": "managerial",
    "filename": "07_bom_standard_cost_rollup.sql",
    "publicPath": "/managerial/07_bom_standard_cost_rollup.sql",
    "teachingObjective": "Compare manufactured-item standard cost to BOM material plus standard conversion cost.",
    "mainTables": "Item, BillOfMaterial, BillOfMaterialLine.",
    "outputShape": "One row per manufactured finished good."
  },
  "managerial/08_work_order_throughput_by_month.sql": {
    "category": "managerial",
    "filename": "08_work_order_throughput_by_month.sql",
    "publicPath": "/managerial/08_work_order_throughput_by_month.sql",
    "teachingObjective": "Summarize released, completed, and closed work-order activity by month.",
    "mainTables": "WorkOrder, ProductionCompletionLine, WorkOrderClose.",
    "outputShape": "One row per release month."
  },
  "managerial/09_material_usage_and_scrap_review.sql": {
    "category": "managerial",
    "filename": "09_material_usage_and_scrap_review.sql",
    "publicPath": "/managerial/09_material_usage_and_scrap_review.sql",
    "teachingObjective": "Compare BOM-based expected component usage to actual issued material by work order.",
    "mainTables": "WorkOrder, BillOfMaterialLine, MaterialIssue, MaterialIssueLine, Item.",
    "outputShape": "One row per work order component."
  },
  "managerial/10_production_completion_and_fg_availability.sql": {
    "category": "managerial",
    "filename": "10_production_completion_and_fg_availability.sql",
    "publicPath": "/managerial/10_production_completion_and_fg_availability.sql",
    "teachingObjective": "Review manufactured finished-goods activity by month, warehouse, and item group.",
    "mainTables": "ProductionCompletion, ProductionCompletionLine, Shipment, ShipmentLine, SalesReturn, SalesReturnLine, WorkOrder, Warehouse, Item.",
    "outputShape": "One row per fiscal period, warehouse, and item group."
  },
  "managerial/11_manufacturing_variance_by_month_item_group.sql": {
    "category": "managerial",
    "filename": "11_manufacturing_variance_by_month_item_group.sql",
    "publicPath": "/managerial/11_manufacturing_variance_by_month_item_group.sql",
    "teachingObjective": "Review manufacturing variance by month, item group, and warehouse.",
    "mainTables": "WorkOrderClose, WorkOrder, Item, Warehouse.",
    "outputShape": "One row per close month, warehouse, and item group."
  },
  "managerial/12_direct_labor_by_work_order_and_employee_class.sql": {
    "category": "managerial",
    "filename": "12_direct_labor_by_work_order_and_employee_class.sql",
    "publicPath": "/managerial/12_direct_labor_by_work_order_and_employee_class.sql",
    "teachingObjective": "Review direct labor hours and cost by work order, employee title, and pay class.",
    "mainTables": "LaborTimeEntry, Employee, WorkOrder, Item, PayrollPeriod.",
    "outputShape": "One row per work order and employee class grouping."
  },
  "managerial/13_unit_cost_bridge_dm_dl_varoh_fixedoh.sql": {
    "category": "managerial",
    "filename": "13_unit_cost_bridge_dm_dl_varoh_fixedoh.sql",
    "publicPath": "/managerial/13_unit_cost_bridge_dm_dl_varoh_fixedoh.sql",
    "teachingObjective": "Show the standard unit-cost bridge for manufactured finished goods.",
    "mainTables": "Item.",
    "outputShape": "One row per manufactured item."
  },
  "managerial/14_absorption_vs_contribution_margin.sql": {
    "category": "managerial",
    "filename": "14_absorption_vs_contribution_margin.sql",
    "publicPath": "/managerial/14_absorption_vs_contribution_margin.sql",
    "teachingObjective": "Compare absorption margin and contribution margin by item and supply mode.",
    "mainTables": "SalesInvoiceLine, SalesInvoice, Item.",
    "outputShape": "One row per item."
  },
  "managerial/15_manufactured_vs_purchased_margin_comparison.sql": {
    "category": "managerial",
    "filename": "15_manufactured_vs_purchased_margin_comparison.sql",
    "publicPath": "/managerial/15_manufactured_vs_purchased_margin_comparison.sql",
    "teachingObjective": "Compare margin structure between manufactured and purchased finished goods.",
    "mainTables": "SalesInvoiceLine, Item.",
    "outputShape": "One row per supply mode."
  },
  "managerial/16_labor_efficiency_and_rate_variance.sql": {
    "category": "managerial",
    "filename": "16_labor_efficiency_and_rate_variance.sql",
    "publicPath": "/managerial/16_labor_efficiency_and_rate_variance.sql",
    "teachingObjective": "Review direct labor rate and efficiency variance by work order.",
    "mainTables": "LaborTimeEntry, WorkOrder, Item, ProductionCompletionLine.",
    "outputShape": "One row per work order with direct labor activity."
  },
  "managerial/17_routing_master_review.sql": {
    "category": "managerial",
    "filename": "17_routing_master_review.sql",
    "publicPath": "/managerial/17_routing_master_review.sql",
    "teachingObjective": "Review the routing design assigned to manufactured items.",
    "mainTables": "Item, Routing, RoutingOperation, WorkCenter.",
    "outputShape": "One row per manufactured item and routing operation."
  },
  "managerial/18_work_center_activity_and_operation_hours.sql": {
    "category": "managerial",
    "filename": "18_work_center_activity_and_operation_hours.sql",
    "publicPath": "/managerial/18_work_center_activity_and_operation_hours.sql",
    "teachingObjective": "Compare operation-level direct labor and work-center activity by month.",
    "mainTables": "WorkOrderOperation, RoutingOperation, WorkCenter, LaborTimeEntry, WorkOrder, Item.",
    "outputShape": "One row per month, work center, and operation code."
  },
  "managerial/19_daily_load_vs_capacity.sql": {
    "category": "managerial",
    "filename": "19_daily_load_vs_capacity.sql",
    "publicPath": "/managerial/19_daily_load_vs_capacity.sql",
    "teachingObjective": "Compare daily scheduled load against available work-center capacity.",
    "mainTables": "WorkCenterCalendar, WorkOrderOperationSchedule, WorkCenter.",
    "outputShape": "One row per work center and calendar date."
  },
  "managerial/20_monthly_work_center_utilization.sql": {
    "category": "managerial",
    "filename": "20_monthly_work_center_utilization.sql",
    "publicPath": "/managerial/20_monthly_work_center_utilization.sql",
    "teachingObjective": "Summarize monthly work-center utilization and identify recurring bottlenecks.",
    "mainTables": "WorkCenterCalendar, WorkOrderOperationSchedule, WorkCenter.",
    "outputShape": "One row per month and work center."
  },
  "managerial/21_operation_delay_and_bottleneck_review.sql": {
    "category": "managerial",
    "filename": "21_operation_delay_and_bottleneck_review.sql",
    "publicPath": "/managerial/21_operation_delay_and_bottleneck_review.sql",
    "teachingObjective": "Review planned versus actual operation timing and highlight bottleneck-prone work centers.",
    "mainTables": "WorkOrderOperation, RoutingOperation, WorkCenter, WorkOrder, Item.",
    "outputShape": "One row per work-order operation."
  },
  "managerial/22_backlog_aging_by_work_center.sql": {
    "category": "managerial",
    "filename": "22_backlog_aging_by_work_center.sql",
    "publicPath": "/managerial/22_backlog_aging_by_work_center.sql",
    "teachingObjective": "Show open operation backlog and how far those operations sit past their planned end dates.",
    "mainTables": "WorkOrderOperation, WorkOrder, RoutingOperation, WorkCenter.",
    "outputShape": "One row per open work-order operation."
  },
  "managerial/23_shift_adherence_and_overtime_by_work_center.sql": {
    "category": "managerial",
    "filename": "23_shift_adherence_and_overtime_by_work_center.sql",
    "publicPath": "/managerial/23_shift_adherence_and_overtime_by_work_center.sql",
    "teachingObjective": "Review shift adherence and overtime concentration by work center and month.",
    "mainTables": "TimeClockEntry, ShiftDefinition, EmployeeShiftAssignment, WorkCenter, Employee.",
    "outputShape": "One row per month, shift, and work-center grouping."
  },
  "managerial/24_approved_clock_hours_vs_labor_allocation.sql": {
    "category": "managerial",
    "filename": "24_approved_clock_hours_vs_labor_allocation.sql",
    "publicPath": "/managerial/24_approved_clock_hours_vs_labor_allocation.sql",
    "teachingObjective": "Compare approved direct-labor time-clock hours to the labor allocation recorded against work-order operations.",
    "mainTables": "TimeClockEntry, LaborTimeEntry, WorkOrderOperation, RoutingOperation, WorkCenter, WorkOrder.",
    "outputShape": "One row per month, work center, and routing operation."
  },
  "managerial/25_backorder_fill_rate_and_shipment_lag.sql": {
    "category": "managerial",
    "filename": "25_backorder_fill_rate_and_shipment_lag.sql",
    "publicPath": "/managerial/25_backorder_fill_rate_and_shipment_lag.sql",
    "teachingObjective": "Measure fill rate, remaining backorder quantity, and shipment lag from order entry.",
    "mainTables": "SalesOrder, SalesOrderLine, Shipment, ShipmentLine, Item.",
    "outputShape": "One row per order month and item group."
  },
  "managerial/26_returns_and_refund_impact_by_customer_and_item.sql": {
    "category": "managerial",
    "filename": "26_returns_and_refund_impact_by_customer_and_item.sql",
    "publicPath": "/managerial/26_returns_and_refund_impact_by_customer_and_item.sql",
    "teachingObjective": "Review how returned quantity, credit activity, and refunds affect customer and item-group performance.",
    "mainTables": "CreditMemo, CreditMemoLine, SalesReturnLine, CustomerRefund, Customer, Item.",
    "outputShape": "One row per credit-memo month, customer region, and item grouping."
  },
  "managerial/27_supplier_lead_time_and_receipt_reliability.sql": {
    "category": "managerial",
    "filename": "27_supplier_lead_time_and_receipt_reliability.sql",
    "publicPath": "/managerial/27_supplier_lead_time_and_receipt_reliability.sql",
    "teachingObjective": "Review supplier lead time and receipt reliability from purchase order to first and final receipt.",
    "mainTables": "PurchaseOrder, PurchaseOrderLine, GoodsReceipt, GoodsReceiptLine, Supplier.",
    "outputShape": "One row per order month and supplier."
  },
  "managerial/28_paid_hours_vs_productive_labor_by_work_center.sql": {
    "category": "managerial",
    "filename": "28_paid_hours_vs_productive_labor_by_work_center.sql",
    "publicPath": "/managerial/28_paid_hours_vs_productive_labor_by_work_center.sql",
    "teachingObjective": "Compare approved paid hours to productive labor allocation by work center and month.",
    "mainTables": "TimeClockEntry, LaborTimeEntry, WorkOrderOperation, WorkCenter, ShiftDefinition.",
    "outputShape": "One row per month and work center."
  },
  "managerial/29_headcount_by_cost_center_job_family_status.sql": {
    "category": "managerial",
    "filename": "29_headcount_by_cost_center_job_family_status.sql",
    "publicPath": "/managerial/29_headcount_by_cost_center_job_family_status.sql",
    "teachingObjective": "Review workforce composition by cost center, job family, level, and employment status.",
    "mainTables": "Employee, CostCenter.",
    "outputShape": "One row per cost center, job family, job level, and employment status."
  },
  "managerial/30_sales_margin_by_collection_style_material.sql": {
    "category": "managerial",
    "filename": "30_sales_margin_by_collection_style_material.sql",
    "publicPath": "/managerial/30_sales_margin_by_collection_style_material.sql",
    "teachingObjective": "Compare billed sales, credits, net sales, cost, and gross margin by product collection and lifecycle attributes.",
    "mainTables": "SalesInvoiceLine, ShipmentLine, CreditMemoLine, SalesReturnLine, Item.",
    "outputShape": "One row per item group, collection, style family, material, and lifecycle status."
  },
  "managerial/31_product_portfolio_mix_by_collection_style_lifecycle_supply_mode.sql": {
    "category": "managerial",
    "filename": "31_product_portfolio_mix_by_collection_style_lifecycle_supply_mode.sql",
    "publicPath": "/managerial/31_product_portfolio_mix_by_collection_style_lifecycle_supply_mode.sql",
    "teachingObjective": "Review the product portfolio by collection, style family, lifecycle, and supply mode with both SKU counts and billed activity.",
    "mainTables": "Item, SalesInvoiceLine.",
    "outputShape": "One row per sellable portfolio grouping."
  },
  "managerial/32_contribution_margin_by_collection_material_lifecycle_supply_mode.sql": {
    "category": "managerial",
    "filename": "32_contribution_margin_by_collection_material_lifecycle_supply_mode.sql",
    "publicPath": "/managerial/32_contribution_margin_by_collection_material_lifecycle_supply_mode.sql",
    "teachingObjective": "Compare contribution margin by collection, material, lifecycle, and supply mode.",
    "mainTables": "SalesInvoiceLine, CreditMemoLine, Item.",
    "outputShape": "One row per item group and portfolio attribute grouping."
  },
  "managerial/33_customer_service_impact_by_collection_style.sql": {
    "category": "managerial",
    "filename": "33_customer_service_impact_by_collection_style.sql",
    "publicPath": "/managerial/33_customer_service_impact_by_collection_style.sql",
    "teachingObjective": "Review customer-service performance by collection and style family using shipment lag, fill rate, and backorder pressure.",
    "mainTables": "SalesOrder, SalesOrderLine, Shipment, ShipmentLine, Item.",
    "outputShape": "One row per item group, collection, and style family."
  },
  "managerial/34_labor_and_headcount_by_work_location_job_family_cost_center.sql": {
    "category": "managerial",
    "filename": "34_labor_and_headcount_by_work_location_job_family_cost_center.sql",
    "publicPath": "/managerial/34_labor_and_headcount_by_work_location_job_family_cost_center.sql",
    "teachingObjective": "Compare headcount, payroll cost, approved time, and direct labor by work location, job family, and cost center.",
    "mainTables": "Employee, CostCenter, PayrollRegister, TimeClockEntry, LaborTimeEntry.",
    "outputShape": "One row per work location, cost center, and job family grouping."
  },
  "managerial/35_portfolio_return_refund_impact_by_collection_lifecycle.sql": {
    "category": "managerial",
    "filename": "35_portfolio_return_refund_impact_by_collection_lifecycle.sql",
    "publicPath": "/managerial/35_portfolio_return_refund_impact_by_collection_lifecycle.sql",
    "teachingObjective": "Compare return, credit, and refund impact by collection and lifecycle status.",
    "mainTables": "SalesInvoiceLine, CreditMemo, CreditMemoLine, CustomerRefund, Item.",
    "outputShape": "One row per item group, collection, and lifecycle grouping."
  },
  "managerial/36_staffing_coverage_vs_work_center_planned_load.sql": {
    "category": "managerial",
    "filename": "36_staffing_coverage_vs_work_center_planned_load.sql",
    "publicPath": "/managerial/36_staffing_coverage_vs_work_center_planned_load.sql",
    "teachingObjective": "Compare rostered staffing hours to scheduled work-center load at the daily grain with monthly rollup context.",
    "mainTables": "EmployeeShiftRoster, WorkOrderOperationSchedule, WorkCenter.",
    "outputShape": "One row per work center and calendar day with rostered hours, scheduled load hours, and the coverage gap."
  },
  "managerial/37_rostered_vs_worked_hours_by_work_center_shift.sql": {
    "category": "managerial",
    "filename": "37_rostered_vs_worked_hours_by_work_center_shift.sql",
    "publicPath": "/managerial/37_rostered_vs_worked_hours_by_work_center_shift.sql",
    "teachingObjective": "Compare planned rostered hours to approved worked hours by work center, shift, and month.",
    "mainTables": "EmployeeShiftRoster, TimeClockEntry, ShiftDefinition, WorkCenter.",
    "outputShape": "One row per month, work center, and shift with planned hours, worked hours, and variance."
  },
  "managerial/38_absence_rate_by_work_location_job_family_month.sql": {
    "category": "managerial",
    "filename": "38_absence_rate_by_work_location_job_family_month.sql",
    "publicPath": "/managerial/38_absence_rate_by_work_location_job_family_month.sql",
    "teachingObjective": "Measure absence rates by month, work location, and job family.",
    "mainTables": "EmployeeAbsence, EmployeeShiftRoster, Employee.",
    "outputShape": "One row per month, work location, and job family with absence hours, rostered hours, and absence rate."
  },
  "managerial/39_overtime_approval_coverage_and_concentration.sql": {
    "category": "managerial",
    "filename": "39_overtime_approval_coverage_and_concentration.sql",
    "publicPath": "/managerial/39_overtime_approval_coverage_and_concentration.sql",
    "teachingObjective": "Review how overtime hours concentrate by work center and how consistently those hours carry overtime approvals.",
    "mainTables": "TimeClockEntry, OvertimeApproval, WorkCenter.",
    "outputShape": "One row per month and work center with overtime totals and approval coverage metrics."
  },
  "managerial/40_punch_to_pay_bridge_for_hourly_workers.sql": {
    "category": "managerial",
    "filename": "40_punch_to_pay_bridge_for_hourly_workers.sql",
    "publicPath": "/managerial/40_punch_to_pay_bridge_for_hourly_workers.sql",
    "teachingObjective": "Trace hourly payroll from raw punch counts through approved time, labor allocation, and gross pay.",
    "mainTables": "TimeClockPunch, TimeClockEntry, LaborTimeEntry, PayrollRegister, Employee.",
    "outputShape": "One row per hourly employee and payroll period."
  },
  "managerial/41_late_arrival_early_departure_by_shift_department.sql": {
    "category": "managerial",
    "filename": "41_late_arrival_early_departure_by_shift_department.sql",
    "publicPath": "/managerial/41_late_arrival_early_departure_by_shift_department.sql",
    "teachingObjective": "Measure late-arrival and early-departure patterns by shift and department.",
    "mainTables": "EmployeeShiftRoster, TimeClockEntry, ShiftDefinition.",
    "outputShape": "One row per month, department, and shift."
  },
  "managerial/42_inventory_coverage_and_projected_stockout_risk.sql": {
    "category": "managerial",
    "filename": "42_inventory_coverage_and_projected_stockout_risk.sql",
    "publicPath": "/managerial/42_inventory_coverage_and_projected_stockout_risk.sql",
    "teachingObjective": "Estimate inventory coverage and stockout risk from the latest planning recommendation state.",
    "mainTables": "SupplyPlanRecommendation, DemandForecast, Item, Warehouse.",
    "outputShape": "One row per item and warehouse at the latest planned week."
  },
  "managerial/43_rough_cut_capacity_load_vs_available_hours.sql": {
    "category": "managerial",
    "filename": "43_rough_cut_capacity_load_vs_available_hours.sql",
    "publicPath": "/managerial/43_rough_cut_capacity_load_vs_available_hours.sql",
    "teachingObjective": "Compare rough-cut planned load to available hours by work center and week.",
    "mainTables": "RoughCutCapacityPlan, WorkCenter.",
    "outputShape": "One row per work center and week."
  },
  "managerial/44_expedite_pressure_by_item_family_and_month.sql": {
    "category": "managerial",
    "filename": "44_expedite_pressure_by_item_family_and_month.sql",
    "publicPath": "/managerial/44_expedite_pressure_by_item_family_and_month.sql",
    "teachingObjective": "Measure how often planning pressure escalates to expedite recommendations.",
    "mainTables": "SupplyPlanRecommendation, Item.",
    "outputShape": "One row per month and item-family slice."
  },
  "managerial/45_forecast_error_and_bias_by_collection_style_family.sql": {
    "category": "managerial",
    "filename": "45_forecast_error_and_bias_by_collection_style_family.sql",
    "publicPath": "/managerial/45_forecast_error_and_bias_by_collection_style_family.sql",
    "teachingObjective": "Summarize forecast error and bias by collection and style family.",
    "mainTables": "DemandForecast, SalesOrder, SalesOrderLine, Item.",
    "outputShape": "One row per collection and style family."
  },
  "managerial/46_supply_plan_driver_mix_by_collection_and_supply_mode.sql": {
    "category": "managerial",
    "filename": "46_supply_plan_driver_mix_by_collection_and_supply_mode.sql",
    "publicPath": "/managerial/46_supply_plan_driver_mix_by_collection_and_supply_mode.sql",
    "teachingObjective": "Review recommendation mix by planning driver, collection, and supply mode.",
    "mainTables": "SupplyPlanRecommendation, Item.",
    "outputShape": "One row per collection, supply mode, and driver."
  },
  "managerial/47_sales_rep_override_rate_and_discount_dispersion.sql": {
    "category": "managerial",
    "filename": "47_sales_rep_override_rate_and_discount_dispersion.sql",
    "publicPath": "/managerial/47_sales_rep_override_rate_and_discount_dispersion.sql",
    "teachingObjective": "Review override concentration and promotion discount dispersion by sales rep and customer segment.",
    "mainTables": "SalesOrder, SalesOrderLine, Employee, Customer.",
    "outputShape": "One row per sales rep and customer segment."
  },
  "managerial/48_collection_revenue_margin_before_after_promotions.sql": {
    "category": "managerial",
    "filename": "48_collection_revenue_margin_before_after_promotions.sql",
    "publicPath": "/managerial/48_collection_revenue_margin_before_after_promotions.sql",
    "teachingObjective": "Compare collection-level revenue before promotions to net revenue after promotions.",
    "mainTables": "SalesInvoiceLine, ShipmentLine, SalesInvoice, Item.",
    "outputShape": "One row per month and collection."
  },
  "managerial/49_customer_specific_pricing_concentration_and_dependency.sql": {
    "category": "managerial",
    "filename": "49_customer_specific_pricing_concentration_and_dependency.sql",
    "publicPath": "/managerial/49_customer_specific_pricing_concentration_and_dependency.sql",
    "teachingObjective": "Show which customers depend most on customer-specific pricing instead of segment pricing.",
    "mainTables": "SalesOrder, SalesOrderLine, Customer.",
    "outputShape": "One row per customer."
  },
  "managerial/50_monthly_price_floor_pressure_and_override_concentration.sql": {
    "category": "managerial",
    "filename": "50_monthly_price_floor_pressure_and_override_concentration.sql",
    "publicPath": "/managerial/50_monthly_price_floor_pressure_and_override_concentration.sql",
    "teachingObjective": "Review how often sales lines sit at or below the price floor and how often override approvals are used.",
    "mainTables": "SalesOrder, SalesOrderLine, PriceListLine.",
    "outputShape": "One row per month."
  },
  "managerial/51_budget_vs_actual_revenue_price_volume_cost_bridge.sql": {
    "category": "managerial",
    "filename": "51_budget_vs_actual_revenue_price_volume_cost_bridge.sql",
    "publicPath": "/managerial/51_budget_vs_actual_revenue_price_volume_cost_bridge.sql",
    "teachingObjective": "Compare budgeted and actual quantity, revenue, price realization, and standard-cost consumption by collection and style family.",
    "mainTables": "BudgetLine, Item, SalesInvoice, SalesInvoiceLine.",
    "outputShape": "One row per fiscal month, collection, and style family."
  },
  "managerial/52_design_service_engagement_utilization_and_labor_margin.sql": {
    "category": "managerial",
    "filename": "52_design_service_engagement_utilization_and_labor_margin.sql",
    "publicPath": "/managerial/52_design_service_engagement_utilization_and_labor_margin.sql",
    "teachingObjective": "Compare engagement staffing mix, utilization, billed revenue, and labor margin for design services.",
    "mainTables": "ServiceEngagement, ServiceEngagementAssignment, ServiceTimeEntry, ServiceBillingLine, Customer, Employee.",
    "outputShape": "One row per service engagement."
  },
  "managerial/53_sales_commission_expense_by_rep_segment.sql": {
    "category": "managerial",
    "filename": "53_sales_commission_expense_by_rep_segment.sql",
    "publicPath": "/managerial/53_sales_commission_expense_by_rep_segment.sql",
    "teachingObjective": "Review sales commission expense by sales rep, revenue type, customer segment, and invoice month.",
    "mainTables": "SalesCommissionAccrual, SalesCommissionAdjustment, Employee, Customer.",
    "outputShape": "One row per sales rep, revenue type, customer segment, and fiscal month."
  }
};

export default queryManifest;
