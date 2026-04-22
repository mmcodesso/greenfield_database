-- Teaching objective: Produce a monthly pro forma classified balance sheet from the driver-based budget roll-forward.
-- Main tables: BudgetLine, Account.
-- Output shape: One row per fiscal month and balance-sheet line.
-- Interpretation notes: BudgetLine stores ending balances for balance-sheet accounts. Current Year Earnings is derived from the pro forma income statement so the balance sheet stays tied without a budget-side close journal.

WITH periods AS (
    SELECT DISTINCT
        FiscalYear,
        Month AS FiscalPeriod
    FROM BudgetLine
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
ending_balance_activity AS (
    SELECT
        bl.FiscalYear,
        bl.Month AS FiscalPeriod,
        CAST(a.AccountNumber AS INTEGER) AS AccountNumber,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Asset' AND a.NormalBalance = 'Debit' THEN bl.BudgetAmount
            WHEN a.AccountType = 'Asset' AND a.NormalBalance = 'Credit' THEN -bl.BudgetAmount
            WHEN a.AccountType IN ('Liability', 'Equity') AND a.NormalBalance = 'Credit' THEN bl.BudgetAmount
            WHEN a.AccountType IN ('Liability', 'Equity') AND a.NormalBalance = 'Debit' THEN -bl.BudgetAmount
            ELSE 0
        END), 2) AS Amount
    FROM BudgetLine AS bl
    JOIN Account AS a
        ON a.AccountID = bl.AccountID
    WHERE bl.BudgetCategory = 'Balance Sheet'
      AND CAST(a.AccountNumber AS INTEGER) <> 3050
    GROUP BY
        bl.FiscalYear,
        bl.Month,
        CAST(a.AccountNumber AS INTEGER)
),
running_account_balances AS (
    SELECT
        p.FiscalYear,
        p.FiscalPeriod,
        al.StatementSection,
        al.LineLabel,
        al.AccountNumber,
        al.LineType,
        al.DisplayOrder,
        ROUND(COALESCE(eba.Amount, 0), 2) AS Amount
    FROM periods AS p
    CROSS JOIN account_lines AS al
    LEFT JOIN ending_balance_activity AS eba
        ON eba.FiscalYear = p.FiscalYear
       AND eba.FiscalPeriod = p.FiscalPeriod
       AND eba.AccountNumber = al.AccountNumber
),
pnl_period_activity AS (
    SELECT
        bl.FiscalYear,
        bl.Month AS FiscalPeriod,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Revenue' AND a.NormalBalance = 'Credit' THEN bl.BudgetAmount
            WHEN a.AccountType = 'Revenue' AND a.NormalBalance = 'Debit' THEN -bl.BudgetAmount
            WHEN a.AccountType = 'Expense' AND a.NormalBalance = 'Debit' THEN -bl.BudgetAmount
            WHEN a.AccountType = 'Expense' AND a.NormalBalance = 'Credit' THEN bl.BudgetAmount
            ELSE 0
        END), 2) AS PeriodAmount
    FROM BudgetLine AS bl
    JOIN Account AS a
        ON a.AccountID = bl.AccountID
    WHERE bl.BudgetCategory IN ('Revenue', 'COGS', 'Operating Expense')
      AND a.AccountType IN ('Revenue', 'Expense')
      AND a.AccountSubType <> 'Header'
    GROUP BY bl.FiscalYear, bl.Month
),
derived_current_year_earnings AS (
    SELECT
        p.FiscalYear,
        p.FiscalPeriod,
        'Equity' AS StatementSection,
        'Current Year Earnings' AS LineLabel,
        3050 AS AccountNumber,
        'account' AS LineType,
        980 AS DisplayOrder,
        ROUND(
            SUM(COALESCE(pnl.PeriodAmount, 0)) OVER (
                PARTITION BY p.FiscalYear
                ORDER BY p.FiscalPeriod
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            2
        ) AS Amount
    FROM periods AS p
    LEFT JOIN pnl_period_activity AS pnl
        ON pnl.FiscalYear = p.FiscalYear
       AND pnl.FiscalPeriod = p.FiscalPeriod
),
statement_accounts AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        StatementSection,
        LineLabel,
        AccountNumber,
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
        AccountNumber,
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
    SELECT FiscalYear, FiscalPeriod, 'Current Assets' AS StatementSection, 'Total Current Assets' AS LineLabel, NULL AS AccountNumber, 'subtotal' AS LineType, 190 AS DisplayOrder, ROUND(CurrentAssets, 2) AS Amount
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Noncurrent Assets', 'Total Noncurrent Assets', NULL, 'subtotal', 390, ROUND(NoncurrentAssets, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Total Assets', 'Total Assets', NULL, 'subtotal', 400, ROUND(CurrentAssets + NoncurrentAssets, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Current Liabilities', 'Total Current Liabilities', NULL, 'subtotal', 590, ROUND(CurrentLiabilities, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Long-Term Liabilities', 'Total Long-Term Liabilities', NULL, 'subtotal', 790, ROUND(LongTermLiabilities, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Total Liabilities', 'Total Liabilities', NULL, 'subtotal', 800, ROUND(CurrentLiabilities + LongTermLiabilities, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Equity', 'Total Equity', NULL, 'subtotal', 990, ROUND(EquityAmount, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Total Liabilities and Equity', 'Total Liabilities and Equity', NULL, 'subtotal', 1000, ROUND(CurrentLiabilities + LongTermLiabilities + EquityAmount, 2)
    FROM section_summary
)
SELECT
    FiscalYear,
    FiscalPeriod,
    StatementSection,
    LineLabel,
    AccountNumber,
    LineType,
    DisplayOrder,
    Amount
FROM (
    SELECT
        FiscalYear,
        FiscalPeriod,
        StatementSection,
        LineLabel,
        AccountNumber,
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
        AccountNumber,
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
