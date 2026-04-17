-- Teaching objective: Summarize month-end accounts receivable aging positions by customer across the full dataset timeline.
-- Main tables: SalesInvoice, CashReceiptApplication, CreditMemo, Customer.
-- Output shape: One row per month-end and customer.
-- Interpretation notes: Month-end positions use the last calendar day of each month and reflect only cash applications and credit memos posted on or before that month-end.

WITH RECURSIVE activity_bounds AS (
    SELECT
        date(MIN(ActivityDate), 'start of month') AS StartMonth,
        date(MAX(ActivityDate), 'start of month') AS EndMonth
    FROM (
        SELECT date(InvoiceDate) AS ActivityDate FROM SalesInvoice
        UNION ALL
        SELECT date(ApplicationDate) AS ActivityDate FROM CashReceiptApplication
        UNION ALL
        SELECT date(CreditMemoDate) AS ActivityDate FROM CreditMemo
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
cash_applications_by_month AS (
    SELECT
        me.MonthEndDate,
        cra.SalesInvoiceID,
        ROUND(SUM(cra.AppliedAmount), 2) AS CashAppliedAsOfMonthEnd
    FROM month_ends AS me
    JOIN CashReceiptApplication AS cra
        ON date(cra.ApplicationDate) <= me.MonthEndDate
    GROUP BY me.MonthEndDate, cra.SalesInvoiceID
),
credit_memos_by_month AS (
    SELECT
        me.MonthEndDate,
        cm.CreditMemoID,
        cm.OriginalSalesInvoiceID AS SalesInvoiceID,
        ROUND(si.GrandTotal, 2) AS InvoiceAmount,
        ROUND(COALESCE(cam.CashAppliedAsOfMonthEnd, 0), 2) AS CashAppliedAsOfMonthEnd,
        ROUND(cm.GrandTotal, 2) AS CreditMemoAmount,
        ROUND(
            COALESCE(
                SUM(cm.GrandTotal) OVER (
                    PARTITION BY me.MonthEndDate, cm.OriginalSalesInvoiceID
                    ORDER BY date(cm.CreditMemoDate), cm.CreditMemoID
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ),
                0
            ),
            2
        ) AS PriorCreditAmount
    FROM month_ends AS me
    JOIN CreditMemo AS cm
        ON date(cm.CreditMemoDate) <= me.MonthEndDate
    JOIN SalesInvoice AS si
        ON si.SalesInvoiceID = cm.OriginalSalesInvoiceID
    LEFT JOIN cash_applications_by_month AS cam
        ON cam.MonthEndDate = me.MonthEndDate
       AND cam.SalesInvoiceID = cm.OriginalSalesInvoiceID
),
credit_memo_allocations_by_month AS (
    SELECT
        MonthEndDate,
        SalesInvoiceID,
        ROUND(
            CASE
                WHEN CreditMemoAmount <= MAX(0, InvoiceAmount - CashAppliedAsOfMonthEnd - PriorCreditAmount)
                    THEN CreditMemoAmount
                ELSE MAX(0, InvoiceAmount - CashAppliedAsOfMonthEnd - PriorCreditAmount)
            END,
            2
        ) AS CreditMemoAppliedAsOfMonthEnd
    FROM credit_memos_by_month
),
credit_memo_totals_by_month AS (
    SELECT
        MonthEndDate,
        SalesInvoiceID,
        ROUND(SUM(CreditMemoAppliedAsOfMonthEnd), 2) AS CreditMemoAppliedAsOfMonthEnd
    FROM credit_memo_allocations_by_month
    GROUP BY MonthEndDate, SalesInvoiceID
),
detail_rows AS (
    SELECT
        me.MonthEndDate,
        c.CustomerName,
        c.Region,
        c.CustomerSegment,
        CAST(julianday(me.MonthEndDate) - julianday(si.DueDate) AS INTEGER) AS DaysFromDueAtMonthEnd,
        ROUND(
            si.GrandTotal - COALESCE(cam.CashAppliedAsOfMonthEnd, 0) - COALESCE(cmt.CreditMemoAppliedAsOfMonthEnd, 0),
            2
        ) AS OpenAmountAsOfMonthEnd
    FROM month_ends AS me
    JOIN SalesInvoice AS si
        ON date(si.InvoiceDate) <= me.MonthEndDate
    JOIN Customer AS c
        ON c.CustomerID = si.CustomerID
    LEFT JOIN cash_applications_by_month AS cam
        ON cam.MonthEndDate = me.MonthEndDate
       AND cam.SalesInvoiceID = si.SalesInvoiceID
    LEFT JOIN credit_memo_totals_by_month AS cmt
        ON cmt.MonthEndDate = me.MonthEndDate
       AND cmt.SalesInvoiceID = si.SalesInvoiceID
    WHERE ROUND(
        si.GrandTotal - COALESCE(cam.CashAppliedAsOfMonthEnd, 0) - COALESCE(cmt.CreditMemoAppliedAsOfMonthEnd, 0),
        2
    ) > 0
)
SELECT
    MonthEndDate,
    CustomerName,
    Region,
    CustomerSegment,
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
GROUP BY MonthEndDate, CustomerName, Region, CustomerSegment
ORDER BY MonthEndDate, TotalOpenAmount DESC, CustomerName;
