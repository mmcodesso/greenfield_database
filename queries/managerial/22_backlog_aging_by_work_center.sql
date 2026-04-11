-- Teaching objective: Show open operation backlog and how far those operations sit past their planned end dates.
-- Main tables: WorkOrderOperation, WorkOrder, RoutingOperation, WorkCenter.
-- Output shape: One row per open work-order operation.
-- Interpretation notes: This is a schedule/backlog view, not a ledger report; larger past-due backlogs usually indicate capacity pressure.

WITH as_of_date AS (
    SELECT MAX(CalendarDate) AS AsOfDate
    FROM WorkCenterCalendar
)
SELECT
    wc.WorkCenterCode,
    wc.WorkCenterName,
    wo.WorkOrderNumber,
    ro.OperationSequence,
    ro.OperationCode,
    woo.Status,
    ROUND(woo.PlannedQuantity, 2) AS PlannedQuantity,
    ROUND(woo.PlannedLoadHours, 2) AS PlannedLoadHours,
    date(woo.PlannedStartDate) AS PlannedStartDate,
    date(woo.PlannedEndDate) AS PlannedEndDate,
    CAST(julianday((SELECT AsOfDate FROM as_of_date)) - julianday(woo.PlannedEndDate) AS INTEGER) AS DaysPastPlannedEnd
FROM WorkOrderOperation AS woo
JOIN WorkOrder AS wo
    ON wo.WorkOrderID = woo.WorkOrderID
JOIN RoutingOperation AS ro
    ON ro.RoutingOperationID = woo.RoutingOperationID
JOIN WorkCenter AS wc
    ON wc.WorkCenterID = woo.WorkCenterID
WHERE woo.Status IN ('Released', 'In Progress')
ORDER BY wc.WorkCenterCode, DaysPastPlannedEnd DESC, wo.WorkOrderNumber, ro.OperationSequence;
