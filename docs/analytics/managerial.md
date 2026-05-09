---
title: Managerial Queries
description: Managerial and cost-accounting query library for portfolio, labor, manufacturing, planning, replenishment, pricing, and operating performance.
sidebar_label: Managerial Queries
---

import { QueryGroupCatalog } from "@site/src/components/QueryReference";
import { queryLibraryGroups } from "@site/src/generated/queryDocCollections";

# Managerial Queries

Use this page as the managerial and cost-accounting query library. The groups below organize reusable SQL around cost management, portfolio performance, sales commissions, inventory and supplier behavior, manufacturing operations, workforce coverage, planning, replenishment, and design-service utilization.

## Managerial Query Groups

<QueryGroupCatalog groups={queryLibraryGroups.managerial} />

## Main Table Families

| Topic | Main tables |
|---|---|
| Budget vs actual | `Budget`, `BudgetLine`, `CostCenter`, `Account`, `GLEntry`, `JournalEntry` |
| Product portfolio and sales mix | `Item`, `SalesInvoiceLine`, `CreditMemoLine`, `ShipmentLine`, `SalesOrderLine`, `Customer`, `PriceList`, `PriceListLine`, `PromotionProgram`, `PriceOverrideApproval` |
| Sales commissions | `SalesCommissionAccrual`, `SalesCommissionAdjustment`, `SalesCommissionRate`, `SalesCommissionPaymentLine`, `SalesInvoiceLine`, `CreditMemoLine`, `Employee`, `Customer` |
| Inventory and purchasing | `GoodsReceiptLine`, `ShipmentLine`, `SalesReturnLine`, `ProductionCompletionLine`, `PurchaseOrderLine`, `Supplier`, `Warehouse`, `Item` |
| BOM, routing, and work-center planning | `BillOfMaterial`, `BillOfMaterialLine`, `Routing`, `RoutingOperation`, `WorkCenter`, `WorkCenterCalendar`, `Item` |
| Work-order throughput and variance | `WorkOrder`, `WorkOrderOperation`, `WorkOrderOperationSchedule`, `MaterialIssueLine`, `ProductionCompletionLine`, `WorkOrderClose` |
| Labor, headcount, payroll mix, and workforce planning | `Employee`, `EmployeeShiftRoster`, `EmployeeAbsence`, `OvertimeApproval`, `TimeClockPunch`, `TimeClockEntry`, `LaborTimeEntry`, `PayrollRegister`, `WorkCenter`, `CostCenter` |

## Recommended Case Pairings

- Use [Product Portfolio Profitability Case](cases/product-portfolio-profitability-case.md) when you want a portfolio, lifecycle, and contribution-margin sequence.
- Use [Workforce Cost and Org-Control Case](cases/workforce-cost-and-org-control-case.md) when you want workforce structure, labor mix, and approval concentration in one lab.
- Use [Workforce Coverage and Attendance Case](cases/workforce-coverage-and-attendance-case.md) when you want planned staffing, approved time, absences, and overtime in one operational lab.
- Use [Demand Planning and Replenishment Case](cases/demand-planning-and-replenishment-case.md) when you want forecast, replenishment, component-demand, and rough-cut capacity analysis in one sequence.
- Use [Pricing and Margin Governance Case](cases/pricing-and-margin-governance-case.md) when you want commercial policy, promotion effect, override concentration, and collection-level margin analysis in one case.
- Use [Product Portfolio Case](cases/product-portfolio-and-lifecycle-case.md) when you want a lighter introductory entry point before moving into the broader profitability pack.

## Interpretation Notes

- The item master now supports collection, style family, material, finish, color, lifecycle, and supply-mode analysis inside the existing `Item` table.
- The employee master now supports work location, job family, job level, employment status, and current-state active analysis without adding a separate HR-history model.
- Supply mode changes the meaning of cost analysis. Manufactured items can support both absorption and contribution-margin work because fixed overhead is stored separately.
- Portfolio mix and profitability should be read together with service-level measures such as fill rate, shipment lag, and return pressure.
- Work location and cost center answer different questions. Use both when students compare workforce structure to payroll or labor usage.
- Workforce-planning analysis is stronger now that rostered hours, approved worked hours, absences, raw punches, and overtime approvals can be compared directly.
- The dataset includes a weekly planning layer, so students can compare forecast, policy, recommendation, and rough-cut capacity pressure before execution starts.
- The dataset includes commercial-pricing coverage, so students can compare list price, resolved price-list pricing, promotions, overrides, and net realized margin without introducing a separate quote system.
- Sales commissions are modeled as a separate selling-cost subledger, so students can compare commission expense by rep, segment, and revenue type without mixing it into payroll.
- The budget model now starts from `BudgetLine`, so students can move from forecast, planned price, standard cost, payroll, and timing assumptions into the summary `Budget` table and the pro forma statements.
- The current manufacturing model is still a foundation. It supports operations, labor, and contribution-margin analysis without switching inventory valuation to actual cost.
- Demand-planning analysis is most useful when students connect `DemandForecast`, `InventoryPolicy`, `SupplyPlanRecommendation`, `MaterialRequirementPlan`, and `RoughCutCapacityPlan` in one analytical path.
