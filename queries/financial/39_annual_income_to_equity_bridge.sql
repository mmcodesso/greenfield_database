-- Teaching objective: Reconcile annual net income to the retained-earnings close and year-end balance-sheet residuals.
-- Main tables: GLEntry, Account, JournalEntry.
-- Expected output shape: One row per closed fiscal year with income-statement, close-process, retained-earnings, and balance-sheet bridge columns.
-- Recommended build mode: Either. Start with a clean full-size build for integrity work, then compare the anomaly build.
-- Interpretation notes: Annual income-statement net income should tie to the year-end close posted to account 3030. Current Year Earnings on the annual balance sheet should be zero after a clean close.

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
pre_close_gl_net_income AS (
    SELECT
        gl.FiscalYear,
        ROUND(SUM(gl.Credit - gl.Debit), 2) AS PreCloseGlNetIncome
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
    GROUP BY gl.FiscalYear
),
income_statement_scope AS (
    SELECT
        gl.FiscalYear,
        CASE
            WHEN a.AccountType = 'Revenue' THEN gl.Credit - gl.Debit
            WHEN a.AccountType = 'Expense' THEN -(gl.Debit - gl.Credit)
            ELSE 0
        END AS SignedAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE gl.FiscalYear IN (SELECT FiscalYear FROM closed_years)
      AND a.AccountSubType <> 'Header'
      AND COALESCE(je.EntryType, '') NOT IN (
            'Year-End Close - P&L to Income Summary',
            'Year-End Close - Income Summary to Retained Earnings'
      )
      AND (
            (
                a.AccountType = 'Revenue'
                AND a.AccountSubType = 'Operating Revenue'
            )
            OR (
                a.AccountType = 'Revenue'
                AND a.AccountSubType = 'Contra Revenue'
            )
            OR (
                a.AccountType = 'Expense'
                AND a.AccountSubType = 'COGS'
                AND CAST(a.AccountNumber AS INTEGER) BETWEEN 5000 AND 5999
            )
            OR (
                a.AccountType = 'Expense'
                AND a.AccountSubType = 'Operating Expense'
                AND CAST(a.AccountNumber AS INTEGER) BETWEEN 6000 AND 6999
            )
            OR (
                CAST(a.AccountNumber AS INTEGER) BETWEEN 7000 AND 7999
                AND a.AccountSubType IN ('Other Income', 'Other Income or Expense', 'Other Expense')
            )
      )
),
income_statement_net_income AS (
    SELECT
        FiscalYear,
        ROUND(SUM(SignedAmount), 2) AS IncomeStatementNetIncome
    FROM income_statement_scope
    GROUP BY FiscalYear
),
retained_earnings_close AS (
    SELECT
        gl.FiscalYear,
        ROUND(SUM(gl.Credit - gl.Debit), 2) AS RetainedEarningsCloseAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE gl.FiscalYear IN (SELECT FiscalYear FROM closed_years)
      AND a.AccountNumber = '3030'
      AND je.EntryType = 'Year-End Close - Income Summary to Retained Earnings'
    GROUP BY gl.FiscalYear
),
balance_sheet_account_layout AS (
    SELECT
        CAST(AccountNumber AS INTEGER) AS AccountNumber,
        AccountName AS LineLabel,
        AccountType,
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
        END AS StatementSection
    FROM Account
    WHERE AccountSubType <> 'Header'
      AND CAST(AccountNumber AS INTEGER) <> 3050
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
      AND CAST(a.AccountNumber AS INTEGER) IN (
            SELECT AccountNumber
            FROM balance_sheet_account_layout
            WHERE StatementSection IS NOT NULL
      )
    GROUP BY
        gl.FiscalYear,
        gl.FiscalPeriod,
        CAST(a.AccountNumber AS INTEGER)
),
running_account_balances AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        bsal.AccountNumber,
        bsal.LineLabel,
        bsal.StatementSection,
        ROUND(
            SUM(COALESCE(bspa.PeriodAmount, 0)) OVER (
                PARTITION BY bsal.AccountNumber
                ORDER BY rp.PeriodIndex
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            2
        ) AS Amount
    FROM reporting_periods AS rp
    CROSS JOIN (
        SELECT
            AccountNumber,
            LineLabel,
            StatementSection
        FROM balance_sheet_account_layout
        WHERE StatementSection IS NOT NULL
    ) AS bsal
    LEFT JOIN balance_sheet_period_activity AS bspa
        ON bspa.FiscalYear = rp.FiscalYear
       AND bspa.FiscalPeriod = rp.FiscalPeriod
       AND bspa.AccountNumber = bsal.AccountNumber
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
        ) AS BalanceSheetCurrentYearEarningsResidual
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
        Amount
    FROM running_account_balances

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Equity' AS StatementSection,
        BalanceSheetCurrentYearEarningsResidual AS Amount
    FROM derived_current_year_earnings
),
section_summary AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        ROUND(SUM(CASE WHEN StatementSection = 'Current Assets' THEN Amount ELSE 0 END), 2) AS TotalCurrentAssets,
        ROUND(SUM(CASE WHEN StatementSection = 'Noncurrent Assets' THEN Amount ELSE 0 END), 2) AS TotalNoncurrentAssets,
        ROUND(SUM(CASE WHEN StatementSection = 'Current Liabilities' THEN Amount ELSE 0 END), 2) AS TotalCurrentLiabilities,
        ROUND(SUM(CASE WHEN StatementSection = 'Long-Term Liabilities' THEN Amount ELSE 0 END), 2) AS TotalLongTermLiabilities,
        ROUND(SUM(CASE WHEN StatementSection = 'Equity' THEN Amount ELSE 0 END), 2) AS TotalEquity
    FROM statement_accounts
    GROUP BY FiscalYear, FiscalPeriod
),
year_end_balance_sheet AS (
    SELECT
        FiscalYear,
        ROUND(TotalCurrentAssets + TotalNoncurrentAssets, 2) AS TotalAssets,
        ROUND(TotalCurrentLiabilities + TotalLongTermLiabilities, 2) AS TotalLiabilities,
        ROUND(TotalEquity, 2) AS TotalEquity,
        ROUND(TotalCurrentLiabilities + TotalLongTermLiabilities + TotalEquity, 2) AS TotalLiabilitiesAndEquity
    FROM section_summary
    WHERE FiscalPeriod = 12
),
year_end_retained_earnings AS (
    SELECT
        FiscalYear,
        ROUND(Amount, 2) AS EndingRetainedEarnings
    FROM running_account_balances
    WHERE FiscalPeriod = 12
      AND AccountNumber = 3030
),
retained_earnings_rollforward AS (
    SELECT
        FiscalYear,
        EndingRetainedEarnings,
        LAG(EndingRetainedEarnings) OVER (ORDER BY FiscalYear) AS PriorYearEndingRetainedEarnings
    FROM year_end_retained_earnings
),
year_end_current_year_earnings AS (
    SELECT
        FiscalYear,
        ROUND(BalanceSheetCurrentYearEarningsResidual, 2) AS BalanceSheetCurrentYearEarningsResidual
    FROM derived_current_year_earnings
    WHERE FiscalPeriod = 12
)
SELECT
    cy.FiscalYear,
    ROUND(COALESCE(isni.IncomeStatementNetIncome, 0), 2) AS IncomeStatementNetIncome,
    ROUND(COALESCE(pg.PreCloseGlNetIncome, 0), 2) AS PreCloseGlNetIncome,
    ROUND(COALESCE(reclose.RetainedEarningsCloseAmount, 0), 2) AS RetainedEarningsCloseAmount,
    ROUND(COALESCE(rerf.EndingRetainedEarnings, 0), 2) AS EndingRetainedEarnings,
    ROUND(rerf.PriorYearEndingRetainedEarnings, 2) AS PriorYearEndingRetainedEarnings,
    ROUND(
        CASE
            WHEN rerf.PriorYearEndingRetainedEarnings IS NULL THEN NULL
            ELSE rerf.EndingRetainedEarnings - rerf.PriorYearEndingRetainedEarnings
        END,
        2
    ) AS RetainedEarningsMovement,
    ROUND(COALESCE(yecye.BalanceSheetCurrentYearEarningsResidual, 0), 2) AS BalanceSheetCurrentYearEarningsResidual,
    ROUND(COALESCE(yebs.TotalAssets, 0), 2) AS TotalAssets,
    ROUND(COALESCE(yebs.TotalLiabilities, 0), 2) AS TotalLiabilities,
    ROUND(COALESCE(yebs.TotalEquity, 0), 2) AS TotalEquity,
    ROUND(COALESCE(yebs.TotalLiabilitiesAndEquity, 0), 2) AS TotalLiabilitiesAndEquity,
    ROUND(COALESCE(isni.IncomeStatementNetIncome, 0) - COALESCE(pg.PreCloseGlNetIncome, 0), 2) AS StatementNetIncomeLessPreCloseGlVariance,
    ROUND(COALESCE(isni.IncomeStatementNetIncome, 0) - COALESCE(reclose.RetainedEarningsCloseAmount, 0), 2) AS StatementNetIncomeLessRetainedEarningsCloseVariance,
    ROUND(COALESCE(pg.PreCloseGlNetIncome, 0) - COALESCE(reclose.RetainedEarningsCloseAmount, 0), 2) AS PreCloseGlNetIncomeLessRetainedEarningsCloseVariance,
    ROUND(
        CASE
            WHEN rerf.PriorYearEndingRetainedEarnings IS NULL THEN NULL
            ELSE (rerf.EndingRetainedEarnings - rerf.PriorYearEndingRetainedEarnings)
                 - COALESCE(reclose.RetainedEarningsCloseAmount, 0)
        END,
        2
    ) AS RetainedEarningsMovementLessRetainedEarningsCloseVariance,
    ROUND(COALESCE(yebs.TotalAssets, 0) - COALESCE(yebs.TotalLiabilitiesAndEquity, 0), 2) AS BalanceSheetOutOfBalance
FROM closed_years AS cy
LEFT JOIN income_statement_net_income AS isni
    ON isni.FiscalYear = cy.FiscalYear
LEFT JOIN pre_close_gl_net_income AS pg
    ON pg.FiscalYear = cy.FiscalYear
LEFT JOIN retained_earnings_close AS reclose
    ON reclose.FiscalYear = cy.FiscalYear
LEFT JOIN retained_earnings_rollforward AS rerf
    ON rerf.FiscalYear = cy.FiscalYear
LEFT JOIN year_end_current_year_earnings AS yecye
    ON yecye.FiscalYear = cy.FiscalYear
LEFT JOIN year_end_balance_sheet AS yebs
    ON yebs.FiscalYear = cy.FiscalYear
ORDER BY cy.FiscalYear;
