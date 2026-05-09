-- Teaching objective: Review sales commission expense by sales rep, revenue type, customer segment, and invoice month.
-- Main tables: SalesCommissionAccrual, SalesCommissionAdjustment, Employee, Customer.
-- Expected output shape: One row per sales rep, revenue type, customer segment, and fiscal month.
-- Recommended build mode: Either.
-- Interpretation notes: Net commission expense subtracts credit-memo clawbacks from the original invoice-line commission accruals.

WITH adjustment_by_accrual AS (
    SELECT
        SalesCommissionAccrualID,
        ROUND(SUM(CommissionBaseReductionAmount), 2) AS ClawedBackBaseAmount,
        ROUND(SUM(CommissionAdjustmentAmount), 2) AS ClawbackAmount
    FROM SalesCommissionAdjustment
    GROUP BY SalesCommissionAccrualID
),
commission_detail AS (
    SELECT
        CAST(strftime('%Y', sca.AccrualDate) AS INTEGER) AS FiscalYear,
        CAST(strftime('%m', sca.AccrualDate) AS INTEGER) AS FiscalPeriod,
        sca.SalesRepEmployeeID,
        e.EmployeeName AS SalesRepName,
        sca.RevenueType,
        sca.CustomerSegment,
        sca.SalesInvoiceLineID,
        sca.CommissionBaseAmount,
        sca.CommissionRatePct,
        sca.CommissionAmount,
        COALESCE(aba.ClawedBackBaseAmount, 0) AS ClawedBackBaseAmount,
        COALESCE(aba.ClawbackAmount, 0) AS ClawbackAmount
    FROM SalesCommissionAccrual AS sca
    JOIN Employee AS e
        ON e.EmployeeID = sca.SalesRepEmployeeID
    LEFT JOIN adjustment_by_accrual AS aba
        ON aba.SalesCommissionAccrualID = sca.SalesCommissionAccrualID
)
SELECT
    FiscalYear,
    FiscalPeriod,
    SalesRepName,
    RevenueType,
    CustomerSegment,
    COUNT(DISTINCT SalesInvoiceLineID) AS CommissionedInvoiceLineCount,
    ROUND(SUM(CommissionBaseAmount), 2) AS CommissionBaseAmount,
    ROUND(AVG(CommissionRatePct) * 100, 2) AS AverageCommissionRatePct,
    ROUND(SUM(CommissionAmount), 2) AS GrossCommissionExpense,
    ROUND(SUM(ClawedBackBaseAmount), 2) AS ClawedBackBaseAmount,
    ROUND(SUM(ClawbackAmount), 2) AS ClawbackAmount,
    ROUND(SUM(CommissionAmount) - SUM(ClawbackAmount), 2) AS NetCommissionExpense
FROM commission_detail
GROUP BY
    FiscalYear,
    FiscalPeriod,
    SalesRepName,
    RevenueType,
    CustomerSegment
ORDER BY
    FiscalYear,
    FiscalPeriod,
    NetCommissionExpense DESC,
    SalesRepName,
    RevenueType,
    CustomerSegment;
