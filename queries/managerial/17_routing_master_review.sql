-- Teaching objective: Review the routing design assigned to manufactured items.
-- Main tables: Item, Routing, RoutingOperation, WorkCenter.
-- Output shape: One row per manufactured item and routing operation.
-- Interpretation notes: Clean builds should show one active routing per manufactured sellable item.

SELECT
    i.ItemCode,
    i.ItemName,
    i.ItemGroup,
    r.RoutingID,
    r.VersionNumber,
    ro.OperationSequence,
    ro.OperationCode,
    ro.OperationName,
    wc.WorkCenterCode,
    wc.WorkCenterName,
    ROUND(ro.StandardSetupHours, 2) AS StandardSetupHours,
    ROUND(ro.StandardRunHoursPerUnit, 2) AS StandardRunHoursPerUnit,
    ro.StandardQueueDays
FROM Item AS i
JOIN Routing AS r
    ON r.ParentItemID = i.ItemID
   AND r.Status = 'Active'
JOIN RoutingOperation AS ro
    ON ro.RoutingID = r.RoutingID
JOIN WorkCenter AS wc
    ON wc.WorkCenterID = ro.WorkCenterID
WHERE i.SupplyMode = 'Manufactured'
  AND i.RevenueAccountID IS NOT NULL
  AND i.IsActive = 1
ORDER BY i.ItemGroup, i.ItemCode, ro.OperationSequence;
