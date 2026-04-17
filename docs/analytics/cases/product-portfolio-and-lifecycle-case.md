---
title: Product Portfolio and Lifecycle Case
description: Inquiry-led walkthrough for catalog structure, item-master quality, lifecycle status, and portfolio interpretation.
sidebar_label: Product Portfolio Case
---

import { QueryReference } from "@site/src/components/QueryReference";

# Product Portfolio and Lifecycle Case

## Business Scenario

Charles River Home Furnishings sells finished goods across multiple collections, style families, materials, and finishes. Merchandising, sales, and operations all depend on the same `Item` master while the catalog is active. They need product attributes that are clear enough to support reporting and reliable enough to support real decisions.

Lifecycle status raises the stakes. A `Core` item supports the steady catalog. A `Seasonal` item carries a narrower selling window. A `Discontinued` item signals that the company should stop treating the product like part of the active portfolio. When those labels drift away from the item master or from actual activity, management loses trust in the portfolio view.

Your job is to explain the portfolio structure first, confirm that the item master can support it, and then show how lifecycle logic changes the way managers interpret sales and exception activity.

## The Problem to Solve

You need to prove which item attributes define the portfolio in a usable way. Confirm that lifecycle labels and active status align with the current catalog state. Confirm that sales and portfolio mix differ by collection, style family, lifecycle status, and supply mode. Confirm that lifecycle exceptions appear in real operational activity.

## What You Need to Develop

- A clean description of the portfolio structure for one or more collections.
- A lifecycle-status interpretation tied directly to item-master fields.
- A mix analysis using collection, style family, lifecycle status, and supply mode.
- An exception view for missing attributes, inconsistent status, or post-discontinuation activity.
- A short management-facing conclusion on which catalog dimensions deserve follow-up in the separate profitability case.

## Before You Start

