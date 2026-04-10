-- Teaching objective: Review routing, work-order operation, and direct-labor linkage completeness.
-- Main tables: Item, Routing, WorkOrder, WorkOrderOperation, LaborTimeEntry.
-- Output shape: One row per potential routing or operation-link exception.
-- Interpretation notes: Clean builds should normally return no rows.

WITH manufactured_items AS (
    SELECT ItemID, ItemCode, ItemName
    FROM Item
    WHERE SupplyMode = 'Manufactured'
      AND RevenueAccountID IS NOT NULL
      AND IsActive = 1
),
item_routing_gaps AS (
    SELECT
        'Manufactured item missing active routing' AS IssueType,
        mi.ItemCode AS ReferenceNumber,
        mi.ItemName AS Description,
        NULL AS RelatedNumber
    FROM manufactured_items AS mi
    LEFT JOIN Routing AS r
        ON r.ParentItemID = mi.ItemID
       AND r.Status = 'Active'
    WHERE r.RoutingID IS NULL
),
work_order_operation_gaps AS (
    SELECT
        'Manufactured work order missing operation rows' AS IssueType,
        wo.WorkOrderNumber AS ReferenceNumber,
        i.ItemCode || ' - ' || i.ItemName AS Description,
        NULL AS RelatedNumber
    FROM WorkOrder AS wo
    JOIN Item AS i
        ON i.ItemID = wo.ItemID
    LEFT JOIN WorkOrderOperation AS woo
        ON woo.WorkOrderID = wo.WorkOrderID
    WHERE i.SupplyMode = 'Manufactured'
    GROUP BY wo.WorkOrderID, wo.WorkOrderNumber, i.ItemCode, i.ItemName
    HAVING COUNT(woo.WorkOrderOperationID) = 0
),
labor_operation_gaps AS (
    SELECT
        'Direct labor missing or invalid operation link' AS IssueType,
        CAST(lte.LaborTimeEntryID AS TEXT) AS ReferenceNumber,
        wo.WorkOrderNumber AS Description,
        CAST(lte.WorkOrderOperationID AS TEXT) AS RelatedNumber
    FROM LaborTimeEntry AS lte
    LEFT JOIN WorkOrder AS wo
        ON wo.WorkOrderID = lte.WorkOrderID
    LEFT JOIN WorkOrderOperation AS woo
        ON woo.WorkOrderOperationID = lte.WorkOrderOperationID
    WHERE lte.LaborType = 'Direct Manufacturing'
      AND (
            lte.WorkOrderOperationID IS NULL
            OR woo.WorkOrderOperationID IS NULL
            OR woo.WorkOrderID <> lte.WorkOrderID
          )
)
SELECT * FROM item_routing_gaps
UNION ALL
SELECT * FROM work_order_operation_gaps
UNION ALL
SELECT * FROM labor_operation_gaps
ORDER BY IssueType, ReferenceNumber;
