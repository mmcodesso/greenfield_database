-- Teaching objective: Compare budgeted and actual month-end working-capital balances and cash on one bridge.
-- Main tables: BudgetLine, GLEntry, Account, JournalEntry.
-- Output shape: One row per fiscal month and working-capital or cash metric.
-- Interpretation notes: Actual balances appear only for generated posting months. Future budget-only months remain in the bridge with zero actuals.

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
actual_periods AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        ROW_NUMBER() OVER (ORDER BY FiscalYear, FiscalPeriod) AS PeriodIndex
    FROM (
        SELECT DISTINCT
            FiscalYear,
            FiscalPeriod
        FROM GLEntry
    ) AS distinct_actual_periods
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
    WHERE CAST(a.AccountNumber AS INTEGER) IN (1010, 1020, 1040, 1045, 2010, 2030, 2040)
    GROUP BY gl.FiscalYear, gl.FiscalPeriod, CAST(a.AccountNumber AS INTEGER)
),
actual_balance_accounts AS (
    SELECT 1010 AS AccountNumber
    UNION ALL SELECT 1020
    UNION ALL SELECT 1040
    UNION ALL SELECT 1045
    UNION ALL SELECT 2010
    UNION ALL SELECT 2030
    UNION ALL SELECT 2040
),
actual_running_balances AS (
    SELECT
        ap.FiscalYear,
        ap.FiscalPeriod,
        aba.AccountNumber,
        ROUND(
            SUM(COALESCE(activity.PeriodAmount, 0)) OVER (
                PARTITION BY aba.AccountNumber
                ORDER BY ap.PeriodIndex
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            2
        ) AS EndingBalance
    FROM actual_periods AS ap
    CROSS JOIN actual_balance_accounts AS aba
    LEFT JOIN actual_balance_activity AS activity
        ON activity.FiscalYear = ap.FiscalYear
       AND activity.FiscalPeriod = ap.FiscalPeriod
       AND activity.AccountNumber = aba.AccountNumber
),
budget_running_balances AS (
    SELECT
        bl.FiscalYear,
        bl.Month AS FiscalPeriod,
        CAST(a.AccountNumber AS INTEGER) AS AccountNumber,
        ROUND(SUM(bl.BudgetAmount), 2) AS EndingBalance
    FROM BudgetLine AS bl
    JOIN Account AS a
        ON a.AccountID = bl.AccountID
    WHERE bl.BudgetCategory = 'Balance Sheet'
      AND CAST(a.AccountNumber AS INTEGER) IN (1010, 1020, 1040, 1045, 2010, 2030, 2040)
    GROUP BY bl.FiscalYear, bl.Month, CAST(a.AccountNumber AS INTEGER)
),
metric_values AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        'Accounts Receivable Ending Balance' AS MetricName,
        ROUND(SUM(CASE WHEN AccountNumber = 1020 THEN EndingBalance ELSE 0 END), 2) AS BudgetAmount,
        0.0 AS ActualAmount
    FROM budget_running_balances
    GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Finished Goods Inventory Ending Balance', ROUND(SUM(CASE WHEN AccountNumber = 1040 THEN EndingBalance ELSE 0 END), 2), 0.0
    FROM budget_running_balances GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Materials Inventory Ending Balance', ROUND(SUM(CASE WHEN AccountNumber = 1045 THEN EndingBalance ELSE 0 END), 2), 0.0
    FROM budget_running_balances GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Accounts Payable Ending Balance', ROUND(SUM(CASE WHEN AccountNumber = 2010 THEN EndingBalance ELSE 0 END), 2), 0.0
    FROM budget_running_balances GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Accrued Payroll Ending Balance', ROUND(SUM(CASE WHEN AccountNumber = 2030 THEN EndingBalance ELSE 0 END), 2), 0.0
    FROM budget_running_balances GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Accrued Expenses Ending Balance', ROUND(SUM(CASE WHEN AccountNumber = 2040 THEN EndingBalance ELSE 0 END), 2), 0.0
    FROM budget_running_balances GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Ending Cash', ROUND(SUM(CASE WHEN AccountNumber = 1010 THEN EndingBalance ELSE 0 END), 2), 0.0
    FROM budget_running_balances GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Net Working Capital',
        ROUND(
            SUM(CASE WHEN AccountNumber IN (1020, 1040, 1045) THEN EndingBalance ELSE 0 END)
            - SUM(CASE WHEN AccountNumber IN (2010, 2030, 2040) THEN EndingBalance ELSE 0 END),
            2
        ),
        0.0
    FROM budget_running_balances
    GROUP BY FiscalYear, FiscalPeriod
),
actual_metric_values AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        'Accounts Receivable Ending Balance' AS MetricName,
        ROUND(SUM(CASE WHEN AccountNumber = 1020 THEN EndingBalance ELSE 0 END), 2) AS ActualAmount
    FROM actual_running_balances
    GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Finished Goods Inventory Ending Balance', ROUND(SUM(CASE WHEN AccountNumber = 1040 THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balances GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Materials Inventory Ending Balance', ROUND(SUM(CASE WHEN AccountNumber = 1045 THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balances GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Accounts Payable Ending Balance', ROUND(SUM(CASE WHEN AccountNumber = 2010 THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balances GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Accrued Payroll Ending Balance', ROUND(SUM(CASE WHEN AccountNumber = 2030 THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balances GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Accrued Expenses Ending Balance', ROUND(SUM(CASE WHEN AccountNumber = 2040 THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balances GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Ending Cash', ROUND(SUM(CASE WHEN AccountNumber = 1010 THEN EndingBalance ELSE 0 END), 2)
    FROM actual_running_balances GROUP BY FiscalYear, FiscalPeriod

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Net Working Capital',
        ROUND(
            SUM(CASE WHEN AccountNumber IN (1020, 1040, 1045) THEN EndingBalance ELSE 0 END)
            - SUM(CASE WHEN AccountNumber IN (2010, 2030, 2040) THEN EndingBalance ELSE 0 END),
            2
        )
    FROM actual_running_balances
    GROUP BY FiscalYear, FiscalPeriod
)
SELECT
    mv.FiscalYear,
    mv.FiscalPeriod,
    mv.MetricName,
    ROUND(mv.BudgetAmount, 2) AS BudgetAmount,
    ROUND(COALESCE(amv.ActualAmount, 0), 2) AS ActualAmount,
    ROUND(COALESCE(amv.ActualAmount, 0) - mv.BudgetAmount, 2) AS VarianceAmount,
    CASE
        WHEN mv.BudgetAmount = 0 THEN NULL
        ELSE ROUND((COALESCE(amv.ActualAmount, 0) - mv.BudgetAmount) / mv.BudgetAmount * 100.0, 2)
    END AS VariancePct
FROM metric_values AS mv
LEFT JOIN actual_metric_values AS amv
    ON amv.FiscalYear = mv.FiscalYear
   AND amv.FiscalPeriod = mv.FiscalPeriod
   AND amv.MetricName = mv.MetricName
ORDER BY
    mv.FiscalYear,
    mv.FiscalPeriod,
    mv.MetricName;
