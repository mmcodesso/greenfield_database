-- Teaching objective: Compare approved paid hours to productive labor allocation by work center and month.
-- Main tables: TimeClockEntry, LaborTimeEntry, WorkOrderOperation, WorkCenter, ShiftDefinition.
-- Expected output shape: One row per month and work center.
-- Recommended build mode: Either.
-- Interpretation notes: Paid hours come from approved clocks; productive allocation comes from labor records tied to manufacturing work.

WITH approved_clock_hours AS (
    SELECT
        substr(tc.WorkDate, 1, 7) AS PeriodMonth,
        COALESCE(tc.WorkCenterID, sd.WorkCenterID) AS WorkCenterID,
        ROUND(SUM(tc.RegularHours + tc.OvertimeHours), 2) AS ApprovedClockHours
    FROM TimeClockEntry AS tc
    LEFT JOIN ShiftDefinition AS sd
        ON sd.ShiftDefinitionID = tc.ShiftDefinitionID
    WHERE tc.ClockStatus = 'Approved'
      AND COALESCE(tc.WorkCenterID, sd.WorkCenterID) IS NOT NULL
    GROUP BY substr(tc.WorkDate, 1, 7), COALESCE(tc.WorkCenterID, sd.WorkCenterID)
),
labor_hours AS (
    SELECT
        substr(lte.WorkDate, 1, 7) AS PeriodMonth,
        COALESCE(woo.WorkCenterID, tc.WorkCenterID) AS WorkCenterID,
        ROUND(SUM(CASE WHEN lte.LaborType = 'Direct Manufacturing' THEN lte.RegularHours + lte.OvertimeHours ELSE 0 END), 2) AS DirectLaborHours,
        ROUND(SUM(CASE WHEN lte.LaborType = 'Indirect Manufacturing' THEN lte.RegularHours + lte.OvertimeHours ELSE 0 END), 2) AS IndirectLaborHours,
        ROUND(SUM(lte.RegularHours + lte.OvertimeHours), 2) AS TotalAllocatedHours
    FROM LaborTimeEntry AS lte
    LEFT JOIN WorkOrderOperation AS woo
        ON woo.WorkOrderOperationID = lte.WorkOrderOperationID
    LEFT JOIN TimeClockEntry AS tc
        ON tc.TimeClockEntryID = lte.TimeClockEntryID
    WHERE COALESCE(woo.WorkCenterID, tc.WorkCenterID) IS NOT NULL
    GROUP BY substr(lte.WorkDate, 1, 7), COALESCE(woo.WorkCenterID, tc.WorkCenterID)
),
months AS (
    SELECT PeriodMonth, WorkCenterID FROM approved_clock_hours
    UNION
    SELECT PeriodMonth, WorkCenterID FROM labor_hours
)
SELECT
    m.PeriodMonth,
    wc.WorkCenterCode,
    wc.WorkCenterName,
    ROUND(COALESCE(ach.ApprovedClockHours, 0), 2) AS ApprovedClockHours,
    ROUND(COALESCE(lh.DirectLaborHours, 0), 2) AS DirectLaborHours,
    ROUND(COALESCE(lh.IndirectLaborHours, 0), 2) AS IndirectLaborHours,
    ROUND(COALESCE(lh.TotalAllocatedHours, 0), 2) AS TotalAllocatedHours,
    ROUND(COALESCE(ach.ApprovedClockHours, 0) - COALESCE(lh.TotalAllocatedHours, 0), 2) AS UnallocatedPaidHours,
    ROUND(100.0 * COALESCE(lh.DirectLaborHours, 0) / NULLIF(COALESCE(ach.ApprovedClockHours, 0), 0), 2) AS DirectProductiveSharePct
FROM months AS m
JOIN WorkCenter AS wc
    ON wc.WorkCenterID = m.WorkCenterID
LEFT JOIN approved_clock_hours AS ach
    ON ach.PeriodMonth = m.PeriodMonth
   AND ach.WorkCenterID = m.WorkCenterID
LEFT JOIN labor_hours AS lh
    ON lh.PeriodMonth = m.PeriodMonth
   AND lh.WorkCenterID = m.WorkCenterID
ORDER BY m.PeriodMonth, wc.WorkCenterCode;
