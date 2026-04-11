# Instructor Guide

**Audience:** Instructors designing AIS, accounting analytics, audit analytics, or SQL/Excel coursework around the dataset.  
**Purpose:** Show how the dataset can be adopted as a teaching package and how the starter analytics layer fits into class delivery.  
**What you will learn:** A recommended teaching sequence, how to map learning goals to documents and query sets, and how to separate student-ready materials from instructor enrichment notes.

> **Implemented in current generator:** Five years of O2C, P2P, manufacturing, payroll, shift-assignment, and time-clock data, opening balances, recurring manual journals, year-end close, budgets, ledger postings, anomalies, and starter analytics materials for financial, managerial, and audit analytics.

> **Planned future extension:** Raw punch-event detail, rotating shift rosters, and shift-level workforce planning.

## How to Position the Dataset

This project works best when students need to connect:

- business process understanding
- relational data structure
- accounting logic
- SQL analysis
- Excel analysis
- audit-style reasoning

The dataset is especially strong when a course wants students to see that operational documents, payroll, subledgers, and financial reporting belong to one system rather than separate topics.

## Student-Ready Materials vs Instructor Enrichment

### Student-ready starter materials

Use these directly with students:

- [company-story.md](company-story.md)
- [dataset-overview.md](dataset-overview.md)
- [process-flows.md](process-flows.md)
- [processes/o2c.md](processes/o2c.md)
- [processes/o2c-returns-credits-refunds.md](processes/o2c-returns-credits-refunds.md)
- [processes/p2p.md](processes/p2p.md)
- [processes/manufacturing.md](processes/manufacturing.md)
- [processes/time-clocks.md](processes/time-clocks.md)
- [processes/payroll.md](processes/payroll.md)
- [processes/manual-journals-and-close.md](processes/manual-journals-and-close.md)
- [database-guide.md](database-guide.md)
- [analytics/index.md](analytics/index.md)
- [analytics/cases/index.md](analytics/cases/index.md)
- [analytics/financial.md](analytics/financial.md)
- [analytics/managerial.md](analytics/managerial.md)
- [analytics/audit.md](analytics/audit.md)
- [analytics/sql-guide.md](analytics/sql-guide.md)
- [analytics/excel-guide.md](analytics/excel-guide.md)
- `queries/financial/`
- `queries/managerial/`
- `queries/audit/`

### Instructor enrichment notes

Use these to frame the course and answer implementation questions:

- [technical-guide.md](technical-guide.md)
- [reference/schema.md](reference/schema.md)
- [reference/posting.md](reference/posting.md)
- [reference/row-volume.md](reference/row-volume.md)
- [code-architecture.md](code-architecture.md)
- [roadmap.md](roadmap.md)

## Recommended Multi-Week Teaching Sequence

| Week or module | Teaching goal | Main docs | Main starter assets |
|---|---|---|---|
| 1. Business orientation | Explain the company, scope, and why the dataset exists | [company-story.md](company-story.md), [dataset-overview.md](dataset-overview.md) | None yet |
| 2. Process mapping | Show O2C, returns, P2P, manufacturing, time clocks, payroll, and close-cycle flow | [process-flows.md](process-flows.md), [processes/o2c.md](processes/o2c.md), [processes/p2p.md](processes/p2p.md), [processes/manufacturing.md](processes/manufacturing.md), [processes/time-clocks.md](processes/time-clocks.md), [processes/payroll.md](processes/payroll.md) | None yet |
| 3. Exception paths | Show returns, credits, refunds, attendance exceptions, payroll liability clearance, and manual journal activity | [processes/o2c-returns-credits-refunds.md](processes/o2c-returns-credits-refunds.md), [processes/time-clocks.md](processes/time-clocks.md), [processes/payroll.md](processes/payroll.md), [processes/manual-journals-and-close.md](processes/manual-journals-and-close.md) | None yet |
| 4. Table navigation and joins | Teach keys, header-line patterns, and traceability | [database-guide.md](database-guide.md) | Introductory ad hoc joins |
| 5. Source-to-ledger bridge | Show how operational activity becomes accounting data | [reference/posting.md](reference/posting.md) | Ledger-oriented examples |
| 6. Financial analytics | Teach revenue, AR, AP, payroll liabilities, trial balance, and close cycle | [analytics/financial.md](analytics/financial.md) | `queries/financial/` |
| 7. Managerial analytics | Teach budgeting, cost centers, sales mix, product cost, labor, inventory movement, BOMs, and work-order behavior | [analytics/managerial.md](analytics/managerial.md) | `queries/managerial/` |
| 8. Audit analytics | Teach completeness, approvals, cut-off, duplicates, manufacturing controls, payroll controls, and exception logic | [analytics/audit.md](analytics/audit.md) | `queries/audit/` |
| 9. Guided walkthroughs | Pair one business scenario with a small sequence of starter queries and workbook checks | [analytics/cases/index.md](analytics/cases/index.md) | case docs plus topic query packs |
| 10. Anomaly-focused work | Move from clean analysis to exception-oriented work | [analytics/audit.md](analytics/audit.md), [analytics/excel-guide.md](analytics/excel-guide.md), [analytics/cases/audit-exception-lab.md](analytics/cases/audit-exception-lab.md) | `AnomalyLog`, `ValidationSummary`, audit query pack |

