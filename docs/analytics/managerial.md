# Managerial Analytics Starter Guide

**Audience:** Students, instructors, and analysts using the dataset for planning, operational, and performance analysis.  
**Purpose:** Show how to work with budgets, cost centers, product mix, inventory movement, purchasing activity, BOMs, work orders, labor, and manufacturing variance.  
**What you will learn:** Which tables to use, how to join them, and which starter queries answer the most useful managerial questions.

> **Implemented in current generator:** Budget rows, cost centers, detailed O2C and P2P volume, item master data, warehouse movement, BOMs, routings, work centers, work-center calendars, work orders, work-order operations, work-order operation schedules, shift assignments, approved daily time clocks, labor time, production completions, payroll-driven direct labor, and manufacturing variance.

> **Planned future extension:** Raw punch-event detail, shift-level capacity analysis, and richer workforce-scheduling detail beyond the current work-center-hour model.

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
| Budget vs actual | [01_budget_vs_actual_by_cost_center.sql](../../queries/managerial/01_budget_vs_actual_by_cost_center.sql) |
| Sales mix | [02_sales_mix_by_customer_region_item_group.sql](../../queries/managerial/02_sales_mix_by_customer_region_item_group.sql) |
| Inventory movement | [03_inventory_movement_by_item_and_warehouse.sql](../../queries/managerial/03_inventory_movement_by_item_and_warehouse.sql) |
| Purchasing activity | [04_purchasing_activity_by_supplier_category.sql](../../queries/managerial/04_purchasing_activity_by_supplier_category.sql) |
| Cost center summary | [05_cost_center_activity_summary.sql](../../queries/managerial/05_cost_center_activity_summary.sql) |
| Basic product profitability | [06_basic_product_profitability.sql](../../queries/managerial/06_basic_product_profitability.sql) |
| BOM standard cost rollup | [07_bom_standard_cost_rollup.sql](../../queries/managerial/07_bom_standard_cost_rollup.sql) |
| Work-order throughput | [08_work_order_throughput_by_month.sql](../../queries/managerial/08_work_order_throughput_by_month.sql) |
| Material usage and scrap | [09_material_usage_and_scrap_review.sql](../../queries/managerial/09_material_usage_and_scrap_review.sql) |
| Production completions and FG availability | [10_production_completion_and_fg_availability.sql](../../queries/managerial/10_production_completion_and_fg_availability.sql) |
| Manufacturing variance | [11_manufacturing_variance_by_month_item_group.sql](../../queries/managerial/11_manufacturing_variance_by_month_item_group.sql) |
| Direct labor by work order | [12_direct_labor_by_work_order_and_employee_class.sql](../../queries/managerial/12_direct_labor_by_work_order_and_employee_class.sql) |
| Unit-cost bridge | [13_unit_cost_bridge_dm_dl_varoh_fixedoh.sql](../../queries/managerial/13_unit_cost_bridge_dm_dl_varoh_fixedoh.sql) |
| Absorption vs contribution margin | [14_absorption_vs_contribution_margin.sql](../../queries/managerial/14_absorption_vs_contribution_margin.sql) |
| Manufactured vs purchased margin comparison | [15_manufactured_vs_purchased_margin_comparison.sql](../../queries/managerial/15_manufactured_vs_purchased_margin_comparison.sql) |
| Labor efficiency and rate variance | [16_labor_efficiency_and_rate_variance.sql](../../queries/managerial/16_labor_efficiency_and_rate_variance.sql) |
| Routing master review | [17_routing_master_review.sql](../../queries/managerial/17_routing_master_review.sql) |
| Work-center activity and operation labor | [18_work_center_activity_and_operation_hours.sql](../../queries/managerial/18_work_center_activity_and_operation_hours.sql) |
| Daily load vs capacity | [19_daily_load_vs_capacity.sql](../../queries/managerial/19_daily_load_vs_capacity.sql) |
| Monthly work-center utilization | [20_monthly_work_center_utilization.sql](../../queries/managerial/20_monthly_work_center_utilization.sql) |
| Operation delay and bottleneck review | [21_operation_delay_and_bottleneck_review.sql](../../queries/managerial/21_operation_delay_and_bottleneck_review.sql) |
| Backlog aging by work center | [22_backlog_aging_by_work_center.sql](../../queries/managerial/22_backlog_aging_by_work_center.sql) |
| Shift adherence and overtime by work center | [23_shift_adherence_and_overtime_by_work_center.sql](../../queries/managerial/23_shift_adherence_and_overtime_by_work_center.sql) |
| Approved clock hours versus labor allocation | [24_approved_clock_hours_vs_labor_allocation.sql](../../queries/managerial/24_approved_clock_hours_vs_labor_allocation.sql) |

## Interpretation Notes

- The item master now mixes purchased and manufactured finished goods.
- `StandardCost` on manufactured items includes BOM-based material cost plus standard direct labor, variable overhead, and fixed overhead.
- Routing tables explain how manufactured items move through operations and which work centers perform the work.
- Work-center calendars and operation schedules now support daily load-versus-capacity and backlog analysis.
- `LaborTimeEntry.WorkOrderOperationID` supports operation-level labor analysis without switching inventory valuation to actual cost.
- `TimeClockEntry` adds an attendance layer for hourly employees, which makes overtime and shift-adherence analysis possible.
- Contribution margin excludes fixed overhead. Absorption margin includes it.
- Manufacturing variance analysis belongs with `WorkOrderClose`, not only with `GLEntry`.
- The current model is still a foundation: it includes shift assignments and approved daily time clocks, but it does not yet include raw punch-event tables, rotating shift rosters, or multi-level BOMs.
