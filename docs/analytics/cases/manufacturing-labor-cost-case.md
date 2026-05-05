---
title: Manufacturing Labor Cost Case
description: Inquiry-led walkthrough for tracing one manufactured item from standard cost through work-order labor support, completion, and close.
sidebar_label: Manufacturing Labor Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# Manufacturing Labor Cost Case

## Business Scenario

Charles River Home Furnishings needs to replenish a manufactured finished good under delivery pressure. Planning has already released the work order. The order now moves through scheduled operations, work centers, approved factory time, labor allocation, production completion, and close.

This case focuses on labor cost inside that full production path. Standard cost sets the baseline. Approved factory time supports the work. `LaborTimeEntry` allocates direct labor into the work order. `ProductionCompletion` returns finished goods to inventory. `WorkOrderClose` resolves the remaining material, labor, and overhead variance.

Your job is to explain that chain as one manufacturing story and one cost story.

## The Problem to Solve

You need to prove that labor cost on a manufactured item can be explained from standard cost baseline through work-order execution and close. Confirm the operation path. Confirm that approved time and direct labor support align with the work order. Confirm that completion and close create the expected accounting effect.

## What You Need to Develop

- A standard-cost narrative for the selected manufactured item.
- A work-order execution narrative through operations, schedule rows, and work centers.
- A labor-support explanation that separates clock approval, labor allocation, and payroll support.
- A completion-and-close explanation tied back to `GLEntry`.
- An exception follow-up on labor timing or delayed close behavior.

## Before You Start

