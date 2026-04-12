-- Teaching objective: Review operational activity that uses items before launch or after they are discontinued from the active catalog.
-- Main tables: Item, SalesOrder, SalesOrderLine, PurchaseOrder, PurchaseOrderLine, WorkOrder, Shipment, ShipmentLine, SalesInvoice, SalesInvoiceLine.
-- Expected output shape: One row per flagged activity line or work order.
-- Recommended build mode: Default.
-- Interpretation notes: Clean builds should normally avoid these rows. The anomaly-enabled build may plant discontinued-item activity for control testing.

WITH activity_events AS (
    SELECT
        'Sales Order' AS SourceTable,
        so.OrderNumber AS DocumentNumber,
        date(so.OrderDate) AS ActivityDate,
        sol.ItemID
    FROM SalesOrderLine AS sol
    JOIN SalesOrder AS so
        ON so.SalesOrderID = sol.SalesOrderID

    UNION ALL

    SELECT
        'Purchase Order',
        po.PONumber,
        date(po.OrderDate),
        pol.ItemID
    FROM PurchaseOrderLine AS pol
    JOIN PurchaseOrder AS po
        ON po.PurchaseOrderID = pol.PurchaseOrderID

    UNION ALL

    SELECT
        'Work Order',
        wo.WorkOrderNumber,
        date(wo.ReleasedDate),
        wo.ItemID
    FROM WorkOrder AS wo

    UNION ALL

    SELECT
        'Shipment',
        s.ShipmentNumber,
        date(s.ShipmentDate),
        sl.ItemID
    FROM ShipmentLine AS sl
    JOIN Shipment AS s
        ON s.ShipmentID = sl.ShipmentID

    UNION ALL

    SELECT
        'Sales Invoice',
        si.InvoiceNumber,
        date(si.InvoiceDate),
        sil.ItemID
    FROM SalesInvoiceLine AS sil
    JOIN SalesInvoice AS si
        ON si.SalesInvoiceID = sil.SalesInvoiceID
),
flagged_activity AS (
    SELECT
        ae.SourceTable,
        ae.DocumentNumber,
        ae.ActivityDate,
        i.ItemCode,
        i.ItemName,
        i.ItemGroup,
        i.LifecycleStatus,
        CAST(i.IsActive AS INTEGER) AS IsActive,
        date(i.LaunchDate) AS LaunchDate,
        CASE
            WHEN date(ae.ActivityDate) < date(i.LaunchDate) THEN 'Used Before Launch'
            WHEN i.LifecycleStatus = 'Discontinued' OR CAST(i.IsActive AS INTEGER) = 0 THEN 'Discontinued or Inactive Item Used'
        END AS ReviewFlag
    FROM activity_events AS ae
    JOIN Item AS i
        ON i.ItemID = ae.ItemID
    WHERE date(ae.ActivityDate) < date(i.LaunchDate)
       OR i.LifecycleStatus = 'Discontinued'
       OR CAST(i.IsActive AS INTEGER) = 0
)
SELECT
    SourceTable,
    DocumentNumber,
    ActivityDate,
    ItemCode,
    ItemName,
    ItemGroup,
    LifecycleStatus,
    IsActive,
    LaunchDate,
    ReviewFlag
FROM flagged_activity
ORDER BY
    ActivityDate,
    SourceTable,
    DocumentNumber,
    ItemCode;
