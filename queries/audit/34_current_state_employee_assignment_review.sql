-- Teaching objective: Review current-state master assignments that still point to inactive or terminated employees.
-- Main tables: CostCenter, Warehouse, WorkCenter, Customer, Employee.
-- Expected output shape: One row per current-state assignment linked to an inactive or terminated employee.
-- Recommended build mode: Default.
-- Interpretation notes: This is a current-state ownership review, not a historical transaction review. Focus on stale master-data assignments.

WITH current_assignments AS (
    SELECT
        'CostCenter' AS AssignmentTable,
        CostCenterID AS AssignmentKey,
        CostCenterName AS AssignmentName,
        'ManagerID' AS AssignmentColumn,
        ManagerID AS EmployeeID
    FROM CostCenter
    WHERE ManagerID IS NOT NULL

    UNION ALL

    SELECT
        'Warehouse',
        WarehouseID,
        WarehouseName,
        'ManagerID',
        ManagerID
    FROM Warehouse
    WHERE ManagerID IS NOT NULL

    UNION ALL

    SELECT
        'WorkCenter',
        WorkCenterID,
        WorkCenterName,
        'ManagerEmployeeID',
        ManagerEmployeeID
    FROM WorkCenter
    WHERE ManagerEmployeeID IS NOT NULL

    UNION ALL

    SELECT
        'Customer',
        CustomerID,
        CustomerName,
        'SalesRepEmployeeID',
        SalesRepEmployeeID
    FROM Customer
    WHERE SalesRepEmployeeID IS NOT NULL
)
SELECT
    ca.AssignmentTable,
    ca.AssignmentKey,
    ca.AssignmentName,
    ca.AssignmentColumn,
    e.EmployeeNumber,
    e.EmployeeName,
    e.JobTitle,
    e.JobFamily,
    e.EmploymentStatus,
    date(e.HireDate) AS HireDate,
    date(e.TerminationDate) AS TerminationDate,
    CAST(e.IsActive AS INTEGER) AS IsActive,
    CASE
        WHEN e.EmploymentStatus = 'Terminated' THEN 'Terminated Employee Still Assigned'
        WHEN CAST(e.IsActive AS INTEGER) = 0 THEN 'Inactive Employee Still Assigned'
        ELSE 'Review'
    END AS ReviewFlag
FROM current_assignments AS ca
JOIN Employee AS e
    ON e.EmployeeID = ca.EmployeeID
WHERE e.EmploymentStatus = 'Terminated'
   OR CAST(e.IsActive AS INTEGER) = 0
ORDER BY
    ca.AssignmentTable,
    ca.AssignmentName,
    e.EmployeeNumber;
