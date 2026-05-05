---
title: Pricing Governance Audit Case
description: Inquiry-led walkthrough for price-list validity, promotion compliance, customer-specific pricing, and override approval controls.
sidebar_label: Pricing Governance Audit
---

import { QueryReference } from "@site/src/components/QueryReference";

# Pricing Governance Audit Case

## Business Scenario

The dataset maintains formal price lists, seasonal promotions, customer-specific pricing, and explicit override approvals. Students need to determine whether the commercial-control design is being followed and where transaction pricing no longer matches the approved pricing framework.

This case reads pricing as a control system rather than just a margin system. It starts from approved commercial rules, traces flagged sales lines back to the source pricing records, and separates poor master data, poor execution, and missing approval discipline.

## The Problem to Solve

The review team needs to identify where transaction pricing breaks from the approved pricing design and which exceptions should be escalated as governance failures rather than normal commercial variation.

## What You Need to Develop

- A price-list validity review that separates expired use from overlapping active lists.
- A promotion compliance review for date and scope mismatches.
- A customer-specific pricing review that identifies bypassed customer-specific lists.
- A floor-discipline review for below-floor sales without approval.
- An override documentation conclusion that determines whether approval support is complete enough to defend the exception.

## Before You Start

- Main tables: `PriceList`, `PriceListLine`, `PromotionProgram`, `PriceOverrideApproval`, `SalesOrder`, `SalesOrderLine`, `Customer`, `Item`
- Related case: [Pricing and Margin Governance Case](pricing-and-margin-governance-case.md)
- Related guide: [Audit Queries](../audit.md)
- Related report: [Commercial and Working Capital](../reports/commercial-and-working-capital.md)
- Supporting references: [Schema Reference](../../reference/schema.md), [Dataset Guide](../../start-here/dataset-overview.md)
- This case is the formal commercial-control audit follow-through. Use the pricing-and-margin case when you want to explain realized pricing and margin effects before audit escalation.

## Step-by-Step Walkthrough

### Step 1. Test price-list validity and overlap

Start with the pricing master data. Transaction pricing cannot be trusted if the governing price lists are expired, overlapping, or ambiguous for the same scope.

**What we are trying to achieve**

Identify price lists used after expiry and active price lists that overlap for the same commercial scope.

**Why this step changes the diagnosis**

This step separates price-list master-data problems from sales-line execution problems. If the policy layer is ambiguous, later transaction exceptions may be symptoms rather than the root control failure.

**Suggested query**

<QueryReference
  queryKey="audit/48_expired_or_overlapping_price_list_review.sql"
  helperText="Use this first to test expired price-list use and overlapping active price lists."
/>

**What this query does**

It returns expired price-list use on sales lines and overlapping active price lists for the same scope.

**How it works**

The query builds one review set by self-joining active `PriceList` rows to find overlapping scope and date windows, then unions sales lines whose linked price list is expired or used after its effective end date.

**What to look for in the result**

- overlapping active lists for the same scope
- expired price lists used by sales orders
- scope values that repeat across exceptions
- whether the issue belongs to pricing master-data cleanup or transaction review

### Step 2. Test promotion scope and date compliance

After price-list validity is clear, test promotional controls. Promotions must fit both the effective date window and the approved scope.

**What we are trying to achieve**

Find sales lines that use a promotion outside the allowed date range or customer/item scope.

**Why this step changes the diagnosis**

Promotion exceptions are governance problems before they are margin problems. This step proves whether promotional pricing followed the approved commercial program.

**Suggested query**

<QueryReference
  queryKey="audit/49_promotion_scope_and_date_mismatch_review.sql"
  helperText="Use this to find promoted sales lines outside approved promotion dates or scope."
/>

**What this query does**

It flags promoted sales lines where the order date falls outside the promotion window or the customer/item does not match the promotion scope.

**How it works**

The query joins `SalesOrderLine` to `SalesOrder`, `Customer`, `Item`, and `PromotionProgram`, then tests order dates and scope fields against the promotion rules.

**What to look for in the result**

- promotions used before start date or after end date
- segment, item-group, or collection scope mismatches
- promotions tied to recurring customers or item groups
- whether the exception is promotion setup or sales execution

### Step 3. Test customer-specific price-list bypass

Once general pricing and promotion controls are tested, move to customer-specific pricing. A valid customer-specific list should be used when it applies.

**What we are trying to achieve**

Identify order lines that bypass an available customer-specific price list.

**Why this step changes the diagnosis**

Customer-specific bypass is a governance issue even when the final price looks commercially plausible. It shows whether transaction pricing followed the approved customer agreement.

