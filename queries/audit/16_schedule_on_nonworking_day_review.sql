-- Teaching objective: Detect work-center schedule rows that fall on non-working days.
-- Main tables: WorkOrderOperationSchedule, WorkCenterCalendar, WorkCenter, WorkOrderOperation, WorkOrder.
-- Output shape: One row per suspicious schedule row.
-- Interpretation notes: Clean builds should normally return no rows; anomaly-enabled builds may return planted exceptions.

SELECT
    wo.WorkOrderNumber,
    wc.WorkCenterCode,
    s.ScheduleDate,
    c.ExceptionReason,
    ROUND(c.AvailableHours, 2) AS AvailableHours,
    ROUND(s.ScheduledHours, 2) AS ScheduledHours
FROM WorkOrderOperationSchedule AS s
JOIN WorkCenterCalendar AS c
    ON c.WorkCenterID = s.WorkCenterID
   AND c.CalendarDate = s.ScheduleDate
JOIN WorkCenter AS wc
    ON wc.WorkCenterID = s.WorkCenterID
JOIN WorkOrderOperation AS woo
    ON woo.WorkOrderOperationID = s.WorkOrderOperationID
JOIN WorkOrder AS wo
    ON wo.WorkOrderID = woo.WorkOrderID
WHERE c.IsWorkingDay = 0
   OR c.AvailableHours = 0
ORDER BY s.ScheduleDate, wc.WorkCenterCode, wo.WorkOrderNumber;
