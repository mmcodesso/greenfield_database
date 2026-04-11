-- Teaching objective: Reconcile approved time clocks, labor allocation, and hourly payroll hours.
-- Main tables: TimeClockEntry, LaborTimeEntry, PayrollRegister, PayrollRegisterLine, PayrollPeriod, Employee.
-- Expected output shape: One row per employee and payroll period with an exception-oriented bridge result.
-- Recommended build mode: Standard anomaly build.
-- Interpretation notes: Clean builds may return no rows; standard anomaly builds should surface planted payroll and time-clock bridge issues.

WITH approved_clock_hours AS (
    SELECT
        EmployeeID,
        PayrollPeriodID,
        ROUND(SUM(RegularHours + OvertimeHours), 2) AS ApprovedClockHours
    FROM TimeClockEntry
    WHERE ClockStatus = 'Approved'
    GROUP BY EmployeeID, PayrollPeriodID
),
labor_hours AS (
    SELECT
        EmployeeID,
        PayrollPeriodID,
        ROUND(SUM(RegularHours + OvertimeHours), 2) AS LaborAllocatedHours
    FROM LaborTimeEntry
    GROUP BY EmployeeID, PayrollPeriodID
),
payroll_hours AS (
    SELECT
        pr.EmployeeID,
        pr.PayrollPeriodID,
        ROUND(SUM(CASE WHEN prl.LineType IN ('Regular Earnings', 'Overtime Earnings') THEN prl.Hours ELSE 0 END), 2) AS PayrollHours
    FROM PayrollRegister AS pr
    JOIN PayrollRegisterLine AS prl
        ON prl.PayrollRegisterID = pr.PayrollRegisterID
    GROUP BY pr.EmployeeID, pr.PayrollPeriodID
),
keys AS (
    SELECT EmployeeID, PayrollPeriodID FROM approved_clock_hours
    UNION
    SELECT EmployeeID, PayrollPeriodID FROM labor_hours
    UNION
    SELECT EmployeeID, PayrollPeriodID FROM payroll_hours
)
SELECT
    pp.PeriodNumber,
    e.EmployeeID,
    e.EmployeeName,
    e.PayClass,
    ROUND(COALESCE(ach.ApprovedClockHours, 0), 2) AS ApprovedClockHours,
    ROUND(COALESCE(lh.LaborAllocatedHours, 0), 2) AS LaborAllocatedHours,
    ROUND(COALESCE(ph.PayrollHours, 0), 2) AS PayrollHours,
    CASE
        WHEN e.PayClass = 'Hourly' AND ROUND(COALESCE(ph.PayrollHours, 0), 2) > 0 AND ROUND(COALESCE(ach.ApprovedClockHours, 0), 2) = 0
            THEN 'Hourly pay without approved time-clock coverage'
        WHEN ABS(COALESCE(ph.PayrollHours, 0) - COALESCE(ach.ApprovedClockHours, 0)) > 0.02
            THEN 'Payroll hours do not match approved clock hours'
        WHEN COALESCE(lh.LaborAllocatedHours, 0) - COALESCE(ach.ApprovedClockHours, 0) > 0.02
            THEN 'Allocated labor exceeds approved clock hours'
        ELSE 'Review time-clock, labor, and payroll bridge'
    END AS PotentialIssue
FROM keys AS k
JOIN Employee AS e
    ON e.EmployeeID = k.EmployeeID
JOIN PayrollPeriod AS pp
    ON pp.PayrollPeriodID = k.PayrollPeriodID
LEFT JOIN approved_clock_hours AS ach
    ON ach.EmployeeID = k.EmployeeID
   AND ach.PayrollPeriodID = k.PayrollPeriodID
LEFT JOIN labor_hours AS lh
    ON lh.EmployeeID = k.EmployeeID
   AND lh.PayrollPeriodID = k.PayrollPeriodID
LEFT JOIN payroll_hours AS ph
    ON ph.EmployeeID = k.EmployeeID
   AND ph.PayrollPeriodID = k.PayrollPeriodID
WHERE (
        e.PayClass = 'Hourly'
        AND ROUND(COALESCE(ph.PayrollHours, 0), 2) > 0
        AND ROUND(COALESCE(ach.ApprovedClockHours, 0), 2) = 0
      )
   OR ABS(COALESCE(ph.PayrollHours, 0) - COALESCE(ach.ApprovedClockHours, 0)) > 0.02
   OR COALESCE(lh.LaborAllocatedHours, 0) - COALESCE(ach.ApprovedClockHours, 0) > 0.02
ORDER BY pp.PeriodNumber, e.EmployeeName;
