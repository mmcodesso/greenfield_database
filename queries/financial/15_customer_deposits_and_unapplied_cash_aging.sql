-- Teaching objective: Review customer deposits and unapplied cash that remain open after receipt.
-- Main tables: CashReceipt, CashReceiptApplication, Customer.
-- Expected output shape: One row per cash receipt with application timing and open unapplied balance.
-- Recommended build mode: Either; standard anomaly builds add more exception-style timing patterns.
-- Interpretation notes: Cash receipts do not settle AR until `CashReceiptApplication` applies them to invoices.

WITH snapshot AS (
    SELECT MAX(date(ReceiptDate)) AS SnapshotDate
    FROM CashReceipt
),
receipt_applications AS (
    SELECT
        CashReceiptID,
        ROUND(SUM(AppliedAmount), 2) AS AppliedAmount,
        MIN(date(ApplicationDate)) AS FirstApplicationDate,
        MAX(date(ApplicationDate)) AS LastApplicationDate,
        COUNT(DISTINCT SalesInvoiceID) AS AppliedInvoiceCount
    FROM CashReceiptApplication
    GROUP BY CashReceiptID
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
    ra.LastApplicationDate,
    ROUND(julianday(s.SnapshotDate) - julianday(date(cr.ReceiptDate)), 2) AS AgeDaysAtSnapshot,
    ROUND(
        julianday(COALESCE(ra.FirstApplicationDate, s.SnapshotDate)) - julianday(date(cr.ReceiptDate)),
        2
    ) AS DaysToFirstApplication
FROM CashReceipt AS cr
JOIN Customer AS c
    ON c.CustomerID = cr.CustomerID
CROSS JOIN snapshot AS s
LEFT JOIN receipt_applications AS ra
    ON ra.CashReceiptID = cr.CashReceiptID
WHERE ROUND(cr.Amount - COALESCE(ra.AppliedAmount, 0), 2) > 0
   OR COALESCE(ra.AppliedAmount, 0) = 0
ORDER BY OpenUnappliedAmount DESC, AgeDaysAtSnapshot DESC, cr.ReceiptNumber;
