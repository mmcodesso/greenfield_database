---
title: Manufacturing Labor Cost Case
description: Guided walkthrough for manufacturing labor, cost, and productivity analysis.
sidebar_label: Manufacturing Labor Case
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# Manufacturing and Labor Cost Case


## Business Scenario

Charles River manufactures a subset of finished goods. A work order is released because demand and finished-goods buffers indicate shortage. Materials are issued, operations are scheduled, hourly workers record approved time clocks, direct labor is allocated, finished goods are completed, and the work order is later closed with any remaining variance.

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

<QuerySequence items={caseQuerySequences["manufacturing-labor-cost-case"]} />

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
