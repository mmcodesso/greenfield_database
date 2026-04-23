-- Teaching objective: Isolate invoice-level revenue cutoff exceptions that move operational invoice revenue into a different GL fiscal year.
-- Main tables: SalesInvoice, SalesInvoiceLine, Shipment, ShipmentLine, GLEntry, Account, SalesOrder, Customer.
-- Expected output shape: One row per exception invoice header with shipment timing, revenue GL posting year, and root-cause classification fields.
-- Recommended build mode: Compare the clean reconciliation build against the default anomaly build; the clean build should return no rows.
-- Interpretation notes: This query narrows the broader invoice-before-shipment population to the invoices that impact annual revenue reconciliation or show incomplete revenue posting. Use audit/06_potential_anomaly_review.sql for the broader timing scan.

WITH invoice_shipment_bounds AS (
    SELECT
        sil.SalesInvoiceID,
        MIN(date(sh.ShipmentDate)) AS FirstShipmentDate,
        MAX(date(sh.ShipmentDate)) AS LastShipmentDate,
        COUNT(DISTINCT sil.SalesInvoiceLineID) AS ShipmentBackedLineCount
    FROM SalesInvoiceLine AS sil
    JOIN ShipmentLine AS shl
        ON shl.ShipmentLineID = sil.ShipmentLineID
    JOIN Shipment AS sh
        ON sh.ShipmentID = shl.ShipmentID
    GROUP BY sil.SalesInvoiceID
),
invoice_line_rollup AS (
    SELECT
        SalesInvoiceID,
        COUNT(DISTINCT SalesInvoiceLineID) AS InvoiceLineCount,
        ROUND(SUM(LineTotal), 2) AS InvoiceSubTotal
    FROM SalesInvoiceLine
    GROUP BY SalesInvoiceID
),
invoice_revenue_gl AS (
    SELECT
        gl.SourceDocumentID AS SalesInvoiceID,
        MIN(date(gl.PostingDate)) AS RevenuePostingDateMin,
        MAX(date(gl.PostingDate)) AS RevenuePostingDateMax,
        MIN(gl.FiscalYear) AS RevenueGlFiscalYearMin,
        MAX(gl.FiscalYear) AS RevenueGlFiscalYearMax,
        CASE
            WHEN MIN(gl.FiscalYear) = MAX(gl.FiscalYear) THEN MIN(gl.FiscalYear)
            ELSE NULL
        END AS RevenueGlFiscalYear,
        COUNT(*) AS RevenueGlEntryCount,
        COUNT(DISTINCT CAST(gl.SourceLineID AS INTEGER)) AS RevenueGlLineCount,
        ROUND(SUM(gl.Credit - gl.Debit), 2) AS RevenueAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE gl.SourceDocumentType = 'SalesInvoice'
      AND gl.SourceDocumentID IS NOT NULL
      AND gl.SourceLineID IS NOT NULL
      AND a.AccountType = 'Revenue'
      AND a.AccountSubType = 'Operating Revenue'
    GROUP BY gl.SourceDocumentID
),
invoice_ar_gl AS (
    SELECT
        gl.SourceDocumentID AS SalesInvoiceID,
        ROUND(SUM(gl.Debit - gl.Credit), 2) AS ArHeaderAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE gl.SourceDocumentType = 'SalesInvoice'
      AND gl.SourceDocumentID IS NOT NULL
      AND gl.SourceLineID IS NULL
      AND CAST(a.AccountNumber AS INTEGER) = 1020
    GROUP BY gl.SourceDocumentID
),
invoice_exception_base AS (
    SELECT
        si.SalesInvoiceID,
        si.InvoiceNumber,
        si.SalesOrderID,
        so.OrderNumber,
        c.CustomerName,
        date(si.InvoiceDate) AS InvoiceDate,
        CAST(substr(si.InvoiceDate, 1, 4) AS INTEGER) AS InvoiceYear,
        sb.FirstShipmentDate,
        sb.LastShipmentDate,
        rg.RevenuePostingDateMin,
        rg.RevenuePostingDateMax,
        rg.RevenueGlFiscalYear,
        ROUND(COALESCE(rg.RevenueAmount, 0), 2) AS RevenueAmount,
        ROUND(COALESCE(ar.ArHeaderAmount, 0), 2) AS ArHeaderAmount,
        CAST(julianday(si.InvoiceDate) - julianday(sb.FirstShipmentDate) AS INTEGER) AS ShipmentToInvoiceDayGap,
        COALESCE(ilr.InvoiceLineCount, 0) AS InvoiceLineCount,
        COALESCE(sb.ShipmentBackedLineCount, 0) AS ShipmentBackedLineCount,
        CASE
            WHEN sb.FirstShipmentDate IS NOT NULL
             AND date(si.InvoiceDate) < date(sb.FirstShipmentDate)
                THEN 1
            ELSE 0
        END AS InvoiceBeforeShipmentFlag,
        CASE
            WHEN rg.RevenueGlFiscalYear IS NOT NULL
             AND CAST(substr(si.InvoiceDate, 1, 4) AS INTEGER) <> rg.RevenueGlFiscalYear
                THEN 1
            WHEN rg.RevenueGlFiscalYearMin IS NOT NULL
             AND rg.RevenueGlFiscalYearMin <> rg.RevenueGlFiscalYearMax
                THEN 1
            ELSE 0
        END AS InvoiceYearVsGlYearFlag,
        ROUND(COALESCE(ilr.InvoiceSubTotal, 0), 2) AS InvoiceSubTotal,
        ROUND(si.GrandTotal, 2) AS InvoiceGrandTotal,
        COALESCE(rg.RevenueGlLineCount, 0) AS RevenueGlLineCount,
        CASE
            WHEN rg.SalesInvoiceID IS NULL THEN 1
            WHEN COALESCE(rg.RevenueGlLineCount, 0) <> COALESCE(ilr.InvoiceLineCount, 0) THEN 1
            WHEN ABS(COALESCE(rg.RevenueAmount, 0) - COALESCE(ilr.InvoiceSubTotal, 0)) > 0.005 THEN 1
            ELSE 0
        END AS RevenueGlIncompleteFlag,
        ROUND(COALESCE(rg.RevenueAmount, 0) - COALESCE(ilr.InvoiceSubTotal, 0), 2) AS RevenueAmountLessInvoiceSubTotalVariance,
        ROUND(COALESCE(ar.ArHeaderAmount, 0) - ROUND(si.GrandTotal, 2), 2) AS ArHeaderLessInvoiceGrandTotalVariance
    FROM SalesInvoice AS si
    JOIN SalesOrder AS so
        ON so.SalesOrderID = si.SalesOrderID
    JOIN Customer AS c
        ON c.CustomerID = si.CustomerID
    LEFT JOIN invoice_line_rollup AS ilr
        ON ilr.SalesInvoiceID = si.SalesInvoiceID
    LEFT JOIN invoice_shipment_bounds AS sb
        ON sb.SalesInvoiceID = si.SalesInvoiceID
    LEFT JOIN invoice_revenue_gl AS rg
        ON rg.SalesInvoiceID = si.SalesInvoiceID
    LEFT JOIN invoice_ar_gl AS ar
        ON ar.SalesInvoiceID = si.SalesInvoiceID
)
SELECT
    SalesInvoiceID,
    InvoiceNumber,
    SalesOrderID,
    OrderNumber,
    CustomerName,
    InvoiceDate,
    InvoiceYear,
    FirstShipmentDate,
    LastShipmentDate,
    RevenuePostingDateMin,
    RevenuePostingDateMax,
    RevenueGlFiscalYear,
    RevenueAmount,
    ArHeaderAmount,
    ShipmentToInvoiceDayGap,
    InvoiceBeforeShipmentFlag,
    InvoiceYearVsGlYearFlag,
    InvoiceSubTotal,
    InvoiceGrandTotal,
    InvoiceLineCount,
    RevenueGlLineCount,
    RevenueGlIncompleteFlag,
    RevenueAmountLessInvoiceSubTotalVariance,
    ArHeaderLessInvoiceGrandTotalVariance,
    CASE
        WHEN RevenueGlIncompleteFlag = 1 THEN 'posting defect'
        WHEN InvoiceBeforeShipmentFlag = 1 AND InvoiceYearVsGlYearFlag = 1 THEN 'seeded anomaly'
        WHEN InvoiceYearVsGlYearFlag = 1 THEN 'posting defect'
        WHEN InvoiceBeforeShipmentFlag = 1 THEN 'clean-process defect'
        ELSE 'statement query defect'
    END AS ExceptionType,
    CASE
        WHEN RevenueGlIncompleteFlag = 1 THEN 'Operating-revenue GL rows are missing or do not tie to the invoice subtotal.'
        WHEN InvoiceBeforeShipmentFlag = 1 AND InvoiceYearVsGlYearFlag = 1 THEN 'Invoice date precedes shipment and the invoice year differs from the revenue GL fiscal year.'
        WHEN InvoiceYearVsGlYearFlag = 1 THEN 'Invoice year differs from the revenue GL fiscal year without an invoice-before-shipment signal.'
        WHEN InvoiceBeforeShipmentFlag = 1 THEN 'Invoice date precedes shipment, but the revenue GL still posts in the same fiscal year.'
        ELSE 'Invoice trace ties source to GL; if the annual bridge still disagrees with the income statement, investigate statement-query logic.'
    END AS ExceptionReason
FROM invoice_exception_base
WHERE InvoiceYearVsGlYearFlag = 1
   OR RevenueGlIncompleteFlag = 1
ORDER BY InvoiceYear, RevenueGlFiscalYear, InvoiceDate, InvoiceNumber;
