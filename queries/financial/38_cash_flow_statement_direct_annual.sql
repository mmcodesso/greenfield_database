-- Teaching objective: Produce a detailed annual direct-method cash flow statement from posted cash-ledger activity.
-- Main tables: GLEntry, Account, JournalEntry.
-- Output shape: One row per fiscal year and cash-flow statement line.
-- Interpretation notes: Annual cash flow is the sum of the in-year monthly flows. Beginning cash is the first month-opening balance of the fiscal year and ending cash is the year-end cash balance.

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
capex_disbursement_flags AS (
    SELECT DISTINCT
        dp.DisbursementID,
        1 AS IsCapexDisbursement
    FROM DisbursementPayment AS dp
    JOIN FixedAssetEvent AS fae
        ON fae.DisbursementID = dp.DisbursementID
    WHERE fae.EventType IN ('Acquisition', 'Improvement')
),
classified_cash_vouchers AS (
    SELECT
        cv.FiscalYear,
        cv.FiscalPeriod,
        CASE
            WHEN cv.SourceDocumentType = 'DisbursementPayment'
             AND COALESCE(cdf.IsCapexDisbursement, 0) = 1
                THEN 'Investing Activities'
            WHEN cv.SourceDocumentType IN (
                'CashReceipt',
                'CustomerRefund',
                'DisbursementPayment',
                'PayrollPayment',
                'PayrollLiabilityRemittance',
                'SalesCommissionPayment'
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
             AND COALESCE(cdf.IsCapexDisbursement, 0) = 0
                THEN 'Cash Paid to Suppliers'
            WHEN cv.SourceDocumentType = 'PayrollPayment'
                THEN 'Cash Paid for Payroll'
            WHEN cv.SourceDocumentType = 'PayrollLiabilityRemittance'
                THEN 'Cash Paid for Payroll Taxes and Withholdings'
            WHEN cv.SourceDocumentType = 'SalesCommissionPayment'
                THEN 'Cash Paid for Sales Commissions'
            WHEN cv.SourceDocumentType = 'DisbursementPayment'
             AND COALESCE(cdf.IsCapexDisbursement, 0) = 1
                THEN 'Capital Expenditures and Asset Transactions'
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
    LEFT JOIN capex_disbursement_flags AS cdf
        ON cdf.DisbursementID = cv.SourceDocumentID
       AND cv.SourceDocumentType = 'DisbursementPayment'
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = cv.SourceDocumentID
       AND cv.SourceDocumentType = 'JournalEntry'
),
detail_amounts AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        StatementSection,
        LineLabel,
        ROUND(SUM(Amount), 2) AS Amount
    FROM classified_cash_vouchers
    GROUP BY FiscalYear, FiscalPeriod, StatementSection, LineLabel
),
line_layout AS (
    SELECT
        'Operating Activities' AS StatementSection,
        'Cash Received from Customers' AS LineLabel,
        'account' AS LineType,
        100 AS DisplayOrder
    UNION ALL SELECT 'Operating Activities', 'Cash Refunded to Customers', 'account', 110
    UNION ALL SELECT 'Operating Activities', 'Cash Paid to Suppliers', 'account', 120
    UNION ALL SELECT 'Operating Activities', 'Cash Paid for Payroll', 'account', 130
    UNION ALL SELECT 'Operating Activities', 'Cash Paid for Payroll Taxes and Withholdings', 'account', 140
    UNION ALL SELECT 'Operating Activities', 'Cash Paid for Sales Commissions', 'account', 145
    UNION ALL SELECT 'Operating Activities', 'Cash Paid for Other Operating Expenses', 'account', 150
    UNION ALL SELECT 'Operating Activities', 'Other Operating Cash', 'account', 160
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
annual_statement_output AS (
    SELECT
        FiscalYear,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder,
        ROUND(SUM(Amount), 2) AS Amount
    FROM statement_output
    WHERE LineLabel NOT IN ('Beginning Cash', 'Ending Cash')
    GROUP BY
        FiscalYear,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder

    UNION ALL

    SELECT
        FiscalYear,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder,
        Amount
    FROM statement_output
    WHERE LineLabel = 'Beginning Cash'
      AND FiscalPeriod = 1

    UNION ALL

    SELECT
        FiscalYear,
        StatementSection,
        LineLabel,
        LineType,
        DisplayOrder,
        Amount
    FROM statement_output
    WHERE LineLabel = 'Ending Cash'
      AND FiscalPeriod = 12
)
SELECT
    FiscalYear,
    StatementSection,
    LineLabel,
    LineType,
    DisplayOrder,
    Amount
FROM annual_statement_output
ORDER BY
    FiscalYear,
    DisplayOrder,
    LineLabel;
