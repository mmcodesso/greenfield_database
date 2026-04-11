-- Teaching objective: Detect work orders completed before their final scheduled operation window ends.
-- Main tables: WorkOrder, WorkOrderOperation, RoutingOperation.
-- Output shape: One row per suspicious work order.
-- Interpretation notes: Clean builds should normally return no rows; anomaly-enabled builds may return planted exceptions.

WITH final_operation AS (
    SELECT
        woo.WorkOrderID,
        MAX(woo.OperationSequence) AS FinalSequence,
        MAX(date(woo.PlannedEndDate)) AS FinalPlannedEndDate
    FROM WorkOrderOperation AS woo
    GROUP BY woo.WorkOrderID
)
SELECT
    wo.WorkOrderNumber,
    date(wo.CompletedDate) AS WorkOrderCompletedDate,
    fo.FinalPlannedEndDate,
    CAST(julianday(fo.FinalPlannedEndDate) - julianday(wo.CompletedDate) AS INTEGER) AS DaysEarly
FROM WorkOrder AS wo
JOIN final_operation AS fo
    ON fo.WorkOrderID = wo.WorkOrderID
WHERE wo.CompletedDate IS NOT NULL
  AND fo.FinalPlannedEndDate IS NOT NULL
  AND julianday(wo.CompletedDate) < julianday(fo.FinalPlannedEndDate)
ORDER BY DaysEarly DESC, wo.WorkOrderNumber;
