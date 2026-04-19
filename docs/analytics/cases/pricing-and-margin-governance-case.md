---
title: Pricing and Margin Governance Case
description: Inquiry-led walkthrough for pricing policy, realized price, promotions, overrides, and commercial margin effect.
sidebar_label: Pricing and Margin Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# Pricing and Margin Governance Case

## Business Scenario

Commercial leadership is reviewing why realized pricing differs from list price across customers, segments, collections, and style families. The company prices through formal price lists, promotions, customer-specific pricing, and rare override approvals. Those choices shape billed revenue before the result reaches the statements.

The central question is not whether realized price fell below list price. The central question is why it happened. Some dilution reflects deliberate pricing policy. Some reflects promotion strategy. Some reflects customer-specific commercial design. Some reflects negotiation pressure that shows up through overrides and price-floor tension. Leadership needs to separate those causes before it decides whether pricing governance needs attention.

Your job is to explain the pricing policy stack first, then show how that stack changes realized revenue and gross margin, and finally identify where the commercial story should move into governance follow-up.

## The Problem to Solve

You need to prove where price realization falls below base list pricing, how much of that result comes from promotions, customer-specific pricing, and override behavior, which customers, collections, and sales teams depend most on non-standard pricing paths, and when pricing pressure starts changing realized margin materially.

## What You Need to Develop

- A pricing-policy narrative from list price through promotions, customer-specific pricing, and overrides.
- A realized-pricing explanation by customer and portfolio segment.
- A promotion-effect explanation tied to revenue and gross margin.
- An override and price-floor pressure explanation tied to commercial concentration rather than audit exception testing.
- A short management-facing conclusion on where pricing governance deserves follow-up first.

## Before You Start

