-- Teaching objective: Show the note-payable amortization schedule and cash impact tied to CAPEX financing.
-- Main tables: DebtAgreement, DebtScheduleLine, FixedAsset.
-- Output shape: One row per scheduled debt payment line.
-- Interpretation notes: Principal repayments belong to financing cash flow, while interest cash remains part of operating cash flow.

WITH schedule AS (
    SELECT
        da.AgreementNumber,
        fa.AssetCode,
        fa.AssetDescription,
        fa.BehaviorGroup,
        date(dsl.PaymentDate) AS PaymentDate,
        CAST(substr(dsl.PaymentDate, 1, 4) AS INTEGER) AS FiscalYear,
        CAST(substr(dsl.PaymentDate, 6, 2) AS INTEGER) AS FiscalPeriod,
        dsl.PaymentSequence,
        ROUND(dsl.BeginningPrincipal, 2) AS BeginningPrincipal,
        ROUND(dsl.PrincipalAmount, 2) AS PrincipalAmount,
        ROUND(dsl.InterestAmount, 2) AS InterestAmount,
        ROUND(dsl.PaymentAmount, 2) AS PaymentAmount,
        ROUND(dsl.EndingPrincipal, 2) AS EndingPrincipal,
        COALESCE(dsl.Status, 'Scheduled') AS ScheduleStatus
    FROM DebtScheduleLine AS dsl
    JOIN DebtAgreement AS da
        ON da.DebtAgreementID = dsl.DebtAgreementID
    JOIN FixedAsset AS fa
        ON fa.FixedAssetID = da.FixedAssetID
)
SELECT
    AgreementNumber,
    AssetCode,
    AssetDescription,
    BehaviorGroup,
    PaymentDate,
    FiscalYear,
    FiscalPeriod,
    PaymentSequence,
    BeginningPrincipal,
    PrincipalAmount,
    InterestAmount,
    PaymentAmount,
    EndingPrincipal,
    ROUND(
        SUM(PrincipalAmount) OVER (
            PARTITION BY AgreementNumber
            ORDER BY PaymentSequence
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS CumulativePrincipalPaid,
    ROUND(
        SUM(InterestAmount) OVER (
            PARTITION BY AgreementNumber
            ORDER BY PaymentSequence
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS CumulativeInterestPaid,
    ScheduleStatus
FROM schedule
ORDER BY PaymentDate, AgreementNumber, PaymentSequence;
