-- Teaching objective: Review weekly forecasts that lack approval or show unusually large overrides.
-- Main tables: DemandForecast, Item, Employee.
-- Expected output shape: One row per flagged forecast row.
-- Recommended build mode: Default.
-- Interpretation notes: Missing approval and outlier overrides are both planning-governance control failures.

SELECT
    df.DemandForecastID,
    df.ForecastWeekStartDate,
    df.ForecastWeekEndDate,
    i.ItemCode,
    i.ItemName,
    w.WarehouseName,
    COALESCE(planner.EmployeeName, '(No Planner)') AS PlannerEmployeeName,
    COALESCE(approver.EmployeeName, '(Missing Approval)') AS ApprovedByEmployeeName,
    ROUND(df.BaselineForecastQuantity, 2) AS BaselineForecastQuantity,
    ROUND(df.ForecastQuantity, 2) AS ForecastQuantity,
    ROUND(df.ForecastQuantity - df.BaselineForecastQuantity, 2) AS ForecastOverrideQuantity,
    ROUND(
        CASE
            WHEN df.BaselineForecastQuantity = 0 THEN NULL
            ELSE df.ForecastQuantity / df.BaselineForecastQuantity
        END,
        2
    ) AS ForecastToBaselineRatio,
    df.ForecastMethod
FROM DemandForecast AS df
JOIN Item AS i
    ON i.ItemID = df.ItemID
JOIN Warehouse AS w
    ON w.WarehouseID = df.WarehouseID
LEFT JOIN Employee AS planner
    ON planner.EmployeeID = df.PlannerEmployeeID
LEFT JOIN Employee AS approver
    ON approver.EmployeeID = df.ApprovedByEmployeeID
WHERE df.ApprovedByEmployeeID IS NULL
   OR df.ApprovedDate IS NULL
   OR (
        df.BaselineForecastQuantity > 0
        AND (
            df.ForecastQuantity / df.BaselineForecastQuantity >= 1.50
            OR df.ForecastQuantity / df.BaselineForecastQuantity <= 0.50
        )
   )
ORDER BY
    df.ForecastWeekStartDate,
    i.ItemCode,
    w.WarehouseName;

