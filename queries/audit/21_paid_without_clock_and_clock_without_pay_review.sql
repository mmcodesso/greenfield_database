-- Teaching objective: Review hourly payroll lines without approved time-clock support and approved time clocks that do not feed hourly pay.
-- Main tables: PayrollRegister, PayrollRegisterLine, LaborTimeEntry, TimeClockEntry, PayrollPeriod, Employee.
-- Output shape: One row per potential payroll-support exception.
-- Interpretation notes: Clean builds should usually return no rows. Default anomaly builds may surface planted exceptions.

WITH hourly_pay_lines AS (
    SELECT
        pr.PayrollRegisterID,
        pr.PayrollPeriodID,
        pr.EmployeeID,
        prl.PayrollRegisterLineID,
        prl.LineType,
        COALESCE(prl.Hours, 0) AS Hours,
        lte.LaborTimeEntryID,
        lte.TimeClockEntryID
    FROM PayrollRegister AS pr
    JOIN Employee AS e
        ON e.EmployeeID = pr.EmployeeID
    JOIN PayrollRegisterLine AS prl
        ON prl.PayrollRegisterID = pr.PayrollRegisterID
    LEFT JOIN LaborTimeEntry AS lte
        ON lte.LaborTimeEntryID = prl.LaborTimeEntryID
    WHERE e.PayClass = 'Hourly'
      AND prl.LineType IN ('Regular Earnings', 'Overtime Earnings')
      AND COALESCE(prl.Hours, 0) > 0
),
paid_without_clock AS (
    SELECT
        'Paid hourly earnings without approved clock support' AS PotentialIssue,
        pp.PeriodNumber AS ReferenceNumber,
        e.EmployeeName,
        date(pp.PayDate) AS EventDate,
        hpl.Hours AS HoursOrAmount
    FROM hourly_pay_lines AS hpl
    JOIN PayrollPeriod AS pp
        ON pp.PayrollPeriodID = hpl.PayrollPeriodID
    JOIN Employee AS e
        ON e.EmployeeID = hpl.EmployeeID
    LEFT JOIN TimeClockEntry AS tc
        ON tc.TimeClockEntryID = hpl.TimeClockEntryID
    WHERE tc.TimeClockEntryID IS NULL
       OR tc.ClockStatus <> 'Approved'
),
clock_without_pay AS (
    SELECT
        'Approved clock without hourly pay line' AS PotentialIssue,
        pp.PeriodNumber AS ReferenceNumber,
        e.EmployeeName,
        date(tc.WorkDate) AS EventDate,
        ROUND(tc.RegularHours + tc.OvertimeHours, 2) AS HoursOrAmount
    FROM TimeClockEntry AS tc
    JOIN Employee AS e
        ON e.EmployeeID = tc.EmployeeID
    JOIN PayrollPeriod AS pp
        ON pp.PayrollPeriodID = tc.PayrollPeriodID
    LEFT JOIN LaborTimeEntry AS lte
        ON lte.TimeClockEntryID = tc.TimeClockEntryID
    LEFT JOIN PayrollRegister AS pr
        ON pr.PayrollPeriodID = tc.PayrollPeriodID
       AND pr.EmployeeID = tc.EmployeeID
    LEFT JOIN PayrollRegisterLine AS prl
        ON prl.PayrollRegisterID = pr.PayrollRegisterID
       AND prl.LaborTimeEntryID = lte.LaborTimeEntryID
       AND prl.LineType IN ('Regular Earnings', 'Overtime Earnings')
    WHERE e.PayClass = 'Hourly'
      AND tc.ClockStatus = 'Approved'
      AND ROUND(tc.RegularHours + tc.OvertimeHours, 2) > 0
      AND prl.PayrollRegisterLineID IS NULL
)
SELECT *
FROM paid_without_clock
UNION ALL
SELECT *
FROM clock_without_pay
ORDER BY PotentialIssue, EventDate, EmployeeName;
