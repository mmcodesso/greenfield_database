-- Teaching objective: Review current-state item master conflicts between lifecycle status and active-flag logic.
-- Main tables: Item.
-- Expected output shape: One row per item with a current-state lifecycle or active-status conflict.
-- Recommended build mode: Default.
-- Interpretation notes: This query isolates current-state item-master conflicts. Use the pre-launch activity review separately when you need transaction-timing evidence.

SELECT
    ItemCode,
    ItemName,
    ItemGroup,
    SupplyMode,
    CollectionName,
    StyleFamily,
    PrimaryMaterial,
    Finish,
    Color,
    SizeDescriptor,
    LifecycleStatus,
    date(LaunchDate) AS LaunchDate,
    CAST(IsActive AS INTEGER) AS IsActive,
    CASE
        WHEN LifecycleStatus = 'Discontinued' AND CAST(IsActive AS INTEGER) = 1 THEN 'Discontinued But Still Active'
        ELSE 'Review'
    END AS ReviewFlag
FROM Item
WHERE LifecycleStatus = 'Discontinued'
  AND CAST(IsActive AS INTEGER) = 1
ORDER BY
    ItemGroup,
    ItemCode;
