-- Teaching objective: Bridge manufacturing material, conversion, and variance activity by period.
-- Main tables: MaterialIssue, MaterialIssueLine, ProductionCompletion, ProductionCompletionLine, WorkOrderClose, GLEntry, Account.
-- Expected output shape: One row per month with operational cost components and ledger-account impact.
-- Recommended build mode: Either.
-- Interpretation notes: This query helps students connect operational manufacturing activity to WIP, manufacturing clearing, and variance balances.

WITH issue_cost AS (
    SELECT
        substr(mi.IssueDate, 1, 7) AS PeriodMonth,
        ROUND(SUM(mil.ExtendedStandardCost), 2) AS MaterialIssuedCost
    FROM MaterialIssue AS mi
    JOIN MaterialIssueLine AS mil
        ON mil.MaterialIssueID = mi.MaterialIssueID
    GROUP BY substr(mi.IssueDate, 1, 7)
),
completion_cost AS (
    SELECT
        substr(pc.CompletionDate, 1, 7) AS PeriodMonth,
        ROUND(SUM(pcl.ExtendedStandardMaterialCost), 2) AS CompletedMaterialCost,
        ROUND(SUM(pcl.ExtendedStandardDirectLaborCost), 2) AS CompletedDirectLaborCost,
        ROUND(SUM(pcl.ExtendedStandardVariableOverheadCost), 2) AS CompletedVariableOverheadCost,
        ROUND(SUM(pcl.ExtendedStandardFixedOverheadCost), 2) AS CompletedFixedOverheadCost,
        ROUND(SUM(pcl.ExtendedStandardTotalCost), 2) AS CompletedTotalCost
    FROM ProductionCompletion AS pc
    JOIN ProductionCompletionLine AS pcl
        ON pcl.ProductionCompletionID = pc.ProductionCompletionID
    GROUP BY substr(pc.CompletionDate, 1, 7)
),
variance_cost AS (
    SELECT
        substr(CloseDate, 1, 7) AS PeriodMonth,
        ROUND(SUM(MaterialVarianceAmount), 2) AS MaterialVarianceAmount,
        ROUND(SUM(DirectLaborVarianceAmount), 2) AS DirectLaborVarianceAmount,
        ROUND(SUM(OverheadVarianceAmount), 2) AS OverheadVarianceAmount,
        ROUND(SUM(TotalVarianceAmount), 2) AS TotalVarianceAmount
    FROM WorkOrderClose
    GROUP BY substr(CloseDate, 1, 7)
),
depreciation_cost AS (
    SELECT
        substr(gl.PostingDate, 1, 7) AS PeriodMonth,
        ROUND(SUM(gl.Debit - gl.Credit), 2) AS ManufacturingDepreciationAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountNumber = '1090'
      AND COALESCE(je.EntryType, '') = 'Depreciation'
    GROUP BY substr(gl.PostingDate, 1, 7)
),
ledger_cost AS (
    SELECT
        substr(gl.PostingDate, 1, 7) AS PeriodMonth,
        ROUND(SUM(CASE WHEN a.AccountNumber = '1046' THEN gl.Debit - gl.Credit ELSE 0 END), 2) AS WipNetLedgerMovement,
        ROUND(SUM(CASE WHEN a.AccountNumber = '1090' THEN gl.Debit - gl.Credit ELSE 0 END), 2) AS ManufacturingClearingNetMovement,
        ROUND(SUM(CASE WHEN a.AccountNumber = '5080' THEN gl.Debit - gl.Credit ELSE 0 END), 2) AS ManufacturingVarianceNetMovement
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE a.AccountNumber IN ('1046', '1090', '5080')
    GROUP BY substr(gl.PostingDate, 1, 7)
),
months AS (
    SELECT PeriodMonth FROM issue_cost
    UNION
    SELECT PeriodMonth FROM completion_cost
    UNION
    SELECT PeriodMonth FROM variance_cost
    UNION
    SELECT PeriodMonth FROM depreciation_cost
    UNION
    SELECT PeriodMonth FROM ledger_cost
)
SELECT
    m.PeriodMonth,
    ROUND(COALESCE(ic.MaterialIssuedCost, 0), 2) AS MaterialIssuedCost,
    ROUND(COALESCE(cc.CompletedMaterialCost, 0), 2) AS CompletedMaterialCost,
    ROUND(COALESCE(cc.CompletedDirectLaborCost, 0), 2) AS CompletedDirectLaborCost,
    ROUND(COALESCE(cc.CompletedVariableOverheadCost, 0), 2) AS CompletedVariableOverheadCost,
    ROUND(COALESCE(cc.CompletedFixedOverheadCost, 0), 2) AS CompletedFixedOverheadCost,
    ROUND(COALESCE(cc.CompletedTotalCost, 0), 2) AS CompletedTotalCost,
    ROUND(COALESCE(vc.MaterialVarianceAmount, 0), 2) AS MaterialVarianceAmount,
    ROUND(COALESCE(vc.DirectLaborVarianceAmount, 0), 2) AS DirectLaborVarianceAmount,
    ROUND(COALESCE(vc.OverheadVarianceAmount, 0), 2) AS OverheadVarianceAmount,
    ROUND(COALESCE(vc.TotalVarianceAmount, 0), 2) AS TotalVarianceAmount,
    ROUND(COALESCE(dc.ManufacturingDepreciationAmount, 0), 2) AS ManufacturingDepreciationAmount,
    ROUND(COALESCE(lc.WipNetLedgerMovement, 0), 2) AS WipNetLedgerMovement,
    ROUND(COALESCE(lc.ManufacturingClearingNetMovement, 0), 2) AS ManufacturingClearingNetMovement,
    ROUND(COALESCE(lc.ManufacturingVarianceNetMovement, 0), 2) AS ManufacturingVarianceNetMovement
FROM months AS m
LEFT JOIN issue_cost AS ic
    ON ic.PeriodMonth = m.PeriodMonth
LEFT JOIN completion_cost AS cc
    ON cc.PeriodMonth = m.PeriodMonth
LEFT JOIN variance_cost AS vc
    ON vc.PeriodMonth = m.PeriodMonth
LEFT JOIN depreciation_cost AS dc
    ON dc.PeriodMonth = m.PeriodMonth
LEFT JOIN ledger_cost AS lc
    ON lc.PeriodMonth = m.PeriodMonth
ORDER BY m.PeriodMonth;
