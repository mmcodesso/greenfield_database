-- Teaching objective: Trace annual net revenue from operational source documents into posted GL activity and the annual income statement.
-- Main tables: SalesInvoice, SalesInvoiceLine, CreditMemo, CreditMemoLine, GLEntry, Account, JournalEntry.
-- Expected output shape: One row per fiscal year with operational, pre-close GL, and statement net-revenue totals plus variances.
-- Recommended build mode: Either. Start with the clean build to confirm the revenue pipeline before investigating anomalies.
-- Interpretation notes: Operational gross revenue should tie to invoice merchandise plus billed freight, contra revenue should tie to credit-memo merchandise plus freight credits, and both should reconcile to the pre-close GL and annual income statement.

WITH closed_years AS (
    SELECT
        CAST(substr(PostingDate, 1, 4) AS INTEGER) AS FiscalYear
    FROM JournalEntry
    WHERE EntryType IN (
        'Year-End Close - P&L to Income Summary',
        'Year-End Close - Income Summary to Retained Earnings'
    )
    GROUP BY CAST(substr(PostingDate, 1, 4) AS INTEGER)
    HAVING COUNT(DISTINCT EntryType) = 2
),
invoice_line_totals AS (
    SELECT
        CAST(substr(si.InvoiceDate, 1, 4) AS INTEGER) AS FiscalYear,
        ROUND(SUM(sil.LineTotal), 2) AS MerchandiseRevenue
    FROM SalesInvoice AS si
    JOIN SalesInvoiceLine AS sil
        ON sil.SalesInvoiceID = si.SalesInvoiceID
    GROUP BY CAST(substr(si.InvoiceDate, 1, 4) AS INTEGER)
),
invoice_freight_totals AS (
    SELECT
        CAST(substr(InvoiceDate, 1, 4) AS INTEGER) AS FiscalYear,
        ROUND(SUM(FreightAmount), 2) AS FreightRevenue
    FROM SalesInvoice
    GROUP BY CAST(substr(InvoiceDate, 1, 4) AS INTEGER)
),
invoice_years AS (
    SELECT FiscalYear FROM invoice_line_totals
    UNION
    SELECT FiscalYear FROM invoice_freight_totals
),
invoice_totals AS (
    SELECT
        iy.FiscalYear,
        ROUND(COALESCE(ilt.MerchandiseRevenue, 0) + COALESCE(ift.FreightRevenue, 0), 2) AS OperationalGrossRevenue
    FROM invoice_years AS iy
    LEFT JOIN invoice_line_totals AS ilt
        ON ilt.FiscalYear = iy.FiscalYear
    LEFT JOIN invoice_freight_totals AS ift
        ON ift.FiscalYear = iy.FiscalYear
),
credit_memo_line_totals AS (
    SELECT
        CAST(substr(cm.CreditMemoDate, 1, 4) AS INTEGER) AS FiscalYear,
        ROUND(SUM(cml.LineTotal), 2) AS MerchandiseCredits
    FROM CreditMemo AS cm
    JOIN CreditMemoLine AS cml
        ON cml.CreditMemoID = cm.CreditMemoID
    GROUP BY CAST(substr(cm.CreditMemoDate, 1, 4) AS INTEGER)
),
credit_memo_freight_totals AS (
    SELECT
        CAST(substr(CreditMemoDate, 1, 4) AS INTEGER) AS FiscalYear,
        ROUND(SUM(FreightCreditAmount), 2) AS FreightCredits
    FROM CreditMemo
    GROUP BY CAST(substr(CreditMemoDate, 1, 4) AS INTEGER)
),
credit_memo_years AS (
    SELECT FiscalYear FROM credit_memo_line_totals
    UNION
    SELECT FiscalYear FROM credit_memo_freight_totals
),
credit_memo_totals AS (
    SELECT
        cmy.FiscalYear,
        ROUND(-(COALESCE(cmlt.MerchandiseCredits, 0) + COALESCE(cmft.FreightCredits, 0)), 2) AS OperationalContraRevenue
    FROM credit_memo_years AS cmy
    LEFT JOIN credit_memo_line_totals AS cmlt
        ON cmlt.FiscalYear = cmy.FiscalYear
    LEFT JOIN credit_memo_freight_totals AS cmft
        ON cmft.FiscalYear = cmy.FiscalYear
),
pre_close_gl_revenue AS (
    SELECT
        gl.FiscalYear,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Revenue'
             AND a.AccountSubType = 'Operating Revenue'
             AND CAST(a.AccountNumber AS INTEGER) BETWEEN 4000 AND 4059
                THEN gl.Credit - gl.Debit
            ELSE 0
        END), 2) AS PreCloseGlGrossRevenue,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Revenue'
             AND a.AccountSubType = 'Contra Revenue'
             AND CAST(a.AccountNumber AS INTEGER) BETWEEN 4060 AND 4099
                THEN gl.Credit - gl.Debit
            ELSE 0
        END), 2) AS PreCloseGlContraRevenue
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountSubType <> 'Header'
      AND COALESCE(je.EntryType, '') NOT IN (
            'Year-End Close - P&L to Income Summary',
            'Year-End Close - Income Summary to Retained Earnings'
      )
      AND (
            (
                a.AccountType = 'Revenue'
                AND a.AccountSubType = 'Operating Revenue'
                AND CAST(a.AccountNumber AS INTEGER) BETWEEN 4000 AND 4059
            )
            OR (
                a.AccountType = 'Revenue'
                AND a.AccountSubType = 'Contra Revenue'
                AND CAST(a.AccountNumber AS INTEGER) BETWEEN 4060 AND 4099
            )
      )
    GROUP BY gl.FiscalYear
),
income_statement_net_revenue AS (
    SELECT
        gl.FiscalYear,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Revenue'
             AND a.AccountSubType = 'Operating Revenue'
             AND CAST(a.AccountNumber AS INTEGER) BETWEEN 4000 AND 4059
                THEN gl.Credit - gl.Debit
            WHEN a.AccountType = 'Revenue'
             AND a.AccountSubType = 'Contra Revenue'
             AND CAST(a.AccountNumber AS INTEGER) BETWEEN 4060 AND 4099
                THEN gl.Credit - gl.Debit
            ELSE 0
        END), 2) AS IncomeStatementNetRevenue
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountSubType <> 'Header'
      AND COALESCE(je.EntryType, '') NOT IN (
            'Year-End Close - P&L to Income Summary',
            'Year-End Close - Income Summary to Retained Earnings'
      )
      AND (
            (
                a.AccountType = 'Revenue'
                AND a.AccountSubType = 'Operating Revenue'
                AND CAST(a.AccountNumber AS INTEGER) BETWEEN 4000 AND 4059
            )
            OR (
                a.AccountType = 'Revenue'
                AND a.AccountSubType = 'Contra Revenue'
                AND CAST(a.AccountNumber AS INTEGER) BETWEEN 4060 AND 4099
            )
    )
    GROUP BY gl.FiscalYear
),
reporting_years AS (
    SELECT FiscalYear FROM closed_years
)
SELECT
    y.FiscalYear,
    ROUND(COALESCE(inv.OperationalGrossRevenue, 0), 2) AS OperationalGrossRevenue,
    ROUND(COALESCE(cm.OperationalContraRevenue, 0), 2) AS OperationalContraRevenue,
    ROUND(COALESCE(inv.OperationalGrossRevenue, 0) + COALESCE(cm.OperationalContraRevenue, 0), 2) AS OperationalNetRevenue,
    ROUND(COALESCE(glr.PreCloseGlGrossRevenue, 0), 2) AS PreCloseGlGrossRevenue,
    ROUND(COALESCE(glr.PreCloseGlContraRevenue, 0), 2) AS PreCloseGlContraRevenue,
    ROUND(COALESCE(glr.PreCloseGlGrossRevenue, 0) + COALESCE(glr.PreCloseGlContraRevenue, 0), 2) AS PreCloseGlNetRevenue,
    ROUND(COALESCE(isr.IncomeStatementNetRevenue, 0), 2) AS IncomeStatementNetRevenue,
    ROUND(
        (COALESCE(inv.OperationalGrossRevenue, 0) + COALESCE(cm.OperationalContraRevenue, 0))
        - (COALESCE(glr.PreCloseGlGrossRevenue, 0) + COALESCE(glr.PreCloseGlContraRevenue, 0)),
        2
    ) AS OperationalToPreCloseGlNetRevenueVariance,
    ROUND(
        (COALESCE(glr.PreCloseGlGrossRevenue, 0) + COALESCE(glr.PreCloseGlContraRevenue, 0))
        - COALESCE(isr.IncomeStatementNetRevenue, 0),
        2
    ) AS PreCloseGlToIncomeStatementNetRevenueVariance
FROM reporting_years AS y
LEFT JOIN invoice_totals AS inv
    ON inv.FiscalYear = y.FiscalYear
LEFT JOIN credit_memo_totals AS cm
    ON cm.FiscalYear = y.FiscalYear
LEFT JOIN pre_close_gl_revenue AS glr
    ON glr.FiscalYear = y.FiscalYear
LEFT JOIN income_statement_net_revenue AS isr
    ON isr.FiscalYear = y.FiscalYear
ORDER BY y.FiscalYear;
