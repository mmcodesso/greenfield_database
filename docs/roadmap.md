# Roadmap

**Audience:** Maintainers, contributors, and instructors tracking planned expansion of the dataset.  
**Purpose:** Define the next implementation phase and capture the remaining roadmap sequence.  
**What you will learn:** What has been delivered, what should be built next, and why.

## Current Status

The current generator already delivers:

- five fiscal years of data from 2026 through 2030
- order-to-cash and procure-to-pay transaction generation
- manufacturing foundation with BOMs, routings, work centers, work orders, operations, issues, completions, and close
- opening balances, recurring manual journals, manufacturing reclasses, year-end close, and budgets
- event-based postings into `GLEntry`
- validations, anomaly injection, starter analytics assets, and exports

## Recently Delivered: Phase 14 - Routing and Work Center Foundation

Phase 14 delivered:

- work centers and active routings for manufactured items
- routing operations with standard setup, run, and queue assumptions
- work-order operation rows created at release time
- operation-level direct-labor assignment through `LaborTimeEntry.WorkOrderOperationID`
- routing-aware manufacturing validation and starter analytics
- updated manufacturing and payroll process documentation

This phase turned the manufacturing model from a single-stage flow into a routing-aware foundation without changing standard-cost valuation.

## Next Phase: Capacity and Scheduling

### Why this is next

The dataset now has routings, work centers, operation-level labor assignment, and standard-cost manufacturing. The next high-value gap is planned load versus available capacity.

The next high-value addition is capacity and schedule logic that can support:

- work-center capacity calendars
- planned load versus available hours
- bottleneck and backlog analytics
- schedule-delay analysis beyond simple queue assumptions

### Planned scope

The next phase should add:

- work-center capacity calendars
- planned load versus capacity measures
- backlog and bottleneck analytics
- richer schedule-delay analytics
- capacity-oriented controls and anomalies

## Recommended Sequence

1. Phase 15: Capacity and Scheduling
2. Phase 16: Time Clocks and Shift Labor
3. Additional analytics packs built on top of those new operational layers
