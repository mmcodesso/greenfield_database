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

## Recently Delivered: Phase 15 - Capacity and Scheduling

Phase 15 delivered:

- `WorkCenter.NominalDailyCapacityHours`
- `WorkCenterCalendar` rows for every work center and calendar day in range
- `WorkOrderOperation.PlannedLoadHours`
- `WorkOrderOperationSchedule` rows with capacity-aware daily load allocation
- schedule-aware manufacturing execution, validation, anomalies, and starter analytics
- updated manufacturing, payroll, analytics, and technical documentation

This phase turned the routing-aware manufacturing model into a capacity-aware scheduling foundation without changing standard-cost valuation.

## Next Phase: Time Clocks and Shift Labor

### Why this is next

The dataset now has routings, work centers, work-center calendars, operation schedules, operation-level labor assignment, and standard-cost manufacturing. The next high-value gap is employee-level time and attendance detail.

The next high-value addition is time-clock and shift logic that can support:

- shift-level attendance
- clock-in and clock-out detail
- richer overtime-timing review
- payroll-to-production timing controls

### Planned scope

The next phase should add:

- employee shift records
- time-clock transactions
- attendance and overtime timing analytics
- richer payroll-control and labor-timing anomalies
- tighter payroll-to-production linkage analysis

## Recommended Sequence

1. Phase 16: Time Clocks and Shift Labor
2. Additional analytics packs built on top of the time-clock layer
3. Additional analytics packs built on top of those new operational layers
