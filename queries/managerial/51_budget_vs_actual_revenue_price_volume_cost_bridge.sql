-- Teaching objective: Compare budgeted and actual quantity, revenue, price realization, and standard-cost consumption by collection and style family.
-- Main tables: BudgetLine, Item, SalesInvoice, SalesInvoiceLine.
-- Output shape: One row per fiscal month, collection, and style family.
-- Interpretation notes: Actual cost uses current item standard cost at the billed item level so the bridge stays comparable to the budget basis.

WITH budget_item_month AS (
    SELECT
        bl.FiscalYear,
        bl.Month AS FiscalPeriod,
        bl.ItemID,
        ROUND(SUM(CASE WHEN bl.BudgetCategory = 'Revenue' THEN COALESCE(bl.Quantity, 0) ELSE 0 END), 2) AS BudgetQuantity,
        ROUND(SUM(CASE WHEN bl.BudgetCategory = 'Revenue' THEN bl.BudgetAmount ELSE 0 END), 2) AS BudgetNetRevenue,
        ROUND(SUM(CASE WHEN bl.BudgetCategory = 'COGS' THEN bl.BudgetAmount ELSE 0 END), 2) AS BudgetCOGS
    FROM BudgetLine AS bl
    WHERE bl.ItemID IS NOT NULL
      AND bl.BudgetCategory IN ('Revenue', 'COGS')
    GROUP BY bl.FiscalYear, bl.Month, bl.ItemID
),
budget_portfolio AS (
    SELECT
        bim.FiscalYear,
        bim.FiscalPeriod,
        COALESCE(i.CollectionName, 'Unassigned') AS CollectionName,
        COALESCE(i.StyleFamily, 'Unassigned') AS StyleFamily,
        ROUND(SUM(bim.BudgetQuantity), 2) AS BudgetQuantity,
        ROUND(SUM(bim.BudgetNetRevenue), 2) AS BudgetNetRevenue,
        ROUND(SUM(bim.BudgetCOGS), 2) AS BudgetCOGS
    FROM budget_item_month AS bim
    JOIN Item AS i
        ON i.ItemID = bim.ItemID
    GROUP BY
        bim.FiscalYear,
        bim.FiscalPeriod,
        COALESCE(i.CollectionName, 'Unassigned'),
        COALESCE(i.StyleFamily, 'Unassigned')
),
actual_item_month AS (
    SELECT
        CAST(substr(si.InvoiceDate, 1, 4) AS INTEGER) AS FiscalYear,
        CAST(substr(si.InvoiceDate, 6, 2) AS INTEGER) AS FiscalPeriod,
        sil.ItemID,
        ROUND(SUM(sil.Quantity), 2) AS ActualQuantity,
        ROUND(SUM(sil.LineTotal), 2) AS ActualNetRevenue,
        ROUND(SUM(sil.Quantity * i.StandardCost), 2) AS ActualCOGS
    FROM SalesInvoiceLine AS sil
    JOIN SalesInvoice AS si
        ON si.SalesInvoiceID = sil.SalesInvoiceID
    JOIN Item AS i
        ON i.ItemID = sil.ItemID
    GROUP BY
        CAST(substr(si.InvoiceDate, 1, 4) AS INTEGER),
        CAST(substr(si.InvoiceDate, 6, 2) AS INTEGER),
        sil.ItemID
),
actual_portfolio AS (
    SELECT
        aim.FiscalYear,
        aim.FiscalPeriod,
        COALESCE(i.CollectionName, 'Unassigned') AS CollectionName,
        COALESCE(i.StyleFamily, 'Unassigned') AS StyleFamily,
        ROUND(SUM(aim.ActualQuantity), 2) AS ActualQuantity,
        ROUND(SUM(aim.ActualNetRevenue), 2) AS ActualNetRevenue,
        ROUND(SUM(aim.ActualCOGS), 2) AS ActualCOGS
    FROM actual_item_month AS aim
    JOIN Item AS i
        ON i.ItemID = aim.ItemID
    GROUP BY
        aim.FiscalYear,
        aim.FiscalPeriod,
        COALESCE(i.CollectionName, 'Unassigned'),
        COALESCE(i.StyleFamily, 'Unassigned')
),
bridge_base AS (
    SELECT
        bp.FiscalYear,
        bp.FiscalPeriod,
        bp.CollectionName,
        bp.StyleFamily,
        ROUND(COALESCE(bp.BudgetQuantity, 0), 2) AS BudgetQuantity,
        ROUND(COALESCE(ap.ActualQuantity, 0), 2) AS ActualQuantity,
        ROUND(COALESCE(bp.BudgetNetRevenue, 0), 2) AS BudgetNetRevenue,
        ROUND(COALESCE(ap.ActualNetRevenue, 0), 2) AS ActualNetRevenue,
        ROUND(COALESCE(bp.BudgetCOGS, 0), 2) AS BudgetCOGS,
        ROUND(COALESCE(ap.ActualCOGS, 0), 2) AS ActualCOGS
    FROM budget_portfolio AS bp
    LEFT JOIN actual_portfolio AS ap
        ON ap.FiscalYear = bp.FiscalYear
       AND ap.FiscalPeriod = bp.FiscalPeriod
       AND ap.CollectionName = bp.CollectionName
       AND ap.StyleFamily = bp.StyleFamily

    UNION ALL

    SELECT
        ap.FiscalYear,
        ap.FiscalPeriod,
        ap.CollectionName,
        ap.StyleFamily,
        0.0 AS BudgetQuantity,
        ROUND(ap.ActualQuantity, 2) AS ActualQuantity,
        0.0 AS BudgetNetRevenue,
        ROUND(ap.ActualNetRevenue, 2) AS ActualNetRevenue,
        0.0 AS BudgetCOGS,
        ROUND(ap.ActualCOGS, 2) AS ActualCOGS
    FROM actual_portfolio AS ap
    LEFT JOIN budget_portfolio AS bp
        ON bp.FiscalYear = ap.FiscalYear
       AND bp.FiscalPeriod = ap.FiscalPeriod
       AND bp.CollectionName = ap.CollectionName
       AND bp.StyleFamily = ap.StyleFamily
    WHERE bp.FiscalYear IS NULL
)
SELECT
    FiscalYear,
    FiscalPeriod,
    CollectionName,
    StyleFamily,
    BudgetQuantity,
    ActualQuantity,
    BudgetNetRevenue,
    ActualNetRevenue,
    BudgetCOGS,
    ActualCOGS,
    ROUND(ActualNetRevenue - BudgetNetRevenue, 2) AS RevenueVariance,
    CASE
        WHEN ActualQuantity = 0 THEN NULL
        ELSE ROUND(
            (
                (ActualNetRevenue / NULLIF(ActualQuantity, 0))
                - (BudgetNetRevenue / NULLIF(BudgetQuantity, 0))
            ) * ActualQuantity,
            2
        )
    END AS PriceVariance,
    CASE
        WHEN BudgetQuantity = 0 THEN ROUND(ActualNetRevenue - BudgetNetRevenue, 2)
        ELSE ROUND((ActualQuantity - BudgetQuantity) * (BudgetNetRevenue / NULLIF(BudgetQuantity, 0)), 2)
    END AS VolumeVariance,
    CASE
        WHEN BudgetQuantity = 0 THEN ROUND(ActualCOGS - BudgetCOGS, 2)
        ELSE ROUND(ActualCOGS - (ActualQuantity * (BudgetCOGS / NULLIF(BudgetQuantity, 0))), 2)
    END AS CostVariance
FROM bridge_base
ORDER BY
    FiscalYear,
    FiscalPeriod,
    CollectionName,
    StyleFamily;
