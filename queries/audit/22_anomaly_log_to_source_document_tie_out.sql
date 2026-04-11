-- Teaching objective: Tie exported anomaly-log entries back to their source documents in the SQLite release artifact.
-- Main tables: AnomalyLog plus the document tables referenced by the anomaly log.
-- Expected output shape: One row per logged anomaly with a tied source-document reference.
-- Recommended build mode: Standard anomaly build.
-- Interpretation notes: This query depends on the exported SQLite support table `AnomalyLog`.

SELECT
    al.anomaly_type,
    al.table_name,
    CAST(al.primary_key_value AS INTEGER) AS PrimaryKeyValue,
    al.fiscal_year,
    COALESCE(
        je.EntryNumber,
        prq.RequisitionNumber,
        po.PONumber,
        si.InvoiceNumber,
        pi.InvoiceNumber,
        dp.PaymentNumber,
        wo.WorkOrderNumber,
        pc.CompletionNumber,
        'WOO-' || printf('%06d', woo.WorkOrderOperationID),
        'WOOS-' || printf('%06d', woos.WorkOrderOperationScheduleID),
        'LTE-' || printf('%06d', lte.LaborTimeEntryID),
        'TCE-' || printf('%06d', tce.TimeClockEntryID),
        'PR-' || printf('%06d', preg.PayrollRegisterID),
        'PP-' || printf('%06d', ppay.PayrollPaymentID)
    ) AS DocumentReference,
    COALESCE(
        date(je.PostingDate),
        date(prq.RequestDate),
        date(po.OrderDate),
        date(si.InvoiceDate),
        date(pi.InvoiceDate),
        date(dp.PaymentDate),
        date(wo.ReleasedDate),
        date(pc.CompletionDate),
        date(woo.ActualStartDate),
        date(woos.ScheduleDate),
        date(lte.WorkDate),
        date(tce.WorkDate),
        date(preg.ApprovedDate),
        date(ppay.PaymentDate)
    ) AS EventDate,
    al.description,
    al.expected_detection_test
FROM AnomalyLog AS al
LEFT JOIN JournalEntry AS je
    ON al.table_name = 'JournalEntry'
   AND je.JournalEntryID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN PurchaseRequisition AS prq
    ON al.table_name = 'PurchaseRequisition'
   AND prq.RequisitionID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN PurchaseOrder AS po
    ON al.table_name = 'PurchaseOrder'
   AND po.PurchaseOrderID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN SalesInvoice AS si
    ON al.table_name = 'SalesInvoice'
   AND si.SalesInvoiceID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN PurchaseInvoice AS pi
    ON al.table_name = 'PurchaseInvoice'
   AND pi.PurchaseInvoiceID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN DisbursementPayment AS dp
    ON al.table_name = 'DisbursementPayment'
   AND dp.DisbursementID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN WorkOrder AS wo
    ON al.table_name = 'WorkOrder'
   AND wo.WorkOrderID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN ProductionCompletion AS pc
    ON al.table_name = 'ProductionCompletion'
   AND pc.ProductionCompletionID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN WorkOrderOperation AS woo
    ON al.table_name = 'WorkOrderOperation'
   AND woo.WorkOrderOperationID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN WorkOrderOperationSchedule AS woos
    ON al.table_name = 'WorkOrderOperationSchedule'
   AND woos.WorkOrderOperationScheduleID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN LaborTimeEntry AS lte
    ON al.table_name = 'LaborTimeEntry'
   AND lte.LaborTimeEntryID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN TimeClockEntry AS tce
    ON al.table_name = 'TimeClockEntry'
   AND tce.TimeClockEntryID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN PayrollRegister AS preg
    ON al.table_name = 'PayrollRegister'
   AND preg.PayrollRegisterID = CAST(al.primary_key_value AS INTEGER)
LEFT JOIN PayrollPayment AS ppay
    ON al.table_name = 'PayrollPayment'
   AND ppay.PayrollPaymentID = CAST(al.primary_key_value AS INTEGER)
ORDER BY al.anomaly_type, EventDate, DocumentReference;
