-- Teaching objective: Review the month-end working-capital bridge across the main current-asset and current-liability control accounts.
-- Main tables: GLEntry, Account.
-- Expected output shape: One row per fiscal month with ending balances for key working-capital buckets.
-- Recommended build mode: Either.
-- Interpretation notes: Inventory includes finished goods, materials and packaging, and WIP. Payroll liabilities combine accrued payroll, withholding, employer-tax, and deduction balances.

WITH monthly_bucket_movements AS (
    SELECT
        g.FiscalYear,
        g.FiscalPeriod,
        CASE
            WHEN a.AccountNumber = '1020' THEN 'Accounts Receivable'
            WHEN a.AccountNumber IN ('1040', '1045', '1046') THEN 'Inventory and WIP'
            WHEN a.AccountNumber = '2010' THEN 'Accounts Payable'
            WHEN a.AccountNumber = '2020' THEN 'GRNI'
            WHEN a.AccountNumber IN ('2030', '2031', '2032', '2033') THEN 'Payroll Liabilities'
            WHEN a.AccountNumber = '2040' THEN 'Accrued Expenses'
            WHEN a.AccountNumber = '2060' THEN 'Customer Deposits and Unapplied Cash'
        END AS WorkingCapitalBucket,
        ROUND(
            SUM(
                CASE
                    WHEN a.NormalBalance = 'Debit' THEN COALESCE(g.Debit, 0) - COALESCE(g.Credit, 0)
                    ELSE COALESCE(g.Credit, 0) - COALESCE(g.Debit, 0)
                END
            ),
            2
        ) AS PeriodNetChange
    FROM GLEntry AS g
    JOIN Account AS a
        ON a.AccountID = g.AccountID
    WHERE a.AccountNumber IN ('1020', '1040', '1045', '1046', '2010', '2020', '2030', '2031', '2032', '2033', '2040', '2060')
    GROUP BY
        g.FiscalYear,
        g.FiscalPeriod,
        CASE
            WHEN a.AccountNumber = '1020' THEN 'Accounts Receivable'
            WHEN a.AccountNumber IN ('1040', '1045', '1046') THEN 'Inventory and WIP'
            WHEN a.AccountNumber = '2010' THEN 'Accounts Payable'
            WHEN a.AccountNumber = '2020' THEN 'GRNI'
            WHEN a.AccountNumber IN ('2030', '2031', '2032', '2033') THEN 'Payroll Liabilities'
            WHEN a.AccountNumber = '2040' THEN 'Accrued Expenses'
            WHEN a.AccountNumber = '2060' THEN 'Customer Deposits and Unapplied Cash'
        END
),
ending_balances AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        WorkingCapitalBucket,
        ROUND(
            SUM(PeriodNetChange) OVER (
                PARTITION BY WorkingCapitalBucket
                ORDER BY FiscalYear, FiscalPeriod
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            2
        ) AS EndingBalance
    FROM monthly_bucket_movements
)
SELECT
    FiscalYear,
    FiscalPeriod,
    ROUND(SUM(CASE WHEN WorkingCapitalBucket = 'Accounts Receivable' THEN EndingBalance ELSE 0 END), 2) AS AccountsReceivableEndingBalance,
    ROUND(SUM(CASE WHEN WorkingCapitalBucket = 'Inventory and WIP' THEN EndingBalance ELSE 0 END), 2) AS InventoryAndWIPEndingBalance,
    ROUND(SUM(CASE WHEN WorkingCapitalBucket = 'Accounts Payable' THEN EndingBalance ELSE 0 END), 2) AS AccountsPayableEndingBalance,
    ROUND(SUM(CASE WHEN WorkingCapitalBucket = 'GRNI' THEN EndingBalance ELSE 0 END), 2) AS GRNIEndingBalance,
    ROUND(SUM(CASE WHEN WorkingCapitalBucket = 'Customer Deposits and Unapplied Cash' THEN EndingBalance ELSE 0 END), 2) AS CustomerDepositsEndingBalance,
    ROUND(SUM(CASE WHEN WorkingCapitalBucket = 'Accrued Expenses' THEN EndingBalance ELSE 0 END), 2) AS AccruedExpensesEndingBalance,
    ROUND(SUM(CASE WHEN WorkingCapitalBucket = 'Payroll Liabilities' THEN EndingBalance ELSE 0 END), 2) AS PayrollLiabilitiesEndingBalance,
    ROUND(
        SUM(CASE WHEN WorkingCapitalBucket IN ('Accounts Receivable', 'Inventory and WIP') THEN EndingBalance ELSE 0 END)
        - SUM(CASE WHEN WorkingCapitalBucket IN ('Accounts Payable', 'GRNI', 'Customer Deposits and Unapplied Cash', 'Accrued Expenses', 'Payroll Liabilities') THEN EndingBalance ELSE 0 END),
        2
    ) AS NetWorkingCapital
FROM ending_balances
GROUP BY FiscalYear, FiscalPeriod
ORDER BY FiscalYear, FiscalPeriod;
