-- Teaching objective: Review planning activity that occurs before launch or against discontinued inactive items.
-- Main tables: DemandForecast, SupplyPlanRecommendation, PurchaseRequisition, WorkOrder, Item.
-- Expected output shape: One row per planning-timing exception.
-- Recommended build mode: Default.
-- Interpretation notes: This query complements the operational prelaunch-item review by focusing on planning-layer support rows.

SELECT
    'Demand Forecast' AS SourceTable,
    df.DemandForecastID AS SourceID,
    df.ForecastWeekStartDate AS ActivityDate,
    i.ItemCode,
    i.ItemName,
    i.LifecycleStatus,
    i.IsActive,
    i.LaunchDate,
    ROUND(df.ForecastQuantity, 2) AS Quantity
FROM DemandForecast AS df
JOIN Item AS i
    ON i.ItemID = df.ItemID
WHERE date(df.ForecastWeekStartDate) < date(i.LaunchDate)
   OR (i.LifecycleStatus = 'Discontinued' AND i.IsActive = 0 AND df.ForecastQuantity > 0)

UNION ALL

SELECT
    'Supply Recommendation' AS SourceTable,
    spr.SupplyPlanRecommendationID AS SourceID,
    spr.ReleaseByDate AS ActivityDate,
    i.ItemCode,
    i.ItemName,
    i.LifecycleStatus,
    i.IsActive,
    i.LaunchDate,
    ROUND(spr.RecommendedOrderQuantity, 2) AS Quantity
FROM SupplyPlanRecommendation AS spr
JOIN Item AS i
    ON i.ItemID = spr.ItemID
WHERE date(spr.ReleaseByDate) < date(i.LaunchDate)
   OR (i.LifecycleStatus = 'Discontinued' AND i.IsActive = 0 AND spr.RecommendedOrderQuantity > 0)

UNION ALL

SELECT
    'Purchase Requisition' AS SourceTable,
    pr.RequisitionID AS SourceID,
    pr.RequestDate AS ActivityDate,
    i.ItemCode,
    i.ItemName,
    i.LifecycleStatus,
    i.IsActive,
    i.LaunchDate,
    ROUND(pr.Quantity, 2) AS Quantity
FROM PurchaseRequisition AS pr
JOIN Item AS i
    ON i.ItemID = pr.ItemID
WHERE date(pr.RequestDate) < date(i.LaunchDate)
   OR (i.LifecycleStatus = 'Discontinued' AND i.IsActive = 0 AND pr.Quantity > 0)

UNION ALL

SELECT
    'Work Order' AS SourceTable,
    wo.WorkOrderID AS SourceID,
    wo.ReleasedDate AS ActivityDate,
    i.ItemCode,
    i.ItemName,
    i.LifecycleStatus,
    i.IsActive,
    i.LaunchDate,
    ROUND(wo.PlannedQuantity, 2) AS Quantity
FROM WorkOrder AS wo
JOIN Item AS i
    ON i.ItemID = wo.ItemID
WHERE date(wo.ReleasedDate) < date(i.LaunchDate)
   OR (i.LifecycleStatus = 'Discontinued' AND i.IsActive = 0 AND wo.PlannedQuantity > 0)
ORDER BY
    ActivityDate,
    SourceTable,
    ItemCode;
