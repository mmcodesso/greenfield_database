---
title: Managerial Analytics
description: Starter managerial and cost-accounting analysis paths using the Greenfield dataset.
sidebar_label: Managerial Analytics
---

# Managerial Analytics Starter Guide

**Audience:** Students, instructors, and analysts using the dataset for planning, operational, and performance analysis.  
**Purpose:** Show how to work with budgets, cost centers, product mix, inventory movement, purchasing activity, BOMs, work orders, labor, and manufacturing variance.  
**What you will learn:** Which tables to use, how to join them, and which starter queries answer the most useful managerial questions.


## Relevant Tables

| Topic | Main tables |
|---|---|
| Budget vs actual | `Budget`, `CostCenter`, `Account`, `GLEntry`, `JournalEntry` |
| Sales mix | `SalesInvoice`, `SalesInvoiceLine`, `Customer`, `Item` |
| Inventory movement | `GoodsReceiptLine`, `ShipmentLine`, `SalesReturnLine`, `ProductionCompletionLine`, `Warehouse`, `Item` |
| Purchasing behavior | `PurchaseOrder`, `PurchaseOrderLine`, `Supplier`, `Item` |
| BOM and standard cost | `BillOfMaterial`, `BillOfMaterialLine`, `Item` |
| Routing and work-center planning | `Routing`, `RoutingOperation`, `WorkCenter`, `WorkCenterCalendar`, `Item` |
| Work-order throughput | `WorkOrder`, `ProductionCompletion`, `WorkOrderClose` |
| Operation throughput and labor | `WorkOrderOperation`, `WorkOrderOperationSchedule`, `RoutingOperation`, `WorkCenter`, `WorkCenterCalendar`, `LaborTimeEntry`, `WorkOrder` |
| Material usage and scrap | `WorkOrder`, `BillOfMaterialLine`, `MaterialIssueLine`, `ProductionCompletionLine` |
| Direct labor and payroll cost | `TimeClockEntry`, `LaborTimeEntry`, `PayrollRegister`, `Employee`, `ShiftDefinition`, `WorkOrder`, `Item` |
| Manufacturing variance | `WorkOrderClose`, `WorkOrder`, `Item`, `Warehouse` |

## Starter SQL Map

| Topic | Starter SQL file |
|---|---|
| Budget vs actual | [01_budget_vs_actual_by_cost_center.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/01_budget_vs_actual_by_cost_center.sql) |
| Sales mix | [02_sales_mix_by_customer_region_item_group.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/02_sales_mix_by_customer_region_item_group.sql) |
| Inventory movement | [03_inventory_movement_by_item_and_warehouse.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/03_inventory_movement_by_item_and_warehouse.sql) |
| Purchasing activity | [04_purchasing_activity_by_supplier_category.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/04_purchasing_activity_by_supplier_category.sql) |
| Cost center summary | [05_cost_center_activity_summary.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/05_cost_center_activity_summary.sql) |
| Basic product profitability | [06_basic_product_profitability.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/06_basic_product_profitability.sql) |
| BOM standard cost rollup | [07_bom_standard_cost_rollup.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/07_bom_standard_cost_rollup.sql) |
| Work-order throughput | [08_work_order_throughput_by_month.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/08_work_order_throughput_by_month.sql) |
| Material usage and scrap | [09_material_usage_and_scrap_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/09_material_usage_and_scrap_review.sql) |
| Production completions and FG availability | [10_production_completion_and_fg_availability.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/10_production_completion_and_fg_availability.sql) |
| Manufacturing variance | [11_manufacturing_variance_by_month_item_group.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/11_manufacturing_variance_by_month_item_group.sql) |
| Direct labor by work order | [12_direct_labor_by_work_order_and_employee_class.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/12_direct_labor_by_work_order_and_employee_class.sql) |
| Unit-cost bridge | [13_unit_cost_bridge_dm_dl_varoh_fixedoh.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/13_unit_cost_bridge_dm_dl_varoh_fixedoh.sql) |
| Absorption vs contribution margin | [14_absorption_vs_contribution_margin.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/14_absorption_vs_contribution_margin.sql) |
| Manufactured vs purchased margin comparison | [15_manufactured_vs_purchased_margin_comparison.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/15_manufactured_vs_purchased_margin_comparison.sql) |
| Labor efficiency and rate variance | [16_labor_efficiency_and_rate_variance.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/16_labor_efficiency_and_rate_variance.sql) |
| Routing master review | [17_routing_master_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/17_routing_master_review.sql) |
| Work-center activity and operation labor | [18_work_center_activity_and_operation_hours.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/18_work_center_activity_and_operation_hours.sql) |
| Daily load vs capacity | [19_daily_load_vs_capacity.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/19_daily_load_vs_capacity.sql) |
| Monthly work-center utilization | [20_monthly_work_center_utilization.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/20_monthly_work_center_utilization.sql) |
| Operation delay and bottleneck review | [21_operation_delay_and_bottleneck_review.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/21_operation_delay_and_bottleneck_review.sql) |
| Backlog aging by work center | [22_backlog_aging_by_work_center.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/22_backlog_aging_by_work_center.sql) |
| Shift adherence and overtime by work center | [23_shift_adherence_and_overtime_by_work_center.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/23_shift_adherence_and_overtime_by_work_center.sql) |
| Approved clock hours versus labor allocation | [24_approved_clock_hours_vs_labor_allocation.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/24_approved_clock_hours_vs_labor_allocation.sql) |
| Backorder fill rate and shipment lag | [25_backorder_fill_rate_and_shipment_lag.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/25_backorder_fill_rate_and_shipment_lag.sql) |
| Returns and refund impact by customer and item | [26_returns_and_refund_impact_by_customer_and_item.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/26_returns_and_refund_impact_by_customer_and_item.sql) |
| Supplier lead time and receipt reliability | [27_supplier_lead_time_and_receipt_reliability.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/27_supplier_lead_time_and_receipt_reliability.sql) |
| Paid hours versus productive labor by work center | [28_paid_hours_vs_productive_labor_by_work_center.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/28_paid_hours_vs_productive_labor_by_work_center.sql) |

## Interpretation Notes

- The item master now mixes purchased and manufactured finished goods.
- `StandardCost` on manufactured items includes BOM-based material cost plus standard direct labor, variable overhead, and fixed overhead.
- Routing tables explain how manufactured items move through operations and which work centers perform the work.
- Work-center calendars and operation schedules now support daily load-versus-capacity and backlog analysis.
- `LaborTimeEntry.WorkOrderOperationID` supports operation-level labor analysis without switching inventory valuation to actual cost.
- `TimeClockEntry` adds an attendance layer for hourly employees, which makes overtime and shift-adherence analysis possible.
- Shipment lag and backorder review belong in managerial analysis because they show how inventory and production capacity affect customer service.
- Returns and refund review belongs here when the goal is operational performance and margin impact rather than audit exception work.
- Contribution margin excludes fixed overhead. Absorption margin includes it.
- Manufacturing variance analysis belongs with `WorkOrderClose`, not only with `GLEntry`.
- The current model is still a foundation: it includes shift assignments and approved daily time clocks, but it does not yet include raw punch-event tables, rotating shift rosters, or multi-level BOMs.
