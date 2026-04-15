---
title: Product Portfolio Profitability Case
description: Guided walkthrough for collection, style, lifecycle, supply mode, and contribution-margin analysis.
sidebar_label: Portfolio Profitability Case
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# Product Portfolio Profitability Case

## Audience and Purpose

Use this case when students need a richer portfolio-analysis exercise than simple item-group reporting.

## Business Scenario

CharlesRiver’s management team wants to know which collections and lifecycle groups are carrying the business. They also want to know whether manufactured and purchased items behave differently on gross margin, contribution margin, service performance, and return pressure.

## Main Tables and Worksheets

- `Item`
- `SalesInvoiceLine`
- `CreditMemoLine`
- `ShipmentLine`
- `SalesOrderLine`
- `CustomerRefund`

## Recommended Query Sequence

<QuerySequence items={caseQuerySequences["product-portfolio-profitability-case"]} />

## Suggested Excel Sequence

1. Build a pivot by `CollectionName`, `StyleFamily`, `LifecycleStatus`, and `SupplyMode`.
2. Compare billed sales, gross margin, contribution margin, and return-rate measures side by side.
3. Filter to one collection and trace whether service-level pressure and returns appear together.

## What Students Should Notice

- A collection can be important operationally even if its contribution margin is weaker than its gross margin.
- Supply mode changes the meaning of cost and contribution margin.
- Lifecycle status adds a portfolio-management angle to return and refund analysis.
- Service issues and return pressure do not always hit the same product families.

## Follow-Up Questions

- Which collection looks strongest on gross margin but weaker on contribution margin?
- Which portfolio attribute is most useful for explaining return pressure?
- When would management prefer a collection-level view over an item-level view?
