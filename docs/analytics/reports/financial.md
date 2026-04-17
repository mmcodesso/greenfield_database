---
title: Financial Reports
description: Curated financial reports generated from the published SQLite build.
sidebar_label: Financial Reports
---

import { ReportCatalog } from "@site/src/components/ReportCatalog";
import { reportAreaCollections } from "@site/src/generated/reportDocCollections";

# Financial Reports

Use these reports when you want a student-first output for monthly close, statements, revenue review, and receivables/payables aging analysis.

<ReportCatalog
  groups={reportAreaCollections.financial}
  helperText="Preview a sample directly in the site, then download the Excel or CSV artifact generated from the current SQLite build."
/>
