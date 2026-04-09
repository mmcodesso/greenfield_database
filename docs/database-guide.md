# Database Guide

**Audience:** Students, instructors, and analysts who want to navigate the tables without starting from code.  
**Purpose:** Explain how the database is organized and how to move from operational data to accounting data.  
**What you will learn:** Table families, key joins, header-line patterns, and where to begin for different analytics topics.

## How the Database Is Organized

The current implementation contains 31 tables grouped into five areas:

| Area | Tables |
|---|---|
| Accounting core | `Account`, `JournalEntry`, `GLEntry` |
| O2C | `Customer`, `SalesOrder`, `SalesOrderLine`, `Shipment`, `ShipmentLine`, `SalesInvoice`, `SalesInvoiceLine`, `CashReceipt`, `CashReceiptApplication`, `SalesReturn`, `SalesReturnLine`, `CreditMemo`, `CreditMemoLine`, `CustomerRefund` |
| P2P | `Supplier`, `PurchaseRequisition`, `PurchaseOrder`, `PurchaseOrderLine`, `GoodsReceipt`, `GoodsReceiptLine`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `DisbursementPayment` |
| Master data | `Item`, `Warehouse`, `Employee` |
| Organizational planning | `CostCenter`, `Budget` |

If you are new to the dataset, the easiest reading order is:

1. [company-story.md](company-story.md)
2. [process-flows.md](process-flows.md)
3. this guide

## Header-Line Pattern

Many business documents use a header table and a line table.

| Header table | Line table | Meaning |
|---|---|---|
| `SalesOrder` | `SalesOrderLine` | One customer order can contain many item lines |
| `Shipment` | `ShipmentLine` | One shipment can contain many shipped lines |
| `SalesInvoice` | `SalesInvoiceLine` | One invoice can contain many billed lines |
| `PurchaseOrder` | `PurchaseOrderLine` | One PO can contain many ordered lines |
| `GoodsReceipt` | `GoodsReceiptLine` | One receipt can contain many received lines |
| `PurchaseInvoice` | `PurchaseInvoiceLine` | One supplier invoice can contain many billed lines |

If you are new to the database, start from the header table to understand the document, then use the line table to analyze quantities, prices, and amounts.

## Most Important Keys

| Key | Use |
|---|---|
| `CustomerID` | Connect customers to orders, invoices, receipts, returns, credit memos, and refunds |
| `SupplierID` | Connect suppliers to purchase orders, invoices, and payments |
| `RequisitionID` | Connect requisitions to purchase-order headers and purchase-order lines |
| `SalesOrderID` | Connect sales order header to shipments and invoices |
| `SalesOrderLineID` | Connect order lines to shipment lines and sales invoice lines |
| `ShipmentLineID` | Connect billed and returned lines to the exact shipped line |
| `PurchaseOrderID` | Connect purchase order header to goods receipts and purchase invoices |
| `POLineID` | Connect purchase order lines to goods receipt lines and purchase invoice lines |
| `GoodsReceiptLineID` | Connect purchase invoice lines to specific receipt lines in the clean Phase 9 match design |
| `ItemID` | Analyze quantities, prices, standard costs, and item account mappings |
| `AccountID` | Connect `GLEntry` and `Budget` to the chart of accounts |
| `CostCenterID` | Connect operational activity, employees, and budgets to organizational reporting |

## Core Navigation Paths

### O2C path

`Customer -> SalesOrder -> SalesOrderLine -> Shipment -> ShipmentLine -> SalesInvoice -> SalesInvoiceLine`

Cash collection is tracked through:

`CashReceipt -> CashReceiptApplication -> SalesInvoice`

Returns, credits, and refunds branch from the billed shipment path:

`SalesInvoiceLine -> SalesReturn -> SalesReturnLine -> CreditMemo -> CreditMemoLine -> CustomerRefund`

Use this path when studying revenue, fulfillment, billing, collections, customer behavior, or receivables.

### P2P path

`Supplier -> PurchaseRequisition -> PurchaseOrder -> PurchaseOrderLine -> GoodsReceipt -> GoodsReceiptLine -> PurchaseInvoice -> PurchaseInvoiceLine -> DisbursementPayment`

