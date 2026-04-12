-- Teaching objective: Review whether item-master rows carry the expected catalog attributes for their item group.
-- Main tables: Item.
-- Expected output shape: One row per item with one or more missing expected attributes.
-- Recommended build mode: Default.
-- Interpretation notes: The clean build should usually return no sellable-item exceptions. The anomaly-enabled build may contain planted catalog-completeness gaps for audit review.

WITH item_checks AS (
    SELECT
        ItemID,
        ItemCode,
        ItemName,
        ItemGroup,
        ItemType,
        SupplyMode,
        LifecycleStatus,
        LaunchDate,
        TRIM(
            (CASE WHEN ItemGroup IN ('Furniture', 'Lighting', 'Textiles') AND CollectionName IS NULL THEN 'CollectionName; ' ELSE '' END) ||
            (CASE WHEN ItemGroup IN ('Furniture', 'Lighting', 'Textiles', 'Accessories') AND StyleFamily IS NULL THEN 'StyleFamily; ' ELSE '' END) ||
            (CASE WHEN ItemGroup IN ('Furniture', 'Lighting', 'Textiles', 'Accessories', 'Raw Materials') AND PrimaryMaterial IS NULL THEN 'PrimaryMaterial; ' ELSE '' END) ||
            (CASE WHEN ItemGroup IN ('Furniture', 'Lighting', 'Accessories') AND Finish IS NULL THEN 'Finish; ' ELSE '' END) ||
            (CASE WHEN ItemGroup = 'Textiles' AND Color IS NULL THEN 'Color; ' ELSE '' END) ||
            (CASE WHEN ItemGroup IN ('Furniture', 'Textiles', 'Packaging') AND SizeDescriptor IS NULL THEN 'SizeDescriptor; ' ELSE '' END) ||
            (CASE WHEN LifecycleStatus IS NULL THEN 'LifecycleStatus; ' ELSE '' END) ||
            (CASE WHEN LaunchDate IS NULL THEN 'LaunchDate; ' ELSE '' END)
        ) AS MissingAttributes
    FROM Item
)
SELECT
    ItemID,
    ItemCode,
    ItemName,
    ItemGroup,
    ItemType,
    SupplyMode,
    LifecycleStatus,
    date(LaunchDate) AS LaunchDate,
    MissingAttributes
FROM item_checks
WHERE MissingAttributes <> ''
ORDER BY
    ItemGroup,
    ItemCode;
