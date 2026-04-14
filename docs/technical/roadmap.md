---
title: Roadmap
description: Planned future expansion areas for the Greenfield dataset and documentation.
slug: /roadmap
sidebar_label: Roadmap
---

# Roadmap

Use this page for current-versus-future scope. The rest of the documentation is intentionally focused on present behavior and present teaching use.

## Current Delivered Scope

The current generator already delivers:

- five fiscal years of data from 2026 through 2030
- order-to-cash and procure-to-pay transaction generation
- manufacturing foundation with BOMs, routings, work centers, work orders, operations, issues, completions, and close
- payroll, approved daily time clocks, and labor allocation support
- weekly demand planning, replenishment recommendations, material-requirement planning, and rough-cut capacity tieout
- richer employee and item master data for role, lifecycle, and portfolio analysis
- event-based postings into `GLEntry`
- validations, anomaly injection, starter analytics assets, walkthrough cases, and exports

## Recently Delivered: Phase 18 - Master Data Realism and Workforce Lifecycle Foundation

Phase 18 delivered:

- richer employee master data with `EmployeeNumber`, `EmploymentStatus`, `TerminationDate`, `JobFamily`, `JobLevel`, and `WorkLocation`
- richer item master data with collection, style family, material, finish, color, size, lifecycle, launch date, and supply-mode context
- unique-role enforcement for CEO, CFO, Controller, Production Manager, and Accounting Manager in clean builds
- date-aware employee and item eligibility across operational generation
- master-data anomaly coverage and starter analytics built on the improved employee and item masters

This phase improved realism and teaching value without adding a new operational subledger.

## Recently Delivered: Phase 19 - Analytics Starter Pack 2.0 and Case Library Expansion

Phase 19 delivered:

- broader starter SQL coverage across financial, managerial, audit, and cost-accounting topics
- new working-capital, financial-statement bridge, product-portfolio, workforce-cost, and audit-review cases
- updated analytics docs, Excel guidance, SQL guidance, and instructor sequencing
- stronger use of the default anomaly-enabled build as the main classroom package

This phase did not change schema, posting, or generation behavior. It expanded the teaching layer on top of the current operational model.

## Earlier Delivered Foundations

### Phase 17 - Starter Analytics and Audit Anomaly Teaching Expansion

Delivered:

- broader starter SQL coverage across financial, managerial, and audit topics
- richer audit anomaly coverage inside the main `standard` anomaly profile
- case-style walkthrough docs and richer subprocess diagrams
- dataset-only SQLite and Excel outputs plus a separate support workbook

### Phase 16 - Time Clocks and Shift Labor

Delivered:

- `ShiftDefinition`
- `EmployeeShiftAssignment`
- `TimeClockEntry`
- `AttendanceException`
- hourly payroll sourced from approved time-clock hours
- direct manufacturing labor linked to both work-order operations and time-clock support

### Phase 15.2 - Performance and Validation Hardening

Delivered:

- shared cache support through `state_cache.py`
- scoped validation entry points: `core`, `operational`, and `full`
- a dedicated profiling config at `config/settings_perf.yaml`
- cleaner build helpers through `build_phase15_2(...)`

## Recently Delivered: Phase 20 - Master Data and Workforce Audit Anomaly Expansion

Phase 20 delivered:

- broader anomaly coverage around employee and item master controls
- stronger approval-authority and current-state assignment exceptions
- audit-query extensions that map directly to the new anomaly families
- a stronger default anomaly-enabled audit path without a separate teaching profile

## Recently Delivered: Phase 21 - Workforce Planning Detail

Phase 21 delivered:

- raw punch-event detail beneath approved daily time-clock rows
- daily shift rosters, explicit absences, and overtime approvals
- deeper attendance, overtime, and roster-control starter analytics and cases
- stronger payroll-to-time-to-labor traceability

## Recently Delivered: Phase 22 - Demand Planning and MRP Foundation

Phase 22 delivered:

- weekly demand forecasts and inventory policies
- replenishment recommendations that now support normal requisition and work-order creation
- component-demand explosion through `MaterialRequirementPlan`
- rough-cut capacity tieout through `RoughCutCapacityPlan`
- starter analytics and audit queries for forecast quality, planning support, and recommendation timing

This phase strengthens the planning-to-execution bridge without changing valuation away from standard cost.

## Recently Completed Sequence

1. Phase 20 - Master Data and Workforce Audit Anomaly Expansion
2. Phase 21 - Workforce Planning Detail
3. Phase 22 - Demand Planning and MRP Foundation
