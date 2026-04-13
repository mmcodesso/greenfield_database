-- Teaching objective: Review how planning recommendations convert into requisitions and work orders by planner and priority.
-- Main tables: SupplyPlanRecommendation, Employee.
-- Expected output shape: One row per recommendation grouping.
-- Recommended build mode: Either.
-- Interpretation notes: This query helps students connect planning output volume to actual replenishment conversion behavior.

SELECT
    spr.RecommendationType,
    spr.PriorityCode,
    spr.DriverType,
    COALESCE(e.EmployeeName, '(No Planner)') AS PlannerEmployeeName,
    COALESCE(e.JobTitle, '(No Planner Role)') AS PlannerJobTitle,
    spr.RecommendationStatus,
    COUNT(*) AS RecommendationCount,
    ROUND(SUM(spr.GrossRequirementQuantity), 2) AS GrossRequirementQuantity,
    ROUND(SUM(spr.NetRequirementQuantity), 2) AS NetRequirementQuantity,
    ROUND(SUM(spr.RecommendedOrderQuantity), 2) AS RecommendedOrderQuantity
FROM SupplyPlanRecommendation AS spr
LEFT JOIN Employee AS e
    ON e.EmployeeID = spr.PlannerEmployeeID
GROUP BY
    spr.RecommendationType,
    spr.PriorityCode,
    spr.DriverType,
    COALESCE(e.EmployeeName, '(No Planner)'),
    COALESCE(e.JobTitle, '(No Planner Role)'),
    spr.RecommendationStatus
ORDER BY
    RecommendationCount DESC,
    RecommendedOrderQuantity DESC,
    spr.RecommendationType,
    spr.PriorityCode;