- Main tables: `PriceList`, `PriceListLine`, `PromotionProgram`, `PriceOverrideApproval`, `SalesOrder`, `SalesOrderLine`, `SalesInvoice`, `SalesInvoiceLine`, `Customer`, `Item`
- Related guides: [Financial Analytics](../financial.md), [Managerial Analytics](../managerial.md), [Commercial and Working Capital](../reports/commercial-and-working-capital.md)
- Related process page: [Order-to-Cash Process](../../processes/o2c.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [GLEntry Posting Reference](../../reference/posting.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case stays on commercial interpretation. Use the pricing audit case when you need full control-exception review.

## Step-by-Step Walkthrough

### Step 1. Define realized pricing against list price

Start with realized pricing. You need to see where billed revenue diverges from base list revenue before you explain the policy layers beneath it.

**What we are trying to achieve**

Establish where realized revenue differs from base list revenue across customers, segments, regions, collections, and style families.

**Why this matters**

This step gives you the commercial outcome first. It shows where pricing pressure exists before you decide whether promotions, customer-specific pricing, or override behavior explain it.

**Suggested query**

<QueryReference
  queryKey="financial/25_price_realization_vs_list_by_segment_customer_region_collection_style.sql"
  helperText="Use this first to compare realized billed revenue with base list revenue across the commercial book."
/>

**What this query does**

It summarizes invoiced quantity, base list revenue, net revenue, average discount, and price-realization percentage by month, customer segment, customer, region, collection, and style family.

**How it works**

The query starts from `SalesInvoiceLine`, joins the billed lines back to `SalesInvoice`, `Customer`, and `Item`, and compares `BaseListPrice` against actual billed line totals.

**What to look for in the result**

- customers or segments with the lowest price realization
- collections or style families showing consistent dilution
- whether the biggest realization gaps sit in a few accounts or across the full book
- where the commercial story clearly needs a policy explanation

### Step 2. Explain the promotion effect on revenue and gross margin

Once realized pricing is visible, separate the promotion effect from the broader pricing picture.

**What we are trying to achieve**

Show how promotions reduce revenue and change gross margin by month and collection.

**Why this matters**

Promotion strategy is a deliberate commercial choice. Students need to show when lower realized pricing reflects planned promotional activity rather than uncontrolled discounting.

**Suggested query**

<QueryReference
  queryKey="financial/26_gross_margin_impact_of_promotions_vs_nonpromotion_sales.sql"
  helperText="Use this first to compare promoted versus non-promoted revenue and gross margin."
/>

<QueryReference
  queryKey="managerial/48_collection_revenue_margin_before_after_promotions.sql"
  helperText="Use this follow-through query to isolate the revenue and gross-margin effect of promotions by collection."
/>

**What this query does**

The first query compares promoted and non-promoted sales by month and collection. The second isolates the revenue reduction from promotions and shows the collection-level margin result after that reduction.

**How it works**

These queries group billed sales by promotion flag and collection, compare revenue before and after promotion effect, and tie net revenue to standard shipment cost through `ShipmentLine`.

**What to look for in the result**

- collections relying most on promotions
- where promotion activity reduces revenue materially
- whether promotion-heavy collections still preserve healthy gross margin
- whether promotional pricing explains the low realization seen in Step 1

### Step 3. Show where customer-specific pricing is concentrated

Promotions are only one policy path. Next, isolate customer-specific pricing and see where commercial dependency is highest.

**What we are trying to achieve**

Identify which customers depend most on customer-specific pricing instead of standard segment pricing.

**Why this matters**

Customer-specific pricing can be commercially justified, but concentration changes negotiation complexity and makes realized pricing more dependent on a narrower set of accounts.

**Suggested query**

<QueryReference
  queryKey="managerial/49_customer_specific_pricing_concentration_and_dependency.sql"
  helperText="Use this to identify which customers rely most on customer-specific price lists."
/>

**What this query does**

It measures how much of each customer’s sales-order-line population uses `Customer Price List` pricing and how much order value sits behind that dependence.

**How it works**

The query starts from `SalesOrderLine`, joins back to `SalesOrder` and `Customer`, filters the `PricingMethod`, and computes customer-specific pricing share and net order value by customer.

**What to look for in the result**

- customers with the highest customer-specific pricing share
- whether those customers are also commercially important by order value
- whether pricing concentration appears strategic or administratively heavy
- which customer relationships deserve deeper commercial review

### Step 4. Measure override concentration and price-floor pressure

Now isolate override behavior. This is where commercial pressure becomes visible before it turns into a formal control issue.

**What we are trying to achieve**

Show where override behavior and floor pressure concentrate by sales rep, customer segment, and month.

**Why this matters**

Override pressure reveals negotiation intensity and pricing discipline. This step stays on commercial concentration and pressure, not on formal exception testing.

**Suggested query**

<QueryReference
  queryKey="managerial/47_sales_rep_override_rate_and_discount_dispersion.sql"
  helperText="Use this first to compare override concentration and discount dispersion by sales rep and customer segment."
/>

<QueryReference
  queryKey="managerial/50_monthly_price_floor_pressure_and_override_concentration.sql"
  helperText="Use this follow-through query to compare monthly floor pressure with override usage."
/>

**What this query does**

The first query measures override concentration by sales rep and customer segment. The second shows how often order lines sit at or below the price floor and how often overrides are used by month.

**How it works**

These queries start from `SalesOrderLine`, join to `SalesOrder`, `Employee`, `Customer`, and `PriceListLine`, and compare override usage, discount dispersion, and price-floor proximity over time and by selling context.

**What to look for in the result**

- sales reps with the highest override concentration
- customer segments showing heavier override pressure
- months where price-floor pressure spikes
- whether override activity looks concentrated and explainable or broad and unstable

### Step 5. Extend the case into governance follow-up

Finish by taking one controlled step into governance risk. This is where commercial interpretation starts handing the issue off to a control review.

**What we are trying to achieve**

Identify where the pricing story moves from commercial interpretation into governance follow-up.

**Why this matters**

The case should end with a decision about where leadership needs stronger review. That does not turn this page into the audit case, but it should show where governance attention becomes necessary.

**Suggested query**

<QueryReference
  queryKey="audit/51_override_approval_completeness_review.sql"
  helperText="Use this to identify missing or incomplete override approvals when override pressure has already been established commercially."
/>

**What this query does**

It isolates incomplete override approval records and missing override links on below-floor sales lines.

**How it works**

The query reads `PriceOverrideApproval`, `SalesOrderLine`, `SalesOrder`, `Customer`, `Item`, and `PriceListLine`, then separates incomplete approval records from missing linked approvals on below-floor lines.

**What to look for in the result**

- override-priced lines with incomplete approval support
- below-floor lines with no linked approval
- whether the governance issue is isolated or recurring
- which patterns should move into the full [Pricing Governance Audit Case](pricing-governance-audit-case.md)

## Optional Excel Follow-Through

1. Start with one customer segment or one collection.
2. Compare `BaseListRevenue`, `NetRevenue`, realized price, promotion effect, and override concentration.
3. Build one pivot by customer or segment and one pivot by collection.
4. Keep price-floor and override detail on a narrower follow-up tab.
5. Keep the workbook focused on commercial interpretation rather than turning it into a full anomaly log.

## Wrap-Up Questions

- Which customer or segment shows the lowest price realization?
- Do promotions or customer-specific pricing explain more of the dilution?
- Where does override concentration look commercially justified versus operationally heavy?
- Which collection appears most dependent on promotions?
- Which pricing pattern should move into the audit case next?

## Where to Go Next

- Use [Pricing Governance Audit Case](pricing-governance-audit-case.md) when you want the full control-focused follow-through.
- Use [Commercial and Working Capital](../reports/commercial-and-working-capital.md) when you want the broader commercial perspective above the case.
- Use [Financial Analytics](../financial.md) and [Managerial Analytics](../managerial.md) for the broader pricing and margin query sets.
