---
title: Product Portfolio Profitability Case
description: Inquiry-led walkthrough for ranking collections and lifecycle groups across sales, margin, service, and return pressure.
sidebar_label: Portfolio Profitability Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# Product Portfolio Profitability Case

## Business Scenario

Management is comparing collections and lifecycle groups to decide which product families truly carry the business. Revenue alone does not answer that question. A collection can drive strong billed sales and still create weaker contribution, slower service, or heavier return pressure.

This case asks students to judge the portfolio through several lenses at the same time. The company needs a view that compares billed sales, gross margin, contribution margin, service performance, and return pressure across the same portfolio families. That is how management decides where to invest, where to repair performance, and where to challenge the current mix.

Your job is to build that portfolio ranking, test where the ranking changes under different measures, and finish with a clear management recommendation.

## The Problem to Solve

You need to prove which collections and lifecycle groups generate the strongest revenue and gross-margin contribution, whether contribution margin changes that ranking materially, whether service performance reinforces or contradicts the financial view, and whether return and refund pressure changes the final portfolio interpretation.

## What You Need to Develop

- A ranked portfolio view by collection and lifecycle status.
- A gross-margin versus contribution-margin explanation.
- A service-level interpretation tied to fill rate, shipment lag, and backorder pressure.
- A return and refund interpretation tied to lifecycle grouping.
- A short management-facing recommendation on the most attractive and least attractive portfolio families.

## Before You Start

