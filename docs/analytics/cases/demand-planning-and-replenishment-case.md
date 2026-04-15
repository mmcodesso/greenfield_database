---
title: Demand Planning and Replenishment Case
description: Guided planning case using forecast, policy, recommendation, and rough-cut capacity tables.
sidebar_label: Demand Planning Case
---

# Demand Planning and Replenishment Case

## Audience and Purpose

- audience: managerial analytics, operations, cost accounting, and supply-chain planning students
- purpose: connect weekly demand forecasts to replenishment recommendations, purchase support, manufacturing release, and rough-cut capacity pressure

## Business Scenario

The dataset plans replenishment weekly. Students need to explain how forecasted demand becomes supply recommendations, why some recommendations are expedited, and where rough-cut capacity tightens before execution starts.

## Query Sequence

1. [23_forecast_vs_actual_demand_by_week_item_group_collection_lifecycle.sql](../../../queries/financial/23_forecast_vs_actual_demand_by_week_item_group_collection_lifecycle.sql)
2. [42_inventory_coverage_and_projected_stockout_risk.sql](../../../queries/managerial/42_inventory_coverage_and_projected_stockout_risk.sql)
3. [24_recommendation_conversion_by_type_priority_planner.sql](../../../queries/financial/24_recommendation_conversion_by_type_priority_planner.sql)
4. [43_rough_cut_capacity_load_vs_available_hours.sql](../../../queries/managerial/43_rough_cut_capacity_load_vs_available_hours.sql)
5. [44_expedite_pressure_by_item_family_and_month.sql](../../../queries/managerial/44_expedite_pressure_by_item_family_and_month.sql)
6. [46_supply_plan_driver_mix_by_collection_and_supply_mode.sql](../../../queries/managerial/46_supply_plan_driver_mix_by_collection_and_supply_mode.sql)

## Suggested Excel Sequence

1. open the dataset workbook sheets `DemandForecast`, `InventoryPolicy`, `SupplyPlanRecommendation`, `MaterialRequirementPlan`, and `RoughCutCapacityPlan`
2. build a weekly pivot from `DemandForecast`
3. compare latest projected availability and expedite counts from `SupplyPlanRecommendation`
4. chart weekly load versus available hours from `RoughCutCapacityPlan`

## What Students Should Notice

- forecast is weekly and warehouse-specific, but execution remains monthly
- expedited recommendations should concentrate in narrower item families and months, not across the full catalog
- manufactured demand creates both supply recommendations and rough-cut capacity pressure
- component demand appears separately from finished-good demand

## Follow-Up Questions

1. Which item families carry the highest recurring expedite pressure?
2. Where does forecast bias appear systematic?
3. Which work centers become tight first when manufactured demand rises?
4. How would a planner explain the mix of forecast-driven versus backlog-driven recommendations?
