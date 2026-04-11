-- Teaching objective: Detect work-center days where scheduled hours exceed available capacity.
-- Main tables: WorkOrderOperationSchedule, WorkCenterCalendar, WorkCenter.
-- Output shape: One row per over-capacity work-center day.
-- Interpretation notes: Clean builds should normally return no rows; anomaly-enabled builds may return planted exceptions.

WITH scheduled_load AS (
    SELECT
        WorkCenterID,
        ScheduleDate,
        ROUND(SUM(ScheduledHours), 2) AS ScheduledHours
    FROM WorkOrderOperationSchedule
    GROUP BY WorkCenterID, ScheduleDate
)
SELECT
    wc.WorkCenterCode,
    c.CalendarDate,
    c.ExceptionReason,
    ROUND(c.AvailableHours, 2) AS AvailableHours,
    ROUND(sl.ScheduledHours, 2) AS ScheduledHours,
    ROUND(sl.ScheduledHours - c.AvailableHours, 2) AS ExcessHours
FROM scheduled_load AS sl
JOIN WorkCenterCalendar AS c
    ON c.WorkCenterID = sl.WorkCenterID
   AND c.CalendarDate = sl.ScheduleDate
JOIN WorkCenter AS wc
    ON wc.WorkCenterID = sl.WorkCenterID
WHERE ROUND(sl.ScheduledHours, 2) > ROUND(c.AvailableHours, 2)
ORDER BY c.CalendarDate, wc.WorkCenterCode;