Use this path when studying approvals, PO batching, receiving, invoice matching, payables, and cash disbursements.

### Ledger path

`GLEntry -> Account`

Then use the source-trace fields on `GLEntry` to move back to the originating document:

- `SourceDocumentType`
- `SourceDocumentID`
- `SourceLineID`
- `VoucherType`
- `VoucherNumber`

## How to Move From Operations to Accounting

Not every operational document posts to the general ledger.

| Document family | Posts to GL? | Notes |
|---|---|---|
| Sales orders | No | Operational demand document |
| Purchase requisitions | No | Internal approval document |
| Purchase orders | No | External commitment document |
| Shipments | Yes | Posts COGS and inventory relief |
| Sales invoices | Yes | Posts AR, revenue, and sales tax |
| Cash receipts | Yes | Posts cash and customer deposits / unapplied cash |
| Cash receipt applications | Yes | Clears AR from customer deposits / unapplied cash |
| Sales returns | Yes | Posts inventory back in and reverses COGS |
| Credit memos | Yes | Posts contra revenue, tax reversal, and AR or customer credit reduction |
| Customer refunds | Yes | Posts customer credit and cash |
| Goods receipts | Yes | Posts inventory and GRNI using receipt-line posting basis |
| Purchase invoices | Yes | Posts GRNI clearing, AP, and purchase variance using matched receipt-line linkage when available |
| Disbursements | Yes | Posts AP and cash |
| Journal entries | Yes | Current implementation includes opening, recurring manual, reversal, and year-end close journals |

## Start Here by Analytics Topic

### Financial analytics

Start with:

- `GLEntry`
- `Account`
- `SalesInvoice`
- `CashReceiptApplication`
- `CreditMemo`
- `CustomerRefund`
- `PurchaseInvoice`
- `DisbursementPayment`

Typical questions:

- What are revenue, COGS, and gross margin by month?
- What remains open in AR and AP?
- How much customer cash is unapplied or held as credit?
- Does the subledger reconcile to the control accounts?

### Managerial analytics

Start with:

- `Budget`
- `CostCenter`
- `Item`
- `SalesOrderLine`
- `ShipmentLine`
- `GoodsReceiptLine`
- `PurchaseOrderLine`
- `PurchaseInvoiceLine`

Typical questions:

- How do budget and actual activity compare by cost center?
- Which products or regions drive sales?
- Which items move most through the warehouses?
- Which suppliers and categories drive purchasing activity?

### Audit analytics

Start with:

- `SalesOrder`, `Shipment`, `SalesInvoice`, `CashReceipt`, `CashReceiptApplication`, `SalesReturn`, `CreditMemo`
- `PurchaseRequisition`, `PurchaseOrder`, `GoodsReceipt`, `PurchaseInvoice`, `DisbursementPayment`
- `GLEntry`
- output files such as `validation_report.json` and the anomaly log in Excel

Typical questions:

- Are document chains complete?
- Are there approval exceptions?
- Are there timing, duplicate-reference, or segregation-of-duties issues?
- Do the control accounts reconcile to the subledger logic?

## Current Practical Tips

- The SQLite export is the easiest format for SQL work.
- The starter SQL files under `queries/` are the fastest way to move from schema understanding to analysis.
- The Excel export places each table on its own worksheet and also includes `AnomalyLog` and `ValidationSummary`.
- `CashReceiptApplication` is the authoritative invoice-settlement link in O2C.
- `JournalEntry` supports journal-entry testing, accrual reversal analysis, and close-cycle exercises in the current base dataset.
- For P2P traceability, prefer `PurchaseOrderLine.RequisitionID` and `PurchaseInvoiceLine.GoodsReceiptLineID` over header-only assumptions.
- For raw multi-year income statement analysis, exclude the two year-end close entry types.

## Where to Go Next

- Read [process-flows.md](process-flows.md) for the business meaning of each document chain.
- Read [analytics/index.md](analytics/index.md) for the starter analytics layer.
- Read [reference/schema.md](reference/schema.md) for the technical schema reference.
