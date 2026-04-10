-- Teaching objective: Compare operation-level direct labor and work-center activity by month.
-- Main tables: WorkOrderOperation, RoutingOperation, WorkCenter, LaborTimeEntry, WorkOrder, Item.
-- Output shape: One row per month, work center, and operation code.
-- Interpretation notes: Direct-labor hours come from LaborTimeEntry and are analytical detail, not a separate inventory valuation basis.

WITH direct_labor AS (
    SELECT
        WorkOrderOperationID,
        ROUND(SUM(RegularHours + OvertimeHours), 2) AS ActualLaborHours,
        ROUND(SUM(ExtendedLaborCost), 2) AS ActualLaborCost
    FROM LaborTimeEntry
    WHERE LaborType = 'Direct Manufacturing'
      AND WorkOrderOperationID IS NOT NULL
    GROUP BY WorkOrderOperationID
)
SELECT
    substr(COALESCE(woo.ActualEndDate, woo.ActualStartDate, woo.PlannedEndDate, woo.PlannedStartDate), 1, 7) AS PeriodMonth,
    wc.WorkCenterCode,
    wc.WorkCenterName,
    ro.OperationCode,
    ro.OperationName,
    COUNT(*) AS WorkOrderOperationCount,
    ROUND(SUM(woo.PlannedQuantity), 2) AS PlannedOperationQuantity,
    ROUND(SUM(ro.StandardSetupHours + (ro.StandardRunHoursPerUnit * woo.PlannedQuantity)), 2) AS PlannedOperationHours,
    ROUND(SUM(COALESCE(dl.ActualLaborHours, 0)), 2) AS ActualLaborHours,
    ROUND(SUM(COALESCE(dl.ActualLaborCost, 0)), 2) AS ActualLaborCost
FROM WorkOrderOperation AS woo
JOIN RoutingOperation AS ro
    ON ro.RoutingOperationID = woo.RoutingOperationID
JOIN WorkCenter AS wc
    ON wc.WorkCenterID = woo.WorkCenterID
JOIN WorkOrder AS wo
    ON wo.WorkOrderID = woo.WorkOrderID
JOIN Item AS i
    ON i.ItemID = wo.ItemID
LEFT JOIN direct_labor AS dl
    ON dl.WorkOrderOperationID = woo.WorkOrderOperationID
WHERE i.SupplyMode = 'Manufactured'
GROUP BY
    substr(COALESCE(woo.ActualEndDate, woo.ActualStartDate, woo.PlannedEndDate, woo.PlannedStartDate), 1, 7),
    wc.WorkCenterCode,
    wc.WorkCenterName,
    ro.OperationCode,
    ro.OperationName
ORDER BY PeriodMonth, wc.WorkCenterCode, ro.OperationCode;
