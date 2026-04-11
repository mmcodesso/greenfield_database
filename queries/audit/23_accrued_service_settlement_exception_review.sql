-- Teaching objective: Review direct service invoices that clear prior accruals and identify timing or amount exceptions.
-- Main tables: JournalEntry, PurchaseInvoice, PurchaseInvoiceLine, DisbursementPayment, Supplier, Item.
-- Expected output shape: One row per accrued-service invoice line with timing, payment, and amount-difference flags.
-- Recommended build mode: Either.
-- Interpretation notes: This review is for accrued-service settlement lines only, not receipt-matched inventory invoices.

WITH accrual_headers AS (
    SELECT
        je.JournalEntryID,
        je.EntryNumber,
        date(je.PostingDate) AS AccrualDate,
        ROUND(je.TotalAmount, 2) AS AccrualAmount
    FROM JournalEntry AS je
    WHERE je.EntryType = 'Accrual'
),
invoice_payment_summary AS (
    SELECT
        PurchaseInvoiceID,
        ROUND(SUM(Amount), 2) AS PaidAmount,
        MIN(date(PaymentDate)) AS FirstPaymentDate
    FROM DisbursementPayment
    GROUP BY PurchaseInvoiceID
),
snapshot AS (
    SELECT MAX(date(InvoiceDate)) AS SnapshotDate
    FROM PurchaseInvoice
)
SELECT
    ah.EntryNumber AS AccrualEntryNumber,
    ah.AccrualDate,
    pi.InvoiceNumber,
    date(pi.InvoiceDate) AS InvoiceDate,
    s.SupplierName,
    i.ItemCode,
    i.ItemName,
    ROUND(ah.AccrualAmount, 2) AS AccrualAmount,
    ROUND(pil.LineTotal, 2) AS InvoiceLineAmount,
    ROUND(pil.LineTotal - ah.AccrualAmount, 2) AS InvoiceMinusAccrualAmount,
    ips.FirstPaymentDate,
    ROUND(COALESCE(ips.PaidAmount, 0), 2) AS PaidAmount,
    ROUND(julianday(date(pi.InvoiceDate)) - julianday(ah.AccrualDate), 2) AS DaysFromAccrualToInvoice,
    CASE
        WHEN date(pi.InvoiceDate) < ah.AccrualDate
            THEN 'Invoice dated before the linked accrual'
        WHEN ABS(pil.LineTotal - ah.AccrualAmount) > ROUND(ah.AccrualAmount * 0.05, 2)
            THEN 'Invoice amount differs from accrual by more than 5%'
        WHEN COALESCE(ips.PaidAmount, 0) = 0
         AND julianday((SELECT SnapshotDate FROM snapshot)) - julianday(date(pi.InvoiceDate)) > 45
            THEN 'Accrued-service invoice remains unpaid after 45 days'
        ELSE 'Review accrued-service settlement'
    END AS PotentialIssue
FROM PurchaseInvoiceLine AS pil
JOIN PurchaseInvoice AS pi
    ON pi.PurchaseInvoiceID = pil.PurchaseInvoiceID
JOIN accrual_headers AS ah
    ON ah.JournalEntryID = pil.AccrualJournalEntryID
JOIN Supplier AS s
    ON s.SupplierID = pi.SupplierID
JOIN Item AS i
    ON i.ItemID = pil.ItemID
LEFT JOIN invoice_payment_summary AS ips
    ON ips.PurchaseInvoiceID = pi.PurchaseInvoiceID
WHERE pil.AccrualJournalEntryID IS NOT NULL
ORDER BY ah.AccrualDate, pi.InvoiceNumber, pil.PILineID;
