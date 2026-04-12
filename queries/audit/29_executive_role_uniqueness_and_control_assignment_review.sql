-- Teaching objective: Review whether key executive and control-owner roles are unique and where those role holders appear in current-state assignments and approvals.
-- Main tables: Employee, CostCenter, Warehouse, WorkCenter, PurchaseOrder, PurchaseInvoice, CreditMemo, CustomerRefund, JournalEntry, PayrollRegister.
-- Expected output shape: One row per key role holder, with role counts and control-assignment evidence.
-- Recommended build mode: Default.
-- Interpretation notes: Duplicate rows for the same key role are a red flag. Current-state assignments and approval counts help students connect org structure to control ownership.

WITH key_roles AS (
    SELECT 'Chief Executive Officer' AS JobTitle
    UNION ALL SELECT 'Chief Financial Officer'
    UNION ALL SELECT 'Controller'
    UNION ALL SELECT 'Production Manager'
    UNION ALL SELECT 'Accounting Manager'
),
control_assignments AS (
    SELECT ManagerID AS EmployeeID, 'Cost Center Manager' AS ControlArea
    FROM CostCenter
    WHERE ManagerID IS NOT NULL

    UNION ALL

    SELECT ManagerID, 'Warehouse Manager'
    FROM Warehouse
    WHERE ManagerID IS NOT NULL

    UNION ALL

    SELECT ManagerEmployeeID, 'Work Center Manager'
    FROM WorkCenter
    WHERE ManagerEmployeeID IS NOT NULL
),
approval_events AS (
    SELECT ApprovedByEmployeeID AS EmployeeID, 'Purchase Order Approval' AS ApprovalArea
    FROM PurchaseOrder
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT ApprovedByEmployeeID, 'Purchase Invoice Approval'
    FROM PurchaseInvoice
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT ApprovedByEmployeeID, 'Credit Memo Approval'
    FROM CreditMemo
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT ApprovedByEmployeeID, 'Customer Refund Approval'
    FROM CustomerRefund
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT ApprovedByEmployeeID, 'Journal Entry Approval'
    FROM JournalEntry
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT ApprovedByEmployeeID, 'Payroll Register Approval'
    FROM PayrollRegister
    WHERE ApprovedByEmployeeID IS NOT NULL
),
role_holders AS (
    SELECT
        e.EmployeeID,
        e.EmployeeNumber,
        e.EmployeeName,
        e.JobTitle,
        e.JobFamily,
        e.JobLevel,
        e.EmploymentStatus,
        CAST(e.IsActive AS INTEGER) AS IsActive,
        COUNT(*) OVER (PARTITION BY e.JobTitle) AS EmployeeCountForRole
    FROM Employee AS e
    JOIN key_roles AS kr
        ON kr.JobTitle = e.JobTitle
),
control_summary AS (
    SELECT
        EmployeeID,
        COUNT(*) AS CurrentStateControlAssignments,
        COUNT(DISTINCT ControlArea) AS DistinctControlAreas
    FROM control_assignments
    GROUP BY EmployeeID
),
approval_summary AS (
    SELECT
        EmployeeID,
        COUNT(*) AS ApprovalEventCount,
        COUNT(DISTINCT ApprovalArea) AS DistinctApprovalAreas
    FROM approval_events
    GROUP BY EmployeeID
)
SELECT
    rh.JobTitle AS KeyRole,
    rh.EmployeeCountForRole,
    rh.EmployeeNumber,
    rh.EmployeeName,
    rh.JobFamily,
    rh.JobLevel,
    rh.EmploymentStatus,
    rh.IsActive,
    COALESCE(cs.CurrentStateControlAssignments, 0) AS CurrentStateControlAssignments,
    COALESCE(cs.DistinctControlAreas, 0) AS DistinctControlAreas,
    COALESCE(aps.ApprovalEventCount, 0) AS ApprovalEventCount,
    COALESCE(aps.DistinctApprovalAreas, 0) AS DistinctApprovalAreas,
    CASE
        WHEN rh.EmployeeCountForRole = 1 THEN 'Unique'
        ELSE 'Duplicate Role Holder'
    END AS RoleUniquenessStatus
FROM role_holders AS rh
LEFT JOIN control_summary AS cs
    ON cs.EmployeeID = rh.EmployeeID
LEFT JOIN approval_summary AS aps
    ON aps.EmployeeID = rh.EmployeeID
ORDER BY
    rh.JobTitle,
    rh.EmployeeName;
