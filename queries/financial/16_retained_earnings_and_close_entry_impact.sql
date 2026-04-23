-- Teaching objective: Separate raw P&L activity from year-end close impact on retained earnings.
-- Main tables: GLEntry, Account, JournalEntry.
-- Expected output shape: One row per fiscal year with pre-close net income, statement net income, close-step amounts, and retained-earnings impact.
-- Recommended build mode: Either.
-- Interpretation notes: Pre-close GL activity should tie to the annual income statement and to the retained-earnings close when the close process is clean.

WITH years AS (
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
pre_close_gl AS (
    SELECT
        gl.FiscalYear,
        ROUND(SUM(gl.Credit - gl.Debit), 2) AS PreCloseNetIncome
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountType IN ('Revenue', 'Expense')
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
    WHERE a.AccountSubType <> 'Header'
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
close_step_pnl_to_income_summary AS (
    SELECT
        gl.FiscalYear,
        ROUND(SUM(gl.Credit - gl.Debit), 2) AS CloseStepPnLToIncomeSummary
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountNumber = '8010'
      AND je.EntryType = 'Year-End Close - P&L to Income Summary'
    GROUP BY gl.FiscalYear
),
close_step_income_summary_to_retained_earnings AS (
    SELECT
        gl.FiscalYear,
        ROUND(SUM(gl.Debit - gl.Credit), 2) AS CloseStepIncomeSummaryToRetainedEarnings
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountNumber = '8010'
      AND je.EntryType = 'Year-End Close - Income Summary to Retained Earnings'
    GROUP BY gl.FiscalYear
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
    WHERE a.AccountNumber = '3030'
      AND je.EntryType = 'Year-End Close - Income Summary to Retained Earnings'
    GROUP BY gl.FiscalYear
)
SELECT
    y.FiscalYear,
    ROUND(COALESCE(pg.PreCloseNetIncome, 0), 2) AS PreCloseNetIncome,
    ROUND(COALESCE(isni.IncomeStatementNetIncome, 0), 2) AS IncomeStatementNetIncome,
    ROUND(COALESCE(step1.CloseStepPnLToIncomeSummary, 0), 2) AS CloseStepPnLToIncomeSummary,
    ROUND(COALESCE(step2.CloseStepIncomeSummaryToRetainedEarnings, 0), 2) AS CloseStepIncomeSummaryToRetainedEarnings,
    ROUND(COALESCE(re.RetainedEarningsCloseAmount, 0), 2) AS RetainedEarningsCloseAmount,
    ROUND(COALESCE(isni.IncomeStatementNetIncome, 0) - COALESCE(pg.PreCloseNetIncome, 0), 2) AS StatementToPreCloseVariance,
    ROUND(COALESCE(isni.IncomeStatementNetIncome, 0) - COALESCE(re.RetainedEarningsCloseAmount, 0), 2) AS StatementToRetainedEarningsCloseVariance
FROM years AS y
LEFT JOIN pre_close_gl AS pg
    ON pg.FiscalYear = y.FiscalYear
LEFT JOIN income_statement_net_income AS isni
    ON isni.FiscalYear = y.FiscalYear
LEFT JOIN close_step_pnl_to_income_summary AS step1
    ON step1.FiscalYear = y.FiscalYear
LEFT JOIN close_step_income_summary_to_retained_earnings AS step2
    ON step2.FiscalYear = y.FiscalYear
LEFT JOIN retained_earnings_close AS re
    ON re.FiscalYear = y.FiscalYear
ORDER BY y.FiscalYear;
