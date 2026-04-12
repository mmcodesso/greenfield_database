---
title: Roadmap
description: Planned future expansion areas for the Greenfield dataset and documentation.
sidebar_label: Roadmap
---

# Roadmap


Use this page for current-versus-future scope. The rest of the documentation is intentionally focused on present behavior and present teaching use.

## Current Delivered Scope

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

## Recently Delivered: Phase 17 - Starter Analytics and Audit Anomaly Teaching Expansion

Phase 17 delivered:

- broader use of the default `config/settings.yaml` build for starter analytics, anomaly work, and walkthrough cases
- broader starter SQL coverage across financial, managerial, and audit topics
- richer audit anomaly coverage inside the main `standard` anomaly profile
- case-style walkthrough docs under `docs/analytics/cases/`
- richer subprocess diagrams inside the process guides
- a split export package with dataset-only SQLite and Excel outputs plus a separate support workbook

This phase did not add a new operational process. It made the current Phase 16 foundation easier to teach, easier to audit, and easier to explore with starter analytics.

## Previously Delivered: Phase 15 - Capacity and Scheduling

Phase 15 delivered:

- `WorkCenter.NominalDailyCapacityHours`
- `WorkCenterCalendar` rows for every work center and calendar day in range
- `WorkOrderOperation.PlannedLoadHours`
- `WorkOrderOperationSchedule` rows with capacity-aware daily load allocation
- schedule-aware manufacturing execution, validation, anomalies, and starter analytics
- updated manufacturing, payroll, analytics, and technical documentation

This phase turned the routing-aware manufacturing model into a capacity-aware scheduling foundation without changing standard-cost valuation.

## Planned Extensions

The next major phase is not locked yet, but the most likely follow-on work is deeper workforce-planning detail beneath the current daily time-clock model.

Likely next candidates:

- raw punch-event detail beneath the current approved daily time-clock model
- rotating shift rosters and richer attendance-planning logic
- shift-level workforce planning that ties employee availability more tightly to work-center scheduling
- deeper labor-timing anomaly packs and workforce-efficiency analytics

## Recommended Sequence

1. Add raw punch-event detail beneath the current approved daily time-clock layer
2. Add rotating shift rosters and richer workforce-planning detail
3. Continue extending analytics and anomaly packs on top of those deeper workforce layers
