-- Teaching objective: Compare accrued-expense recognition timing to later invoicing and payment timing.
-- Main tables: JournalEntry, GLEntry, Account, PurchaseInvoice, PurchaseInvoiceLine, DisbursementPayment, Supplier.
-- Output shape: One row per accrual-linked service invoice.
-- Interpretation notes: This query highlights lag from accrual date to invoice and payment date, plus over/under-accrual differences.

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
      AND a.AccountType = 'Expense'
      AND a.AccountSubType <> 'Header'
    GROUP BY je.JournalEntryID, date(je.PostingDate), a.AccountNumber, a.AccountName
),
payment_summary AS (
    SELECT
        PurchaseInvoiceID,
        MIN(date(PaymentDate)) AS FirstPaymentDate,
        ROUND(SUM(Amount), 2) AS PaidAmount
    FROM DisbursementPayment
    GROUP BY PurchaseInvoiceID
)
SELECT
    aa.ExpenseAccountNumber,
    aa.ExpenseAccountName,
    aa.AccrualDate,
    pi.InvoiceNumber,
    date(pi.InvoiceDate) AS InvoiceDate,
    s.SupplierName,
    ROUND(aa.AccruedAmount, 2) AS AccruedAmount,
    ROUND(pil.LineTotal, 2) AS InvoiceAmount,
    ROUND(pil.LineTotal - aa.AccruedAmount, 2) AS OverUnderAccrualAmount,
    CAST(julianday(pi.InvoiceDate) - julianday(aa.AccrualDate) AS INTEGER) AS DaysToInvoice,
    ps.FirstPaymentDate,
    CASE
        WHEN ps.FirstPaymentDate IS NULL THEN NULL
        ELSE CAST(julianday(ps.FirstPaymentDate) - julianday(aa.AccrualDate) AS INTEGER)
    END AS DaysToFirstPayment,
    ROUND(COALESCE(ps.PaidAmount, 0), 2) AS PaidAmount
FROM PurchaseInvoiceLine AS pil
JOIN PurchaseInvoice AS pi
    ON pi.PurchaseInvoiceID = pil.PurchaseInvoiceID
JOIN Supplier AS s
    ON s.SupplierID = pi.SupplierID
JOIN accrual_amounts AS aa
    ON aa.JournalEntryID = pil.AccrualJournalEntryID
LEFT JOIN payment_summary AS ps
    ON ps.PurchaseInvoiceID = pil.PurchaseInvoiceID
WHERE pil.AccrualJournalEntryID IS NOT NULL
ORDER BY aa.AccrualDate, aa.ExpenseAccountNumber, pi.InvoiceDate, pi.InvoiceNumber;
