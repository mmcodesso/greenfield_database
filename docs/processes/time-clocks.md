# Time Clocks and Shift Labor

## Business Storyline

Charles River models time and attendance as the bridge between workforce planning and payroll. Supervisors define the expected shift pattern, hourly employees work against those expectations, and the approved daily clock becomes the support for both payroll hours and labor analysis.

This page is about the workforce side of the story: when employees were expected to work, when they actually worked, how overtime appears, how direct manufacturing time can be tied to a work-order operation, and where attendance exceptions show up. The actual pay cycle is covered on the separate [Payroll](payroll.md) page.

## Process Diagram

```mermaid
flowchart LR
    SD[ShiftDefinition]
    ESA[EmployeeShiftAssignment]
    ESR[EmployeeShiftRoster]
    ABS[EmployeeAbsence]
    TCP[TimeClockPunch]
    OTA[OvertimeApproval]
    TCE[TimeClockEntry]
    AE[AttendanceException]
    LTE[LaborTimeEntry]
    WOO[WorkOrderOperation]
    PR[PayrollRegister]
    PRL[PayrollRegisterLine]
    PAY[PayrollPayment]
    REM[PayrollLiabilityRemittance]
    GL[GLEntry]

    SD --> ESA
    ESA --> ESR
    ESR --> ABS
    ESR --> TCP
    ESR --> TCE
    OTA --> TCE
    TCP --> TCE
    WOO --> TCE
    TCE --> LTE
    TCE --> PR
    TCE --> AE
    LTE --> PRL
    PR --> PRL
    PR --> PAY
    PR --> REM
    PR --> GL
    PAY --> GL
    REM --> GL
```

Read the diagram from workforce planning to approved attendance and then to downstream use. Time clocks support payroll, labor tracing, overtime analysis, manufacturing support, and control testing.

## Step-by-Step Walkthrough

### 1. Define the shift structure

Charles River starts by defining standard shifts for areas such as manufacturing, warehouse, and customer service. Those shift definitions tell students what "on time" and "normal hours" are supposed to look like.

Main table:

- `ShiftDefinition`

### 2. Assign hourly employees to a primary shift

Each hourly employee receives one primary active assignment. In some cases the assignment also ties the employee to a work center, which matters later for manufacturing and overtime analysis.

Main table:

- `EmployeeShiftAssignment`

### 3. Build the daily shift roster

Charles River now adds a daily planned roster beneath the approved daily time summary. The roster tells students who was supposed to work, on which date, in which work center, and for how many scheduled hours.

Main table:

- `EmployeeShiftRoster`

### 4. Capture absences and overtime approvals

The dataset now separates planned-shift exceptions from worked-time records:

- `EmployeeAbsence` records planned absence from the roster
- `OvertimeApproval` records approved overtime support when worked hours exceed the planned shift

Main tables:

- `EmployeeAbsence`
- `OvertimeApproval`

### 5. Record raw punches and derive approved daily time clocks

For each worked day, Charles River now records raw badge-style punches first. Those punches roll up into one approved `TimeClockEntry` row that captures the daily attendance summary:

- `Clock In`
- `Meal Start`
- `Meal End`
- `Clock Out`

The approved daily summary then carries:

- `ClockInTime`
- `ClockOutTime`
- `BreakMinutes`
- `RegularHours`
- `OvertimeHours`

For direct manufacturing workers, the same daily clock can also point to:

- `WorkOrderID`
- `WorkOrderOperationID`

Main table:

- `TimeClockPunch`
- `TimeClockEntry`

### 6. Link approved attendance to labor support

Approved attendance does not stay isolated in the time-clock table. It feeds `LaborTimeEntry`, where direct manufacturing labor can be tied back to the work order, the routing operation, and the supporting time-clock row.

Main table:

- `LaborTimeEntry`

### 7. Use attendance for payroll and costing

