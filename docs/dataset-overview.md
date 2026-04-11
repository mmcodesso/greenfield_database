# Dataset Overview

**Audience:** Students, instructors, and analysts using the dataset in AIS, accounting analytics, managerial accounting, and auditing courses.  
**Purpose:** Explain what the dataset is, why it exists, and what it currently contains.  
**What you will learn:** The database scope, business context, implemented process coverage, and the core terms used across the project.

## What This Project Is

Greenfield Accounting Dataset is a teachable business database for **Greenfield Home Furnishings, Inc.**

It connects:

- business processes
- operational source documents
- subledger logic
- posted `GLEntry` records

The project is built for:

- SQL exercises
- Excel analysis
- financial accounting analytics
- managerial accounting analytics
- auditing and controls analytics
- document tracing and business-process understanding

> **Implemented in current generator:** A five-year dataset with 55 tables covering O2C, P2P, manufacturing, payroll, time and attendance, accounting core, master data, budgets, recurring journals, year-end close, validations, anomalies, and exports.

> **Planned future extension:** Raw punch-event detail, richer shift planning, and deeper cost-accounting detail.

## Business Context

Greenfield is a hybrid manufacturer-distributor with two warehouses and one manufacturing cost center.

The current dataset models a company that:

- sells finished goods to customers
- buys finished goods, raw materials, and packaging from suppliers
- manufactures selected finished goods internally
- ships, invoices, collects cash, processes returns, and issues credit memos and refunds
- assigns shifts, records approved daily time clocks for hourly employees, and runs payroll
- records recurring journals, manufacturing reclasses, and year-end close

Read [company-story.md](company-story.md) for the narrative version of that operating model.

## What the Database Contains

The current implementation contains **55 tables** across seven areas:

| Area | Example tables | Count |
|---|---|---:|
| Accounting core | `Account`, `JournalEntry`, `GLEntry` | 3 |
| Order-to-cash | `Customer`, `SalesOrder`, `Shipment`, `SalesInvoice`, `CashReceiptApplication`, `SalesReturn`, `CreditMemo`, `CustomerRefund` | 14 |
| Procure-to-pay | `Supplier`, `PurchaseRequisition`, `PurchaseOrder`, `GoodsReceipt`, `PurchaseInvoice`, `DisbursementPayment` | 9 |
| Manufacturing | `BillOfMaterial`, `BillOfMaterialLine`, `WorkCenter`, `WorkCenterCalendar`, `Routing`, `RoutingOperation`, `WorkOrder`, `WorkOrderOperation`, `WorkOrderOperationSchedule`, `MaterialIssue`, `ProductionCompletion`, `WorkOrderClose` | 14 |
| Payroll and time | `ShiftDefinition`, `EmployeeShiftAssignment`, `TimeClockEntry`, `AttendanceException`, `PayrollPeriod`, `LaborTimeEntry`, `PayrollRegister`, `PayrollRegisterLine`, `PayrollPayment`, `PayrollLiabilityRemittance` | 10 |
| Master data | `Item`, `Warehouse`, `Employee` | 3 |
| Organizational planning | `CostCenter`, `Budget` | 2 |

The project also produces release-ready outputs:

- a SQLite database
- an Excel workbook
- a JSON validation report
- a generation log

## What Students Can Do With It

### Financial accounting

Students can:

- analyze revenue, COGS, contra revenue, and close-cycle activity
- reconcile AR using invoices, cash applications, credit memos, and refunds
- reconcile AP using purchase invoices and disbursements
- review WIP, manufacturing clearing, and manufacturing variance balances
- review payroll liabilities, gross-to-net payroll, time-clock-to-payroll support, and payroll cash flows
- trace source transactions into `GLEntry`

### Managerial accounting

Students can:

- compare budget to actual by cost center and account
- analyze sales mix by product, customer, region, and segment
- study warehouse movement and supplier concentration
- roll up BOM-based standard costs
- analyze work-order throughput, completions, production variance, and direct labor cost
- compare absorption cost and contribution margin for manufactured versus purchased items

### Auditing

Students can:

- test O2C, P2P, and manufacturing document chains
- test payroll approvals, time-clock support, time-entry linkage, and payroll-control behavior
- review approvals and segregation-of-duties patterns
- examine timing and cut-off behavior
- detect duplicate references and planted anomalies
- trace source documents to posted ledger activity

## What Is Not in Scope Yet

The current generator does **not** yet include:

- raw punch-event tables beneath the current approved daily time-clock rows
- rotating shift rosters or shift-level capacity calendars
- multi-level BOMs or subassemblies

Those topics are future roadmap items, not hidden functionality.

## Glossary

| Term | Plain-language meaning |
|---|---|
| O2C | Order-to-cash. The sales cycle from customer order through billing, cash application, and possible return activity. |
| P2P | Procure-to-pay. The purchasing cycle from requisition through supplier payment. |
| BOM | Bill of material. The standard list of components required to make a manufactured item. |
| WIP | Work in process. Inventory value that has been issued into production but not yet completed into finished goods. |
| GL | General ledger. The accounting table used for reporting and control-account reconciliation. |
| Control account | A GL account such as AR, AP, inventory, GRNI, customer deposits, WIP, or manufacturing clearing that summarizes detailed activity. |
| GRNI | Goods Received Not Invoiced. A liability recorded when inventory is received before the supplier invoice is approved. |
| Manufacturing variance | The difference between actual and standard manufacturing cost that is closed from work orders. |
| Absorption cost | Full product cost including direct material, direct labor, variable overhead, and fixed overhead. |
| Contribution margin | Revenue less variable product cost. In this dataset, fixed overhead is excluded from contribution-margin analysis. |
| Cost center | An organizational unit used for planning and performance analysis. |
| Anomaly | A deliberately planted exception or unusual pattern for analytics and audit exercises. |

## Where to Go Next

- Read [company-story.md](company-story.md) for the business narrative.
- Read [process-flows.md](process-flows.md) for O2C, P2P, manufacturing, journals, and ledger traceability.
- Read [database-guide.md](database-guide.md) to learn how to navigate the tables.
