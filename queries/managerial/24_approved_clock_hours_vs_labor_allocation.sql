-- Teaching objective: Compare approved direct-labor time-clock hours to the labor allocation recorded against work-order operations.
-- Main tables: TimeClockEntry, LaborTimeEntry, WorkOrderOperation, RoutingOperation, WorkCenter, WorkOrder.
-- Output shape: One row per month, work center, and routing operation.
-- Interpretation notes: Clean builds should show approved clock hours supporting direct labor with minimal or zero allocation variance.

WITH direct_clock_hours AS (
    SELECT
        TimeClockEntryID,
        WorkOrderOperationID,
        WorkOrderID,
        WorkDate,
        WorkCenterID,
        ROUND(RegularHours + OvertimeHours, 2) AS ApprovedClockHours
    FROM TimeClockEntry
    WHERE ClockStatus = 'Approved'
      AND WorkOrderOperationID IS NOT NULL
),
direct_labor_hours AS (
    SELECT
        TimeClockEntryID,
        WorkOrderOperationID,
        ROUND(SUM(RegularHours + OvertimeHours), 2) AS AllocatedLaborHours,
        ROUND(SUM(ExtendedLaborCost), 2) AS AllocatedLaborCost
    FROM LaborTimeEntry
    WHERE LaborType = 'Direct Manufacturing'
      AND TimeClockEntryID IS NOT NULL
      AND WorkOrderOperationID IS NOT NULL
    GROUP BY TimeClockEntryID, WorkOrderOperationID
)
SELECT
    substr(dch.WorkDate, 1, 7) AS PeriodMonth,
    wc.WorkCenterCode,
    wc.WorkCenterName,
    ro.OperationCode,
    ro.OperationName,
    COUNT(*) AS SupportedClockRows,
    ROUND(SUM(dch.ApprovedClockHours), 2) AS ApprovedClockHours,
    ROUND(SUM(COALESCE(dlh.AllocatedLaborHours, 0)), 2) AS AllocatedLaborHours,
    ROUND(SUM(COALESCE(dlh.AllocatedLaborCost, 0)), 2) AS AllocatedLaborCost,
    ROUND(SUM(COALESCE(dlh.AllocatedLaborHours, 0) - dch.ApprovedClockHours), 2) AS AllocationVarianceHours
FROM direct_clock_hours AS dch
JOIN WorkOrderOperation AS woo
    ON woo.WorkOrderOperationID = dch.WorkOrderOperationID
JOIN RoutingOperation AS ro
    ON ro.RoutingOperationID = woo.RoutingOperationID
LEFT JOIN WorkCenter AS wc
    ON wc.WorkCenterID = COALESCE(dch.WorkCenterID, woo.WorkCenterID)
LEFT JOIN direct_labor_hours AS dlh
    ON dlh.TimeClockEntryID = dch.TimeClockEntryID
   AND dlh.WorkOrderOperationID = dch.WorkOrderOperationID
GROUP BY
    substr(dch.WorkDate, 1, 7),
    wc.WorkCenterCode,
    wc.WorkCenterName,
    ro.OperationCode,
    ro.OperationName
ORDER BY PeriodMonth, wc.WorkCenterCode, ro.OperationCode;
