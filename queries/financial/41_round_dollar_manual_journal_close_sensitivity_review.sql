-- Teaching objective: Highlight rounded manual journals that are likely to affect annual close and statement reconciliation.
-- Main tables: JournalEntry, GLEntry, Account.
-- Expected output shape: One row per close-sensitive manual journal with whole-dollar and two-line diagnostics.
-- Recommended build mode: Either. Compare clean and anomaly builds to identify seeded close-sensitive journals.
-- Interpretation notes: Rounded two-line manual journals near year-end are strong candidates when residual P&L balances appear after close. Utilities is included because the seeded anomaly profile can round that manual journal and leave a year-end P&L residue.

WITH candidate_lines AS (
    SELECT
        gl.FiscalYear,
        je.PostingDate,
        gl.FiscalPeriod,
        je.JournalEntryID,
        je.EntryNumber,
        je.EntryType,
        je.Description,
        a.AccountNumber,
        a.AccountName,
        ROUND(gl.Debit, 2) AS Debit,
        ROUND(gl.Credit, 2) AS Credit
    FROM JournalEntry AS je
    JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'JournalEntry'
       AND gl.SourceDocumentID = je.JournalEntryID
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE je.EntryType IN (
        'Utilities',
        'Factory Overhead',
        'Year-End Close - P&L to Income Summary',
        'Year-End Close - Income Summary to Retained Earnings'
    )
),
journal_rollup AS (
    SELECT
        FiscalYear,
        date(PostingDate) AS PostingDate,
        FiscalPeriod,
        JournalEntryID,
        EntryNumber,
        EntryType,
        Description,
        COUNT(*) AS GLRowCount,
        ROUND(SUM(Debit), 2) AS TotalDebit,
        ROUND(SUM(Credit), 2) AS TotalCredit,
        ROUND(SUM(Debit), 2) AS JournalTotalAmount,
        ROUND(ABS(ROUND(SUM(Debit), 2) - ROUND(ROUND(SUM(Debit), 2), 0)), 4) AS DistanceFromWholeDollar,
        CASE
            WHEN ABS(ROUND(SUM(Debit), 2) - ROUND(ROUND(SUM(Debit), 2), 0)) < 0.0001 THEN 1
            ELSE 0
        END AS WholeDollarJournalFlag,
        CASE
            WHEN COUNT(*) = 2 THEN 1
            ELSE 0
        END AS TwoLineJournalFlag,
        GROUP_CONCAT(
            CASE
                WHEN Debit > 0 THEN AccountNumber || ' ' || AccountName || ' = ' || printf('%.2f', Debit)
                ELSE NULL
            END,
            '; '
        ) AS DebitAccountSummary,
        GROUP_CONCAT(
            CASE
                WHEN Credit > 0 THEN AccountNumber || ' ' || AccountName || ' = ' || printf('%.2f', Credit)
                ELSE NULL
            END,
            '; '
        ) AS CreditAccountSummary
    FROM candidate_lines
    GROUP BY
        FiscalYear,
        date(PostingDate),
        FiscalPeriod,
        JournalEntryID,
        EntryNumber,
        EntryType,
        Description
)
SELECT
    FiscalYear,
    PostingDate,
    FiscalPeriod,
    JournalEntryID,
    EntryNumber,
    EntryType,
    Description,
    GLRowCount,
    TotalDebit,
    TotalCredit,
    JournalTotalAmount,
    DistanceFromWholeDollar,
    WholeDollarJournalFlag,
    TwoLineJournalFlag,
    CASE
        WHEN WholeDollarJournalFlag = 1 AND TwoLineJournalFlag = 1 THEN 1
        ELSE 0
    END AS WholeDollarTwoLineFlag,
    DebitAccountSummary,
    CreditAccountSummary
FROM journal_rollup
ORDER BY FiscalYear, PostingDate, EntryNumber;
