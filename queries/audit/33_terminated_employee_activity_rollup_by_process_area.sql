-- Teaching objective: Roll up post-termination activity by process area so students can see where workforce-control failures appear.
-- Main tables: Employee, PayrollRegister, TimeClockEntry, LaborTimeEntry, PurchaseRequisition, PurchaseOrder, PurchaseInvoice, CreditMemo, CustomerRefund, JournalEntry.
-- Expected output shape: One row per process area and source table with counts of post-termination activity.
-- Recommended build mode: Default.
-- Interpretation notes: This query summarizes the same risk family from several tables. Use it with the detail review query when you want to trace individual exceptions.

WITH terminated_employees AS (
    SELECT
        EmployeeID,
        EmployeeNumber,
        EmployeeName,
        date(TerminationDate) AS TerminationDate
    FROM Employee
    WHERE EmploymentStatus = 'Terminated'
      AND TerminationDate IS NOT NULL
),
activity_events AS (
    SELECT
        'Payroll' AS ProcessArea,
        'PayrollRegister' AS SourceTable,
        pr.EmployeeID,
        date(pr.ApprovedDate) AS ActivityDate
    FROM PayrollRegister AS pr

    UNION ALL

    SELECT
        'Time',
        'TimeClockEntry',
        tc.EmployeeID,
        date(tc.WorkDate)
    FROM TimeClockEntry AS tc

    UNION ALL

    SELECT
        'Labor',
        'LaborTimeEntry',
        lte.EmployeeID,
        date(lte.WorkDate)
    FROM LaborTimeEntry AS lte

    UNION ALL

    SELECT
        'Approvals',
        'PurchaseRequisition',
        ApprovedByEmployeeID,
        date(ApprovedDate)
    FROM PurchaseRequisition
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT
        'Approvals',
        'PurchaseOrder',
        ApprovedByEmployeeID,
        date(OrderDate)
    FROM PurchaseOrder
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT
        'Approvals',
        'PurchaseInvoice',
        ApprovedByEmployeeID,
        date(ApprovedDate)
    FROM PurchaseInvoice
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT
        'Approvals',
        'CreditMemo',
        ApprovedByEmployeeID,
        date(ApprovedDate)
    FROM CreditMemo
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT
        'Approvals',
        'CustomerRefund',
        ApprovedByEmployeeID,
        date(RefundDate)
    FROM CustomerRefund
    WHERE ApprovedByEmployeeID IS NOT NULL

    UNION ALL

    SELECT
        'Approvals',
        'JournalEntry',
        ApprovedByEmployeeID,
        date(ApprovedDate)
    FROM JournalEntry
    WHERE ApprovedByEmployeeID IS NOT NULL
),
post_termination_activity AS (
    SELECT
        ae.ProcessArea,
        ae.SourceTable,
        te.EmployeeNumber,
        te.EmployeeName,
        te.TerminationDate,
        ae.ActivityDate
    FROM activity_events AS ae
    JOIN terminated_employees AS te
        ON te.EmployeeID = ae.EmployeeID
    WHERE ae.ActivityDate > te.TerminationDate
)
SELECT
    ProcessArea,
    SourceTable,
    COUNT(*) AS PostTerminationActivityCount,
    COUNT(DISTINCT EmployeeNumber) AS AffectedEmployeeCount,
    MIN(ActivityDate) AS FirstPostTerminationActivityDate,
    MAX(ActivityDate) AS LastPostTerminationActivityDate
FROM post_termination_activity
GROUP BY
    ProcessArea,
    SourceTable
ORDER BY
    PostTerminationActivityCount DESC,
    ProcessArea,
    SourceTable;
