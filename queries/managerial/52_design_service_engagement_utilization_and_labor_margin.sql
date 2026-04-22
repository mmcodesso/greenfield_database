-- Teaching objective: Compare engagement staffing mix, utilization, billed revenue, and labor margin for design services.
-- Main tables: ServiceEngagement, ServiceEngagementAssignment, ServiceTimeEntry, ServiceBillingLine, Customer, Employee.
-- Expected output shape: One row per service engagement.
-- Recommended build mode: Either.
-- Interpretation notes: Labor margin here is analytical, using `ServiceTimeEntry.ExtendedCost` rather than inventory or COGS postings.

WITH assignment_summary AS (
    SELECT
        sea.ServiceEngagementID,
        COUNT(DISTINCT sea.EmployeeID) AS AssignedEmployeeCount,
        ROUND(SUM(sea.AssignedHours), 2) AS AssignedHours,
        ROUND(SUM(CASE WHEN sea.AssignedRole = 'Design Services Manager' THEN sea.AssignedHours ELSE 0 END), 2) AS ManagerAssignedHours,
        ROUND(SUM(CASE WHEN sea.AssignedRole = 'Senior Designer' THEN sea.AssignedHours ELSE 0 END), 2) AS SeniorDesignerAssignedHours,
        ROUND(SUM(CASE WHEN sea.AssignedRole = 'Designer' THEN sea.AssignedHours ELSE 0 END), 2) AS DesignerAssignedHours
    FROM ServiceEngagementAssignment AS sea
    GROUP BY sea.ServiceEngagementID
),
time_summary AS (
    SELECT
        ste.ServiceEngagementID,
        ROUND(SUM(ste.BillableHours), 2) AS ApprovedBillableHours,
        ROUND(SUM(ste.NonBillableHours), 2) AS ApprovedNonBillableHours,
        ROUND(SUM(ste.ExtendedCost), 2) AS LaborCost
    FROM ServiceTimeEntry AS ste
    GROUP BY ste.ServiceEngagementID
),
billing_summary AS (
    SELECT
        sbl.ServiceEngagementID,
        ROUND(SUM(sbl.BilledHours), 2) AS BilledHours,
        ROUND(SUM(sbl.LineAmount), 2) AS BilledRevenue
    FROM ServiceBillingLine AS sbl
    GROUP BY sbl.ServiceEngagementID
)
SELECT
    se.EngagementNumber,
    c.CustomerName,
    i.ItemName AS ServiceName,
    lead.EmployeeName AS LeadEmployeeName,
    se.Status AS EngagementStatus,
    se.StartDate,
    se.EndDate,
    COALESCE(asg.AssignedEmployeeCount, 0) AS AssignedEmployeeCount,
    ROUND(COALESCE(asg.ManagerAssignedHours, 0), 2) AS ManagerAssignedHours,
    ROUND(COALESCE(asg.SeniorDesignerAssignedHours, 0), 2) AS SeniorDesignerAssignedHours,
    ROUND(COALESCE(asg.DesignerAssignedHours, 0), 2) AS DesignerAssignedHours,
    ROUND(COALESCE(asg.AssignedHours, 0), 2) AS AssignedHours,
    ROUND(COALESCE(ts.ApprovedBillableHours, 0), 2) AS ApprovedBillableHours,
    ROUND(COALESCE(ts.ApprovedNonBillableHours, 0), 2) AS ApprovedNonBillableHours,
    ROUND(COALESCE(bs.BilledHours, 0), 2) AS BilledHours,
    CASE
        WHEN COALESCE(asg.AssignedHours, 0) = 0 THEN NULL
        ELSE ROUND(COALESCE(ts.ApprovedBillableHours, 0) / asg.AssignedHours * 100.0, 2)
    END AS BillableUtilizationPct,
    ROUND(COALESCE(bs.BilledRevenue, 0), 2) AS BilledRevenue,
    ROUND(COALESCE(ts.LaborCost, 0), 2) AS LaborCost,
    ROUND(COALESCE(bs.BilledRevenue, 0) - COALESCE(ts.LaborCost, 0), 2) AS LaborMargin,
    CASE
        WHEN COALESCE(bs.BilledRevenue, 0) = 0 THEN NULL
        ELSE ROUND((COALESCE(bs.BilledRevenue, 0) - COALESCE(ts.LaborCost, 0)) / bs.BilledRevenue * 100.0, 2)
    END AS LaborMarginPct
FROM ServiceEngagement AS se
JOIN Customer AS c
    ON c.CustomerID = se.CustomerID
JOIN Item AS i
    ON i.ItemID = se.ItemID
LEFT JOIN Employee AS lead
    ON lead.EmployeeID = se.LeadEmployeeID
LEFT JOIN assignment_summary AS asg
    ON asg.ServiceEngagementID = se.ServiceEngagementID
LEFT JOIN time_summary AS ts
    ON ts.ServiceEngagementID = se.ServiceEngagementID
LEFT JOIN billing_summary AS bs
    ON bs.ServiceEngagementID = se.ServiceEngagementID
ORDER BY LaborMargin DESC, se.EngagementNumber;
