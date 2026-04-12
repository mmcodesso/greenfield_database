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

## Why Master Data Comes Next

The next major phase should improve master data realism before adding deeper workforce-operating detail.

Current gaps that matter for teaching:

- employee titles still repeat in ways that weaken role-based controls, such as multiple CEOs and missing unique finance leadership roles
- the employee master does not yet model inactive, terminated, or leave-status employees
- item names are still generic patterns rather than business-readable product names
- the product catalog does not yet support richer collection, style, material, finish, and lifecycle analysis

Fixing those gaps first improves the current dataset more broadly than raw punch-event detail would:

- **Auditing:** stronger approval, HR, master-data, and terminated-employee control scenarios
- **Financial analytics:** clearer payroll, organization, and close-role interpretation
- **Managerial analytics:** stronger product-family, collection, lifecycle, and portfolio analysis
- **Cost accounting:** better rollups and comparisons by meaningful product family and product attributes

## Next Planned Phase: Phase 18 - Master Data Realism and Workforce Lifecycle Foundation

Phase 18 should add a more realistic but still teachable employee and item master.

Planned employee improvements:

- deterministic org-structure role assignment instead of repeated executive titles
- exactly one `Chief Executive Officer`
- exactly one `Chief Financial Officer`
- exactly one `Controller`
- exactly one `Production Manager`
- exactly one `Accounting Manager`
- repeatable frontline and supervisory roles only where repetition makes business sense
- moderate workforce lifecycle modeling through status, termination, and role metadata
- historical employee retention for traceability, while preventing new clean-build activity after termination

Planned item and product-catalog improvements:

- deterministic business-readable product names instead of `Item ####`
- richer item attributes inside the existing `Item` table, such as collection, style family, material, finish, color, size, launch timing, and lifecycle status
- continued support for purchased and manufactured finished goods without changing the current operational model
- clearer catalog structure for profitability, returns, mix, and cost-accounting analysis

Planned teaching value:

- stronger org-role and approval analytics
- headcount, tenure, turnover, and terminated-employee audit review
- richer sales, return, and margin analysis by collection and product family
- stronger cost and contribution-margin analysis by meaningful product groupings

## Planned Follow-On Phases

### Phase 19 - Analytics Starter Pack 2.0 and Case Library Expansion

Phase 19 should use the richer employee and item masters to expand the teaching layer.

Planned focus:

- more guided SQL and Excel paths across financial, managerial, audit, and cost-accounting topics
- richer walkthrough cases built around named products, collections, departments, and employee roles
- stronger product profitability, turnover, payroll-mix, and org-control labs
- instructor-facing activity sequencing that separates clean analysis from anomaly analysis

This phase should remain documentation, query, and case heavy rather than process-model heavy.

### Phase 20 - Master Data and Workforce Audit Anomaly Expansion

Phase 20 should expand anomaly coverage around employee and item master controls.

Planned focus:

- terminated or inactive employee activity
- conflicting executive-role assignments
- approval-authority mismatch and stale employee-master scenarios
- inactive or discontinued item usage
- missing or inconsistent product-catalog attributes
- stronger linkage between anomaly packs, audit starter queries, and case labs

This phase should improve audit teaching coverage without turning the base dataset into an exception-heavy build.

### Phase 21 - Workforce Planning Detail

Only after Phases 18 to 20 should the roadmap return to deeper workforce-operating detail beneath the current daily time-clock model.

Planned focus:

- raw punch-event detail beneath approved daily time-clock rows
- rotating shift rosters
- richer employee-availability and attendance-planning logic
- deeper labor-timing and workforce-efficiency anomalies

This work still matters, but it is no longer the immediate next step because it improves operational detail more narrowly than master-data realism and teaching-pack expansion.

## Recommended Sequence

1. Phase 18 - Master Data Realism and Workforce Lifecycle Foundation
2. Phase 19 - Analytics Starter Pack 2.0 and Case Library Expansion
3. Phase 20 - Master Data and Workforce Audit Anomaly Expansion
4. Phase 21 - Workforce Planning Detail
