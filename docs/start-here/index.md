---
title: Start Here
description: The main entry page for learning the accounting dataset from files to analysis.
slug: /
sidebar_label: Start Here
---

# Start Here

<DatasetName /> is easiest to understand when it is treated as one company moving through a small number of connected business cycles. Sales demand becomes fulfillment and cash collection. Purchasing supports inventory and operating needs. Manufacturing turns materials and labor into finished goods. Payroll supports labor, liabilities, and cash settlement. Finance closes the whole picture in the ledger.

That is the main learning path of the site. Students should begin with the business itself, then move into the processes, and only then move into reports, SQL, Excel, or cases. The published files are important, but they make more sense after the company and the business cycles are clear.

## Start With the Company and the Cycles

Read the first pages as one sequence:

1. [Downloads](downloads.md) to get the published teaching package
2. [Company Story](../learn-the-business/company-story.md) to understand the business model
3. [Process Flows](../learn-the-business/process-flows.md) to see how the major cycles connect
4. One process page such as [O2C](../processes/o2c.md), [P2P](../processes/p2p.md), [Manufacturing](../processes/manufacturing.md), or [Payroll](../processes/payroll.md)

This sequence keeps the business logic in front of the data. By the time students open a table or query, they should already know what the company is doing and where the accounting evidence comes from.

## How the Business Reaches Analysis

| Business cycle | What it changes in the company | Best analytical follow-through |
|---|---|---|
| [O2C](../processes/o2c.md) | Revenue, receivables, collections, returns, and customer corrections | [Commercial and Working Capital](../analytics/reports/commercial-and-working-capital.md), [Financial Reports](../analytics/reports/financial.md), [O2C Trace Case](../analytics/cases/o2c-trace-case.md) |
| [P2P](../processes/p2p.md) | Supplier commitments, receipts, AP timing, and accrual settlement | [Commercial and Working Capital](../analytics/reports/commercial-and-working-capital.md), [Financial Reports](../analytics/reports/financial.md), [P2P Accrual Case](../analytics/cases/p2p-accrual-settlement-case.md) |
| [Manufacturing](../processes/manufacturing.md) | Planning pressure, component usage, labor support, completion, and close | [Operations and Risk](../analytics/reports/operations-and-risk.md), [Managerial Reports](../analytics/reports/managerial.md), [Manufacturing Labor Case](../analytics/cases/manufacturing-labor-cost-case.md) |
| [Payroll](../processes/payroll.md) | People cost, approved time, payroll liabilities, cash settlement, and control review | [Payroll and Workforce](../analytics/reports/payroll-perspective.md), [Financial Reports](../analytics/reports/financial.md), [Workforce Cost and Org-Control Case](../analytics/cases/workforce-cost-and-org-control-case.md) |
| [Manual Journals and Close](../processes/manual-journals-and-close.md) | Accruals, reclasses, retained earnings, and final statement presentation | [Executive Overview](../analytics/reports/executive-overview.md), [Financial Reports](../analytics/reports/financial.md), [Financial Statement Bridge Case](../analytics/cases/financial-statement-bridge-case.md) |

## The Published Teaching Files

The downloaded files contain the same dataset in different formats. Students can use them with different tools and for different kinds of work, but the underlying business activity and accounting are the same:

- <FileName type="sqlite" /> is the best file for source-to-ledger SQL analysis.
- <FileName type="excel" /> is the best file for workbook-based review, pivots, charts, and filters.
- <FileName type="csv" /> is the best file when you want one table per file for external tools or import workflows.

Students should read the files as the same data package delivered in different formats, not as separate datasets or separate learning paths.

## Next Steps

1. Read [Company Story](../learn-the-business/company-story.md).
2. Read [Process Flows](../learn-the-business/process-flows.md).
3. Open the process page that matches the business question you want to follow first.
4. Then move into [Analytics Guides](../analytics/index.md), [Reports Hub](../analytics/reports/index.md), or [Analytics Cases](../analytics/cases/index.md).
