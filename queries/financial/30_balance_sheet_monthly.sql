-- Teaching objective: Produce a detailed monthly classified balance sheet from posted general-ledger activity.
-- Main tables: GLEntry, Account, JournalEntry.
-- Output shape: One row per fiscal month and balance-sheet line.
-- Interpretation notes: The statement shows ending balances, not period activity. Interim equity includes a derived Current Year Earnings line so the statement ties before year-end close.

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
period_numbers AS (
    SELECT 1 AS FiscalPeriod
    UNION ALL SELECT 2
    UNION ALL SELECT 3
    UNION ALL SELECT 4
    UNION ALL SELECT 5
    UNION ALL SELECT 6
    UNION ALL SELECT 7
    UNION ALL SELECT 8
    UNION ALL SELECT 9
    UNION ALL SELECT 10
    UNION ALL SELECT 11
    UNION ALL SELECT 12
),
reporting_periods AS (
    SELECT
        cy.FiscalYear,
        pn.FiscalPeriod,
        ROW_NUMBER() OVER (ORDER BY cy.FiscalYear, pn.FiscalPeriod) AS PeriodIndex
    FROM closed_years AS cy
    CROSS JOIN period_numbers AS pn
),
balance_sheet_account_layout AS (
    SELECT
        CAST(AccountNumber AS INTEGER) AS AccountNumber,
        AccountName AS LineLabel,
        CASE
            WHEN AccountType = 'Asset'
             AND AccountSubType IN ('Current Asset', 'Contra Current Asset')
                THEN 'Current Assets'
            WHEN AccountType = 'Asset'
             AND AccountSubType IN ('Fixed Asset', 'Contra Fixed Asset', 'Noncurrent Asset')
                THEN 'Noncurrent Assets'
            WHEN AccountType = 'Liability'
             AND AccountSubType = 'Current Liability'
                THEN 'Current Liabilities'
            WHEN AccountType = 'Liability'
             AND AccountSubType = 'Long-Term Liability'
                THEN 'Long-Term Liabilities'
            WHEN AccountType = 'Equity'
             AND AccountSubType IN ('Equity', 'Contra Equity')
                THEN 'Equity'
            ELSE NULL
        END AS StatementSection,
        CASE
            WHEN AccountType = 'Asset'
             AND AccountSubType IN ('Current Asset', 'Contra Current Asset')
                THEN 100
            WHEN AccountType = 'Asset'
             AND AccountSubType IN ('Fixed Asset', 'Contra Fixed Asset', 'Noncurrent Asset')
                THEN 300
            WHEN AccountType = 'Liability'
             AND AccountSubType = 'Current Liability'
                THEN 500
            WHEN AccountType = 'Liability'
             AND AccountSubType = 'Long-Term Liability'
                THEN 700
            WHEN AccountType = 'Equity'
             AND AccountSubType IN ('Equity', 'Contra Equity')
                THEN 900
            ELSE NULL
        END AS SectionBaseOrder
    FROM Account
    WHERE AccountSubType <> 'Header'
      AND CAST(AccountNumber AS INTEGER) <> 3050
),
account_lines AS (
    SELECT
        AccountNumber,
        StatementSection,
        LineLabel,
        'account' AS LineType,
        SectionBaseOrder
            + ROW_NUMBER() OVER (
                PARTITION BY StatementSection
                ORDER BY AccountNumber, LineLabel
            ) AS DisplayOrder
    FROM balance_sheet_account_layout
    WHERE StatementSection IS NOT NULL
),
balance_sheet_period_activity AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        CAST(a.AccountNumber AS INTEGER) AS AccountNumber,
        SUM(
            CASE
                WHEN a.AccountType = 'Asset' THEN gl.Debit - gl.Credit
                WHEN a.AccountType IN ('Liability', 'Equity') THEN gl.Credit - gl.Debit
                ELSE 0
            END
        ) AS PeriodAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE gl.FiscalYear IN (SELECT FiscalYear FROM closed_years)
      AND CAST(a.AccountNumber AS INTEGER) IN (SELECT AccountNumber FROM account_lines)
    GROUP BY
        gl.FiscalYear,
        gl.FiscalPeriod,
        CAST(a.AccountNumber AS INTEGER)
),
running_account_balances AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        al.StatementSection,
        al.LineLabel,
        al.LineType,
        al.DisplayOrder,
        ROUND(
            SUM(COALESCE(bspa.PeriodAmount, 0)) OVER (
                PARTITION BY al.AccountNumber
                ORDER BY rp.PeriodIndex
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            2
        ) AS Amount
    FROM reporting_periods AS rp
    CROSS JOIN account_lines AS al
    LEFT JOIN balance_sheet_period_activity AS bspa
        ON bspa.FiscalYear = rp.FiscalYear
       AND bspa.FiscalPeriod = rp.FiscalPeriod
       AND bspa.AccountNumber = al.AccountNumber
),
pnl_period_activity AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        SUM(gl.Credit - gl.Debit) AS PeriodAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE gl.FiscalYear IN (SELECT FiscalYear FROM closed_years)
      AND a.AccountType IN ('Revenue', 'Expense')
      AND a.AccountSubType <> 'Header'
      AND COALESCE(je.EntryType, '') NOT IN (
            'Year-End Close - P&L to Income Summary',
            'Year-End Close - Income Summary to Retained Earnings'
      )
    GROUP BY gl.FiscalYear, gl.FiscalPeriod
),
retained_earnings_close_period_activity AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        SUM(gl.Credit - gl.Debit) AS PeriodAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE gl.FiscalYear IN (SELECT FiscalYear FROM closed_years)
      AND CAST(a.AccountNumber AS INTEGER) = 3030
      AND je.EntryType = 'Year-End Close - Income Summary to Retained Earnings'
    GROUP BY gl.FiscalYear, gl.FiscalPeriod
),
posted_current_year_earnings_period_activity AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        SUM(gl.Credit - gl.Debit) AS PeriodAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE gl.FiscalYear IN (SELECT FiscalYear FROM closed_years)
      AND CAST(a.AccountNumber AS INTEGER) = 3050
    GROUP BY gl.FiscalYear, gl.FiscalPeriod
),
derived_current_year_earnings AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        'Equity' AS StatementSection,
        'Current Year Earnings' AS LineLabel,
        'account' AS LineType,
        980 AS DisplayOrder,
        ROUND(
            COALESCE(
                SUM(COALESCE(pnl.PeriodAmount, 0)) OVER (
                    PARTITION BY rp.FiscalYear
                    ORDER BY rp.FiscalPeriod
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ),
                0
            )
            - COALESCE(
                SUM(COALESCE(reclose.PeriodAmount, 0)) OVER (
                    PARTITION BY rp.FiscalYear
                    ORDER BY rp.FiscalPeriod
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ),
                0
            )
            + COALESCE(
                SUM(COALESCE(p3050.PeriodAmount, 0)) OVER (
                    ORDER BY rp.PeriodIndex
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ),
                0
            ),
            2
        ) AS Amount
    FROM reporting_periods AS rp
    LEFT JOIN pnl_period_activity AS pnl
        ON pnl.FiscalYear = rp.FiscalYear
       AND pnl.FiscalPeriod = rp.FiscalPeriod
    LEFT JOIN retained_earnings_close_period_activity AS reclose
        ON reclose.FiscalYear = rp.FiscalYear
       AND reclose.FiscalPeriod = rp.FiscalPeriod
    LEFT JOIN posted_current_year_earnings_period_activity AS p3050
        ON p3050.FiscalYear = rp.FiscalYear
       AND p3050.FiscalPeriod = rp.FiscalPeriod
),
statement_accounts AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder,
        Amount
    FROM running_account_balances

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder,
        Amount
    FROM derived_current_year_earnings
),
section_summary AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        ROUND(SUM(CASE WHEN StatementSection = 'Current Assets' THEN Amount ELSE 0 END), 2) AS CurrentAssets,
        ROUND(SUM(CASE WHEN StatementSection = 'Noncurrent Assets' THEN Amount ELSE 0 END), 2) AS NoncurrentAssets,
        ROUND(SUM(CASE WHEN StatementSection = 'Current Liabilities' THEN Amount ELSE 0 END), 2) AS CurrentLiabilities,
        ROUND(SUM(CASE WHEN StatementSection = 'Long-Term Liabilities' THEN Amount ELSE 0 END), 2) AS LongTermLiabilities,
        ROUND(SUM(CASE WHEN StatementSection = 'Equity' THEN Amount ELSE 0 END), 2) AS EquityAmount
    FROM statement_accounts
    GROUP BY FiscalYear, FiscalPeriod
),
subtotal_lines AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        'Current Assets' AS StatementSection,
        'Total Current Assets' AS LineLabel,
        'subtotal' AS LineType,
        190 AS DisplayOrder,
        ROUND(CurrentAssets, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Noncurrent Assets' AS StatementSection,
        'Total Noncurrent Assets' AS LineLabel,
        'subtotal' AS LineType,
        390 AS DisplayOrder,
        ROUND(NoncurrentAssets, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Total Assets' AS StatementSection,
        'Total Assets' AS LineLabel,
        'subtotal' AS LineType,
        400 AS DisplayOrder,
        ROUND(CurrentAssets + NoncurrentAssets, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Current Liabilities' AS StatementSection,
        'Total Current Liabilities' AS LineLabel,
        'subtotal' AS LineType,
        590 AS DisplayOrder,
        ROUND(CurrentLiabilities, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Long-Term Liabilities' AS StatementSection,
        'Total Long-Term Liabilities' AS LineLabel,
        'subtotal' AS LineType,
        790 AS DisplayOrder,
        ROUND(LongTermLiabilities, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Total Liabilities' AS StatementSection,
        'Total Liabilities' AS LineLabel,
        'subtotal' AS LineType,
        800 AS DisplayOrder,
        ROUND(CurrentLiabilities + LongTermLiabilities, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Equity' AS StatementSection,
        'Total Equity' AS LineLabel,
        'subtotal' AS LineType,
        990 AS DisplayOrder,
        ROUND(EquityAmount, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Total Liabilities and Equity' AS StatementSection,
        'Total Liabilities and Equity' AS LineLabel,
        'subtotal' AS LineType,
        1000 AS DisplayOrder,
        ROUND(CurrentLiabilities + LongTermLiabilities + EquityAmount, 2) AS Amount
    FROM section_summary
)
SELECT
    FiscalYear,
    FiscalPeriod,
    StatementSection,
    LineLabel,
    LineType,
    DisplayOrder,
    Amount
FROM (
    SELECT
        FiscalYear,
        FiscalPeriod,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder,
        Amount
    FROM statement_accounts

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder,
        Amount
    FROM subtotal_lines
)
ORDER BY
    FiscalYear,
    FiscalPeriod,
    DisplayOrder,
    LineLabel;
