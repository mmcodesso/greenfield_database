-- Teaching objective: Produce a monthly pro forma income statement from driver-based budget detail.
-- Main tables: BudgetLine, Account.
-- Output shape: One row per fiscal month and income-statement line.
-- Interpretation notes: BudgetLine stores positive planned amounts. Contra accounts are signed from their normal balance so subtotals behave like the posted income statement.

WITH periods AS (
    SELECT DISTINCT
        FiscalYear,
        Month AS FiscalPeriod
    FROM BudgetLine
),
budget_activity AS (
    SELECT
        bl.FiscalYear,
        bl.Month AS FiscalPeriod,
        CAST(a.AccountNumber AS INTEGER) AS AccountNumber,
        a.AccountName,
        a.AccountType,
        a.AccountSubType,
        CASE
            WHEN a.AccountType = 'Revenue' AND a.NormalBalance = 'Credit'
                THEN bl.BudgetAmount
            WHEN a.AccountType = 'Revenue' AND a.NormalBalance = 'Debit'
                THEN -bl.BudgetAmount
            WHEN a.AccountType = 'Expense' AND a.NormalBalance = 'Debit'
                THEN bl.BudgetAmount
            WHEN a.AccountType = 'Expense' AND a.NormalBalance = 'Credit'
                THEN -bl.BudgetAmount
            ELSE 0
        END AS SignedAmount
    FROM BudgetLine AS bl
    JOIN Account AS a
        ON a.AccountID = bl.AccountID
    WHERE bl.BudgetCategory IN ('Revenue', 'COGS', 'Operating Expense')
      AND a.AccountType IN ('Revenue', 'Expense')
      AND a.AccountSubType <> 'Header'
),
account_layout AS (
    SELECT
        CAST(AccountNumber AS INTEGER) AS AccountNumber,
        AccountName AS LineLabel,
        AccountType,
        CASE
            WHEN AccountType = 'Revenue'
             AND AccountSubType = 'Operating Revenue'
             AND CAST(AccountNumber AS INTEGER) BETWEEN 4000 AND 4059
                THEN 'Operating Revenue'
            WHEN AccountType = 'Revenue'
             AND AccountSubType = 'Contra Revenue'
             AND CAST(AccountNumber AS INTEGER) BETWEEN 4060 AND 4099
                THEN 'Contra Revenue'
            WHEN AccountType = 'Expense'
             AND AccountSubType = 'COGS'
             AND CAST(AccountNumber AS INTEGER) BETWEEN 5000 AND 5999
                THEN 'Cost of Goods Sold'
            WHEN AccountType = 'Expense'
             AND AccountSubType = 'Operating Expense'
             AND CAST(AccountNumber AS INTEGER) BETWEEN 6000 AND 6999
                THEN 'Operating Expenses'
            WHEN CAST(AccountNumber AS INTEGER) BETWEEN 7000 AND 7999
             AND AccountSubType IN ('Other Income', 'Other Income or Expense', 'Other Expense')
                THEN 'Other Income and Expense'
            ELSE NULL
        END AS StatementSection,
        CASE
            WHEN AccountType = 'Revenue'
             AND AccountSubType = 'Operating Revenue'
             AND CAST(AccountNumber AS INTEGER) BETWEEN 4000 AND 4059
                THEN 100
            WHEN AccountType = 'Revenue'
             AND AccountSubType = 'Contra Revenue'
             AND CAST(AccountNumber AS INTEGER) BETWEEN 4060 AND 4099
                THEN 200
            WHEN AccountType = 'Expense'
             AND AccountSubType = 'COGS'
             AND CAST(AccountNumber AS INTEGER) BETWEEN 5000 AND 5999
                THEN 400
            WHEN AccountType = 'Expense'
             AND AccountSubType = 'Operating Expense'
             AND CAST(AccountNumber AS INTEGER) BETWEEN 6000 AND 6999
                THEN 600
            WHEN CAST(AccountNumber AS INTEGER) BETWEEN 7000 AND 7999
             AND AccountSubType IN ('Other Income', 'Other Income or Expense', 'Other Expense')
                THEN 800
            ELSE NULL
        END AS SectionBaseOrder
    FROM Account
    WHERE AccountType IN ('Revenue', 'Expense')
      AND IsActive = 1
      AND AccountSubType <> 'Header'
),
account_lines AS (
    SELECT
        StatementSection,
        LineLabel,
        'account' AS LineType,
        SectionBaseOrder
            + ROW_NUMBER() OVER (
                PARTITION BY StatementSection
                ORDER BY AccountNumber, LineLabel
            ) AS DisplayOrder,
        AccountNumber,
        AccountType
    FROM account_layout
    WHERE StatementSection IS NOT NULL
),
account_activity AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        AccountNumber,
        ROUND(SUM(SignedAmount), 2) AS Amount
    FROM budget_activity
    GROUP BY
        FiscalYear,
        FiscalPeriod,
        AccountNumber
),
statement_accounts AS (
    SELECT
        p.FiscalYear,
        p.FiscalPeriod,
        al.StatementSection,
        al.LineLabel,
        al.AccountNumber,
        al.LineType,
        al.DisplayOrder,
        al.AccountType,
        ROUND(COALESCE(aa.Amount, 0), 2) AS Amount
    FROM periods AS p
    CROSS JOIN account_lines AS al
    LEFT JOIN account_activity AS aa
        ON aa.FiscalYear = p.FiscalYear
       AND aa.FiscalPeriod = p.FiscalPeriod
       AND aa.AccountNumber = al.AccountNumber
),
section_summary AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        ROUND(SUM(CASE WHEN StatementSection = 'Operating Revenue' THEN Amount ELSE 0 END), 2) AS OperatingRevenue,
        ROUND(SUM(CASE WHEN StatementSection = 'Contra Revenue' THEN Amount ELSE 0 END), 2) AS ContraRevenue,
        ROUND(SUM(CASE WHEN StatementSection = 'Cost of Goods Sold' THEN Amount ELSE 0 END), 2) AS CostOfGoodsSold,
        ROUND(SUM(CASE WHEN StatementSection = 'Operating Expenses' THEN Amount ELSE 0 END), 2) AS OperatingExpenses,
        ROUND(SUM(CASE
            WHEN StatementSection = 'Other Income and Expense'
             AND AccountType = 'Revenue'
                THEN Amount
            ELSE 0
        END), 2) AS OtherIncome,
        ROUND(SUM(CASE
            WHEN StatementSection = 'Other Income and Expense'
             AND AccountType = 'Expense'
                THEN Amount
            ELSE 0
        END), 2) AS OtherExpense
    FROM statement_accounts
    GROUP BY
        FiscalYear,
        FiscalPeriod
),
subtotal_lines AS (
    SELECT FiscalYear, FiscalPeriod, 'Operating Revenue' AS StatementSection, 'Operating Revenue' AS LineLabel, NULL AS AccountNumber, 'subtotal' AS LineType, 190 AS DisplayOrder, ROUND(OperatingRevenue, 2) AS Amount
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Contra Revenue', 'Contra Revenue', NULL, 'subtotal', 290, ROUND(ContraRevenue, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Net Revenue', 'Net Revenue', NULL, 'subtotal', 300, ROUND(OperatingRevenue + ContraRevenue, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Cost of Goods Sold', 'Cost of Goods Sold', NULL, 'subtotal', 490, ROUND(CostOfGoodsSold, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Gross Profit', 'Gross Profit', NULL, 'subtotal', 500, ROUND((OperatingRevenue + ContraRevenue) - CostOfGoodsSold, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Operating Expenses', 'Operating Expenses', NULL, 'subtotal', 690, ROUND(OperatingExpenses, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Operating Income', 'Operating Income', NULL, 'subtotal', 700, ROUND(((OperatingRevenue + ContraRevenue) - CostOfGoodsSold) - OperatingExpenses, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Other Income and Expense', 'Other Income and Expense', NULL, 'subtotal', 890, ROUND(OtherIncome - OtherExpense, 2)
    FROM section_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Net Income', 'Net Income', NULL, 'subtotal', 900, ROUND((((OperatingRevenue + ContraRevenue) - CostOfGoodsSold) - OperatingExpenses) + (OtherIncome - OtherExpense), 2)
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
