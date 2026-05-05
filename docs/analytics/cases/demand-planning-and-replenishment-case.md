---
title: Demand Planning and Replenishment Case
description: Inquiry-led walkthrough for forecast quality, supply-plan drivers, projected availability, expedite pressure, and rough-cut capacity response.
sidebar_label: Demand Planning Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# Demand Planning and Replenishment Case

## Business Scenario

The planning team reviews replenishment weekly, long before receipts, work orders, or monthly financial results appear. Forecasts set the demand signal. Inventory policy shapes the expected buffer. Supply recommendations translate that planning state into proposed replenishment actions across purchased and manufactured items.

Pressure builds when that planning layer stops lining up cleanly. Some item families show systematic forecast bias. Some recommendations come from backlog or safety-stock pressure rather than forecast alone. Some items move toward low projected availability and stockout risk. Manufactured demand can also tighten rough-cut capacity before any work order is released.

This case stays at the planning layer. Your job is to explain why the recommendation pool exists, where urgency starts rising, and which capacity signals show strain before execution begins.

## The Problem to Solve

You need to prove where forecast demand diverges from actual order demand, what is driving the recommendation pool, where projected availability looks weak, and where recommendation pressure escalates into expedites and rough-cut capacity strain. You also need to explain which planning issue deserves management follow-up first.

## What You Need to Develop

- A forecast-quality narrative that explains where weekly demand signals diverge from actual order intake.
- A supply-plan explanation that separates forecast-driven replenishment from backlog, safety-stock, and component-demand pressure.
- A projected-availability interpretation that identifies the areas with the strongest stockout risk.
- An urgency and conversion explanation tied to expedites and recommendation follow-through.
- A short management-facing recommendation on which planning issue should move next into audit review or execution follow-through.

## Before You Start

