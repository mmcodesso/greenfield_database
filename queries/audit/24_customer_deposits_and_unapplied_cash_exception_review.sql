-- Teaching objective: Review customer receipts that remain unapplied or show unusual application timing.
-- Main tables: CashReceipt, CashReceiptApplication, Customer.
-- Expected output shape: One row per customer receipt flagged for deposit or unapplied-cash review.
-- Recommended build mode: Either.
-- Interpretation notes: Open unapplied cash is not automatically wrong, but it is an important audit-style follow-up area.

WITH receipt_applications AS (
    SELECT
        CashReceiptID,
        ROUND(SUM(AppliedAmount), 2) AS AppliedAmount,
        MIN(date(ApplicationDate)) AS FirstApplicationDate,
        COUNT(DISTINCT SalesInvoiceID) AS AppliedInvoiceCount
    FROM CashReceiptApplication
    GROUP BY CashReceiptID
),
snapshot AS (
    SELECT MAX(date(ReceiptDate)) AS SnapshotDate
    FROM CashReceipt
)
SELECT
    cr.ReceiptNumber,
    date(cr.ReceiptDate) AS ReceiptDate,
    c.CustomerName,
    ROUND(cr.Amount, 2) AS ReceiptAmount,
    ROUND(COALESCE(ra.AppliedAmount, 0), 2) AS AppliedAmount,
    ROUND(cr.Amount - COALESCE(ra.AppliedAmount, 0), 2) AS OpenUnappliedAmount,
    ra.AppliedInvoiceCount,
    ra.FirstApplicationDate,
    ROUND(julianday((SELECT SnapshotDate FROM snapshot)) - julianday(date(cr.ReceiptDate)), 2) AS AgeDaysAtSnapshot,
    CASE
        WHEN ra.FirstApplicationDate IS NOT NULL
         AND julianday(ra.FirstApplicationDate) < julianday(date(cr.ReceiptDate))
            THEN 'Receipt application dated before receipt date'
        WHEN ROUND(cr.Amount - COALESCE(ra.AppliedAmount, 0), 2) > 0
         AND julianday((SELECT SnapshotDate FROM snapshot)) - julianday(date(cr.ReceiptDate)) > 30
            THEN 'Open unapplied cash older than 30 days'
        ELSE 'Review customer deposit or unapplied cash balance'
    END AS PotentialIssue
FROM CashReceipt AS cr
JOIN Customer AS c
    ON c.CustomerID = cr.CustomerID
LEFT JOIN receipt_applications AS ra
    ON ra.CashReceiptID = cr.CashReceiptID
WHERE (ra.FirstApplicationDate IS NOT NULL AND julianday(ra.FirstApplicationDate) < julianday(date(cr.ReceiptDate)))
   OR ROUND(cr.Amount - COALESCE(ra.AppliedAmount, 0), 2) > 0
ORDER BY OpenUnappliedAmount DESC, AgeDaysAtSnapshot DESC, cr.ReceiptNumber;
