---
title: Product Portfolio Profitability Case
description: Guided walkthrough for collection, style, lifecycle, supply mode, and contribution-margin analysis.
sidebar_label: Portfolio Profitability Case
---

# Product Portfolio Profitability Case

## Audience and Purpose

Use this case when students need a richer portfolio-analysis exercise than simple item-group reporting.

## Recommended Build Mode

- Default anomaly-enabled or clean build

## Business Scenario

Greenfield’s management team wants to know which collections and lifecycle groups are carrying the business. They also want to know whether manufactured and purchased items behave differently on gross margin, contribution margin, service performance, and return pressure.

## Main Tables and Worksheets

- `Item`
- `SalesInvoiceLine`
- `CreditMemoLine`
- `ShipmentLine`
- `SalesOrderLine`
- `CustomerRefund`

## Recommended Query Sequence

1. Run [../../../queries/managerial/31_product_portfolio_mix_by_collection_style_lifecycle_supply_mode.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/31_product_portfolio_mix_by_collection_style_lifecycle_supply_mode.sql).
2. Run [../../../queries/financial/21_revenue_and_gross_margin_by_collection_style_lifecycle_supply_mode.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/financial/21_revenue_and_gross_margin_by_collection_style_lifecycle_supply_mode.sql).
3. Run [../../../queries/managerial/32_contribution_margin_by_collection_material_lifecycle_supply_mode.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/32_contribution_margin_by_collection_material_lifecycle_supply_mode.sql).
4. Run [../../../queries/managerial/33_customer_service_impact_by_collection_style.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/33_customer_service_impact_by_collection_style.sql).
5. Run [../../../queries/managerial/35_portfolio_return_refund_impact_by_collection_lifecycle.sql](https://github.com/mmcodesso/greenfield_database/blob/main/queries/managerial/35_portfolio_return_refund_impact_by_collection_lifecycle.sql).

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
