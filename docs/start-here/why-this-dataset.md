---
title: Why Use This Accounting Analytics Dataset
description: Why this synthetic accounting analytics dataset works for SQL, Excel, audit, financial, managerial, and business-process teaching paths.
slug: /why-this-dataset
sidebar_label: Why This Dataset
---

# Why This Dataset

## Overview

Accounting analytics becomes more meaningful when students can connect business events, source documents, and ledger impact inside one teaching model. <DisplayName /> gives them that model. It brings together business context, process flows, source documents, posted GLEntry activity, and classroom-ready guidance in one openly shareable package.

Students can trace business activity from operations to accounting. Instructors can teach SQL, Excel, audit, financial, managerial, and process-focused work within one company model.

## How the Dataset Supports Teaching

Instructors need data they can distribute widely and explain clearly. Students need a model that shows how a business event creates a document chain, moves through operational activity, and reaches the ledger. <DisplayName /> supports both goals with one coherent structure.

The dataset supports process analysis, accounting analysis, control review, and source-to-ledger explanation in the same environment. The synthetic design also supports broad classroom use, open distribution, and course reuse across institutions.

## What the Dataset Models

<DisplayName /> models one fictional company: <CompanyName />. The business buys some finished goods, manufactures others, and delivers hourly design services. That hybrid structure gives students a realistic view of how customer demand, supplier activity, inventory movement, labor usage, service delivery, and finance connect inside one operating system.

The model brings together these core threads:

- customer demand, commercial pricing, shipment, service billing, receipt, return, credit, and refund activity
- purchasing, receiving, supplier invoicing, and payment activity
- manufacturing planning, material issue, production completion, and work-order close activity
- time, payroll, labor allocation, design-service support, and payroll liability settlement activity
- recurring journals, accruals, close-cycle entries, and posted ledger activity

Students can see how revenue connects to fulfillment and service delivery, how purchasing supports manufacturing, how labor supports both operations and services, and how those events affect the ledger. For the full business narrative, use [Company Story](../learn-the-business/company-story.md). For the detailed cycle walkthroughs, use [Process Flows](../learn-the-business/process-flows.md).

## How the Data Reaches the Ledger

The dataset carries business events into posted ledger detail and preserves the trace fields that let users move back to the source.

Take a short order-to-cash example:

`Customer -> SalesOrder -> SalesOrderLine -> Shipment -> ShipmentLine -> SalesInvoice -> SalesInvoiceLine -> CashReceiptApplication -> GLEntry`

Students can ask several important questions along that path. Which document created revenue. Which event moved inventory into cost of goods sold. Which invoice remained open at period end. Which cash application cleared the receivable. Which ledger entries belong to the same business event.

The design-services branch adds a second revenue path:

`Customer -> SalesOrder -> SalesOrderLine -> ServiceEngagement -> ServiceTimeEntry -> ServiceBillingLine -> SalesInvoiceLine -> GLEntry`

<DisplayName /> supports that work because posted ledger rows include the traceability fields that matter most:

- `SourceDocumentType`
- `SourceDocumentID`
- `SourceLineID`
- `VoucherType`
- `VoucherNumber`
- `PostingDate`
- `FiscalYear`
- `FiscalPeriod`

Those fields make the ledger a strong teaching asset. An instructor can ask students to explain a revenue posting from its shipment or service-billing records. A student can start in `GLEntry` and work back to the source document chain. An auditing assignment can test whether the ledger reflects the expected document path. For the event-by-event rules, use [GLEntry Posting Reference](../reference/posting.md). For the table-level structure behind those paths, use [Schema Reference](../reference/schema.md).

## What Teaching Materials Come With It

<DisplayName /> is a teaching package with linked materials that support orientation, analysis, and course adoption.

- [Company Story](../learn-the-business/company-story.md): explains the business model and why the company structure matters for accounting analysis
- [Process Flows](../learn-the-business/process-flows.md): shows the major business cycles and how events move toward the ledger
- [Dataset Guide](dataset-overview.md): gives the mental model for the table families, key joins, and navigation paths
- [Schema Reference](../reference/schema.md): supports table lookup, high-value fields, and join cues
- [GLEntry Posting Reference](../reference/posting.md): explains what posts and which accounts move
- [SQL Guide](../analytics/sql-guide.md): gives a structured path into query-based work
- [Excel Guide](../analytics/excel-guide.md): gives a parallel path for workbook-based analysis
- [Analyze the Data](../analytics/index.md): introduces the SQL, Excel, reports, cases, and topic-track paths
- [Cases](../analytics/cases/index.md): provides guided walkthroughs that connect business context, starter SQL, and interpretation
- [Instructor Adoption Guide](../teach-with-data/instructor-guide.md): helps instructors sequence the material and choose assignment paths

These materials give students and instructors a coherent path from orientation to analysis.

## Why the OER Model Helps

<DisplayName /> is designed as an open educational resource. Instructors and institutions can adopt it, adapt it, and extend it for teaching. The project uses the `CC BY-SA 4.0` license so users can share the material with attribution and keep derivative versions under the same open terms.

That licensing model supports long-term classroom use. Faculty can revise assignments, localize cases, add course notes, and build new teaching sequences on top of the same foundation. Curriculum developers can use the model as a reusable platform for continued teaching and development.

## Who Should Use It

The dataset is designed for three main groups:

- instructors who need a reusable environment for accounting analytics, AIS, audit, process, or cost-accounting modules
- students who need to learn how business events become accounting information through SQL, Excel, and guided process analysis
- researchers and curriculum developers who need an openly licensed teaching environment that can support reuse, comparison, and extension

## Where to Start

Use this reading path when you want to move from orientation to adoption quickly:

- [Start Here](index.md): begin with the classroom files and the core reading order
- [Company Story](../learn-the-business/company-story.md): learn the business model before reading tables
- [Process Flows](../learn-the-business/process-flows.md): follow the major cycles that drive the dataset
- [Dataset Guide](dataset-overview.md): understand the table families and navigation paths
- [SQL Guide](../analytics/sql-guide.md): start the query-based path
- [Excel Guide](../analytics/excel-guide.md): start the workbook-based path
- [Cases](../analytics/cases/index.md): use guided assignments before open-ended analysis
- [Instructor Adoption Guide](../teach-with-data/instructor-guide.md): plan course sequencing and adoption

<DisplayName /> works best when readers start with the business model, move through the process pages, and then open the data. That sequence keeps the joins meaningful and keeps the ledger tied to business reasoning.