Payroll uses approved clock hours as the source for hourly earnings, while manufacturing uses the same support to trace labor into product-cost analysis. Salaried employees remain outside the routine time-clock flow.

Main downstream tables:

- `PayrollRegister`
- `PayrollRegisterLine`

### 8. Review exceptions

Attendance review can surface issues such as:

- missing clock-out
- duplicate time-clock day
- off-shift clocking
- paid without approved clock support
- labor booked after operation close

Main table:

- `AttendanceException`

## Main Tables in This Process

| Table | Role |
|---|---|
| `ShiftDefinition` | Standard shift template |
| `EmployeeShiftAssignment` | Employee-to-shift assignment |
| `EmployeeShiftRoster` | Daily planned work schedule for hourly employees |
| `EmployeeAbsence` | Planned absence tied to the rostered shift |
| `TimeClockPunch` | Raw attendance punch event |
| `OvertimeApproval` | Approval support for worked overtime |
| `TimeClockEntry` | Approved daily attendance row for hourly employees |
| `AttendanceException` | Logged time-and-attendance issues used for control review |
| `LaborTimeEntry` | Labor allocation record used for costing and payroll traceability |
| `WorkOrderOperation` | Operation-level production link for direct labor |
| `PayrollRegister` | Downstream payroll header that uses approved clock hours for hourly pay |
| `PayrollRegisterLine` | Downstream earnings and deduction detail |

## When Accounting Happens

Time clocks and shift assignments do **not** post directly to the ledger.

They affect accounting indirectly by driving:

- hourly earnings on `PayrollRegister`
- direct labor and overtime analysis
- payroll-control validation
- manufacturing labor reclass logic through `LaborTimeEntry`

The posting events happen later in the payroll process:

- `PayrollRegister`
- related payroll settlements and remittances described on [Payroll](payroll.md)

## Common Student Questions

- Which employees are hourly and therefore expected to have time clocks?
- How close are actual clock-in times to the assigned shift start?
- How much overtime is concentrated in each work center and month?
- Which time-clock rows support direct manufacturing labor?
- How do approved clock hours relate to paid hourly earnings?
- Which attendance issues should be treated as control exceptions?

## What to Notice in the Data

- The published dataset includes raw `TimeClockPunch` rows beneath the approved daily `TimeClockEntry`.
- Salaried employees generally do not receive routine time-clock rows.
- Hourly payroll earnings use approved time-clock hours as the source for regular and overtime pay.
- Direct manufacturing time clocks can link to `WorkOrderOperationID`, which makes operation-level labor analytics possible.
- Daily roster rows make it possible to compare scheduled hours to worked hours, absence hours, and overtime approvals.
- Attendance exceptions support control review and exception analysis.

## Subprocess Spotlight: Shift Expectation to Approved Hours

```mermaid
flowchart LR
    SD[ShiftDefinition]
    ESA[EmployeeShiftAssignment]
    ESR[EmployeeShiftRoster]
    TCP[TimeClockPunch]
    TCE[TimeClockEntry]
    LTE[LaborTimeEntry]
    PR[PayrollRegister]
    OTA[OvertimeApproval]
    AE[AttendanceException]

    SD --> ESA --> ESR --> TCP --> TCE --> LTE
    ESR --> OTA --> TCE
    TCE --> PR
    TCE --> AE
```

This view highlights the main learning path on this page:

- shifts define the expected work pattern
- rosters define who was scheduled to work that day
- punches show the raw attendance sequence
- approved time clocks show the summarized worked day
- labor support carries that attendance into costing
- payroll later uses the approved hours for hourly earnings
- exception analysis sits beside the normal flow as a control lens

## Where to Go Next

- Read [Payroll](payroll.md) for the pay-cycle view of the same labor support.
- Read [Manufacturing](manufacturing.md) for the production side of direct labor.
- Read [Managerial Analytics](../analytics/managerial.md) and [Audit Analytics](../analytics/audit.md) for starter time-clock analysis.
