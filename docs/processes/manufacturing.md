# Manufacturing Process

**Audience:** Students, instructors, analysts, and contributors who need to understand how production works in the current dataset.  
**Purpose:** Explain the manufacturing flow in plain language and connect it to the database tables and accounting entries.  
**What you will learn:** How Greenfield plans production, issues materials, captures labor, completes finished goods, closes work orders, and links manufacturing to purchasing, payroll, inventory, and the ledger.

> **Implemented in current generator:** Single-level BOMs, work centers, active routings, work-order operations, manufacturing work orders, material issues, production completions, work-order close, payroll-driven direct-labor integration, factory-overhead journals, manufacturing labor / overhead reclasses, and manufacturing variance accounting.

> **Planned future extension:** Capacity calendars, time clocks, shift detail, and richer production scheduling.

## Business Storyline

Greenfield does not manufacture every product it sells.

Instead, it produces a selected subset of furniture, lighting, and some textile items in-house. When customer demand and finished-goods buffers indicate a shortage, the manufacturing team releases work orders. Raw materials and packaging are issued to production, direct labor is traced from payroll time entries, completed finished goods move into inventory, and accounting closes the work order when actual and standard costs are fully resolved.

## Process Diagram

```mermaid
flowchart LR
    SO[Sales backlog and FG demand]
    PR[Material purchase requisitions]
    PO[Purchase orders]
    GR[Goods receipts]
    BOM[Bill of material]
    RT[Routing and work centers]
    WO[Work order]
    WOO[Work-order operations]
    MI[Material issue]
    LT[Labor time and payroll]
    PC[Production completion]
    WC[Work-order close]
    SH[Shipment]
    GL[GLEntry]

    SO --> WO
    BOM --> WO
    RT --> WO
    WO --> PR
    WO --> WOO
    PR --> PO --> GR --> MI
    WOO --> MI
    WOO --> LT
    MI --> PC
    LT --> PC
    PC --> WC
    PC --> SH
    MI --> GL
    PC --> GL
    WC --> GL
```

In plain language:

- customer demand helps determine when new production is needed
- BOMs define which components are required
- purchasing replenishes raw materials and packaging
- production issues components into WIP
- payroll and labor time provide actual labor input
- completed goods move into finished-goods inventory at standard cost
- work-order close pushes remaining material, labor, and overhead differences into manufacturing variance

## Step-by-Step Walkthrough

### 1. Define the standard recipe

Each manufactured finished good has one active BOM. The BOM lists raw-material and packaging components plus standard component quantities and scrap factors.

Main tables:

- `BillOfMaterial`
- `BillOfMaterialLine`
- `Item`

### 2. Define the routing and work centers

Each manufactured item also has one active routing. The routing breaks production into `2` to `4` ordered operations and assigns each operation to a work center such as cutting, assembly, finishing, packing, or selected quality checks.

Main tables:

- `WorkCenter`
- `Routing`
- `RoutingOperation`

### 3. Release a work order

Work orders are created for manufactured items when projected shortage exists after considering:

- open sales backlog
- available finished-goods inventory
- scheduled open completions
- a target finished-goods buffer

Main table:

- `WorkOrder`

At release time the generator also creates work-order operation rows for the routing sequence that item uses.

Main linked table:

- `WorkOrderOperation`

### 4. Replenish components through P2P

If the planned work order needs more materials than current stock supports, the generator creates purchasing demand through `PurchaseRequisition`. Those requisitions move through the normal P2P process into purchase orders and goods receipts.

Main linked tables:

- `PurchaseRequisition`
- `PurchaseOrder`
- `GoodsReceipt`

### 5. Issue components to production

When work begins, raw materials and packaging are issued from warehouse inventory into WIP.

Main tables:

- `MaterialIssue`
- `MaterialIssueLine`

Accounting event:

- debit `1046` Inventory - Work in Process
- credit `1045` Inventory - Materials and Packaging

