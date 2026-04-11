# Order-to-Cash Process

## Business Storyline

A customer places an order with Greenfield. Sales records the demand. Warehouse operations ship the goods when inventory is available. Those finished goods may come from purchased inventory or from Greenfield's own production completions. Accounting bills the customer from the shipped lines, not from the original order alone. Treasury records the cash receipt, and accounting applies that cash to one or more invoices.

That means students can see the difference between:

- demand
- fulfillment
- billing
- cash collection

In the clean base dataset, most invoices stop there. Returns are documented separately because they are intentionally modeled as a minority exception path rather than a normal outcome on most sales.

## Process Diagram

```mermaid
flowchart LR
    C[Customer]
    SO[SalesOrder]
    SOL[SalesOrderLine]
    SH[Shipment]
    SHL[ShipmentLine]
    SI[SalesInvoice]
    SIL[SalesInvoiceLine]
    CR[CashReceipt]
    CRA[CashReceiptApplication]
    GL[GLEntry]

    C --> SO --> SOL --> SH --> SHL --> SI --> SIL
    C --> CR --> CRA
    SH -. Posts COGS and Inventory .-> GL
    SI -. Posts AR Revenue and Sales Tax .-> GL
    CR -. Posts Cash and Customer Deposits .-> GL
    CRA -. Clears AR from Customer Deposits .-> GL
```

The diagram shows the basic revenue cycle. Orders do not post to the GL. Shipping, billing, cash movement, and receipt application do.

## Step-by-Step Walkthrough

1. A customer places an order, which creates `SalesOrder` and `SalesOrderLine`.
2. The warehouse tries to fulfill the order from available stock. If stock is short, some quantity stays open or backordered.
3. A shipment is recorded in `Shipment` and `ShipmentLine`.
4. Accounting creates a `SalesInvoice` from the shipped lines. The invoice lines point back to the exact `ShipmentLineID`.
5. Treasury records a `CashReceipt` when money arrives from the customer.
6. Accounting uses `CashReceiptApplication` to apply that receipt against one or more open invoices.
7. Posted activity lands in `GLEntry`, where students can analyze revenue, receivables, and cash timing.

## Main Tables in This Process

| Business step | Main tables | Why they matter |
|---|---|---|
| Order capture | `SalesOrder`, `SalesOrderLine` | Show customer demand and requested items |
| Fulfillment | `Shipment`, `ShipmentLine` | Show what actually shipped and when |
| Billing | `SalesInvoice`, `SalesInvoiceLine` | Show what was billed from the shipped lines |
| Cash movement | `CashReceipt` | Shows when customer money arrived |
| Cash settlement | `CashReceiptApplication` | Shows which invoices the cash actually settled |

## When Accounting Happens

| Event | Accounting effect |
|---|---|
| Shipment | Debit COGS, credit inventory |
| Sales invoice | Debit AR, credit revenue and sales tax payable |
| Cash receipt | Debit cash, credit customer deposits and unapplied cash |
| Cash receipt application | Debit customer deposits and unapplied cash, credit AR |

## Common Student Questions

- Which orders shipped immediately and which became backorders?
- Which shipment lines were billed later than shipment date?
- Which invoices remain open after cash applications?
- Which customers pay one invoice at a time versus several at once?
- How do revenue, receivables, and cash collection timing differ by period?

## Current Implementation Notes

- `SalesInvoiceLine.ShipmentLineID` is the core shipment-to-invoice traceability field.
- `CashReceiptApplication` is the authoritative settlement table in O2C.
- `CashReceipt.SalesInvoiceID` is compatibility metadata only and should not be treated as the main settlement link.
- Some receipts remain temporarily unapplied, which supports customer-deposit and cash-application analysis.

## Subprocess Spotlight: Cash Application and Customer Deposits

```mermaid
flowchart LR
    CR[CashReceipt]
    DEP[Customer Deposits and Unapplied Cash]
    CRA[CashReceiptApplication]
    INV[SalesInvoice]
    GL[GLEntry]

    CR --> DEP --> CRA --> INV
    CR -. Cash receipt posts cash and deposit liability .-> GL
    CRA -. Application clears deposit liability into AR settlement .-> GL
```

The key teaching idea is that customer money can arrive before accounting applies it to one or more invoices. That makes `CashReceipt` a cash event and `CashReceiptApplication` the true settlement event.

## Subprocess Spotlight: Backorder to Shipment Lag

```mermaid
flowchart LR
    SO[SalesOrderLine]
    AV[Available Inventory]
    BO[Backordered Quantity]
    SH[Later ShipmentLine]
    SI[Later SalesInvoiceLine]

    SO --> AV
    AV -->|Enough stock| SH --> SI
    AV -->|Short stock| BO --> SH
```

This mini-flow helps students see why order date, shipment date, and invoice date do not always match. Inventory availability drives fulfillment timing, and later shipments create later billing.

## Where to Go Next

- Read [Returns, Credits, and Refunds](o2c-returns-credits-refunds.md) for the return and refund path.
- Read [Dataset Guide](../dataset-overview.md) for the main joins used in analysis.
