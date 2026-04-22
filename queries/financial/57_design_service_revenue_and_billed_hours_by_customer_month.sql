-- Teaching objective: Review monthly billed design-service hours and posted service revenue by customer.
-- Main tables: ServiceBillingLine, SalesInvoice, SalesInvoiceLine, Customer, GLEntry, Account.
-- Expected output shape: One row per invoice month and customer.
-- Recommended build mode: Either.
-- Interpretation notes: Hours come from approved-billing rollups while revenue comes from posted `4080` sales entries.

WITH service_billing AS (
    SELECT
        si.SalesInvoiceID,
        sil.SalesInvoiceLineID,
        strftime('%Y-%m', si.InvoiceDate) AS InvoiceMonth,
        c.CustomerName,
        c.Region,
        c.CustomerSegment,
        sbl.ServiceEngagementID,
        ROUND(sbl.BilledHours, 2) AS BilledHours,
        ROUND(sbl.LineAmount, 2) AS LineAmount
    FROM ServiceBillingLine AS sbl
    JOIN SalesInvoiceLine AS sil
        ON sil.SalesInvoiceLineID = sbl.SalesInvoiceLineID
    JOIN SalesInvoice AS si
        ON si.SalesInvoiceID = sil.SalesInvoiceID
    JOIN Customer AS c
        ON c.CustomerID = si.CustomerID
),
posted_service_revenue AS (
    SELECT
        sil.SalesInvoiceLineID,
        ROUND(
            SUM(
                CASE
                    WHEN CAST(a.AccountNumber AS TEXT) = '4080'
                        THEN gl.Credit - gl.Debit
                    ELSE 0
                END
            ),
            2
        ) AS PostedServiceRevenue
    FROM SalesInvoiceLine AS sil
    JOIN SalesInvoice AS si
        ON si.SalesInvoiceID = sil.SalesInvoiceID
    LEFT JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'SalesInvoice'
       AND gl.SourceDocumentID = si.SalesInvoiceID
       AND gl.SourceLineID = sil.SalesInvoiceLineID
    LEFT JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE sil.ShipmentLineID IS NULL
    GROUP BY sil.SalesInvoiceLineID
)
SELECT
    sb.InvoiceMonth,
    sb.CustomerName,
    sb.Region,
    sb.CustomerSegment,
    COUNT(DISTINCT sb.SalesInvoiceID) AS InvoiceCount,
    COUNT(DISTINCT sb.ServiceEngagementID) AS EngagementCount,
    ROUND(SUM(sb.BilledHours), 2) AS BilledHours,
    ROUND(SUM(COALESCE(psr.PostedServiceRevenue, sb.LineAmount)), 2) AS ServiceRevenueAmount,
    CASE
        WHEN SUM(sb.BilledHours) = 0 THEN NULL
        ELSE ROUND(SUM(COALESCE(psr.PostedServiceRevenue, sb.LineAmount)) / SUM(sb.BilledHours), 2)
    END AS AverageHourlyRate
FROM service_billing AS sb
LEFT JOIN posted_service_revenue AS psr
    ON psr.SalesInvoiceLineID = sb.SalesInvoiceLineID
GROUP BY
    sb.InvoiceMonth,
    sb.CustomerName,
    sb.Region,
    sb.CustomerSegment
ORDER BY sb.InvoiceMonth, ServiceRevenueAmount DESC, sb.CustomerName;
