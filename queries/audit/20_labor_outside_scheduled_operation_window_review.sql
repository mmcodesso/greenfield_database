-- Teaching objective: Find direct labor booked outside the scheduled or actual operation window.
-- Main tables: LaborTimeEntry, TimeClockEntry, WorkOrderOperation, WorkOrder, RoutingOperation, Employee.
-- Output shape: One row per potential labor-window exception.
-- Interpretation notes: Clean builds should usually return no rows. Anomaly builds may show planted post-close or outside-window labor.

WITH operation_window AS (
    SELECT
        WorkOrderOperationID,
        date(COALESCE(ActualStartDate, PlannedStartDate)) AS WindowStartDate,
        date(COALESCE(ActualEndDate, PlannedEndDate)) AS WindowEndDate
    FROM WorkOrderOperation
)
SELECT
    lte.LaborTimeEntryID,
    e.EmployeeName,
    wo.WorkOrderNumber,
    ro.OperationCode,
    ro.OperationName,
    date(lte.WorkDate) AS LaborDate,
    ow.WindowStartDate,
    ow.WindowEndDate,
    ROUND(lte.RegularHours + lte.OvertimeHours, 2) AS LaborHours,
    CASE
        WHEN date(lte.WorkDate) < ow.WindowStartDate THEN 'Labor before operation start'
        WHEN date(lte.WorkDate) > ow.WindowEndDate THEN 'Labor after operation end'
        ELSE 'Window aligned'
    END AS PotentialIssue
FROM LaborTimeEntry AS lte
JOIN WorkOrderOperation AS woo
    ON woo.WorkOrderOperationID = lte.WorkOrderOperationID
JOIN operation_window AS ow
    ON ow.WorkOrderOperationID = lte.WorkOrderOperationID
JOIN WorkOrder AS wo
    ON wo.WorkOrderID = lte.WorkOrderID
JOIN RoutingOperation AS ro
    ON ro.RoutingOperationID = woo.RoutingOperationID
JOIN Employee AS e
    ON e.EmployeeID = lte.EmployeeID
WHERE lte.LaborType = 'Direct Manufacturing'
  AND lte.WorkOrderOperationID IS NOT NULL
  AND (
        date(lte.WorkDate) < ow.WindowStartDate
        OR date(lte.WorkDate) > ow.WindowEndDate
      )
ORDER BY LaborDate, wo.WorkOrderNumber, ro.OperationCode, e.EmployeeName;
