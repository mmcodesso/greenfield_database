---
title: Why CharlesRiver
description: Why Charles River exists and why its integrated teaching model matters for accounting analytics courses.
slug: /why-CharlesRiver
sidebar_label: Why CharlesRiver
---

# Why CharlesRiver

## Overview

Accounting analytics is hard to teach when students see tables first and business logic later. Many classes can show journal entries. Many classes can show sample spreadsheets. Far fewer can show how a business event creates a document chain, moves through operational activity, and finally reaches the ledger. That gap slows learning and weakens explanation.

Charles River addresses that problem with a synthetic, integrated, ERP-style accounting analytics environment. It combines business context, process flows, source documents, posted GLEntry activity, and teaching materials in one openly shareable package. Students can trace business activity from operations to accounting. Instructors can adopt a ready-to-use environment with one coherent model and supporting materials.

## Why This Project Was Necessary

Publicly shareable ERP-style accounting datasets with end-to-end process logic and ledger traceability are rare. That matters for teaching. Instructors need data they can distribute widely. They also need data that carries enough business structure to support process analysis, accounting analysis, and control review in the same course or across several courses.

Many available teaching options solve only part of the problem. Some datasets are easy to share but flatten the business story into disconnected tables. Some examples show transactions without the upstream operational documents that created them. Some systems offer rich process context but sit behind proprietary platforms or limited teaching environments. The result is predictable. Students learn how to query fields without learning how the business works. Or they learn the business story without getting a traceable dataset they can analyze directly.

Charles River closes that gap. It gives instructors one integrated teaching model that can support process mining, SQL work, Excel work, visualization, subledger review, control analysis, and source-to-ledger explanation. That makes the project useful in AIS, accounting analytics, auditing, financial accounting, managerial accounting, and business process courses.

## Why Synthetic Data Is the Right Choice

Synthetic data makes this project possible. Real accounting data often contains confidential customer terms, supplier pricing, payroll details, approval history, and internal control evidence. Even when a company wants to support education, broad public sharing is difficult and course reuse across institutions becomes harder.

Charles River takes a practical path. It uses synthetic data to model realistic business activity without exposing a real company, real employees, or confidential transactions. That choice protects privacy and supports open distribution. It also gives instructors a stable teaching asset that they can share in a syllabus, course shell, workshop, or public website without waiting for a special data access arrangement.

Synthetic does not mean shallow. The educational value comes from the structure of the model. The important question is whether the data supports source-to-ledger reasoning, process analysis, and accounting interpretation. Charles River is built to do exactly that.

## What Charles River Models

Charles River models one fictional company: **Charles River Home Furnishings, Inc.** The business buys some finished goods and manufactures others. That hybrid structure creates the right teaching environment for accounting analytics because it forces the data to connect customer demand, supplier activity, inventory movement, labor usage, and finance.

The model brings together these core threads:

- customer demand, commercial pricing, shipment, billing, receipt, return, credit, and refund activity
- purchasing, receiving, supplier invoicing, and payment activity
- manufacturing planning, material issue, production completion, and work-order close activity
- time, payroll, labor allocation, and payroll liability settlement activity
- recurring journals, accruals, close-cycle entries, and posted ledger activity

That integration matters for teaching because students rarely analyze accounting outcomes in isolation. They need to see how revenue connects to fulfillment, how purchasing supports manufacturing, how labor reaches product cost, and how all of those events affect the ledger. For the full business narrative, use [Company Story](../learn-the-business/company-story.md). For the detailed cycle walkthroughs, use [Process Flows](../learn-the-business/process-flows.md).

## How the Data Reaches the Ledger

This is the core reason Charles River is analytically useful. The dataset does not stop at operational records. It carries business events into posted ledger detail and preserves the trace fields that let users move back to the source.

Take a short order-to-cash example:

`Customer -> SalesOrder -> SalesOrderLine -> Shipment -> ShipmentLine -> SalesInvoice -> SalesInvoiceLine -> CashReceiptApplication -> GLEntry`

That path lets students ask several important questions. Which document created revenue. Which event moved inventory into cost of goods sold. Which invoice remained open at period end. Which cash application cleared the receivable. Which ledger entries belong to the same business event.

Charles River supports that work because posted ledger rows include the traceability fields that matter most:

- `SourceDocumentType`
- `SourceDocumentID`
- `SourceLineID`
- `VoucherType`
- `VoucherNumber`
- `PostingDate`
- `FiscalYear`
- `FiscalPeriod`

Those fields make the ledger a usable teaching asset. An instructor can ask students to explain a revenue posting from its shipment and invoice records. A student can start in `GLEntry` and work back to the source document chain. An auditing assignment can test whether the ledger reflects the expected document path. For the event-by-event rules, use [GLEntry Posting Reference](../reference/posting.md). For the table-level structure behind those paths, use [Schema Reference](../reference/schema.md).

## What Teaching Materials Come With It

Charles River is a teaching package with linked materials that support orientation, analysis, and course adoption.

- [Company Story](../learn-the-business/company-story.md): explains the business model and why the company structure matters for accounting analysis
- [Process Flows](../learn-the-business/process-flows.md): shows the major business cycles and how events move toward the ledger
- [Dataset Guide](dataset-overview.md): gives the mental model for the table families, key joins, and navigation paths
- [Schema Reference](../reference/schema.md): supports table lookup, high-value fields, and join cues
- [GLEntry Posting Reference](../reference/posting.md): explains what posts, what does not post, and which accounts move
- [SQL Guide](../analytics/sql-guide.md): gives a structured path into query-based work
- [Excel Guide](../analytics/excel-guide.md): gives a parallel path for workbook-based analysis
- [Analytics Hub](../analytics/index.md): organizes the main financial, managerial, and audit topics
- [Analytics Cases](../analytics/cases/index.md): provides guided walkthroughs that connect business context, starter SQL, and interpretation
- [Instructor Adoption Guide](../teach-with-CharlesRiver/instructor-guide.md): helps instructors sequence the material and choose assignment paths

These materials reduce setup friction. Students do not need to guess why a table exists. Instructors do not need to build the business context from scratch. The site gives a coherent path from orientation to analysis.

## Why It Works as an OER

Charles River is designed as an open educational resource. In plain language, that means instructors and institutions can adopt it, adapt it, and extend it for teaching. The project uses the `CC BY-SA 4.0` license so users can share the material with attribution and keep derivative versions under the same open terms.

That licensing model is part of the educational value. Faculty can revise assignments, localize cases, add course notes, or build new teaching sequences on top of the same foundation. Curriculum developers can use the model as a reusable platform for continued teaching and development.

## Who Should Use It

Charles River is designed for three main groups:

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
- [Analytics Cases](../analytics/cases/index.md): use guided assignments before open-ended analysis
- [Instructor Adoption Guide](../teach-with-CharlesRiver/instructor-guide.md): plan course sequencing and adoption

Charles River works best when readers start with the teaching problem, move into the business model, and then open the data. That sequence keeps the joins meaningful and keeps the ledger tied to real business reasoning.
