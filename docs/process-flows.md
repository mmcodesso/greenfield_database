---
title: Process Flows
description: Hub for understanding how the main business cycles move through the database and into the ledger.
slug: /process-flows
sidebar_label: Process Flows
---

# Process Flows


## How to Use This Section

Use this page as the hub for the detailed process guides:

| Process area | Detailed guide | What it covers |
|---|---|---|
| Core O2C | [O2C](processes/o2c.md) | Customer order through shipment, invoice, receipt, and cash application |
| Returns and credits | [Returns, Credits, and Refunds](processes/o2c-returns-credits-refunds.md) | Returned goods, credit memos, customer credits, and refunds |
| P2P | [P2P](processes/p2p.md) | Requisition through PO, goods receipt, supplier invoice, and payment |
| Manufacturing | [Manufacturing](processes/manufacturing.md) | BOMs, routings, work centers, work orders, material issues, completions, and work-order close |
| Payroll | [Payroll](processes/payroll.md) | Pay periods, labor time, payroll registers, payments, remittances, and operation-level labor integration |
| Time clocks and shifts | [Time Clocks](processes/time-clocks.md) | Shift definitions, employee assignments, approved time clocks, attendance exceptions, and payroll-hour sourcing |
| Journals and close | [Manual Journals and Close](processes/manual-journals-and-close.md) | Recurring journals, accrued-expense estimates and adjustments, reclasses, and year-end close |

## Greenfield Process Map

```mermaid
flowchart LR
    STORY[Company Operations]
    O2C[Order-to-Cash]
    RET[Returns Credits Refunds]
    P2P[Procure-to-Pay]
    MFG[Manufacturing]
    PAY[Payroll]
    TC[Time Clocks and Shifts]
    JE[Manual Journals and Close]
    GL[GLEntry]
    AN[Analytics and Coursework]

    STORY --> O2C
    STORY --> P2P
    STORY --> MFG
    STORY --> PAY
    STORY --> TC
    O2C --> RET
    P2P --> MFG
    TC --> PAY
    TC --> MFG
    O2C --> GL
    RET --> GL
    P2P --> GL
    MFG --> GL
    PAY --> GL
    JE --> GL
    GL --> AN
```

At Greenfield, students can think of the database as one business with six accounting-relevant threads:

- selling and collecting from customers
- correcting customer-side exceptions through returns and credits
- buying inventory and materials from suppliers
- manufacturing selected finished goods internally
- assigning shifts, recording hourly attendance, paying employees, and tracing labor into product cost
- recording recurring finance activity and year-end close

Each of those threads eventually reaches `GLEntry`.

## Subledger-to-Ledger Traceability

```mermaid
flowchart LR
    SH[Shipment]
    SI[SalesInvoice]
    CRA[CashReceiptApplication]
    SR[SalesReturn]
    CM[CreditMemo]
    RF[CustomerRefund]
    GR[GoodsReceipt]
    PI[PurchaseInvoice]
    DP[DisbursementPayment]
    MI[MaterialIssue]
    PC[ProductionCompletion]
    WC[WorkOrderClose]
    PR[PayrollRegister]
    PP[PayrollPayment]
    RM[PayrollLiabilityRemittance]
    JE[JournalEntry]
    GL[GLEntry]
    R[Reporting and Analytics]

    SH --> GL
    SI --> GL
    CRA --> GL
    SR --> GL
    CM --> GL
    RF --> GL
    GR --> GL
    PI --> GL
    DP --> GL
    MI --> GL
    PC --> GL
    WC --> GL
    PR --> GL
    PP --> GL
    RM --> GL
    JE --> GL
    GL --> R
```

This is the core design idea behind the dataset: many operational tables exist, but posted accounting analysis converges into `GLEntry`.

The most important traceability fields are:

- `VoucherType`
- `VoucherNumber`
- `SourceDocumentType`
- `SourceDocumentID`
- `SourceLineID`
- `FiscalYear`
- `FiscalPeriod`

## Recommended Reading Order

1. Read [Company Story](company-story.md) to understand the business.
2. Read [O2C](processes/o2c.md) and [P2P](processes/p2p.md).
3. Read [Returns, Credits, and Refunds](processes/o2c-returns-credits-refunds.md) for the sales-side exception path.
4. Read [Manufacturing](processes/manufacturing.md) for the production flow.
5. Read [Time Clocks](processes/time-clocks.md) for shift and attendance flow.
6. Read [Payroll](processes/payroll.md) for payroll and labor-cost flow.
7. Read [Manual Journals and Close](processes/manual-journals-and-close.md) for finance-team activity outside the operational cycles.
8. Read [Dataset Guide](dataset-overview.md) once you are ready to navigate tables and joins.

## Where to Go Next

- Read [Dataset Guide](dataset-overview.md) for joins and table families.
- Read [Posting Reference](reference/posting.md) for the technical posting rules.
