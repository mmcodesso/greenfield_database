# Order-to-Cash Process

## What Students Should Learn

- Distinguish the order, shipment, invoice, cash receipt, settlement, and return-correction stages in one customer sale.
- Trace an O2C transaction from operational documents into `GLEntry`.
- Identify the core tables used for revenue, receivables, fulfillment, cash, and customer-side exceptions.
- Recognize timing differences that matter for cut-off, completeness, open-AR, working-capital, and return analysis.

## Business Storyline

In this dataset, the order-to-cash cycle starts when the sales team records customer demand and ends only when that sale is settled in cash. Several teams touch the process along the way. Sales captures the order, warehouse staff ship what is available, accounting bills what actually left the warehouse, treasury records the money when it arrives, and accounting applies that cash against open invoices.

That distinction matters. A customer order is not revenue. A shipment is not the same thing as an invoice. A cash receipt is not the same thing as settlement. Students can see those stages separately in the data and use that separation to answer both accounting and audit questions.

Most sales follow the normal path of order, shipment, invoice, cash, and settlement. Some sales later move into the customer-side exception path of return, credit, and sometimes refund. That exception path is part of O2C, not a separate business cycle.

## Normal Process Overview

```mermaid
flowchart LR
    C[Customer]
    SO[Sales Order]
    SH[Shipment]
    SI[Sales Invoice]
    CR[Cash Receipt]
    CRA[Cash Receipt Application]
    GL[GLEntry]

    C --> SO --> SH --> SI
    C --> CR --> CRA
    SH -. Posts COGS and Inventory .-> GL
    SI -. Posts AR Revenue and Sales Tax .-> GL
    CR -. Posts Cash and Customer Deposits .-> GL
    CRA -. Clears AR from Customer Deposits .-> GL
```

Read the main diagram as promise, fulfillment, billing, cash, and settlement. Orders show demand. Shipments show physical movement. Invoices create receivables and revenue. Cash receipts record the arrival of money. Cash applications show which invoices were actually settled.

## How to Read This Process in the Data

This page is organized around business flow first and data navigation second. The main diagram shows the normal O2C path. The smaller diagrams below show local lineage for one analytical task at a time. The fuller relationship map belongs on [Schema Reference](../reference/schema.md), not on this process page.

:::tip
Use this page to understand the business flow first. Then move into the subsection diagrams and tables when you need the exact trace for one analytical question.
:::

## Core Tables and What They Represent

| Process stage | Main tables | Grain or event represented | Why students use them |
|---|---|---|---|
| Pricing and commercial setup | `PriceList`, `PriceListLine`, `PromotionProgram`, `PriceOverrideApproval` | Pricing rules, promotions, and rare override approvals behind a sales line | Review commercial terms, pricing controls, and margin drivers |
| Order capture | `SalesOrder`, `SalesOrderLine` | Customer order header and ordered line | See promised demand and ordered quantity before fulfillment |
| Fulfillment | `Shipment`, `ShipmentLine` | Physical shipment event and shipped line | Measure what actually left the warehouse and when |
| Billing | `SalesInvoice`, `SalesInvoiceLine` | Invoice header and billed line | Trace receivable creation and billed revenue back to shipment |
| Cash receipt | `CashReceipt` | Cash arrival from the customer | Review collection timing, unapplied cash, and deposit behavior |
| Settlement | `CashReceiptApplication` | Application of received cash to one or more invoices | Measure true invoice settlement and open-AR reduction |

## When Accounting Happens

| Event | Business meaning | Accounting effect |
|---|---|---|
| Shipment | Goods physically leave inventory and customer fulfillment occurs | Debit COGS and credit inventory |
| Sales invoice | Accounting bills shipped quantity and creates the customer receivable | Debit AR and credit revenue plus sales tax payable |
| Cash receipt | Customer money arrives, even if it is not yet matched to a specific invoice | Debit cash and credit customer deposits or unapplied cash |
| Cash application | Accounting settles one or more open invoices with previously received cash | Debit customer deposits or unapplied cash and credit AR |

## Key Traceability and Data Notes

- `SalesInvoiceLine.ShipmentLineID` is the main shipment-to-invoice traceability field in the normal O2C path.
- `CashReceiptApplication` is the true settlement table because it shows which invoices the cash actually cleared.
- `CashReceipt.SalesInvoiceID` is compatibility metadata only and should not be treated as the authoritative settlement link.
- `SalesOrderLine` carries pricing lineage through `BaseListPrice`, `PriceListLineID`, `PromotionID`, `PriceOverrideApprovalID`, and `PricingMethod`.
- Some receipts remain unapplied for a period of time, which is useful for open-AR, unapplied-cash, and settlement-timing analysis.

