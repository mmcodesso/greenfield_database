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
        "SalesInvoiceLineID", "SalesInvoiceID", "SalesOrderLineID", "ShipmentLineID",
        "LineNumber", "ItemID", "Quantity", "UnitPrice", "Discount", "LineTotal",
    ],
    "CashReceipt": [
        "CashReceiptID", "ReceiptNumber", "ReceiptDate", "CustomerID", "SalesInvoiceID",
        "Amount", "PaymentMethod", "ReferenceNumber", "DepositDate", "RecordedByEmployeeID",
    ],
    "CashReceiptApplication": [
        "CashReceiptApplicationID", "CashReceiptID", "SalesInvoiceID", "ApplicationDate",
        "AppliedAmount", "AppliedByEmployeeID",
    ],
    "SalesReturn": [
        "SalesReturnID", "ReturnNumber", "ReturnDate", "CustomerID", "SalesOrderID",
        "WarehouseID", "ReceivedByEmployeeID", "ReasonCode", "Status",
    ],
    "SalesReturnLine": [
        "SalesReturnLineID", "SalesReturnID", "ShipmentLineID", "LineNumber", "ItemID",
        "QuantityReturned", "ExtendedStandardCost",
    ],
    "CreditMemo": [
        "CreditMemoID", "CreditMemoNumber", "CreditMemoDate", "SalesReturnID", "SalesOrderID",
        "CustomerID", "OriginalSalesInvoiceID", "SubTotal", "TaxAmount", "GrandTotal", "Status",
        "ApprovedByEmployeeID", "ApprovedDate",
    ],
    "CreditMemoLine": [
        "CreditMemoLineID", "CreditMemoID", "SalesReturnLineID", "LineNumber", "ItemID",
        "Quantity", "UnitPrice", "LineTotal",
    ],
    "CustomerRefund": [
        "CustomerRefundID", "RefundNumber", "RefundDate", "CustomerID", "CreditMemoID",
        "Amount", "PaymentMethod", "ReferenceNumber", "ApprovedByEmployeeID", "ClearedDate",
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
        "PILineID", "PurchaseInvoiceID", "POLineID", "GoodsReceiptLineID", "AccrualJournalEntryID",
        "LineNumber", "ItemID", "Quantity", "UnitCost", "LineTotal",
    ],
    "DisbursementPayment": [
        "DisbursementID", "PaymentNumber", "PaymentDate", "SupplierID",
        "PurchaseInvoiceID", "Amount", "PaymentMethod", "CheckNumber",
        "ApprovedByEmployeeID", "ClearedDate",
    ],
    "Item": [
        "ItemID", "ItemCode", "ItemName", "ItemGroup", "ItemType", "StandardCost",
        "ListPrice", "UnitOfMeasure", "SupplyMode", "ProductionLeadTimeDays",
        "StandardLaborHoursPerUnit", "StandardDirectLaborCost", "StandardVariableOverheadCost",
        "StandardFixedOverheadCost", "StandardConversionCost", "RoutingID", "InventoryAccountID",
        "RevenueAccountID", "COGSAccountID", "PurchaseVarianceAccountID", "TaxCategory", "IsActive",
    ],
    "BillOfMaterial": [
        "BOMID", "ParentItemID", "VersionNumber", "EffectiveStartDate", "EffectiveEndDate",
        "Status", "StandardBatchQuantity",
    ],
    "BillOfMaterialLine": [
        "BOMLineID", "BOMID", "ComponentItemID", "LineNumber", "QuantityPerUnit", "ScrapFactorPct",
    ],
    "WorkCenter": [
        "WorkCenterID", "WorkCenterCode", "WorkCenterName", "Department", "WarehouseID",
        "ManagerEmployeeID", "NominalDailyCapacityHours", "IsActive",
    ],
    "WorkCenterCalendar": [
        "WorkCenterCalendarID", "WorkCenterID", "CalendarDate", "IsWorkingDay", "AvailableHours",
        "ExceptionReason",
    ],
    "Routing": [
        "RoutingID", "ParentItemID", "VersionNumber", "EffectiveStartDate", "EffectiveEndDate",
        "Status",
    ],
    "RoutingOperation": [
        "RoutingOperationID", "RoutingID", "OperationSequence", "OperationCode", "OperationName",
        "WorkCenterID", "StandardSetupHours", "StandardRunHoursPerUnit", "StandardQueueDays",
    ],
    "WorkOrder": [
        "WorkOrderID", "WorkOrderNumber", "ItemID", "BOMID", "RoutingID", "WarehouseID",
        "PlannedQuantity", "ReleasedDate", "DueDate", "CompletedDate", "ClosedDate", "Status",
        "CostCenterID", "ReleasedByEmployeeID", "ClosedByEmployeeID",
    ],
    "WorkOrderOperation": [
        "WorkOrderOperationID", "WorkOrderID", "RoutingOperationID", "OperationSequence", "WorkCenterID",
        "PlannedQuantity", "PlannedLoadHours", "PlannedStartDate", "PlannedEndDate", "ActualStartDate", "ActualEndDate", "Status",
    ],
    "WorkOrderOperationSchedule": [
        "WorkOrderOperationScheduleID", "WorkOrderOperationID", "WorkCenterID", "ScheduleDate", "ScheduledHours",
    ],
    "MaterialIssue": [
        "MaterialIssueID", "IssueNumber", "WorkOrderID", "IssueDate", "WarehouseID",
        "IssuedByEmployeeID", "Status",
    ],
    "MaterialIssueLine": [
        "MaterialIssueLineID", "MaterialIssueID", "BOMLineID", "LineNumber", "ItemID",
        "QuantityIssued", "ExtendedStandardCost",
    ],
    "ProductionCompletion": [
        "ProductionCompletionID", "CompletionNumber", "WorkOrderID", "CompletionDate",
        "WarehouseID", "ReceivedByEmployeeID", "Status",
    ],
    "ProductionCompletionLine": [
        "ProductionCompletionLineID", "ProductionCompletionID", "LineNumber", "ItemID",
        "QuantityCompleted", "ExtendedStandardMaterialCost", "ExtendedStandardDirectLaborCost",
        "ExtendedStandardVariableOverheadCost", "ExtendedStandardFixedOverheadCost",
        "ExtendedStandardConversionCost", "ExtendedStandardTotalCost",
    ],
    "WorkOrderClose": [
        "WorkOrderCloseID", "WorkOrderID", "CloseDate", "MaterialVarianceAmount",
        "DirectLaborVarianceAmount", "OverheadVarianceAmount", "ConversionVarianceAmount",
        "TotalVarianceAmount", "Status", "ClosedByEmployeeID",
    ],
    "PayrollPeriod": [
        "PayrollPeriodID", "PeriodNumber", "PeriodStartDate", "PeriodEndDate", "PayDate",
        "FiscalYear", "FiscalPeriod", "Status",
    ],
    "LaborTimeEntry": [
        "LaborTimeEntryID", "PayrollPeriodID", "EmployeeID", "WorkOrderID", "WorkOrderOperationID",
        "TimeClockEntryID", "WorkDate", "LaborType", "RegularHours", "OvertimeHours", "HourlyRateUsed",
        "ExtendedLaborCost", "ApprovedByEmployeeID", "ApprovedDate",
    ],
    "ShiftDefinition": [
        "ShiftDefinitionID", "ShiftCode", "ShiftName", "Department", "WorkCenterID", "StartTime",
        "EndTime", "StandardBreakMinutes", "ShiftType", "IsOvernight", "IsActive",
    ],
    "EmployeeShiftAssignment": [
        "EmployeeShiftAssignmentID", "EmployeeID", "ShiftDefinitionID", "EffectiveStartDate",
        "EffectiveEndDate", "WorkCenterID", "IsPrimary",
    ],
    "TimeClockEntry": [
        "TimeClockEntryID", "EmployeeID", "PayrollPeriodID", "WorkDate", "ShiftDefinitionID",
        "WorkCenterID", "WorkOrderID", "WorkOrderOperationID", "ClockInTime", "ClockOutTime",
        "BreakMinutes", "RegularHours", "OvertimeHours", "ClockStatus", "ApprovedByEmployeeID",
        "ApprovedDate",
    ],
    "AttendanceException": [
        "AttendanceExceptionID", "EmployeeID", "PayrollPeriodID", "WorkDate", "ShiftDefinitionID",
        "TimeClockEntryID", "ExceptionType", "Severity", "MinutesVariance", "Status",
        "ReviewedByEmployeeID", "ReviewedDate",
    ],
    "PayrollRegister": [
        "PayrollRegisterID", "PayrollPeriodID", "EmployeeID", "CostCenterID", "GrossPay",
        "EmployeeWithholdings", "EmployerPayrollTax", "EmployerBenefits", "NetPay", "Status",
        "ApprovedByEmployeeID", "ApprovedDate",
    ],
    "PayrollRegisterLine": [
        "PayrollRegisterLineID", "PayrollRegisterID", "LineNumber", "LineType", "Hours",
        "Rate", "Amount", "WorkOrderID", "LaborTimeEntryID",
    ],
    "PayrollPayment": [
        "PayrollPaymentID", "PayrollRegisterID", "PaymentDate", "PaymentMethod",
        "ReferenceNumber", "ClearedDate", "RecordedByEmployeeID",
    ],
    "PayrollLiabilityRemittance": [
        "PayrollLiabilityRemittanceID", "PayrollPeriodID", "LiabilityType", "RemittanceDate",
        "Amount", "AgencyOrVendor", "ReferenceNumber", "ClearedDate", "ApprovedByEmployeeID",
    ],
    "Warehouse": [
        "WarehouseID", "WarehouseName", "Address", "City", "State", "ManagerID",
    ],
    "Employee": [
        "EmployeeID", "EmployeeName", "CostCenterID", "JobTitle", "Email", "Address",
        "City", "State", "HireDate", "ManagerID", "IsActive", "AuthorizationLevel", "PayClass",
        "BaseHourlyRate", "BaseAnnualSalary", "StandardHoursPerWeek", "OvertimeEligible",
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
