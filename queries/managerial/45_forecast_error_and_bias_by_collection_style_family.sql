-- Teaching objective: Summarize forecast error and bias by collection and style family.
-- Main tables: DemandForecast, SalesOrder, SalesOrderLine, Item.
-- Expected output shape: One row per collection and style family.
-- Recommended build mode: Either.
-- Interpretation notes: This query is useful for discussing where forecast error is systematic rather than random.

WITH forecast AS (
    SELECT
        i.CollectionName,
        i.StyleFamily,
        ROUND(SUM(df.ForecastQuantity), 2) AS ForecastQuantity
    FROM DemandForecast AS df
    JOIN Item AS i
        ON i.ItemID = df.ItemID
    GROUP BY
        i.CollectionName,
        i.StyleFamily
),
actual AS (
    SELECT
        i.CollectionName,
        i.StyleFamily,
        ROUND(SUM(sol.Quantity), 2) AS ActualOrderQuantity
    FROM SalesOrderLine AS sol
    JOIN Item AS i
        ON i.ItemID = sol.ItemID
    GROUP BY
        i.CollectionName,
        i.StyleFamily
),
keys AS (
    SELECT CollectionName, StyleFamily FROM forecast
    UNION
    SELECT CollectionName, StyleFamily FROM actual
)
SELECT
    COALESCE(k.CollectionName, '(No Collection)') AS CollectionName,
    COALESCE(k.StyleFamily, '(No Style Family)') AS StyleFamily,
    ROUND(COALESCE(f.ForecastQuantity, 0), 2) AS ForecastQuantity,
    ROUND(COALESCE(a.ActualOrderQuantity, 0), 2) AS ActualOrderQuantity,
    ROUND(COALESCE(a.ActualOrderQuantity, 0) - COALESCE(f.ForecastQuantity, 0), 2) AS BiasQuantity,
    ROUND(ABS(COALESCE(a.ActualOrderQuantity, 0) - COALESCE(f.ForecastQuantity, 0)), 2) AS AbsoluteErrorQuantity
FROM keys AS k
LEFT JOIN forecast AS f
    ON f.CollectionName = k.CollectionName
   AND f.StyleFamily = k.StyleFamily
LEFT JOIN actual AS a
    ON a.CollectionName = k.CollectionName
   AND a.StyleFamily = k.StyleFamily
ORDER BY
    AbsoluteErrorQuantity DESC,
    CollectionName,
    StyleFamily;