## Analytical Subsections

### 1. Pricing and Commercial Terms

Before warehouse activity or billing begins, the dataset resolves the commercial terms for the order line. Students should read this step as the pricing decision layer: what was the base price, did a promotion apply, was an override approved, and how did the final pricing method affect margin and pricing-control review. For the full process-level entity relationships, see the [Schema Reference](../reference/schema.md).

```mermaid
flowchart LR
    CTX[Customer and Item Context]
    PL[Price List]
    PROMO[Promotion Program]
    OVR[Price Override Approval]
    SO[Sales Order]

    CTX --> PL --> SO
    CTX --> PROMO --> SO
    CTX --> OVR --> SO
```

**Tables involved**

| Table | Why it matters here |
|---|---|
| `PriceList`, `PriceListLine` | Provide the base commercial price by customer or segment scope |
| `PromotionProgram` | Adds the promotion-based discount when one valid promotion applies |
| `PriceOverrideApproval` | Captures rare below-floor approval support |
| `SalesOrderLine` | Stores the final pricing lineage on the ordered line |

**Starter analytical question:** Which sales lines used standard price-list logic versus promotion pricing versus approved override logic?

```sql
-- Teaching objective: Compare pricing method, promotion use, and override approvals.
-- Main join path: SalesOrderLine -> PriceListLine -> PriceList, plus PromotionProgram and PriceOverrideApproval.
-- Suggested analysis: Group by PricingMethod, customer segment, item group, or sales rep.
```

### 2. Shipment to Invoice Traceability

This view teaches students how billed revenue ties back to physical fulfillment. Treat this as a traceability diagram, not as a full ER diagram. For the full process-level entity relationships, see the [Schema Reference](../reference/schema.md). This subsection is especially useful for cutoff, completeness, and occurrence testing.

```mermaid
flowchart LR
    C[Customer]
    SO[Sales Order]
    SH[Shipment]
    SI[Sales Invoice]
    GL[GLEntry]

    C --> SO -->  SH  --> SI  --> GL
```

**Tables involved**

| Table | Why it matters here |
|---|---|
| `SalesOrder`, `SalesOrderLine` | Show the original customer promise and ordered quantity |
| `Shipment`, `ShipmentLine` | Show what actually shipped and when it shipped |
| `SalesInvoice`, `SalesInvoiceLine` | Show what was billed from the shipped quantity |
| `GLEntry` | Shows the posted receivable and revenue effect |

**Key joins**

- `ShipmentLine.SalesOrderLineID -> SalesOrderLine.SalesOrderLineID`
- `SalesInvoiceLine.ShipmentLineID -> ShipmentLine.ShipmentLineID`
- `GLEntry.SourceDocumentType` plus `SourceDocumentID` or `SourceLineID` for posting trace

```sql
-- Teaching objective: Trace billed revenue back to the shipped line that supported it.
-- Main join path: SalesOrderLine -> ShipmentLine -> SalesInvoiceLine.
-- Suggested analysis: Filter invoice and shipment dates by month-end to test cutoff timing.
```

### 3. Cash Receipt, Application, and Settlement

This is the section students often need most. The cash receipt is the cash event. The cash application is the settlement event. Those are related, but they are not the same accounting moment. This distinction drives open-AR analysis, unapplied-cash review, and receivables testing.

```mermaid
flowchart LR
    CR[Cash Receipt]
    DEP[Customer Deposits and Unapplied Cash]
    CRA[Cash Receipt Application]
    SI[Sales Invoice]
    GL[GLEntry]

    CR --> DEP --> CRA --> SI --> GL
```

**Tables involved**

| Table | Why it matters here |
|---|---|
| `CashReceipt` | Records when customer cash arrived |
| `CashReceiptApplication` | Records which invoices were actually settled |
| `SalesInvoice` | Provides the receivable being cleared |
| `GLEntry` | Shows cash, liability, and AR-clearing effects |

:::warning
Do not use `CashReceipt.SalesInvoiceID` as the main settlement link. The authoritative settlement path is `CashReceiptApplication`, because one receipt can settle multiple invoices and some cash can remain unapplied temporarily.
:::

```sql
-- Teaching objective: Separate cash arrival from invoice settlement.
-- Main join path: CashReceipt -> CashReceiptApplication -> SalesInvoice.
-- Suggested analysis: Compare receipt date, application date, and invoice due date for open-AR review.
```

### 4. Backorder to Shipment Lag

Not every order ships immediately. This subsection helps students see why order date, shipment date, and invoice date can diverge when inventory is short. It is useful for fulfillment-lag analysis, billing-lag review, and period timing differences around month-end.

