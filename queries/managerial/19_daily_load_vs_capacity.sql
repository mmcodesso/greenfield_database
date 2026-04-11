-- Teaching objective: Compare daily scheduled load against available work-center capacity.
-- Main tables: WorkCenterCalendar, WorkOrderOperationSchedule, WorkCenter.
-- Output shape: One row per work center and calendar date.
-- Interpretation notes: Clean builds should show some fully booked days and mild pressure, but scheduled hours should not exceed available hours.

WITH scheduled_load AS (
    SELECT
        WorkCenterID,
        ScheduleDate,
        ROUND(SUM(ScheduledHours), 2) AS ScheduledHours
    FROM WorkOrderOperationSchedule
    GROUP BY WorkCenterID, ScheduleDate
)
SELECT
    c.CalendarDate,
    wc.WorkCenterCode,
    wc.WorkCenterName,
    c.ExceptionReason,
    ROUND(c.AvailableHours, 2) AS AvailableHours,
    ROUND(COALESCE(sl.ScheduledHours, 0), 2) AS ScheduledHours,
    ROUND(c.AvailableHours - COALESCE(sl.ScheduledHours, 0), 2) AS RemainingHours
FROM WorkCenterCalendar AS c
JOIN WorkCenter AS wc
    ON wc.WorkCenterID = c.WorkCenterID
LEFT JOIN scheduled_load AS sl
    ON sl.WorkCenterID = c.WorkCenterID
   AND sl.ScheduleDate = c.CalendarDate
WHERE c.AvailableHours > 0
   OR COALESCE(sl.ScheduledHours, 0) > 0
ORDER BY c.CalendarDate, wc.WorkCenterCode;
