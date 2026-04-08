# Schema Reference

**Audience:** Contributors, advanced users, and instructors who need the implemented schema in a compact technical form.  
**Purpose:** Summarize the executable schema that the generator currently creates.  
**What you will learn:** The implemented table groups, key columns, and the patterns that matter for joins and traceability.

The canonical schema lives in `src/greenfield_dataset/schema.py` as `TABLE_COLUMNS`.

> **Implemented in current generator:** 25 tables across accounting, O2C, P2P, master data, and organizational planning.

> **Planned future extension:** Additional tables for recurring manual journals and manufacturing-related processes.

## Table Groups

| Group | Tables | Count |
|---|---|---:|
| Accounting core | `Account`, `JournalEntry`, `GLEntry` | 3 |
| O2C | `Customer`, `SalesOrder`, `SalesOrderLine`, `Shipment`, `ShipmentLine`, `SalesInvoice`, `SalesInvoiceLine`, `CashReceipt` | 8 |
| P2P | `Supplier`, `PurchaseRequisition`, `PurchaseOrder`, `PurchaseOrderLine`, `GoodsReceipt`, `GoodsReceiptLine`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment` | 9 |
| Master data | `Item`, `Warehouse`, `Employee` | 3 |
| Organizational planning | `CostCenter`, `Budget` | 2 |
| Total |  | 25 |

## Design Patterns That Matter

- Header-line tables are used for sales orders, shipments, sales invoices, purchase orders, goods receipts, and purchase invoices.
- `GLEntry` is the reporting bridge between operational events and accounting analysis.
- `Item` carries account-mapping fields used by the posting engine.
- `Employee` and `CostCenter` reference each other, so generation uses a backfill step for managers.
- `JournalEntry` exists in the current schema, but the generated dataset currently contains only the opening balance header.

## Accounting Core

| Table | Purpose | High-value columns |
|---|---|---|
| `Account` | Chart of accounts and hierarchy | `AccountNumber`, `AccountType`, `AccountSubType`, `ParentAccountID`, `NormalBalance` |
| `JournalEntry` | Manual journal header table | `EntryNumber`, `PostingDate`, `EntryType`, `CreatedByEmployeeID`, `ApprovedByEmployeeID`, `ReversesJournalEntryID` |
| `GLEntry` | Posted ledger detail and source traceability | `PostingDate`, `AccountID`, `Debit`, `Credit`, `VoucherType`, `VoucherNumber`, `SourceDocumentType`, `SourceDocumentID`, `SourceLineID`, `FiscalYear`, `FiscalPeriod` |

## Order-to-Cash

| Table | Purpose | High-value columns |
|---|---|---|
| `Customer` | Customer master data | `CreditLimit`, `PaymentTerms`, `SalesRepEmployeeID`, `CustomerSegment`, `Industry`, `Region` |
| `SalesOrder` | Sales order header | `OrderNumber`, `OrderDate`, `CustomerID`, `RequestedDeliveryDate`, `SalesRepEmployeeID`, `CostCenterID`, `OrderTotal`, `Status` |
| `SalesOrderLine` | Sales order detail | `SalesOrderID`, `LineNumber`, `ItemID`, `Quantity`, `UnitPrice`, `Discount`, `LineTotal` |
| `Shipment` | Shipment header | `ShipmentNumber`, `SalesOrderID`, `ShipmentDate`, `WarehouseID`, `Status`, `DeliveryDate` |
| `ShipmentLine` | Shipment detail used for fulfillment and COGS | `ShipmentID`, `SalesOrderLineID`, `ItemID`, `QuantityShipped`, `ExtendedStandardCost` |
| `SalesInvoice` | Sales invoice header | `InvoiceNumber`, `InvoiceDate`, `DueDate`, `SalesOrderID`, `CustomerID`, `SubTotal`, `TaxAmount`, `GrandTotal`, `Status` |
| `SalesInvoiceLine` | Sales invoice detail | `SalesInvoiceID`, `SalesOrderLineID`, `ItemID`, `Quantity`, `UnitPrice`, `Discount`, `LineTotal` |
| `CashReceipt` | Customer payment record | `ReceiptNumber`, `ReceiptDate`, `CustomerID`, `SalesInvoiceID`, `Amount`, `PaymentMethod`, `ReferenceNumber`, `RecordedByEmployeeID` |

## Procure-to-Pay

| Table | Purpose | High-value columns |
|---|---|---|
| `Supplier` | Supplier master data | `PaymentTerms`, `TaxID`, `BankAccount`, `SupplierCategory`, `SupplierRiskRating`, `DefaultCurrency` |
| `PurchaseRequisition` | Internal request document | `RequisitionNumber`, `RequestDate`, `RequestedByEmployeeID`, `CostCenterID`, `ItemID`, `Quantity`, `EstimatedUnitCost`, `ApprovedByEmployeeID`, `Status` |
| `PurchaseOrder` | Purchase order header | `PONumber`, `OrderDate`, `SupplierID`, `RequisitionID`, `ExpectedDeliveryDate`, `CreatedByEmployeeID`, `ApprovedByEmployeeID`, `OrderTotal`, `Status` |
| `PurchaseOrderLine` | Purchase order detail | `PurchaseOrderID`, `LineNumber`, `ItemID`, `Quantity`, `UnitCost`, `LineTotal` |
| `GoodsReceipt` | Receipt header | `ReceiptNumber`, `ReceiptDate`, `PurchaseOrderID`, `WarehouseID`, `ReceivedByEmployeeID`, `Status` |
| `GoodsReceiptLine` | Receipt detail used for quantity and cost tracking | `GoodsReceiptID`, `POLineID`, `ItemID`, `QuantityReceived`, `ExtendedStandardCost` |
| `PurchaseInvoice` | Supplier invoice header | `InvoiceNumber`, `InvoiceDate`, `ReceivedDate`, `DueDate`, `PurchaseOrderID`, `SupplierID`, `SubTotal`, `TaxAmount`, `GrandTotal`, `ApprovedByEmployeeID`, `Status` |
| `PurchaseInvoiceLine` | Supplier invoice detail | `PurchaseInvoiceID`, `POLineID`, `ItemID`, `Quantity`, `UnitCost`, `LineTotal` |
| `DisbursementPayment` | Supplier payment record | `PaymentNumber`, `PaymentDate`, `SupplierID`, `PurchaseInvoiceID`, `Amount`, `PaymentMethod`, `CheckNumber`, `ApprovedByEmployeeID`, `ClearedDate` |

## Master Data

| Table | Purpose | High-value columns |
|---|---|---|
| `Item` | Product master and account mapping | `ItemCode`, `ItemGroup`, `ItemType`, `StandardCost`, `ListPrice`, `InventoryAccountID`, `RevenueAccountID`, `COGSAccountID`, `PurchaseVarianceAccountID`, `TaxCategory` |
| `Warehouse` | Inventory storage locations | `WarehouseName`, `ManagerID`, address fields |
| `Employee` | Employee and approval metadata | `CostCenterID`, `JobTitle`, `ManagerID`, `AuthorizationLevel`, `MaxApprovalAmount`, `IsActive` |

## Organizational Planning

| Table | Purpose | High-value columns |
|---|---|---|
| `CostCenter` | Organizational reporting structure | `CostCenterName`, `ParentCostCenterID`, `ManagerID`, `IsActive` |
| `Budget` | Monthly budget by fiscal year, cost center, and account | `FiscalYear`, `Month`, `CostCenterID`, `AccountID`, `BudgetAmount`, `ApprovedByEmployeeID` |

## Traceability Fields

The most important lineage fields in the implementation are on `GLEntry`:

- `VoucherType`
- `VoucherNumber`
- `SourceDocumentType`
- `SourceDocumentID`
- `SourceLineID`
- `FiscalYear`
- `FiscalPeriod`

These fields make it possible to trace from posted accounting detail back to the source document that created the entry.

## Current Implementation Notes

- `JournalEntry` currently holds the opening balance entry only.
- Excel exports include additional worksheets such as `AnomalyLog` and `ValidationSummary`, but those are export artifacts, not schema tables.
- For the exact column order and names, use `TABLE_COLUMNS` in `src/greenfield_dataset/schema.py`.
