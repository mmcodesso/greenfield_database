-- Teaching objective: Review planned versus actual operation timing and highlight bottleneck-prone work centers.
-- Main tables: WorkOrderOperation, RoutingOperation, WorkCenter, WorkOrder, Item.
-- Output shape: One row per work-order operation.
-- Interpretation notes: Positive delay values suggest schedule slippage; repeated delays at the same work center are bottleneck candidates.

WITH as_of_date AS (
    SELECT MAX(CalendarDate) AS AsOfDate
    FROM WorkCenterCalendar
)
SELECT
    wo.WorkOrderNumber,
    i.ItemCode,
    i.ItemName,
    wc.WorkCenterCode,
    ro.OperationSequence,
    ro.OperationCode,
    date(woo.PlannedStartDate) AS PlannedStartDate,
    date(woo.PlannedEndDate) AS PlannedEndDate,
    date(woo.ActualStartDate) AS ActualStartDate,
    date(woo.ActualEndDate) AS ActualEndDate,
    ROUND(woo.PlannedLoadHours, 2) AS PlannedLoadHours,
    CAST(julianday(COALESCE(woo.ActualEndDate, woo.PlannedEndDate)) - julianday(woo.PlannedEndDate) AS INTEGER) AS EndDelayDays,
    CASE
        WHEN woo.ActualEndDate IS NOT NULL
         AND julianday(woo.ActualEndDate) > julianday(woo.PlannedEndDate)
            THEN 'Late'
        WHEN woo.ActualEndDate IS NULL
         AND julianday((SELECT AsOfDate FROM as_of_date)) > julianday(woo.PlannedEndDate)
            THEN 'Still Open Past Plan'
        ELSE 'On Plan or Early'
    END AS DelayStatus
FROM WorkOrderOperation AS woo
JOIN WorkOrder AS wo
    ON wo.WorkOrderID = woo.WorkOrderID
JOIN RoutingOperation AS ro
    ON ro.RoutingOperationID = woo.RoutingOperationID
JOIN WorkCenter AS wc
    ON wc.WorkCenterID = woo.WorkCenterID
JOIN Item AS i
    ON i.ItemID = wo.ItemID
ORDER BY wc.WorkCenterCode, EndDelayDays DESC, wo.WorkOrderNumber, ro.OperationSequence;
