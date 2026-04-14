---
title: Schema Reference
description: Student-friendly reference for the 68 implemented Greenfield tables, key columns, and join patterns.
sidebar_label: Schema Reference
---

# Schema Reference

Use this page when you need a lookup tool: which tables belong to each business area, which fields matter most for joins, and which columns are the fastest way back to the source document.

If you need the big-picture map first, start with [Dataset Guide](../start-here/dataset-overview.md). The canonical schema lives in `src/greenfield_dataset/schema.py` as `TABLE_COLUMNS`.

## How to Use This Page

- Use **Table Groups** when you want to see the model at a glance.
- Use the area sections when you need the main purpose and highest-value fields for a table.
- Use **Join and Traceability Cues** when you know the process but need the exact bridge fields.

## Table Groups

| Group | What belongs here | Count |
|---|---|---:|
| Accounting core | Accounts, journals, and posted ledger detail | 3 |
| O2C | Customer, pricing, order, shipment, invoice, receipt, return, credit, and refund tables | 18 |
| P2P | Supplier, requisition, PO, receipt, invoice, and payment tables | 9 |
| Manufacturing | BOMs, routings, work centers, work orders, issues, completions, and close | 14 |
| Payroll and time | Shift, roster, absence, overtime, time, payroll, and remittance tables | 14 |
| Master data | Item, warehouse, and employee records | 3 |
| Organizational planning | Cost centers and budgets | 2 |
| Demand planning and MRP | Forecasting, policy, recommendation, MRP, and rough-cut capacity tables | 5 |
| Total |  | 68 |

## Design Patterns

- Header-line tables are used for sales, purchasing, material issues, completions, and payroll registers.
- `GLEntry` is the reporting bridge between operational events and accounting analysis.
- `JournalEntry` and `GLEntry` together represent recurring finance activity, accrual adjustments, reclasses, and close-cycle entries.
- `Item` is the product anchor for pricing, costing, supply mode, and account mapping.
- `PriceList`, `PriceListLine`, `PromotionProgram`, and `PriceOverrideApproval` provide explicit commercial-pricing lineage inside the O2C flow.
- Payroll and time are modeled as operational tables, not as a simple journal simulation.

## Accounting Core

| Table | Use it for | Start with these fields |
|---|---|---|
| `Account` | Chart of accounts and hierarchy | `AccountNumber`, `AccountType`, `AccountSubType`, `ParentAccountID`, `NormalBalance` |
| `JournalEntry` | Manual journal header lookup | `EntryNumber`, `PostingDate`, `EntryType`, `ApprovedByEmployeeID`, `ReversesJournalEntryID` |
| `GLEntry` | Posted ledger detail and source traceability | `PostingDate`, `AccountID`, `Debit`, `Credit`, `VoucherType`, `VoucherNumber`, `SourceDocumentType`, `SourceDocumentID`, `SourceLineID`, `FiscalYear`, `FiscalPeriod` |

## Order-to-Cash