- Main tables: `Item`, `SalesInvoiceLine`, `ShipmentLine`, `SalesOrderLine`, `SalesReturnLine`, `CreditMemoLine`, `WorkOrder`, `PurchaseOrderLine`
- Related process pages: [Order-to-Cash Process](../../processes/o2c.md), [Manufacturing Process](../../processes/manufacturing.md), [Procure-to-Pay Process](../../processes/p2p.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case stays focused on catalog structure and lifecycle interpretation. Use the separate portfolio profitability case when you need deeper margin analysis.

## Step-by-Step Walkthrough

### Step 1. Define the portfolio structure in the item master

Start with the portfolio itself. Before you interpret sales or returns, you need to know how the company classifies the catalog.

**What we are trying to achieve**

Establish the main catalog dimensions that segment the portfolio across collections, style families, lifecycle status, and supply mode.

**Why this matters**

Every later conclusion depends on these dimensions. If the portfolio structure is weak or unclear, later managerial analysis will also be weak.

**Suggested query**

<QueryReference
  queryKey="managerial/31_product_portfolio_mix_by_collection_style_lifecycle_supply_mode.sql"
  helperText="Use this first to see how the catalog is distributed across collection, style family, lifecycle status, and supply mode."
/>

**What this query does**

It summarizes the product portfolio using the main item-master attributes that define catalog structure.

**How it works**

The query groups `Item` rows by collection, style family, lifecycle status, and supply mode. That gives you a high-level portfolio map before you move into quality or transaction evidence.

**What to look for in the result**

- the largest collections and style families
- how much of the catalog sits in each lifecycle group
- where manufactured and purchased items concentrate
- which dimensions look strong enough to support later analysis

### Step 2. Check whether the item master is complete enough to trust

Once the catalog structure is visible, test whether the supporting attributes are complete enough to trust.

**What we are trying to achieve**

Find sellable items that are missing key catalog attributes such as collection, style family, primary material, finish, or lifecycle status.

**Why this matters**

Missing item attributes weaken reporting, teaching, and management review. A portfolio analysis fails quickly if core item-master fields are blank.

**Suggested query**

<QueryReference
  queryKey="audit/30_item_master_completeness_review.sql"
  helperText="Use this to find items with missing catalog attributes that should exist for their item group."
/>

**What this query does**

It flags items that do not carry the expected descriptive fields for their item group.

**How it works**

The query evaluates item-group-specific attribute expectations inside `Item` and returns rows where one or more required descriptive fields are missing.

**What to look for in the result**

- missing `CollectionName`
- missing `StyleFamily`
- missing `PrimaryMaterial`
- missing `Finish` or `Color`
- missing `LifecycleStatus`

### Step 3. Test whether lifecycle labels and active status align

After completeness, move to consistency. A complete item master can still carry conflicting lifecycle logic.

**What we are trying to achieve**

Identify current-state conflicts between `LifecycleStatus` and `IsActive`.

**Why this matters**

Lifecycle analysis only works when current-state item status makes sense. If active flags and lifecycle labels disagree, portfolio reporting becomes hard to defend.

**Suggested query**

<QueryReference
  queryKey="audit/36_item_status_alignment_review.sql"
  helperText="Use this to isolate conflicts between lifecycle status and active-status logic."
/>

**What this query does**

It returns item-master rows where current catalog status appears internally inconsistent.

**How it works**

The query reads `Item` directly and compares lifecycle labels with active-status logic and related descriptive fields.

**What to look for in the result**

- discontinued items that still look active
- inactive items that still look like current catalog items
- catalog segments where status logic appears less reliable
- whether the problem is isolated or widespread

### Step 4. Connect the catalog to sales and portfolio mix

Now connect the item master to business activity. The goal here is to confirm that the catalog dimensions actually matter when products sell.

**What we are trying to achieve**

Show how portfolio dimensions appear in billed sales and contribution interpretation across collections, materials, lifecycle groups, and supply modes.

**Why this matters**

Catalog structure earns its value when it explains business results. This step shows whether the item-master dimensions are useful enough to support later profitability work.

**Suggested query**

<QueryReference
  queryKey="managerial/30_sales_margin_by_collection_style_material.sql"
  helperText="Use this to connect billed sales and margin patterns back to collection, style family, and material."
/>

<QueryReference
  queryKey="managerial/32_contribution_margin_by_collection_material_lifecycle_supply_mode.sql"
  helperText="Use this follow-through query to extend the view into lifecycle and supply-mode interpretation."
/>

**What this query does**

The first query summarizes billed sales and margin by catalog dimensions. The second extends the same view into lifecycle status and supply mode.

**How it works**

These queries join sales activity back to `Item` and aggregate results by the descriptive fields that define the portfolio.

**What to look for in the result**

- collections with stronger billed sales concentration
- lifecycle groups that carry weaker or stronger contribution patterns
- supply-mode differences inside the same collection family
- which dimensions deserve deeper follow-up in the profitability case

### Step 5. Extend the case into lifecycle exception follow-up

Finish with the control question. If lifecycle status matters, it should change how you interpret real activity after the catalog state shifts.

**What we are trying to achieve**

Find lifecycle-driven exception activity and connect it to customer-facing outcomes such as returns or refunds.

**Why this matters**

This step turns lifecycle status into an operational control concept. It shows whether the company continued using products after launch windows or after discontinuation.

**Suggested query**

<QueryReference
  queryKey="audit/31_discontinued_or_prelaunch_item_activity_review.sql"
  helperText="Use this to identify operational activity that occurred before launch or after discontinuation."
/>

<QueryReference
  queryKey="managerial/35_portfolio_return_refund_impact_by_collection_lifecycle.sql"
  helperText="Use this follow-through query to connect lifecycle grouping to return and refund behavior."
/>

**What this query does**

The first query flags item activity that conflicts with lifecycle timing. The second shows how lifecycle groupings relate to downstream return and refund pressure.

**How it works**

The audit query overlays item lifecycle fields with transaction dates from sales, purchasing, manufacturing, shipment, and invoicing. The managerial query groups return and refund measures by collection and lifecycle status.

**What to look for in the result**

- discontinued items that still show fresh activity
- pre-launch items used too early
- collections with heavier return or refund pressure by lifecycle group
- whether lifecycle status changes the interpretation of the portfolio story

## Optional Excel Follow-Through

1. Filter `Item` to one collection or one style family.
2. Compare `CollectionName`, `StyleFamily`, `PrimaryMaterial`, `Finish`, `Color`, `SupplyMode`, and `LifecycleStatus`.
3. Build one pivot that counts items by collection, lifecycle status, and supply mode.
4. Build one follow-up pivot that compares billed sales or return pressure by collection and lifecycle group.
5. Keep the workbook focused on catalog structure and lifecycle interpretation. Save broader profitability modeling for the separate profitability case.

## Wrap-Up Questions

- Which item attributes create the strongest portfolio segmentation in this dataset?
- How does lifecycle status change the way you interpret item activity?
- Which item-master quality issue would most weaken management reporting?
- Which portfolio dimension should management carry into the profitability case next?

## Where to Go Next

- Use [Product Portfolio Profitability Case](product-portfolio-profitability-case.md) when you want deeper margin and contribution interpretation.
- Use [Schema Reference](../../reference/schema.md) when you need table-level support for item and transaction joins.
- Use [Order-to-Cash Process](../../processes/o2c.md), [Manufacturing Process](../../processes/manufacturing.md), and [Procure-to-Pay Process](../../processes/p2p.md) when you want to trace how lifecycle status shows up in operational activity.
