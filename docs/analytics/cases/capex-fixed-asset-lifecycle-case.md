---
title: CAPEX and Fixed Asset Lifecycle Case
description: Guided walkthrough for tracing CAPEX additions, debt financing, depreciation routing, and disposals across the fixed-asset lifecycle.
sidebar_label: CAPEX Lifecycle Case
---

import { QuerySequence } from "@site/src/components/QueryReference";
import { caseQuerySequences } from "@site/src/generated/queryDocCollections";

# CAPEX and Fixed Asset Lifecycle Case

## Business Scenario

Charles River now needs a teachable fixed-asset story that matches how a real company behaves. The company adds plant equipment, warehouse equipment, and office or showroom assets across multiple years. Some purchases are paid in cash, some are reclassed from AP into notes payable, some assets are improved later, and some are eventually retired or replaced.

The accounting behavior is not uniform. Manufacturing equipment depreciation belongs in manufacturing cost through `1090` Manufacturing Cost Clearing. Warehouse and office depreciation stay in operating expense through `6130`. Disposal removes gross cost and accumulated depreciation, and note-financed assets create a second lifecycle through scheduled principal and interest payments.

## The Problem to Solve

You need to explain one CAPEX story from source documents through the asset register and into the financial statements. Show how acquisitions, financing, depreciation, and disposals affect the ledger, cash flow, and manufacturing cost interpretation.

## Key Data Sources

- `PurchaseRequisition`, `PurchaseOrder`, `PurchaseInvoice`, `DisbursementPayment`
- `FixedAsset`, `FixedAssetEvent`, `DebtAgreement`, `DebtScheduleLine`
- `Warehouse`, `WorkCenter`, `CostCenter`
- `JournalEntry`, `GLEntry`, `Account`

## Recommended Query Sequence

<QuerySequence items={caseQuerySequences["capex-fixed-asset-lifecycle-case"]} />

## What Students Should Prove

- Manufacturing, warehouse, and office assets can share one fixed-asset lifecycle while still producing different depreciation behavior.
- Cash CAPEX and note-financed CAPEX both begin in P2P, but note-financed purchases create a later AP-to-notes reclass and then separate principal and interest cash behavior.
- Manufacturing-equipment depreciation belongs in manufacturing cost interpretation because it debits `1090`, while warehouse and office depreciation stay in `6130`.
- Disposal accounting removes gross cost and accumulated depreciation before recognizing any gain or loss in `7020`.

## Questions To Answer

- Which additions were paid in cash and which were financed through notes payable?
- Which assets belong to manufacturing, warehouse, and office behavior groups?
- How much monthly depreciation is staying in operating expense versus entering manufacturing cost?
- Which disposal events produced cash proceeds, and what happened to the remaining net book value?
- How do principal and interest payments affect financing cash versus operating cash?

## Next Steps

- Read [Procure-to-Pay Process](../../processes/p2p.md) to see how CAPEX items still begin in the normal requisition, PO, invoice, and payment flow.
- Read [Manufacturing Process](../../processes/manufacturing.md) to connect plant-equipment depreciation back into manufacturing clearing and standard-cost interpretation.
- Read [Manual Journals and Close Cycle](../../processes/manual-journals-and-close.md) for the debt reclass, depreciation, note payment, and disposal journals that complete the lifecycle.
- Read [GLEntry Posting Reference](../../reference/posting.md) and [Schema Reference](../../reference/schema.md) when you need the exact posting rules or table bridges.
- Use [Financial Analytics](../financial.md) when you want the wider statement and cash-flow analysis around the same CAPEX events.
