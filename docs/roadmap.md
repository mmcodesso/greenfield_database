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

## Recently Delivered: Phase 15.2 - Performance and Validation Hardening

Phase 15.2 delivered:

- shared cache support through `state_cache.py`
- scoped validation entry points: `core`, `operational`, and `full`
- a dedicated profiling config at `config/settings_perf.yaml`
- cleaner build helpers through `build_phase15_2(...)`
- a clean five-year no-export build time under the current hardening gate

This phase did not change business behavior. It made the Phase 15 foundation faster to generate and validate.

## Recently Delivered: Phase 16 - Time Clocks and Shift Labor

Phase 16 delivered:

- `ShiftDefinition`
- `EmployeeShiftAssignment`
- `TimeClockEntry`
- `AttendanceException`
- hourly payroll sourced from approved time-clock hours
- direct manufacturing labor linked to both work-order operations and supporting time-clock rows
- time-clock validation, anomaly coverage, and starter analytics

This phase turned payroll and manufacturing labor into a more realistic time-and-attendance model without changing standard-cost valuation.

## Previously Delivered: Phase 15 - Capacity and Scheduling

Phase 15 delivered:

- `WorkCenter.NominalDailyCapacityHours`
- `WorkCenterCalendar` rows for every work center and calendar day in range
- `WorkOrderOperation.PlannedLoadHours`
- `WorkOrderOperationSchedule` rows with capacity-aware daily load allocation
- schedule-aware manufacturing execution, validation, anomalies, and starter analytics
- updated manufacturing, payroll, analytics, and technical documentation

This phase turned the routing-aware manufacturing model into a capacity-aware scheduling foundation without changing standard-cost valuation.

## Next Planning Focus

The next major phase is not locked yet, but the most likely follow-on work is deeper workforce and operations planning built on top of the new time-clock layer.

Likely next candidates:

- raw punch-event detail beneath the current approved daily time-clock model
- rotating shift rosters and richer attendance-planning logic
- shift-level capacity planning that ties workforce availability more tightly to work-center scheduling
- deeper labor-timing anomaly packs and workforce-efficiency analytics

## Recommended Sequence

1. Expand the starter analytics pack around the Phase 16 time-clock layer
2. Add richer workforce-planning detail when the next phase is locked
3. Continue extending analytics and anomaly packs on top of those operational layers
