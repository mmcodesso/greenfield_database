-- Teaching objective: Review recommendation mix by planning driver, collection, and supply mode.
-- Main tables: SupplyPlanRecommendation, Item.
-- Expected output shape: One row per collection, supply mode, and driver.
-- Recommended build mode: Either.
-- Interpretation notes: This query helps students separate forecast-driven replenishment from backlog, safety-stock, and component-demand pressure.

SELECT
    COALESCE(i.CollectionName, '(No Collection)') AS CollectionName,
    i.ItemGroup,
    i.SupplyMode,
    spr.DriverType,
    COUNT(*) AS RecommendationCount,
    ROUND(SUM(spr.GrossRequirementQuantity), 2) AS GrossRequirementQuantity,
    ROUND(SUM(spr.NetRequirementQuantity), 2) AS NetRequirementQuantity,
    ROUND(SUM(spr.RecommendedOrderQuantity), 2) AS RecommendedOrderQuantity
FROM SupplyPlanRecommendation AS spr
JOIN Item AS i
    ON i.ItemID = spr.ItemID
GROUP BY
    COALESCE(i.CollectionName, '(No Collection)'),
    i.ItemGroup,
    i.SupplyMode,
    spr.DriverType
ORDER BY
    RecommendedOrderQuantity DESC,
    CollectionName,
    i.ItemGroup,
    i.SupplyMode,
    spr.DriverType;

