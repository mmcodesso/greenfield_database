-- Teaching objective: Compare monthly budget to posted operating expense by cost center and account.
-- Main tables: Budget, CostCenter, Account, GLEntry, JournalEntry.
-- Output shape: One row per fiscal year, month, cost center, and budgeted account.
-- Interpretation notes: Actuals include operating-expense postings and exclude year-end close entries.

WITH actual_expense AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod AS Month,
        gl.CostCenterID,
        gl.AccountID,
        ROUND(SUM(gl.Debit - gl.Credit), 2) AS ActualAmount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON gl.SourceDocumentType = 'JournalEntry'
       AND gl.VoucherNumber = je.EntryNumber
    WHERE gl.CostCenterID IS NOT NULL
      AND a.AccountType = 'Expense'
      AND a.AccountSubType = 'Operating Expense'
      AND (
            gl.SourceDocumentType <> 'JournalEntry'
            OR COALESCE(je.EntryType, '') NOT LIKE 'Year-End Close%'
        )
    GROUP BY gl.FiscalYear, gl.FiscalPeriod, gl.CostCenterID, gl.AccountID
)
SELECT
    b.FiscalYear,
    b.Month,
    cc.CostCenterName,
    a.AccountNumber,
    a.AccountName,
    ROUND(b.BudgetAmount, 2) AS BudgetAmount,
    ROUND(COALESCE(ae.ActualAmount, 0), 2) AS ActualAmount,
    ROUND(COALESCE(ae.ActualAmount, 0) - b.BudgetAmount, 2) AS VarianceAmount,
    CASE
        WHEN b.BudgetAmount = 0 THEN NULL
        ELSE ROUND((COALESCE(ae.ActualAmount, 0) - b.BudgetAmount) / b.BudgetAmount * 100.0, 2)
    END AS VariancePct
FROM Budget AS b
JOIN CostCenter AS cc
    ON cc.CostCenterID = b.CostCenterID
JOIN Account AS a
    ON a.AccountID = b.AccountID
LEFT JOIN actual_expense AS ae
    ON ae.FiscalYear = b.FiscalYear
   AND ae.Month = b.Month
   AND ae.CostCenterID = b.CostCenterID
   AND ae.AccountID = b.AccountID
WHERE a.AccountType = 'Expense'
  AND a.AccountSubType = 'Operating Expense'
ORDER BY b.FiscalYear, b.Month, cc.CostCenterName, a.AccountNumber;
