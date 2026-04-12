-- Teaching objective: Compare how quickly Greenfield turns sales invoices, purchase invoices, and goods receipts into cash settlement events.
-- Main tables: SalesInvoice, CashReceiptApplication, PurchaseInvoice, DisbursementPayment, GoodsReceipt, GoodsReceiptLine, PurchaseInvoiceLine.
-- Expected output shape: One row per source-month and timing metric family.
-- Recommended build mode: Either; the default build usually produces a wider spread of timing patterns.
-- Interpretation notes: Sales timing uses invoice to first cash application, AP timing uses invoice to first payment, and receipt timing uses goods receipt to first linked supplier payment.

WITH ar_source AS (
    SELECT
        'Sales Invoice to First Application' AS MetricFamily,
        date(si.InvoiceDate) AS SourceDate,
        si.SalesInvoiceID AS DocumentID,
        MIN(date(cra.ApplicationDate)) AS SettlementDate
    FROM SalesInvoice AS si
    LEFT JOIN CashReceiptApplication AS cra
        ON cra.SalesInvoiceID = si.SalesInvoiceID
    GROUP BY
        si.SalesInvoiceID,
        date(si.InvoiceDate)
),
ap_source AS (
    SELECT
        'Purchase Invoice to First Payment' AS MetricFamily,
        date(pi.InvoiceDate) AS SourceDate,
        pi.PurchaseInvoiceID AS DocumentID,
        MIN(date(dp.PaymentDate)) AS SettlementDate
    FROM PurchaseInvoice AS pi
    LEFT JOIN DisbursementPayment AS dp
        ON dp.PurchaseInvoiceID = pi.PurchaseInvoiceID
    GROUP BY
        pi.PurchaseInvoiceID,
        date(pi.InvoiceDate)
),
receipt_source AS (
    SELECT
        'Goods Receipt to First Payment' AS MetricFamily,
        date(gr.ReceiptDate) AS SourceDate,
        gr.GoodsReceiptID AS DocumentID,
        MIN(date(dp.PaymentDate)) AS SettlementDate
    FROM GoodsReceipt AS gr
    JOIN GoodsReceiptLine AS grl
        ON grl.GoodsReceiptID = gr.GoodsReceiptID
    LEFT JOIN PurchaseInvoiceLine AS pil
        ON pil.GoodsReceiptLineID = grl.GoodsReceiptLineID
    LEFT JOIN PurchaseInvoice AS pi
        ON pi.PurchaseInvoiceID = pil.PurchaseInvoiceID
    LEFT JOIN DisbursementPayment AS dp
        ON dp.PurchaseInvoiceID = pi.PurchaseInvoiceID
    GROUP BY
        gr.GoodsReceiptID,
        date(gr.ReceiptDate)
),
timing_sources AS (
    SELECT * FROM ar_source
    UNION ALL
    SELECT * FROM ap_source
    UNION ALL
    SELECT * FROM receipt_source
)
SELECT
    MetricFamily,
    CAST(strftime('%Y', SourceDate) AS INTEGER) AS FiscalYear,
    CAST(strftime('%m', SourceDate) AS INTEGER) AS FiscalPeriod,
    COUNT(*) AS DocumentCount,
    SUM(CASE WHEN SettlementDate IS NOT NULL THEN 1 ELSE 0 END) AS SettledDocumentCount,
    SUM(CASE WHEN SettlementDate IS NULL THEN 1 ELSE 0 END) AS OpenDocumentCount,
    ROUND(AVG(CASE WHEN SettlementDate IS NOT NULL THEN julianday(SettlementDate) - julianday(SourceDate) END), 2) AS AvgDaysToFirstSettlement,
    ROUND(MAX(CASE WHEN SettlementDate IS NOT NULL THEN julianday(SettlementDate) - julianday(SourceDate) END), 2) AS MaxDaysToFirstSettlement
FROM timing_sources
GROUP BY
    MetricFamily,
    CAST(strftime('%Y', SourceDate) AS INTEGER),
    CAST(strftime('%m', SourceDate) AS INTEGER)
ORDER BY
    MetricFamily,
    FiscalYear,
    FiscalPeriod;
