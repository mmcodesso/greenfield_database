---
title: Audit Analytics
description: Starter auditing and controls analytics paths using the published dataset.
sidebar_label: Audit Analytics
---

import { QueryCatalog } from "@site/src/components/QueryReference";
import {
  auditAnomalyQueryCards,
  starterQueryMaps,
} from "@site/src/generated/queryDocCollections";

# Audit Analytics Starter Guide

## Relevant Tables

| Topic | Main tables |
|---|---|
| O2C and P2P completeness | O2C and P2P header and line tables plus `CashReceiptApplication` |
| Approvals and segregation of duties | `PurchaseRequisition`, `PurchaseOrder`, `PurchaseInvoice`, `JournalEntry`, `CreditMemo`, `CustomerRefund`, `PayrollRegister`, `Employee` |
| Manufacturing controls | `Item`, `BillOfMaterial`, `Routing`, `WorkCenter`, `WorkOrder`, `WorkOrderOperation`, `WorkOrderOperationSchedule`, `MaterialIssueLine`, `ProductionCompletionLine`, `WorkOrderClose` |
| Payroll and time controls | `ShiftDefinition`, `EmployeeShiftAssignment`, `EmployeeShiftRoster`, `EmployeeAbsence`, `OvertimeApproval`, `TimeClockPunch`, `TimeClockEntry`, `AttendanceException`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollPayment`, `PayrollLiabilityRemittance`, `Employee` |
| Master-data controls | `Employee`, `Item`, `PriceList`, `PriceListLine`, `PromotionProgram`, `PriceOverrideApproval`, plus operational tables that reuse those masters |
| Cross-process control review | Combine query output with source-table tracing across the affected process tables |

## Starter SQL Map

<QueryCatalog items={starterQueryMaps.audit} />

## Baseline Control Queries

Use these first when you want control logic without relying on planted anomalies:

- O2C and P2P completeness
- approval-role review by organization position
- executive-role uniqueness and control-assignment review
- approval-authority review by expected role family

## Exception-Oriented Queries

Use these when you want students to review the exception patterns present in the published dataset:

- duplicate payment or AP reference review
- payroll control review
- routing and operation-link review
- released work orders due without actual start review
- released work orders due without actual start summary
- time-clock and labor exception review
- roster, punch, absence, and overtime-approval review
- terminated-employee activity review
- item-master completeness review
- discontinued or pre-launch item activity review
- current-state employee assignment review
- approval authority-limit review
- item status alignment review
- forecast approval and override review
- inactive or stale inventory policy review
- requisitions and work orders without planning support
- recommendation converted after need-by date review
- discontinued or pre-launch planning activity review
- sales below floor without approval
- expired or overlapping price-list review
- promotion scope and date mismatch review
- customer-specific price-list bypass review
- override approval completeness review

## Interpretation Notes

- Exception-oriented queries are designed to return reviewable control patterns from the published dataset.
- The GL remains balanced even when audit queries identify exceptions.
- Employee-master review should distinguish current-state `IsActive` from historical validity driven by `HireDate` and `TerminationDate`.
- Item-master review should distinguish current-state lifecycle and launch-date logic from operational usage timing.
- Pricing-control review should distinguish price-list master-data failures from transaction-level override and promotion-use failures.
- Source-table tracing should remain the final step in explaining each exception pattern.

## Anomaly Coverage Queries

<QueryCatalog items={auditAnomalyQueryCards} />
