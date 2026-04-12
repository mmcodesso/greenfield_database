-- Teaching objective: Compare billed sales, credits, net sales, standard cost, and gross margin by collection, style family, lifecycle, and supply mode.
-- Main tables: SalesInvoiceLine, ShipmentLine, CreditMemoLine, SalesReturnLine, Item.
-- Expected output shape: One row per item group, collection, style family, lifecycle status, and supply mode.
-- Recommended build mode: Either.
-- Interpretation notes: This is a financial view of product portfolio performance. Net sales reduce billed sales by credit memos, and net standard cost reduces shipped cost by returned standard cost.

WITH billed_sales AS (
    SELECT
        i.ItemGroup,
        COALESCE(i.CollectionName, '(No Collection)') AS CollectionName,
        COALESCE(i.StyleFamily, '(No Style Family)') AS StyleFamily,
        COALESCE(i.LifecycleStatus, '(No Lifecycle)') AS LifecycleStatus,
        COALESCE(i.SupplyMode, '(No Supply Mode)') AS SupplyMode,
        ROUND(SUM(sil.Quantity), 2) AS BilledQuantity,
        ROUND(SUM(sil.LineTotal), 2) AS BilledSales,
        ROUND(SUM(COALESCE(sl.ExtendedStandardCost, 0)), 2) AS BilledStandardCost
    FROM SalesInvoiceLine AS sil
    JOIN Item AS i
        ON i.ItemID = sil.ItemID
    LEFT JOIN ShipmentLine AS sl
        ON sl.ShipmentLineID = sil.ShipmentLineID
    GROUP BY
        i.ItemGroup,
        COALESCE(i.CollectionName, '(No Collection)'),
        COALESCE(i.StyleFamily, '(No Style Family)'),
        COALESCE(i.LifecycleStatus, '(No Lifecycle)'),
        COALESCE(i.SupplyMode, '(No Supply Mode)')
),
credited_returns AS (
    SELECT
        i.ItemGroup,
        COALESCE(i.CollectionName, '(No Collection)') AS CollectionName,
        COALESCE(i.StyleFamily, '(No Style Family)') AS StyleFamily,
        COALESCE(i.LifecycleStatus, '(No Lifecycle)') AS LifecycleStatus,
        COALESCE(i.SupplyMode, '(No Supply Mode)') AS SupplyMode,
        ROUND(SUM(cml.Quantity), 2) AS CreditedQuantity,
        ROUND(SUM(cml.LineTotal), 2) AS CreditValue,
        ROUND(SUM(COALESCE(srl.ExtendedStandardCost, 0)), 2) AS ReturnedStandardCost
    FROM CreditMemoLine AS cml
    JOIN Item AS i
        ON i.ItemID = cml.ItemID
    LEFT JOIN SalesReturnLine AS srl
        ON srl.SalesReturnLineID = cml.SalesReturnLineID
    GROUP BY
        i.ItemGroup,
        COALESCE(i.CollectionName, '(No Collection)'),
        COALESCE(i.StyleFamily, '(No Style Family)'),
        COALESCE(i.LifecycleStatus, '(No Lifecycle)'),
        COALESCE(i.SupplyMode, '(No Supply Mode)')
),
attribute_keys AS (
    SELECT ItemGroup, CollectionName, StyleFamily, LifecycleStatus, SupplyMode FROM billed_sales
    UNION
    SELECT ItemGroup, CollectionName, StyleFamily, LifecycleStatus, SupplyMode FROM credited_returns
)
SELECT
    ak.ItemGroup,
    ak.CollectionName,
    ak.StyleFamily,
    ak.LifecycleStatus,
    ak.SupplyMode,
    ROUND(COALESCE(bs.BilledQuantity, 0), 2) AS BilledQuantity,
    ROUND(COALESCE(cr.CreditedQuantity, 0), 2) AS CreditedReturnQuantity,
    ROUND(COALESCE(bs.BilledSales, 0), 2) AS BilledSales,
    ROUND(COALESCE(cr.CreditValue, 0), 2) AS CreditMemoValue,
    ROUND(COALESCE(bs.BilledSales, 0) - COALESCE(cr.CreditValue, 0), 2) AS NetSales,
    ROUND(COALESCE(bs.BilledStandardCost, 0) - COALESCE(cr.ReturnedStandardCost, 0), 2) AS NetStandardCost,
    ROUND(
        (COALESCE(bs.BilledSales, 0) - COALESCE(cr.CreditValue, 0))
        - (COALESCE(bs.BilledStandardCost, 0) - COALESCE(cr.ReturnedStandardCost, 0)),
        2
    ) AS GrossMargin,
    ROUND(
        CASE
            WHEN (COALESCE(bs.BilledSales, 0) - COALESCE(cr.CreditValue, 0)) = 0 THEN NULL
            ELSE (
                (
                    (COALESCE(bs.BilledSales, 0) - COALESCE(cr.CreditValue, 0))
                    - (COALESCE(bs.BilledStandardCost, 0) - COALESCE(cr.ReturnedStandardCost, 0))
                ) * 100.0
            ) / (COALESCE(bs.BilledSales, 0) - COALESCE(cr.CreditValue, 0))
        END,
        2
    ) AS GrossMarginPct
FROM attribute_keys AS ak
LEFT JOIN billed_sales AS bs
    ON bs.ItemGroup = ak.ItemGroup
   AND bs.CollectionName = ak.CollectionName
   AND bs.StyleFamily = ak.StyleFamily
   AND bs.LifecycleStatus = ak.LifecycleStatus
   AND bs.SupplyMode = ak.SupplyMode
LEFT JOIN credited_returns AS cr
    ON cr.ItemGroup = ak.ItemGroup
   AND cr.CollectionName = ak.CollectionName
   AND cr.StyleFamily = ak.StyleFamily
   AND cr.LifecycleStatus = ak.LifecycleStatus
   AND cr.SupplyMode = ak.SupplyMode
ORDER BY
    NetSales DESC,
    ak.ItemGroup,
    ak.CollectionName,
    ak.StyleFamily;
