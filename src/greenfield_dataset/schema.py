from __future__ import annotations

import pandas as pd

from greenfield_dataset.settings import GenerationContext


TABLE_COLUMNS = {
    "Account": [
        "AccountID", "AccountNumber", "AccountName", "AccountType", "AccountSubType",
        "ParentAccountID", "NormalBalance", "IsActive",
    ],
    "JournalEntry": [
        "JournalEntryID", "EntryNumber", "PostingDate", "EntryType", "Description",
        "TotalAmount", "CreatedByEmployeeID", "CreatedDate", "ApprovedByEmployeeID",
        "ApprovedDate", "ReversesJournalEntryID",
    ],
    "GLEntry": [
        "GLEntryID", "PostingDate", "AccountID", "Debit", "Credit", "VoucherType",
        "VoucherNumber", "SourceDocumentType", "SourceDocumentID", "SourceLineID",
        "CostCenterID", "Description", "CreatedByEmployeeID", "CreatedDate",
        "FiscalYear", "FiscalPeriod",
    ],
    "Customer": [
        "CustomerID", "CustomerName", "ContactName", "Address", "City", "State",
        "PostalCode", "Country", "Phone", "Email", "CreditLimit", "PaymentTerms",
        "CustomerSince", "SalesRepEmployeeID", "CustomerSegment", "Industry", "Region",
        "IsActive",
    ],
    "SalesOrder": [
        "SalesOrderID", "OrderNumber", "OrderDate", "CustomerID", "RequestedDeliveryDate",
        "Status", "SalesRepEmployeeID", "CostCenterID", "OrderTotal", "Notes",
    ],
    "SalesOrderLine": [
        "SalesOrderLineID", "SalesOrderID", "LineNumber", "ItemID", "Quantity",
        "UnitPrice", "Discount", "LineTotal",
    ],
    "Shipment": [
        "ShipmentID", "ShipmentNumber", "SalesOrderID", "ShipmentDate", "WarehouseID",
        "ShippedBy", "TrackingNumber", "Status", "DeliveryDate",
    ],
    "ShipmentLine": [
        "ShipmentLineID", "ShipmentID", "SalesOrderLineID", "LineNumber", "ItemID",
        "QuantityShipped", "ExtendedStandardCost",
    ],
    "SalesInvoice": [
        "SalesInvoiceID", "InvoiceNumber", "InvoiceDate", "DueDate", "SalesOrderID",
        "CustomerID", "SubTotal", "TaxAmount", "GrandTotal", "Status", "PaymentDate",
    ],
    "SalesInvoiceLine": [
        "SalesInvoiceLineID", "SalesInvoiceID", "SalesOrderLineID", "LineNumber",
        "ItemID", "Quantity", "UnitPrice", "Discount", "LineTotal",
    ],
    "CashReceipt": [
        "CashReceiptID", "ReceiptNumber", "ReceiptDate", "CustomerID", "SalesInvoiceID",
        "Amount", "PaymentMethod", "ReferenceNumber", "DepositDate", "RecordedByEmployeeID",
    ],
    "Supplier": [
        "SupplierID", "SupplierName", "ContactName", "Address", "City", "State",
        "PostalCode", "Country", "Phone", "Email", "PaymentTerms", "IsApproved",
        "TaxID", "BankAccount", "SupplierCategory", "SupplierRiskRating", "DefaultCurrency",
    ],
    "PurchaseRequisition": [
        "RequisitionID", "RequisitionNumber", "RequestDate", "RequestedByEmployeeID",
        "CostCenterID", "ItemID", "Quantity", "EstimatedUnitCost", "Justification",
        "ApprovedByEmployeeID", "ApprovedDate", "Status",
    ],
    "PurchaseOrder": [
        "PurchaseOrderID", "PONumber", "OrderDate", "SupplierID", "RequisitionID",
        "ExpectedDeliveryDate", "Status", "CreatedByEmployeeID", "ApprovedByEmployeeID",
        "OrderTotal",
    ],
    "PurchaseOrderLine": [
        "POLineID", "PurchaseOrderID", "RequisitionID", "LineNumber", "ItemID", "Quantity",
        "UnitCost", "LineTotal",
    ],
    "GoodsReceipt": [
        "GoodsReceiptID", "ReceiptNumber", "ReceiptDate", "PurchaseOrderID", "WarehouseID",
        "ReceivedByEmployeeID", "Status",
    ],
    "GoodsReceiptLine": [
        "GoodsReceiptLineID", "GoodsReceiptID", "POLineID", "LineNumber", "ItemID",
        "QuantityReceived", "ExtendedStandardCost",
    ],
    "PurchaseInvoice": [
        "PurchaseInvoiceID", "InvoiceNumber", "InvoiceDate", "ReceivedDate", "DueDate",
        "PurchaseOrderID", "SupplierID", "SubTotal", "TaxAmount", "GrandTotal", "Status",
        "ApprovedByEmployeeID", "ApprovedDate",
    ],
    "PurchaseInvoiceLine": [
        "PILineID", "PurchaseInvoiceID", "POLineID", "GoodsReceiptLineID", "LineNumber",
        "ItemID", "Quantity", "UnitCost", "LineTotal",
    ],
    "DisbursementPayment": [
        "DisbursementID", "PaymentNumber", "PaymentDate", "SupplierID",
        "PurchaseInvoiceID", "Amount", "PaymentMethod", "CheckNumber",
        "ApprovedByEmployeeID", "ClearedDate",
    ],
    "Item": [
        "ItemID", "ItemCode", "ItemName", "ItemGroup", "ItemType", "StandardCost",
        "ListPrice", "UnitOfMeasure", "InventoryAccountID", "RevenueAccountID",
        "COGSAccountID", "PurchaseVarianceAccountID", "TaxCategory", "IsActive",
    ],
    "Warehouse": [
        "WarehouseID", "WarehouseName", "Address", "City", "State", "ManagerID",
    ],
    "Employee": [
        "EmployeeID", "EmployeeName", "CostCenterID", "JobTitle", "Email", "Address",
        "City", "State", "HireDate", "ManagerID", "IsActive", "AuthorizationLevel",
        "MaxApprovalAmount",
    ],
    "CostCenter": [
        "CostCenterID", "CostCenterName", "ParentCostCenterID", "ManagerID", "IsActive",
    ],
    "Budget": [
        "BudgetID", "FiscalYear", "CostCenterID", "AccountID", "Month", "BudgetAmount",
        "ApprovedByEmployeeID", "ApprovedDate",
    ],
}


def create_empty_tables(context: GenerationContext) -> None:
    context.tables = {
        table_name: pd.DataFrame(columns=columns)
        for table_name, columns in TABLE_COLUMNS.items()
    }
    context.counters = {table_name: 1 for table_name in TABLE_COLUMNS}
