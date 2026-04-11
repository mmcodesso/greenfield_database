-- Teaching objective: Review payroll expense mix by cost center and pay class.
-- Main tables: PayrollRegister, PayrollPeriod, Employee, CostCenter.
-- Expected output shape: One row per pay month, cost center, and pay class.
-- Recommended build mode: Either.
-- Interpretation notes: This is a payroll-subledger view; it explains payroll mix before students move to ledger-only expense analysis.

SELECT
    substr(pp.PayDate, 1, 7) AS PayMonth,
    cc.CostCenterName,
    e.PayClass,
    COUNT(DISTINCT pr.EmployeeID) AS EmployeeCount,
    ROUND(SUM(pr.GrossPay), 2) AS GrossPay,
    ROUND(SUM(pr.EmployeeWithholdings), 2) AS EmployeeWithholdings,
    ROUND(SUM(pr.EmployerPayrollTax), 2) AS EmployerPayrollTax,
    ROUND(SUM(pr.EmployerBenefits), 2) AS EmployerBenefits,
    ROUND(SUM(pr.NetPay), 2) AS NetPay
FROM PayrollRegister AS pr
JOIN PayrollPeriod AS pp
    ON pp.PayrollPeriodID = pr.PayrollPeriodID
JOIN Employee AS e
    ON e.EmployeeID = pr.EmployeeID
JOIN CostCenter AS cc
    ON cc.CostCenterID = pr.CostCenterID
GROUP BY
    substr(pp.PayDate, 1, 7),
    cc.CostCenterName,
    e.PayClass
ORDER BY PayMonth, cc.CostCenterName, e.PayClass;
