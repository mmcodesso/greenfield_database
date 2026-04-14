---
title: Product Portfolio and Lifecycle Case
description: Guided walkthrough for product naming, catalog attributes, lifecycle status, and portfolio margin analysis.
sidebar_label: Product Portfolio Case
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# Product Portfolio and Lifecycle Case


## Business Scenario

Greenfield no longer uses generic item names. Finished goods now belong to collections and style families, use more meaningful materials and finishes, and carry lifecycle labels such as `Core`, `Seasonal`, and `Discontinued`.

This case uses that richer item master to connect catalog realism to managerial and cost-accounting analysis.

## Main Tables and Worksheets

- `Item`
- `SalesInvoiceLine`
- `CreditMemoLine`
- `ShipmentLine`
- `SalesReturnLine`
- `Customer`

## Recommended Query Sequence

<QuerySequence items={caseQuerySequences["product-portfolio-and-lifecycle-case"]} />

## Suggested Excel Sequence

1. Filter `Item` to one collection or style family.
2. Compare item names, materials, finishes, colors, and lifecycle status.
3. Build a pivot of billed sales, credits, and margin by `CollectionName` and `LifecycleStatus`.
4. Check whether seasonal or discontinued products behave differently from core products.

## What Students Should Notice

- Better item names make portfolio analysis easier to teach and easier to explain.
- Lifecycle status adds a managerial angle to margin and return analysis.
- Collection, style family, and material attributes create a more realistic product-story layer than generic item-group analysis alone.
- The same item master now supports managerial analysis, cost accounting, and audit completeness checks.

## Follow-Up Questions

- Which product attributes matter most for gross-margin review?
- What is the difference between a collection and a style family in this dataset?
- How could lifecycle status change the way an instructor frames a product-profitability exercise?