- Main tables: `Item`, `SalesInvoiceLine`, `CreditMemoLine`, `SalesReturnLine`, `ShipmentLine`, `SalesOrderLine`, `CustomerRefund`
- Related guides: [Managerial Queries](../managerial.md), [Financial Queries](../financial.md), [Operations and Risk](../reports/operations-and-risk.md)
- Related cases: [Product Portfolio and Lifecycle Case](product-portfolio-and-lifecycle-case.md), [Pricing and Margin Governance Case](pricing-and-margin-governance-case.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case ranks portfolio families across multiple performance lenses rather than tracing one document flow. Use the lighter portfolio case for catalog setup and the pricing case for commercial-policy interpretation.

## Step-by-Step Walkthrough

### Step 1. Define the portfolio mix you are evaluating

Start by defining the portfolio population. Before you rank performance, you need a clear view of collections, style families, lifecycle groups, and supply modes.

**What we are trying to achieve**

Establish the mix of collections, style families, lifecycle groups, and supply modes that management is evaluating.

**Why this step changes the diagnosis**

This step gives you the portfolio frame. A ranking means very little if the underlying mix is unclear.

**Suggested query**

<QueryReference
  queryKey="managerial/31_product_portfolio_mix_by_collection_style_lifecycle_supply_mode.sql"
  helperText="Use this first to see how the portfolio is distributed across collection, style family, lifecycle status, and supply mode."
/>

**What this query does**

It summarizes the portfolio mix across the main descriptive dimensions used later in the case.

**How it works**

The query groups `Item` rows by collection, style family, lifecycle status, and supply mode. That creates the portfolio frame for the rest of the walkthrough.

**What to look for in the result**

- the largest collections and style families
- how much of the catalog sits in each lifecycle group
- where manufactured and purchased items concentrate
- which portfolio families are large enough to matter in later ranking work

### Step 2. Rank the portfolio on billed sales and gross margin

Once the mix is clear, move to the first economic ranking. This step establishes the top-line and gross-margin view that management usually sees first.

**What we are trying to achieve**

Identify which collections and lifecycle groups carry the most net sales and gross margin.

**Why this step changes the diagnosis**

This is the first performance ranking, not the final answer. It shows where the portfolio looks strongest before contribution, service, and return pressure change the interpretation.

**Suggested query**

<QueryReference
  queryKey="financial/21_revenue_and_gross_margin_by_collection_style_lifecycle_supply_mode.sql"
  helperText="Use this to rank collections and lifecycle groups on billed sales, net sales, and gross margin."
/>

**What this query does**

It compares billed sales, credit activity, net sales, net standard cost, and gross margin by collection, style family, lifecycle status, and supply mode.

**How it works**

The query starts from billed sales in `SalesInvoiceLine`, offsets them with `CreditMemoLine` and `SalesReturnLine`, and ties the billed and returned activity back to `Item` attributes.

**What to look for in the result**

- the collections carrying the most net sales
- the families generating the strongest gross margin
- lifecycle groups that look stronger or weaker than expected
- whether supply mode already appears to matter materially

### Step 3. Test whether contribution margin changes the ranking

Now test the ranking under a different cost lens. Gross margin can overstate the attractiveness of some families when variable-cost logic tells a different story.

**What we are trying to achieve**

Show whether the portfolio ranking changes once variable-cost logic is used.

**Why this step changes the diagnosis**

This step changes the ranking logic. Supply mode matters here because manufactured items exclude fixed overhead in this contribution view, so some families can look better or worse than they did on gross margin alone.

**Suggested query**

<QueryReference
  queryKey="managerial/32_contribution_margin_by_collection_material_lifecycle_supply_mode.sql"
  helperText="Use this to compare contribution margin across collections, materials, lifecycle groups, and supply modes."
/>

**What this query does**

It compares net sales with variable-cost logic to produce contribution margin by collection, material, lifecycle status, and supply mode.

**How it works**

The query starts from `Item`, derives a variable unit cost, then compares billed and credited activity through `SalesInvoiceLine` and `CreditMemoLine` to build net sales, net variable cost, and contribution margin.

**What to look for in the result**

- collections whose rank changes when contribution margin replaces gross margin
- whether manufactured and purchased families behave differently
- lifecycle groups that look weaker once fixed-overhead logic is removed
- which families deserve caution despite strong gross-margin performance

### Step 4. Add the service-performance lens

Financial performance still does not finish the portfolio story. Now test whether service performance reinforces or weakens the ranking.

**What we are trying to achieve**

Show where fill rate, shipment lag, and backorder pressure reinforce or weaken the profitability view.

**Why this step changes the diagnosis**

This step adds the operating lens. A strong collection financially can still create operational strain, and management needs both views before it makes a portfolio decision.

**Suggested query**

<QueryReference
  queryKey="managerial/33_customer_service_impact_by_collection_style.sql"
  helperText="Use this to compare fill rate, shipment lag, and backorder pressure by collection and style family."
/>

**What this query does**

It measures ordered quantity, shipped quantity, backordered quantity, fill rate, days to first shipment, and backordered-line share by collection and style family.

**How it works**

The query starts from `SalesOrderLine`, joins shipment activity back through `ShipmentLine`, and aggregates the service measures by collection and style family.

**What to look for in the result**

- collections with low fill rate or high backorder pressure
- collections with longer shipment lag
- whether the strongest financial families also perform well operationally
- where service strain changes the portfolio ranking

### Step 5. Add return and refund pressure to finalize the portfolio view

Finish the case by testing whether returns and refunds change the final portfolio interpretation.

**What we are trying to achieve**

Show how credit and refund pressure changes the final interpretation of portfolio attractiveness.

**Why this step changes the diagnosis**

This step finishes the management view. A single metric cannot rank the portfolio reliably if return and refund pressure changes the real outcome.

**Suggested query**

<QueryReference
  queryKey="managerial/35_portfolio_return_refund_impact_by_collection_lifecycle.sql"
  helperText="Use this to compare credit and refund pressure by collection and lifecycle status."
/>

**What this query does**

It compares billed sales, credited activity, allocated refunds, credit rate, and refund rate by collection and lifecycle status.

**How it works**

The query starts from `SalesInvoiceLine`, offsets the billed base with `CreditMemoLine`, allocates `CustomerRefund` values back to the credited lines, and groups the result by collection and lifecycle status.

**What to look for in the result**

- collections with the heaviest credit or refund pressure
- lifecycle groups that carry more after-sale correction
- whether return pressure confirms or contradicts the earlier ranking
- which portfolio families management should protect, repair, or reconsider first

## Required Student Output

Submit a short case memo or notebook note with these four artifacts:

- Evidence summary: identify the key result rows, metrics, timing patterns, or exception families that changed your diagnosis.
- Accounting or business interpretation: explain what the evidence means for the process, accounting treatment, managerial decision, or control risk.
- Database explanation: name the source tables, row grain, join keys, or trace path that make the evidence defensible.
- Management or audit conclusion: state which driver, document path, or exception family should be followed up first and why.

## Optional Excel Follow-Through

1. Start with one portfolio mix pivot by collection, lifecycle status, and supply mode.
2. Add a second view that ranks gross margin by the same portfolio families.
3. Add a third view that compares gross margin with contribution margin to show rank changes.
4. Add a narrow service-and-return tab so fill rate, backorder pressure, credits, and refunds sit beside the economic ranking.
5. Finish with a short conclusion tab that names which families to protect, invest in, repair, or reconsider.

## Wrap-Up Questions

- Accounting/process: Which portfolio family changes most when the view moves from gross margin to contribution and after-sale pressure?
- Database/source evidence: Which collection, lifecycle, service, return, or refund grain supports the portfolio ranking?
- Analytics judgment: Which family combines strong economics with weak service, or weak economics with high return pressure?
- Escalation/next step: Which portfolio family should management protect, invest in, repair, or reconsider first?

## Next Steps

- Use [Product Portfolio and Lifecycle Case](product-portfolio-and-lifecycle-case.md) when you want the catalog and lifecycle setup behind this ranking view.
- Use [Pricing and Margin Governance Case](pricing-and-margin-governance-case.md) when you want the commercial pricing explanation beneath realized revenue and margin.
- Use [Managerial Queries](../managerial.md) and [Operations and Risk](../reports/operations-and-risk.md) for the broader portfolio and performance context.
