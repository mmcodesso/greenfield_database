# Manufacturing and Labor Cost Case

**Audience:** Students and instructors using the dataset for product-cost and manufacturing analytics.  
**Purpose:** Walk through how BOM, routing, scheduling, time clocks, labor time, payroll, and work-order close fit into product-cost analysis.  
**What you will learn:** How direct material, direct labor, overhead, and variance appear across both operational and accounting tables.

## Business Scenario

Greenfield manufactures a subset of finished goods. A work order is released because demand and finished-goods buffers indicate shortage. Materials are issued, operations are scheduled, hourly workers record approved time clocks, direct labor is allocated, finished goods are completed, and the work order is later closed with any remaining variance.

## Recommended Build Mode

- Clean build for the clearest cost bridge
- Default build if you also want anomaly-oriented routing or labor controls

## Main Tables and Worksheets

- `Item`
- `BillOfMaterial`
- `Routing`
- `WorkCenter`
- `WorkOrder`
- `WorkOrderOperation`
- `WorkOrderOperationSchedule`
- `TimeClockEntry`
- `LaborTimeEntry`
- `PayrollRegister`
- `ProductionCompletionLine`
- `WorkOrderClose`
- `GLEntry`

## Recommended Query Sequence

1. Run [../../../queries/managerial/07_bom_standard_cost_rollup.sql](../../../queries/managerial/07_bom_standard_cost_rollup.sql).
2. Run [../../../queries/managerial/13_unit_cost_bridge_dm_dl_varoh_fixedoh.sql](../../../queries/managerial/13_unit_cost_bridge_dm_dl_varoh_fixedoh.sql).
3. Run [../../../queries/managerial/18_work_center_activity_and_operation_hours.sql](../../../queries/managerial/18_work_center_activity_and_operation_hours.sql).
4. Run [../../../queries/managerial/28_paid_hours_vs_productive_labor_by_work_center.sql](../../../queries/managerial/28_paid_hours_vs_productive_labor_by_work_center.sql).
5. Run [../../../queries/financial/17_manufacturing_cost_component_bridge.sql](../../../queries/financial/17_manufacturing_cost_component_bridge.sql).

## Suggested Excel Sequence

1. Use `Item` to choose one manufactured finished good.
2. Review its BOM and routing.
3. Trace a related work order through operations, schedules, time clocks, and labor entries.
4. Compare `ProductionCompletionLine` standard costs with `WorkOrderClose` variance.
5. Tie the cost flow back to ledger accounts `1046`, `1090`, and `5080`.

## What Students Should Notice

- The dataset stays on standard-cost valuation even though payroll provides actual labor detail.
- Approved time clocks support hourly payroll and labor analytics without switching to actual-cost inventory.
- Work-order close is the key place where residual DM, DL, and OH differences appear.
- Work-center schedules, labor, and payroll can be taught as one integrated manufacturing story.

## Follow-Up Questions

- Which tables provide standard cost versus actual labor evidence?
- Why does contribution margin exclude fixed overhead while absorption cost includes it?
- How would you explain manufacturing variance to a student using only one work order as an example?
