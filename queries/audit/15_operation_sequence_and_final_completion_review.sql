-- Teaching objective: Review operation sequencing and final completion timing for manufactured work orders.
-- Main tables: WorkOrder, WorkOrderOperation, RoutingOperation.
-- Output shape: One row per potential sequencing or completion-timing exception.
-- Interpretation notes: Clean builds should normally return no rows or very few rows.

WITH operation_checks AS (
    SELECT
        woo.WorkOrderID,
        wo.WorkOrderNumber,
        woo.OperationSequence,
        ro.OperationCode,
        date(woo.ActualStartDate) AS ActualStartDate,
        date(woo.ActualEndDate) AS ActualEndDate,
        date(prev.ActualEndDate) AS PriorOperationEndDate,
        date(wo.CompletedDate) AS WorkOrderCompletedDate
    FROM WorkOrderOperation AS woo
    JOIN WorkOrder AS wo
        ON wo.WorkOrderID = woo.WorkOrderID
    JOIN RoutingOperation AS ro
        ON ro.RoutingOperationID = woo.RoutingOperationID
    LEFT JOIN WorkOrderOperation AS prev
        ON prev.WorkOrderID = woo.WorkOrderID
       AND prev.OperationSequence = woo.OperationSequence - 1
)
SELECT
    WorkOrderNumber,
    OperationSequence,
    OperationCode,
    ActualStartDate,
    ActualEndDate,
    PriorOperationEndDate,
    WorkOrderCompletedDate,
    CASE
        WHEN PriorOperationEndDate IS NOT NULL
         AND ActualStartDate IS NOT NULL
         AND julianday(ActualStartDate) < julianday(PriorOperationEndDate)
            THEN 'Operation started before the prior operation finished'
        WHEN WorkOrderCompletedDate IS NOT NULL
         AND ActualEndDate IS NOT NULL
         AND OperationSequence = (
                SELECT MAX(OperationSequence)
                FROM WorkOrderOperation AS last_op
                WHERE last_op.WorkOrderID = operation_checks.WorkOrderID
            )
         AND julianday(WorkOrderCompletedDate) < julianday(ActualEndDate)
            THEN 'Work order completed before the final routing operation finished'
        ELSE 'Other sequencing issue'
    END AS PotentialIssue
FROM operation_checks
WHERE (
        PriorOperationEndDate IS NOT NULL
        AND ActualStartDate IS NOT NULL
        AND julianday(ActualStartDate) < julianday(PriorOperationEndDate)
      )
   OR (
        WorkOrderCompletedDate IS NOT NULL
        AND ActualEndDate IS NOT NULL
        AND OperationSequence = (
            SELECT MAX(OperationSequence)
            FROM WorkOrderOperation AS last_op
            WHERE last_op.WorkOrderID = operation_checks.WorkOrderID
        )
        AND julianday(WorkOrderCompletedDate) < julianday(ActualEndDate)
      )
ORDER BY WorkOrderNumber, OperationSequence;
