-- Teaching objective: Produce a monthly pro forma indirect-method cash flow statement from the driver-based budget roll-forward.
-- Main tables: BudgetLine, Account, GLEntry, JournalEntry.
-- Output shape: One row per fiscal month and cash-flow statement line.
-- Interpretation notes: Beginning balances for the first budget period come from the opening journal. Operating cash is reconciled from net income plus non-cash items and working-capital movement; investing cash reflects gross fixed-asset additions implied by the maintenance-capex policy.

WITH reporting_periods AS (
    SELECT
        FiscalYear,
        Month AS FiscalPeriod,
        ROW_NUMBER() OVER (ORDER BY FiscalYear, Month) AS PeriodIndex
    FROM (
        SELECT DISTINCT
            FiscalYear,
            Month
        FROM BudgetLine
    )
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
balance_sheet_budget AS (
    SELECT
        bl.FiscalYear,
        bl.Month AS FiscalPeriod,
        CAST(a.AccountNumber AS INTEGER) AS AccountNumber,
        ROUND(SUM(bl.BudgetAmount), 2) AS EndingBalance
    FROM BudgetLine AS bl
    JOIN Account AS a
        ON a.AccountID = bl.AccountID
    WHERE bl.BudgetCategory = 'Balance Sheet'
    GROUP BY
        bl.FiscalYear,
        bl.Month,
        CAST(a.AccountNumber AS INTEGER)
),
balance_sheet_accounts AS (
    SELECT 1010 AS AccountNumber, 'Cash' AS LineLabel, 'Asset' AS AccountType
    UNION ALL SELECT 1020, 'Change in Accounts Receivable', 'Asset'
    UNION ALL SELECT 1040, 'Change in Inventory', 'Asset'
    UNION ALL SELECT 1045, 'Change in Inventory', 'Asset'
    UNION ALL SELECT 1046, 'Change in Inventory', 'Asset'
    UNION ALL SELECT 1050, 'Change in Prepaids and Other Current Assets', 'Asset'
    UNION ALL SELECT 1060, 'Change in Prepaids and Other Current Assets', 'Asset'
    UNION ALL SELECT 1070, 'Change in Prepaids and Other Current Assets', 'Asset'
    UNION ALL SELECT 1080, 'Change in Prepaids and Other Current Assets', 'Asset'
    UNION ALL SELECT 2010, 'Change in Accounts Payable', 'Liability'
    UNION ALL SELECT 2030, 'Change in Payroll Liabilities', 'Liability'
    UNION ALL SELECT 2031, 'Change in Payroll Liabilities', 'Liability'
    UNION ALL SELECT 2032, 'Change in Payroll Liabilities', 'Liability'
    UNION ALL SELECT 2033, 'Change in Payroll Liabilities', 'Liability'
    UNION ALL SELECT 2040, 'Change in Accrued Expenses', 'Liability'
    UNION ALL SELECT 2060, 'Change in Unearned Revenue / Customer Advances', 'Liability'
    UNION ALL SELECT 2070, 'Change in Unearned Revenue / Customer Advances', 'Liability'
    UNION ALL SELECT 1110, 'Capital Expenditures and Asset Transactions', 'Asset'
    UNION ALL SELECT 1120, 'Capital Expenditures and Asset Transactions', 'Asset'
    UNION ALL SELECT 1130, 'Capital Expenditures and Asset Transactions', 'Asset'
    UNION ALL SELECT 1140, 'Capital Expenditures and Asset Transactions', 'Asset'
    UNION ALL SELECT 2110, 'Debt and Equity Cash', 'Liability'
    UNION ALL SELECT 2120, 'Debt and Equity Cash', 'Liability'
    UNION ALL SELECT 2130, 'Debt and Equity Cash', 'Liability'
    UNION ALL SELECT 3010, 'Debt and Equity Cash', 'Equity'
    UNION ALL SELECT 3020, 'Debt and Equity Cash', 'Equity'
    UNION ALL SELECT 3040, 'Debt and Equity Cash', 'Equity'
),
account_balance_changes AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        rp.PeriodIndex,
        bsa.AccountNumber,
        bsa.LineLabel,
        bsa.AccountType,
        ROUND(COALESCE(bsb.EndingBalance, 0), 2) AS EndingBalance,
        ROUND(
            COALESCE(bsb.EndingBalance, 0)
            - COALESCE(
                LAG(COALESCE(bsb.EndingBalance, 0)) OVER (
                    PARTITION BY bsa.AccountNumber
                    ORDER BY rp.PeriodIndex
                ),
                CASE
                    WHEN rp.FiscalPeriod = (
                        SELECT MIN(first_period.FiscalPeriod)
                        FROM reporting_periods AS first_period
                        WHERE first_period.FiscalYear = rp.FiscalYear
                    )
                        THEN COALESCE(obs.OpeningBalance, 0)
                    ELSE 0
                END
            ),
            2
        ) AS BalanceChange
    FROM reporting_periods AS rp
    CROSS JOIN balance_sheet_accounts AS bsa
    LEFT JOIN balance_sheet_budget AS bsb
        ON bsb.FiscalYear = rp.FiscalYear
       AND bsb.FiscalPeriod = rp.FiscalPeriod
       AND bsb.AccountNumber = bsa.AccountNumber
    LEFT JOIN opening_balance_seed AS obs
        ON obs.FiscalYear = rp.FiscalYear
       AND obs.AccountNumber = bsa.AccountNumber
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
        END), 2) AS NetIncome,
        ROUND(SUM(CASE
            WHEN a.AccountNumber = '6130' THEN bl.BudgetAmount
            ELSE 0
        END), 2) AS DepreciationAmount
    FROM BudgetLine AS bl
    JOIN Account AS a
        ON a.AccountID = bl.AccountID
    WHERE bl.BudgetCategory IN ('Revenue', 'COGS', 'Operating Expense')
      AND a.AccountType IN ('Revenue', 'Expense')
      AND a.AccountSubType <> 'Header'
    GROUP BY bl.FiscalYear, bl.Month
),
working_capital_adjustments AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        LineLabel,
        ROUND(SUM(CASE
            WHEN AccountType = 'Asset' THEN -BalanceChange
            WHEN AccountType = 'Liability' THEN BalanceChange
            ELSE 0
        END), 2) AS Amount
    FROM account_balance_changes
    WHERE LineLabel IN (
        'Change in Accounts Receivable',
        'Change in Inventory',
        'Change in Prepaids and Other Current Assets',
        'Change in Accounts Payable',
        'Change in Accrued Expenses',
        'Change in Payroll Liabilities',
        'Change in Unearned Revenue / Customer Advances'
    )
    GROUP BY FiscalYear, FiscalPeriod, LineLabel
),
investing_cash AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        ROUND(-SUM(BalanceChange), 2) AS Amount
    FROM account_balance_changes
    WHERE LineLabel = 'Capital Expenditures and Asset Transactions'
    GROUP BY FiscalYear, FiscalPeriod
),
financing_cash AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        ROUND(SUM(CASE
            WHEN AccountNumber = 3040 THEN -BalanceChange
            ELSE BalanceChange
        END), 2) AS Amount
    FROM account_balance_changes
    WHERE LineLabel = 'Debt and Equity Cash'
    GROUP BY FiscalYear, FiscalPeriod
),
cash_reconciliation AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        rp.PeriodIndex,
        ROUND(COALESCE(cash_balance.EndingBalance, 0), 2) AS EndingCash,
        ROUND(COALESCE(cash_balance.BalanceChange, 0), 2) AS NetChangeInCash,
        ROUND(
            COALESCE(
                LAG(COALESCE(cash_balance.EndingBalance, 0)) OVER (ORDER BY rp.PeriodIndex),
                COALESCE(opening_cash.OpeningBalance, 0)
            ),
            2
        ) AS BeginningCash
    FROM reporting_periods AS rp
    LEFT JOIN account_balance_changes AS cash_balance
        ON cash_balance.FiscalYear = rp.FiscalYear
       AND cash_balance.FiscalPeriod = rp.FiscalPeriod
       AND cash_balance.AccountNumber = 1010
    LEFT JOIN opening_balance_seed AS opening_cash
        ON opening_cash.FiscalYear = rp.FiscalYear
       AND opening_cash.AccountNumber = 1010
),
known_operating_lines AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        'Operating Activities' AS StatementSection,
        'Net Income' AS LineLabel,
        NetIncome AS Amount
    FROM pnl_period_activity

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Operating Activities',
        'Depreciation and Amortization',
        DepreciationAmount
    FROM pnl_period_activity

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Operating Activities',
        LineLabel,
        Amount
    FROM working_capital_adjustments
),
other_operating_adjustment AS (
    SELECT
        cr.FiscalYear,
        cr.FiscalPeriod,
        'Operating Activities' AS StatementSection,
        'Other Operating Adjustments' AS LineLabel,
        ROUND(
            cr.NetChangeInCash
            - COALESCE(ic.Amount, 0)
            - COALESCE(fc.Amount, 0)
            - COALESCE(SUM(kol.Amount), 0),
            2
        ) AS Amount
    FROM cash_reconciliation AS cr
    LEFT JOIN investing_cash AS ic
        ON ic.FiscalYear = cr.FiscalYear
       AND ic.FiscalPeriod = cr.FiscalPeriod
    LEFT JOIN financing_cash AS fc
        ON fc.FiscalYear = cr.FiscalYear
       AND fc.FiscalPeriod = cr.FiscalPeriod
    LEFT JOIN known_operating_lines AS kol
        ON kol.FiscalYear = cr.FiscalYear
       AND kol.FiscalPeriod = cr.FiscalPeriod
    GROUP BY
        cr.FiscalYear,
        cr.FiscalPeriod,
        cr.NetChangeInCash,
        ic.Amount,
        fc.Amount
),
detail_amounts AS (
    SELECT FiscalYear, FiscalPeriod, StatementSection, LineLabel, ROUND(Amount, 2) AS Amount
    FROM known_operating_lines

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, StatementSection, LineLabel, ROUND(Amount, 2) AS Amount
    FROM other_operating_adjustment

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Investing Activities', 'Capital Expenditures and Asset Transactions', ROUND(COALESCE(Amount, 0), 2)
    FROM investing_cash

    UNION ALL

    SELECT FiscalYear, FiscalPeriod, 'Financing Activities', 'Debt and Equity Cash', ROUND(COALESCE(Amount, 0), 2)
    FROM financing_cash
),
line_layout AS (
    SELECT 'Operating Activities' AS StatementSection, 'Net Income' AS LineLabel, 'account' AS LineType, 100 AS DisplayOrder
    UNION ALL SELECT 'Operating Activities', 'Depreciation and Amortization', 'account', 110
    UNION ALL SELECT 'Operating Activities', 'Change in Accounts Receivable', 'account', 120
    UNION ALL SELECT 'Operating Activities', 'Change in Inventory', 'account', 130
    UNION ALL SELECT 'Operating Activities', 'Change in Prepaids and Other Current Assets', 'account', 140
    UNION ALL SELECT 'Operating Activities', 'Change in Accounts Payable', 'account', 150
    UNION ALL SELECT 'Operating Activities', 'Change in Accrued Expenses', 'account', 160
    UNION ALL SELECT 'Operating Activities', 'Change in Payroll Liabilities', 'account', 170
    UNION ALL SELECT 'Operating Activities', 'Change in Unearned Revenue / Customer Advances', 'account', 180
    UNION ALL SELECT 'Operating Activities', 'Other Operating Adjustments', 'account', 189
    UNION ALL SELECT 'Net Cash from Operating Activities', 'Net Cash from Operating Activities', 'subtotal', 190
    UNION ALL SELECT 'Investing Activities', 'Capital Expenditures and Asset Transactions', 'account', 300
    UNION ALL SELECT 'Net Cash from Investing Activities', 'Net Cash from Investing Activities', 'subtotal', 390
    UNION ALL SELECT 'Financing Activities', 'Debt and Equity Cash', 'account', 500
    UNION ALL SELECT 'Net Cash from Financing Activities', 'Net Cash from Financing Activities', 'subtotal', 590
    UNION ALL SELECT 'Net Change in Cash', 'Net Change in Cash', 'subtotal', 700
    UNION ALL SELECT 'Beginning Cash', 'Beginning Cash', 'subtotal', 800
    UNION ALL SELECT 'Ending Cash', 'Ending Cash', 'subtotal', 900
),
subtotal_amounts AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        'Net Cash from Operating Activities' AS StatementSection,
        'Net Cash from Operating Activities' AS LineLabel,
        ROUND(COALESCE(SUM(CASE WHEN da.StatementSection = 'Operating Activities' THEN da.Amount ELSE 0 END), 0), 2) AS Amount
    FROM reporting_periods AS rp
    LEFT JOIN detail_amounts AS da
        ON da.FiscalYear = rp.FiscalYear
       AND da.FiscalPeriod = rp.FiscalPeriod
    GROUP BY rp.FiscalYear, rp.FiscalPeriod

    UNION ALL

    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        'Net Cash from Investing Activities',
        'Net Cash from Investing Activities',
        ROUND(COALESCE(SUM(CASE WHEN da.StatementSection = 'Investing Activities' THEN da.Amount ELSE 0 END), 0), 2) AS Amount
    FROM reporting_periods AS rp
    LEFT JOIN detail_amounts AS da
        ON da.FiscalYear = rp.FiscalYear
       AND da.FiscalPeriod = rp.FiscalPeriod
    GROUP BY rp.FiscalYear, rp.FiscalPeriod

    UNION ALL

    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        'Net Cash from Financing Activities',
        'Net Cash from Financing Activities',
        ROUND(COALESCE(SUM(CASE WHEN da.StatementSection = 'Financing Activities' THEN da.Amount ELSE 0 END), 0), 2) AS Amount
    FROM reporting_periods AS rp
    LEFT JOIN detail_amounts AS da
        ON da.FiscalYear = rp.FiscalYear
       AND da.FiscalPeriod = rp.FiscalPeriod
    GROUP BY rp.FiscalYear, rp.FiscalPeriod

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Net Change in Cash',
        'Net Change in Cash',
        NetChangeInCash
    FROM cash_reconciliation

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Beginning Cash',
        'Beginning Cash',
        BeginningCash
    FROM cash_reconciliation

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Ending Cash',
        'Ending Cash',
        EndingCash
    FROM cash_reconciliation
),
statement_amounts AS (
    SELECT FiscalYear, FiscalPeriod, StatementSection, LineLabel, Amount FROM detail_amounts
    UNION ALL
    SELECT FiscalYear, FiscalPeriod, StatementSection, LineLabel, Amount FROM subtotal_amounts
),
statement_output AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        ll.StatementSection,
        ll.LineLabel,
        ll.LineType,
        ll.DisplayOrder,
        ROUND(COALESCE(sa.Amount, 0), 2) AS Amount
    FROM reporting_periods AS rp
    CROSS JOIN line_layout AS ll
    LEFT JOIN statement_amounts AS sa
        ON sa.FiscalYear = rp.FiscalYear
       AND sa.FiscalPeriod = rp.FiscalPeriod
       AND sa.StatementSection = ll.StatementSection
       AND sa.LineLabel = ll.LineLabel
)
SELECT
    FiscalYear,
    FiscalPeriod,
    StatementSection,
    LineLabel,
    LineType,
    DisplayOrder,
    Amount
FROM statement_output
ORDER BY
    FiscalYear,
    FiscalPeriod,
    DisplayOrder,
    LineLabel;
