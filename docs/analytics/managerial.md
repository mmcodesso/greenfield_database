---
title: Managerial Analytics
description: Starter managerial and cost-accounting analysis paths using the Greenfield dataset.
sidebar_label: Managerial Analytics
---

# Managerial Analytics Starter Guide

## Relevant Tables

| Topic | Main tables |
|---|---|
| Budget vs actual | `Budget`, `CostCenter`, `Account`, `GLEntry`, `JournalEntry` |
| Product portfolio and sales mix | `Item`, `SalesInvoiceLine`, `CreditMemoLine`, `ShipmentLine`, `SalesOrderLine`, `Customer` |
| Inventory and purchasing | `GoodsReceiptLine`, `ShipmentLine`, `SalesReturnLine`, `ProductionCompletionLine`, `PurchaseOrderLine`, `Supplier`, `Warehouse`, `Item` |
| BOM, routing, and work-center planning | `BillOfMaterial`, `BillOfMaterialLine`, `Routing`, `RoutingOperation`, `WorkCenter`, `WorkCenterCalendar`, `Item` |
| Work-order throughput and variance | `WorkOrder`, `WorkOrderOperation`, `WorkOrderOperationSchedule`, `MaterialIssueLine`, `ProductionCompletionLine`, `WorkOrderClose` |
| Labor, headcount, and payroll mix | `Employee`, `TimeClockEntry`, `LaborTimeEntry`, `PayrollRegister`, `WorkCenter`, `CostCenter` |

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
| Headcount by cost center, job family, and employment status | [29_headcount_by_cost_center_job_family_status.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/29_headcount_by_cost_center_job_family_status.sql) |
| Sales and margin by collection, style family, material, and lifecycle | [30_sales_margin_by_collection_style_material.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/30_sales_margin_by_collection_style_material.sql) |
| Product portfolio mix by collection, style, lifecycle, and supply mode | [31_product_portfolio_mix_by_collection_style_lifecycle_supply_mode.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/31_product_portfolio_mix_by_collection_style_lifecycle_supply_mode.sql) |
| Contribution margin by collection, material, lifecycle, and supply mode | [32_contribution_margin_by_collection_material_lifecycle_supply_mode.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/32_contribution_margin_by_collection_material_lifecycle_supply_mode.sql) |
| Customer-service impact by collection and style | [33_customer_service_impact_by_collection_style.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/33_customer_service_impact_by_collection_style.sql) |
| Labor and headcount by work location, job family, and cost center | [34_labor_and_headcount_by_work_location_job_family_cost_center.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/34_labor_and_headcount_by_work_location_job_family_cost_center.sql) |
| Portfolio return and refund impact by collection and lifecycle | [35_portfolio_return_refund_impact_by_collection_lifecycle.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/35_portfolio_return_refund_impact_by_collection_lifecycle.sql) |

## Phase 19 Pairings

- Use [Product Portfolio Profitability Case](cases/product-portfolio-profitability-case.md) when you want a portfolio, lifecycle, and contribution-margin sequence.
- Use [Workforce Cost and Org-Control Case](cases/workforce-cost-and-org-control-case.md) when you want workforce structure, labor mix, and approval concentration in one lab.
- Use [Product Portfolio Case](cases/product-portfolio-and-lifecycle-case.md) when you want a lighter Phase 18-style entry point before moving into the fuller Phase 19 pack.

## Interpretation Notes

- The item master now supports collection, style family, material, finish, color, lifecycle, and supply-mode analysis inside the existing `Item` table.
- The employee master now supports work location, job family, job level, employment status, and current-state active analysis without adding a separate HR-history model.
- Supply mode changes the meaning of cost analysis. Manufactured items can support both absorption and contribution-margin work because fixed overhead is stored separately.
- Portfolio mix and profitability should be read together with service-level measures such as fill rate, shipment lag, and return pressure.
- Work location and cost center answer different questions. Use both when students compare workforce structure to payroll or labor usage.
- The current manufacturing model is still a foundation. It supports operations, labor, and contribution-margin analysis without switching inventory valuation to actual cost.