| Table | Use it for | Start with these fields |
|---|---|---|
| `Customer` | Customer master and segmentation | `CustomerName`, `CustomerSegment`, `Industry`, `Region`, `SalesRepEmployeeID` |
| `PriceList` | Pricing scope header by segment or customer | `PriceListName`, `ScopeType`, `CustomerID`, `CustomerSegment`, `EffectiveStartDate`, `EffectiveEndDate`, `Status` |
| `PriceListLine` | Item-level price and floor by quantity break | `PriceListID`, `ItemID`, `MinimumQuantity`, `UnitPrice`, `MinimumUnitPrice`, `Status` |
| `PromotionProgram` | Seasonal or scoped promotion master | `PromotionCode`, `ScopeType`, `CustomerSegment`, `ItemGroup`, `CollectionName`, `DiscountPct`, `EffectiveStartDate`, `EffectiveEndDate` |
| `PriceOverrideApproval` | Manual below-floor approval record | `SalesOrderLineID`, `RequestedByEmployeeID`, `ApprovedByEmployeeID`, `ReferenceUnitPrice`, `ApprovedUnitPrice`, `ReasonCode`, `Status` |
| `SalesOrder` | Order header and promised demand | `OrderNumber`, `OrderDate`, `CustomerID`, `RequestedDeliveryDate`, `Status` |
| `SalesOrderLine` | Ordered item detail with pricing lineage | `SalesOrderID`, `LineNumber`, `ItemID`, `Quantity`, `BaseListPrice`, `UnitPrice`, `Discount`, `PriceListLineID`, `PromotionID`, `PriceOverrideApprovalID`, `PricingMethod`, `LineTotal` |
| `Shipment` | Shipment header and warehouse fulfillment | `ShipmentNumber`, `SalesOrderID`, `ShipmentDate`, `WarehouseID`, `Status` |
| `ShipmentLine` | Shipped item detail and COGS basis | `ShipmentID`, `SalesOrderLineID`, `ItemID`, `QuantityShipped`, `ExtendedStandardCost` |
| `SalesInvoice` | Invoice header and receivable creation | `InvoiceNumber`, `InvoiceDate`, `CustomerID`, `DueDate`, `GrandTotal`, `Status` |
| `SalesInvoiceLine` | Billed line detail tied to fulfillment and inherited pricing lineage | `SalesInvoiceID`, `SalesOrderLineID`, `ShipmentLineID`, `ItemID`, `Quantity`, `BaseListPrice`, `UnitPrice`, `Discount`, `PriceListLineID`, `PromotionID`, `PriceOverrideApprovalID`, `PricingMethod`, `LineTotal` |
| `CashReceipt` | Customer payment record | `ReceiptNumber`, `ReceiptDate`, `CustomerID`, `Amount`, `PaymentMethod`, `ReferenceNumber` |
| `CashReceiptApplication` | Invoice settlement detail | `CashReceiptID`, `SalesInvoiceID`, `ApplicationDate`, `AppliedAmount` |
| `SalesReturn` | Return header | `ReturnNumber`, `ReturnDate`, `CustomerID`, `ReasonCode`, `Status` |
| `SalesReturnLine` | Returned item detail | `SalesReturnID`, `ShipmentLineID`, `ItemID`, `QuantityReturned` |
| `CreditMemo` | Customer credit header | `CreditMemoNumber`, `CreditMemoDate`, `SalesReturnID`, `OriginalSalesInvoiceID`, `GrandTotal`, `Status` |
| `CreditMemoLine` | Credit detail by returned line with inherited pricing lineage | `CreditMemoID`, `SalesReturnLineID`, `ItemID`, `Quantity`, `BaseListPrice`, `UnitPrice`, `Discount`, `PriceListLineID`, `PromotionID`, `PriceOverrideApprovalID`, `PricingMethod`, `LineTotal` |
| `CustomerRefund` | Cash refund against customer credit | `RefundNumber`, `RefundDate`, `CustomerID`, `CreditMemoID`, `Amount` |

### Join and Traceability Cues

- `SalesOrder -> SalesOrderLine`
- `PriceListLine.PriceListID -> PriceList`
- `SalesOrderLine.PriceListLineID -> PriceListLine`
- `SalesOrderLine.PromotionID -> PromotionProgram`
- `SalesOrderLine.PriceOverrideApprovalID -> PriceOverrideApproval`
- `Shipment.SalesOrderID -> SalesOrder`
- `ShipmentLine.SalesOrderLineID -> SalesOrderLine`
- `SalesInvoiceLine.ShipmentLineID -> ShipmentLine`
- `CashReceiptApplication.SalesInvoiceID -> SalesInvoice`
- `SalesReturnLine.ShipmentLineID -> ShipmentLine`
- `CreditMemo.OriginalSalesInvoiceID -> SalesInvoice`
- `CustomerRefund.CreditMemoID -> CreditMemo`

## Procure-to-Pay

| Table | Use it for | Start with these fields |
|---|---|---|
| `Supplier` | Supplier master and risk context | `SupplierName`, `PaymentTerms`, `SupplierCategory`, `SupplierRiskRating`, `DefaultCurrency` |
| `PurchaseRequisition` | Internal purchase demand | `RequisitionNumber`, `RequestDate`, `RequestedByEmployeeID`, `CostCenterID`, `ItemID`, `Status`, `SupplyPlanRecommendationID` |
| `PurchaseOrder` | PO header and supplier commitment | `PONumber`, `OrderDate`, `SupplierID`, `ExpectedDeliveryDate`, `Status` |
| `PurchaseOrderLine` | Ordered item detail | `PurchaseOrderID`, `RequisitionID`, `ItemID`, `Quantity`, `UnitCost`, `LineTotal` |
| `GoodsReceipt` | Receipt header | `ReceiptNumber`, `ReceiptDate`, `PurchaseOrderID`, `WarehouseID`, `Status` |
| `GoodsReceiptLine` | Receipt detail and inventory posting basis | `GoodsReceiptID`, `POLineID`, `ItemID`, `QuantityReceived`, `ExtendedStandardCost` |
| `PurchaseInvoice` | Supplier invoice header | `InvoiceNumber`, `InvoiceDate`, `SupplierID`, `PurchaseOrderID`, `GrandTotal`, `Status` |
| `PurchaseInvoiceLine` | Supplier invoice detail | `PurchaseInvoiceID`, `POLineID`, `GoodsReceiptLineID`, `AccrualJournalEntryID`, `ItemID`, `Quantity`, `LineTotal` |
| `DisbursementPayment` | Supplier payment record | `PaymentNumber`, `PaymentDate`, `SupplierID`, `PurchaseInvoiceID`, `Amount`, `PaymentMethod` |

