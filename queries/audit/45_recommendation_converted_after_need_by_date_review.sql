-- Teaching objective: Review planning recommendations that converted after their need-by date.
-- Main tables: SupplyPlanRecommendation, PurchaseRequisition, WorkOrder, Item.
-- Expected output shape: One row per late conversion.
-- Recommended build mode: Default.
-- Interpretation notes: This query isolates planning-timing failures rather than item-master or approval failures.

WITH requisition_match AS (
    SELECT
        spr.SupplyPlanRecommendationID,
        pr.RequisitionNumber AS ConvertedDocumentNumber,
        pr.RequestDate AS ConvertedDocumentDate
    FROM SupplyPlanRecommendation AS spr
    JOIN PurchaseRequisition AS pr
        ON pr.RequisitionID = spr.ConvertedDocumentID
    WHERE spr.ConvertedDocumentType = 'PurchaseRequisition'
),
work_order_match AS (
    SELECT
        spr.SupplyPlanRecommendationID,
        wo.WorkOrderNumber AS ConvertedDocumentNumber,
        wo.ReleasedDate AS ConvertedDocumentDate
    FROM SupplyPlanRecommendation AS spr
    JOIN WorkOrder AS wo
        ON wo.WorkOrderID = spr.ConvertedDocumentID
    WHERE spr.ConvertedDocumentType = 'WorkOrder'
),
matches AS (
    SELECT * FROM requisition_match
    UNION ALL
    SELECT * FROM work_order_match
)
SELECT
    spr.SupplyPlanRecommendationID,
    spr.RecommendationType,
    spr.PriorityCode,
    spr.DriverType,
    i.ItemCode,
    i.ItemName,
    spr.NeedByDate,
    m.ConvertedDocumentNumber,
    m.ConvertedDocumentDate,
    ROUND(spr.RecommendedOrderQuantity, 2) AS RecommendedOrderQuantity
FROM SupplyPlanRecommendation AS spr
JOIN matches AS m
    ON m.SupplyPlanRecommendationID = spr.SupplyPlanRecommendationID
JOIN Item AS i
    ON i.ItemID = spr.ItemID
WHERE date(m.ConvertedDocumentDate) > date(spr.NeedByDate)
ORDER BY
    spr.NeedByDate,
    m.ConvertedDocumentDate,
    spr.SupplyPlanRecommendationID;

