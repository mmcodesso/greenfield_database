---
title: Pricing and Margin Governance Case
description: Guided commercial-pricing case using price lists, promotions, overrides, and realized margin.
sidebar_label: Pricing and Margin Case
---

# Pricing and Margin Governance Case

## Audience and Purpose

- audience: financial analytics, managerial analytics, and commercial-policy students
- purpose: connect list price, negotiated pricing, promotions, and net margin without introducing a separate quote system

## Business Scenario

Greenfield now prices from formal segment and customer price lists with explicit promotions and override approvals. Students need to explain how price realization changes by customer mix, where promotions dilute revenue, and when override approvals become commercially significant.

## Query Sequence

1. [25_price_realization_vs_list_by_segment_customer_region_collection_style.sql](../../../queries/financial/25_price_realization_vs_list_by_segment_customer_region_collection_style.sql)
2. [26_gross_margin_impact_of_promotions_vs_nonpromotion_sales.sql](../../../queries/financial/26_gross_margin_impact_of_promotions_vs_nonpromotion_sales.sql)
3. [47_sales_rep_override_rate_and_discount_dispersion.sql](../../../queries/managerial/47_sales_rep_override_rate_and_discount_dispersion.sql)
4. [48_collection_revenue_margin_before_after_promotions.sql](../../../queries/managerial/48_collection_revenue_margin_before_after_promotions.sql)
5. [49_customer_specific_pricing_concentration_and_dependency.sql](../../../queries/managerial/49_customer_specific_pricing_concentration_and_dependency.sql)
6. [50_monthly_price_floor_pressure_and_override_concentration.sql](../../../queries/managerial/50_monthly_price_floor_pressure_and_override_concentration.sql)

## Suggested Excel Sequence

1. open the sheets `PriceList`, `PriceListLine`, `PromotionProgram`, `PriceOverrideApproval`, `SalesOrderLine`, and `SalesInvoiceLine`
2. build a pivot of base-list revenue versus net revenue by customer segment
3. chart promotion revenue reduction by collection
4. isolate override lines and compare them to the price-floor thresholds from `PriceListLine`

## What Students Should Notice

- price realization now comes from explicit commercial rules
- promotions lower net revenue through the line discount field while revenue still posts net in the GL
- customer-specific pricing should concentrate in a minority of strategic accounts, not across the full customer base
- override pressure should be visible but rare relative to total order-line volume

## Follow-Up Questions

1. Which customer segments realize the largest gap between base-list revenue and net revenue?
2. Which collections rely most on promotions to drive billed volume?
3. Which sales reps show the highest override concentration?
4. Where does customer-specific pricing appear commercially justified versus administratively heavy?
