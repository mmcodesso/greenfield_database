-- Teaching objective: Measure fill rate, remaining backorder quantity, and shipment lag from order entry.
-- Main tables: SalesOrder, SalesOrderLine, Shipment, ShipmentLine, Item.
-- Expected output shape: One row per order month and item group.
-- Recommended build mode: Either.
-- Interpretation notes: Shipment lag and partial fulfillment help students connect demand, inventory availability, and customer service performance.

WITH shipped_by_line AS (
    SELECT
        shl.SalesOrderLineID,
        ROUND(SUM(shl.QuantityShipped), 2) AS ShippedQuantity,
        MIN(date(sh.ShipmentDate)) AS FirstShipmentDate,
        MAX(date(sh.ShipmentDate)) AS LastShipmentDate
    FROM ShipmentLine AS shl
    JOIN Shipment AS sh
        ON sh.ShipmentID = shl.ShipmentID
    GROUP BY shl.SalesOrderLineID
)
SELECT
    substr(so.OrderDate, 1, 7) AS OrderMonth,
    i.ItemGroup,
    COUNT(*) AS SalesOrderLineCount,
    ROUND(SUM(sol.Quantity), 2) AS OrderedQuantity,
    ROUND(SUM(COALESCE(sbl.ShippedQuantity, 0)), 2) AS ShippedQuantity,
    ROUND(SUM(sol.Quantity - COALESCE(sbl.ShippedQuantity, 0)), 2) AS RemainingBackorderQuantity,
    SUM(CASE WHEN COALESCE(sbl.ShippedQuantity, 0) < sol.Quantity THEN 1 ELSE 0 END) AS BackorderedLineCount,
    SUM(CASE WHEN COALESCE(sbl.ShippedQuantity, 0) >= sol.Quantity THEN 1 ELSE 0 END) AS FullyShippedLineCount,
    ROUND(100.0 * SUM(COALESCE(sbl.ShippedQuantity, 0)) / NULLIF(SUM(sol.Quantity), 0), 2) AS FillRatePct,
    ROUND(AVG(
        CASE
            WHEN sbl.FirstShipmentDate IS NOT NULL
            THEN julianday(sbl.FirstShipmentDate) - julianday(date(so.OrderDate))
        END
    ), 2) AS AvgDaysToFirstShipment
FROM SalesOrderLine AS sol
JOIN SalesOrder AS so
    ON so.SalesOrderID = sol.SalesOrderID
JOIN Item AS i
    ON i.ItemID = sol.ItemID
LEFT JOIN shipped_by_line AS sbl
    ON sbl.SalesOrderLineID = sol.SalesOrderLineID
GROUP BY substr(so.OrderDate, 1, 7), i.ItemGroup
ORDER BY OrderMonth, i.ItemGroup;