This sequence can be compressed into fewer weeks or expanded into several assignments. The important sequencing rule is: process understanding first, analytics second.

## Learning Objective Map

| Learning objective | Best starting docs | Best starter SQL set | Best Excel path |
|---|---|---|---|
| Understand the company and business model | [company-story.md](company-story.md), [dataset-overview.md](dataset-overview.md) | None required | Workbook orientation |
| Understand the business cycles | [process-flows.md](process-flows.md), [processes/o2c.md](processes/o2c.md), [processes/p2p.md](processes/p2p.md), [processes/payroll.md](processes/payroll.md) | None required | Process walkthrough in workbook sheets |
| Learn the table structure | [database-guide.md](database-guide.md) | Any topic folder | Sheet-by-sheet workbook tour |
| Trace source documents to postings | [reference/posting.md](reference/posting.md) | Financial and audit packs | `GLEntry` plus source-document sheets |
| Analyze revenue, AR, AP, journals, and payroll liabilities | [analytics/financial.md](analytics/financial.md) | `queries/financial/` | Financial section in [analytics/excel-guide.md](analytics/excel-guide.md) |
| Analyze budgets, mix, labor, and operations | [analytics/managerial.md](analytics/managerial.md) | `queries/managerial/` | Managerial section in [analytics/excel-guide.md](analytics/excel-guide.md) |
| Analyze controls and anomalies | [analytics/audit.md](analytics/audit.md) | `queries/audit/` | Audit section in [analytics/excel-guide.md](analytics/excel-guide.md) |

## How the Dataset Supports SQL and Excel

### SQL use

The current dataset works well for:

- joins across headers and lines
- aggregation by month, customer, supplier, item, cost center, pay period, and work order
- subledger-to-ledger reconciliation
- exception detection using dates, approvals, duplicate references, and missing linkages
- trend analysis across five fiscal years

### Excel use

The current workbook works well for:

- pivots by month, customer segment, supplier category, account, cost center, and pay period
- shift adherence and overtime analysis by work center and month
- budget-versus-actual analysis
- aging views for receivables and payables
- payroll cash-flow and liability analysis
- anomaly review using `AnomalyLog`
- charting seasonality, mix, timing gaps, and manufacturing variance

## Topic Coverage by Area

### Financial accounting

Use the starter layer for:

- monthly revenue and gross margin
- AR aging
- AP aging
- trial balance logic
- journal-entry review
- close-cycle analysis
- control-account reconciliation
- payroll liability roll-forward
- gross-to-net payroll review

### Managerial accounting

Use the starter layer for:

- budget vs actual
- cost center expense behavior
- customer and product mix
- inventory movement
- supplier and category spend
- simple profitability analysis
- BOM cost rollup
- work-order throughput
- direct labor by work order
- unit-cost bridges
- absorption-margin versus contribution-margin analysis
- labor rate and efficiency variance
- manufacturing variance review

### Auditing

Use the starter layer for:

- O2C and P2P completeness testing
- approval and segregation-of-duties checks
- cut-off and timing analysis
- duplicate payment or invoice reference review
- anomaly-focused exercises
- BOM integrity and work-order close review
- payroll-control and labor-time exception review

## Clean Dataset vs Anomaly-Enabled Dataset

- For baseline process and accounting teaching, a clean build with `anomaly_mode: none` is useful.
- For auditing and controls exercises, `config/settings.yaml` is usually the best starting point.
- Make the distinction explicit to students. Some audit starter queries may return no rows on a clean build, and that is expected.

## Recommended Build Pairing

- Use `config/settings_validation.yaml` when you want a fast clean baseline for instructor prep.
- Use `config/settings.yaml` when you want the standard five-year anomaly-enabled build for starter analytics, walkthroughs, and audit labs.
- If you want a narrower classroom exercise, filter the default SQLite or Excel outputs to a single year instead of generating a separate teaching-only config.

## Teaching Notes

- Start with process understanding before asking students to write joins.
- Use the company story to explain why each document exists before discussing its table structure.
- Use `GLEntry` only after students understand which source events post and which do not.
- Teach the distinction between:
  - clean baseline analysis
  - anomaly-enabled exception analysis
- If you want raw multi-year income-statement activity, have students exclude the two year-end close entry types from `JournalEntry`.
- If you want the simplest student onboarding path, begin from the starter SQL files rather than from blank query prompts.

## What to Avoid Teaching as If It Already Exists

The current dataset does **not** yet include:

- raw punch-event tables beneath the current approved daily time-clock rows
- rotating shift rosters or shift-level capacity calendars

These are future expansion areas, not hidden parts of the current model.

## Where to Go Next

- Read [analytics/index.md](analytics/index.md) for the starter analytics hub.
- Read [code-architecture.md](code-architecture.md) if assistants or contributors need to understand how the generator is built.
