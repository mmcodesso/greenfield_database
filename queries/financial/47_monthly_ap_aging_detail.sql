-- Teaching objective: Reconstruct month-end accounts payable aging positions across the full dataset timeline.
-- Main tables: PurchaseInvoice, DisbursementPayment, Supplier.
-- Output shape: One row per open supplier invoice per month-end.
-- Interpretation notes: Month-end positions use the last calendar day of each month and reflect only disbursements posted on or before that month-end.

WITH RECURSIVE activity_bounds AS (
    SELECT
        date(MIN(ActivityDate), 'start of month') AS StartMonth,
        date(MAX(ActivityDate), 'start of month') AS EndMonth
    FROM (
        SELECT date(InvoiceDate) AS ActivityDate FROM PurchaseInvoice
        UNION ALL
        SELECT date(PaymentDate) AS ActivityDate FROM DisbursementPayment
    )
),
month_starts AS (
    SELECT StartMonth AS MonthStart
    FROM activity_bounds
    WHERE StartMonth IS NOT NULL

    UNION ALL

    SELECT date(ms.MonthStart, '+1 month') AS MonthStart
    FROM month_starts AS ms
    JOIN activity_bounds AS ab
        ON 1 = 1
    WHERE ms.MonthStart < ab.EndMonth
),
month_ends AS (
    SELECT date(MonthStart, '+1 month', '-1 day') AS MonthEndDate
    FROM month_starts
),
cash_paid_by_month AS (
    SELECT
        me.MonthEndDate,
        dp.PurchaseInvoiceID,
        ROUND(SUM(dp.Amount), 2) AS CashPaidAsOfMonthEnd
    FROM month_ends AS me
    JOIN DisbursementPayment AS dp
        ON date(dp.PaymentDate) <= me.MonthEndDate
    GROUP BY me.MonthEndDate, dp.PurchaseInvoiceID
),
open_invoice_positions AS (
    SELECT
        me.MonthEndDate,
        strftime('%Y-%m', pi.InvoiceDate) AS InvoiceMonth,
        pi.InvoiceNumber,
        s.SupplierName,
        s.SupplierCategory,
        s.SupplierRiskRating,
        date(pi.InvoiceDate) AS InvoiceDate,
        date(pi.DueDate) AS DueDate,
        CAST(julianday(me.MonthEndDate) - julianday(pi.DueDate) AS INTEGER) AS DaysFromDueAtMonthEnd,
        ROUND(pi.GrandTotal, 2) AS InvoiceAmount,
        ROUND(COALESCE(cpm.CashPaidAsOfMonthEnd, 0), 2) AS CashPaidAsOfMonthEnd,
        ROUND(pi.GrandTotal - COALESCE(cpm.CashPaidAsOfMonthEnd, 0), 2) AS OpenAmountAsOfMonthEnd
    FROM month_ends AS me
    JOIN PurchaseInvoice AS pi
        ON date(pi.InvoiceDate) <= me.MonthEndDate
    JOIN Supplier AS s
        ON s.SupplierID = pi.SupplierID
    LEFT JOIN cash_paid_by_month AS cpm
        ON cpm.MonthEndDate = me.MonthEndDate
       AND cpm.PurchaseInvoiceID = pi.PurchaseInvoiceID
    WHERE ROUND(pi.GrandTotal - COALESCE(cpm.CashPaidAsOfMonthEnd, 0), 2) > 0
)
SELECT
    MonthEndDate,
    InvoiceMonth,
    InvoiceNumber,
    SupplierName,
    SupplierCategory,
    SupplierRiskRating,
    InvoiceDate,
    DueDate,
    DaysFromDueAtMonthEnd,
    CASE
        WHEN DaysFromDueAtMonthEnd <= 0 THEN 'Current'
        WHEN DaysFromDueAtMonthEnd <= 30 THEN '1-30 Days'
        WHEN DaysFromDueAtMonthEnd <= 60 THEN '31-60 Days'
        WHEN DaysFromDueAtMonthEnd <= 90 THEN '61-90 Days'
        ELSE '91+ Days'
    END AS AgingBucket,
    InvoiceAmount,
    CashPaidAsOfMonthEnd,
    OpenAmountAsOfMonthEnd
FROM open_invoice_positions
ORDER BY MonthEndDate, DaysFromDueAtMonthEnd DESC, OpenAmountAsOfMonthEnd DESC, InvoiceNumber;
