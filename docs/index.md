# Documentation Index

This page is the main navigation hub for the Greenfield Accounting Dataset documentation.

The docs are organized for two broad uses:

- course users who need to understand the company, the business processes, and the database
- technical users who need to understand how the generator and schema work

## Start Here by Audience

| If you are a... | Read this first | Then continue with |
|---|---|---|
| Student | [company-story.md](company-story.md) | [process-flows.md](process-flows.md), [database-guide.md](database-guide.md), [analytics/index.md](analytics/index.md) |
| Instructor | [instructor-guide.md](instructor-guide.md) | [company-story.md](company-story.md), [process-flows.md](process-flows.md), [analytics/index.md](analytics/index.md) |
| Analyst | [database-guide.md](database-guide.md) | [process-flows.md](process-flows.md), [analytics/index.md](analytics/index.md), [reference/schema.md](reference/schema.md) |
| Contributor | [technical-guide.md](technical-guide.md) | [code-architecture.md](code-architecture.md), [reference/schema.md](reference/schema.md), [reference/posting.md](reference/posting.md) |

## Business and Course Docs

| Document | What it covers |
|---|---|
| [company-story.md](company-story.md) | The business context of Greenfield Home Furnishings and how the company operates |
| [dataset-overview.md](dataset-overview.md) | What the dataset contains, what it is for, and the glossary of core terms |
| [process-flows.md](process-flows.md) | Process hub, reading order, and subledger-to-ledger traceability |
| [processes/o2c.md](processes/o2c.md) | Order-to-cash process explained step by step |
| [processes/o2c-returns-credits-refunds.md](processes/o2c-returns-credits-refunds.md) | Return, credit, and refund process explained step by step |
| [processes/p2p.md](processes/p2p.md) | Procure-to-pay process explained step by step |
| [processes/manual-journals-and-close.md](processes/manual-journals-and-close.md) | Recurring journal and close-cycle process explained step by step |
| [database-guide.md](database-guide.md) | Table families, key joins, and navigation patterns |
| [instructor-guide.md](instructor-guide.md) | Suggested teaching sequence and material mapping |

## Analytics Docs

| Document | What it covers |
|---|---|
| [analytics/index.md](analytics/index.md) | Analytics starter hub for SQL and Excel users |
| [analytics/financial.md](analytics/financial.md) | Financial accounting starter analytics |
| [analytics/managerial.md](analytics/managerial.md) | Managerial accounting starter analytics |
| [analytics/audit.md](analytics/audit.md) | Auditing starter analytics |
| [analytics/sql-guide.md](analytics/sql-guide.md) | How to run and adapt the starter SQL files |
| [analytics/excel-guide.md](analytics/excel-guide.md) | How to use the Excel workbook for analytics |

## Technical Docs

| Document | What it covers |
|---|---|
| [technical-guide.md](technical-guide.md) | System-level design guide for the current generator and dataset |
| [code-architecture.md](code-architecture.md) | Module-level explanation of the Python codebase |
| [reference/schema.md](reference/schema.md) | Implemented schema and key column patterns |
| [reference/posting.md](reference/posting.md) | Current posting logic and control-account behavior |
| [reference/row-volume.md](reference/row-volume.md) | Current default row counts versus historical design targets |
| [roadmap.md](roadmap.md) | Remaining roadmap and next planned implementation phase |

## Current Scope vs Future Scope

### Implemented in current generator

- five fiscal years from 2026 through 2030
- 31 tables across O2C, P2P, accounting core, master data, and planning
- returns, credit memos, refunds, receipt applications, and customer-credit behavior in O2C
- batched and matched multi-period P2P flows
- recurring manual journals, accrual reversals, and year-end close
- analytics starter docs, starter SQL packs, Excel workflow guidance, and exports

### Planned future extension

- manufacturing process coverage
- production accounting and manufacturing analytics

## Root-Level Entry Points

- [../README.md](../README.md): public landing page
- [../CONTRIBUTING.md](../CONTRIBUTING.md): contribution guidance
- [../LICENSE](../LICENSE): license terms