- Main tables: `DemandForecast`, `InventoryPolicy`, `SupplyPlanRecommendation`, `MaterialRequirementPlan`, `RoughCutCapacityPlan`, `PurchaseRequisition`, `WorkOrder`, `Item`
- Related guides: [Operations and Risk](../reports/operations-and-risk.md), [Managerial Analytics](../managerial.md)
- Related process pages: [Manufacturing Process](../../processes/manufacturing.md), [Procure-to-Pay Process](../../processes/p2p.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case stays at the planning-signal layer before execution and audit follow-up. Use the replenishment audit case for planning-governance failures and the manufacturing process page when you need execution follow-through.

## Step-by-Step Walkthrough

### Step 1. Define the demand signal and forecast quality

Start with the demand signal itself. Before you explain replenishment pressure, you need to know whether forecast demand tracks actual order intake.

**What we are trying to achieve**

Measure where weekly forecast demand diverges from actual demand and identify where forecast bias appears systematic.

**Why this step changes the diagnosis**

This step anchors the diagnosis in signal quality. If forecast bias is concentrated in specific item families or lifecycle groups, later recommendation pressure becomes easier to explain.

**Suggested query**

<QueryReference
  queryKey="financial/23_forecast_vs_actual_demand_by_week_item_group_collection_lifecycle.sql"
  helperText="Use this first to compare weekly forecast demand with actual order demand by item family slice."
/>

<QueryReference
  queryKey="managerial/45_forecast_error_and_bias_by_collection_style_family.sql"
  helperText="Use this follow-through query to identify where forecast error and bias look systematic at the collection and style-family level."
/>

**What this query does**

The first query compares weekly forecast quantity to weekly actual order quantity. The second summarizes forecast error and bias at a higher portfolio level.

**How it works**

The first query aggregates `DemandForecast` by forecast week and matches it to weekly `SalesOrderLine` demand through `Item`. The second rolls forecast and actual demand up by collection and style family so persistent bias is easier to spot.

**What to look for in the result**

- weeks where forecast quantity and actual order quantity separate materially
- item groups or lifecycle slices with recurring overforecast or underforecast patterns
- collections or style families where forecast bias looks systematic
- whether the planning problem looks broad or concentrated

### Step 2. Explain what is driving the recommendation pool

Once the signal quality is clear, explain why recommendations exist. Forecast is only one driver.

**What we are trying to achieve**

Separate forecast-driven replenishment from backlog, safety-stock, and component-demand drivers.

**Why this step changes the diagnosis**

This step separates the cause of the recommendation pool. A forecast-driven recommendation and a backlog-driven recommendation carry different planning meaning.

**Suggested query**

<QueryReference
  queryKey="managerial/46_supply_plan_driver_mix_by_collection_and_supply_mode.sql"
  helperText="Use this to separate recommendation volume by planning driver, collection, and supply mode."
/>

**What this query does**

It summarizes the recommendation pool by collection, item group, supply mode, and `DriverType`.

**How it works**

The query starts from `SupplyPlanRecommendation`, joins `Item`, and groups recommendation counts and quantities by the descriptive fields that explain the planning mix.

**What to look for in the result**

- whether forecast-driven recommendations dominate the planning pool
- where backlog or safety-stock pressure becomes material
- how manufactured and purchased items differ in driver mix
- which collections carry the heaviest component-demand pressure

### Step 3. Measure projected availability and stockout risk

After you understand the recommendation mix, assess the planning state behind it. This is where projected availability and stockout risk become visible.

**What we are trying to achieve**

Identify the items and warehouses with weak projected coverage and rising stockout risk.

**Why this step changes the diagnosis**

This step turns the recommendation story into service-risk interpretation. It shows where planning pressure is already threatening future availability.

**Suggested query**

<QueryReference
  queryKey="managerial/42_inventory_coverage_and_projected_stockout_risk.sql"
  helperText="Use this to measure projected availability, average weekly forecast, and stockout risk at the latest planning state."
/>

**What this query does**

It estimates inventory coverage and projected stockout risk using the latest recommendation bucket and recent forecast demand.

**How it works**

The query finds the latest `SupplyPlanRecommendation` bucket, joins recent `DemandForecast` averages, and then compares projected availability, net requirement, and recommended quantity at the item-and-warehouse level.

**What to look for in the result**

- items with low projected availability
- item and warehouse combinations with clear stockout risk
- whether projected weakness aligns with the forecast and driver patterns from the earlier steps
- where planning pressure looks local rather than portfolio-wide

### Step 4. Show where planning pressure escalates into urgency and conversion

Now move from planning state to planner response. Urgency and conversion answer different questions and should stay separate.

**What we are trying to achieve**

Show where recommendation pressure turns into expedites and how planners are converting recommendations into follow-through activity.

**Why this step changes the diagnosis**

This step separates urgency from follow-through. Expedite pressure signals where planning pressure has escalated, while conversion status shows whether planners are acting on the recommendation pool.

**Suggested query**

<QueryReference
  queryKey="managerial/44_expedite_pressure_by_item_family_and_month.sql"
  helperText="Use this first to measure where expedite recommendations concentrate by month and item family."
/>

<QueryReference
  queryKey="financial/24_recommendation_conversion_by_type_priority_planner.sql"
  helperText="Use this follow-through query to show how recommendation volume and status vary by type, priority, and planner."
/>

**What this query does**

The first query measures expedite concentration by month and item family. The second summarizes recommendation volume, quantity, and status by recommendation type, priority, driver, and planner.

**How it works**

The expedite query groups `SupplyPlanRecommendation` by planning month and item-family slice and isolates recommendations marked `Expedite`. The conversion query groups the same recommendation population by planner and status to show how the pool is being handled.

**What to look for in the result**

- months where expedite pressure spikes
- item families carrying repeated expedite volume
- planners or recommendation types with heavier unresolved or open recommendation counts
- whether urgency and follow-through appear aligned or disconnected

### Step 5. Connect replenishment pressure to rough-cut capacity response

Finish by linking manufactured planning pressure to rough-cut capacity. This is the last planning step before execution begins.

**What we are trying to achieve**

Identify which work centers tighten first once manufactured replenishment pressure rises.

**Why this step changes the diagnosis**

This step connects manufactured planning pressure to capacity response. Rough-cut capacity shows where the pressure becomes operationally meaningful before work orders are scheduled in detail.

**Suggested query**

<QueryReference
  queryKey="managerial/43_rough_cut_capacity_load_vs_available_hours.sql"
  helperText="Use this to compare rough-cut planned load with available hours by work center and week."
/>

**What this query does**

It summarizes weekly planned load, available hours, utilization, and capacity status by work center.

**How it works**

The query starts from `RoughCutCapacityPlan`, joins `WorkCenter`, aggregates planned load at the weekly work-center grain, and compares that load to available hours to classify capacity status.

**What to look for in the result**

- work centers that move into tight or over-capacity status first
- weeks where capacity pressure overlaps with expedite pressure
- whether manufactured planning pressure concentrates in a narrow set of centers
- which issue should move next into [Manufacturing Process](../../processes/manufacturing.md) for execution follow-through or [Replenishment Support Audit Case](replenishment-support-audit-case.md) for planning-control follow-up

## Required Student Output

Submit a short case memo or notebook note with these four artifacts:

- Evidence summary: identify the key result rows, metrics, timing patterns, or exception families that changed your diagnosis.
- Accounting or business interpretation: explain what the evidence means for the process, accounting treatment, managerial decision, or control risk.
- Database explanation: name the source tables, row grain, join keys, or trace path that make the evidence defensible.
- Management or audit conclusion: state which driver, document path, or exception family should be followed up first and why.

## Optional Excel Follow-Through

1. Build one weekly pivot for forecast quantity versus actual order quantity by item family or collection.
2. Add a forecast-error tab that ranks overforecast and underforecast patterns by collection and style family.
3. Build one recommendation tab for driver mix and projected coverage.
4. Add one urgency tab for expedite concentration and recommendation conversion by planner.
5. Finish with one rough-cut capacity tab and a short conclusion on whether follow-up belongs in planning, manufacturing execution, or replenishment audit.

## Wrap-Up Questions

- Accounting/process: Which planning signal best explains replenishment pressure before execution begins?
- Database/source evidence: Which item, week, warehouse, recommendation, or work-center grain supports your conclusion?
- Analytics judgment: Where do forecast bias, projected stockout risk, expedite pressure, and capacity tightness overlap?
- Escalation/next step: Should the next action stay in planning, move to manufacturing execution, or move into the replenishment audit case?

## Next Steps

- Use [Replenishment Support Audit Case](replenishment-support-audit-case.md) when you want to test forecast approval, policy coverage, unsupported planning documents, and late recommendation conversion.
- Use [Manufacturing Process](../../processes/manufacturing.md) when you want to trace rough-cut pressure into released work orders and detailed operation schedules.
- Use [Operations and Risk](../reports/operations-and-risk.md) when you want the broader report-level interpretation of the same planning signals.
- Use [Managerial Analytics](../managerial.md) for the wider planning, capacity, and supply-risk query set.
