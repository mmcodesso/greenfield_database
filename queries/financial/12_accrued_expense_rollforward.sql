-- Teaching objective: Roll forward accrued-expense activity by month and accrual source.
-- Main tables: JournalEntry, GLEntry, Account, PurchaseInvoice, PurchaseInvoiceLine, Shipment.
-- Output shape: One row per fiscal year, fiscal period, accrual source, and expense family.
-- Interpretation notes: Finance-managed accruals clear through supplier invoices or accrual adjustments, while outbound freight accrues operationally at shipment and settles through monthly cash journals.

WITH calendar_months AS (
    SELECT DISTINCT
        FiscalYear,
        FiscalPeriod
    FROM GLEntry
),
finance_accrual_details AS (
    SELECT
        je.JournalEntryID,
        a.AccountNumber AS ExpenseAccountNumber,
        a.AccountName AS ExpenseAccountName,
        ROUND(SUM(gl.Debit), 2) AS AccruedAmount
    FROM JournalEntry AS je
    JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'JournalEntry'
       AND gl.SourceDocumentID = je.JournalEntryID
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE je.EntryType = 'Accrual'
      AND gl.Debit > 0
      AND a.AccountType = 'Expense'
      AND a.AccountSubType <> 'Header'
    GROUP BY je.JournalEntryID, a.AccountNumber, a.AccountName
),
finance_accruals AS (
    SELECT
        CAST(strftime('%Y', je.PostingDate) AS INTEGER) AS FiscalYear,
        CAST(strftime('%m', je.PostingDate) AS INTEGER) AS FiscalPeriod,
        'Finance Accrual' AS AccrualSource,
        fad.ExpenseAccountNumber,
        fad.ExpenseAccountName,
        ROUND(SUM(fad.AccruedAmount), 2) AS AccruedAmount
    FROM JournalEntry AS je
    JOIN finance_accrual_details AS fad
        ON fad.JournalEntryID = je.JournalEntryID
    WHERE je.EntryType = 'Accrual'
    GROUP BY
        CAST(strftime('%Y', je.PostingDate) AS INTEGER),
        CAST(strftime('%m', je.PostingDate) AS INTEGER),
        fad.ExpenseAccountNumber,
        fad.ExpenseAccountName
),
finance_invoice_clears AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        'Finance Accrual' AS AccrualSource,
        fad.ExpenseAccountNumber,
        fad.ExpenseAccountName,
        ROUND(SUM(gl.Debit), 2) AS ClearedByInvoice
    FROM GLEntry AS gl
    JOIN Account AS a2040
        ON a2040.AccountID = gl.AccountID
    JOIN PurchaseInvoiceLine AS pil
        ON pil.PILineID = gl.SourceLineID
    JOIN finance_accrual_details AS fad
        ON fad.JournalEntryID = pil.AccrualJournalEntryID
    WHERE gl.SourceDocumentType = 'PurchaseInvoice'
      AND a2040.AccountNumber = '2040'
      AND gl.Debit > 0
      AND pil.AccrualJournalEntryID IS NOT NULL
    GROUP BY gl.FiscalYear, gl.FiscalPeriod, fad.ExpenseAccountNumber, fad.ExpenseAccountName
),
finance_adjustments AS (
    SELECT
        CAST(strftime('%Y', je.PostingDate) AS INTEGER) AS FiscalYear,
        CAST(strftime('%m', je.PostingDate) AS INTEGER) AS FiscalPeriod,
        'Finance Accrual' AS AccrualSource,
        fad.ExpenseAccountNumber,
        fad.ExpenseAccountName,
        ROUND(SUM(gl.Debit), 2) AS AdjustedDown
    FROM JournalEntry AS je
    JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'JournalEntry'
       AND gl.SourceDocumentID = je.JournalEntryID
    JOIN Account AS a2040
        ON a2040.AccountID = gl.AccountID
    JOIN finance_accrual_details AS fad
        ON fad.JournalEntryID = je.ReversesJournalEntryID
    WHERE je.EntryType = 'Accrual Adjustment'
      AND a2040.AccountNumber = '2040'
      AND gl.Debit > 0
      AND je.ReversesJournalEntryID IS NOT NULL
    GROUP BY
        CAST(strftime('%Y', je.PostingDate) AS INTEGER),
        CAST(strftime('%m', je.PostingDate) AS INTEGER),
        fad.ExpenseAccountNumber,
        fad.ExpenseAccountName
),
freight_accruals AS (
    SELECT
        CAST(strftime('%Y', ShipmentDate) AS INTEGER) AS FiscalYear,
        CAST(strftime('%m', ShipmentDate) AS INTEGER) AS FiscalPeriod,
        'Outbound Freight' AS AccrualSource,
        '5050' AS ExpenseAccountNumber,
        'Freight-Out Expense' AS ExpenseAccountName,
        ROUND(SUM(FreightCost), 2) AS AccruedAmount
    FROM Shipment
    WHERE COALESCE(FreightCost, 0) > 0
    GROUP BY
        CAST(strftime('%Y', ShipmentDate) AS INTEGER),
        CAST(strftime('%m', ShipmentDate) AS INTEGER)
),
freight_settlements AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        'Outbound Freight' AS AccrualSource,
        '5050' AS ExpenseAccountNumber,
        'Freight-Out Expense' AS ExpenseAccountName,
        ROUND(SUM(gl.Debit), 2) AS SettledByCash
    FROM JournalEntry AS je
    JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'JournalEntry'
       AND gl.SourceDocumentID = je.JournalEntryID
    JOIN Account AS a2040
        ON a2040.AccountID = gl.AccountID
    WHERE je.EntryType = 'Freight Settlement'
      AND a2040.AccountNumber = '2040'
      AND gl.Debit > 0
    GROUP BY gl.FiscalYear, gl.FiscalPeriod
),
families AS (
    SELECT DISTINCT
        AccrualSource,
        ExpenseAccountNumber,
        ExpenseAccountName
    FROM finance_accruals
    UNION
    SELECT DISTINCT
        AccrualSource,
        ExpenseAccountNumber,
        ExpenseAccountName
    FROM freight_accruals
    UNION
    SELECT DISTINCT
        AccrualSource,
        ExpenseAccountNumber,
        ExpenseAccountName
    FROM freight_settlements
),
month_family_grid AS (
    SELECT
        cm.FiscalYear,
        cm.FiscalPeriod,
        f.AccrualSource,
        f.ExpenseAccountNumber,
        f.ExpenseAccountName
    FROM calendar_months AS cm
    CROSS JOIN families AS f
),
monthly_activity AS (
    SELECT
        mfg.FiscalYear,
        mfg.FiscalPeriod,
        mfg.AccrualSource,
        mfg.ExpenseAccountNumber,
        mfg.ExpenseAccountName,
        ROUND(COALESCE(fa.AccruedAmount, 0) + COALESCE(foa.AccruedAmount, 0), 2) AS AccruedAmount,
        ROUND(COALESCE(fic.ClearedByInvoice, 0), 2) AS ClearedByInvoice,
        ROUND(COALESCE(fs.SettledByCash, 0), 2) AS SettledByCash,
        ROUND(COALESCE(fadj.AdjustedDown, 0), 2) AS AdjustedDown
    FROM month_family_grid AS mfg
    LEFT JOIN finance_accruals AS fa
        ON fa.FiscalYear = mfg.FiscalYear
       AND fa.FiscalPeriod = mfg.FiscalPeriod
       AND fa.AccrualSource = mfg.AccrualSource
       AND fa.ExpenseAccountNumber = mfg.ExpenseAccountNumber
    LEFT JOIN finance_invoice_clears AS fic
        ON fic.FiscalYear = mfg.FiscalYear
       AND fic.FiscalPeriod = mfg.FiscalPeriod
       AND fic.AccrualSource = mfg.AccrualSource
       AND fic.ExpenseAccountNumber = mfg.ExpenseAccountNumber
    LEFT JOIN finance_adjustments AS fadj
        ON fadj.FiscalYear = mfg.FiscalYear
       AND fadj.FiscalPeriod = mfg.FiscalPeriod
       AND fadj.AccrualSource = mfg.AccrualSource
       AND fadj.ExpenseAccountNumber = mfg.ExpenseAccountNumber
    LEFT JOIN freight_accruals AS foa
        ON foa.FiscalYear = mfg.FiscalYear
       AND foa.FiscalPeriod = mfg.FiscalPeriod
       AND foa.AccrualSource = mfg.AccrualSource
       AND foa.ExpenseAccountNumber = mfg.ExpenseAccountNumber
    LEFT JOIN freight_settlements AS fs
        ON fs.FiscalYear = mfg.FiscalYear
       AND fs.FiscalPeriod = mfg.FiscalPeriod
       AND fs.AccrualSource = mfg.AccrualSource
       AND fs.ExpenseAccountNumber = mfg.ExpenseAccountNumber
),
rollforward AS (
    SELECT
        ma.*,
        ROUND(
            COALESCE(
                SUM(ma.AccruedAmount - ma.ClearedByInvoice - ma.SettledByCash - ma.AdjustedDown) OVER (
                    PARTITION BY ma.AccrualSource, ma.ExpenseAccountNumber
                    ORDER BY ma.FiscalYear, ma.FiscalPeriod
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ),
                0
            ),
            2
        ) AS BeginningLiability,
        ROUND(
            SUM(ma.AccruedAmount - ma.ClearedByInvoice - ma.SettledByCash - ma.AdjustedDown) OVER (
                PARTITION BY ma.AccrualSource, ma.ExpenseAccountNumber
                ORDER BY ma.FiscalYear, ma.FiscalPeriod
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ),
            2
        ) AS EndingLiability
    FROM monthly_activity AS ma
)
SELECT
    FiscalYear,
    FiscalPeriod,
    AccrualSource,
    ExpenseAccountNumber,
    ExpenseAccountName,
    BeginningLiability,
    AccruedAmount,
    ClearedByInvoice,
    SettledByCash,
    AdjustedDown,
    EndingLiability
FROM rollforward
WHERE AccruedAmount <> 0
   OR ClearedByInvoice <> 0
   OR SettledByCash <> 0
   OR AdjustedDown <> 0
   OR BeginningLiability <> 0
   OR EndingLiability <> 0
ORDER BY FiscalYear, FiscalPeriod, AccrualSource, ExpenseAccountNumber;