**Suggested query**

<QueryReference
  queryKey="audit/50_customer_specific_price_list_bypass_review.sql"
  helperText="Use this to find order lines where a valid customer-specific price list existed but was not used."
/>

**What this query does**

It returns sales order lines where a customer-specific price list option existed for the customer, item, date, and quantity, but the line used a different pricing method.

**How it works**

The query builds customer-specific options from `SalesOrder`, `SalesOrderLine`, `Customer`, `PriceList`, and `PriceListLine`, then keeps lines whose pricing method is not customer-specific despite a valid customer-specific option.

**What to look for in the result**

- customers with repeated bypasses
- order lines where quantity meets the customer-specific minimum
- pricing methods used instead of the customer-specific list
- whether bypass reflects sales execution or pricing master-data confusion

### Step 4. Review below-floor sales without approval

After approved pricing paths are tested, inspect floor discipline. Below-floor pricing requires valid approval support.

**What we are trying to achieve**

Identify sales lines priced below the configured floor without a linked override approval.

**Why this step changes the diagnosis**

This step turns pricing variance into a control finding. A below-floor line is not automatically wrong, but it becomes a governance exception when approval support is missing.

**Suggested query**

<QueryReference
  queryKey="audit/47_sales_below_floor_without_approval.sql"
  helperText="Use this to find sales lines below minimum price with no override approval link."
/>

**What this query does**

It lists sales order lines where `UnitPrice` is below `MinimumUnitPrice` and no price override approval is linked.

**How it works**

The query joins `SalesOrderLine` to `SalesOrder`, `Customer`, `Item`, and `PriceListLine`, compares actual unit price to minimum unit price, and keeps rows with no `PriceOverrideApprovalID`.

**What to look for in the result**

- lines below floor with no approval link
- customers or item families with repeated below-floor activity
- whether the pricing method explains the exception
- whether the issue should be escalated to sales leadership or finance

### Step 5. Close with override approval completeness

Finish by reviewing whether override approvals are complete when they do exist, and whether below-floor override-priced lines are missing their approval record.

**What we are trying to achieve**

Determine whether override approval documentation is complete enough to support exception pricing.

**Why this step changes the diagnosis**

The closeout separates missing approval from incomplete approval. Both matter, but they point to different remediation: transaction linkage versus approval workflow discipline.

**Suggested query**

<QueryReference
  queryKey="audit/51_override_approval_completeness_review.sql"
  helperText="Use this to test incomplete override approvals and missing override links for below-floor lines."
/>

**What this query does**

It returns incomplete approval records and below-floor sales lines that are missing an override approval link.

**How it works**

The query builds one set from `PriceOverrideApproval` joined to sales lines and keeps missing approver, missing date, or non-approved status records. It unions below-floor sales lines with no linked override approval.

**What to look for in the result**

- incomplete approval records
- missing override links
- below-floor lines where approval documentation is absent or not approved
- whether the final issue is floor discipline, approval completeness, or both

## Required Student Output

Submit a short case memo or notebook note with these four artifacts:

- Evidence summary: identify the key result rows, metrics, timing patterns, or exception families that changed your diagnosis.
- Accounting or business interpretation: explain what the evidence means for the process, accounting treatment, managerial decision, or control risk.
- Database explanation: name the source tables, row grain, join keys, or trace path that make the evidence defensible.
- Management or audit conclusion: state which driver, document path, or exception family should be followed up first and why.

## Optional Excel Follow-Through

1. Build one price-list tab for expired use and overlapping active lists by scope.
2. Add one promotion tab that compares order date and customer/item scope to promotion rules.
3. Build one customer-specific pricing tab for bypassed customer price lists.
4. Add one price-floor tab that compares unit price to minimum unit price and approval link.
5. Finish with one override documentation tab and a short conclusion on the strongest commercial-control issue.

## Wrap-Up Questions

- Accounting/process: Which pricing-control failure most weakens commercial governance or margin discipline?
- Database/source evidence: Which price-list, promotion, customer-specific, floor, or override source row proves the exception?
- Analytics judgment: Is the strongest issue master data, promotion compliance, bypass behavior, floor discipline, or approval documentation?
- Escalation/next step: Which controls should sales leadership own, and which should finance or audit review first?

## Next Steps

- Read [Pricing and Margin Governance Case](pricing-and-margin-governance-case.md) when you want the commercial interpretation beside the audit interpretation.
- Read [Audit Queries](../audit.md) for the broader control-review query library.
- Read [Commercial and Working Capital](../reports/commercial-and-working-capital.md) when you want the business perspective that sits above the control issues.
