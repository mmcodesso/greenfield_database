# Procure-to-Pay Process

## What Students Should Learn

- Distinguish planning support, requisition, purchase order, receipt, supplier invoice, and payment as separate P2P stages.
- Trace a purchased item or expense from operational documents into `GLEntry`.
- Identify the core tables used for three-way match, open AP, and planning-supported replenishment analysis.
- Recognize the control difference between receipt-matched inventory invoicing and direct accrued-service settlement.

## Business Storyline

The company does not buy inventory or services at random. A department or planning signal identifies a need, purchasing turns that need into supplier orders, warehouse staff receive the goods when they arrive, accounts payable records the supplier invoice, and treasury pays it when approved. Some purchasing demand is routine replenishment, and some supports manufacturing's need for raw materials and packaging.

That distinction matters. A requisition is not the same thing as a purchase order. A receipt is not the same thing as a supplier invoice. A supplier invoice is not the same thing as payment. Students can see each stage separately in the data and use that separation to answer both accounting and audit questions.

Most P2P activity follows the normal inventory and materials path: plan, requisition, order, receive, invoice, pay. A secondary AP path also exists for certain operating expenses. Finance may estimate the expense first through an accrual, then AP later clears that estimate through a direct service invoice that has no goods receipt behind it.

## Normal Process Overview

```mermaid
flowchart LR
    PLAN[Planning Support]
    PR[PurchaseRequisition]
    PO[PurchaseOrder]
    POL[PurchaseOrderLine]
    GR[GoodsReceipt]
    GRL[GoodsReceiptLine]
    PI[PurchaseInvoice]
    PIL[PurchaseInvoiceLine]
    DP[DisbursementPayment]
    GL[GLEntry]

    PLAN --> PR --> PO --> POL --> GR --> GRL --> PI --> PIL --> DP
    GR -. Posts Inventory and GRNI .-> GL
    PI -. Clears GRNI and records AP .-> GL
    DP -. Clears AP and Cash .-> GL
```

Read the main diagram as planning support, internal demand, supplier commitment, physical receipt, supplier billing, and payment. Requisitions and purchase orders are operational commitments; receiving, invoicing, and payment are the stages that reach the ledger.

## How to Read This Process in the Data

This page is organized around business flow first and data navigation second. The main diagram shows the normal inventory and materials path. The smaller diagrams below show one analytical task at a time, such as planning support, PO-to-receipt traceability, three-way match, or payment timing. The fuller relationship map belongs on [Schema Reference](../reference/schema.md), not on this process page.

:::tip
Use this page to separate the operational chain from the accounting chain. Start with why the purchase was needed, then move into supplier commitment, receiving, invoicing, and payment.
:::

## Core Tables and What They Represent

| Process stage | Main tables | Grain or event represented | Why students use them |
|---|---|---|---|
| Planning support | `DemandForecast`, `InventoryPolicy`, `SupplyPlanRecommendation` | Weekly planning signal behind normal purchased replenishment | Explain why purchased demand existed before requisitions were created |
| Internal demand | `PurchaseRequisition` | One internal request for an item, quantity, and cost center | Trace who requested the item and why |
| Supplier commitment | `PurchaseOrder`, `PurchaseOrderLine` | Supplier order header and ordered line | Review ordering, batching, and supplier commitment |
| Physical receipt | `GoodsReceipt`, `GoodsReceiptLine` | What physically arrived and when it arrived | Measure receipt timing, partial receipts, and inventory posting support |
| Supplier billing | `PurchaseInvoice`, `PurchaseInvoiceLine` | What the supplier billed and whether the line matched a receipt or accrual | Review three-way match, AP creation, and accrued-service settlement |
| Payment | `DisbursementPayment` | AP settlement event | Analyze payment timing and open payable behavior |

## When Accounting Happens

| Event | Business meaning | Accounting effect |
|---|---|---|
| Goods receipt | Goods physically arrive and inventory is recognized before the supplier bill is posted | Debit inventory and credit `2020` GRNI |
| Purchase invoice | AP records the supplier bill | For receipt-matched inventory lines: clear GRNI, record any purchase variance, and credit AP. For accrued-service lines: clear `2040` up to the estimate, book any excess to expense, and credit AP |
| Disbursement payment | Treasury or AP settles the supplier liability | Debit AP and credit cash |

## Key Traceability and Data Notes

