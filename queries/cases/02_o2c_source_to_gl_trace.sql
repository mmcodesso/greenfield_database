-- Teaching objective: Tie shipment and invoice source rows back to posted GL activity.
-- Main tables: Shipment, ShipmentLine, SalesInvoice, SalesInvoiceLine, GLEntry, Account, SalesOrder, Customer.
-- Expected output shape: One row per shipment or invoice source line and related GL posting row.
-- Interpretation notes: Shipment rows should explain inventory, COGS, and outbound-freight accrual postings; invoice rows should explain merchandise revenue, billed freight, tax, and AR postings.

WITH shipment_trace AS (
    SELECT
        'Shipment' AS SourceEvent,
        'Line' AS TraceLevel,
        so.SalesOrderID,
        so.OrderNumber,
        c.CustomerName,
        sh.ShipmentNumber AS SourceDocumentNumber,
        date(sh.ShipmentDate) AS SourceEventDate,
        sh.ShipmentID AS SourceDocumentID,
        shl.ShipmentLineID AS SourceLineID,
        shl.SalesOrderLineID,
        gl.GLEntryID,
        date(gl.PostingDate) AS GLPostingDate,
        gl.VoucherType,
        gl.VoucherNumber,
        a.AccountNumber,
        a.AccountName,
        ROUND(gl.Debit, 2) AS Debit,
        ROUND(gl.Credit, 2) AS Credit,
        gl.FiscalYear,
        gl.FiscalPeriod
    FROM ShipmentLine AS shl
    JOIN Shipment AS sh
        ON sh.ShipmentID = shl.ShipmentID
    JOIN SalesOrder AS so
        ON so.SalesOrderID = sh.SalesOrderID
    JOIN Customer AS c
        ON c.CustomerID = so.CustomerID
    LEFT JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'Shipment'
       AND gl.SourceDocumentID = sh.ShipmentID
       AND gl.SourceLineID = shl.ShipmentLineID
    LEFT JOIN Account AS a
        ON a.AccountID = gl.AccountID
),
shipment_header_trace AS (
    SELECT
        'Shipment' AS SourceEvent,
        'Header' AS TraceLevel,
        so.SalesOrderID,
        so.OrderNumber,
        c.CustomerName,
        sh.ShipmentNumber AS SourceDocumentNumber,
        date(sh.ShipmentDate) AS SourceEventDate,
        sh.ShipmentID AS SourceDocumentID,
        NULL AS SourceLineID,
        NULL AS SalesOrderLineID,
        gl.GLEntryID,
        date(gl.PostingDate) AS GLPostingDate,
        gl.VoucherType,
        gl.VoucherNumber,
        a.AccountNumber,
        a.AccountName,
        ROUND(gl.Debit, 2) AS Debit,
        ROUND(gl.Credit, 2) AS Credit,
        gl.FiscalYear,
        gl.FiscalPeriod
    FROM Shipment AS sh
    JOIN SalesOrder AS so
        ON so.SalesOrderID = sh.SalesOrderID
    JOIN Customer AS c
        ON c.CustomerID = so.CustomerID
    LEFT JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'Shipment'
       AND gl.SourceDocumentID = sh.ShipmentID
       AND gl.SourceLineID IS NULL
    LEFT JOIN Account AS a
        ON a.AccountID = gl.AccountID
),
invoice_trace AS (
    SELECT
        'SalesInvoice' AS SourceEvent,
        'Line' AS TraceLevel,
        so.SalesOrderID,
        so.OrderNumber,
        c.CustomerName,
        si.InvoiceNumber AS SourceDocumentNumber,
        date(si.InvoiceDate) AS SourceEventDate,
        si.SalesInvoiceID AS SourceDocumentID,
        sil.SalesInvoiceLineID AS SourceLineID,
        sil.SalesOrderLineID,
        gl.GLEntryID,
        date(gl.PostingDate) AS GLPostingDate,
        gl.VoucherType,
        gl.VoucherNumber,
        a.AccountNumber,
        a.AccountName,
        ROUND(gl.Debit, 2) AS Debit,
        ROUND(gl.Credit, 2) AS Credit,
        gl.FiscalYear,
        gl.FiscalPeriod
    FROM SalesInvoiceLine AS sil
    JOIN SalesInvoice AS si
        ON si.SalesInvoiceID = sil.SalesInvoiceID
    JOIN SalesOrder AS so
        ON so.SalesOrderID = si.SalesOrderID
    JOIN Customer AS c
        ON c.CustomerID = si.CustomerID
    LEFT JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'SalesInvoice'
       AND gl.SourceDocumentID = si.SalesInvoiceID
       AND gl.SourceLineID = sil.SalesInvoiceLineID
    LEFT JOIN Account AS a
        ON a.AccountID = gl.AccountID
),
invoice_header_trace AS (
    SELECT
        'SalesInvoice' AS SourceEvent,
        'Header' AS TraceLevel,
        so.SalesOrderID,
        so.OrderNumber,
        c.CustomerName,
        si.InvoiceNumber AS SourceDocumentNumber,
        date(si.InvoiceDate) AS SourceEventDate,
        si.SalesInvoiceID AS SourceDocumentID,
        NULL AS SourceLineID,
        NULL AS SalesOrderLineID,
        gl.GLEntryID,
        date(gl.PostingDate) AS GLPostingDate,
        gl.VoucherType,
        gl.VoucherNumber,
        a.AccountNumber,
        a.AccountName,
        ROUND(gl.Debit, 2) AS Debit,
        ROUND(gl.Credit, 2) AS Credit,
        gl.FiscalYear,
        gl.FiscalPeriod
    FROM SalesInvoice AS si
    JOIN SalesOrder AS so
        ON so.SalesOrderID = si.SalesOrderID
    JOIN Customer AS c
        ON c.CustomerID = si.CustomerID
    LEFT JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'SalesInvoice'
       AND gl.SourceDocumentID = si.SalesInvoiceID
       AND gl.SourceLineID IS NULL
    LEFT JOIN Account AS a
        ON a.AccountID = gl.AccountID
)
SELECT
    SourceEvent,
    TraceLevel,
    SalesOrderID,
    OrderNumber,
    CustomerName,
    SourceDocumentNumber,
    SourceEventDate,
    SourceDocumentID,
    SourceLineID,
    SalesOrderLineID,
    GLEntryID,
    GLPostingDate,
    VoucherType,
    VoucherNumber,
    AccountNumber,
    AccountName,
    Debit,
    Credit,
    FiscalYear,
    FiscalPeriod
