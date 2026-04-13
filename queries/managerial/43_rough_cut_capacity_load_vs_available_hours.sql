-- Teaching objective: Compare rough-cut planned load to available hours by work center and week.
-- Main tables: RoughCutCapacityPlan, WorkCenter.
-- Expected output shape: One row per work center and week.
-- Recommended build mode: Either.
-- Interpretation notes: This query provides the rough-cut capacity tieout beneath work-order release pressure.

SELECT
    rccp.BucketWeekStartDate,
    rccp.BucketWeekEndDate,
    wc.WorkCenterCode,
    wc.WorkCenterName,
    ROUND(SUM(rccp.PlannedLoadHours), 2) AS PlannedLoadHours,
    ROUND(MAX(rccp.AvailableHours), 2) AS AvailableHours,
    ROUND(SUM(rccp.PlannedLoadHours) / NULLIF(MAX(rccp.AvailableHours), 0), 4) AS UtilizationPct,
    CASE
        WHEN SUM(rccp.PlannedLoadHours) > MAX(rccp.AvailableHours) THEN 'Over Capacity'
        WHEN SUM(rccp.PlannedLoadHours) >= MAX(rccp.AvailableHours) * 0.90 THEN 'Tight'
        ELSE 'Within Capacity'
    END AS CapacityStatus
FROM RoughCutCapacityPlan AS rccp
JOIN WorkCenter AS wc
    ON wc.WorkCenterID = rccp.WorkCenterID
GROUP BY
    rccp.BucketWeekStartDate,
    rccp.BucketWeekEndDate,
    wc.WorkCenterCode,
    wc.WorkCenterName
ORDER BY
    rccp.BucketWeekStartDate,
    UtilizationPct DESC,
    wc.WorkCenterCode;

