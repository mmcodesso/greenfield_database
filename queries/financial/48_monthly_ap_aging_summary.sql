-- Teaching objective: Summarize month-end accounts payable aging positions by supplier across the full dataset timeline.
-- Main tables: PurchaseInvoice, DisbursementPayment, Supplier.
-- Output shape: One row per month-end and supplier.
-- Interpretation notes: Month-end positions use the last calendar day of each month and reflect only disbursements posted on or before that month-end.

WITH RECURSIVE activity_bounds AS (
    SELECT
        date(MIN(ActivityDate), 'start of month') AS StartMonth,
        date(MAX(ActivityDate), 'start of month') AS EndMonth
    FROM (
        SELECT InvoiceDate AS ActivityDate FROM PurchaseInvoice
        UNION ALL
        SELECT PaymentDate AS ActivityDate FROM DisbursementPayment
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
        ON dp.PaymentDate <= me.MonthEndDate
    GROUP BY me.MonthEndDate, dp.PurchaseInvoiceID
),
detail_rows AS (
    SELECT
        oia.MonthEndDate,
        s.SupplierName,
        s.SupplierCategory,
        s.SupplierRiskRating,
        oia.DaysFromDueAtMonthEnd,
        oia.OpenAmountAsOfMonthEnd
    FROM (
        SELECT
            me.MonthEndDate,
            pi.SupplierID,
            CAST(julianday(me.MonthEndDate) - julianday(pi.DueDate) AS INTEGER) AS DaysFromDueAtMonthEnd,
            ROUND(pi.GrandTotal - COALESCE(cpm.CashPaidAsOfMonthEnd, 0), 2) AS OpenAmountAsOfMonthEnd
        FROM month_ends AS me
        JOIN PurchaseInvoice AS pi
            ON pi.InvoiceDate <= me.MonthEndDate
        LEFT JOIN cash_paid_by_month AS cpm
            ON cpm.MonthEndDate = me.MonthEndDate
           AND cpm.PurchaseInvoiceID = pi.PurchaseInvoiceID
        WHERE ROUND(pi.GrandTotal - COALESCE(cpm.CashPaidAsOfMonthEnd, 0), 2) > 0
    ) AS oia
    JOIN Supplier AS s
        ON s.SupplierID = oia.SupplierID
)
SELECT
    MonthEndDate,
    SupplierName,
    SupplierCategory,
    SupplierRiskRating,
    COUNT(*) AS OpenInvoiceCount,
    ROUND(SUM(OpenAmountAsOfMonthEnd), 2) AS TotalOpenAmount,
    ROUND(SUM(CASE WHEN DaysFromDueAtMonthEnd <= 0 THEN OpenAmountAsOfMonthEnd ELSE 0 END), 2) AS CurrentAmount,
    ROUND(SUM(CASE WHEN DaysFromDueAtMonthEnd BETWEEN 1 AND 30 THEN OpenAmountAsOfMonthEnd ELSE 0 END), 2) AS Days1To30Amount,
    ROUND(SUM(CASE WHEN DaysFromDueAtMonthEnd BETWEEN 31 AND 60 THEN OpenAmountAsOfMonthEnd ELSE 0 END), 2) AS Days31To60Amount,
    ROUND(SUM(CASE WHEN DaysFromDueAtMonthEnd BETWEEN 61 AND 90 THEN OpenAmountAsOfMonthEnd ELSE 0 END), 2) AS Days61To90Amount,
    ROUND(SUM(CASE WHEN DaysFromDueAtMonthEnd > 90 THEN OpenAmountAsOfMonthEnd ELSE 0 END), 2) AS Days90PlusAmount,
    ROUND(SUM(CASE WHEN DaysFromDueAtMonthEnd > 0 THEN OpenAmountAsOfMonthEnd ELSE 0 END), 2) AS PastDueAmount,
    MAX(CASE WHEN DaysFromDueAtMonthEnd > 0 THEN DaysFromDueAtMonthEnd END) AS OldestDaysPastDue
FROM detail_rows
GROUP BY MonthEndDate, SupplierName, SupplierCategory, SupplierRiskRating
ORDER BY MonthEndDate, TotalOpenAmount DESC, SupplierName;
