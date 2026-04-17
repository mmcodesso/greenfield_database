-- Teaching objective: Trace one work order through operation sequence, schedule rows, approved clocks, and direct labor support.
-- Main tables: WorkOrderOperation, WorkOrder, Item, RoutingOperation, WorkCenter, WorkOrderOperationSchedule, TimeClockEntry, LaborTimeEntry.
-- Output shape: One row per work-order operation.
-- Interpretation notes: Scheduled hours show the execution plan. Approved clocks show factory time support. Direct labor rows show productive labor allocated into the work order.

WITH schedule_summary AS (
    SELECT
        WorkOrderOperationID,
        COUNT(*) AS ScheduleRowCount,
        MIN(date(ScheduleDate)) AS FirstScheduleDate,
        MAX(date(ScheduleDate)) AS LastScheduleDate,
        ROUND(SUM(ScheduledHours), 2) AS ScheduledHours
    FROM WorkOrderOperationSchedule
    GROUP BY WorkOrderOperationID
),
approved_clock_summary AS (
    SELECT
        WorkOrderOperationID,
        COUNT(*) AS ApprovedClockRows,
        MIN(date(WorkDate)) AS FirstClockDate,
        MAX(date(WorkDate)) AS LastClockDate,
        ROUND(SUM(RegularHours + OvertimeHours), 2) AS ApprovedClockHours
    FROM TimeClockEntry
    WHERE ClockStatus = 'Approved'
      AND WorkOrderOperationID IS NOT NULL
    GROUP BY WorkOrderOperationID
),
direct_labor_summary AS (
    SELECT
        WorkOrderOperationID,
        COUNT(*) AS DirectLaborRows,
        MIN(date(WorkDate)) AS FirstLaborDate,
        MAX(date(WorkDate)) AS LastLaborDate,
        ROUND(SUM(RegularHours + OvertimeHours), 2) AS DirectLaborHours,
        ROUND(SUM(ExtendedLaborCost), 2) AS DirectLaborCost
    FROM LaborTimeEntry
    WHERE LaborType = 'Direct Manufacturing'
      AND WorkOrderOperationID IS NOT NULL
    GROUP BY WorkOrderOperationID
)
SELECT
    wo.WorkOrderNumber,
    i.ItemCode,
    i.ItemName,
    i.ItemGroup,
    ROUND(wo.PlannedQuantity, 2) AS WorkOrderPlannedQuantity,
    date(wo.ReleasedDate) AS ReleasedDate,
    date(wo.DueDate) AS DueDate,
    wo.Status AS WorkOrderStatus,
    woo.WorkOrderOperationID,
    woo.OperationSequence,
    ro.OperationCode,
    ro.OperationName,
    wc.WorkCenterCode,
    wc.WorkCenterName,
    ROUND(woo.PlannedQuantity, 2) AS PlannedOperationQuantity,
    ROUND(woo.PlannedLoadHours, 2) AS PlannedLoadHours,
    date(woo.PlannedStartDate) AS PlannedStartDate,
    date(woo.PlannedEndDate) AS PlannedEndDate,
    date(woo.ActualStartDate) AS ActualStartDate,
    date(woo.ActualEndDate) AS ActualEndDate,
    woo.Status AS OperationStatus,
    COALESCE(ss.ScheduleRowCount, 0) AS ScheduleRowCount,
    ss.FirstScheduleDate,
    ss.LastScheduleDate,
    ROUND(COALESCE(ss.ScheduledHours, 0), 2) AS ScheduledHours,
    COALESCE(acs.ApprovedClockRows, 0) AS ApprovedClockRows,
    acs.FirstClockDate,
    acs.LastClockDate,
    ROUND(COALESCE(acs.ApprovedClockHours, 0), 2) AS ApprovedClockHours,
    COALESCE(dls.DirectLaborRows, 0) AS DirectLaborRows,
    dls.FirstLaborDate,
    dls.LastLaborDate,
    ROUND(COALESCE(dls.DirectLaborHours, 0), 2) AS DirectLaborHours,
    ROUND(COALESCE(dls.DirectLaborCost, 0), 2) AS DirectLaborCost,
    ROUND(COALESCE(dls.DirectLaborHours, 0) - COALESCE(acs.ApprovedClockHours, 0), 2) AS LaborVsClockVarianceHours
FROM WorkOrderOperation AS woo
JOIN WorkOrder AS wo
    ON wo.WorkOrderID = woo.WorkOrderID
JOIN Item AS i
    ON i.ItemID = wo.ItemID
JOIN RoutingOperation AS ro
    ON ro.RoutingOperationID = woo.RoutingOperationID
JOIN WorkCenter AS wc
    ON wc.WorkCenterID = woo.WorkCenterID
LEFT JOIN schedule_summary AS ss
    ON ss.WorkOrderOperationID = woo.WorkOrderOperationID
LEFT JOIN approved_clock_summary AS acs
    ON acs.WorkOrderOperationID = woo.WorkOrderOperationID
LEFT JOIN direct_labor_summary AS dls
    ON dls.WorkOrderOperationID = woo.WorkOrderOperationID
ORDER BY
    date(wo.ReleasedDate),
    wo.WorkOrderNumber,
    woo.OperationSequence;
