-- Teaching objective: Review active inventory items that lack a current active policy or carry inactive policy rows.
-- Main tables: InventoryPolicy, Item, Warehouse, Employee.
-- Expected output shape: One row per policy exception.
-- Recommended build mode: Default.
-- Interpretation notes: This query supports planning-governance review over stale or missing replenishment policy.

WITH active_items AS (
    SELECT
        i.ItemID,
        i.ItemCode,
        i.ItemName,
        i.ItemGroup,
        i.SupplyMode
    FROM Item AS i
    WHERE i.InventoryAccountID IS NOT NULL
      AND i.IsActive = 1
),
item_warehouse AS (
    SELECT
        ai.ItemID,
        ai.ItemCode,
        ai.ItemName,
        ai.ItemGroup,
        ai.SupplyMode,
        w.WarehouseID,
        w.WarehouseName
    FROM active_items AS ai
    CROSS JOIN Warehouse AS w
),
active_policy AS (
    SELECT
        ip.ItemID,
        ip.WarehouseID,
        COUNT(*) AS ActivePolicyCount
    FROM InventoryPolicy AS ip
    WHERE ip.IsActive = 1
    GROUP BY
        ip.ItemID,
        ip.WarehouseID
)
SELECT
    iw.ItemCode,
    iw.ItemName,
    iw.ItemGroup,
    iw.SupplyMode,
    iw.WarehouseName,
    COALESCE(ap.ActivePolicyCount, 0) AS ActivePolicyCount,
    CASE
        WHEN COALESCE(ap.ActivePolicyCount, 0) = 0 THEN 'Missing Active Policy'
        WHEN COALESCE(ap.ActivePolicyCount, 0) > 1 THEN 'Duplicate Active Policy'
        ELSE 'Inactive Policy Review'
    END AS PolicyException
FROM item_warehouse AS iw
LEFT JOIN active_policy AS ap
    ON ap.ItemID = iw.ItemID
   AND ap.WarehouseID = iw.WarehouseID
WHERE COALESCE(ap.ActivePolicyCount, 0) <> 1

UNION ALL

SELECT
    i.ItemCode,
    i.ItemName,
    i.ItemGroup,
    i.SupplyMode,
    w.WarehouseName,
    0 AS ActivePolicyCount,
    'Inactive Policy Row Present' AS PolicyException
FROM InventoryPolicy AS ip
JOIN Item AS i
    ON i.ItemID = ip.ItemID
JOIN Warehouse AS w
    ON w.WarehouseID = ip.WarehouseID
WHERE i.IsActive = 1
  AND ip.IsActive = 0
ORDER BY
    PolicyException,
    ItemCode,
    WarehouseName;

