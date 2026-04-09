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

Phase 11 is now complete. The default build includes:

- recurring journals, reversals, and year-end close activity at useful teaching scale
- inventory-constrained O2C shipments, receipt applications, customer deposits, sales returns, credit memos, and customer refunds
- multi-period P2P activity with batched purchase orders, matched supplier invoices, and split settlement behavior
- a starter analytics layer with topic guides, starter SQL packs, Excel workflow guidance, and expanded instructor-facing teaching structure
- validation outputs, anomaly logging, and release-ready exports

The next practical gap is no longer starter usability or O2C realism. The next high-value addition is manufacturing coverage.

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

## Recently Delivered: Phase 10 - Analytics Starter Layer

Phase 10 delivered:

- analytics documentation under `docs/analytics/`
- starter SQL packs under `queries/financial/`, `queries/managerial/`, and `queries/audit/`
- Excel workflow guidance for the generated workbook
- expanded instructor-facing teaching structure and learning-objective mapping
- automated verification that starter queries run against a generated SQLite dataset

This phase turned the repository into a more complete course-user package without changing the core generator model.

## Recently Delivered: Phase 11 - O2C and Inventory Enrichment

Phase 11 delivered:

- inventory-constrained shipments with backorders across periods
- exact shipment-to-invoice linkage through `SalesInvoiceLine.ShipmentLineID`
- customer-level receipts with separate cash applications
- customer deposits and unapplied cash behavior through `2060`
- operational returns, credit memos, and customer refunds
- stricter O2C validation and richer analytics starter coverage

This phase materially improved the revenue-cycle realism and brought the starter analytics layer into alignment with a fuller O2C process.

## Next Phase: Phase 12 - Manufacturing Foundation

### Why this is next

The next remaining expansion is manufacturing. The current dataset now has richer distributor-style O2C and P2P flows, but it still does not model work orders, WIP, completions, or production variance.

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

1. Phase 12 - Manufacturing Foundation

This order now focuses the project on the next major schema expansion instead of further refinement of already-implemented O2C behavior.
