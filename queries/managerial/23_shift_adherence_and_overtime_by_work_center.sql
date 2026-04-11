-- Teaching objective: Review shift adherence and overtime concentration by work center and month.
-- Main tables: TimeClockEntry, ShiftDefinition, EmployeeShiftAssignment, WorkCenter, Employee.
-- Output shape: One row per month, shift, and work-center grouping.
-- Interpretation notes: Approved time clocks support workforce-timing analysis without requiring raw punch-event tables.

WITH approved_clocks AS (
    SELECT
        substr(tc.WorkDate, 1, 7) AS PeriodMonth,
        COALESCE(tc.WorkCenterID, sd.WorkCenterID) AS EffectiveWorkCenterID,
        tc.ShiftDefinitionID,
        ROUND(
            (julianday(tc.ClockInTime) - julianday(date(tc.WorkDate) || ' ' || sd.StartTime)) * 24 * 60,
            2
        ) AS ClockInVarianceMinutes,
        tc.RegularHours,
        tc.OvertimeHours
    FROM TimeClockEntry AS tc
    JOIN ShiftDefinition AS sd
        ON sd.ShiftDefinitionID = tc.ShiftDefinitionID
    WHERE tc.ClockStatus = 'Approved'
)
SELECT
    ac.PeriodMonth,
    COALESCE(wc.WorkCenterCode, sd.Department) AS WorkCenterCode,
    COALESCE(wc.WorkCenterName, sd.Department || ' Shift Coverage') AS WorkCenterName,
    sd.ShiftCode,
    sd.ShiftName,
    COUNT(*) AS ApprovedClockRows,
    ROUND(AVG(ac.ClockInVarianceMinutes), 2) AS AvgClockInVarianceMinutes,
    SUM(CASE WHEN ac.ClockInVarianceMinutes > 15 THEN 1 ELSE 0 END) AS LateStartCount,
    ROUND(SUM(ac.RegularHours), 2) AS TotalRegularHours,
    ROUND(SUM(ac.OvertimeHours), 2) AS TotalOvertimeHours
FROM approved_clocks AS ac
JOIN ShiftDefinition AS sd
    ON sd.ShiftDefinitionID = ac.ShiftDefinitionID
LEFT JOIN WorkCenter AS wc
    ON wc.WorkCenterID = ac.EffectiveWorkCenterID
GROUP BY
    ac.PeriodMonth,
    COALESCE(wc.WorkCenterCode, sd.Department),
    COALESCE(wc.WorkCenterName, sd.Department || ' Shift Coverage'),
    sd.ShiftCode,
    sd.ShiftName
ORDER BY ac.PeriodMonth, WorkCenterCode, sd.ShiftCode;
