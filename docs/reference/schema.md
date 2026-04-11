---
title: Schema Reference
description: Compact reference for the 55 implemented Greenfield tables and key column patterns.
sidebar_label: Schema Reference
---

# Schema Reference

**Audience:** Contributors, advanced users, and instructors who need the implemented schema in a compact technical form.  
**Purpose:** Summarize the executable schema that the generator currently creates.  
**What you will learn:** The implemented table groups, key columns, and the patterns that matter for joins and traceability.

The canonical schema lives in `src/greenfield_dataset/schema.py` as `TABLE_COLUMNS`.


## Table Groups

| Group | Tables | Count |
|---|---|---:|
| Accounting core | `Account`, `JournalEntry`, `GLEntry` | 3 |
| O2C | `Customer`, `SalesOrder`, `SalesOrderLine`, `Shipment`, `ShipmentLine`, `SalesInvoice`, `SalesInvoiceLine`, `CashReceipt`, `CashReceiptApplication`, `SalesReturn`, `SalesReturnLine`, `CreditMemo`, `CreditMemoLine`, `CustomerRefund` | 14 |
| P2P | `Supplier`, `PurchaseRequisition`, `PurchaseOrder`, `PurchaseOrderLine`, `GoodsReceipt`, `GoodsReceiptLine`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment` | 9 |
| Manufacturing | `BillOfMaterial`, `BillOfMaterialLine`, `WorkCenter`, `WorkCenterCalendar`, `Routing`, `RoutingOperation`, `WorkOrder`, `WorkOrderOperation`, `WorkOrderOperationSchedule`, `MaterialIssue`, `MaterialIssueLine`, `ProductionCompletion`, `ProductionCompletionLine`, `WorkOrderClose` | 14 |
| Payroll and time | `ShiftDefinition`, `EmployeeShiftAssignment`, `TimeClockEntry`, `AttendanceException`, `PayrollPeriod`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollPayment`, `PayrollLiabilityRemittance` | 10 |
| Master data | `Item`, `Warehouse`, `Employee` | 3 |
| Organizational planning | `CostCenter`, `Budget` | 2 |
| Total |  | 55 |

## Design Patterns That Matter

- Header-line tables are used for orders, shipments, invoices, purchase orders, goods receipts, purchase invoices, material issues, production completions, and payroll registers.
- `GLEntry` is the reporting bridge between operational events and accounting analysis.
- `Item` carries account-mapping fields plus manufacturing and costing attributes such as `SupplyMode`, `ProductionLeadTimeDays`, `RoutingID`, `StandardLaborHoursPerUnit`, and `StandardConversionCost`.
- `JournalEntry` and `GLEntry` together represent opening, recurring, manufacturing, accrual-adjustment, and close-cycle activity without a separate journal-line table.
- Payroll is now operationally modeled through shift-assignment, time-clock, payroll-period, register, payment, and remittance tables rather than clean-build payroll accrual journals.

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
| `SalesInvoiceLine` | Sales invoice detail | `SalesInvoiceID`, `SalesOrderLineID`, `ShipmentLineID`, `ItemID`, `Quantity`, `UnitPrice`, `Discount`, `LineTotal` |
| `CashReceipt` | Customer payment header | `ReceiptNumber`, `ReceiptDate`, `CustomerID`, `SalesInvoiceID`, `Amount`, `PaymentMethod`, `ReferenceNumber`, `RecordedByEmployeeID` |
| `CashReceiptApplication` | Receipt-to-invoice application detail | `CashReceiptID`, `SalesInvoiceID`, `ApplicationDate`, `AppliedAmount`, `AppliedByEmployeeID` |
| `SalesReturn` | Customer return header | `ReturnNumber`, `ReturnDate`, `CustomerID`, `SalesOrderID`, `WarehouseID`, `ReasonCode`, `Status` |
| `SalesReturnLine` | Returned item detail | `SalesReturnID`, `ShipmentLineID`, `ItemID`, `QuantityReturned`, `ExtendedStandardCost` |
| `CreditMemo` | Customer credit memo header | `CreditMemoNumber`, `CreditMemoDate`, `SalesReturnID`, `OriginalSalesInvoiceID`, `SubTotal`, `TaxAmount`, `GrandTotal`, `Status` |
| `CreditMemoLine` | Customer credit memo detail | `CreditMemoID`, `SalesReturnLineID`, `ItemID`, `Quantity`, `UnitPrice`, `LineTotal` |
| `CustomerRefund` | Customer refund payment record | `RefundNumber`, `RefundDate`, `CustomerID`, `CreditMemoID`, `Amount`, `PaymentMethod`, `ReferenceNumber` |

