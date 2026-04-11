-- Teaching objective: Review time-clock and attendance exceptions by employee, supervisor, and work center.
-- Main tables: AttendanceException, TimeClockEntry, ShiftDefinition, Employee, WorkCenter.
-- Output shape: One row per attendance exception.
-- Interpretation notes: Clean builds may return no rows. Default anomaly builds should show low-volume planted time-and-attendance issues.

SELECT
    ae.ExceptionType,
    ae.Severity,
    date(ae.WorkDate) AS WorkDate,
    e.EmployeeID,
    e.EmployeeName,
    mgr.EmployeeName AS SupervisorName,
    COALESCE(wc.WorkCenterCode, sd.Department) AS WorkCenterCode,
    COALESCE(wc.WorkCenterName, sd.ShiftName) AS WorkCenterName,
    ae.MinutesVariance,
    ae.Status,
    tc.ClockStatus,
    time(tc.ClockInTime) AS ClockInTime,
    time(tc.ClockOutTime) AS ClockOutTime
FROM AttendanceException AS ae
JOIN Employee AS e
    ON e.EmployeeID = ae.EmployeeID
LEFT JOIN Employee AS mgr
    ON mgr.EmployeeID = e.ManagerID
LEFT JOIN TimeClockEntry AS tc
    ON tc.TimeClockEntryID = ae.TimeClockEntryID
LEFT JOIN ShiftDefinition AS sd
    ON sd.ShiftDefinitionID = COALESCE(ae.ShiftDefinitionID, tc.ShiftDefinitionID)
LEFT JOIN WorkCenter AS wc
    ON wc.WorkCenterID = COALESCE(tc.WorkCenterID, sd.WorkCenterID)
ORDER BY ae.ExceptionType, WorkDate, e.EmployeeName;
