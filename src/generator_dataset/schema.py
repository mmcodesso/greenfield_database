from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from generator_dataset.settings import GenerationContext


@dataclass(frozen=True)
class SQLiteIndexDefinition:
    name: str
    columns: tuple[str, ...]
    unique: bool = False


def _sqlite_index(name: str, *columns: str, unique: bool = False) -> SQLiteIndexDefinition:
    return SQLiteIndexDefinition(name=name, columns=tuple(columns), unique=unique)


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
    "PriceList": [
        "PriceListID", "PriceListName", "ScopeType", "CustomerID", "CustomerSegment",
        "EffectiveStartDate", "EffectiveEndDate", "CurrencyCode", "Status",
        "ApprovedByEmployeeID", "ApprovedDate",
    ],
    "PriceListLine": [
        "PriceListLineID", "PriceListID", "ItemID", "MinimumQuantity", "UnitPrice",
        "MinimumUnitPrice", "Status",
    ],
    "PromotionProgram": [
        "PromotionID", "PromotionCode", "PromotionName", "ScopeType", "CustomerSegment",
        "ItemGroup", "CollectionName", "DiscountPct", "EffectiveStartDate",
        "EffectiveEndDate", "Status", "ApprovedByEmployeeID", "ApprovedDate",
    ],
    "PriceOverrideApproval": [
        "PriceOverrideApprovalID", "SalesOrderLineID", "CustomerID", "ItemID",
        "RequestedByEmployeeID", "ApprovedByEmployeeID", "RequestDate", "ApprovedDate",
        "ReferenceUnitPrice", "RequestedUnitPrice", "ApprovedUnitPrice", "ReasonCode",
        "Status",
    ],
    "SalesOrder": [
        "SalesOrderID", "OrderNumber", "OrderDate", "CustomerID", "RequestedDeliveryDate",
        "Status", "SalesRepEmployeeID", "CostCenterID", "OrderTotal", "FreightTerms", "Notes",
    ],
    "SalesOrderLine": [
        "SalesOrderLineID", "SalesOrderID", "LineNumber", "ItemID", "Quantity",
        "BaseListPrice", "UnitPrice", "Discount", "LineTotal", "PriceListLineID",
        "PromotionID", "PriceOverrideApprovalID", "PricingMethod",
    ],
    "Shipment": [
        "ShipmentID", "ShipmentNumber", "SalesOrderID", "ShipmentDate", "WarehouseID",
        "ShippedBy", "TrackingNumber", "Status", "DeliveryDate", "FreightCost",
        "BillableFreightAmount",
    ],
    "ShipmentLine": [
        "ShipmentLineID", "ShipmentID", "SalesOrderLineID", "LineNumber", "ItemID",
        "QuantityShipped", "ExtendedStandardCost",
    ],
    "SalesInvoice": [
        "SalesInvoiceID", "InvoiceNumber", "InvoiceDate", "DueDate", "SalesOrderID",
        "CustomerID", "SubTotal", "FreightAmount", "TaxAmount", "GrandTotal", "Status",
        "PaymentDate",
    ],
    "SalesInvoiceLine": [
        "SalesInvoiceLineID", "SalesInvoiceID", "SalesOrderLineID", "ShipmentLineID",
        "LineNumber", "ItemID", "Quantity", "BaseListPrice", "UnitPrice", "Discount",
        "LineTotal", "PriceListLineID", "PromotionID", "PriceOverrideApprovalID",
        "PricingMethod",
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
        "CustomerID", "OriginalSalesInvoiceID", "SubTotal", "FreightCreditAmount",
        "TaxAmount", "GrandTotal", "Status", "ApprovedByEmployeeID", "ApprovedDate",
    ],
    "CreditMemoLine": [
        "CreditMemoLineID", "CreditMemoID", "SalesReturnLineID", "LineNumber", "ItemID",
        "Quantity", "BaseListPrice", "UnitPrice", "Discount", "LineTotal",
        "PriceListLineID", "PromotionID", "PriceOverrideApprovalID", "PricingMethod",
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
        "ApprovedByEmployeeID", "ApprovedDate", "Status", "SupplyPlanRecommendationID",
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
        "RevenueAccountID", "COGSAccountID", "PurchaseVarianceAccountID", "TaxCategory",
        "CollectionName", "StyleFamily", "PrimaryMaterial", "Finish", "Color", "SizeDescriptor",
        "LifecycleStatus", "LaunchDate", "IsActive",
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
        "CostCenterID", "ReleasedByEmployeeID", "ClosedByEmployeeID", "SupplyPlanRecommendationID",
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
    "EmployeeShiftRoster": [
        "EmployeeShiftRosterID", "EmployeeID", "RosterDate", "ShiftDefinitionID", "WorkCenterID",
        "ScheduledStartTime", "ScheduledEndTime", "ScheduledHours", "RosterStatus",
        "CreatedByEmployeeID", "CreatedDate",
    ],
    "EmployeeAbsence": [
        "EmployeeAbsenceID", "EmployeeID", "PayrollPeriodID", "AbsenceDate", "EmployeeShiftRosterID",
        "AbsenceType", "HoursAbsent", "IsPaid", "ApprovedByEmployeeID", "ApprovedDate", "Status",
    ],
    "OvertimeApproval": [
        "OvertimeApprovalID", "EmployeeID", "PayrollPeriodID", "WorkDate", "EmployeeShiftRosterID",
        "WorkCenterID", "WorkOrderID", "WorkOrderOperationID", "RequestedHours", "ApprovedHours",
        "ReasonCode", "ApprovedByEmployeeID", "ApprovedDate", "Status",
    ],
    "TimeClockEntry": [
        "TimeClockEntryID", "EmployeeID", "PayrollPeriodID", "WorkDate", "ShiftDefinitionID",
        "EmployeeShiftRosterID", "OvertimeApprovalID", "WorkCenterID", "WorkOrderID",
        "WorkOrderOperationID", "ClockInTime", "ClockOutTime", "BreakMinutes", "RegularHours",
        "OvertimeHours", "ClockStatus", "ApprovedByEmployeeID", "ApprovedDate",
    ],
    "TimeClockPunch": [
        "TimeClockPunchID", "EmployeeID", "PayrollPeriodID", "WorkDate", "EmployeeShiftRosterID",
        "TimeClockEntryID", "WorkCenterID", "PunchTimestamp", "PunchType", "PunchSource",
        "SequenceNumber",
    ],
    "AttendanceException": [
        "AttendanceExceptionID", "EmployeeID", "PayrollPeriodID", "WorkDate", "ShiftDefinitionID",
        "EmployeeShiftRosterID", "TimeClockEntryID", "ExceptionType", "Severity",
        "MinutesVariance", "Status", "ReviewedByEmployeeID", "ReviewedDate",
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
        "City", "State", "HireDate", "ManagerID", "EmployeeNumber", "EmploymentStatus",
        "TerminationDate", "TerminationReason", "JobFamily", "JobLevel", "WorkLocation",
        "IsActive", "AuthorizationLevel", "PayClass", "BaseHourlyRate", "BaseAnnualSalary",
        "StandardHoursPerWeek", "OvertimeEligible", "MaxApprovalAmount",
    ],
    "CostCenter": [
        "CostCenterID", "CostCenterName", "ParentCostCenterID", "ManagerID", "IsActive",
    ],
    "Budget": [
        "BudgetID", "FiscalYear", "CostCenterID", "AccountID", "Month", "BudgetAmount",
        "ApprovedByEmployeeID", "ApprovedDate",
    ],
    "BudgetLine": [
        "BudgetLineID", "FiscalYear", "Month", "AccountID", "CostCenterID", "ItemID",
        "WarehouseID", "Quantity", "UnitAmount", "BudgetAmount", "BudgetCategory",
        "DriverType", "ApprovedByEmployeeID", "ApprovedDate",
    ],
    "DemandForecast": [
        "DemandForecastID", "ForecastWeekStartDate", "ForecastWeekEndDate", "ItemID", "WarehouseID",
        "BaselineForecastQuantity", "ForecastQuantity", "ForecastMethod", "ForecastVersion",
        "PlannerEmployeeID", "ApprovedByEmployeeID", "ApprovedDate", "IsCurrent",
    ],
    "InventoryPolicy": [
        "InventoryPolicyID", "ItemID", "WarehouseID", "PlanningGroup", "PolicyType",
        "SafetyStockQuantity", "ReorderPointQuantity", "ReorderQuantity", "TargetDaysSupply",
        "PlanningLeadTimeDays", "PlannerEmployeeID", "BuyerEmployeeID", "EffectiveStartDate",
        "EffectiveEndDate", "IsActive",
    ],
    "SupplyPlanRecommendation": [
        "SupplyPlanRecommendationID", "RecommendationDate", "BucketWeekStartDate", "BucketWeekEndDate",
        "ItemID", "WarehouseID", "RecommendationType", "PriorityCode", "SupplyMode",
        "GrossRequirementQuantity", "ProjectedAvailableQuantity", "NetRequirementQuantity",
        "RecommendedOrderQuantity", "NeedByDate", "ReleaseByDate", "RecommendationStatus",
        "DriverType", "PlannerEmployeeID", "ConvertedDocumentType", "ConvertedDocumentID",
    ],
    "MaterialRequirementPlan": [
        "MaterialRequirementPlanID", "BucketWeekStartDate", "BucketWeekEndDate", "ParentItemID",
        "ComponentItemID", "WarehouseID", "SupplyPlanRecommendationID", "GrossRequirementQuantity",
        "ScheduledSupplyQuantity", "ProjectedAvailableQuantity", "NetRequirementQuantity",
        "RecommendedOrderQuantity",
    ],
    "RoughCutCapacityPlan": [
        "RoughCutCapacityPlanID", "BucketWeekStartDate", "BucketWeekEndDate", "WorkCenterID", "ItemID",
        "SupplyPlanRecommendationID", "PlannedLoadHours", "AvailableHours", "UtilizationPct",
        "CapacityStatus",
    ],
}

