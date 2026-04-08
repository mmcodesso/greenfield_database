# Documentation Index

This page is the main navigation hub for the Greenfield Accounting Dataset Generator documentation.

The project has two documentation layers:

- **Course-user documentation** for students, instructors, and analysts
- **Technical reference documentation** for contributors and maintainers

## Start Here by Audience

| If you are a... | Read this first | Then continue with |
|---|---|---|
| Student | [dataset-overview.md](dataset-overview.md) | [process-flows.md](process-flows.md), [database-guide.md](database-guide.md) |
| Instructor | [instructor-guide.md](instructor-guide.md) | [process-flows.md](process-flows.md), [database-guide.md](database-guide.md) |
| Analyst | [database-guide.md](database-guide.md) | [reference/schema.md](reference/schema.md), [reference/posting.md](reference/posting.md) |
| Contributor | [code-architecture.md](code-architecture.md) | [reference/schema.md](reference/schema.md), [reference/posting.md](reference/posting.md), [reference/row-volume.md](reference/row-volume.md) |

## Course-User Documentation

| Document | What it covers |
|---|---|
| [dataset-overview.md](dataset-overview.md) | What the dataset is, why it exists, and the main glossary terms |
| [process-flows.md](process-flows.md) | O2C, P2P, and subledger-to-ledger traceability with diagrams |
| [database-guide.md](database-guide.md) | Table families, key joins, and where to start for financial, managerial, and audit analytics |
| [instructor-guide.md](instructor-guide.md) | Suggested teaching sequence and exercise categories |
| [code-architecture.md](code-architecture.md) | How the generator works end to end |

## Technical Reference

| Document | What it covers |
|---|---|
| [reference/schema.md](reference/schema.md) | Implemented schema and key column patterns |
| [reference/posting.md](reference/posting.md) | Current posting logic and control-account behavior |
| [reference/row-volume.md](reference/row-volume.md) | Current default row counts versus design-intent ranges |
| [roadmap.md](roadmap.md) | Next implementation phase and the remaining roadmap |

## Historical Appendix

| Document | What it covers |
|---|---|
| [../Design.md](../Design.md) | Original long-form blueprint and historical design notes; includes future ideas that do not always match the current generator |

## Current Scope vs Future Scope

### Implemented in current generator

- Five-year dataset from 2026 through 2030
- Order-to-cash and procure-to-pay transaction generation
- Opening balances, recurring manual journals, year-end close, and budgets
- Event-based postings into `GLEntry`
- Validation outputs, anomaly injection, and exports

### Planned future extension

- Analytics starter assets and teaching examples
- Manufacturing process coverage
- Broader O2C and inventory behavior

## Root-Level Entry Points

- [../README.md](../README.md): public landing page and quick start
- [../CONTRIBUTING.md](../CONTRIBUTING.md): contribution guidance
- [../LICENSE](../LICENSE): license terms
