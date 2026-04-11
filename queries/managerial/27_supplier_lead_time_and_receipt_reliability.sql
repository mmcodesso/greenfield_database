-- Teaching objective: Review supplier lead time and receipt reliability from purchase order to first and final receipt.
-- Main tables: PurchaseOrder, PurchaseOrderLine, GoodsReceipt, GoodsReceiptLine, Supplier.
-- Expected output shape: One row per order month and supplier.
-- Recommended build mode: Either.
-- Interpretation notes: This is a teachable operational summary rather than a formal vendor-scorecard model.

WITH receipt_summary AS (
    SELECT
        po.PurchaseOrderID,
        MIN(date(gr.ReceiptDate)) AS FirstReceiptDate,
        MAX(date(gr.ReceiptDate)) AS LastReceiptDate,
        ROUND(SUM(COALESCE(grl.QuantityReceived, 0)), 2) AS ReceivedQuantity
    FROM PurchaseOrder AS po
    JOIN PurchaseOrderLine AS pol
        ON pol.PurchaseOrderID = po.PurchaseOrderID
    LEFT JOIN GoodsReceiptLine AS grl
        ON grl.POLineID = pol.POLineID
    LEFT JOIN GoodsReceipt AS gr
        ON gr.GoodsReceiptID = grl.GoodsReceiptID
    GROUP BY po.PurchaseOrderID
),
order_summary AS (
    SELECT
        po.PurchaseOrderID,
        date(po.OrderDate) AS OrderDate,
        substr(po.OrderDate, 1, 7) AS OrderMonth,
        po.SupplierID,
        ROUND(SUM(pol.Quantity), 2) AS OrderedQuantity
    FROM PurchaseOrder AS po
    JOIN PurchaseOrderLine AS pol
        ON pol.PurchaseOrderID = po.PurchaseOrderID
    GROUP BY po.PurchaseOrderID, date(po.OrderDate), substr(po.OrderDate, 1, 7), po.SupplierID
)
SELECT
    os.OrderMonth,
    s.SupplierName,
    s.SupplierCategory,
    COUNT(*) AS PurchaseOrderCount,
    ROUND(AVG(
        CASE
            WHEN rs.FirstReceiptDate IS NOT NULL
            THEN julianday(rs.FirstReceiptDate) - julianday(os.OrderDate)
        END
    ), 2) AS AvgDaysToFirstReceipt,
    ROUND(AVG(
        CASE
            WHEN rs.LastReceiptDate IS NOT NULL
            THEN julianday(rs.LastReceiptDate) - julianday(os.OrderDate)
        END
    ), 2) AS AvgDaysToFullReceipt,
    SUM(CASE WHEN COALESCE(rs.ReceivedQuantity, 0) >= os.OrderedQuantity THEN 1 ELSE 0 END) AS FullyReceivedPOCount,
    SUM(CASE WHEN COALESCE(rs.ReceivedQuantity, 0) < os.OrderedQuantity THEN 1 ELSE 0 END) AS PartiallyReceivedPOCount,
    SUM(CASE WHEN rs.FirstReceiptDate IS NULL THEN 1 ELSE 0 END) AS NoReceiptPOCount,
    SUM(
        CASE
            WHEN rs.FirstReceiptDate IS NOT NULL
             AND julianday(rs.FirstReceiptDate) - julianday(os.OrderDate) > 14
            THEN 1
            ELSE 0
        END
    ) AS FirstReceiptOver14DaysCount
FROM order_summary AS os
JOIN Supplier AS s
    ON s.SupplierID = os.SupplierID
LEFT JOIN receipt_summary AS rs
    ON rs.PurchaseOrderID = os.PurchaseOrderID
GROUP BY os.OrderMonth, s.SupplierName, s.SupplierCategory
ORDER BY os.OrderMonth, s.SupplierName;
