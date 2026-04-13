-- Teaching objective: Review replenishment documents that lack planning support.
-- Main tables: PurchaseRequisition, WorkOrder, Item.
-- Expected output shape: One row per unsupported requisition or work order.
-- Recommended build mode: Default.
-- Interpretation notes: In the Phase 22 model, normal replenishment activity should be traceable to a planning recommendation.

SELECT
    'Purchase Requisition' AS DocumentType,
    pr.RequisitionID AS DocumentID,
    pr.RequisitionNumber AS DocumentNumber,
    pr.RequestDate AS DocumentDate,
    i.ItemCode,
    i.ItemName,
    ROUND(pr.Quantity, 2) AS Quantity,
    pr.Justification,
    pr.Status
FROM PurchaseRequisition AS pr
JOIN Item AS i
    ON i.ItemID = pr.ItemID
WHERE pr.SupplyPlanRecommendationID IS NULL
  AND i.InventoryAccountID IS NOT NULL

UNION ALL

SELECT
    'Work Order' AS DocumentType,
    wo.WorkOrderID AS DocumentID,
    wo.WorkOrderNumber AS DocumentNumber,
    wo.ReleasedDate AS DocumentDate,
    i.ItemCode,
    i.ItemName,
    ROUND(wo.PlannedQuantity, 2) AS Quantity,
    'Released without supply plan support' AS Justification,
    wo.Status
FROM WorkOrder AS wo
JOIN Item AS i
    ON i.ItemID = wo.ItemID
WHERE wo.SupplyPlanRecommendationID IS NULL
ORDER BY
    DocumentDate,
    DocumentType,
    DocumentNumber;

