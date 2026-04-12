-- Teaching objective: Compare document approval amounts to approver limits and expected approver role families.
-- Main tables: PurchaseOrder, PurchaseInvoice, CreditMemo, CustomerRefund, JournalEntry, PayrollRegister, Employee.
-- Expected output shape: One row per flagged approval event.
-- Recommended build mode: Default.
-- Interpretation notes: Use this query to separate authority-limit exceptions from role-family exceptions. Some rows may show both flags at once.

WITH approvals AS (
    SELECT
        'Purchase Order' AS DocumentType,
        PONumber AS DocumentNumber,
        date(OrderDate) AS DocumentDate,
        OrderTotal AS DocumentAmount,
        ApprovedByEmployeeID
    FROM PurchaseOrder
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT
        'Purchase Invoice',
        InvoiceNumber,
        date(ApprovedDate),
        GrandTotal,
        ApprovedByEmployeeID
    FROM PurchaseInvoice
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT
        'Credit Memo',
        CreditMemoNumber,
        date(ApprovedDate),
        GrandTotal,
        ApprovedByEmployeeID
    FROM CreditMemo
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT
        'Customer Refund',
        RefundNumber,
        date(RefundDate),
        Amount,
        ApprovedByEmployeeID
    FROM CustomerRefund
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT
        'Journal Entry',
        EntryNumber,
        date(ApprovedDate),
        TotalAmount,
        ApprovedByEmployeeID
    FROM JournalEntry
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT
        'Payroll Register',
        'PR-' || CAST(PayrollRegisterID AS TEXT),
        date(ApprovedDate),
        GrossPay,
        ApprovedByEmployeeID
    FROM PayrollRegister
    WHERE ApprovedByEmployeeID IS NOT NULL
),
expected_role_families AS (
    SELECT 'Purchase Order' AS DocumentType, 'Finance and Accounting' AS ExpectedRoleFamily
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
approval_review AS (
    SELECT
        a.DocumentType,
        a.DocumentNumber,
        a.DocumentDate,
        ROUND(a.DocumentAmount, 2) AS DocumentAmount,
        e.EmployeeNumber,
        e.EmployeeName,
        e.JobTitle,
        e.JobFamily,
        e.JobLevel,
        e.AuthorizationLevel,
        ROUND(COALESCE(e.MaxApprovalAmount, 0), 2) AS MaxApprovalAmount,
        el.ExpectedRoleFamilies,
        CASE
            WHEN ROUND(a.DocumentAmount, 2) > ROUND(COALESCE(e.MaxApprovalAmount, 0), 2) THEN 1
            ELSE 0
        END AS AboveAuthorityLimitFlag,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM expected_role_families AS erf
                WHERE erf.DocumentType = a.DocumentType
                  AND erf.ExpectedRoleFamily = e.JobFamily
            ) THEN 0
            ELSE 1
        END AS OutsideExpectedRoleFamilyFlag
    FROM approvals AS a
    JOIN Employee AS e
        ON e.EmployeeID = a.ApprovedByEmployeeID
    JOIN expected_lists AS el
        ON el.DocumentType = a.DocumentType
)
SELECT
    DocumentType,
    DocumentNumber,
    DocumentDate,
    DocumentAmount,
    EmployeeNumber,
    EmployeeName,
    JobTitle,
    JobFamily,
    JobLevel,
    AuthorizationLevel,
    MaxApprovalAmount,
    ExpectedRoleFamilies,
    AboveAuthorityLimitFlag,
    OutsideExpectedRoleFamilyFlag,
    CASE
        WHEN AboveAuthorityLimitFlag = 1 AND OutsideExpectedRoleFamilyFlag = 1 THEN 'Above Limit and Outside Expected Role Family'
        WHEN AboveAuthorityLimitFlag = 1 THEN 'Above Approval Limit'
        WHEN OutsideExpectedRoleFamilyFlag = 1 THEN 'Outside Expected Role Family'
    END AS ReviewFlag
FROM approval_review
WHERE AboveAuthorityLimitFlag = 1
   OR OutsideExpectedRoleFamilyFlag = 1
ORDER BY
    AboveAuthorityLimitFlag DESC,
    OutsideExpectedRoleFamilyFlag DESC,
    DocumentDate,
    DocumentType,
    DocumentNumber;