## Procure-to-Pay

| Table | Purpose | High-value columns |
|---|---|---|
| `Supplier` | Supplier master data | `PaymentTerms`, `TaxID`, `BankAccount`, `SupplierCategory`, `SupplierRiskRating`, `DefaultCurrency` |
| `PurchaseRequisition` | Internal request document | `RequisitionNumber`, `RequestDate`, `RequestedByEmployeeID`, `CostCenterID`, `ItemID`, `Quantity`, `EstimatedUnitCost`, `ApprovedByEmployeeID`, `Status` |
| `PurchaseOrder` | Purchase order header | `PONumber`, `OrderDate`, `SupplierID`, `RequisitionID`, `ExpectedDeliveryDate`, `CreatedByEmployeeID`, `ApprovedByEmployeeID`, `OrderTotal`, `Status` |
| `PurchaseOrderLine` | Purchase order detail | `PurchaseOrderID`, `RequisitionID`, `LineNumber`, `ItemID`, `Quantity`, `UnitCost`, `LineTotal` |
| `GoodsReceipt` | Receipt header | `ReceiptNumber`, `ReceiptDate`, `PurchaseOrderID`, `WarehouseID`, `ReceivedByEmployeeID`, `Status` |
| `GoodsReceiptLine` | Receipt detail used for quantity and cost tracking | `GoodsReceiptID`, `POLineID`, `ItemID`, `QuantityReceived`, `ExtendedStandardCost` |
| `PurchaseInvoice` | Supplier invoice header | `InvoiceNumber`, `InvoiceDate`, `ReceivedDate`, `DueDate`, `PurchaseOrderID`, `SupplierID`, `SubTotal`, `TaxAmount`, `GrandTotal`, `ApprovedByEmployeeID`, `Status` |
| `PurchaseInvoiceLine` | Supplier invoice detail | `PurchaseInvoiceID`, `POLineID`, `GoodsReceiptLineID`, `AccrualJournalEntryID`, `LineNumber`, `ItemID`, `Quantity`, `UnitCost`, `LineTotal` |
| `DisbursementPayment` | Supplier payment record | `PaymentNumber`, `PaymentDate`, `SupplierID`, `PurchaseInvoiceID`, `Amount`, `PaymentMethod`, `CheckNumber`, `ApprovedByEmployeeID`, `ClearedDate` |

## Manufacturing

| Table | Purpose | High-value columns |
|---|---|---|
| `BillOfMaterial` | BOM header for manufactured items | `ParentItemID`, `VersionNumber`, `Status`, `StandardBatchQuantity` |
| `BillOfMaterialLine` | BOM component detail | `BOMID`, `ComponentItemID`, `LineNumber`, `QuantityPerUnit`, `ScrapFactorPct` |
| `WorkCenter` | Manufacturing resource grouping | `WorkCenterCode`, `WorkCenterName`, `Department`, `WarehouseID`, `ManagerEmployeeID`, `NominalDailyCapacityHours`, `IsActive` |
| `WorkCenterCalendar` | Daily work-center capacity calendar | `WorkCenterID`, `CalendarDate`, `IsWorkingDay`, `AvailableHours`, `ExceptionReason` |
| `Routing` | Routing header for manufactured items | `ParentItemID`, `VersionNumber`, `EffectiveStartDate`, `EffectiveEndDate`, `Status` |
| `RoutingOperation` | Ordered routing step | `RoutingID`, `OperationSequence`, `OperationCode`, `OperationName`, `WorkCenterID`, `StandardSetupHours`, `StandardRunHoursPerUnit`, `StandardQueueDays` |
| `WorkOrder` | Production order header | `ItemID`, `BOMID`, `RoutingID`, `WarehouseID`, `PlannedQuantity`, `ReleasedDate`, `DueDate`, `CompletedDate`, `ClosedDate`, `Status`, `CostCenterID` |
| `WorkOrderOperation` | Operation-level work-order execution record | `WorkOrderID`, `RoutingOperationID`, `OperationSequence`, `WorkCenterID`, `PlannedQuantity`, `PlannedLoadHours`, `PlannedStartDate`, `PlannedEndDate`, `ActualStartDate`, `ActualEndDate`, `Status` |
| `WorkOrderOperationSchedule` | Daily scheduled hours for one work-order operation | `WorkOrderOperationID`, `WorkCenterID`, `ScheduleDate`, `ScheduledHours` |
| `MaterialIssue` | Material issue header | `WorkOrderID`, `IssueDate`, `WarehouseID`, `IssuedByEmployeeID`, `Status` |
| `MaterialIssueLine` | Material issue detail | `MaterialIssueID`, `BOMLineID`, `ItemID`, `QuantityIssued`, `ExtendedStandardCost` |
| `ProductionCompletion` | Production completion header | `WorkOrderID`, `CompletionDate`, `WarehouseID`, `ReceivedByEmployeeID`, `Status` |
| `ProductionCompletionLine` | Production completion detail | `ProductionCompletionID`, `ItemID`, `QuantityCompleted`, `ExtendedStandardMaterialCost`, `ExtendedStandardDirectLaborCost`, `ExtendedStandardVariableOverheadCost`, `ExtendedStandardFixedOverheadCost`, `ExtendedStandardConversionCost`, `ExtendedStandardTotalCost` |
| `WorkOrderClose` | Work-order close and variance record | `WorkOrderID`, `CloseDate`, `MaterialVarianceAmount`, `DirectLaborVarianceAmount`, `OverheadVarianceAmount`, `ConversionVarianceAmount`, `TotalVarianceAmount`, `Status` |

