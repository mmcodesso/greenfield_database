-- Teaching objective: Bridge approved hourly time-clock hours to payroll earnings and payment timing.
-- Main tables: TimeClockEntry, LaborTimeEntry, PayrollRegister, PayrollRegisterLine, PayrollPayment, PayrollPeriod, Employee.
-- Output shape: One row per hourly employee payroll register.
-- Interpretation notes: Clean builds should show approved clock hours supporting hourly regular and overtime earnings.

WITH clock_hours AS (
    SELECT
        PayrollPeriodID,
        EmployeeID,
        ROUND(SUM(RegularHours), 2) AS ApprovedRegularHours,
        ROUND(SUM(OvertimeHours), 2) AS ApprovedOvertimeHours
    FROM TimeClockEntry
    WHERE ClockStatus = 'Approved'
    GROUP BY PayrollPeriodID, EmployeeID
),
labor_support AS (
    SELECT
        PayrollPeriodID,
        EmployeeID,
        ROUND(SUM(RegularHours + OvertimeHours), 2) AS LaborHoursSupported
    FROM LaborTimeEntry
    GROUP BY PayrollPeriodID, EmployeeID
),
earnings_lines AS (
    SELECT
        PayrollRegisterID,
        ROUND(SUM(CASE WHEN LineType = 'Regular Earnings' THEN COALESCE(Hours, 0) ELSE 0 END), 2) AS PayrollRegularHours,
        ROUND(SUM(CASE WHEN LineType = 'Overtime Earnings' THEN COALESCE(Hours, 0) ELSE 0 END), 2) AS PayrollOvertimeHours,
        ROUND(SUM(CASE WHEN LineType IN ('Regular Earnings', 'Overtime Earnings') THEN Amount ELSE 0 END), 2) AS HourlyEarningsAmount
    FROM PayrollRegisterLine
    GROUP BY PayrollRegisterID
),
payment_dates AS (
    SELECT
        PayrollRegisterID,
        MIN(date(PaymentDate)) AS FirstPaymentDate
    FROM PayrollPayment
    GROUP BY PayrollRegisterID
)
SELECT
    pp.PeriodNumber,
    date(pp.PayDate) AS PayDate,
    e.EmployeeID,
    e.EmployeeName,
    cc.CostCenterName,
    COALESCE(ch.ApprovedRegularHours, 0) AS ApprovedRegularHours,
    COALESCE(ch.ApprovedOvertimeHours, 0) AS ApprovedOvertimeHours,
    COALESCE(ls.LaborHoursSupported, 0) AS LaborHoursSupported,
    COALESCE(el.PayrollRegularHours, 0) AS PayrollRegularHours,
    COALESCE(el.PayrollOvertimeHours, 0) AS PayrollOvertimeHours,
    COALESCE(el.HourlyEarningsAmount, 0) AS HourlyEarningsAmount,
    pr.GrossPay,
    pr.NetPay,
    pd.FirstPaymentDate,
    pr.Status
FROM PayrollRegister AS pr
JOIN PayrollPeriod AS pp
    ON pp.PayrollPeriodID = pr.PayrollPeriodID
JOIN Employee AS e
    ON e.EmployeeID = pr.EmployeeID
JOIN CostCenter AS cc
    ON cc.CostCenterID = pr.CostCenterID
LEFT JOIN clock_hours AS ch
    ON ch.PayrollPeriodID = pr.PayrollPeriodID
   AND ch.EmployeeID = pr.EmployeeID
LEFT JOIN labor_support AS ls
    ON ls.PayrollPeriodID = pr.PayrollPeriodID
   AND ls.EmployeeID = pr.EmployeeID
LEFT JOIN earnings_lines AS el
    ON el.PayrollRegisterID = pr.PayrollRegisterID
LEFT JOIN payment_dates AS pd
    ON pd.PayrollRegisterID = pr.PayrollRegisterID
WHERE e.PayClass = 'Hourly'
ORDER BY date(pp.PayDate), cc.CostCenterName, e.EmployeeName;
