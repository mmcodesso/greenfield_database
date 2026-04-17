-- Teaching objective: Trace an accrual-linked supplier invoice line from accrual journal through invoice clearing and disbursement postings.
-- Main tables: JournalEntry, PurchaseInvoiceLine, PurchaseInvoice, DisbursementPayment, GLEntry, Account, Supplier, Item.
-- Output shape: One row per accrual-linked purchase invoice line.
-- Interpretation notes: The accrual creates the estimate, the supplier invoice clears 2040 and creates AP, and disbursement later clears AP through cash.

WITH accrual_amounts AS (
    SELECT
        je.JournalEntryID,
        je.EntryNumber,
        date(je.PostingDate) AS AccrualDate,
        MAX(CASE
            WHEN gl.Debit > 0 AND a.AccountNumber <> '2040' THEN a.AccountNumber
        END) AS ExpenseAccountNumber,
        MAX(CASE
            WHEN gl.Debit > 0 AND a.AccountNumber <> '2040' THEN a.AccountName
        END) AS ExpenseAccountName,
        ROUND(SUM(CASE
            WHEN gl.Debit > 0 AND a.AccountNumber <> '2040' THEN gl.Debit
            ELSE 0
        END), 2) AS AccruedAmount
    FROM JournalEntry AS je
    JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'JournalEntry'
       AND gl.SourceDocumentID = je.JournalEntryID
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE je.EntryType = 'Accrual'
    GROUP BY je.JournalEntryID, je.EntryNumber, date(je.PostingDate)
),
invoice_line_posting AS (
    SELECT
        gl.SourceDocumentID AS PurchaseInvoiceID,
        CAST(gl.SourceLineID AS INTEGER) AS PILineID,
        ROUND(SUM(CASE
            WHEN a.AccountNumber = '2040' THEN gl.Debit
            ELSE 0
        END), 2) AS InvoiceClears2040Amount,
        ROUND(SUM(CASE
            WHEN gl.Debit > 0 AND a.AccountNumber NOT IN ('2010', '2040') THEN gl.Debit
            ELSE 0
        END), 2) AS InvoiceAdditionalExpenseAmount,
        GROUP_CONCAT(DISTINCT CASE
            WHEN gl.Debit > 0 THEN a.AccountNumber || ' ' || a.AccountName
        END) AS InvoiceDebitAccounts
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE gl.SourceDocumentType = 'PurchaseInvoice'
      AND gl.SourceLineID IS NOT NULL
    GROUP BY gl.SourceDocumentID, CAST(gl.SourceLineID AS INTEGER)
),
invoice_header_posting AS (
    SELECT
        gl.SourceDocumentID AS PurchaseInvoiceID,
        ROUND(SUM(CASE
            WHEN a.AccountNumber = '2010' THEN gl.Credit
            ELSE 0
        END), 2) AS InvoiceHeaderAPAmount,
        GROUP_CONCAT(DISTINCT CASE
            WHEN a.AccountNumber = '2010' THEN a.AccountNumber || ' ' || a.AccountName
        END) AS InvoiceCreditAccounts
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE gl.SourceDocumentType = 'PurchaseInvoice'
    GROUP BY gl.SourceDocumentID
),
adjustment_posting AS (
    SELECT
        je.ReversesJournalEntryID AS JournalEntryID,
        GROUP_CONCAT(DISTINCT je.EntryNumber) AS AdjustmentEntryNumbers,
        MIN(date(je.PostingDate)) AS FirstAdjustmentDate,
        ROUND(SUM(CASE
            WHEN a.AccountNumber = '2040' THEN gl.Debit
            ELSE 0
        END), 2) AS AdjustmentAmount,
        GROUP_CONCAT(DISTINCT CASE
            WHEN gl.Debit > 0 THEN a.AccountNumber || ' ' || a.AccountName
        END) AS AdjustmentDebitAccounts,
        GROUP_CONCAT(DISTINCT CASE
            WHEN gl.Credit > 0 THEN a.AccountNumber || ' ' || a.AccountName
        END) AS AdjustmentCreditAccounts
    FROM JournalEntry AS je
    JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'JournalEntry'
       AND gl.SourceDocumentID = je.JournalEntryID
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE je.EntryType = 'Accrual Adjustment'
      AND je.ReversesJournalEntryID IS NOT NULL
    GROUP BY je.ReversesJournalEntryID
),
payment_summary AS (
    SELECT
        dp.PurchaseInvoiceID,
        MIN(date(dp.PaymentDate)) AS FirstPaymentDate,
        ROUND(SUM(dp.Amount), 2) AS PaidAmount
    FROM DisbursementPayment AS dp
    GROUP BY dp.PurchaseInvoiceID
),
payment_posting AS (
    SELECT
        dp.PurchaseInvoiceID,
        ROUND(SUM(CASE
            WHEN a.AccountNumber = '2010' THEN gl.Debit
            ELSE 0
        END), 2) AS PaymentClearsAPAmount,
        GROUP_CONCAT(DISTINCT CASE
            WHEN gl.Credit > 0 THEN a.AccountNumber || ' ' || a.AccountName
        END) AS PaymentCreditAccounts
    FROM DisbursementPayment AS dp
    LEFT JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'DisbursementPayment'
       AND gl.SourceDocumentID = dp.DisbursementID
    LEFT JOIN Account AS a
        ON a.AccountID = gl.AccountID
    GROUP BY dp.PurchaseInvoiceID
)
SELECT
    aa.EntryNumber AS AccrualEntryNumber,
    aa.AccrualDate,
    aa.ExpenseAccountNumber,
    aa.ExpenseAccountName,
    ROUND(aa.AccruedAmount, 2) AS AccruedAmount,
    pi.InvoiceNumber,
    date(pi.InvoiceDate) AS InvoiceDate,
    s.SupplierName,
    pil.PILineID,
    i.ItemCode,
    i.ItemName,
    ROUND(pil.LineTotal, 2) AS InvoiceLineAmount,
    ROUND(pil.LineTotal - aa.AccruedAmount, 2) AS InvoiceMinusAccrualAmount,
    COALESCE(ilp.InvoiceClears2040Amount, 0) AS InvoiceClears2040Amount,
    COALESCE(ilp.InvoiceAdditionalExpenseAmount, 0) AS InvoiceAdditionalExpenseAmount,
    COALESCE(ihp.InvoiceHeaderAPAmount, 0) AS InvoiceHeaderAPAmount,
    adj.AdjustmentEntryNumbers,
    adj.FirstAdjustmentDate,
    COALESCE(adj.AdjustmentAmount, 0) AS AdjustmentAmount,
    ilp.InvoiceDebitAccounts,
    ihp.InvoiceCreditAccounts,
    adj.AdjustmentDebitAccounts,
    adj.AdjustmentCreditAccounts,
    CAST(julianday(pi.InvoiceDate) - julianday(aa.AccrualDate) AS INTEGER) AS DaysToInvoice,
    ps.FirstPaymentDate,
    CASE
        WHEN ps.FirstPaymentDate IS NULL THEN NULL
        ELSE CAST(julianday(ps.FirstPaymentDate) - julianday(aa.AccrualDate) AS INTEGER)
    END AS DaysToFirstPayment,
    ROUND(COALESCE(ps.PaidAmount, 0), 2) AS PaidAmount,
    ROUND(COALESCE(pp.PaymentClearsAPAmount, 0), 2) AS PaymentClearsAPAmount,
    pp.PaymentCreditAccounts