- `PurchaseRequisition.SupplyPlanRecommendationID` is the authoritative planning-support link for normal replenishment demand.
- `PurchaseOrderLine.RequisitionID` is the authoritative requisition link when one purchase order batches several requisitions.
- `GoodsReceiptLine.POLineID` is the operational bridge from ordered line to received line.
- `PurchaseInvoiceLine.GoodsReceiptLineID` is the authoritative receipt-match link for inventory and material invoicing.
- `PurchaseInvoiceLine.AccrualJournalEntryID` is the authoritative link for direct accrued-service settlement.
- P2P is multi-period in the current generator. Receipt, invoicing, and payment do not need to occur in the same month.

## Analytical Subsections

### Planning Support and Requisition Creation

The normal replenishment path starts before purchasing talks to a supplier. Weekly forecast, policy, and projected availability create `SupplyPlanRecommendation` rows, and those recommendations become the main support for new requisitions. Students should read this as the “why did we need to buy this?” layer.

```mermaid
flowchart LR
    DF[DemandForecast]
    IP[InventoryPolicy]
    SPR[SupplyPlanRecommendation]
    PR[PurchaseRequisition]

    DF --> SPR
    IP --> SPR --> PR
```

**Tables involved**

| Table | Why it matters here |
|---|---|
| `DemandForecast` | Shows the expected demand pattern behind planned replenishment |
| `InventoryPolicy` | Shows safety stock, reorder logic, and lead-time assumptions |
| `SupplyPlanRecommendation` | Shows the planned purchase signal by week, item, and warehouse |
| `PurchaseRequisition` | Shows the internal demand that purchasing converts into supplier orders |

**Starter analytical question:** Which purchase requisitions were clearly supported by weekly planning versus created as residual execution demand?

```sql
-- Teaching objective: Trace purchased demand from planning support into requisition creation.
-- Main join path: SupplyPlanRecommendation -> PurchaseRequisition, with DemandForecast and InventoryPolicy for planning context.
-- Suggested analysis: Group by item group, warehouse, planner, or driver type.
```

### Purchase Order to Receipt Traceability

This subsection teaches the operational supplier path. Students should use it to trace how internal demand turns into a supplier order and then into one or more physical receipts. It is especially useful for partial receipt review, receiving lag analysis, and supplier-delivery questions.

```mermaid
flowchart LR
    PR[PurchaseRequisition]
    PO[PurchaseOrder]
    POL[PurchaseOrderLine]
    GR[GoodsReceipt]
    GRL[GoodsReceiptLine]

    PR --> PO --> POL --> GR --> GRL
```

**Tables involved**

| Table | Why it matters here |
|---|---|
| `PurchaseRequisition` | Shows the original internal demand |
| `PurchaseOrder`, `PurchaseOrderLine` | Show the supplier commitment and ordered line detail |
| `GoodsReceipt`, `GoodsReceiptLine` | Show what physically arrived and when it arrived |

**Key joins**

- `PurchaseOrderLine.RequisitionID -> PurchaseRequisition.RequisitionID`
- `GoodsReceiptLine.POLineID -> PurchaseOrderLine.POLineID`
- `GoodsReceiptLine.GoodsReceiptID -> GoodsReceipt.GoodsReceiptID`

```sql
-- Teaching objective: Trace supplier orders into one or more physical receipts.
-- Main join path: PurchaseRequisition -> PurchaseOrderLine -> GoodsReceiptLine.
-- Suggested analysis: Compare requisition date, order date, expected delivery date, and receipt date by supplier or item group.
```

### Receipt to Supplier Invoice Matching

This is the three-way-match teaching path. Students should use it to see how a supplier invoice ties back to a specific receipt line when the purchase follows the normal inventory or materials route.

```mermaid
flowchart LR
    GRL[GoodsReceiptLine]
    PI[PurchaseInvoice]
    PIL[PurchaseInvoiceLine]
    GL[GLEntry]

    GRL --> PIL --> PI --> GL
```

**Tables involved**

| Table | Why it matters here |
|---|---|
| `GoodsReceiptLine` | Provides the receipt-match basis for inventory invoicing |
| `PurchaseInvoice`, `PurchaseInvoiceLine` | Show the supplier bill and matched billed line |
| `GLEntry` | Shows the posted AP and GRNI-clearing effect |

**Starter analytical question:** Which supplier invoice lines matched receipts cleanly, and which receipt lines remained uninvoiced at period end?

```sql
-- Teaching objective: Trace receipt-based invoicing through the three-way-match path.
-- Main join path: GoodsReceiptLine -> PurchaseInvoiceLine -> PurchaseInvoice.
-- Suggested analysis: Compare receipt date and invoice date by supplier, item, or month-end.
```

