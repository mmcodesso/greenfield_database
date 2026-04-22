-- Teaching objective: Review whether approved design-service hours, billed hours, and invoice coverage stay aligned by engagement.
-- Main tables: ServiceEngagement, ServiceEngagementAssignment, ServiceTimeEntry, ServiceBillingLine, Customer.
-- Expected output shape: One row per service engagement.
-- Recommended build mode: Either.
-- Interpretation notes: This review focuses on approved billable hours because non-billable hours support delivery but should not reach the customer invoice.

WITH assignment_summary AS (
    SELECT
        sea.ServiceEngagementID,
        ROUND(SUM(sea.AssignedHours), 2) AS AssignedHours
    FROM ServiceEngagementAssignment AS sea
    GROUP BY sea.ServiceEngagementID
),
time_summary AS (
    SELECT
        ste.ServiceEngagementID,
        ROUND(SUM(ste.BillableHours), 2) AS ApprovedBillableHours,
        ROUND(SUM(ste.NonBillableHours), 2) AS ApprovedNonBillableHours,
        SUM(
            CASE
                WHEN ste.BillingStatus = 'Unbilled' AND ste.BillableHours > 0
                    THEN 1
                ELSE 0
            END
        ) AS UnbilledTimeEntryCount
    FROM ServiceTimeEntry AS ste
    GROUP BY ste.ServiceEngagementID
),
billing_summary AS (
    SELECT
        sbl.ServiceEngagementID,
        COUNT(DISTINCT sbl.SalesInvoiceLineID) AS InvoiceLineCount,
        ROUND(SUM(sbl.BilledHours), 2) AS BilledHours
    FROM ServiceBillingLine AS sbl
    GROUP BY sbl.ServiceEngagementID
)
SELECT
    se.EngagementNumber,
    c.CustomerName,
    i.ItemName AS ServiceName,
    se.Status AS EngagementStatus,
    se.StartDate,
    se.EndDate,
    ROUND(se.PlannedHours, 2) AS PlannedHours,
    ROUND(COALESCE(asg.AssignedHours, 0), 2) AS AssignedHours,
    ROUND(COALESCE(ts.ApprovedBillableHours, 0), 2) AS ApprovedBillableHours,
    ROUND(COALESCE(ts.ApprovedNonBillableHours, 0), 2) AS ApprovedNonBillableHours,
    ROUND(COALESCE(bs.BilledHours, 0), 2) AS BilledHours,
    ROUND(COALESCE(ts.ApprovedBillableHours, 0) - COALESCE(bs.BilledHours, 0), 2) AS ApprovedUnbilledHours,
    COALESCE(ts.UnbilledTimeEntryCount, 0) AS UnbilledTimeEntryCount,
    COALESCE(bs.InvoiceLineCount, 0) AS InvoiceLineCount,
    CASE
        WHEN COALESCE(bs.BilledHours, 0) > COALESCE(ts.ApprovedBillableHours, 0) THEN 'Overbilled'
        WHEN COALESCE(ts.ApprovedBillableHours, 0) > COALESCE(asg.AssignedHours, 0) THEN 'Approved over assigned'
        WHEN ROUND(COALESCE(ts.ApprovedBillableHours, 0) - COALESCE(bs.BilledHours, 0), 2) > 0 THEN 'Approved not fully billed'
        WHEN COALESCE(ts.ApprovedBillableHours, 0) = 0 THEN 'No approved billable time yet'
        ELSE 'Matched'
    END AS AuditFlag
FROM ServiceEngagement AS se
JOIN Customer AS c
    ON c.CustomerID = se.CustomerID
JOIN Item AS i
    ON i.ItemID = se.ItemID
LEFT JOIN assignment_summary AS asg
    ON asg.ServiceEngagementID = se.ServiceEngagementID
LEFT JOIN time_summary AS ts
    ON ts.ServiceEngagementID = se.ServiceEngagementID
LEFT JOIN billing_summary AS bs
    ON bs.ServiceEngagementID = se.ServiceEngagementID
ORDER BY ApprovedUnbilledHours DESC, se.EngagementNumber;
