-- Teaching objective: Trace CAPEX additions, financing, and disposals across the asset lifecycle.
-- Main tables: FixedAssetEvent, FixedAsset, PurchaseInvoice, DisbursementPayment, DebtAgreement, JournalEntry.
-- Output shape: One row per fixed-asset event excluding opening balances.
-- Interpretation notes: Use this query to separate cash purchases, note-financed additions, and disposal activity while keeping the source documents visible.

SELECT
    date(fae.EventDate) AS EventDate,
    CAST(substr(fae.EventDate, 1, 4) AS INTEGER) AS FiscalYear,
    CAST(substr(fae.EventDate, 6, 2) AS INTEGER) AS FiscalPeriod,
    fa.BehaviorGroup,
    fa.AssetCategory,
    fa.AssetCode,
    fa.AssetDescription,
    fae.EventType,
    COALESCE(fae.FinancingType, 'None') AS FinancingType,
    ROUND(COALESCE(fae.Amount, 0), 2) AS EventAmount,
    ROUND(
        CASE
            WHEN fae.EventType IN ('Acquisition', 'Improvement')
             AND COALESCE(fae.FinancingType, 'Cash') = 'Cash'
                THEN COALESCE(dp.Amount, 0)
            ELSE 0
        END,
        2
    ) AS CashPaidAmount,
    ROUND(
        CASE
            WHEN COALESCE(fae.FinancingType, '') = 'Note'
                THEN COALESCE(da.PrincipalAmount, 0)
            ELSE 0
        END,
        2
    ) AS NotesPrincipalAmount,
    ROUND(COALESCE(fae.ProceedsAmount, 0), 2) AS DisposalProceedsAmount,
    pr.RequisitionNumber,
    po.PONumber,
    pi.InvoiceNumber,
    dp.PaymentNumber,
    da.AgreementNumber,
    ROUND(COALESCE(da.AnnualInterestRate, 0), 4) AS AnnualInterestRate,
    COALESCE(da.TermMonths, 0) AS TermMonths,
    ROUND(COALESCE(da.ScheduledPaymentAmount, 0), 2) AS ScheduledPaymentAmount,
    je.EntryNumber AS LinkedJournalEntryNumber
FROM FixedAssetEvent AS fae
JOIN FixedAsset AS fa
    ON fa.FixedAssetID = fae.FixedAssetID
LEFT JOIN PurchaseRequisition AS pr
    ON pr.RequisitionID = fae.PurchaseRequisitionID
LEFT JOIN PurchaseOrder AS po
    ON po.PurchaseOrderID = fae.PurchaseOrderID
LEFT JOIN PurchaseInvoice AS pi
    ON pi.PurchaseInvoiceID = fae.PurchaseInvoiceID
LEFT JOIN DisbursementPayment AS dp
    ON dp.DisbursementID = fae.DisbursementID
LEFT JOIN DebtAgreement AS da
    ON da.DebtAgreementID = fae.DebtAgreementID
LEFT JOIN JournalEntry AS je
    ON je.JournalEntryID = fae.JournalEntryID
WHERE fae.EventType <> 'Opening'
ORDER BY date(fae.EventDate), fae.FixedAssetEventID;
