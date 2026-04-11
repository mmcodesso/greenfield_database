-- Teaching objective: Separate raw P&L activity from year-end close impact on retained earnings.
-- Main tables: GLEntry, Account, JournalEntry.
-- Expected output shape: One row per fiscal year with pre-close P&L, close-step amounts, and retained-earnings impact.
-- Recommended build mode: Either.
-- Interpretation notes: Excluding close entries is essential when students want raw multi-year income-statement activity.

WITH raw_pnl AS (
    SELECT
        gl.FiscalYear,
        ROUND(SUM(
            CASE
                WHEN a.AccountType = 'Revenue' THEN gl.Credit - gl.Debit
                WHEN a.AccountType = 'Expense' THEN gl.Debit - gl.Credit
                ELSE 0
            END
        ), 2) AS PreCloseNetIncome
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountType IN ('Revenue', 'Expense')
      AND COALESCE(je.EntryType, '') NOT IN (
            'Year-End Close - P&L to Income Summary',
            'Year-End Close - Income Summary to Retained Earnings'
      )
    GROUP BY gl.FiscalYear
),
close_steps AS (
    SELECT
        gl.FiscalYear,
        je.EntryType,
        ROUND(SUM(gl.Credit - gl.Debit), 2) AS NetCreditAmount
    FROM GLEntry AS gl
    JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE je.EntryType IN (
        'Year-End Close - P&L to Income Summary',
        'Year-End Close - Income Summary to Retained Earnings'
    )
    GROUP BY gl.FiscalYear, je.EntryType
),
retained_earnings AS (
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
    years.FiscalYear,
    ROUND(COALESCE(rp.PreCloseNetIncome, 0), 2) AS PreCloseNetIncome,
    ROUND(COALESCE(step1.NetCreditAmount, 0), 2) AS CloseStepPnLToIncomeSummary,
    ROUND(COALESCE(step2.NetCreditAmount, 0), 2) AS CloseStepIncomeSummaryToRetainedEarnings,
    ROUND(COALESCE(re.RetainedEarningsCloseAmount, 0), 2) AS RetainedEarningsCloseAmount
FROM (
    SELECT DISTINCT FiscalYear
    FROM GLEntry
) AS years
LEFT JOIN raw_pnl AS rp
    ON rp.FiscalYear = years.FiscalYear
LEFT JOIN close_steps AS step1
    ON step1.FiscalYear = years.FiscalYear
   AND step1.EntryType = 'Year-End Close - P&L to Income Summary'
LEFT JOIN close_steps AS step2
    ON step2.FiscalYear = years.FiscalYear
   AND step2.EntryType = 'Year-End Close - Income Summary to Retained Earnings'
LEFT JOIN retained_earnings AS re
    ON re.FiscalYear = years.FiscalYear
ORDER BY years.FiscalYear;
