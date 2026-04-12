-- Teaching objective: Review customer-service performance by collection and style family using shipment lag, fill rate, and backorder pressure.
-- Main tables: SalesOrder, SalesOrderLine, Shipment, ShipmentLine, Item.
-- Expected output shape: One row per item group, collection, and style family.
-- Recommended build mode: Either.
-- Interpretation notes: This is a service-level query, not a financial one. It starts from ordered demand and asks how quickly and how fully Greenfield ships those orders.

WITH shipment_summary AS (
    SELECT
        sl.SalesOrderLineID,
        ROUND(SUM(sl.QuantityShipped), 2) AS QuantityShipped,
        MIN(date(s.ShipmentDate)) AS FirstShipmentDate
    FROM ShipmentLine AS sl
    JOIN Shipment AS s
        ON s.ShipmentID = sl.ShipmentID
    GROUP BY sl.SalesOrderLineID
)
SELECT
    i.ItemGroup,
    COALESCE(i.CollectionName, '(No Collection)') AS CollectionName,
    COALESCE(i.StyleFamily, '(No Style Family)') AS StyleFamily,
    COUNT(*) AS SalesOrderLineCount,
    ROUND(SUM(sol.Quantity), 2) AS OrderedQuantity,
    ROUND(SUM(COALESCE(ss.QuantityShipped, 0)), 2) AS ShippedQuantity,
    ROUND(SUM(CASE WHEN COALESCE(ss.QuantityShipped, 0) < sol.Quantity THEN sol.Quantity - COALESCE(ss.QuantityShipped, 0) ELSE 0 END), 2) AS BackorderedQuantity,
    ROUND(
        CASE
            WHEN SUM(sol.Quantity) = 0 THEN NULL
            ELSE 100.0 * SUM(COALESCE(ss.QuantityShipped, 0)) / SUM(sol.Quantity)
        END,
        2
    ) AS FillRatePct,
    ROUND(
        AVG(
            CASE
                WHEN ss.FirstShipmentDate IS NOT NULL THEN julianday(ss.FirstShipmentDate) - julianday(date(so.OrderDate))
            END
        ),
        2
    ) AS AvgDaysToFirstShipment,
    ROUND(
        100.0 * AVG(
            CASE
                WHEN COALESCE(ss.QuantityShipped, 0) < sol.Quantity THEN 1.0
                ELSE 0.0
            END
        ),
        2
    ) AS BackorderedLinePct
FROM SalesOrderLine AS sol
JOIN SalesOrder AS so
    ON so.SalesOrderID = sol.SalesOrderID
JOIN Item AS i
    ON i.ItemID = sol.ItemID
LEFT JOIN shipment_summary AS ss
    ON ss.SalesOrderLineID = sol.SalesOrderLineID
GROUP BY
    i.ItemGroup,
    COALESCE(i.CollectionName, '(No Collection)'),
    COALESCE(i.StyleFamily, '(No Style Family)')
ORDER BY
    BackorderedQuantity DESC,
    FillRatePct ASC,
    AvgDaysToFirstShipment DESC;