### Supplier Payment and Open AP

This is the settlement view of P2P. Supplier invoices create AP, but payment can happen later and not necessarily in the same period. Students should use this section to analyze payment timing, open AP, and working-capital behavior.

```mermaid
flowchart LR
    PI[PurchaseInvoice]
    AP[Accounts Payable]
    DP[DisbursementPayment]
    GL[GLEntry]

    PI --> AP --> DP --> GL
```

**Tables involved**

| Table | Why it matters here |
|---|---|
| `PurchaseInvoice` | Creates the payable and anchors due-date analysis |
| `DisbursementPayment` | Shows how and when the invoice was settled |
| `GLEntry` | Shows the posted AP and cash effect |

**Starter analytical question:** Which supplier invoices remained unpaid after due date, and how does payment lag vary by supplier or item group?

```sql
-- Teaching objective: Separate supplier invoicing from supplier payment.
-- Main join path: PurchaseInvoice -> DisbursementPayment, with GLEntry for posted effect.
-- Suggested analysis: Compare invoice date, due date, and payment date by supplier or spend type.
```

## Accruals and Direct Service Settlement

This is a valid AP path, but it is not the same control path as receipt-matched inventory invoicing. In this branch, finance estimates an operating expense first through an accrual. AP later clears that estimate through a direct supplier service invoice that intentionally has no goods receipt behind it.

```mermaid
flowchart LR
    AC[JournalEntry Accrual]
    PIL[PurchaseInvoiceLine with AccrualJournalEntryID]
    PI[PurchaseInvoice]
    DP[DisbursementPayment]
    GL[GLEntry]

    AC --> PIL --> PI --> DP --> GL
```

| Exception stage | Main tables | Why students use them |
|---|---|---|
| Initial estimate | `JournalEntry` | Shows the original accrued expense estimate |
| Service settlement line | `PurchaseInvoiceLine` | Shows the invoice line that clears the prior accrual instead of matching a receipt |
| Supplier invoice | `PurchaseInvoice` | Shows the AP document created from the direct service bill |
| Payment | `DisbursementPayment` | Shows when the service invoice was settled in cash |

| Event | Business meaning | Accounting effect |
|---|---|---|
| Accrual journal | Finance estimates an expense before the supplier bill arrives | Debit expense and credit `2040` accrued expenses |
| Direct service invoice | AP records the bill and clears the prior estimate | Debit `2040` up to the estimate, expense any excess, and credit AP |
| Disbursement payment | Treasury clears the supplier payable | Debit AP and credit cash |

**Traceability notes**

- `PurchaseInvoiceLine.GoodsReceiptLineID` is the authoritative link for receipt-matched inventory and material invoicing.
- `PurchaseInvoiceLine.AccrualJournalEntryID` is the authoritative link for direct accrued-service settlement.
- `PurchaseOrderLine.RequisitionID` remains the authoritative requisition link when purchase orders batch several demand lines.

```mermaid
flowchart LR
    GRL[Receipt-Matched GoodsReceiptLine]
    PIL1[PurchaseInvoiceLine with GoodsReceiptLineID]
    AC[Accrual JournalEntry]
    PIL2[PurchaseInvoiceLine with AccrualJournalEntryID]
    PI[PurchaseInvoice]
    DP[DisbursementPayment]

    GRL --> PIL1 --> PI --> DP
    AC --> PIL2 --> PI
```

This local lineage view separates the two main AP control paths. One path depends on a physical receipt. The other depends on a prior accrual estimate.

## Common Student Questions

- Which requisitions were converted from planning-supported demand?
- Which requisitions were grouped into the same purchase order?
- Which PO lines were only partially received or invoiced?
- Which supplier invoice lines matched receipt lines cleanly?
- Which invoices remained unpaid after due date?
- Which AP lines cleared a prior accrual instead of matching a receipt?
- How do receiving, invoicing, and payment timing differ by supplier, item group, or cost center?

## Where to Go Next

- Jump to [Accruals and Direct Service Settlement](#accruals-and-direct-service-settlement) when you want the secondary AP control path.
- Read [Manufacturing](manufacturing.md) to see how purchasing supports work orders and material availability.
- Read [Dataset Guide](../start-here/dataset-overview.md) for navigation patterns and join paths.
- Read [GLEntry Posting Reference](../reference/posting.md) for the detailed posting rules behind receipts, supplier invoices, and payments.
- Read [Schema Reference for full table relationships](../reference/schema.md) when you need the broader process-level table map.