### 6. Capture labor and overhead inputs

Manufacturing direct workers record `LaborTimeEntry` rows tied to both the work order and the specific work-order operation where labor was consumed. Payroll later turns those time entries into direct-labor and manufacturing-overhead reclass journals.

Main linked tables:

- `LaborTimeEntry`
- `PayrollRegister`
- `WorkOrderOperation`
- `JournalEntry`

### 7. Complete finished goods

Completed production moves finished goods into inventory at standard material plus standard direct labor plus standard variable and fixed overhead.

Main tables:

- `ProductionCompletion`
- `ProductionCompletionLine`

Accounting event:

- debit `1040` Inventory - Finished Goods
- credit `1046` Inventory - Work in Process
- credit `1090` Manufacturing Cost Clearing

### 8. Close the work order

When the generator determines the work order is ready to close, residual material, direct-labor, and overhead differences are closed to manufacturing variance.

Main table:

- `WorkOrderClose`

Accounting event:

- residual WIP and clearing balances move to `5080` Manufacturing Variance

### 9. Ship the completed goods

Once finished goods are in inventory, normal O2C shipments can consume them.

## Main Tables Involved

| Table | Role |
|---|---|
| `Item` | Identifies which sellable items are purchased versus manufactured and stores standard cost components |
| `BillOfMaterial` | BOM header for manufactured items |
| `BillOfMaterialLine` | BOM component detail |
| `WorkCenter` | Manufacturing resource group where an operation is performed |
| `Routing` | Active operation plan for a manufactured item |
| `RoutingOperation` | Ordered routing step with standard setup, run, and queue assumptions |
| `WorkOrder` | Production order for a manufactured item |
| `WorkOrderOperation` | Operation-level execution plan and actual start/end progression for a work order |
| `MaterialIssue` | Header for component issue to production |
| `MaterialIssueLine` | Component issue detail |
| `ProductionCompletion` | Header for finished-goods completion |
| `ProductionCompletionLine` | Finished-goods completion detail with cost components |
| `WorkOrderClose` | Variance close and work-order closure record |
| `LaborTimeEntry` | Direct and indirect labor detail that feeds manufacturing actuals |

## When Accounting Happens

Manufacturing creates both operational and journal-driven accounting:

- `MaterialIssue` posts WIP and materials inventory
- `ProductionCompletion` posts finished goods, WIP, and manufacturing clearing
- `WorkOrderClose` posts manufacturing variance
- recurring journals also include:
  - `Factory Overhead`
  - `Direct Labor Reclass`
  - `Manufacturing Overhead Reclass`

## Common Student Questions

- Which products are manufactured and which are purchased?
- What materials go into a manufactured item?
- Which operations and work centers are used for each manufactured item?
- How much direct labor is tied to each work order and operation?
- Which work centers look busiest by month?
- Which work orders stayed open at period end?
- How much material was issued compared with standard requirement?
- How much manufacturing variance was posted by month or item group?
- How do production activity and payroll affect finished-goods availability and margin analysis?

## Current Implementation Notes

- The current model is intentionally a foundation:
  - single-level BOMs only
  - no multi-level BOMs or subassemblies
  - no capacity calendars or formal finite scheduling
  - no time-clock or shift-attendance layer
- Manufacturing demand is linked to sales backlog and finished-goods inventory logic.
- Raw-material replenishment uses the existing P2P flow instead of a separate procurement subsystem.
- Manufacturing remains standard-cost based even though payroll now provides actual labor detail and direct labor is assigned at the operation level.

## Where to Go Next

- Read [payroll.md](payroll.md) to see how labor enters the manufacturing flow.
- Read [p2p.md](p2p.md) to see how materials enter inventory.
- Read [o2c.md](o2c.md) to see how finished goods leave inventory.
- Read [../reference/posting.md](../reference/posting.md) for the detailed accounting rules.
