-- Teaching objective: Flag accrued-expense settlements that materially differ from the original estimate or remain uncleared.
-- Main tables: JournalEntry, GLEntry, Account, PurchaseInvoiceLine, PurchaseInvoice.
-- Output shape: One row per potentially unusual accrual outcome.
-- Interpretation notes: Direct service invoices without goods receipts are expected for accrual settlement; the focus here is estimate accuracy and stale balances.

WITH accrual_amounts AS (
    SELECT
        je.JournalEntryID,
        date(je.PostingDate) AS AccrualDate,
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
      AND a.AccountNumber IN ('6100', '6140', '6180')
    GROUP BY je.JournalEntryID, date(je.PostingDate), a.AccountNumber, a.AccountName
),
invoice_summary AS (
    SELECT
        pil.AccrualJournalEntryID AS JournalEntryID,
        MIN(date(pi.InvoiceDate)) AS FirstInvoiceDate,
        ROUND(SUM(pil.LineTotal), 2) AS TotalInvoiceAmount
    FROM PurchaseInvoiceLine AS pil
    JOIN PurchaseInvoice AS pi
        ON pi.PurchaseInvoiceID = pil.PurchaseInvoiceID
    WHERE pil.AccrualJournalEntryID IS NOT NULL
    GROUP BY pil.AccrualJournalEntryID
),
adjustment_summary AS (
    SELECT
        je.ReversesJournalEntryID AS JournalEntryID,
        MIN(date(je.PostingDate)) AS FirstAdjustmentDate,
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
    aa.JournalEntryID AS AccrualJournalEntryID,
    aa.AccrualDate,
    aa.ExpenseAccountNumber,
    aa.ExpenseAccountName,
    aa.AccruedAmount,
    COALESCE(inv.TotalInvoiceAmount, 0) AS InvoicedAmount,
    COALESCE(adj.AdjustmentAmount, 0) AS AdjustedAmount,
    ROUND(aa.AccruedAmount - COALESCE(inv.TotalInvoiceAmount, 0) - COALESCE(adj.AdjustmentAmount, 0), 2) AS ResidualAmount,
    inv.FirstInvoiceDate,
    adj.FirstAdjustmentDate,
    CASE
        WHEN inv.JournalEntryID IS NULL THEN 'No linked service invoice'
        WHEN ABS(inv.TotalInvoiceAmount - aa.AccruedAmount) / NULLIF(aa.AccruedAmount, 0) > 0.10 THEN 'Invoice differs from estimate by more than 10%'
        WHEN ROUND(aa.AccruedAmount - COALESCE(inv.TotalInvoiceAmount, 0) - COALESCE(adj.AdjustmentAmount, 0), 2) > 250 THEN 'Residual accrued balance remains open'
        ELSE 'Review'
    END AS PotentialIssue
FROM accrual_amounts AS aa
LEFT JOIN invoice_summary AS inv
    ON inv.JournalEntryID = aa.JournalEntryID
LEFT JOIN adjustment_summary AS adj
    ON adj.JournalEntryID = aa.JournalEntryID
WHERE inv.JournalEntryID IS NULL
   OR ABS(COALESCE(inv.TotalInvoiceAmount, 0) - aa.AccruedAmount) / NULLIF(aa.AccruedAmount, 0) > 0.10
   OR ROUND(aa.AccruedAmount - COALESCE(inv.TotalInvoiceAmount, 0) - COALESCE(adj.AdjustmentAmount, 0), 2) > 250
ORDER BY aa.AccrualDate, aa.ExpenseAccountNumber, aa.JournalEntryID;