FROM PurchaseInvoiceLine AS pil
JOIN PurchaseInvoice AS pi
    ON pi.PurchaseInvoiceID = pil.PurchaseInvoiceID
JOIN Supplier AS s
    ON s.SupplierID = pi.SupplierID
JOIN Item AS i
    ON i.ItemID = pil.ItemID
JOIN accrual_amounts AS aa
    ON aa.JournalEntryID = pil.AccrualJournalEntryID
LEFT JOIN invoice_line_posting AS ilp
    ON ilp.PurchaseInvoiceID = pi.PurchaseInvoiceID
   AND ilp.PILineID = pil.PILineID
LEFT JOIN invoice_header_posting AS ihp
    ON ihp.PurchaseInvoiceID = pi.PurchaseInvoiceID
LEFT JOIN adjustment_posting AS adj
    ON adj.JournalEntryID = aa.JournalEntryID
LEFT JOIN payment_summary AS ps
    ON ps.PurchaseInvoiceID = pi.PurchaseInvoiceID
LEFT JOIN payment_posting AS pp
    ON pp.PurchaseInvoiceID = pi.PurchaseInvoiceID
WHERE pil.AccrualJournalEntryID IS NOT NULL
ORDER BY
    aa.AccrualDate,
    aa.ExpenseAccountNumber,
    pi.InvoiceDate,
    pi.InvoiceNumber,
    pil.PILineID;