TABLE_PRIMARY_KEYS = {
    table_name: columns[0]
    for table_name, columns in TABLE_COLUMNS.items()
}

SQLITE_INDEXES = {
    "Account": (
        _sqlite_index("ux_account_accountnumber", "AccountNumber", unique=True),
    ),
    "JournalEntry": (
        _sqlite_index("ux_journalentry_entrynumber", "EntryNumber", unique=True),
    ),
    "GLEntry": (
        _sqlite_index("ix_glentry_accountid_fiscalyear_fiscalperiod", "AccountID", "FiscalYear", "FiscalPeriod"),
        _sqlite_index("ix_glentry_sourcedocument_trace", "SourceDocumentType", "SourceDocumentID", "SourceLineID"),
    ),
    "SalesOrder": (
        _sqlite_index("ux_salesorder_ordernumber", "OrderNumber", unique=True),
    ),
    "SalesOrderLine": (
        _sqlite_index("ix_salesorderline_salesorderid", "SalesOrderID"),
    ),
    "Shipment": (
        _sqlite_index("ux_shipment_shipmentnumber", "ShipmentNumber", unique=True),
    ),
    "ShipmentLine": (
        _sqlite_index("ix_shipmentline_shipmentid_salesorderlineid", "ShipmentID", "SalesOrderLineID"),
    ),
    "SalesInvoice": (
        _sqlite_index("ux_salesinvoice_invoicenumber", "InvoiceNumber", unique=True),
    ),
    "SalesInvoiceLine": (
        _sqlite_index(
            "ix_salesinvoiceline_salesinvoiceid_salesorderlineid_itemid",
            "SalesInvoiceID",
            "SalesOrderLineID",
            "ItemID",
        ),
    ),
    "CashReceipt": (
        _sqlite_index("ux_cashreceipt_receiptnumber", "ReceiptNumber", unique=True),
    ),
    "CashReceiptApplication": (
        _sqlite_index("ix_cashreceiptapplication_salesinvoiceid", "SalesInvoiceID"),
    ),
    "SalesReturn": (
        _sqlite_index("ux_salesreturn_returnnumber", "ReturnNumber", unique=True),
    ),
    "SalesReturnLine": (
        _sqlite_index("ix_salesreturnline_salesreturnid", "SalesReturnID"),
    ),
    "CreditMemo": (
        _sqlite_index("ix_creditmemo_salesreturnid", "SalesReturnID"),
        _sqlite_index("ux_creditmemo_creditmemonumber", "CreditMemoNumber", unique=True),
    ),
    "CustomerRefund": (
        _sqlite_index("ux_customerrefund_refundnumber", "RefundNumber", unique=True),
    ),
    "PurchaseRequisition": (
        _sqlite_index("ux_purchaserequisition_requisitionnumber", "RequisitionNumber", unique=True),
    ),
    "PurchaseOrder": (
        _sqlite_index("ux_purchaseorder_ponumber", "PONumber", unique=True),
    ),
    "PurchaseOrderLine": (
        _sqlite_index("ix_purchaseorderline_purchaseorderid_requisitionid", "PurchaseOrderID", "RequisitionID"),
    ),
    "GoodsReceipt": (
        _sqlite_index("ux_goodsreceipt_receiptnumber", "ReceiptNumber", unique=True),
    ),
    "GoodsReceiptLine": (
        _sqlite_index("ix_goodsreceiptline_goodsreceiptid_polineid", "GoodsReceiptID", "POLineID"),
    ),
    "PurchaseInvoiceLine": (
        _sqlite_index(
            "ix_purchaseinvoiceline_piid_polid_grid_accrualjeid",
            "PurchaseInvoiceID",
            "POLineID",
            "GoodsReceiptLineID",
            "AccrualJournalEntryID",
        ),
    ),
    "DisbursementPayment": (
        _sqlite_index("ix_disbursementpayment_purchaseinvoiceid_supplierid", "PurchaseInvoiceID", "SupplierID"),
        _sqlite_index("ux_disbursementpayment_paymentnumber", "PaymentNumber", unique=True),
    ),
    "Item": (
        _sqlite_index("ux_item_itemcode", "ItemCode", unique=True),
    ),
    "WorkCenter": (
        _sqlite_index("ux_workcenter_workcentercode", "WorkCenterCode", unique=True),
    ),
    "WorkOrder": (
        _sqlite_index("ux_workorder_workordernumber", "WorkOrderNumber", unique=True),
    ),
    "LaborTimeEntry": (
        _sqlite_index("ix_labortimeentry_employeeid_payrollperiodid", "EmployeeID", "PayrollPeriodID"),
    ),
    "ShiftDefinition": (
        _sqlite_index("ux_shiftdefinition_shiftcode", "ShiftCode", unique=True),
    ),
    "TimeClockEntry": (
        _sqlite_index("ix_timeclockentry_employeeid_payrollperiodid", "EmployeeID", "PayrollPeriodID"),
    ),
    "TimeClockPunch": (
        _sqlite_index("ix_timeclockpunch_employeeid_payrollperiodid", "EmployeeID", "PayrollPeriodID"),
    ),
    "PayrollPeriod": (
        _sqlite_index("ux_payrollperiod_periodnumber", "PeriodNumber", unique=True),
    ),
    "PayrollRegister": (
        _sqlite_index("ix_payrollregister_employeeid_payrollperiodid", "EmployeeID", "PayrollPeriodID"),
    ),
    "PayrollRegisterLine": (
        _sqlite_index("ix_payrollregisterline_payrollregisterid_labortimeentryid", "PayrollRegisterID", "LaborTimeEntryID"),
    ),
    "Employee": (
        _sqlite_index("ux_employee_employeenumber", "EmployeeNumber", unique=True),
    ),
}


def create_empty_tables(context: GenerationContext) -> None:
    context.tables = {
        table_name: pd.DataFrame(columns=columns)
        for table_name, columns in TABLE_COLUMNS.items()
    }
    context.counters = {table_name: 1 for table_name in TABLE_COLUMNS}
