-- Teaching objective: Estimate inventory coverage and stockout risk from the latest planning recommendation state.
-- Main tables: SupplyPlanRecommendation, DemandForecast, Item, Warehouse.
-- Expected output shape: One row per item and warehouse at the latest planned week.
-- Recommended build mode: Either.
-- Interpretation notes: Use this query to discuss safety stock, projected availability, and the operational meaning of expedite pressure.

WITH latest_bucket AS (
    SELECT MAX(BucketWeekStartDate) AS BucketWeekStartDate
    FROM SupplyPlanRecommendation
),
latest_recommendations AS (
    SELECT
        spr.ItemID,
        spr.WarehouseID,
        spr.PriorityCode,
        spr.ProjectedAvailableQuantity,
        spr.NetRequirementQuantity,
        spr.RecommendedOrderQuantity
    FROM SupplyPlanRecommendation AS spr
    JOIN latest_bucket AS lb
        ON lb.BucketWeekStartDate = spr.BucketWeekStartDate
),
recent_forecast AS (
    SELECT
        df.ItemID,
        df.WarehouseID,
        ROUND(AVG(df.ForecastQuantity), 2) AS AvgWeeklyForecastQuantity
    FROM DemandForecast AS df
    WHERE date(df.ForecastWeekStartDate) >= date((SELECT BucketWeekStartDate FROM latest_bucket), '-21 days')
      AND date(df.ForecastWeekStartDate) <= date((SELECT BucketWeekStartDate FROM latest_bucket), '+35 days')
    GROUP BY
        df.ItemID,
        df.WarehouseID
)
SELECT
    i.ItemCode,
    i.ItemName,
    i.ItemGroup,
    COALESCE(i.CollectionName, '(No Collection)') AS CollectionName,
    COALESCE(i.StyleFamily, '(No Style Family)') AS StyleFamily,
    w.WarehouseName,
    COALESCE(rf.AvgWeeklyForecastQuantity, 0) AS AvgWeeklyForecastQuantity,
    ROUND(COALESCE(lr.ProjectedAvailableQuantity, 0), 2) AS ProjectedAvailableQuantity,
    ROUND(COALESCE(lr.NetRequirementQuantity, 0), 2) AS NetRequirementQuantity,
    ROUND(COALESCE(lr.RecommendedOrderQuantity, 0), 2) AS RecommendedOrderQuantity,
    ROUND(
        CASE
            WHEN COALESCE(rf.AvgWeeklyForecastQuantity, 0) = 0 THEN NULL
            ELSE lr.ProjectedAvailableQuantity / rf.AvgWeeklyForecastQuantity
        END,
        2
    ) AS WeeksOfCoverage,
    CASE
        WHEN COALESCE(lr.PriorityCode, 'Normal') = 'Expedite' THEN 'High'
        WHEN COALESCE(lr.ProjectedAvailableQuantity, 0) <= 0 THEN 'High'
        WHEN COALESCE(lr.NetRequirementQuantity, 0) > 0 THEN 'Medium'
        ELSE 'Low'
    END AS StockoutRisk
FROM latest_recommendations AS lr
JOIN Item AS i
    ON i.ItemID = lr.ItemID
JOIN Warehouse AS w
    ON w.WarehouseID = lr.WarehouseID
LEFT JOIN recent_forecast AS rf
    ON rf.ItemID = lr.ItemID
   AND rf.WarehouseID = lr.WarehouseID
ORDER BY
    CASE StockoutRisk WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
    WeeksOfCoverage,
    i.ItemCode,
    w.WarehouseName;