### Join and Traceability Cues

- `PurchaseOrderLine.RequisitionID -> PurchaseRequisition`
- `GoodsReceipt.PurchaseOrderID -> PurchaseOrder`
- `GoodsReceiptLine.POLineID -> PurchaseOrderLine`
- `PurchaseInvoiceLine.GoodsReceiptLineID -> GoodsReceiptLine`
- `PurchaseInvoiceLine.AccrualJournalEntryID -> JournalEntry`
- `DisbursementPayment.PurchaseInvoiceID -> PurchaseInvoice`

## Manufacturing

| Table | Use it for | Start with these fields |
|---|---|---|
| `BillOfMaterial` | BOM header for manufactured items | `ParentItemID`, `VersionNumber`, `Status`, `StandardBatchQuantity` |
| `BillOfMaterialLine` | BOM component detail | `BOMID`, `ComponentItemID`, `LineNumber`, `QuantityPerUnit`, `ScrapFactorPct` |
| `WorkCenter` | Work-center master | `WorkCenterCode`, `WorkCenterName`, `Department`, `WarehouseID`, `NominalDailyCapacityHours` |
| `WorkCenterCalendar` | Daily available-hours calendar | `WorkCenterID`, `CalendarDate`, `IsWorkingDay`, `AvailableHours`, `ExceptionReason` |
| `Routing` | Routing header for one manufactured item | `ParentItemID`, `VersionNumber`, `Status`, `EffectiveStartDate`, `EffectiveEndDate` |
| `RoutingOperation` | Ordered routing step | `RoutingID`, `OperationSequence`, `OperationCode`, `OperationName`, `WorkCenterID` |
| `WorkOrder` | Production order header | `WorkOrderNumber`, `ItemID`, `BOMID`, `RoutingID`, `WarehouseID`, `PlannedQuantity`, `Status`, `SupplyPlanRecommendationID` |
| `WorkOrderOperation` | Operation-level work-order activity | `WorkOrderID`, `RoutingOperationID`, `OperationSequence`, `WorkCenterID`, `PlannedLoadHours`, `Status` |
| `WorkOrderOperationSchedule` | Daily scheduled hours for one operation | `WorkOrderOperationID`, `WorkCenterID`, `ScheduleDate`, `ScheduledHours` |
| `MaterialIssue` | Material issue header | `WorkOrderID`, `IssueDate`, `WarehouseID`, `Status` |
| `MaterialIssueLine` | Material issue detail | `MaterialIssueID`, `BOMLineID`, `ItemID`, `QuantityIssued`, `ExtendedStandardCost` |
| `ProductionCompletion` | Completion header | `WorkOrderID`, `CompletionDate`, `WarehouseID`, `Status` |
| `ProductionCompletionLine` | Completion cost detail | `ProductionCompletionID`, `ItemID`, `QuantityCompleted`, `ExtendedStandardTotalCost` |
| `WorkOrderClose` | Work-order close and variance record | `WorkOrderID`, `CloseDate`, `TotalVarianceAmount`, `Status` |

### Join and Traceability Cues

- `WorkOrder.BOMID -> BillOfMaterial`
- `WorkOrder.RoutingID -> Routing`
- `WorkOrderOperation.RoutingOperationID -> RoutingOperation`
- `WorkOrderOperationSchedule.WorkOrderOperationID -> WorkOrderOperation`
- `MaterialIssue.WorkOrderID -> WorkOrder`
- `MaterialIssueLine.BOMLineID -> BillOfMaterialLine`
- `ProductionCompletion.WorkOrderID -> WorkOrder`
- `WorkOrderClose.WorkOrderID -> WorkOrder`

## Payroll and Time

