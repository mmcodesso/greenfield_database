-- Teaching objective: Review detailed duplicate AP reference patterns by supplier, document, and amount.
-- Main tables: PurchaseInvoice, DisbursementPayment, Supplier.
-- Expected output shape: One row per duplicated AP document reference.
-- Recommended build mode: Standard anomaly build.
-- Interpretation notes: This is a more detailed companion to the broader duplicate-reference review.

WITH duplicate_supplier_invoice_numbers AS (
    SELECT
        SupplierID,
        InvoiceNumber AS ReferenceValue,
        COUNT(*) AS DuplicateCount
    FROM PurchaseInvoice
    GROUP BY SupplierID, InvoiceNumber
    HAVING COUNT(*) > 1
),
duplicate_payment_references AS (
    SELECT
        SupplierID,
        CheckNumber AS ReferenceValue,
        COUNT(*) AS DuplicateCount
    FROM DisbursementPayment
    WHERE CheckNumber IS NOT NULL
    GROUP BY SupplierID, CheckNumber
    HAVING COUNT(*) > 1
)
SELECT
    'Duplicate supplier invoice number' AS ReviewType,
    s.SupplierName,
    pi.InvoiceNumber AS ReferenceValue,
    pi.InvoiceNumber AS DocumentNumber,
    date(pi.InvoiceDate) AS DocumentDate,
    ROUND(pi.GrandTotal, 2) AS DocumentAmount,
    dsin.DuplicateCount
FROM duplicate_supplier_invoice_numbers AS dsin
JOIN PurchaseInvoice AS pi
    ON pi.SupplierID = dsin.SupplierID
   AND pi.InvoiceNumber = dsin.ReferenceValue
JOIN Supplier AS s
    ON s.SupplierID = dsin.SupplierID

UNION ALL

SELECT
    'Duplicate supplier payment reference' AS ReviewType,
    s.SupplierName,
    dp.CheckNumber AS ReferenceValue,
    dp.PaymentNumber AS DocumentNumber,
    date(dp.PaymentDate) AS DocumentDate,
    ROUND(dp.Amount, 2) AS DocumentAmount,
    dpr.DuplicateCount
FROM duplicate_payment_references AS dpr
JOIN DisbursementPayment AS dp
    ON dp.SupplierID = dpr.SupplierID
   AND dp.CheckNumber = dpr.ReferenceValue
JOIN Supplier AS s
    ON s.SupplierID = dpr.SupplierID
ORDER BY ReviewType, SupplierName, ReferenceValue, DocumentDate, DocumentNumber;
