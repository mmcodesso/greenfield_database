-- Teaching objective: Summarize monthly work-center utilization and identify recurring bottlenecks.
-- Main tables: WorkCenterCalendar, WorkOrderOperationSchedule, WorkCenter.
-- Output shape: One row per month and work center.
-- Interpretation notes: Assembly and finish should usually show the highest utilization and most fully booked days.

WITH daily_schedule AS (
    SELECT
        WorkCenterID,
        ScheduleDate,
        ROUND(SUM(ScheduledHours), 2) AS ScheduledHours
    FROM WorkOrderOperationSchedule
    GROUP BY WorkCenterID, ScheduleDate
)
SELECT
    substr(c.CalendarDate, 1, 7) AS PeriodMonth,
    wc.WorkCenterCode,
    wc.WorkCenterName,
    ROUND(SUM(c.AvailableHours), 2) AS AvailableHours,
    ROUND(SUM(COALESCE(ds.ScheduledHours, 0)), 2) AS ScheduledHours,
    ROUND(
        CASE
            WHEN SUM(c.AvailableHours) = 0 THEN 0
            ELSE (SUM(COALESCE(ds.ScheduledHours, 0)) / SUM(c.AvailableHours)) * 100
        END,
        2
    ) AS UtilizationPct,
    SUM(
        CASE
            WHEN c.AvailableHours > 0 AND ROUND(COALESCE(ds.ScheduledHours, 0), 2) >= ROUND(c.AvailableHours, 2)
                THEN 1
            ELSE 0
        END
    ) AS FullyBookedDays
FROM WorkCenterCalendar AS c
JOIN WorkCenter AS wc
    ON wc.WorkCenterID = c.WorkCenterID
LEFT JOIN daily_schedule AS ds
    ON ds.WorkCenterID = c.WorkCenterID
   AND ds.ScheduleDate = c.CalendarDate
GROUP BY substr(c.CalendarDate, 1, 7), wc.WorkCenterCode, wc.WorkCenterName
ORDER BY PeriodMonth, UtilizationPct DESC, wc.WorkCenterCode;
