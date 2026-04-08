# Roadmap

**Audience:** Maintainers, contributors, and instructors tracking planned expansion of the dataset.  
**Purpose:** Define the next implementation phase in concrete terms and capture the remaining roadmap in execution order.  
**What you will learn:** What should be built next, why it is next, and how the later phases fit together.

## Current Status

The current generator already delivers:

- five fiscal years of data from 2026 through 2030
- order-to-cash and procure-to-pay transaction generation
- opening balances, recurring manual journals, year-end close, and budgets
- event-based postings into `GLEntry`
- validations, anomaly injection, and exports

Phase 9 is now complete. The default build includes:

- 1,442 journal headers across opening, recurring operating journals, reversals, and year-end close
- 176,643 GL rows in the default five-year build
- journal-focused anomaly patterns that preserve overall GL balance while creating detectable control exceptions
- multi-period P2P activity with 5,548 purchase-order lines, 9,163 goods-receipt lines, 12,658 purchase-invoice lines, and 13,904 disbursement records

The next practical gap is no longer basic P2P document realism. The next high-value addition is teaching support on top of the existing dataset.

## Recently Delivered: Phase 8 - Manual Journals and Close Cycle

Phase 8 delivered:

- monthly payroll accruals by cost center
- monthly payroll settlements
- monthly office and warehouse rent journals
- monthly utilities journals
- monthly depreciation journals by asset class
- month-end accrued expense journals with linked reversals
- year-end close journals for every fiscal year in range
- journal-specific validation and anomaly coverage

This phase moved `JournalEntry` into its intended teaching scale without adding a new schema table.

## Recently Delivered: Phase 9 - P2P Realism Expansion

Phase 9 delivered:

- batched requisition-to-PO conversion
- line-level requisition linkage on `PurchaseOrderLine.RequisitionID`
- open-line receipt processing with partial receipts across periods
- receipt-line invoice matching through `PurchaseInvoiceLine.GoodsReceiptLineID`
- split disbursement settlement and invoice status progression
- matched GRNI clearing and stricter P2P clean-build validation
- richer monthly generation logging for open P2P balances and throughput

This phase materially improved three-way-match realism and pushed several P2P tables into or near their original design-intent scale.

## Next Phase: Phase 10 - Analytics Starter Layer

### Why this is next

The data generator is now broad enough for teaching, but the repository still relies on instructors and students to invent their own starting queries and workflows. The next highest-value step is to turn the dataset into a more usable teaching package.

### Goal

Add starter assets that help instructors and students begin using the dataset immediately in SQL and Excel without reading the code first.

### In Scope

- starter SQL query sets by topic
- starter Excel analysis paths and workbook guidance
- optional reusable SQLite views for common teaching questions
- example workflows for financial, managerial, and audit analytics
- documentation updates that connect the starter assets to the existing guides

### Implementation Areas

- `docs/`
- optional `queries/` or `examples/` directory
- optional SQLite view support if kept simple and documented
- `README.md` and instructor-facing docs

### Acceptance Criteria

- first-time users can run the generator and find working starter exercises immediately
- starter materials cover financial, managerial, and audit analytics
- examples are aligned to the current schema and row volumes
- documentation is updated to point users to the new starter assets

## Remaining Roadmap

### Phase 11 - O2C and Inventory Enrichment

Focus areas:

- more partial-shipment behavior
- richer late-delivery and backorder patterns
- improved collection behavior and payment timing
- optional returns or credit-memo flow
- stronger inventory availability logic

Why it matters:

- deepens revenue-cycle analytics
- improves fulfillment and cut-off exercises
- creates more realistic inventory movement behavior

### Phase 12 - Manufacturing Foundation

Focus areas:

- manufacturing-related master and transaction tables
- production activity generation
- WIP, completion, and variance postings
- manufacturing-specific validations
- process-flow and documentation updates for the new cycle

Why it matters:

- expands the dataset from distributor/light assembler framing into true manufacturing coverage
- opens the door to cost accounting and production analytics

## Recommended Sequence

1. Phase 10 - Analytics Starter Layer
2. Phase 11 - O2C and Inventory Enrichment
3. Phase 12 - Manufacturing Foundation

This order adds the most teaching value first, improves current realism before major schema expansion, and prepares the project for manufacturing later without forcing a large redesign too early.
