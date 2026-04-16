---
title: Replenishment Support Audit Case
description: Guided audit case for planning approval, policy, and replenishment-support controls.
sidebar_label: Replenishment Audit Case
---

# Replenishment Support Audit Case

## Audience and Purpose

- audience: auditing, AIS, and accounting analytics students
- purpose: test whether purchase requisitions and work orders remain traceable to approved planning support

## Business Scenario

The dataset expects weekly planning support behind normal replenishment activity. The audit task is to identify missing forecast approval, inactive policy coverage, unsupported requisitions or work orders, late recommendation conversion, and prelaunch or discontinued planning activity.

## Query Sequence

1. [42_forecast_approval_and_override_review.sql](../../../queries/audit/42_forecast_approval_and_override_review.sql)
2. [43_inactive_or_stale_inventory_policy_review.sql](../../../queries/audit/43_inactive_or_stale_inventory_policy_review.sql)
3. [44_requisitions_and_work_orders_without_planning_support.sql](../../../queries/audit/44_requisitions_and_work_orders_without_planning_support.sql)
4. [45_recommendation_converted_after_need_by_date_review.sql](../../../queries/audit/45_recommendation_converted_after_need_by_date_review.sql)
5. [46_discontinued_or_prelaunch_planning_activity_review.sql](../../../queries/audit/46_discontinued_or_prelaunch_planning_activity_review.sql)

## Suggested Excel Sequence

1. trace the primary keys from the query results into `DemandForecast`, `InventoryPolicy`, `SupplyPlanRecommendation`, `PurchaseRequisition`, and `WorkOrder`
2. compare the audit SQL results to the source-table detail

## What Students Should Notice

- approval failure and override outlier are different control failures
- policy inactivity can break planning support before transaction execution fails
- unsupported requisitions and work orders are document-trace failures as well as planning failures
- late conversion is a timing-control issue even when the source recommendation exists

## Follow-Up Questions

1. Which anomalies indicate poor planning governance versus poor execution timing?
2. How would you separate planning-master exceptions from replenishment-document exceptions in an audit memo?
3. Which planning control failures could cascade into inventory, capacity, or cash-cycle issues?
