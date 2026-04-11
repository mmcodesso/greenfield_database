-- Teaching objective: Review how returned quantity, credit activity, and refunds affect customer and item-group performance.
-- Main tables: CreditMemo, CreditMemoLine, SalesReturnLine, CustomerRefund, Customer, Item.
-- Expected output shape: One row per credit-memo month, customer region, and item grouping.
-- Recommended build mode: Either; standard anomaly builds may add extra exception-style patterns.
-- Interpretation notes: Returns reduce sales value through credit memos, while refunds show which credits left the business in cash.

WITH refunds_by_credit_memo AS (
    SELECT
        CreditMemoID,
        ROUND(SUM(Amount), 2) AS RefundedAmount
    FROM CustomerRefund
    GROUP BY CreditMemoID
)
SELECT
    substr(cm.CreditMemoDate, 1, 7) AS CreditMonth,
    c.Region,
    i.ItemGroup,
    i.ItemCode,
    i.ItemName,
    COUNT(DISTINCT cm.CreditMemoID) AS CreditMemoCount,
    ROUND(SUM(cml.Quantity), 2) AS ReturnedQuantity,
    ROUND(SUM(cml.LineTotal), 2) AS CreditMemoSubtotal,
    ROUND(SUM(srl.ExtendedStandardCost), 2) AS RestoredStandardCost,
    ROUND(SUM(COALESCE(rbc.RefundedAmount, 0)), 2) AS RefundedAmount
FROM CreditMemo AS cm
JOIN CreditMemoLine AS cml
    ON cml.CreditMemoID = cm.CreditMemoID
JOIN SalesReturnLine AS srl
    ON srl.SalesReturnLineID = cml.SalesReturnLineID
JOIN Customer AS c
    ON c.CustomerID = cm.CustomerID
JOIN Item AS i
    ON i.ItemID = cml.ItemID
LEFT JOIN refunds_by_credit_memo AS rbc
    ON rbc.CreditMemoID = cm.CreditMemoID
GROUP BY
    substr(cm.CreditMemoDate, 1, 7),
    c.Region,
    i.ItemGroup,
    i.ItemCode,
    i.ItemName
ORDER BY CreditMonth, c.Region, i.ItemGroup, i.ItemCode;
