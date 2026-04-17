-- Teaching objective: Produce a detailed quarterly indirect-method cash flow statement from posted ledger activity.
-- Main tables: GLEntry, Account, JournalEntry.
-- Output shape: One row per fiscal quarter and cash-flow statement line.
-- Interpretation notes: Quarterly cash flow is the sum of the in-quarter monthly flows. Beginning cash is the first month-opening balance of the quarter and ending cash is the quarter-end cash balance.

WITH closed_years AS (
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
period_numbers AS (
    SELECT 1 AS FiscalPeriod
    UNION ALL SELECT 2
    UNION ALL SELECT 3
    UNION ALL SELECT 4
    UNION ALL SELECT 5
    UNION ALL SELECT 6
    UNION ALL SELECT 7
    UNION ALL SELECT 8
    UNION ALL SELECT 9
    UNION ALL SELECT 10
    UNION ALL SELECT 11
    UNION ALL SELECT 12
),
reporting_periods AS (
    SELECT
        cy.FiscalYear,
        pn.FiscalPeriod,
        ROW_NUMBER() OVER (ORDER BY cy.FiscalYear, pn.FiscalPeriod) AS PeriodIndex
    FROM closed_years AS cy
    CROSS JOIN period_numbers AS pn
),
opening_cash_seed AS (
    SELECT
        CAST(substr(je.PostingDate, 1, 4) AS INTEGER) AS FiscalYear,
        ROUND(SUM(gl.Debit - gl.Credit), 2) AS OpeningCash
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountNumber = '1010'
      AND je.EntryType = 'Opening'
    GROUP BY CAST(substr(je.PostingDate, 1, 4) AS INTEGER)
),
cash_period_activity AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        ROUND(SUM(gl.Debit - gl.Credit), 2) AS PeriodCashAmount,
        ROUND(SUM(
            CASE
                WHEN COALESCE(je.EntryType, '') = 'Opening' THEN 0
                ELSE gl.Debit - gl.Credit
            END
        ), 2) AS PeriodCashFlowAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountNumber = '1010'
      AND gl.FiscalYear IN (SELECT FiscalYear FROM closed_years)
      AND COALESCE(je.EntryType, '') NOT IN (
            'Year-End Close - P&L to Income Summary',
            'Year-End Close - Income Summary to Retained Earnings'
      )
    GROUP BY gl.FiscalYear, gl.FiscalPeriod
),
cash_ending_balances AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        rp.PeriodIndex,
        ROUND(
            SUM(COALESCE(cpa.PeriodCashAmount, 0)) OVER (
                ORDER BY rp.PeriodIndex
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            2
        ) AS EndingCash,
        ROUND(COALESCE(cpa.PeriodCashFlowAmount, 0), 2) AS NetChangeInCash
    FROM reporting_periods AS rp
    LEFT JOIN cash_period_activity AS cpa
        ON cpa.FiscalYear = rp.FiscalYear
       AND cpa.FiscalPeriod = rp.FiscalPeriod
),
cash_reconciliation AS (
    SELECT
        ceb.FiscalYear,
        ceb.FiscalPeriod,
        ROUND(
            COALESCE(
                LAG(ceb.EndingCash) OVER (ORDER BY ceb.PeriodIndex),
                COALESCE(ocs.OpeningCash, 0)
            ),
            2
        ) AS BeginningCash,
        ceb.NetChangeInCash,
        ceb.EndingCash
    FROM cash_ending_balances AS ceb
    LEFT JOIN opening_cash_seed AS ocs
        ON ocs.FiscalYear = ceb.FiscalYear
),
cash_vouchers AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        gl.VoucherType,
        gl.VoucherNumber,
        gl.SourceDocumentType,
        gl.SourceDocumentID,
        ROUND(SUM(gl.Debit - gl.Credit), 2) AS CashAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountNumber = '1010'
      AND gl.FiscalYear IN (SELECT FiscalYear FROM closed_years)
      AND COALESCE(je.EntryType, '') NOT IN (
            'Opening',
            'Year-End Close - P&L to Income Summary',
            'Year-End Close - Income Summary to Retained Earnings'
      )
    GROUP BY
        gl.FiscalYear,
        gl.FiscalPeriod,
        gl.VoucherType,
        gl.VoucherNumber,
        gl.SourceDocumentType,
        gl.SourceDocumentID
    HAVING ROUND(SUM(gl.Debit - gl.Credit), 2) <> 0
),
voucher_counterpart_flags AS (
    SELECT
        cv.FiscalYear,
        cv.FiscalPeriod,
        cv.VoucherType,
        cv.VoucherNumber,
        MAX(CASE
            WHEN a.AccountType = 'Asset'
             AND a.AccountSubType IN ('Fixed Asset', 'Contra Fixed Asset', 'Noncurrent Asset')
                THEN 1 ELSE 0 END) AS HasInvestingCounterpart,
        MAX(CASE
            WHEN a.AccountType = 'Equity'
              OR a.AccountSubType = 'Long-Term Liability'
                THEN 1 ELSE 0 END) AS HasFinancingCounterpart,
        MAX(CASE
            WHEN a.AccountType = 'Expense'
                THEN 1 ELSE 0 END) AS HasExpenseCounterpart
    FROM cash_vouchers AS cv
    JOIN GLEntry AS gl
        ON gl.FiscalYear = cv.FiscalYear
       AND gl.FiscalPeriod = cv.FiscalPeriod
       AND gl.VoucherType = cv.VoucherType
       AND gl.VoucherNumber = cv.VoucherNumber
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE a.AccountNumber <> '1010'
    GROUP BY
        cv.FiscalYear,
        cv.FiscalPeriod,
        cv.VoucherType,
        cv.VoucherNumber
),
classified_cash_vouchers AS (
    SELECT
        cv.FiscalYear,
        cv.FiscalPeriod,
        CASE
            WHEN cv.SourceDocumentType IN (
                'CashReceipt',
                'CustomerRefund',
                'DisbursementPayment',
                'PayrollPayment',
                'PayrollLiabilityRemittance'
            )
                THEN 'Operating Activities'
            WHEN vcf.HasInvestingCounterpart = 1
                THEN 'Investing Activities'
            WHEN vcf.HasFinancingCounterpart = 1
                THEN 'Financing Activities'
            ELSE 'Operating Activities'
        END AS StatementSection,
        CASE
            WHEN cv.SourceDocumentType = 'CashReceipt'
                THEN 'Cash Received from Customers'
            WHEN cv.SourceDocumentType = 'CustomerRefund'
                THEN 'Cash Refunded to Customers'
            WHEN cv.SourceDocumentType = 'DisbursementPayment'
                THEN 'Cash Paid to Suppliers'
            WHEN cv.SourceDocumentType = 'PayrollPayment'
                THEN 'Cash Paid for Payroll'
            WHEN cv.SourceDocumentType = 'PayrollLiabilityRemittance'
                THEN 'Cash Paid for Payroll Taxes and Withholdings'
            WHEN vcf.HasInvestingCounterpart = 1
                THEN 'Capital Expenditures and Asset Transactions'
            WHEN vcf.HasFinancingCounterpart = 1
                THEN 'Debt and Equity Cash'
            WHEN cv.SourceDocumentType = 'JournalEntry'
             AND COALESCE(je.EntryType, '') IN ('Rent', 'Utilities', 'Factory Overhead')
                THEN 'Cash Paid for Other Operating Expenses'
            WHEN cv.SourceDocumentType = 'JournalEntry'
             AND vcf.HasExpenseCounterpart = 1
             AND cv.CashAmount < 0
                THEN 'Cash Paid for Other Operating Expenses'
            ELSE 'Other Operating Cash'
        END AS LineLabel,
        cv.CashAmount AS Amount
    FROM cash_vouchers AS cv
    LEFT JOIN voucher_counterpart_flags AS vcf
        ON vcf.FiscalYear = cv.FiscalYear
       AND vcf.FiscalPeriod = cv.FiscalPeriod
       AND vcf.VoucherType = cv.VoucherType
       AND vcf.VoucherNumber = cv.VoucherNumber
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = cv.SourceDocumentID
       AND cv.SourceDocumentType = 'JournalEntry'
),
actual_cash_sections AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        ROUND(COALESCE(SUM(CASE WHEN ccv.StatementSection = 'Operating Activities' THEN ccv.Amount ELSE 0 END), 0), 2) AS ActualOperatingCash,
        ROUND(COALESCE(SUM(CASE WHEN ccv.StatementSection = 'Investing Activities' THEN ccv.Amount ELSE 0 END), 0), 2) AS ActualInvestingCash,
        ROUND(COALESCE(SUM(CASE WHEN ccv.StatementSection = 'Financing Activities' THEN ccv.Amount ELSE 0 END), 0), 2) AS ActualFinancingCash
    FROM reporting_periods AS rp
    LEFT JOIN classified_cash_vouchers AS ccv
        ON ccv.FiscalYear = rp.FiscalYear
       AND ccv.FiscalPeriod = rp.FiscalPeriod
    GROUP BY rp.FiscalYear, rp.FiscalPeriod
),
pnl_period_activity AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        ROUND(COALESCE(SUM(CASE
            WHEN a.AccountType IN ('Revenue', 'Expense')
             AND a.AccountSubType <> 'Header'
             AND COALESCE(je.EntryType, '') NOT IN (
                'Year-End Close - P&L to Income Summary',
                'Year-End Close - Income Summary to Retained Earnings'
             )
                THEN gl.Credit - gl.Debit
            ELSE 0
        END), 0), 2) AS NetIncome,
        ROUND(COALESCE(SUM(CASE
            WHEN a.AccountNumber = '6130'
             AND COALESCE(je.EntryType, '') NOT IN (
                'Year-End Close - P&L to Income Summary',
                'Year-End Close - Income Summary to Retained Earnings'
             )
                THEN gl.Debit - gl.Credit
            ELSE 0
        END), 0), 2) AS DepreciationAmount
    FROM reporting_periods AS rp
    LEFT JOIN GLEntry AS gl
        ON gl.FiscalYear = rp.FiscalYear
       AND gl.FiscalPeriod = rp.FiscalPeriod
    LEFT JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    GROUP BY rp.FiscalYear, rp.FiscalPeriod
),
working_capital_account_layout AS (
    SELECT
        CAST(AccountNumber AS INTEGER) AS AccountNumber,
        AccountType,
        CASE
            WHEN CAST(AccountNumber AS INTEGER) = 1020 THEN 'Change in Accounts Receivable'
            WHEN CAST(AccountNumber AS INTEGER) IN (1040, 1045, 1046) THEN 'Change in Inventory'
            WHEN CAST(AccountNumber AS INTEGER) IN (1050, 1060, 1070, 1080) THEN 'Change in Prepaids and Other Current Assets'
            WHEN CAST(AccountNumber AS INTEGER) = 2010 THEN 'Change in Accounts Payable'
            WHEN CAST(AccountNumber AS INTEGER) = 2040 THEN 'Change in Accrued Expenses'
            WHEN CAST(AccountNumber AS INTEGER) IN (2030, 2031, 2032, 2033) THEN 'Change in Payroll Liabilities'
            WHEN CAST(AccountNumber AS INTEGER) IN (2060, 2070) THEN 'Change in Unearned Revenue / Customer Advances'
            ELSE 'Other Operating Adjustments'
        END AS LineLabel
    FROM Account
    WHERE AccountSubType IN ('Current Asset', 'Contra Current Asset', 'Current Liability')
      AND CAST(AccountNumber AS INTEGER) <> 1010
),
working_capital_opening_seed AS (
    SELECT
        CAST(substr(je.PostingDate, 1, 4) AS INTEGER) AS FiscalYear,
        CAST(a.AccountNumber AS INTEGER) AS AccountNumber,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Asset' THEN gl.Debit - gl.Credit
            WHEN a.AccountType = 'Liability' THEN gl.Credit - gl.Debit
            ELSE 0
        END), 2) AS OpeningBalance
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE je.EntryType = 'Opening'
      AND CAST(a.AccountNumber AS INTEGER) IN (SELECT AccountNumber FROM working_capital_account_layout)
    GROUP BY CAST(substr(je.PostingDate, 1, 4) AS INTEGER), CAST(a.AccountNumber AS INTEGER)
),
working_capital_period_activity AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        CAST(a.AccountNumber AS INTEGER) AS AccountNumber,
        ROUND(SUM(CASE
            WHEN a.AccountType = 'Asset' THEN gl.Debit - gl.Credit
            WHEN a.AccountType = 'Liability' THEN gl.Credit - gl.Debit
            ELSE 0
        END), 2) AS PeriodAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE gl.FiscalYear IN (SELECT FiscalYear FROM closed_years)
      AND CAST(a.AccountNumber AS INTEGER) IN (SELECT AccountNumber FROM working_capital_account_layout)
    GROUP BY gl.FiscalYear, gl.FiscalPeriod, CAST(a.AccountNumber AS INTEGER)
),
working_capital_running_balances AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        rp.PeriodIndex,
        wcal.AccountNumber,
        wcal.AccountType,
        wcal.LineLabel,
        ROUND(
            SUM(COALESCE(wcpa.PeriodAmount, 0)) OVER (
                PARTITION BY wcal.AccountNumber
                ORDER BY rp.PeriodIndex
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            2
        ) AS EndingBalance,
        COALESCE(wcos.OpeningBalance, 0) AS OpeningSeed
    FROM reporting_periods AS rp
    CROSS JOIN working_capital_account_layout AS wcal
    LEFT JOIN working_capital_period_activity AS wcpa
        ON wcpa.FiscalYear = rp.FiscalYear
       AND wcpa.FiscalPeriod = rp.FiscalPeriod
       AND wcpa.AccountNumber = wcal.AccountNumber
    LEFT JOIN working_capital_opening_seed AS wcos
        ON wcos.FiscalYear = rp.FiscalYear
       AND wcos.AccountNumber = wcal.AccountNumber
),
working_capital_balance_changes AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        AccountNumber,
        AccountType,
        LineLabel,
        ROUND(
            EndingBalance - COALESCE(
                LAG(EndingBalance) OVER (PARTITION BY AccountNumber ORDER BY PeriodIndex),
                OpeningSeed
            ),
            2
        ) AS BalanceChange
    FROM working_capital_running_balances
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
    FROM working_capital_balance_changes
    GROUP BY FiscalYear, FiscalPeriod, LineLabel
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
    WHERE LineLabel <> 'Other Operating Adjustments'
),
other_operating_adjustment AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        'Operating Activities' AS StatementSection,
        'Other Operating Adjustments' AS LineLabel,
        ROUND(
            acs.ActualOperatingCash - COALESCE(SUM(kol.Amount), 0),
            2
        ) AS Amount
    FROM reporting_periods AS rp
    JOIN actual_cash_sections AS acs
        ON acs.FiscalYear = rp.FiscalYear
       AND acs.FiscalPeriod = rp.FiscalPeriod
    LEFT JOIN known_operating_lines AS kol
        ON kol.FiscalYear = rp.FiscalYear
       AND kol.FiscalPeriod = rp.FiscalPeriod
    GROUP BY rp.FiscalYear, rp.FiscalPeriod, acs.ActualOperatingCash
),
detail_amounts AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        StatementSection,
        LineLabel,
        ROUND(Amount, 2) AS Amount
    FROM known_operating_lines

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        StatementSection,
        LineLabel,
        ROUND(Amount, 2) AS Amount
    FROM other_operating_adjustment

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Investing Activities',
        'Capital Expenditures and Asset Transactions',
        ActualInvestingCash
    FROM actual_cash_sections

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        'Financing Activities',
        'Debt and Equity Cash',
        ActualFinancingCash
    FROM actual_cash_sections
),
line_layout AS (
    SELECT
        'Operating Activities' AS StatementSection,
        'Net Income' AS LineLabel,
        'account' AS LineType,
        100 AS DisplayOrder
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
    SELECT
        FiscalYear,
        FiscalPeriod,
        StatementSection,
        LineLabel,
        Amount
    FROM detail_amounts

    UNION ALL

    SELECT
        FiscalYear,
        FiscalPeriod,
        StatementSection,
        LineLabel,
        Amount
    FROM subtotal_amounts
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
),
quarterly_statement_output AS (
    SELECT
        FiscalYear,
        CAST((FiscalPeriod - 1) / 3 AS INTEGER) + 1 AS FiscalQuarter,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder,
        ROUND(SUM(Amount), 2) AS Amount
    FROM statement_output
    WHERE LineLabel NOT IN ('Beginning Cash', 'Ending Cash')
    GROUP BY
        FiscalYear,
        CAST((FiscalPeriod - 1) / 3 AS INTEGER) + 1,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder

    UNION ALL

    SELECT
        FiscalYear,
        CAST((FiscalPeriod - 1) / 3 AS INTEGER) + 1 AS FiscalQuarter,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder,
        Amount
    FROM statement_output
    WHERE LineLabel = 'Beginning Cash'
      AND FiscalPeriod IN (1, 4, 7, 10)

    UNION ALL

    SELECT
        FiscalYear,
        CAST((FiscalPeriod - 1) / 3 AS INTEGER) + 1 AS FiscalQuarter,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder,
        Amount
    FROM statement_output
    WHERE LineLabel = 'Ending Cash'
      AND FiscalPeriod IN (3, 6, 9, 12)
)
SELECT
    FiscalYear,
    FiscalQuarter,
    StatementSection,
    LineLabel,
    LineType,
    DisplayOrder,
    Amount
FROM quarterly_statement_output
ORDER BY
    FiscalYear,
    FiscalQuarter,
    DisplayOrder,
    LineLabel;
