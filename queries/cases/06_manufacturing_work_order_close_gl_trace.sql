-- Teaching objective: Trace one work order from material issue through completion, close variance, and supporting GL postings.
-- Main tables: WorkOrder, MaterialIssue, MaterialIssueLine, ProductionCompletion, ProductionCompletionLine, WorkOrderClose, GLEntry, Account, Item.
-- Output shape: One row per work order.
-- Interpretation notes: Material issue moves cost into WIP. Production completion moves finished goods out of WIP and through manufacturing clearing. Work-order close resolves residual variance.

WITH material_issue_summary AS (
    SELECT
        mi.WorkOrderID,
        COUNT(DISTINCT mi.MaterialIssueID) AS MaterialIssueCount,
        MIN(date(mi.IssueDate)) AS FirstIssueDate,
        MAX(date(mi.IssueDate)) AS LastIssueDate,
        ROUND(SUM(mil.ExtendedStandardCost), 2) AS MaterialIssuedCost
    FROM MaterialIssue AS mi
    JOIN MaterialIssueLine AS mil
        ON mil.MaterialIssueID = mi.MaterialIssueID
    GROUP BY mi.WorkOrderID
),
material_issue_gl AS (
    SELECT
        mi.WorkOrderID,
        ROUND(SUM(CASE WHEN a.AccountNumber = '1046' THEN gl.Debit ELSE 0 END), 2) AS MaterialIssueWipDebitAmount,
        ROUND(SUM(CASE WHEN a.AccountNumber = '1045' THEN gl.Credit ELSE 0 END), 2) AS MaterialIssueMaterialCreditAmount
    FROM MaterialIssue AS mi
    JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'MaterialIssue'
       AND gl.SourceDocumentID = mi.MaterialIssueID
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    GROUP BY mi.WorkOrderID
),
completion_summary AS (
    SELECT
        pc.WorkOrderID,
        COUNT(DISTINCT pc.ProductionCompletionID) AS CompletionEventCount,
        MIN(date(pc.CompletionDate)) AS FirstCompletionDate,
        MAX(date(pc.CompletionDate)) AS LastCompletionDate,
        ROUND(SUM(pcl.QuantityCompleted), 2) AS QuantityCompleted,
        ROUND(SUM(pcl.ExtendedStandardMaterialCost), 2) AS CompletedMaterialCost,
        ROUND(SUM(pcl.ExtendedStandardDirectLaborCost), 2) AS CompletedDirectLaborCost,
        ROUND(SUM(pcl.ExtendedStandardVariableOverheadCost), 2) AS CompletedVariableOverheadCost,
        ROUND(SUM(pcl.ExtendedStandardFixedOverheadCost), 2) AS CompletedFixedOverheadCost,
        ROUND(SUM(pcl.ExtendedStandardConversionCost), 2) AS CompletedConversionCost,
        ROUND(SUM(pcl.ExtendedStandardTotalCost), 2) AS CompletedTotalCost
    FROM ProductionCompletion AS pc
    JOIN ProductionCompletionLine AS pcl
        ON pcl.ProductionCompletionID = pc.ProductionCompletionID
    GROUP BY pc.WorkOrderID
),
completion_gl AS (
    SELECT
        pc.WorkOrderID,
        ROUND(SUM(CASE WHEN a.AccountNumber = '1040' THEN gl.Debit ELSE 0 END), 2) AS CompletionFinishedGoodsDebitAmount,
        ROUND(SUM(CASE WHEN a.AccountNumber = '1046' THEN gl.Credit ELSE 0 END), 2) AS CompletionWipCreditAmount,
        ROUND(SUM(CASE WHEN a.AccountNumber = '1090' THEN gl.Credit ELSE 0 END), 2) AS CompletionClearingCreditAmount
    FROM ProductionCompletion AS pc
    JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'ProductionCompletion'
       AND gl.SourceDocumentID = pc.ProductionCompletionID
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    GROUP BY pc.WorkOrderID
),
close_summary AS (
    SELECT
        WorkOrderID,
        date(CloseDate) AS CloseDate,
        ROUND(MaterialVarianceAmount, 2) AS MaterialVarianceAmount,
        ROUND(DirectLaborVarianceAmount, 2) AS DirectLaborVarianceAmount,
        ROUND(OverheadVarianceAmount, 2) AS OverheadVarianceAmount,
        ROUND(ConversionVarianceAmount, 2) AS ConversionVarianceAmount,
        ROUND(TotalVarianceAmount, 2) AS TotalVarianceAmount,
        Status AS CloseStatus
    FROM WorkOrderClose
),
close_gl AS (
    SELECT
        woc.WorkOrderID,
        ROUND(SUM(CASE WHEN a.AccountNumber = '1046' THEN gl.Debit - gl.Credit ELSE 0 END), 2) AS CloseWipNetMovement,
        ROUND(SUM(CASE WHEN a.AccountNumber = '1090' THEN gl.Debit - gl.Credit ELSE 0 END), 2) AS CloseClearingNetMovement,
        ROUND(SUM(CASE WHEN a.AccountNumber = '5080' THEN gl.Debit - gl.Credit ELSE 0 END), 2) AS CloseVarianceNetMovement
    FROM WorkOrderClose AS woc
    JOIN GLEntry AS gl
        ON gl.SourceDocumentType = 'WorkOrderClose'
       AND gl.SourceDocumentID = woc.WorkOrderCloseID
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    GROUP BY woc.WorkOrderID
)
SELECT
    wo.WorkOrderNumber,
    i.ItemCode,
    i.ItemName,
    i.ItemGroup,
    ROUND(wo.PlannedQuantity, 2) AS PlannedQuantity,
    date(wo.ReleasedDate) AS ReleasedDate,
    date(wo.CompletedDate) AS CompletedDate,
    date(wo.ClosedDate) AS ClosedDate,
    wo.Status AS WorkOrderStatus,
    COALESCE(mis.MaterialIssueCount, 0) AS MaterialIssueCount,
    mis.FirstIssueDate,
    mis.LastIssueDate,
    ROUND(COALESCE(mis.MaterialIssuedCost, 0), 2) AS MaterialIssuedCost,
    ROUND(COALESCE(mig.MaterialIssueWipDebitAmount, 0), 2) AS MaterialIssueWipDebitAmount,
    ROUND(COALESCE(mig.MaterialIssueMaterialCreditAmount, 0), 2) AS MaterialIssueMaterialCreditAmount,
    COALESCE(cs.CompletionEventCount, 0) AS CompletionEventCount,
    cs.FirstCompletionDate,
    cs.LastCompletionDate,
    ROUND(COALESCE(cs.QuantityCompleted, 0), 2) AS QuantityCompleted,
    ROUND(COALESCE(cs.CompletedMaterialCost, 0), 2) AS CompletedMaterialCost,
    ROUND(COALESCE(cs.CompletedDirectLaborCost, 0), 2) AS CompletedDirectLaborCost,
    ROUND(COALESCE(cs.CompletedVariableOverheadCost, 0), 2) AS CompletedVariableOverheadCost,
    ROUND(COALESCE(cs.CompletedFixedOverheadCost, 0), 2) AS CompletedFixedOverheadCost,
    ROUND(COALESCE(cs.CompletedConversionCost, 0), 2) AS CompletedConversionCost,
    ROUND(COALESCE(cs.CompletedTotalCost, 0), 2) AS CompletedTotalCost,
    ROUND(COALESCE(cg.CompletionFinishedGoodsDebitAmount, 0), 2) AS CompletionFinishedGoodsDebitAmount,
    ROUND(COALESCE(cg.CompletionWipCreditAmount, 0), 2) AS CompletionWipCreditAmount,
    ROUND(COALESCE(cg.CompletionClearingCreditAmount, 0), 2) AS CompletionClearingCreditAmount,
    cls.CloseDate,
    cls.CloseStatus,
    ROUND(COALESCE(cls.MaterialVarianceAmount, 0), 2) AS MaterialVarianceAmount,
    ROUND(COALESCE(cls.DirectLaborVarianceAmount, 0), 2) AS DirectLaborVarianceAmount,
    ROUND(COALESCE(cls.OverheadVarianceAmount, 0), 2) AS OverheadVarianceAmount,
    ROUND(COALESCE(cls.ConversionVarianceAmount, 0), 2) AS ConversionVarianceAmount,
    ROUND(COALESCE(cls.TotalVarianceAmount, 0), 2) AS TotalVarianceAmount,
    ROUND(COALESCE(clg.CloseWipNetMovement, 0), 2) AS CloseWipNetMovement,
    ROUND(COALESCE(clg.CloseClearingNetMovement, 0), 2) AS CloseClearingNetMovement,
    ROUND(COALESCE(clg.CloseVarianceNetMovement, 0), 2) AS CloseVarianceNetMovement
FROM WorkOrder AS wo
JOIN Item AS i
    ON i.ItemID = wo.ItemID
LEFT JOIN material_issue_summary AS mis
    ON mis.WorkOrderID = wo.WorkOrderID
LEFT JOIN material_issue_gl AS mig
    ON mig.WorkOrderID = wo.WorkOrderID
LEFT JOIN completion_summary AS cs
    ON cs.WorkOrderID = wo.WorkOrderID
LEFT JOIN completion_gl AS cg
    ON cg.WorkOrderID = wo.WorkOrderID
LEFT JOIN close_summary AS cls
    ON cls.WorkOrderID = wo.WorkOrderID
LEFT JOIN close_gl AS clg
    ON clg.WorkOrderID = wo.WorkOrderID
ORDER BY
    date(wo.ReleasedDate),
    wo.WorkOrderNumber;
