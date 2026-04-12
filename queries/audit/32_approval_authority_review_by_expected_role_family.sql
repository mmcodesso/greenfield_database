-- Teaching objective: Compare expected approver role families to the roles that actually approve key document families.
-- Main tables: Employee, PurchaseRequisition, PurchaseOrder, PurchaseInvoice, CreditMemo, CustomerRefund, JournalEntry, PayrollRegister.
-- Expected output shape: One row per document type and observed approver role family.
-- Recommended build mode: Default.
-- Interpretation notes: This is a control-design review query. It shows who is actually approving documents, even when there is no planted anomaly.

WITH approvals AS (
    SELECT 'Purchase Requisition' AS DocumentType, ApprovedByEmployeeID
    FROM PurchaseRequisition
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT 'Purchase Order', ApprovedByEmployeeID
    FROM PurchaseOrder
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT 'Purchase Invoice', ApprovedByEmployeeID
    FROM PurchaseInvoice
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT 'Credit Memo', ApprovedByEmployeeID
    FROM CreditMemo
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT 'Customer Refund', ApprovedByEmployeeID
    FROM CustomerRefund
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT 'Journal Entry', ApprovedByEmployeeID
    FROM JournalEntry
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT 'Payroll Register', ApprovedByEmployeeID
    FROM PayrollRegister
    WHERE ApprovedByEmployeeID IS NOT NULL
),
expected_role_families AS (
    SELECT 'Purchase Requisition' AS DocumentType, 'Finance and Accounting' AS ExpectedRoleFamily
    UNION ALL SELECT 'Purchase Requisition', 'Executive Leadership'
    UNION ALL SELECT 'Purchase Order', 'Finance and Accounting'
    UNION ALL SELECT 'Purchase Order', 'Executive Leadership'
    UNION ALL SELECT 'Purchase Invoice', 'Finance and Accounting'
    UNION ALL SELECT 'Credit Memo', 'Finance and Accounting'
    UNION ALL SELECT 'Credit Memo', 'Executive Leadership'
    UNION ALL SELECT 'Customer Refund', 'Finance and Accounting'
    UNION ALL SELECT 'Customer Refund', 'Executive Leadership'
    UNION ALL SELECT 'Journal Entry', 'Finance and Accounting'
    UNION ALL SELECT 'Journal Entry', 'Executive Leadership'
    UNION ALL SELECT 'Payroll Register', 'Finance and Accounting'
    UNION ALL SELECT 'Payroll Register', 'Executive Leadership'
),
expected_lists AS (
    SELECT
        DocumentType,
        GROUP_CONCAT(ExpectedRoleFamily, ', ') AS ExpectedRoleFamilies
    FROM expected_role_families
    GROUP BY DocumentType
),
approval_summary AS (
    SELECT
        a.DocumentType,
        COALESCE(e.JobFamily, '(No Job Family)') AS ObservedJobFamily,
        COALESCE(e.JobTitle, '(No Job Title)') AS ObservedJobTitle,
        COUNT(*) AS ApprovalCount,
        COUNT(DISTINCT a.ApprovedByEmployeeID) AS DistinctApprovers
    FROM approvals AS a
    JOIN Employee AS e
        ON e.EmployeeID = a.ApprovedByEmployeeID
    GROUP BY
        a.DocumentType,
        COALESCE(e.JobFamily, '(No Job Family)'),
        COALESCE(e.JobTitle, '(No Job Title)')
)
SELECT
    aps.DocumentType,
    el.ExpectedRoleFamilies,
    aps.ObservedJobFamily,
    aps.ObservedJobTitle,
    aps.ApprovalCount,
    aps.DistinctApprovers,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM expected_role_families AS erf
            WHERE erf.DocumentType = aps.DocumentType
              AND erf.ExpectedRoleFamily = aps.ObservedJobFamily
        ) THEN 0
        ELSE 1
    END AS OutsideExpectedRoleFamilyFlag
FROM approval_summary AS aps
JOIN expected_lists AS el
    ON el.DocumentType = aps.DocumentType
ORDER BY
    aps.DocumentType,
    OutsideExpectedRoleFamilyFlag DESC,
    aps.ApprovalCount DESC,
    aps.ObservedJobFamily,
    aps.ObservedJobTitle;
