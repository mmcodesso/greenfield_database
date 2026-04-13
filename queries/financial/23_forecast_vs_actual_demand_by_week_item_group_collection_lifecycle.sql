-- Teaching objective: Compare weekly forecast demand to realized sales-order demand by item family.
-- Main tables: DemandForecast, SalesOrder, SalesOrderLine, Item.
-- Expected output shape: One row per week and item-family slice.
-- Recommended build mode: Either.
-- Interpretation notes: Use this query to discuss forecast error, seasonality, and the gap between planned demand and actual order intake.

WITH forecast AS (
    SELECT
        df.ForecastWeekStartDate AS WeekStartDate,
        i.ItemGroup,
        COALESCE(i.CollectionName, '(No Collection)') AS CollectionName,
        COALESCE(i.LifecycleStatus, '(No Lifecycle)') AS LifecycleStatus,
        ROUND(SUM(df.ForecastQuantity), 2) AS ForecastQuantity
    FROM DemandForecast AS df
    JOIN Item AS i
        ON i.ItemID = df.ItemID
    GROUP BY
        df.ForecastWeekStartDate,
        i.ItemGroup,
        COALESCE(i.CollectionName, '(No Collection)'),
        COALESCE(i.LifecycleStatus, '(No Lifecycle)')
),
actual AS (
    SELECT
        date(so.OrderDate, printf('-%d days', (CAST(strftime('%w', so.OrderDate) AS INTEGER) + 6) % 7)) AS WeekStartDate,
        i.ItemGroup,
        COALESCE(i.CollectionName, '(No Collection)') AS CollectionName,
        COALESCE(i.LifecycleStatus, '(No Lifecycle)') AS LifecycleStatus,
        ROUND(SUM(sol.Quantity), 2) AS ActualOrderQuantity
    FROM SalesOrderLine AS sol
    JOIN SalesOrder AS so
        ON so.SalesOrderID = sol.SalesOrderID
    JOIN Item AS i
        ON i.ItemID = sol.ItemID
    GROUP BY
        date(so.OrderDate, printf('-%d days', (CAST(strftime('%w', so.OrderDate) AS INTEGER) + 6) % 7)),
        i.ItemGroup,
        COALESCE(i.CollectionName, '(No Collection)'),
        COALESCE(i.LifecycleStatus, '(No Lifecycle)')
),
keys AS (
    SELECT WeekStartDate, ItemGroup, CollectionName, LifecycleStatus FROM forecast
    UNION
    SELECT WeekStartDate, ItemGroup, CollectionName, LifecycleStatus FROM actual
)
SELECT
    k.WeekStartDate,
    k.ItemGroup,
    k.CollectionName,
    k.LifecycleStatus,
    ROUND(COALESCE(f.ForecastQuantity, 0), 2) AS ForecastQuantity,
    ROUND(COALESCE(a.ActualOrderQuantity, 0), 2) AS ActualOrderQuantity,
    ROUND(COALESCE(a.ActualOrderQuantity, 0) - COALESCE(f.ForecastQuantity, 0), 2) AS ForecastError,
    ROUND(
        CASE
            WHEN COALESCE(f.ForecastQuantity, 0) = 0 THEN NULL
            ELSE (COALESCE(a.ActualOrderQuantity, 0) - COALESCE(f.ForecastQuantity, 0)) / f.ForecastQuantity
        END,
        4
    ) AS ForecastErrorPct
FROM keys AS k
LEFT JOIN forecast AS f
    ON f.WeekStartDate = k.WeekStartDate
   AND f.ItemGroup = k.ItemGroup
   AND f.CollectionName = k.CollectionName
   AND f.LifecycleStatus = k.LifecycleStatus
LEFT JOIN actual AS a
    ON a.WeekStartDate = k.WeekStartDate
   AND a.ItemGroup = k.ItemGroup
   AND a.CollectionName = k.CollectionName
   AND a.LifecycleStatus = k.LifecycleStatus
ORDER BY
    k.WeekStartDate,
    k.ItemGroup,
    k.CollectionName,
    k.LifecycleStatus;