| Table | Use it for | Start with these fields |
|---|---|---|
| `ShiftDefinition` | Standard shift template | `ShiftCode`, `ShiftName`, `Department`, `WorkCenterID`, `StartTime`, `EndTime` |
| `EmployeeShiftAssignment` | Employee-to-shift assignment | `EmployeeID`, `ShiftDefinitionID`, `EffectiveStartDate`, `EffectiveEndDate`, `WorkCenterID`, `IsPrimary` |
| `EmployeeShiftRoster` | Daily planned roster row | `EmployeeID`, `RosterDate`, `ShiftDefinitionID`, `WorkCenterID`, `ScheduledStartTime`, `ScheduledHours`, `RosterStatus` |
| `EmployeeAbsence` | Absence tied to the roster | `EmployeeID`, `PayrollPeriodID`, `AbsenceDate`, `EmployeeShiftRosterID`, `AbsenceType`, `HoursAbsent`, `Status` |
| `OvertimeApproval` | Approved overtime request | `EmployeeID`, `PayrollPeriodID`, `WorkDate`, `EmployeeShiftRosterID`, `ApprovedHours`, `ReasonCode`, `Status` |
| `TimeClockEntry` | Approved daily time record | `EmployeeID`, `PayrollPeriodID`, `WorkDate`, `EmployeeShiftRosterID`, `OvertimeApprovalID`, `WorkOrderOperationID`, `RegularHours`, `OvertimeHours`, `ClockStatus` |
| `TimeClockPunch` | Raw punch events under the approved daily summary | `EmployeeID`, `WorkDate`, `EmployeeShiftRosterID`, `TimeClockEntryID`, `PunchTimestamp`, `PunchType` |
| `AttendanceException` | Attendance-control exception log | `EmployeeID`, `PayrollPeriodID`, `WorkDate`, `EmployeeShiftRosterID`, `TimeClockEntryID`, `ExceptionType`, `Severity`, `Status` |
| `PayrollPeriod` | Biweekly payroll calendar | `PeriodNumber`, `PeriodStartDate`, `PeriodEndDate`, `PayDate`, `FiscalYear`, `FiscalPeriod` |
| `LaborTimeEntry` | Labor detail used for payroll and costing | `PayrollPeriodID`, `EmployeeID`, `TimeClockEntryID`, `WorkOrderID`, `WorkOrderOperationID`, `LaborType`, `RegularHours`, `ExtendedLaborCost` |
| `PayrollRegister` | Payroll header | `PayrollPeriodID`, `EmployeeID`, `CostCenterID`, `GrossPay`, `NetPay`, `Status` |
| `PayrollRegisterLine` | Earnings and deduction detail | `PayrollRegisterID`, `LineType`, `Hours`, `Rate`, `Amount`, `LaborTimeEntryID` |
| `PayrollPayment` | Net-pay settlement | `PayrollRegisterID`, `PaymentDate`, `PaymentMethod`, `ReferenceNumber`, `ClearedDate` |
| `PayrollLiabilityRemittance` | Liability clearance | `PayrollPeriodID`, `LiabilityType`, `RemittanceDate`, `Amount`, `AgencyOrVendor` |

### Join and Traceability Cues

- `EmployeeShiftAssignment.ShiftDefinitionID -> ShiftDefinition`
- `EmployeeShiftRoster.ShiftDefinitionID -> ShiftDefinition`
- `EmployeeAbsence.EmployeeShiftRosterID -> EmployeeShiftRoster`
- `OvertimeApproval.EmployeeShiftRosterID -> EmployeeShiftRoster`
- `TimeClockEntry.EmployeeShiftRosterID -> EmployeeShiftRoster`
- `TimeClockEntry.OvertimeApprovalID -> OvertimeApproval`
- `TimeClockPunch.TimeClockEntryID -> TimeClockEntry`
- `AttendanceException.TimeClockEntryID -> TimeClockEntry`
- `LaborTimeEntry.TimeClockEntryID -> TimeClockEntry`
- `PayrollRegister.PayrollPeriodID -> PayrollPeriod`
- `PayrollRegisterLine.LaborTimeEntryID -> LaborTimeEntry`
- `PayrollPayment.PayrollRegisterID -> PayrollRegister`
- `PayrollLiabilityRemittance.PayrollPeriodID -> PayrollPeriod`

## Master Data