## Payroll

| Table | Purpose | High-value columns |
|---|---|---|
| `ShiftDefinition` | Standard shift template for hourly work | `ShiftCode`, `ShiftName`, `Department`, `WorkCenterID`, `StartTime`, `EndTime`, `StandardBreakMinutes`, `ShiftType`, `IsOvernight` |
| `EmployeeShiftAssignment` | Employee-to-shift assignment | `EmployeeID`, `ShiftDefinitionID`, `EffectiveStartDate`, `EffectiveEndDate`, `WorkCenterID`, `IsPrimary` |
| `TimeClockEntry` | Approved daily time and attendance row | `EmployeeID`, `PayrollPeriodID`, `WorkDate`, `ShiftDefinitionID`, `WorkCenterID`, `WorkOrderID`, `WorkOrderOperationID`, `ClockInTime`, `ClockOutTime`, `RegularHours`, `OvertimeHours`, `ClockStatus` |
| `AttendanceException` | Logged time-and-attendance issue | `EmployeeID`, `PayrollPeriodID`, `WorkDate`, `ShiftDefinitionID`, `TimeClockEntryID`, `ExceptionType`, `Severity`, `MinutesVariance`, `Status` |
| `PayrollPeriod` | Biweekly payroll calendar | `PeriodNumber`, `PeriodStartDate`, `PeriodEndDate`, `PayDate`, `FiscalYear`, `FiscalPeriod`, `Status` |
| `LaborTimeEntry` | Employee labor detail used for payroll and costing | `PayrollPeriodID`, `EmployeeID`, `TimeClockEntryID`, `WorkOrderID`, `WorkOrderOperationID`, `WorkDate`, `LaborType`, `RegularHours`, `OvertimeHours`, `HourlyRateUsed`, `ExtendedLaborCost` |
| `PayrollRegister` | Employee payroll header | `PayrollPeriodID`, `EmployeeID`, `CostCenterID`, `GrossPay`, `EmployeeWithholdings`, `EmployerPayrollTax`, `EmployerBenefits`, `NetPay`, `Status` |
| `PayrollRegisterLine` | Earnings and deduction detail | `PayrollRegisterID`, `LineType`, `Hours`, `Rate`, `Amount`, `WorkOrderID`, `LaborTimeEntryID` |
| `PayrollPayment` | Net-pay settlement record | `PayrollRegisterID`, `PaymentDate`, `PaymentMethod`, `ReferenceNumber`, `ClearedDate` |
| `PayrollLiabilityRemittance` | Liability-clearance record | `PayrollPeriodID`, `LiabilityType`, `RemittanceDate`, `Amount`, `AgencyOrVendor`, `ReferenceNumber`, `ClearedDate` |

## Master Data

