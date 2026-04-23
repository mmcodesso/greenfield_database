-- Teaching objective: Trace invoice-level revenue cutoff exceptions from order and shipment source lines into the posted revenue GL rows.
-- Main tables: SalesOrder, SalesOrderLine, Shipment, ShipmentLine, SalesInvoice, SalesInvoiceLine, GLEntry, Account, Item, Customer.
-- Expected output shape: One row per exception invoice line and related operating-revenue GL row, including trace classifications and line-to-GL variances.
-- Recommended build mode: Run after financial/43_invoice_revenue_cutoff_exception_summary.sql on both clean and anomaly datasets.
-- Interpretation notes: Clean builds should return no rows. In the default anomaly build, the trace should show invoice dates moved before shipment while the revenue GL still posts by operational posting date in the next fiscal year.

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
exception_invoices AS (
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
        CASE
            WHEN rg.SalesInvoiceID IS NULL THEN 1
            WHEN COALESCE(rg.RevenueGlLineCount, 0) <> COALESCE(ilr.InvoiceLineCount, 0) THEN 1
            WHEN ABS(COALESCE(rg.RevenueAmount, 0) - COALESCE(ilr.InvoiceSubTotal, 0)) > 0.005 THEN 1
            ELSE 0
        END AS RevenueGlIncompleteFlag,
        CASE
            WHEN rg.SalesInvoiceID IS NULL THEN 'posting defect'
            WHEN COALESCE(rg.RevenueGlLineCount, 0) <> COALESCE(ilr.InvoiceLineCount, 0) THEN 'posting defect'
            WHEN ABS(COALESCE(rg.RevenueAmount, 0) - COALESCE(ilr.InvoiceSubTotal, 0)) > 0.005 THEN 'posting defect'
            WHEN sb.FirstShipmentDate IS NOT NULL
             AND date(si.InvoiceDate) < date(sb.FirstShipmentDate)
             AND rg.RevenueGlFiscalYear IS NOT NULL
             AND CAST(substr(si.InvoiceDate, 1, 4) AS INTEGER) <> rg.RevenueGlFiscalYear
                THEN 'seeded anomaly'
            WHEN rg.RevenueGlFiscalYear IS NOT NULL
             AND CAST(substr(si.InvoiceDate, 1, 4) AS INTEGER) <> rg.RevenueGlFiscalYear
                THEN 'posting defect'
            WHEN sb.FirstShipmentDate IS NOT NULL
             AND date(si.InvoiceDate) < date(sb.FirstShipmentDate)
                THEN 'clean-process defect'
            ELSE 'statement query defect'
        END AS ExceptionType
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
    WHERE (
        CASE
            WHEN rg.RevenueGlFiscalYear IS NOT NULL
             AND CAST(substr(si.InvoiceDate, 1, 4) AS INTEGER) <> rg.RevenueGlFiscalYear
                THEN 1
            WHEN rg.RevenueGlFiscalYearMin IS NOT NULL
             AND rg.RevenueGlFiscalYearMin <> rg.RevenueGlFiscalYearMax
                THEN 1
            ELSE 0
        END
    ) = 1
       OR (
            CASE
                WHEN rg.SalesInvoiceID IS NULL THEN 1
                WHEN COALESCE(rg.RevenueGlLineCount, 0) <> COALESCE(ilr.InvoiceLineCount, 0) THEN 1
                WHEN ABS(COALESCE(rg.RevenueAmount, 0) - COALESCE(ilr.InvoiceSubTotal, 0)) > 0.005 THEN 1
                ELSE 0
            END
       ) = 1
),
line_trace AS (
    SELECT
        ex.SalesInvoiceID,
        ex.InvoiceNumber,
        ex.SalesOrderID,
        ex.OrderNumber,
        ex.CustomerName,
        ex.InvoiceDate,
        ex.InvoiceYear,
        ex.FirstShipmentDate,
        ex.LastShipmentDate,
        ex.RevenuePostingDateMin,
        ex.RevenuePostingDateMax,
        ex.RevenueGlFiscalYear,
        ex.InvoiceBeforeShipmentFlag,
        ex.InvoiceYearVsGlYearFlag,
        ex.RevenueGlIncompleteFlag,
        ex.ExceptionType,
        sol.SalesOrderLineID,
        sol.LineNumber AS SalesOrderLineNumber,
        date(so.OrderDate) AS OrderDate,
        sh.ShipmentID,
        sh.ShipmentNumber,
        date(sh.ShipmentDate) AS ShipmentDate,
        shl.ShipmentLineID,
        shl.LineNumber AS ShipmentLineNumber,
        sil.SalesInvoiceLineID,
        sil.LineNumber AS SalesInvoiceLineNumber,
        sil.ItemID,
        i.ItemCode,
        i.ItemName,
        ROUND(sol.Quantity, 2) AS OrderedQuantity,
        ROUND(shl.QuantityShipped, 2) AS QuantityShipped,
        ROUND(sil.Quantity, 2) AS QuantityInvoiced,
        ROUND(sil.LineTotal, 2) AS InvoiceLineTotal,
        gl.GLEntryID,
        date(gl.PostingDate) AS GLPostingDate,
        gl.FiscalYear,
        gl.FiscalPeriod,
        a.AccountNumber,
        a.AccountName,
        ROUND(COALESCE(gl.Debit, 0), 2) AS Debit,
        ROUND(COALESCE(gl.Credit, 0), 2) AS Credit
    FROM exception_invoices AS ex
    JOIN SalesInvoiceLine AS sil
        ON sil.SalesInvoiceID = ex.SalesInvoiceID
    JOIN SalesOrderLine AS sol
        ON sol.SalesOrderLineID = sil.SalesOrderLineID
    JOIN SalesOrder AS so
        ON so.SalesOrderID = ex.SalesOrderID
    LEFT JOIN ShipmentLine AS shl
        ON shl.ShipmentLineID = sil.ShipmentLineID
    LEFT JOIN Shipment AS sh
        ON sh.ShipmentID = shl.ShipmentID
    JOIN Item AS i
        ON i.ItemID = sil.ItemID
    LEFT JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'SalesInvoice'
       AND gl.SourceDocumentID = sil.SalesInvoiceID
       AND CAST(gl.SourceLineID AS INTEGER) = sil.SalesInvoiceLineID
    LEFT JOIN Account AS a
        ON a.AccountID = gl.AccountID
       AND a.AccountType = 'Revenue'
       AND a.AccountSubType = 'Operating Revenue'
    WHERE gl.GLEntryID IS NULL
       OR a.AccountID IS NOT NULL
)
SELECT
    SalesInvoiceID,
    InvoiceNumber,
    SalesOrderID,
    OrderNumber,
    CustomerName,
    OrderDate,
    InvoiceDate,
    InvoiceYear,
    FirstShipmentDate,
    LastShipmentDate,
    RevenuePostingDateMin,
    RevenuePostingDateMax,
    RevenueGlFiscalYear,
    InvoiceBeforeShipmentFlag,
    InvoiceYearVsGlYearFlag,
    RevenueGlIncompleteFlag,
    ExceptionType,
    SalesOrderLineID,
    SalesOrderLineNumber,
    ShipmentID,
    ShipmentNumber,
    ShipmentDate,
    ShipmentLineID,
    ShipmentLineNumber,
    SalesInvoiceLineID,
    SalesInvoiceLineNumber,
    ItemID,
    ItemCode,
    ItemName,
    OrderedQuantity,
    QuantityShipped,
    QuantityInvoiced,
    InvoiceLineTotal,
    GLEntryID,
    GLPostingDate,
    FiscalYear,
    FiscalPeriod,
    AccountNumber,
    AccountName,
    Debit,
    Credit,
    ROUND(SUM(COALESCE(Credit - Debit, 0)) OVER (PARTITION BY SalesInvoiceLineID), 2) AS RevenueGlAmountForInvoiceLine,
    ROUND(
        InvoiceLineTotal - SUM(COALESCE(Credit - Debit, 0)) OVER (PARTITION BY SalesInvoiceLineID),
        2
    ) AS InvoiceLineToRevenueGlVariance,
    CASE
        WHEN GLEntryID IS NULL THEN 'posting defect'
        WHEN ABS(
            InvoiceLineTotal - SUM(COALESCE(Credit - Debit, 0)) OVER (PARTITION BY SalesInvoiceLineID)
        ) > 0.005 THEN 'posting defect'
        WHEN ExceptionType = 'seeded anomaly' THEN 'seeded anomaly'
        WHEN ExceptionType = 'posting defect' THEN 'posting defect'
        WHEN ExceptionType = 'clean-process defect' THEN 'clean-process defect'
        ELSE 'statement query defect'
    END AS TraceClassification
FROM line_trace
ORDER BY InvoiceYear, RevenueGlFiscalYear, InvoiceNumber, SalesInvoiceLineNumber, GLEntryID;
