-- Teaching objective: Compare monthly pro forma statement lines to posted actual statement lines across performance, position, and cash.
-- Main tables: BudgetLine, GLEntry, Account, JournalEntry.
-- Output shape: One row per fiscal month and bridged statement line.
-- Interpretation notes: Actual values appear only for generated posting months. Forward-budget months remain in the output with zero actuals so the bridge can show where the planning horizon extends beyond recorded activity.

WITH reporting_periods AS (
    SELECT DISTINCT
        FiscalYear,
        Month AS FiscalPeriod
    FROM BudgetLine
),
opening_balance_seed AS (
    SELECT
        CAST(substr(je.PostingDate, 1, 4) AS INTEGER) AS FiscalYear,
        CAST(a.AccountNumber AS INTEGER) AS AccountNumber,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Asset' THEN gl.Debit - gl.Credit
            WHEN a.AccountType IN ('Liability', 'Equity') THEN gl.Credit - gl.Debit
            ELSE 0
        END), 2) AS OpeningBalance
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE je.EntryType = 'Opening'
    GROUP BY
        CAST(substr(je.PostingDate, 1, 4) AS INTEGER),
        CAST(a.AccountNumber AS INTEGER)
),
actual_pnl AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Revenue'
             AND a.AccountSubType = 'Operating Revenue'
                THEN gl.Credit - gl.Debit
            WHEN a.AccountType = 'Revenue'
             AND a.AccountSubType = 'Contra Revenue'
                THEN gl.Credit - gl.Debit
            ELSE 0
        END), 2) AS NetRevenue,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Expense'
             AND a.AccountSubType = 'COGS'
                THEN gl.Debit - gl.Credit
            ELSE 0
        END), 2) AS CostOfGoodsSold,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Expense'
             AND a.AccountSubType = 'Operating Expense'
                THEN gl.Debit - gl.Credit
            ELSE 0
        END), 2) AS OperatingExpenses,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Revenue'
             AND a.AccountSubType IN ('Operating Revenue', 'Contra Revenue', 'Other Income', 'Other Income or Expense')
                THEN gl.Credit - gl.Debit
            WHEN a.AccountType = 'Expense'
             AND a.AccountSubType IN ('COGS', 'Operating Expense', 'Other Expense')
                THEN -(gl.Debit - gl.Credit)
            ELSE 0
        END), 2) AS NetIncome
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
    GROUP BY gl.FiscalYear, gl.FiscalPeriod
),
budget_pnl AS (
    SELECT
        bl.FiscalYear,
        bl.Month AS FiscalPeriod,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Revenue'
             AND a.AccountSubType = 'Operating Revenue'
             AND a.NormalBalance = 'Credit'
                THEN bl.BudgetAmount
            WHEN a.AccountType = 'Revenue'
             AND a.AccountSubType = 'Operating Revenue'
             AND a.NormalBalance = 'Debit'
                THEN -bl.BudgetAmount
            WHEN a.AccountType = 'Revenue'
             AND a.AccountSubType = 'Contra Revenue'
             AND a.NormalBalance = 'Credit'
                THEN bl.BudgetAmount
            WHEN a.AccountType = 'Revenue'
             AND a.AccountSubType = 'Contra Revenue'
             AND a.NormalBalance = 'Debit'
                THEN -bl.BudgetAmount
            ELSE 0
        END), 2) AS NetRevenue,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Expense'
             AND a.AccountSubType = 'COGS'
             AND a.NormalBalance = 'Debit'
                THEN bl.BudgetAmount
            WHEN a.AccountType = 'Expense'
             AND a.AccountSubType = 'COGS'
             AND a.NormalBalance = 'Credit'
                THEN -bl.BudgetAmount
            ELSE 0
        END), 2) AS CostOfGoodsSold,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Expense'
             AND a.AccountSubType = 'Operating Expense'
             AND a.NormalBalance = 'Debit'
                THEN bl.BudgetAmount
            WHEN a.AccountType = 'Expense'
             AND a.AccountSubType = 'Operating Expense'
             AND a.NormalBalance = 'Credit'
                THEN -bl.BudgetAmount
            ELSE 0
        END), 2) AS OperatingExpenses,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Revenue' AND a.NormalBalance = 'Credit' THEN bl.BudgetAmount
            WHEN a.AccountType = 'Revenue' AND a.NormalBalance = 'Debit' THEN -bl.BudgetAmount
            WHEN a.AccountType = 'Expense' AND a.NormalBalance = 'Debit' THEN -bl.BudgetAmount
            WHEN a.AccountType = 'Expense' AND a.NormalBalance = 'Credit' THEN bl.BudgetAmount
            ELSE 0
        END), 2) AS NetIncome
    FROM BudgetLine AS bl
    JOIN Account AS a
        ON a.AccountID = bl.AccountID
    WHERE bl.BudgetCategory IN ('Revenue', 'COGS', 'Operating Expense')
      AND a.AccountType IN ('Revenue', 'Expense')
      AND a.AccountSubType <> 'Header'
    GROUP BY bl.FiscalYear, bl.Month
),
actual_balance_periods AS (
    SELECT DISTINCT
        FiscalYear,
        FiscalPeriod,
        ROW_NUMBER() OVER (ORDER BY FiscalYear, FiscalPeriod) AS PeriodIndex
    FROM GLEntry
),
balance_account_layout AS (
    SELECT
        CAST(AccountNumber AS INTEGER) AS AccountNumber,
        AccountName,
        AccountType,
        AccountSubType
    FROM Account
    WHERE AccountSubType <> 'Header'
      AND CAST(AccountNumber AS INTEGER) <> 3050
),
actual_balance_activity AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        CAST(a.AccountNumber AS INTEGER) AS AccountNumber,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Asset' THEN gl.Debit - gl.Credit
            WHEN a.AccountType IN ('Liability', 'Equity') THEN gl.Credit - gl.Debit
            ELSE 0
        END), 2) AS PeriodAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE a.AccountSubType <> 'Header'
      AND CAST(a.AccountNumber AS INTEGER) <> 3050
    GROUP BY gl.FiscalYear, gl.FiscalPeriod, CAST(a.AccountNumber AS INTEGER)
),
actual_running_balance_lines AS (
    SELECT
        abp.FiscalYear,
        abp.FiscalPeriod,
        bal.AccountNumber,
        bal.AccountName,
        bal.AccountType,
        bal.AccountSubType,
        ROUND(
            SUM(COALESCE(aba.PeriodAmount, 0)) OVER (
                PARTITION BY bal.AccountNumber
                ORDER BY abp.PeriodIndex
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            2
        ) AS EndingBalance
    FROM actual_balance_periods AS abp
    CROSS JOIN balance_account_layout AS bal
    LEFT JOIN actual_balance_activity AS aba
        ON aba.FiscalYear = abp.FiscalYear
       AND aba.FiscalPeriod = abp.FiscalPeriod
       AND aba.AccountNumber = bal.AccountNumber
),
budget_balance_lines AS (
    SELECT
        bl.FiscalYear,
        bl.Month AS FiscalPeriod,
        CAST(a.AccountNumber AS INTEGER) AS AccountNumber,
        a.AccountName,
        a.AccountType,
        a.AccountSubType,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Asset' AND a.NormalBalance = 'Debit' THEN bl.BudgetAmount
            WHEN a.AccountType = 'Asset' AND a.NormalBalance = 'Credit' THEN -bl.BudgetAmount
            WHEN a.AccountType IN ('Liability', 'Equity') AND a.NormalBalance = 'Credit' THEN bl.BudgetAmount
            WHEN a.AccountType IN ('Liability', 'Equity') AND a.NormalBalance = 'Debit' THEN -bl.BudgetAmount
            ELSE 0
        END), 2) AS EndingBalance
    FROM BudgetLine AS bl
    JOIN Account AS a
        ON a.AccountID = bl.AccountID
    WHERE bl.BudgetCategory = 'Balance Sheet'
      AND a.AccountSubType <> 'Header'
      AND CAST(a.AccountNumber AS INTEGER) <> 3050
    GROUP BY
        bl.FiscalYear,
        bl.Month,
        CAST(a.AccountNumber AS INTEGER),
        a.AccountName,
        a.AccountType,
        a.AccountSubType
),
actual_current_year_earnings AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        ROUND(
            SUM(COALESCE(NetIncome, 0)) OVER (
                PARTITION BY FiscalYear
                ORDER BY FiscalPeriod
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            2
        ) AS CurrentYearEarnings
    FROM actual_pnl
),
budget_current_year_earnings AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        ROUND(
            SUM(COALESCE(NetIncome, 0)) OVER (
                PARTITION BY FiscalYear
                ORDER BY FiscalPeriod
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            2
        ) AS CurrentYearEarnings
    FROM budget_pnl
),
actual_balance_summary AS (
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet' AS StatementName, 'Accounts Receivable' AS LineLabel, ROUND(SUM(CASE WHEN AccountNumber = 1020 THEN EndingBalance ELSE 0 END), 2) AS Amount
    FROM actual_running_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Inventory - Finished Goods', ROUND(SUM(CASE WHEN AccountNumber = 1040 THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Inventory - Materials and Packaging', ROUND(SUM(CASE WHEN AccountNumber = 1045 THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Accounts Payable', ROUND(SUM(CASE WHEN AccountNumber = 2010 THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Accrued Payroll', ROUND(SUM(CASE WHEN AccountNumber = 2030 THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Accrued Expenses', ROUND(SUM(CASE WHEN AccountNumber = 2040 THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Ending Cash', ROUND(SUM(CASE WHEN AccountNumber = 1010 THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Total Assets', ROUND(SUM(CASE WHEN AccountType = 'Asset' THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Total Liabilities', ROUND(SUM(CASE WHEN AccountType = 'Liability' THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT arbl.FiscalYear, arbl.FiscalPeriod, 'Balance Sheet', 'Total Equity', ROUND(SUM(CASE WHEN arbl.AccountType = 'Equity' THEN arbl.EndingBalance ELSE 0 END) + COALESCE(acye.CurrentYearEarnings, 0), 2)
    FROM actual_running_balance_lines AS arbl
    LEFT JOIN actual_current_year_earnings AS acye
        ON acye.FiscalYear = arbl.FiscalYear
       AND acye.FiscalPeriod = arbl.FiscalPeriod
    GROUP BY arbl.FiscalYear, arbl.FiscalPeriod, acye.CurrentYearEarnings
),
budget_balance_summary AS (
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet' AS StatementName, 'Accounts Receivable' AS LineLabel, ROUND(SUM(CASE WHEN AccountNumber = 1020 THEN EndingBalance ELSE 0 END), 2) AS Amount
    FROM budget_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Inventory - Finished Goods', ROUND(SUM(CASE WHEN AccountNumber = 1040 THEN EndingBalance ELSE 0 END), 2)
    FROM budget_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Inventory - Materials and Packaging', ROUND(SUM(CASE WHEN AccountNumber = 1045 THEN EndingBalance ELSE 0 END), 2)
    FROM budget_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Accounts Payable', ROUND(SUM(CASE WHEN AccountNumber = 2010 THEN EndingBalance ELSE 0 END), 2)
    FROM budget_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Accrued Payroll', ROUND(SUM(CASE WHEN AccountNumber = 2030 THEN EndingBalance ELSE 0 END), 2)
    FROM budget_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Accrued Expenses', ROUND(SUM(CASE WHEN AccountNumber = 2040 THEN EndingBalance ELSE 0 END), 2)
    FROM budget_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Ending Cash', ROUND(SUM(CASE WHEN AccountNumber = 1010 THEN EndingBalance ELSE 0 END), 2)
    FROM budget_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Total Assets', ROUND(SUM(CASE WHEN AccountType = 'Asset' THEN EndingBalance ELSE 0 END), 2)
    FROM budget_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Balance Sheet', 'Total Liabilities', ROUND(SUM(CASE WHEN AccountType = 'Liability' THEN EndingBalance ELSE 0 END), 2)
    FROM budget_balance_lines GROUP BY FiscalYear, FiscalPeriod
    UNION ALL
    SELECT bbl.FiscalYear, bbl.FiscalPeriod, 'Balance Sheet', 'Total Equity', ROUND(SUM(CASE WHEN bbl.AccountType = 'Equity' THEN bbl.EndingBalance ELSE 0 END) + COALESCE(bcye.CurrentYearEarnings, 0), 2)
    FROM budget_balance_lines AS bbl
    LEFT JOIN budget_current_year_earnings AS bcye
        ON bcye.FiscalYear = bbl.FiscalYear
       AND bcye.FiscalPeriod = bbl.FiscalPeriod
    GROUP BY bbl.FiscalYear, bbl.FiscalPeriod, bcye.CurrentYearEarnings
),
actual_ending_cash AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        ROUND(SUM(CASE WHEN AccountNumber = 1010 THEN EndingBalance ELSE 0 END), 2) AS EndingCash
    FROM actual_running_balance_lines
    GROUP BY FiscalYear, FiscalPeriod
),
budget_ending_cash AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        ROUND(SUM(CASE WHEN AccountNumber = 1010 THEN EndingBalance ELSE 0 END), 2) AS EndingCash
    FROM budget_balance_lines
    GROUP BY FiscalYear, FiscalPeriod
),
actual_cash_summary AS (
    SELECT
        aec.FiscalYear,
        aec.FiscalPeriod,
        'Cash Flow' AS StatementName,
        'Ending Cash' AS LineLabel,
        aec.EndingCash AS Amount
    FROM actual_ending_cash AS aec

    UNION ALL

      SELECT
          aec.FiscalYear,
          aec.FiscalPeriod,
          'Cash Flow',
          'Net Change in Cash',
          ROUND(
              aec.EndingCash
              - COALESCE(
                  LAG(aec.EndingCash) OVER (
                      ORDER BY aec.FiscalYear, aec.FiscalPeriod
                  ),
                  COALESCE(obs.OpeningBalance, 0)
              ),
              2
          ) AS Amount
      FROM actual_ending_cash AS aec
    LEFT JOIN opening_balance_seed AS obs
        ON obs.FiscalYear = aec.FiscalYear
       AND obs.AccountNumber = 1010
),
budget_cash_summary AS (
    SELECT
        bec.FiscalYear,
        bec.FiscalPeriod,
        'Cash Flow' AS StatementName,
        'Ending Cash' AS LineLabel,
        bec.EndingCash AS Amount
    FROM budget_ending_cash AS bec

    UNION ALL

    SELECT
        bec.FiscalYear,
        bec.FiscalPeriod,
        'Cash Flow',
        'Net Change in Cash',
        ROUND(
            bec.EndingCash
            - COALESCE(
                LAG(bec.EndingCash) OVER (
                    ORDER BY bec.FiscalYear, bec.FiscalPeriod
                ),
                COALESCE(obs.OpeningBalance, 0)
            ),
            2
        ) AS Amount
    FROM budget_ending_cash AS bec
    LEFT JOIN opening_balance_seed AS obs
        ON obs.FiscalYear = bec.FiscalYear
       AND obs.AccountNumber = 1010
),
statement_bridge_lines AS (
    SELECT FiscalYear, FiscalPeriod, 'Income Statement' AS StatementName, 'Net Revenue' AS LineLabel, NetRevenue AS BudgetAmount, 0.0 AS ActualAmount
    FROM budget_pnl
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Income Statement', 'Gross Profit', ROUND(NetRevenue - CostOfGoodsSold, 2), 0.0 FROM budget_pnl
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Income Statement', 'Operating Income', ROUND((NetRevenue - CostOfGoodsSold) - OperatingExpenses, 2), 0.0 FROM budget_pnl
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Income Statement', 'Net Income', NetIncome, 0.0 FROM budget_pnl
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, StatementName, LineLabel, Amount, 0.0 FROM budget_balance_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, StatementName, LineLabel, Amount, 0.0 FROM budget_cash_summary
),
actual_statement_lines AS (
    SELECT FiscalYear, FiscalPeriod, 'Income Statement' AS StatementName, 'Net Revenue' AS LineLabel, NetRevenue AS Amount FROM actual_pnl
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Income Statement', 'Gross Profit', ROUND(NetRevenue - CostOfGoodsSold, 2) FROM actual_pnl
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Income Statement', 'Operating Income', ROUND((NetRevenue - CostOfGoodsSold) - OperatingExpenses, 2) FROM actual_pnl
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, 'Income Statement', 'Net Income', NetIncome FROM actual_pnl
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, StatementName, LineLabel, Amount FROM actual_balance_summary
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, StatementName, LineLabel, Amount FROM actual_cash_summary
)
SELECT
    rp.FiscalYear,
    rp.FiscalPeriod,
    sbl.StatementName,
    sbl.LineLabel,
    ROUND(sbl.BudgetAmount, 2) AS BudgetAmount,
    ROUND(COALESCE(asl.Amount, 0), 2) AS ActualAmount,
    ROUND(COALESCE(asl.Amount, 0) - sbl.BudgetAmount, 2) AS VarianceAmount,
    CASE
        WHEN sbl.BudgetAmount = 0 THEN NULL
        ELSE ROUND((COALESCE(asl.Amount, 0) - sbl.BudgetAmount) / sbl.BudgetAmount * 100.0, 2)
    END AS VariancePct
FROM reporting_periods AS rp
JOIN statement_bridge_lines AS sbl
    ON sbl.FiscalYear = rp.FiscalYear
   AND sbl.FiscalPeriod = rp.FiscalPeriod
LEFT JOIN actual_statement_lines AS asl
    ON asl.FiscalYear = sbl.FiscalYear
   AND asl.FiscalPeriod = sbl.FiscalPeriod
   AND asl.StatementName = sbl.StatementName
   AND asl.LineLabel = sbl.LineLabel
ORDER BY
    rp.FiscalYear,
    rp.FiscalPeriod,
    sbl.StatementName,
    sbl.LineLabel;
