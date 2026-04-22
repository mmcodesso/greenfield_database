-- Teaching objective: Roll forward fixed-asset gross cost, accumulated depreciation, and net book value by behavior group.
-- Main tables: FixedAsset, FixedAssetEvent, JournalEntry.
-- Output shape: One row per fiscal month and asset behavior group.
-- Interpretation notes: The behavior groups separate manufacturing, warehouse, and office/showroom assets so students can compare product-cost versus operating-expense depreciation behavior.

WITH closed_years AS (
    SELECT
        CAST(substr(PostingDate, 1, 4) AS INTEGER) AS FiscalYear
    FROM JournalEntry
    WHERE EntryType IN (
        'Year-End Close - P&L to Income Summary',
        'Year-End Close - Income Summary to Retained Earnings'
    )
    GROUP BY CAST(substr(PostingDate, 1, 4) AS INTEGER)
    HAVING COUNT(DISTINCT EntryType) = 2
),
period_numbers AS (
    SELECT 1 AS FiscalPeriod
    UNION ALL SELECT 2
    UNION ALL SELECT 3
    UNION ALL SELECT 4
    UNION ALL SELECT 5
    UNION ALL SELECT 6
    UNION ALL SELECT 7
    UNION ALL SELECT 8
    UNION ALL SELECT 9
    UNION ALL SELECT 10
    UNION ALL SELECT 11
    UNION ALL SELECT 12
),
reporting_periods AS (
    SELECT
        cy.FiscalYear,
        pn.FiscalPeriod,
        date(printf('%04d-%02d-01', cy.FiscalYear, pn.FiscalPeriod)) AS PeriodStart,
        date(printf('%04d-%02d-01', cy.FiscalYear, pn.FiscalPeriod), '+1 month', '-1 day') AS PeriodEnd
    FROM closed_years AS cy
    CROSS JOIN period_numbers AS pn
),
horizon AS (
    SELECT MIN(PeriodStart) AS HorizonStart
    FROM reporting_periods
),
behavior_groups AS (
    SELECT DISTINCT BehaviorGroup
    FROM FixedAsset
),
asset_periods AS (
    SELECT
        rp.FiscalYear,
        rp.FiscalPeriod,
        rp.PeriodStart,
        rp.PeriodEnd,
        bg.BehaviorGroup,
        fa.FixedAssetID,
        fa.AssetCode,
        COALESCE(fa.OriginalCost, 0) AS OriginalCost,
        COALESCE(fa.OpeningAccumulatedDepreciation, 0) AS OpeningAccumulatedDepreciation,
        COALESCE(fa.ResidualValue, 0) AS ResidualValue,
        COALESCE(fa.UsefulLifeMonths, 0) AS UsefulLifeMonths,
        date(fa.InServiceDate) AS InServiceDate,
        CASE
            WHEN fa.DisposalDate IS NOT NULL THEN date(fa.DisposalDate)
            ELSE NULL
        END AS DisposalDate,
        CASE
            WHEN fa.FixedAssetID IS NOT NULL
                THEN date(strftime('%Y-%m-01', fa.InServiceDate), '+1 month')
            ELSE NULL
        END AS FirstDepreciationMonth,
        CASE
            WHEN COALESCE(fa.UsefulLifeMonths, 0) > 0
                THEN ROUND((COALESCE(fa.OriginalCost, 0) - COALESCE(fa.ResidualValue, 0)) / fa.UsefulLifeMonths, 2)
            ELSE 0
        END AS MonthlyDepreciation,
        CASE
            WHEN COALESCE(fa.UsefulLifeMonths, 0) > 0
             AND ROUND((COALESCE(fa.OriginalCost, 0) - COALESCE(fa.ResidualValue, 0)) / fa.UsefulLifeMonths, 2) > 0
                THEN CAST(
                    ROUND(
                        COALESCE(fa.OpeningAccumulatedDepreciation, 0)
                        / ROUND((COALESCE(fa.OriginalCost, 0) - COALESCE(fa.ResidualValue, 0)) / fa.UsefulLifeMonths, 2),
                        0
                    ) AS INTEGER
                )
            ELSE 0
        END AS OpeningMonthsDepreciated,
        CASE
            WHEN fa.DisposalDate IS NOT NULL
                THEN date(strftime('%Y-%m-01', fa.DisposalDate))
            ELSE NULL
        END AS DisposalMonth,
        CASE
            WHEN fa.FixedAssetID IS NOT NULL
             AND date(strftime('%Y-%m-01', fa.InServiceDate), '+1 month') > (SELECT HorizonStart FROM horizon)
                THEN date(strftime('%Y-%m-01', fa.InServiceDate), '+1 month')
            ELSE (SELECT HorizonStart FROM horizon)
        END AS DepreciationStartMonth
    FROM reporting_periods AS rp
    CROSS JOIN behavior_groups AS bg
    LEFT JOIN FixedAsset AS fa
        ON fa.BehaviorGroup = bg.BehaviorGroup
),
asset_rollforward AS (
    SELECT
        ap.FiscalYear,
        ap.FiscalPeriod,
        ap.BehaviorGroup,
        ap.FixedAssetID,
        CASE
            WHEN ap.FixedAssetID IS NOT NULL
             AND ap.InServiceDate < ap.PeriodStart
             AND (ap.DisposalDate IS NULL OR ap.DisposalDate >= ap.PeriodStart)
                THEN ROUND(ap.OriginalCost, 2)
            ELSE 0
        END AS OpeningGrossCost,
        CASE
            WHEN ap.FixedAssetID IS NOT NULL
             AND ap.InServiceDate >= ap.PeriodStart
             AND ap.InServiceDate <= ap.PeriodEnd
                THEN ROUND(ap.OriginalCost, 2)
            ELSE 0
        END AS AdditionsAndImprovements,
        CASE
            WHEN ap.FixedAssetID IS NOT NULL
             AND ap.DisposalDate >= ap.PeriodStart
             AND ap.DisposalDate <= ap.PeriodEnd
                THEN ROUND(ap.OriginalCost, 2)
            ELSE 0
        END AS DisposalsAtCost,
        CASE
            WHEN ap.FixedAssetID IS NOT NULL
             AND ap.InServiceDate <= ap.PeriodEnd
             AND (ap.DisposalDate IS NULL OR ap.DisposalDate > ap.PeriodEnd)
                THEN ROUND(ap.OriginalCost, 2)
            ELSE 0
        END AS EndingGrossCost,
        CASE
            WHEN ap.FixedAssetID IS NULL
             OR ap.InServiceDate >= ap.PeriodStart
             OR (ap.DisposalDate IS NOT NULL AND ap.DisposalDate < ap.PeriodStart)
                THEN 0
            WHEN ap.MonthlyDepreciation <= 0
                THEN ROUND(ap.OpeningAccumulatedDepreciation, 2)
            ELSE ROUND(
                ap.OpeningAccumulatedDepreciation
                + (
                    MIN(
                        MAX(ap.UsefulLifeMonths - ap.OpeningMonthsDepreciated, 0),
                        MAX(
                            (
                                (CAST(strftime('%Y', ap.PeriodStart) AS INTEGER) - CAST(strftime('%Y', ap.DepreciationStartMonth) AS INTEGER)) * 12
                                + (CAST(strftime('%m', ap.PeriodStart) AS INTEGER) - CAST(strftime('%m', ap.DepreciationStartMonth) AS INTEGER))
                            ),
                            0
                        )
                    ) * ap.MonthlyDepreciation
                ),
                2
            )
        END AS OpeningAccumulatedDepreciation,
        CASE
            WHEN ap.FixedAssetID IS NULL
             OR ap.MonthlyDepreciation <= 0
             OR ap.InServiceDate > ap.PeriodEnd
             OR ap.PeriodStart < ap.DepreciationStartMonth
             OR (ap.DisposalMonth IS NOT NULL AND ap.PeriodStart >= ap.DisposalMonth)
                THEN 0
            WHEN (
                ap.OpeningAccumulatedDepreciation
                + (
                    MIN(
                        MAX(ap.UsefulLifeMonths - ap.OpeningMonthsDepreciated, 0),
                        MAX(
                            (
                                (CAST(strftime('%Y', ap.PeriodStart) AS INTEGER) - CAST(strftime('%Y', ap.DepreciationStartMonth) AS INTEGER)) * 12
                                + (CAST(strftime('%m', ap.PeriodStart) AS INTEGER) - CAST(strftime('%m', ap.DepreciationStartMonth) AS INTEGER))
                            ),
                            0
                        )
                    ) * ap.MonthlyDepreciation
                )
            ) >= (ap.OriginalCost - ap.ResidualValue)
                THEN 0
            ELSE ROUND(
                MIN(
                    ap.MonthlyDepreciation,
                    (ap.OriginalCost - ap.ResidualValue)
                    - (
                        ap.OpeningAccumulatedDepreciation
                        + (
                            MIN(
                                MAX(ap.UsefulLifeMonths - ap.OpeningMonthsDepreciated, 0),
                                MAX(
                                    (
                                        (CAST(strftime('%Y', ap.PeriodStart) AS INTEGER) - CAST(strftime('%Y', ap.DepreciationStartMonth) AS INTEGER)) * 12
                                        + (CAST(strftime('%m', ap.PeriodStart) AS INTEGER) - CAST(strftime('%m', ap.DepreciationStartMonth) AS INTEGER))
                                    ),
                                    0
                                )
                            ) * ap.MonthlyDepreciation
                        )
                    )
                ),
                2
            )
        END AS DepreciationExpense,
        CASE
            WHEN ap.FixedAssetID IS NOT NULL
             AND ap.DisposalDate >= ap.PeriodStart
             AND ap.DisposalDate <= ap.PeriodEnd
                THEN CASE
                    WHEN ap.MonthlyDepreciation <= 0
                        THEN ROUND(ap.OpeningAccumulatedDepreciation, 2)
                    ELSE ROUND(
                        ap.OpeningAccumulatedDepreciation
                        + (
                            MIN(
                                MAX(ap.UsefulLifeMonths - ap.OpeningMonthsDepreciated, 0),
                                MAX(
                                    (
                                        (CAST(strftime('%Y', ap.PeriodStart) AS INTEGER) - CAST(strftime('%Y', ap.DepreciationStartMonth) AS INTEGER)) * 12
                                        + (CAST(strftime('%m', ap.PeriodStart) AS INTEGER) - CAST(strftime('%m', ap.DepreciationStartMonth) AS INTEGER))
                                    ),
                                    0
                                )
                            ) * ap.MonthlyDepreciation
                        ),
                        2
                    )
                END
            ELSE 0
        END AS AccumulatedDepreciationRelievedOnDisposal
    FROM asset_periods AS ap
),
group_rollforward AS (
    SELECT
        FiscalYear,
        FiscalPeriod,
        BehaviorGroup,
        ROUND(SUM(OpeningGrossCost), 2) AS OpeningGrossCost,
        ROUND(SUM(AdditionsAndImprovements), 2) AS AdditionsAndImprovements,
        ROUND(SUM(DisposalsAtCost), 2) AS DisposalsAtCost,
        ROUND(SUM(EndingGrossCost), 2) AS EndingGrossCost,
        ROUND(SUM(OpeningAccumulatedDepreciation), 2) AS OpeningAccumulatedDepreciation,
        ROUND(SUM(DepreciationExpense), 2) AS DepreciationExpense,
        ROUND(SUM(AccumulatedDepreciationRelievedOnDisposal), 2) AS AccumulatedDepreciationRelievedOnDisposal
    FROM asset_rollforward
    GROUP BY FiscalYear, FiscalPeriod, BehaviorGroup
)
SELECT
    FiscalYear,
    FiscalPeriod,
    BehaviorGroup,
    OpeningGrossCost,
    AdditionsAndImprovements,
    DisposalsAtCost,
    EndingGrossCost,
    OpeningAccumulatedDepreciation,
    DepreciationExpense,
    AccumulatedDepreciationRelievedOnDisposal,
    ROUND(
        OpeningAccumulatedDepreciation
        + DepreciationExpense
        - AccumulatedDepreciationRelievedOnDisposal,
        2
    ) AS EndingAccumulatedDepreciation,
    ROUND(
        EndingGrossCost
        - (
            OpeningAccumulatedDepreciation
            + DepreciationExpense
            - AccumulatedDepreciationRelievedOnDisposal
        ),
        2
    ) AS EndingNetBookValue
FROM group_rollforward
ORDER BY FiscalYear, FiscalPeriod, BehaviorGroup;
