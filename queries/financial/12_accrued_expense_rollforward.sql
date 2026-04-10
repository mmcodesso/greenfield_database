-- Teaching objective: Reconcile accrued-expense activity by month and expense family.
-- Main tables: JournalEntry, GLEntry, Account, PurchaseInvoiceLine, PurchaseInvoice.
-- Output shape: One row per fiscal year, fiscal period, and accrual family.
-- Interpretation notes: Accruals increase the liability, direct service invoices clear it, and accrual adjustments reduce overstated residual balances.

WITH accrual_journals AS (
    SELECT
        je.JournalEntryID,
        CAST(strftime('%Y', je.PostingDate) AS INTEGER) AS FiscalYear,
        CAST(strftime('%m', je.PostingDate) AS INTEGER) AS FiscalPeriod
    FROM JournalEntry AS je
    WHERE je.EntryType = 'Accrual'
),
accrual_amounts AS (
    SELECT
        aj.JournalEntryID,
        aj.FiscalYear,
        aj.FiscalPeriod,
        a.AccountNumber AS ExpenseAccountNumber,
        a.AccountName AS ExpenseAccountName,
        ROUND(SUM(gl.Debit), 2) AS AccruedAmount
    FROM accrual_journals AS aj
    JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'JournalEntry'
       AND gl.SourceDocumentID = aj.JournalEntryID
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE gl.Debit > 0
      AND a.AccountNumber IN ('6100', '6140', '6180')
    GROUP BY aj.JournalEntryID, aj.FiscalYear, aj.FiscalPeriod, a.AccountNumber, a.AccountName
),
service_invoice_clears AS (
    SELECT
        pil.AccrualJournalEntryID AS JournalEntryID,
        ROUND(SUM(CASE
            WHEN pil.LineTotal <= aa.AccruedAmount THEN pil.LineTotal
            ELSE aa.AccruedAmount
        END), 2) AS ClearedByInvoice
    FROM PurchaseInvoiceLine AS pil
    JOIN accrual_amounts AS aa
        ON aa.JournalEntryID = pil.AccrualJournalEntryID
    GROUP BY pil.AccrualJournalEntryID
),
adjustment_amounts AS (
    SELECT
        je.ReversesJournalEntryID AS JournalEntryID,
        ROUND(SUM(gl.Debit), 2) AS AdjustmentAmount
    FROM JournalEntry AS je
    JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'JournalEntry'
       AND gl.SourceDocumentID = je.JournalEntryID
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE je.EntryType = 'Accrual Adjustment'
      AND a.AccountNumber = '2040'
    GROUP BY je.ReversesJournalEntryID
)
SELECT
    aa.FiscalYear,
    aa.FiscalPeriod,
    aa.ExpenseAccountNumber,
    aa.ExpenseAccountName,
    ROUND(SUM(aa.AccruedAmount), 2) AS AccruedAmount,
    ROUND(SUM(COALESCE(sic.ClearedByInvoice, 0)), 2) AS ClearedByInvoice,
    ROUND(SUM(COALESCE(adj.AdjustmentAmount, 0)), 2) AS AdjustedDown,
    ROUND(SUM(aa.AccruedAmount - COALESCE(sic.ClearedByInvoice, 0) - COALESCE(adj.AdjustmentAmount, 0)), 2) AS ResidualLiability
FROM accrual_amounts AS aa
LEFT JOIN service_invoice_clears AS sic
    ON sic.JournalEntryID = aa.JournalEntryID
LEFT JOIN adjustment_amounts AS adj
    ON adj.JournalEntryID = aa.JournalEntryID
GROUP BY aa.FiscalYear, aa.FiscalPeriod, aa.ExpenseAccountNumber, aa.ExpenseAccountName
ORDER BY aa.FiscalYear, aa.FiscalPeriod, aa.ExpenseAccountNumber;
