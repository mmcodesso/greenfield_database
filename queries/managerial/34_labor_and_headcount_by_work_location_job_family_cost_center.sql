-- Teaching objective: Compare headcount, payroll cost, approved time, and direct labor by work location, job family, and cost center.
-- Main tables: Employee, CostCenter, PayrollRegister, TimeClockEntry, LaborTimeEntry.
-- Expected output shape: One row per work location, cost center, and job family grouping.
-- Recommended build mode: Either.
-- Interpretation notes: This query helps students connect workforce structure to labor cost and productive-hours usage.

WITH headcount AS (
    SELECT
        COALESCE(e.WorkLocation, '(No Work Location)') AS WorkLocation,
        COALESCE(cc.CostCenterName, '(No Cost Center)') AS CostCenterName,
        COALESCE(e.JobFamily, '(No Job Family)') AS JobFamily,
        COUNT(*) AS EndStateHeadcount,
        SUM(CASE WHEN e.EmploymentStatus = 'Active' THEN 1 ELSE 0 END) AS ActiveHeadcount,
        SUM(CASE WHEN e.EmploymentStatus = 'Terminated' THEN 1 ELSE 0 END) AS TerminatedHeadcount
    FROM Employee AS e
    LEFT JOIN CostCenter AS cc
        ON cc.CostCenterID = e.CostCenterID
    GROUP BY
        COALESCE(e.WorkLocation, '(No Work Location)'),
        COALESCE(cc.CostCenterName, '(No Cost Center)'),
        COALESCE(e.JobFamily, '(No Job Family)')
),
payroll_cost AS (
    SELECT
        COALESCE(e.WorkLocation, '(No Work Location)') AS WorkLocation,
        COALESCE(cc.CostCenterName, '(No Cost Center)') AS CostCenterName,
        COALESCE(e.JobFamily, '(No Job Family)') AS JobFamily,
        ROUND(SUM(pr.GrossPay), 2) AS GrossPay,
        ROUND(SUM(pr.EmployerPayrollTax + pr.EmployerBenefits), 2) AS EmployerBurden,
        ROUND(SUM(pr.GrossPay + pr.EmployerPayrollTax + pr.EmployerBenefits), 2) AS TotalPeopleCost
    FROM PayrollRegister AS pr
    JOIN Employee AS e
        ON e.EmployeeID = pr.EmployeeID
    LEFT JOIN CostCenter AS cc
        ON cc.CostCenterID = pr.CostCenterID
    GROUP BY
        COALESCE(e.WorkLocation, '(No Work Location)'),
        COALESCE(cc.CostCenterName, '(No Cost Center)'),
        COALESCE(e.JobFamily, '(No Job Family)')
),
approved_time AS (
    SELECT
        COALESCE(e.WorkLocation, '(No Work Location)') AS WorkLocation,
        COALESCE(cc.CostCenterName, '(No Cost Center)') AS CostCenterName,
        COALESCE(e.JobFamily, '(No Job Family)') AS JobFamily,
        ROUND(SUM(COALESCE(tc.RegularHours, 0) + COALESCE(tc.OvertimeHours, 0)), 2) AS ApprovedClockHours
    FROM TimeClockEntry AS tc
    JOIN Employee AS e
        ON e.EmployeeID = tc.EmployeeID
    LEFT JOIN CostCenter AS cc
        ON cc.CostCenterID = e.CostCenterID
    GROUP BY
        COALESCE(e.WorkLocation, '(No Work Location)'),
        COALESCE(cc.CostCenterName, '(No Cost Center)'),
        COALESCE(e.JobFamily, '(No Job Family)')
),
labor_cost AS (
    SELECT
        COALESCE(e.WorkLocation, '(No Work Location)') AS WorkLocation,
        COALESCE(cc.CostCenterName, '(No Cost Center)') AS CostCenterName,
        COALESCE(e.JobFamily, '(No Job Family)') AS JobFamily,
        ROUND(SUM(CASE WHEN lte.LaborType = 'Direct Manufacturing' THEN COALESCE(lte.RegularHours, 0) + COALESCE(lte.OvertimeHours, 0) ELSE 0 END), 2) AS DirectLaborHours,
        ROUND(SUM(COALESCE(lte.ExtendedLaborCost, 0)), 2) AS ExtendedLaborCost
    FROM LaborTimeEntry AS lte
    JOIN Employee AS e
        ON e.EmployeeID = lte.EmployeeID
    LEFT JOIN CostCenter AS cc
        ON cc.CostCenterID = e.CostCenterID
    GROUP BY
        COALESCE(e.WorkLocation, '(No Work Location)'),
        COALESCE(cc.CostCenterName, '(No Cost Center)'),
        COALESCE(e.JobFamily, '(No Job Family)')
),
dimension_keys AS (
    SELECT WorkLocation, CostCenterName, JobFamily FROM headcount
    UNION
    SELECT WorkLocation, CostCenterName, JobFamily FROM payroll_cost
    UNION
    SELECT WorkLocation, CostCenterName, JobFamily FROM approved_time
    UNION
    SELECT WorkLocation, CostCenterName, JobFamily FROM labor_cost
)
SELECT
    dk.WorkLocation,
    dk.CostCenterName,
    dk.JobFamily,
    COALESCE(h.EndStateHeadcount, 0) AS EndStateHeadcount,
    COALESCE(h.ActiveHeadcount, 0) AS ActiveHeadcount,
    COALESCE(h.TerminatedHeadcount, 0) AS TerminatedHeadcount,
    ROUND(COALESCE(pc.GrossPay, 0), 2) AS GrossPay,
    ROUND(COALESCE(pc.EmployerBurden, 0), 2) AS EmployerBurden,
    ROUND(COALESCE(pc.TotalPeopleCost, 0), 2) AS TotalPeopleCost,
    ROUND(COALESCE(at.ApprovedClockHours, 0), 2) AS ApprovedClockHours,
    ROUND(COALESCE(lc.DirectLaborHours, 0), 2) AS DirectLaborHours,
    ROUND(COALESCE(lc.ExtendedLaborCost, 0), 2) AS ExtendedLaborCost
FROM dimension_keys AS dk
LEFT JOIN headcount AS h
    ON h.WorkLocation = dk.WorkLocation
   AND h.CostCenterName = dk.CostCenterName
   AND h.JobFamily = dk.JobFamily
LEFT JOIN payroll_cost AS pc
    ON pc.WorkLocation = dk.WorkLocation
   AND pc.CostCenterName = dk.CostCenterName
   AND pc.JobFamily = dk.JobFamily
LEFT JOIN approved_time AS at
    ON at.WorkLocation = dk.WorkLocation
   AND at.CostCenterName = dk.CostCenterName
   AND at.JobFamily = dk.JobFamily
LEFT JOIN labor_cost AS lc
    ON lc.WorkLocation = dk.WorkLocation
   AND lc.CostCenterName = dk.CostCenterName
   AND lc.JobFamily = dk.JobFamily
ORDER BY
    TotalPeopleCost DESC,
    dk.WorkLocation,
    dk.CostCenterName,
    dk.JobFamily;
