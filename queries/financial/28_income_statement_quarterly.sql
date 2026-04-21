-- Teaching objective: Produce a detailed quarterly income statement from posted general-ledger activity.
-- Main tables: GLEntry, Account, JournalEntry.
-- Output shape: One row per fiscal quarter and income-statement line.
-- Interpretation notes: Account rows use revenue as credit minus debit and expense as debit minus credit. Subtotal rows apply income-statement formulas and exclude year-end close journals.

WITH filtered_gl AS (
    SELECT
        gl.FiscalYear,
        CAST((gl.FiscalPeriod - 1) / 3 AS INTEGER) + 1 AS FiscalQuarter,
        CAST(a.AccountNumber AS INTEGER) AS AccountNumber,
        a.AccountName,
        a.AccountType,
        a.AccountSubType,
        CASE
            WHEN a.AccountType = 'Revenue' THEN gl.Credit - gl.Debit
            WHEN a.AccountType = 'Expense' THEN gl.Debit - gl.Credit
            ELSE 0
        END AS SignedAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountType IN ('Revenue', 'Expense')
      AND a.IsActive = 1
      AND a.AccountSubType <> 'Header'
      AND COALESCE(je.EntryType, '') NOT IN (
            'Year-End Close - P&L to Income Summary',
            'Year-End Close - Income Summary to Retained Earnings'
      )
),
periods AS (
    SELECT DISTINCT
        FiscalYear,
        FiscalQuarter
    FROM filtered_gl
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
        FiscalQuarter,
        AccountNumber,
        ROUND(SUM(SignedAmount), 2) AS Amount
    FROM filtered_gl
    GROUP BY
        FiscalYear,
        FiscalQuarter,
        AccountNumber
),
statement_accounts AS (
    SELECT
        p.FiscalYear,
        p.FiscalQuarter,
        al.StatementSection,
        al.LineLabel,
        al.LineType,
        al.DisplayOrder,
        al.AccountType,
        ROUND(COALESCE(aa.Amount, 0), 2) AS Amount
    FROM periods AS p
    CROSS JOIN account_lines AS al
    LEFT JOIN account_activity AS aa
        ON aa.FiscalYear = p.FiscalYear
       AND aa.FiscalQuarter = p.FiscalQuarter
       AND aa.AccountNumber = al.AccountNumber
),
section_summary AS (
    SELECT
        FiscalYear,
        FiscalQuarter,
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
        FiscalQuarter
),
subtotal_lines AS (
    SELECT
        FiscalYear,
        FiscalQuarter,
        'Operating Revenue' AS StatementSection,
        'Operating Revenue' AS LineLabel,
        'subtotal' AS LineType,
        190 AS DisplayOrder,
        ROUND(OperatingRevenue, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalQuarter,
        'Contra Revenue' AS StatementSection,
        'Contra Revenue' AS LineLabel,
        'subtotal' AS LineType,
        290 AS DisplayOrder,
        ROUND(ContraRevenue, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalQuarter,
        'Net Revenue' AS StatementSection,
        'Net Revenue' AS LineLabel,
        'subtotal' AS LineType,
        300 AS DisplayOrder,
        ROUND(OperatingRevenue + ContraRevenue, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalQuarter,
        'Cost of Goods Sold' AS StatementSection,
        'Cost of Goods Sold' AS LineLabel,
        'subtotal' AS LineType,
        490 AS DisplayOrder,
        ROUND(CostOfGoodsSold, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalQuarter,
        'Gross Profit' AS StatementSection,
        'Gross Profit' AS LineLabel,
        'subtotal' AS LineType,
        500 AS DisplayOrder,
        ROUND((OperatingRevenue + ContraRevenue) - CostOfGoodsSold, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalQuarter,
        'Operating Expenses' AS StatementSection,
        'Operating Expenses' AS LineLabel,
        'subtotal' AS LineType,
        690 AS DisplayOrder,
        ROUND(OperatingExpenses, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalQuarter,
        'Operating Income' AS StatementSection,
        'Operating Income' AS LineLabel,
        'subtotal' AS LineType,
        700 AS DisplayOrder,
        ROUND(((OperatingRevenue + ContraRevenue) - CostOfGoodsSold) - OperatingExpenses, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalQuarter,
        'Other Income and Expense' AS StatementSection,
        'Other Income and Expense' AS LineLabel,
        'subtotal' AS LineType,
        890 AS DisplayOrder,
        ROUND(OtherIncome - OtherExpense, 2) AS Amount
    FROM section_summary

    UNION ALL

    SELECT
        FiscalYear,
        FiscalQuarter,
        'Net Income' AS StatementSection,
        'Net Income' AS LineLabel,
        'subtotal' AS LineType,
        900 AS DisplayOrder,
        ROUND(
            (((OperatingRevenue + ContraRevenue) - CostOfGoodsSold) - OperatingExpenses)
            + (OtherIncome - OtherExpense),
            2
        ) AS Amount
    FROM section_summary
)
SELECT
    FiscalYear,
    FiscalQuarter,
    StatementSection,
    LineLabel,
    LineType,
    DisplayOrder,
    Amount
FROM (
    SELECT
        FiscalYear,
        FiscalQuarter,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder,
        Amount
    FROM statement_accounts

    UNION ALL

    SELECT
        FiscalYear,
        FiscalQuarter,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder,
        Amount
    FROM subtotal_lines
)
ORDER BY
    FiscalYear,
    FiscalQuarter,
    DisplayOrder,
    LineLabel;
