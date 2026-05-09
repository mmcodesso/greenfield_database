-- Teaching objective: Tie shipment, invoice, and commission source rows back to posted GL activity.
-- Main tables: Shipment, ShipmentLine, SalesInvoice, SalesInvoiceLine, SalesCommissionAccrual, SalesCommissionAdjustment, SalesCommissionPayment, GLEntry, Account, SalesOrder, Customer.
-- Expected output shape: One row per shipment or invoice source line and related GL posting row.
-- Interpretation notes: Shipment rows explain inventory, COGS, and outbound-freight accrual postings; invoice rows explain revenue, billed freight, tax, and AR postings; commission rows explain 6290 expense and 2034 payable movement.

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
),
commission_accrual_trace AS (
    SELECT
        'SalesCommissionAccrual' AS SourceEvent,
        'Line' AS TraceLevel,
        so.SalesOrderID,
        so.OrderNumber,
        c.CustomerName,
        sca.AccrualNumber AS SourceDocumentNumber,
        date(sca.AccrualDate) AS SourceEventDate,
        sca.SalesCommissionAccrualID AS SourceDocumentID,
        sca.SalesInvoiceLineID AS SourceLineID,
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
    FROM SalesCommissionAccrual AS sca
    JOIN SalesInvoiceLine AS sil
        ON sil.SalesInvoiceLineID = sca.SalesInvoiceLineID
    JOIN SalesOrder AS so
        ON so.SalesOrderID = sca.SalesOrderID
    JOIN Customer AS c
        ON c.CustomerID = sca.CustomerID
    LEFT JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'SalesCommissionAccrual'
       AND gl.SourceDocumentID = sca.SalesCommissionAccrualID
       AND gl.SourceLineID = sca.SalesInvoiceLineID
    LEFT JOIN Account AS a
        ON a.AccountID = gl.AccountID
),
commission_adjustment_trace AS (
    SELECT
        'SalesCommissionAdjustment' AS SourceEvent,
        'Line' AS TraceLevel,
        so.SalesOrderID,
        so.OrderNumber,
        c.CustomerName,
        scadj.AdjustmentNumber AS SourceDocumentNumber,
        date(scadj.AdjustmentDate) AS SourceEventDate,
        scadj.SalesCommissionAdjustmentID AS SourceDocumentID,
        scadj.CreditMemoLineID AS SourceLineID,
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
    FROM SalesCommissionAdjustment AS scadj
    JOIN SalesInvoiceLine AS sil
        ON sil.SalesInvoiceLineID = scadj.SalesInvoiceLineID
    JOIN SalesOrder AS so
        ON so.SalesOrderID = scadj.SalesOrderID
    JOIN Customer AS c
        ON c.CustomerID = scadj.CustomerID
    LEFT JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'SalesCommissionAdjustment'
       AND gl.SourceDocumentID = scadj.SalesCommissionAdjustmentID
       AND gl.SourceLineID = scadj.CreditMemoLineID
    LEFT JOIN Account AS a
        ON a.AccountID = gl.AccountID
),
commission_payment_trace AS (
    SELECT
        'SalesCommissionPayment' AS SourceEvent,
        'Header' AS TraceLevel,
        NULL AS SalesOrderID,
        NULL AS OrderNumber,
        e.EmployeeName AS CustomerName,
        scp.PaymentNumber AS SourceDocumentNumber,
        date(scp.PaymentDate) AS SourceEventDate,
        scp.SalesCommissionPaymentID AS SourceDocumentID,
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
    FROM SalesCommissionPayment AS scp
    JOIN Employee AS e
        ON e.EmployeeID = scp.SalesRepEmployeeID
    LEFT JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'SalesCommissionPayment'
       AND gl.SourceDocumentID = scp.SalesCommissionPaymentID
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
FROM commission_accrual_trace

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
FROM commission_adjustment_trace

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
FROM commission_payment_trace
ORDER BY OrderNumber, SourceEventDate, SourceEvent, SourceDocumentNumber, GLEntryID;