| Table | Purpose | High-value columns |
|---|---|---|
| `Item` | Product master and account mapping | `ItemCode`, `ItemGroup`, `SupplyMode`, `ProductionLeadTimeDays`, `RoutingID`, `StandardLaborHoursPerUnit`, `StandardDirectLaborCost`, `StandardVariableOverheadCost`, `StandardFixedOverheadCost`, `StandardConversionCost`, `StandardCost`, `InventoryAccountID`, `RevenueAccountID`, `COGSAccountID`, `PurchaseVarianceAccountID` |
| `Warehouse` | Inventory storage locations | `WarehouseName`, `ManagerID`, address fields |
| `Employee` | Employee and approval metadata | `CostCenterID`, `JobTitle`, `ManagerID`, `AuthorizationLevel`, `PayClass`, `BaseHourlyRate`, `BaseAnnualSalary`, `StandardHoursPerWeek`, `OvertimeEligible`, `IsActive` |

## Organizational Planning

| Table | Purpose | High-value columns |
|---|---|---|
| `CostCenter` | Organizational reporting structure | `CostCenterName`, `ParentCostCenterID`, `ManagerID`, `IsActive` |
| `Budget` | Monthly budget by fiscal year, cost center, and account | `FiscalYear`, `Month`, `CostCenterID`, `AccountID`, `BudgetAmount`, `ApprovedByEmployeeID` |

## Traceability Fields

The most important lineage fields in the implementation are:

- `PurchaseOrderLine.RequisitionID`
- `PurchaseInvoiceLine.GoodsReceiptLineID`
- `PurchaseInvoiceLine.AccrualJournalEntryID`
- `SalesInvoiceLine.ShipmentLineID`
- `CashReceiptApplication.CashReceiptID`
- `CashReceiptApplication.SalesInvoiceID`
- `SalesReturnLine.ShipmentLineID`
- `CreditMemo.SalesReturnID`
- `CreditMemo.OriginalSalesInvoiceID`
- `CustomerRefund.CreditMemoID`
- `WorkOrder.BOMID`
- `WorkOrder.RoutingID`
- `WorkOrderOperation.RoutingOperationID`
- `WorkOrderOperationSchedule.WorkOrderOperationID`
- `EmployeeShiftAssignment.ShiftDefinitionID`
- `TimeClockEntry.ShiftDefinitionID`
- `TimeClockEntry.WorkOrderOperationID`
- `AttendanceException.TimeClockEntryID`
- `MaterialIssueLine.BOMLineID`
- `ProductionCompletion.WorkOrderID`
- `WorkOrderClose.WorkOrderID`
- `LaborTimeEntry.WorkOrderID`
- `LaborTimeEntry.WorkOrderOperationID`
- `LaborTimeEntry.TimeClockEntryID`
- `PayrollRegister.PayrollPeriodID`
- `PayrollRegisterLine.PayrollRegisterID`
- `PayrollRegisterLine.LaborTimeEntryID`
- `PayrollPayment.PayrollRegisterID`
- `PayrollLiabilityRemittance.PayrollPeriodID`
- `GLEntry.SourceDocumentType`
- `GLEntry.SourceDocumentID`
- `GLEntry.SourceLineID`

## Current Implementation Notes

- `CashReceipt.SalesInvoiceID` is compatibility metadata only. The authoritative settlement link is `CashReceiptApplication`.
- `PurchaseOrder.RequisitionID` is compatibility metadata when a PO batches multiple requisitions.
- `PurchaseInvoiceLine.GoodsReceiptLineID` is the clean-match key for receipt-based inventory invoices.
- `PurchaseInvoiceLine.AccrualJournalEntryID` links direct service invoices back to month-end accrual journals.
- `GoodsReceiptLine.ExtendedStandardCost` stores the receipt posting basis used for inventory and GRNI.
- The manufacturing foundation uses single-level BOMs plus one active routing per manufactured item.
- `WorkCenterCalendar` and `WorkOrderOperationSchedule` add daily work-center capacity and scheduled-load detail.
- `WorkOrderOperation` is the operation-level planning and actual-flow bridge between routing design, scheduling, and payroll labor detail.
- Approved `TimeClockEntry` rows are the clean-build hour source for hourly payroll.
- Payroll is operationally modeled, but manufacturing still uses standard-cost valuation rather than full actual-cost inventory.
- For exact column order and names, use `TABLE_COLUMNS` in `src/greenfield_dataset/schema.py`.
