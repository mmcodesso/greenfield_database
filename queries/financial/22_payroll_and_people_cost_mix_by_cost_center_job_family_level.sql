-- Teaching objective: Review payroll cost mix by cost center, job family, job level, and pay class.
-- Main tables: PayrollRegister, Employee, CostCenter.
-- Expected output shape: One row per cost center and workforce grouping.
-- Recommended build mode: Either.
-- Interpretation notes: This query combines current headcount context with payroll register totals so students can compare workforce structure to people-cost concentration.

WITH payroll_cost AS (
    SELECT
        pr.CostCenterID,
        COALESCE(e.JobFamily, '(No Job Family)') AS JobFamily,
        COALESCE(e.JobLevel, '(No Job Level)') AS JobLevel,
        COALESCE(e.PayClass, '(No Pay Class)') AS PayClass,
        COUNT(DISTINCT pr.EmployeeID) AS EmployeesWithPayroll,
        ROUND(SUM(pr.GrossPay), 2) AS GrossPay,
        ROUND(SUM(pr.EmployerPayrollTax), 2) AS EmployerPayrollTax,
        ROUND(SUM(pr.EmployerBenefits), 2) AS EmployerBenefits,
        ROUND(SUM(pr.GrossPay + pr.EmployerPayrollTax + pr.EmployerBenefits), 2) AS TotalPeopleCost
    FROM PayrollRegister AS pr
    JOIN Employee AS e
        ON e.EmployeeID = pr.EmployeeID
    GROUP BY
        pr.CostCenterID,
        COALESCE(e.JobFamily, '(No Job Family)'),
        COALESCE(e.JobLevel, '(No Job Level)'),
        COALESCE(e.PayClass, '(No Pay Class)')
),
headcount AS (
    SELECT
        e.CostCenterID,
        COALESCE(e.JobFamily, '(No Job Family)') AS JobFamily,
        COALESCE(e.JobLevel, '(No Job Level)') AS JobLevel,
        COALESCE(e.PayClass, '(No Pay Class)') AS PayClass,
        COUNT(*) AS EndStateHeadcount,
        SUM(CASE WHEN e.EmploymentStatus = 'Active' THEN 1 ELSE 0 END) AS ActiveHeadcount,
        SUM(CASE WHEN e.EmploymentStatus = 'Terminated' THEN 1 ELSE 0 END) AS TerminatedHeadcount
    FROM Employee AS e
    GROUP BY
        e.CostCenterID,
        COALESCE(e.JobFamily, '(No Job Family)'),
        COALESCE(e.JobLevel, '(No Job Level)'),
        COALESCE(e.PayClass, '(No Pay Class)')
),
dimension_keys AS (
    SELECT CostCenterID, JobFamily, JobLevel, PayClass FROM payroll_cost
    UNION
    SELECT CostCenterID, JobFamily, JobLevel, PayClass FROM headcount
)
SELECT
    COALESCE(cc.CostCenterName, '(No Cost Center)') AS CostCenterName,
    dk.JobFamily,
    dk.JobLevel,
    dk.PayClass,
    COALESCE(h.EndStateHeadcount, 0) AS EndStateHeadcount,
    COALESCE(h.ActiveHeadcount, 0) AS ActiveHeadcount,
    COALESCE(h.TerminatedHeadcount, 0) AS TerminatedHeadcount,
    COALESCE(pc.EmployeesWithPayroll, 0) AS EmployeesWithPayroll,
    ROUND(COALESCE(pc.GrossPay, 0), 2) AS GrossPay,
    ROUND(COALESCE(pc.EmployerPayrollTax, 0), 2) AS EmployerPayrollTax,
    ROUND(COALESCE(pc.EmployerBenefits, 0), 2) AS EmployerBenefits,
    ROUND(COALESCE(pc.TotalPeopleCost, 0), 2) AS TotalPeopleCost
FROM dimension_keys AS dk
LEFT JOIN CostCenter AS cc
    ON cc.CostCenterID = dk.CostCenterID
LEFT JOIN headcount AS h
    ON h.CostCenterID = dk.CostCenterID
   AND h.JobFamily = dk.JobFamily
   AND h.JobLevel = dk.JobLevel
   AND h.PayClass = dk.PayClass
LEFT JOIN payroll_cost AS pc
    ON pc.CostCenterID = dk.CostCenterID
   AND pc.JobFamily = dk.JobFamily
   AND pc.JobLevel = dk.JobLevel
   AND pc.PayClass = dk.PayClass
ORDER BY
    TotalPeopleCost DESC,
    CostCenterName,
    dk.JobFamily,
    dk.JobLevel,
    dk.PayClass;
