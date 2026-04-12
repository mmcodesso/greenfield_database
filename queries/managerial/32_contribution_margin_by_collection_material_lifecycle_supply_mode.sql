-- Teaching objective: Compare contribution margin by collection, material, lifecycle, and supply mode.
-- Main tables: SalesInvoiceLine, CreditMemoLine, Item.
-- Expected output shape: One row per item group and portfolio attribute grouping.
-- Recommended build mode: Either.
-- Interpretation notes: Manufactured items exclude fixed overhead from variable cost. Purchased items use standard cost as the variable cost proxy in this starter query.

WITH item_costs AS (
    SELECT
        ItemID,
        ItemGroup,
        COALESCE(CollectionName, '(No Collection)') AS CollectionName,
        COALESCE(PrimaryMaterial, '(No Material)') AS PrimaryMaterial,
        COALESCE(LifecycleStatus, '(No Lifecycle)') AS LifecycleStatus,
        COALESCE(SupplyMode, '(No Supply Mode)') AS SupplyMode,
        CASE
            WHEN SupplyMode = 'Manufactured' THEN COALESCE(StandardCost, 0) - COALESCE(StandardFixedOverheadCost, 0)
            ELSE COALESCE(StandardCost, 0)
        END AS VariableUnitCost
    FROM Item
    WHERE RevenueAccountID IS NOT NULL
),
billed_activity AS (
    SELECT
        ic.ItemGroup,
        ic.CollectionName,
        ic.PrimaryMaterial,
        ic.LifecycleStatus,
        ic.SupplyMode,
        ROUND(SUM(sil.Quantity), 2) AS BilledQuantity,
        ROUND(SUM(sil.LineTotal), 2) AS BilledSales,
        ROUND(SUM(sil.Quantity * ic.VariableUnitCost), 2) AS BilledVariableCost
    FROM SalesInvoiceLine AS sil
    JOIN item_costs AS ic
        ON ic.ItemID = sil.ItemID
    GROUP BY
        ic.ItemGroup,
        ic.CollectionName,
        ic.PrimaryMaterial,
        ic.LifecycleStatus,
        ic.SupplyMode
),
credited_activity AS (
    SELECT
        ic.ItemGroup,
        ic.CollectionName,
        ic.PrimaryMaterial,
        ic.LifecycleStatus,
        ic.SupplyMode,
        ROUND(SUM(cml.Quantity), 2) AS CreditedQuantity,
        ROUND(SUM(cml.LineTotal), 2) AS CreditValue,
        ROUND(SUM(cml.Quantity * ic.VariableUnitCost), 2) AS ReturnedVariableCost
    FROM CreditMemoLine AS cml
    JOIN item_costs AS ic
        ON ic.ItemID = cml.ItemID
    GROUP BY
        ic.ItemGroup,
        ic.CollectionName,
        ic.PrimaryMaterial,
        ic.LifecycleStatus,
        ic.SupplyMode
),
attribute_keys AS (
    SELECT ItemGroup, CollectionName, PrimaryMaterial, LifecycleStatus, SupplyMode FROM billed_activity
    UNION
    SELECT ItemGroup, CollectionName, PrimaryMaterial, LifecycleStatus, SupplyMode FROM credited_activity
)
SELECT
    ak.ItemGroup,
    ak.CollectionName,
    ak.PrimaryMaterial,
    ak.LifecycleStatus,
    ak.SupplyMode,
    ROUND(COALESCE(ba.BilledQuantity, 0), 2) AS BilledQuantity,
    ROUND(COALESCE(ca.CreditedQuantity, 0), 2) AS CreditedQuantity,
    ROUND(COALESCE(ba.BilledSales, 0), 2) AS BilledSales,
    ROUND(COALESCE(ca.CreditValue, 0), 2) AS CreditMemoValue,
    ROUND(COALESCE(ba.BilledSales, 0) - COALESCE(ca.CreditValue, 0), 2) AS NetSales,
    ROUND(COALESCE(ba.BilledVariableCost, 0) - COALESCE(ca.ReturnedVariableCost, 0), 2) AS NetVariableCost,
    ROUND(
        (COALESCE(ba.BilledSales, 0) - COALESCE(ca.CreditValue, 0))
        - (COALESCE(ba.BilledVariableCost, 0) - COALESCE(ca.ReturnedVariableCost, 0)),
        2
    ) AS ContributionMargin,
    ROUND(
        CASE
            WHEN (COALESCE(ba.BilledSales, 0) - COALESCE(ca.CreditValue, 0)) = 0 THEN NULL
            ELSE (
                (
                    (COALESCE(ba.BilledSales, 0) - COALESCE(ca.CreditValue, 0))
                    - (COALESCE(ba.BilledVariableCost, 0) - COALESCE(ca.ReturnedVariableCost, 0))
                ) * 100.0
            ) / (COALESCE(ba.BilledSales, 0) - COALESCE(ca.CreditValue, 0))
        END,
        2
    ) AS ContributionMarginPct
FROM attribute_keys AS ak
LEFT JOIN billed_activity AS ba
    ON ba.ItemGroup = ak.ItemGroup
   AND ba.CollectionName = ak.CollectionName
   AND ba.PrimaryMaterial = ak.PrimaryMaterial
   AND ba.LifecycleStatus = ak.LifecycleStatus
   AND ba.SupplyMode = ak.SupplyMode
LEFT JOIN credited_activity AS ca
    ON ca.ItemGroup = ak.ItemGroup
   AND ca.CollectionName = ak.CollectionName
   AND ca.PrimaryMaterial = ak.PrimaryMaterial
   AND ca.LifecycleStatus = ak.LifecycleStatus
   AND ca.SupplyMode = ak.SupplyMode
ORDER BY
    ContributionMargin DESC,
    ak.ItemGroup,
    ak.CollectionName,
    ak.PrimaryMaterial;
