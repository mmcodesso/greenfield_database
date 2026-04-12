-- Teaching objective: Compare return, credit, and refund impact by collection and lifecycle status.
-- Main tables: SalesInvoiceLine, CreditMemo, CreditMemoLine, CustomerRefund, Item.
-- Expected output shape: One row per item group, collection, and lifecycle grouping.
-- Recommended build mode: Either; anomaly-enabled builds may show stronger refund patterns.
-- Interpretation notes: Refunds occur at the credit-memo level, so this query allocates refund value to credit-memo lines in proportion to line amount.

WITH billed_sales AS (
    SELECT
        i.ItemGroup,
        COALESCE(i.CollectionName, '(No Collection)') AS CollectionName,
        COALESCE(i.LifecycleStatus, '(No Lifecycle)') AS LifecycleStatus,
        ROUND(SUM(sil.Quantity), 2) AS BilledQuantity,
        ROUND(SUM(sil.LineTotal), 2) AS BilledSales
    FROM SalesInvoiceLine AS sil
    JOIN Item AS i
        ON i.ItemID = sil.ItemID
    GROUP BY
        i.ItemGroup,
        COALESCE(i.CollectionName, '(No Collection)'),
        COALESCE(i.LifecycleStatus, '(No Lifecycle)')
),
credit_totals AS (
    SELECT
        cml.CreditMemoID,
        ROUND(SUM(cml.LineTotal), 2) AS CreditMemoLineTotal
    FROM CreditMemoLine AS cml
    GROUP BY cml.CreditMemoID
),
refund_totals AS (
    SELECT
        CreditMemoID,
        ROUND(SUM(Amount), 2) AS RefundAmount
    FROM CustomerRefund
    GROUP BY CreditMemoID
),
credited_activity AS (
    SELECT
        i.ItemGroup,
        COALESCE(i.CollectionName, '(No Collection)') AS CollectionName,
        COALESCE(i.LifecycleStatus, '(No Lifecycle)') AS LifecycleStatus,
        ROUND(SUM(cml.Quantity), 2) AS CreditedQuantity,
        ROUND(SUM(cml.LineTotal), 2) AS CreditMemoValue,
        ROUND(
            SUM(
                CASE
                    WHEN COALESCE(ct.CreditMemoLineTotal, 0) = 0 THEN 0
                    ELSE COALESCE(rt.RefundAmount, 0) * (cml.LineTotal / ct.CreditMemoLineTotal)
                END
            ),
            2
        ) AS AllocatedRefundAmount
    FROM CreditMemoLine AS cml
    JOIN CreditMemo AS cm
        ON cm.CreditMemoID = cml.CreditMemoID
    JOIN Item AS i
        ON i.ItemID = cml.ItemID
    LEFT JOIN credit_totals AS ct
        ON ct.CreditMemoID = cml.CreditMemoID
    LEFT JOIN refund_totals AS rt
        ON rt.CreditMemoID = cml.CreditMemoID
    GROUP BY
        i.ItemGroup,
        COALESCE(i.CollectionName, '(No Collection)'),
        COALESCE(i.LifecycleStatus, '(No Lifecycle)')
),
attribute_keys AS (
    SELECT ItemGroup, CollectionName, LifecycleStatus FROM billed_sales
    UNION
    SELECT ItemGroup, CollectionName, LifecycleStatus FROM credited_activity
)
SELECT
    ak.ItemGroup,
    ak.CollectionName,
    ak.LifecycleStatus,
    ROUND(COALESCE(bs.BilledQuantity, 0), 2) AS BilledQuantity,
    ROUND(COALESCE(ca.CreditedQuantity, 0), 2) AS CreditedQuantity,
    ROUND(COALESCE(bs.BilledSales, 0), 2) AS BilledSales,
    ROUND(COALESCE(ca.CreditMemoValue, 0), 2) AS CreditMemoValue,
    ROUND(COALESCE(ca.AllocatedRefundAmount, 0), 2) AS AllocatedRefundAmount,
    ROUND(
        CASE
            WHEN COALESCE(bs.BilledSales, 0) = 0 THEN NULL
            ELSE 100.0 * COALESCE(ca.CreditMemoValue, 0) / COALESCE(bs.BilledSales, 0)
        END,
        2
    ) AS CreditRatePct,
    ROUND(
        CASE
            WHEN COALESCE(bs.BilledSales, 0) = 0 THEN NULL
            ELSE 100.0 * COALESCE(ca.AllocatedRefundAmount, 0) / COALESCE(bs.BilledSales, 0)
        END,
        2
    ) AS RefundRatePct
FROM attribute_keys AS ak
LEFT JOIN billed_sales AS bs
    ON bs.ItemGroup = ak.ItemGroup
   AND bs.CollectionName = ak.CollectionName
   AND bs.LifecycleStatus = ak.LifecycleStatus
LEFT JOIN credited_activity AS ca
    ON ca.ItemGroup = ak.ItemGroup
   AND ca.CollectionName = ak.CollectionName
   AND ca.LifecycleStatus = ak.LifecycleStatus
ORDER BY
    CreditMemoValue DESC,
    AllocatedRefundAmount DESC,
    ak.ItemGroup,
    ak.CollectionName;
