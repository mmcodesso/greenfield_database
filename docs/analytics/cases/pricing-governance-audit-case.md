---
title: Pricing Governance Audit Case
description: Guided audit case focused on expired pricing, promotion misuse, customer-specific bypass, and override approval completeness.
sidebar_label: Pricing Governance Audit
---

# Pricing Governance Audit Case

## Audience and Purpose

- audience: audit, AIS, and controls-focused analytics students
- purpose: review whether formal price lists, promotions, and override approvals are being used as designed

## Business Scenario

Greenfield now maintains formal price lists, seasonal promotions, and explicit override approvals. Students need to determine whether the commercial-control design is being followed and where transaction pricing no longer matches the approved pricing framework.

## Query Sequence

1. [47_sales_below_floor_without_approval.sql](../../../queries/audit/47_sales_below_floor_without_approval.sql)
2. [48_expired_or_overlapping_price_list_review.sql](../../../queries/audit/48_expired_or_overlapping_price_list_review.sql)
3. [49_promotion_scope_and_date_mismatch_review.sql](../../../queries/audit/49_promotion_scope_and_date_mismatch_review.sql)
4. [50_customer_specific_price_list_bypass_review.sql](../../../queries/audit/50_customer_specific_price_list_bypass_review.sql)
5. [51_override_approval_completeness_review.sql](../../../queries/audit/51_override_approval_completeness_review.sql)

## Suggested Excel Sequence

1. open `PriceList`, `PriceListLine`, `PromotionProgram`, `PriceOverrideApproval`, `SalesOrderLine`, and `AnomalyLog`
2. filter `AnomalyLog` to the Phase 23 pricing anomaly families
3. trace one flagged line from the order line into its linked price-list line and override record
4. compare effective dates and scope fields directly in the workbook

## What Students Should Notice

- expired-price-list use and overlapping active lists are different failures and should not be treated as the same control issue
- a line below floor is only acceptable when the override documentation is complete
- customer-specific price-list bypass is a governance issue even when the final price still looks commercially plausible
- promotion date and scope failures are master-data/control problems before they are margin-analysis problems

## Follow-Up Questions

1. Which anomaly type creates the strongest evidence of missing commercial governance?
2. Which exceptions are master-data failures versus transaction-execution failures?
3. Which pricing exceptions would require immediate remediation before the next sales cycle?
4. Which pricing controls should be reviewed by sales leadership versus finance leadership?
