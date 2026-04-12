-- Teaching objective: Review the product portfolio by collection, style family, lifecycle, and supply mode with both SKU counts and billed activity.
-- Main tables: Item, SalesInvoiceLine.
-- Expected output shape: One row per sellable portfolio grouping.
-- Recommended build mode: Either.
-- Interpretation notes: This query starts from the item master, then layers billed activity on top so students can compare assortment breadth to revenue concentration.

WITH sellable_items AS (
    SELECT
        ItemID,
        ItemGroup,
        COALESCE(CollectionName, '(No Collection)') AS CollectionName,
        COALESCE(StyleFamily, '(No Style Family)') AS StyleFamily,
        COALESCE(LifecycleStatus, '(No Lifecycle)') AS LifecycleStatus,
        COALESCE(SupplyMode, '(No Supply Mode)') AS SupplyMode,
        IsActive,
        StandardCost,
        ListPrice
    FROM Item
    WHERE RevenueAccountID IS NOT NULL
),
portfolio_summary AS (
    SELECT
        ItemGroup,
        CollectionName,
        StyleFamily,
        LifecycleStatus,
        SupplyMode,
        COUNT(*) AS PortfolioSKUCount,
        SUM(CASE WHEN CAST(IsActive AS INTEGER) = 1 THEN 1 ELSE 0 END) AS ActiveSKUCount,
        ROUND(AVG(ListPrice), 2) AS AvgListPrice,
        ROUND(AVG(StandardCost), 2) AS AvgStandardCost
    FROM sellable_items
    GROUP BY
        ItemGroup,
        CollectionName,
        StyleFamily,
        LifecycleStatus,
        SupplyMode
),
billed_activity AS (
    SELECT
        si.ItemGroup,
        si.CollectionName,
        si.StyleFamily,
        si.LifecycleStatus,
        si.SupplyMode,
        COUNT(DISTINCT sil.ItemID) AS SoldSKUCount,
        ROUND(SUM(sil.Quantity), 2) AS BilledQuantity,
        ROUND(SUM(sil.LineTotal), 2) AS BilledSales
    FROM SalesInvoiceLine AS sil
    JOIN sellable_items AS si
        ON si.ItemID = sil.ItemID
    GROUP BY
        si.ItemGroup,
        si.CollectionName,
        si.StyleFamily,
        si.LifecycleStatus,
        si.SupplyMode
)
SELECT
    ps.ItemGroup,
    ps.CollectionName,
    ps.StyleFamily,
    ps.LifecycleStatus,
    ps.SupplyMode,
    ps.PortfolioSKUCount,
    ps.ActiveSKUCount,
    COALESCE(ba.SoldSKUCount, 0) AS SoldSKUCount,
    ROUND(COALESCE(ba.BilledQuantity, 0), 2) AS BilledQuantity,
    ROUND(COALESCE(ba.BilledSales, 0), 2) AS BilledSales,
    ps.AvgListPrice,
    ps.AvgStandardCost
FROM portfolio_summary AS ps
LEFT JOIN billed_activity AS ba
    ON ba.ItemGroup = ps.ItemGroup
   AND ba.CollectionName = ps.CollectionName
   AND ba.StyleFamily = ps.StyleFamily
   AND ba.LifecycleStatus = ps.LifecycleStatus
   AND ba.SupplyMode = ps.SupplyMode
ORDER BY
    COALESCE(ba.BilledSales, 0) DESC,
    ps.ItemGroup,
    ps.CollectionName,
    ps.StyleFamily;
