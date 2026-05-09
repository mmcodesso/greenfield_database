-- Teaching objective: Reconcile sales commission payable activity from invoice accrual through clawback and payment.
-- Main tables: GLEntry, Account, SalesCommissionAccrual, SalesCommissionAdjustment, SalesCommissionPayment.
-- Expected output shape: One row per fiscal period with sales commission payable activity and ending balance.
-- Recommended build mode: Either.
-- Interpretation notes: Credits increase commission payable through invoice-line accruals. Debits reduce payable through credit-memo clawbacks and monthly payments.

WITH commission_payable_activity AS (
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        ROUND(SUM(CASE WHEN gl.SourceDocumentType = 'SalesCommissionAccrual' THEN gl.Credit ELSE 0 END), 2) AS AccruedCommissionAmount,
        ROUND(SUM(CASE WHEN gl.SourceDocumentType = 'SalesCommissionAdjustment' THEN gl.Debit ELSE 0 END), 2) AS ClawbackAmount,
        ROUND(SUM(CASE WHEN gl.SourceDocumentType = 'SalesCommissionPayment' THEN gl.Debit ELSE 0 END), 2) AS PaymentAmount,
        ROUND(SUM(gl.Credit), 2) AS CreditAmount,
        ROUND(SUM(gl.Debit), 2) AS DebitAmount,
        ROUND(SUM(gl.Credit - gl.Debit), 2) AS NetIncrease
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    WHERE a.AccountNumber = '2034'
    GROUP BY gl.FiscalYear, gl.FiscalPeriod
)
SELECT
    cpa.FiscalYear,
    cpa.FiscalPeriod,
    cpa.AccruedCommissionAmount,
    cpa.ClawbackAmount,
    cpa.PaymentAmount,
    cpa.CreditAmount,
    cpa.DebitAmount,
    cpa.NetIncrease,
    ROUND(
        SUM(cpa.NetIncrease) OVER (
            ORDER BY cpa.FiscalYear, cpa.FiscalPeriod
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS EndingCommissionPayable
FROM commission_payable_activity AS cpa
ORDER BY cpa.FiscalYear, cpa.FiscalPeriod;