| Table | Use it for | Start with these fields |
|---|---|---|
| `Item` | Product master and account mapping | `ItemCode`, `ItemName`, `ItemGroup`, `CollectionName`, `StyleFamily`, `PrimaryMaterial`, `LifecycleStatus`, `SupplyMode`, `StandardCost`, `InventoryAccountID`, `RevenueAccountID`, `COGSAccountID` |
| `Warehouse` | Warehouse master | `WarehouseName`, `ManagerID`, address fields |
| `Employee` | Employee master and approval metadata | `EmployeeNumber`, `JobTitle`, `JobFamily`, `JobLevel`, `WorkLocation`, `EmploymentStatus`, `TerminationDate`, `AuthorizationLevel`, `PayClass`, `OvertimeEligible` |

## Organizational Planning

| Table | Use it for | Start with these fields |
|---|---|---|
| `CostCenter` | Organizational reporting structure | `CostCenterName`, `ParentCostCenterID`, `ManagerID`, `IsActive` |
| `Budget` | Monthly budget by cost center and account | `FiscalYear`, `Month`, `CostCenterID`, `AccountID`, `BudgetAmount` |

## Demand Planning and MRP

| Table | Use it for | Start with these fields |
|---|---|---|
| `DemandForecast` | Weekly demand-planning input | `ForecastWeekStartDate`, `ItemID`, `WarehouseID`, `ForecastQuantity`, `ForecastMethod`, `PlannerEmployeeID`, `ApprovedByEmployeeID`, `IsCurrent` |
| `InventoryPolicy` | Active replenishment-policy master | `ItemID`, `WarehouseID`, `PlanningGroup`, `PolicyType`, `SafetyStockQuantity`, `ReorderPointQuantity`, `TargetDaysSupply`, `IsActive` |
| `SupplyPlanRecommendation` | Weekly replenishment recommendation | `RecommendationDate`, `BucketWeekStartDate`, `ItemID`, `WarehouseID`, `RecommendationType`, `SupplyMode`, `RecommendedOrderQuantity`, `RecommendationStatus`, `ConvertedDocumentType`, `ConvertedDocumentID` |
| `MaterialRequirementPlan` | Component-demand explosion | `BucketWeekStartDate`, `ParentItemID`, `ComponentItemID`, `SupplyPlanRecommendationID`, `GrossRequirementQuantity`, `NetRequirementQuantity` |
| `RoughCutCapacityPlan` | Weekly load-versus-capacity tieout | `BucketWeekStartDate`, `WorkCenterID`, `ItemID`, `SupplyPlanRecommendationID`, `PlannedLoadHours`, `AvailableHours`, `UtilizationPct`, `CapacityStatus` |

### Join and Traceability Cues

- `PurchaseRequisition.SupplyPlanRecommendationID -> SupplyPlanRecommendation`
- `WorkOrder.SupplyPlanRecommendationID -> SupplyPlanRecommendation`
- `MaterialRequirementPlan.SupplyPlanRecommendationID -> SupplyPlanRecommendation`
- `RoughCutCapacityPlan.SupplyPlanRecommendationID -> SupplyPlanRecommendation`

## Important Schema Notes

- `CashReceipt.SalesInvoiceID` is compatibility metadata only. The authoritative settlement link is `CashReceiptApplication`.
- Price-list and promotion lineage live directly on `SalesOrderLine`, `SalesInvoiceLine`, and `CreditMemoLine`; postings still remain net revenue rather than separate contra-revenue discount postings.
- `PurchaseOrder.RequisitionID` is compatibility metadata when a PO batches multiple requisitions.
- `PurchaseInvoiceLine.GoodsReceiptLineID` is the main match key for receipt-based inventory invoicing.
- `PurchaseInvoiceLine.AccrualJournalEntryID` links direct service invoices back to accrual journals.
- `GoodsReceiptLine.ExtendedStandardCost` stores the receipt posting basis used for inventory and GRNI.
- `EmployeeShiftRoster`, `EmployeeAbsence`, `TimeClockPunch`, and `OvertimeApproval` sit beneath the approved `TimeClockEntry` layer.
- Manufacturing uses single-level BOMs plus one active routing per manufactured item.
- Manufacturing remains standard-cost based even though payroll and time provide operational labor detail.

## Where to Go Next

- Read [Dataset Guide](../start-here/dataset-overview.md) when you need the mental model, main paths, and posting overview.
- Read [Process Flows](../learn-the-business/process-flows.md) when you want the business-cycle story behind the tables.
- Read [GLEntry Posting Reference](posting.md) when you want the exact event-to-ledger rules.