- Main tables: `Item`, `BillOfMaterial`, `Routing`, `WorkCenter`, `WorkOrder`, `WorkOrderOperation`, `WorkOrderOperationSchedule`, `TimeClockEntry`, `LaborTimeEntry`, `ProductionCompletion`, `ProductionCompletionLine`, `WorkOrderClose`, `GLEntry`
- Related process pages: [Manufacturing Process](../../processes/manufacturing.md), [Payroll Process](../../processes/payroll.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [GLEntry Posting Reference](../../reference/posting.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case uses both starter query packs and two case-support SQL files built specifically for one-work-order tracing.

## Step-by-Step Walkthrough

### Step 1. Define the standard cost baseline

Start with the cost baseline before you look at any actual labor support. Students need to know what the item should cost before they interpret what the work order actually consumed.

**What we are trying to achieve**

Establish the standard material and conversion structure for the manufactured item.

Standard cost drives completion value and sets the benchmark for later variance analysis. Without that baseline, actual labor support and close amounts have no clear point of reference.

**Suggested query**

<QueryReference
  queryKey="managerial/07_bom_standard_cost_rollup.sql"
  helperText="Use this first to compare BOM-driven rolled cost with item-master standard cost."
/>

<QueryReference
  queryKey="managerial/13_unit_cost_bridge_dm_dl_varoh_fixedoh.sql"
  helperText="Use this follow-through query to break standard cost into direct material, direct labor, and overhead layers."
/>

**What this query does**

The first query compares BOM material rollup to the item master standard cost. The second decomposes standard cost into direct material, direct labor, variable overhead, and fixed overhead.

**How it works**

The BOM rollup query aggregates component standard cost from `BillOfMaterialLine` and combines it with item-level conversion cost. The unit-cost bridge reads the manufactured item master directly and surfaces the standard cost layers already stored on the finished good.

**What to look for in the result**

- manufactured items where rolled cost and item master standard cost align cleanly
- the size of the standard conversion layer relative to direct material
- the direct labor share inside standard conversion cost
- the item you want to carry through the rest of the case

### Step 2. Trace one work order through operations and scheduled hours

After you define the cost baseline, move into execution. The work order is the operational anchor for the labor-cost story.

**What we are trying to achieve**

Trace one released work order through operation sequence, schedule dates, work centers, and planned load.

Labor cost sits inside a real execution path. Students need to see where the work was scheduled and which operation consumed the labor support.

**Suggested query**

<QueryReference
  queryKey="cases/05_manufacturing_work_order_operation_trace.sql"
  helperText="Use this to trace one work order across operations, scheduled hours, approved clocks, and direct labor support."
/>

<QueryReference
  queryKey="managerial/18_work_center_activity_and_operation_hours.sql"
  helperText="Use this follow-through query to place the selected work order inside broader work-center and operation activity."
/>

**What this query does**

The case-support query shows one row per `WorkOrderOperation` with planned dates, actual dates, scheduled hours, approved clock hours, and direct labor support. The managerial query summarizes operation activity by work center and month.

**How it works**

The trace query starts at `WorkOrderOperation`, then joins `WorkOrder`, `Item`, `RoutingOperation`, `WorkCenter`, `WorkOrderOperationSchedule`, `TimeClockEntry`, and `LaborTimeEntry`. The work-center summary query aggregates the same execution layer at a higher level for comparison.

**What to look for in the result**

- the operation sequence for the selected work order
- scheduled hours versus planned load hours
- which work center carried the work
- where approved clock support and direct labor support first appear

### Step 3. Connect approved clocks to productive labor and direct labor cost

Now move from execution shape into labor support. This step shows how approved time becomes direct manufacturing labor on the work order.

**What we are trying to achieve**

Connect approved time-clock support to direct labor allocation and labor cost on the work order.

Approved clocks, labor allocation, and direct labor cost answer different questions. Students need to separate attendance support from productive allocation and from cost.

**Suggested query**

<QueryReference
  queryKey="managerial/24_approved_clock_hours_vs_labor_allocation.sql"
  helperText="Use this first to compare approved direct clock hours with allocated direct labor hours."
/>

<QueryReference
  queryKey="managerial/12_direct_labor_by_work_order_and_employee_class.sql"
  helperText="Use this follow-through query to summarize direct labor hours and cost by work order and employee class."
/>

**What this query does**

The first query compares approved direct clock hours with allocated labor hours and cost by work center and operation. The second summarizes direct labor hours and cost by work order and employee grouping.

**How it works**

The clock-versus-allocation query starts with approved `TimeClockEntry` rows tied to `WorkOrderOperationID`, then joins them to direct-manufacturing `LaborTimeEntry`. The direct-labor summary aggregates `LaborTimeEntry` by work order, payroll period, employee title, and pay class.

**What to look for in the result**

- approved clock hours that support direct manufacturing work
- direct labor hours and labor cost on the selected work order
- differences between approved hours and allocated hours
- the employee mix behind the direct labor cost

### Step 4. Move from completion to close and ledger impact

Labor support becomes financially meaningful only when you connect it to completion and close. This is where the operational work order reaches inventory and later resolves residual variance.

**What we are trying to achieve**

Connect material issue, completion, close variance, and the posted manufacturing accounts for one work order.

Completion moves finished goods into inventory. Close resolves the remaining WIP, clearing, and variance balances. Students need to explain both events clearly.

**Suggested query**

<QueryReference
  queryKey="financial/17_manufacturing_cost_component_bridge.sql"
  helperText="Use this first to see monthly material, completion, variance, and ledger movement across manufacturing."
/>

<QueryReference
  queryKey="cases/06_manufacturing_work_order_close_gl_trace.sql"
  helperText="Use this follow-through query to tie one work order to issue cost, completion standard cost, close variance, and GL posting support."
/>

**What this query does**

The financial bridge summarizes manufacturing cost movement by month. The case-support query drills into one work order and shows material issue cost, completion standard cost components, close variance, and related `GLEntry` support.

**How it works**

The monthly bridge aggregates operational manufacturing tables and ledger postings by period. The work-order trace aggregates `MaterialIssue`, `ProductionCompletion`, `ProductionCompletionLine`, `WorkOrderClose`, and `GLEntry` back to one work-order row.

**What to look for in the result**

- material issued into WIP before completion
- standard direct labor and overhead embedded in completion cost
- total variance recognized at close
- the posting support behind `1046`, `1090`, and `5080`

### Step 5. Extend the case into control follow-up

Finish with control interpretation. Once the core labor-cost story is clear, test whether the timing and close behavior still make sense.

**What we are trying to achieve**

Identify labor-support or close-timing patterns that deserve follow-up.

This case ends with judgment. Students should know when labor support aligns with the operation path and when the pattern becomes unusual enough for audit review.

**Suggested query**

<QueryReference
  queryKey="audit/20_labor_outside_scheduled_operation_window_review.sql"
  helperText="Use this first to isolate direct labor booked outside the scheduled or actual operation window."
/>

<QueryReference
  queryKey="audit/12_labor_time_after_close_and_paid_without_time.sql"
  helperText="Use this follow-through query to identify labor posted after close or hourly payroll without time support."
/>

**What this query does**

The first query flags direct labor outside the operation window. The second flags labor recorded after work-order close and hourly payroll without time-entry support.

**How it works**

The labor-window review compares `LaborTimeEntry.WorkDate` to the scheduled or actual operation dates on `WorkOrderOperation`. The second review combines `LaborTimeEntry`, `WorkOrder`, and payroll-period support to surface timing and ghost-payroll style issues.

**What to look for in the result**

- direct labor booked before an operation starts or after it ends
- labor posted after the work order was closed
- hourly payroll that lacks time support
- which issues reflect process timing and which issues require control follow-up

## Required Student Output

Submit a short case memo or notebook note with these four artifacts:

- Evidence summary: identify the key result rows, metrics, timing patterns, or exception families that changed your diagnosis.
- Accounting or business interpretation: explain what the evidence means for the process, accounting treatment, managerial decision, or control risk.
- Database explanation: name the source tables, row grain, join keys, or trace path that make the evidence defensible.
- Management or audit conclusion: state which driver, document path, or exception family should be followed up first and why.

## Optional Excel Follow-Through

1. Filter `Item` to one manufactured finished good and review its standard cost structure.
2. Use `WorkOrder` and `WorkOrderOperation` to trace the selected order through operation sequence and dates.
3. Use `WorkOrderOperationID` to tie `WorkOrderOperationSchedule`, `TimeClockEntry`, and `LaborTimeEntry` together.
4. Use `WorkOrderID` to trace into `ProductionCompletion`, `ProductionCompletionLine`, and `WorkOrderClose`.
5. Use `SourceDocumentType` and `SourceDocumentID` in `GLEntry` to compare the material issue, completion, and close postings for the same work order.

## Wrap-Up Questions

- Accounting/process: Which event moves finished goods into inventory, and which event resolves residual variance?
- Database/source evidence: Which work-order, operation, clock, labor-allocation, or GL key proves the labor-cost path?
- Analytics judgment: Where do standard cost, approved time, direct labor allocation, and close variance diverge?
- Escalation/next step: What timing or support pattern would make labor cost or work-order close worth audit follow-up?

## Next Steps

- Use [Manufacturing Process](../../processes/manufacturing.md) for the full planning, execution, and close walkthrough behind this case.
- Use [Payroll Process](../../processes/payroll.md) when you need the approved-hours and payroll-side support behind factory labor.
- Use [Schema Reference](../../reference/schema.md) when you need table-level join support while tracing the work order.
- Use [GLEntry Posting Reference](../../reference/posting.md) when you want the exact posting rules for material issue, completion, close, and manufacturing reclass support.
- Use [Financial Statement Bridge Case](financial-statement-bridge-case.md) when you want to extend this work-order analysis into broader ledger interpretation.
