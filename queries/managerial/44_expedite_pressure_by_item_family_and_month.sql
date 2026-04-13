-- Teaching objective: Measure how often planning pressure escalates to expedite recommendations.
-- Main tables: SupplyPlanRecommendation, Item.
-- Expected output shape: One row per month and item-family slice.
-- Recommended build mode: Either.
-- Interpretation notes: Use this query to discuss supply pressure concentration, planner workload, and service risk.

SELECT
    strftime('%Y-%m', spr.BucketWeekStartDate) AS PlanningMonth,
    i.ItemGroup,
    COALESCE(i.CollectionName, '(No Collection)') AS CollectionName,
    COALESCE(i.StyleFamily, '(No Style Family)') AS StyleFamily,
    spr.RecommendationType,
    COUNT(*) AS RecommendationCount,
    SUM(CASE WHEN spr.PriorityCode = 'Expedite' THEN 1 ELSE 0 END) AS ExpediteRecommendationCount,
    ROUND(SUM(spr.RecommendedOrderQuantity), 2) AS RecommendedOrderQuantity,
    ROUND(
        SUM(CASE WHEN spr.PriorityCode = 'Expedite' THEN spr.RecommendedOrderQuantity ELSE 0 END),
        2
    ) AS ExpediteRecommendedQuantity
FROM SupplyPlanRecommendation AS spr
JOIN Item AS i
    ON i.ItemID = spr.ItemID
GROUP BY
    strftime('%Y-%m', spr.BucketWeekStartDate),
    i.ItemGroup,
    COALESCE(i.CollectionName, '(No Collection)'),
    COALESCE(i.StyleFamily, '(No Style Family)'),
    spr.RecommendationType
ORDER BY
    PlanningMonth,
    ExpediteRecommendationCount DESC,
    ExpediteRecommendedQuantity DESC;

