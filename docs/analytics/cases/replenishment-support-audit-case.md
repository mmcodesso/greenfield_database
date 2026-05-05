---
title: Replenishment Support Audit Case
description: Inquiry-led walkthrough for planning approval, policy, and replenishment-support controls.
sidebar_label: Replenishment Audit Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# Replenishment Support Audit Case

## Business Scenario

The dataset expects weekly planning support behind normal replenishment activity. The audit task is to identify missing forecast approval, inactive policy coverage, unsupported requisitions or work orders, late recommendation conversion, and prelaunch or discontinued planning activity.

This case treats planning support as an audit trail rather than only a forecasting exercise. Students test whether replenishment documents still point back to approved planning logic and whether policy, approval, and conversion controls remain intact before execution begins.

## The Problem to Solve

The audit team needs to separate planning-governance failures from later execution failures and decide which unsupported replenishment documents create the strongest control concern.

## What You Need to Develop

- A forecast governance view that separates missing approval from unusual override behavior.
- An inventory policy coverage review for missing, duplicate, or inactive planning policies.
- A document-support test for requisitions and work orders that lack supply-plan recommendations.
- A recommendation timing view that identifies conversions after need-by date.
- A lifecycle control conclusion for prelaunch or discontinued planning activity.

## Before You Start

- Main tables: `DemandForecast`, `InventoryPolicy`, `SupplyPlanRecommendation`, `PurchaseRequisition`, `WorkOrder`, `Item`
- Related case: [Demand Planning and Replenishment Case](demand-planning-and-replenishment-case.md)
- Related guide: [Audit Analytics](../audit.md)
- Related report: [Operations and Risk](../reports/operations-and-risk.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case is the formal planning-support control test. Use the demand-planning case when you want to explain forecast quality, supply recommendations, and operational pressure before audit follow-up.

## Step-by-Step Walkthrough

### Step 1. Test forecast approval and override governance

Start with the forecast layer. If the forecast is missing approval or carries unusually large overrides, downstream replenishment recommendations may already rest on weak governance.

**What we are trying to achieve**

Identify weekly forecasts that lack approval or show unusually large overrides from baseline.

**Why this step changes the diagnosis**

This step separates forecast governance from later replenishment execution. Missing approval and override outliers are planning-control issues before they become inventory or purchasing problems.

**Suggested query**

<QueryReference
  queryKey="audit/42_forecast_approval_and_override_review.sql"
  helperText="Use this first to test missing forecast approval and unusually large forecast overrides."
/>

**What this query does**

It flags forecast rows with missing approver evidence or forecast quantities that are materially above or below the baseline forecast quantity.

**How it works**

The query starts from `DemandForecast`, joins `Item`, `Warehouse`, and planner/approver employees, calculates override quantity and forecast-to-baseline ratio, then keeps rows with missing approval or large override ratios.

**What to look for in the result**

- forecasts with no approver or approval date
- forecast-to-baseline ratios at unusually high or low levels
- planner or item patterns that repeat
- whether the issue is approval failure or override governance

### Step 2. Review inventory policy coverage

After forecast governance is tested, review the policy layer that should guide replenishment settings for active inventory items.

**What we are trying to achieve**

Find active inventory items that lack exactly one current active inventory policy by warehouse.

**Why this step changes the diagnosis**

Policy coverage can break planning support before any requisition or work order exists. Missing, duplicate, or inactive policies point to planning-master control failures.

**Suggested query**

<QueryReference
  queryKey="audit/43_inactive_or_stale_inventory_policy_review.sql"
  helperText="Use this to test missing, duplicate, or inactive inventory policy coverage."
/>

**What this query does**

It identifies active inventory item and warehouse combinations with missing active policies, duplicate active policies, or inactive policy rows.

**How it works**

The query builds active item and warehouse combinations, counts active policies by item and warehouse, then unions inactive policy rows that still exist for active items.

**What to look for in the result**

- missing active policy coverage
- duplicate active policy coverage
- inactive policy rows for active items
- whether exceptions cluster by item group, warehouse, or supply mode

### Step 3. Test unsupported replenishment documents

Once forecast and policy support are reviewed, test whether execution documents point back to planning recommendations.

**What we are trying to achieve**

Identify purchase requisitions and work orders that lack supply-plan recommendation support.

**Why this step changes the diagnosis**

Unsupported documents are the bridge from planning governance into execution risk. A requisition or work order can be operationally real but still fail the planning-support control.

**Suggested query**

<QueryReference
  queryKey="audit/44_requisitions_and_work_orders_without_planning_support.sql"
  helperText="Use this to find requisitions and work orders without supply-plan recommendation support."
/>

**What this query does**

It lists inventory purchase requisitions and work orders where `SupplyPlanRecommendationID` is missing.

**How it works**

The query selects unsupported `PurchaseRequisition` rows for inventory items, unions unsupported `WorkOrder` rows, joins `Item`, and retains document numbers, dates, quantities, and statuses.

**What to look for in the result**

- unsupported requisitions versus unsupported work orders
- document dates and statuses that suggest execution already moved forward
- item families or supply modes with repeated unsupported documents
- whether the source issue is missing recommendation support or downstream execution bypass

### Step 4. Review late recommendation conversion

After unsupported documents are isolated, test recommendations that did convert but converted too late.

**What we are trying to achieve**

Identify planning recommendations converted to requisitions or work orders after their need-by date.

**Why this step changes the diagnosis**

Late conversion is a timing-control issue. It is different from missing support because the recommendation exists, but the execution response did not happen within the planning window.

**Suggested query**

<QueryReference
  queryKey="audit/45_recommendation_converted_after_need_by_date_review.sql"
  helperText="Use this to find converted recommendations where document creation happened after need-by date."
/>

**What this query does**

It lists supply-plan recommendations where the converted requisition or work order date is later than the recommendation need-by date.

**How it works**

The query builds conversion matches for purchase requisitions and work orders, joins those matches to `SupplyPlanRecommendation` and `Item`, and keeps rows where the converted document date exceeds `NeedByDate`.

**What to look for in the result**

- recommendation types and priority codes with late conversion
- need-by dates versus converted document dates
- whether late conversion affects purchased or manufactured supply
- timing patterns that could cascade into expedites, stockouts, or capacity pressure

### Step 5. Close with lifecycle-inconsistent planning activity

Finish by testing whether planning activity occurs before launch or against discontinued inactive items.

**What we are trying to achieve**

Identify forecasts, recommendations, requisitions, and work orders tied to prelaunch or discontinued inactive items.

**Why this step changes the diagnosis**

Lifecycle misuse is not only a planning timing issue. It can signal item-master governance weakness that affects forecasts, supply recommendations, and execution documents together.

**Suggested query**

<QueryReference
  queryKey="audit/46_discontinued_or_prelaunch_planning_activity_review.sql"
  helperText="Use this to find planning-layer activity before launch or against discontinued inactive items."
/>

**What this query does**

It lists demand forecasts, supply recommendations, purchase requisitions, and work orders where activity occurs before item launch or against discontinued inactive items.

**How it works**

The query unions planning and replenishment source tables, joins each source to `Item`, compares activity dates to launch date, and keeps discontinued inactive item activity with positive quantity.

**What to look for in the result**

- source tables where lifecycle misuse appears first
- prelaunch activity dates compared with launch date
- discontinued inactive items with positive planned or execution quantity
- whether remediation belongs with planning owners or item-master owners

## Required Student Output

Submit a short case memo or notebook note with these four artifacts:

- Evidence summary: identify the key result rows, metrics, timing patterns, or exception families that changed your diagnosis.
- Accounting or business interpretation: explain what the evidence means for the process, accounting treatment, managerial decision, or control risk.
- Database explanation: name the source tables, row grain, join keys, or trace path that make the evidence defensible.
- Management or audit conclusion: state which driver, document path, or exception family should be followed up first and why.

## Optional Excel Follow-Through

1. Build one forecast governance tab for missing approval and override ratios.
2. Add one inventory policy tab by item, warehouse, supply mode, and policy exception.
3. Build one unsupported document tab for requisitions and work orders without planning support.
4. Add one recommendation timing tab comparing need-by date to converted document date.
5. Finish with one lifecycle-control tab and a short conclusion on the strongest replenishment-support risk.

## Wrap-Up Questions

- Accounting/process: Which planning-support failure could cascade into inventory, capacity, or cash-cycle risk?
- Database/source evidence: Which forecast, policy, recommendation, requisition, work-order, or item-lifecycle row proves the control break?
- Analytics judgment: Is the strongest issue forecast governance, policy coverage, unsupported execution, late conversion, or lifecycle misuse?
- Escalation/next step: Which exception should move from planning review into formal audit follow-up first?

## Next Steps

- Read [Demand Planning and Replenishment Case](demand-planning-and-replenishment-case.md) when you want the managerial reading of the same planning layer.
- Read [Audit Analytics](../audit.md) for the broader planning-support and control-review query set.
- Read [Operations and Risk](../reports/operations-and-risk.md) when you want the higher-level operational interpretation.