```mermaid
flowchart LR
    SOL[Sales Order]
    FG[Available Finished Goods]
    BO[Backordered Quantity]
    SHL[Later Shipment]
    SIL[Later Sales Invoice]

    SOL --> FG
    FG -->|Enough stock| SHL --> SIL
    FG -->|Short stock| BO --> SHL
```

**Tables involved**

| Table | Why it matters here |
|---|---|
| `SalesOrderLine` | Shows the original promised quantity |
| `ShipmentLine` | Shows what quantity left inventory and when |
| `SalesInvoiceLine` | Shows when the delayed shipment was billed |

**Starter analytical question:** Which customers or item groups show the longest lag between order capture, shipment, and billing?

```sql
-- Teaching objective: Measure fulfillment lag from ordered quantity to shipped quantity and billed quantity.
-- Main join path: SalesOrderLine -> ShipmentLine -> SalesInvoiceLine.
-- Suggested analysis: Compare order date, shipment date, and invoice date by customer, item group, or month.
```

## Returns, Credits, and Refunds

Some sales do not end with the original invoice. In this dataset, returns are the main customer-side exception path inside O2C, not a separate business cycle. The exception starts from something that was already shipped and billed, then moves through physical return, financial correction, and sometimes cash refund if the customer had already paid.

```mermaid
flowchart LR
    SHL[Shipment]
    SIL[Sales Invoice]
    SR[Sales Return]
    SRL[Sales Return]
    CM[Credit Memo]
    RF[CustomerRefund]
    GL[GLEntry]

    SHL --> SIL --> SR --> SRL --> CM --> RF
    SR -. Restores Inventory and Reverses COGS .-> GL
    CM -. Posts Contra Revenue Tax Reversal and AR or Customer Credit .-> GL
    RF -. Clears Customer Credit and Cash .-> GL
```

| Exception stage | Main tables | Why students use them |
|---|---|---|
| Original billed shipment | `ShipmentLine`, `SalesInvoiceLine` | Identify the shipment and invoice that the correction started from |
| Physical return | `SalesReturn`, `SalesReturnLine` | Show returned quantity and the operational return event |
| Financial correction | `CreditMemo`, `CreditMemoLine` | Show the customer-facing credit and whether it reduced AR or created customer credit |
| Cash resolution | `CustomerRefund` | Show when customer credit was returned in cash |

| Event | Business meaning | Accounting effect |
|---|---|---|
| Sales return | Goods come back after a shipment and invoice already existed | Debit inventory and credit COGS |
| Credit memo | Accounting reverses part of the original sale | Debit sales returns and allowances plus tax reversal, and credit AR or customer credit |
| Customer refund | Treasury clears customer credit in cash | Debit customer credit and credit cash |

**Traceability notes**

- `SalesReturnLine.ShipmentLineID` is the core operational return trace field.
- `CreditMemo.OriginalSalesInvoiceID` ties the financial correction back to the earlier invoice.
- `CreditMemoLine` preserves the original pricing lineage through `BaseListPrice`, `PriceListLineID`, `PromotionID`, `PriceOverrideApprovalID`, `PricingMethod`, and `Discount`.
- `CustomerRefund` is used only when the return scenario leaves customer credit that is later cleared in cash.

```mermaid
flowchart LR
    INV[Original Sales Invoice]
    RET[Sales Return]
    CM[Credit Memo]
    CC[Customer Credit]
    RF[Customer Refund]

    INV --> RET --> CM
    CM -->|Invoice still open| INV
    CM -->|Invoice already paid| CC --> RF
```

This local lineage view separates two outcomes that students often mix together. A credit memo can reduce open AR when the original invoice is still unsettled, or it can create customer credit that treasury later clears through `CustomerRefund`.

## Common Student Questions

- Which orders shipped immediately and which became backorders?
- Which shipment lines were invoiced later than the shipment date?
- Which invoices remain open after cash applications?
- Which customers pay one invoice at a time versus several at once?
- Which pricing methods appear most often by customer segment or item family?
- Which shipment lines were later returned?
- Which returns reduced open AR versus created customer credit?
- How do revenue, receivables, unapplied cash, collections timing, and return corrections differ by period?

## Where to Go Next

- Jump to [Returns, Credits, and Refunds](#returns-credits-and-refunds) when you want the main O2C exception path.
- Read [Dataset Guide](../start-here/dataset-overview.md) for the main joins used in analysis.
- Read [GLEntry Posting Reference](../reference/posting.md) when you want the detailed posting rules.
- Read [Schema Reference for full table relationships](../reference/schema.md) when you need the broader process-level table map.