FROM shipment_trace

UNION ALL

SELECT
    SourceEvent,
    TraceLevel,
    SalesOrderID,
    OrderNumber,
    CustomerName,
    SourceDocumentNumber,
    SourceEventDate,
    SourceDocumentID,
    SourceLineID,
    SalesOrderLineID,
    GLEntryID,
    GLPostingDate,
    VoucherType,
    VoucherNumber,
    AccountNumber,
    AccountName,
    Debit,
    Credit,
    FiscalYear,
    FiscalPeriod
FROM shipment_header_trace

UNION ALL

SELECT
    SourceEvent,
    TraceLevel,
    SalesOrderID,
    OrderNumber,
    CustomerName,
    SourceDocumentNumber,
    SourceEventDate,
    SourceDocumentID,
    SourceLineID,
    SalesOrderLineID,
    GLEntryID,
    GLPostingDate,
    VoucherType,
    VoucherNumber,
    AccountNumber,
    AccountName,
    Debit,
    Credit,
    FiscalYear,
    FiscalPeriod
FROM invoice_trace

UNION ALL

SELECT
    SourceEvent,
    TraceLevel,
    SalesOrderID,
    OrderNumber,
    CustomerName,
    SourceDocumentNumber,
    SourceEventDate,
    SourceDocumentID,
    SourceLineID,
    SalesOrderLineID,
    GLEntryID,
    GLPostingDate,
    VoucherType,
    VoucherNumber,
    AccountNumber,
    AccountName,
    Debit,
    Credit,
    FiscalYear,
    FiscalPeriod
FROM invoice_header_trace
ORDER BY OrderNumber, SourceEventDate, SourceEvent, SourceDocumentNumber, GLEntryID;
