from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.settings import GenerationContext
from greenfield_dataset.utils import money, next_id


def fiscal_years(context: GenerationContext) -> list[int]:
    start = pd.Timestamp(context.settings.fiscal_year_start).year
    end = pd.Timestamp(context.settings.fiscal_year_end).year
    return list(range(int(start), int(end) + 1))


def load_anomaly_profile(
    context: GenerationContext,
    profile_path: str | Path = "config/anomaly_profile.yaml",
) -> dict[str, Any]:
    path = Path(profile_path)
    if not path.exists():
        return {"enabled": False}

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    mode = context.settings.anomaly_mode or raw.get("mode", "none")
    return raw.get("profiles", {}).get(mode, {"enabled": False})


def log_anomaly(
    context: GenerationContext,
    anomaly_type: str,
    table_name: str,
    primary_key_value: int,
    fiscal_year: int,
    description: str,
    expected_detection_test: str,
) -> None:
    context.anomaly_log.append({
        "anomaly_type": anomaly_type,
        "table_name": table_name,
        "primary_key_value": int(primary_key_value),
        "fiscal_year": int(fiscal_year),
        "description": description,
        "expected_detection_test": expected_detection_test,
    })


def rows_for_year(df: pd.DataFrame, date_column: str, year: int) -> pd.DataFrame:
    if df.empty or date_column not in df.columns:
        return df.head(0)
    dates = pd.to_datetime(df[date_column], errors="coerce")
    return df[dates.dt.year.eq(year)]


def first_saturday(year: int) -> str:
    day = pd.Timestamp(year=year, month=1, day=1)
    while day.day_name() != "Saturday":
        day = day + pd.Timedelta(days=1)
    return day.strftime("%Y-%m-%d")


def used_primary_keys(
    context: GenerationContext,
    table_name: str,
    anomaly_type: str | None = None,
) -> set[int]:
    return {
        int(entry["primary_key_value"])
        for entry in context.anomaly_log
        if entry["table_name"] == table_name and (anomaly_type is None or entry["anomaly_type"] == anomaly_type)
    }


def invalidate_all_caches(context: GenerationContext) -> None:
    for attribute_name in list(vars(context)):
        if attribute_name.startswith("_"):
            delattr(context, attribute_name)


def compose_timestamp(new_date: str, original_value: object, default_time: str) -> str | None:
    if pd.isna(original_value):
        return None

    text = str(original_value)
    time_part = text.split(" ", 1)[1] if " " in text else default_time
    return f"{new_date} {time_part}"


def update_journal_posting_date(context: GenerationContext, journal_entry_id: int, posting_date: str) -> None:
    posting_timestamp = pd.Timestamp(posting_date)
    journal_mask = context.tables["JournalEntry"]["JournalEntryID"].astype(int).eq(int(journal_entry_id))
    journal_rows = context.tables["JournalEntry"].loc[journal_mask]
    if journal_rows.empty:
        return

    created_date = journal_rows.iloc[0]["CreatedDate"]
    approved_date = journal_rows.iloc[0]["ApprovedDate"]
    context.tables["JournalEntry"].loc[journal_mask, "PostingDate"] = posting_date
    context.tables["JournalEntry"].loc[journal_mask, "CreatedDate"] = compose_timestamp(posting_date, created_date, "08:00:00")
    context.tables["JournalEntry"].loc[journal_mask, "ApprovedDate"] = compose_timestamp(posting_date, approved_date, "09:00:00")

    gl_mask = (
        context.tables["GLEntry"]["SourceDocumentType"].eq("JournalEntry")
        & context.tables["GLEntry"]["SourceDocumentID"].astype(int).eq(int(journal_entry_id))
    )
    if not gl_mask.any():
        return

    created_dates = context.tables["GLEntry"].loc[gl_mask, "CreatedDate"]
    context.tables["GLEntry"].loc[gl_mask, "PostingDate"] = posting_date
    context.tables["GLEntry"].loc[gl_mask, "FiscalYear"] = int(posting_timestamp.year)
    context.tables["GLEntry"].loc[gl_mask, "FiscalPeriod"] = int(posting_timestamp.month)
    context.tables["GLEntry"].loc[gl_mask, "CreatedDate"] = created_dates.apply(
        lambda value: compose_timestamp(posting_date, value, "08:00:00")
    )


def append_attendance_exception(
    context: GenerationContext,
    employee_id: int,
    payroll_period_id: int,
    work_date: str,
    shift_definition_id: int | None,
    time_clock_entry_id: int | None,
    exception_type: str,
    severity: str,
    minutes_variance: float,
) -> None:
    row = {
        "AttendanceExceptionID": next_id(context, "AttendanceException"),
        "EmployeeID": int(employee_id),
        "PayrollPeriodID": int(payroll_period_id),
        "WorkDate": str(work_date),
        "ShiftDefinitionID": shift_definition_id,
        "TimeClockEntryID": time_clock_entry_id,
        "ExceptionType": exception_type,
        "Severity": severity,
        "MinutesVariance": money(minutes_variance),
        "Status": "Open",
        "ReviewedByEmployeeID": None,
        "ReviewedDate": None,
    }
    new_rows = pd.DataFrame([row], columns=TABLE_COLUMNS["AttendanceException"])
    context.tables["AttendanceException"] = pd.concat(
        [context.tables["AttendanceException"], new_rows],
        ignore_index=True,
    )


def journal_entries_for_year(
    context: GenerationContext,
    year: int,
    *,
    entry_types: set[str] | None = None,
    exclude_used: bool = False,
) -> pd.DataFrame:
    journal_entries = rows_for_year(context.tables["JournalEntry"], "PostingDate", year)
    if entry_types is not None:
        journal_entries = journal_entries[journal_entries["EntryType"].isin(entry_types)]
    if exclude_used:
        used_ids = used_primary_keys(context, "JournalEntry")
        if used_ids:
            journal_entries = journal_entries[~journal_entries["JournalEntryID"].astype(int).isin(used_ids)]
    return journal_entries.sort_values(["PostingDate", "JournalEntryID"]).reset_index(drop=True)


def journal_gl_rows(context: GenerationContext, journal_entry_id: int) -> pd.DataFrame:
    gl = context.tables["GLEntry"]
    return gl[
        gl["SourceDocumentType"].eq("JournalEntry")
        & gl["SourceDocumentID"].astype(int).eq(int(journal_entry_id))
    ].copy()


def inject_weekend_journal_entries(context: GenerationContext, count_per_year: int) -> None:
    if context.tables["JournalEntry"].empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        selected = journal_entries_for_year(context, year).head(count_per_year)
        for row in selected.itertuples(index=False):
            weekend_date = first_saturday(year)
            mask = context.tables["JournalEntry"]["JournalEntryID"].astype(int).eq(int(row.JournalEntryID))
            context.tables["JournalEntry"].loc[mask, "CreatedDate"] = f"{weekend_date} 10:00:00"
            context.tables["JournalEntry"].loc[mask, "ApprovedDate"] = f"{weekend_date} 11:00:00"
            log_anomaly(
                context,
                "weekend_journal_entry",
                "JournalEntry",
                int(row.JournalEntryID),
                year,
                f"Journal entry created and approved on Saturday {weekend_date}.",
                "Weekend journal entry query using CreatedDate or ApprovedDate.",
            )


def inject_same_creator_approver(context: GenerationContext, count_per_year: int) -> None:
    purchase_orders = context.tables["PurchaseOrder"]
    if purchase_orders.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        selected = rows_for_year(purchase_orders, "OrderDate", year).head(count_per_year)
        for row in selected.itertuples(index=False):
            mask = context.tables["PurchaseOrder"]["PurchaseOrderID"].astype(int).eq(int(row.PurchaseOrderID))
            context.tables["PurchaseOrder"].loc[mask, "ApprovedByEmployeeID"] = int(row.CreatedByEmployeeID)
            log_anomaly(
                context,
                "same_creator_approver",
                "PurchaseOrder",
                int(row.PurchaseOrderID),
                year,
                "Purchase order creator also appears as approver.",
                "Creator-versus-approver segregation of duties query.",
            )


def inject_same_creator_approver_journals(context: GenerationContext, count_per_year: int) -> None:
    if context.tables["JournalEntry"].empty or count_per_year <= 0:
        return

    candidate_types = {
        "Rent",
        "Utilities",
        "Factory Overhead",
        "Direct Labor Reclass",
        "Manufacturing Overhead Reclass",
        "Depreciation",
        "Accrual",
        "Accrual Adjustment",
    }
    for year in fiscal_years(context):
        selected = journal_entries_for_year(
            context,
            year,
            entry_types=candidate_types,
            exclude_used=True,
        ).head(count_per_year)
        for row in selected.itertuples(index=False):
            mask = context.tables["JournalEntry"]["JournalEntryID"].astype(int).eq(int(row.JournalEntryID))
            context.tables["JournalEntry"].loc[mask, "ApprovedByEmployeeID"] = int(row.CreatedByEmployeeID)
            log_anomaly(
                context,
                "same_creator_approver_journal",
                "JournalEntry",
                int(row.JournalEntryID),
                year,
                "Manual journal creator also appears as approver.",
                "Segregation of duties query on JournalEntry creator and approver.",
            )


def inject_missing_approvals(context: GenerationContext, count_per_year: int) -> None:
    requisitions = context.tables["PurchaseRequisition"]
    if requisitions.empty or count_per_year <= 0:
        return

    converted = requisitions[requisitions["Status"].eq("Converted to PO")]
    for year in fiscal_years(context):
        selected = rows_for_year(converted, "RequestDate", year).head(count_per_year)
        for row in selected.itertuples(index=False):
            mask = context.tables["PurchaseRequisition"]["RequisitionID"].astype(int).eq(int(row.RequisitionID))
            context.tables["PurchaseRequisition"].loc[mask, "ApprovedByEmployeeID"] = None
            context.tables["PurchaseRequisition"].loc[mask, "ApprovedDate"] = None
            log_anomaly(
                context,
                "missing_approval",
                "PurchaseRequisition",
                int(row.RequisitionID),
                year,
                "Converted requisition has missing approval fields.",
                "Converted requisitions with null ApprovedByEmployeeID or ApprovedDate.",
            )


def inject_missing_reversal_links(context: GenerationContext, count_per_year: int) -> None:
    if context.tables["JournalEntry"].empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        selected = journal_entries_for_year(context, year, entry_types={"Accrual Adjustment"})
        used_ids = used_primary_keys(context, "JournalEntry", "missing_reversal_link")
        if used_ids:
            selected = selected[~selected["JournalEntryID"].astype(int).isin(used_ids)]
        selected = selected.head(count_per_year)
        for row in selected.itertuples(index=False):
            mask = context.tables["JournalEntry"]["JournalEntryID"].astype(int).eq(int(row.JournalEntryID))
            context.tables["JournalEntry"].loc[mask, "ReversesJournalEntryID"] = None
            log_anomaly(
                context,
                "missing_reversal_link",
                "JournalEntry",
                int(row.JournalEntryID),
                year,
                "Accrual adjustment is missing its link to the original accrual journal.",
                "Accrual adjustments with null ReversesJournalEntryID.",
            )


def inject_invoice_before_shipment(context: GenerationContext, count_per_year: int) -> None:
    invoices = context.tables["SalesInvoice"]
    shipments = context.tables["Shipment"]
    if invoices.empty or shipments.empty or count_per_year <= 0:
        return

    shipment_by_order = shipments.sort_values("ShipmentDate").drop_duplicates("SalesOrderID").set_index("SalesOrderID")
    for year in fiscal_years(context):
        selected = rows_for_year(invoices, "InvoiceDate", year)
        injected = 0
        for row in selected.itertuples(index=False):
            if injected >= count_per_year or int(row.SalesOrderID) not in shipment_by_order.index:
                continue

            shipment_date = pd.Timestamp(shipment_by_order.loc[int(row.SalesOrderID), "ShipmentDate"])
            invoice_date = shipment_date - pd.Timedelta(days=2)
            due_date = invoice_date + (pd.Timestamp(row.DueDate) - pd.Timestamp(row.InvoiceDate))
            mask = context.tables["SalesInvoice"]["SalesInvoiceID"].astype(int).eq(int(row.SalesInvoiceID))
            context.tables["SalesInvoice"].loc[mask, "InvoiceDate"] = invoice_date.strftime("%Y-%m-%d")
            context.tables["SalesInvoice"].loc[mask, "DueDate"] = due_date.strftime("%Y-%m-%d")
            log_anomaly(
                context,
                "invoice_before_shipment",
                "SalesInvoice",
                int(row.SalesInvoiceID),
                year,
                "Sales invoice date intentionally precedes related shipment date.",
                "Invoice date before earliest shipment date by sales order.",
            )
            injected += 1


def inject_late_reversals(context: GenerationContext, count_per_year: int) -> None:
    if context.tables["JournalEntry"].empty or count_per_year <= 0:
        return

    journal_entries = context.tables["JournalEntry"]
    for year in fiscal_years(context):
        reversals = journal_entries[
            pd.to_datetime(journal_entries["PostingDate"]).dt.year.eq(year)
            & journal_entries["EntryType"].eq("Accrual Adjustment")
            & journal_entries["ReversesJournalEntryID"].notna()
        ].sort_values(["PostingDate", "JournalEntryID"])
        used_ids = used_primary_keys(context, "JournalEntry", "late_reversal")
        if used_ids:
            reversals = reversals[~reversals["JournalEntryID"].astype(int).isin(used_ids)]

        for row in reversals.head(count_per_year).itertuples(index=False):
            current_date = pd.Timestamp(row.PostingDate)
            delayed_date = current_date + pd.Timedelta(days=5)
            while delayed_date.day_name() in {"Saturday", "Sunday"}:
                delayed_date = delayed_date + pd.Timedelta(days=1)

            update_journal_posting_date(context, int(row.JournalEntryID), delayed_date.strftime("%Y-%m-%d"))
            log_anomaly(
                context,
                "late_reversal",
                "JournalEntry",
                int(row.JournalEntryID),
                year,
                "Accrual adjustment posting date was moved later than the intended cleanup window.",
                "Accrual adjustment journals posted later than their clean-build timing.",
            )


def inject_duplicate_vendor_payment_reference(context: GenerationContext, count_per_year: int) -> None:
    payments = context.tables["DisbursementPayment"]
    if len(payments) < 2 or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        year_payments = rows_for_year(payments, "PaymentDate", year).copy()
        if len(year_payments) < 2:
            continue
        used_ids = used_primary_keys(context, "DisbursementPayment", "duplicate_vendor_payment_reference")
        if used_ids:
            year_payments = year_payments[~year_payments["DisbursementID"].astype(int).isin(used_ids)]
        injected = 0
        for _, supplier_rows in year_payments.groupby("SupplierID", sort=True):
            supplier_rows = supplier_rows.sort_values(["PaymentDate", "DisbursementID"])
            if len(supplier_rows) < 2:
                continue

            first_payment = supplier_rows.iloc[0]
            duplicate_reference = first_payment["CheckNumber"] or first_payment["PaymentNumber"]
            first_mask = context.tables["DisbursementPayment"]["DisbursementID"].astype(int).eq(int(first_payment["DisbursementID"]))
            context.tables["DisbursementPayment"].loc[first_mask, "CheckNumber"] = duplicate_reference
            duplicate_row = supplier_rows.iloc[1]
            mask = context.tables["DisbursementPayment"]["DisbursementID"].astype(int).eq(int(duplicate_row["DisbursementID"]))
            context.tables["DisbursementPayment"].loc[mask, "PaymentMethod"] = first_payment["PaymentMethod"]
            context.tables["DisbursementPayment"].loc[mask, "CheckNumber"] = duplicate_reference
            log_anomaly(
                context,
                "duplicate_vendor_payment_reference",
                "DisbursementPayment",
                int(duplicate_row["DisbursementID"]),
                year,
                "Vendor payment shares a duplicate check reference with another payment for the same supplier.",
                "Duplicate supplier payment reference review by SupplierID and CheckNumber.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_duplicate_supplier_invoice_number(context: GenerationContext, count_per_year: int) -> None:
    invoices = context.tables["PurchaseInvoice"]
    if len(invoices) < 2 or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        year_invoices = rows_for_year(invoices, "InvoiceDate", year).copy()
        if len(year_invoices) < 2:
            continue
        used_ids = used_primary_keys(context, "PurchaseInvoice", "duplicate_supplier_invoice_number")
        if used_ids:
            year_invoices = year_invoices[~year_invoices["PurchaseInvoiceID"].astype(int).isin(used_ids)]
        injected = 0
        for _, supplier_rows in year_invoices.groupby("SupplierID", sort=True):
            supplier_rows = supplier_rows.sort_values(["InvoiceDate", "PurchaseInvoiceID"])
            if len(supplier_rows) < 2:
                continue

            first_invoice = supplier_rows.iloc[0]
            duplicate_row = supplier_rows.iloc[1]
            mask = context.tables["PurchaseInvoice"]["PurchaseInvoiceID"].astype(int).eq(int(duplicate_row["PurchaseInvoiceID"]))
            context.tables["PurchaseInvoice"].loc[mask, "InvoiceNumber"] = str(first_invoice["InvoiceNumber"])
            log_anomaly(
                context,
                "duplicate_supplier_invoice_number",
                "PurchaseInvoice",
                int(duplicate_row["PurchaseInvoiceID"]),
                year,
                "Supplier invoice number was duplicated within the same supplier account.",
                "Duplicate supplier invoice number review by SupplierID and InvoiceNumber.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_missing_payroll_payment(context: GenerationContext, count_per_year: int) -> None:
    registers = context.tables["PayrollRegister"]
    payments = context.tables["PayrollPayment"]
    if registers.empty or payments.empty or count_per_year <= 0:
        return

    payment_counts = payments.groupby("PayrollRegisterID").size()
    for year in fiscal_years(context):
        year_registers = rows_for_year(registers, "ApprovedDate", year).copy()
        year_registers = year_registers[
            year_registers["Status"].eq("Approved")
            & year_registers["ApprovedDate"].notna()
            & year_registers["PayrollRegisterID"].astype(int).isin(payment_counts.index.astype(int))
        ]
        used_ids = used_primary_keys(context, "PayrollRegister", "missing_payroll_payment")
        if used_ids:
            year_registers = year_registers[~year_registers["PayrollRegisterID"].astype(int).isin(used_ids)]
        for row in year_registers.head(count_per_year).itertuples(index=False):
            context.tables["PayrollPayment"] = context.tables["PayrollPayment"][
                ~context.tables["PayrollPayment"]["PayrollRegisterID"].astype(int).eq(int(row.PayrollRegisterID))
            ].reset_index(drop=True)
            log_anomaly(
                context,
                "missing_payroll_payment",
                "PayrollRegister",
                int(row.PayrollRegisterID),
                year,
                "Approved payroll register no longer has a supporting payroll payment row.",
                "Payroll control review for approved payroll registers missing payment.",
            )


def inject_payroll_payment_before_approval(context: GenerationContext, count_per_year: int) -> None:
    registers = context.tables["PayrollRegister"]
    payments = context.tables["PayrollPayment"]
    if registers.empty or payments.empty or count_per_year <= 0:
        return

    payment_lookup = payments.groupby("PayrollRegisterID").size()
    for year in fiscal_years(context):
        year_registers = rows_for_year(registers, "ApprovedDate", year).copy()
        year_registers = year_registers[
            year_registers["Status"].eq("Approved")
            & year_registers["ApprovedDate"].notna()
            & year_registers["PayrollRegisterID"].astype(int).isin(payment_lookup.index.astype(int))
        ]
        used_ids = used_primary_keys(context, "PayrollPayment", "payroll_payment_before_approval")
        injected = 0
        for row in year_registers.itertuples(index=False):
            payment_rows = context.tables["PayrollPayment"][
                context.tables["PayrollPayment"]["PayrollRegisterID"].astype(int).eq(int(row.PayrollRegisterID))
            ].sort_values(["PaymentDate", "PayrollPaymentID"])
            if payment_rows.empty:
                continue
            payment_row = payment_rows.iloc[0]
            if int(payment_row["PayrollPaymentID"]) in used_ids:
                continue
            target_date = (pd.Timestamp(row.ApprovedDate) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            mask = context.tables["PayrollPayment"]["PayrollPaymentID"].astype(int).eq(int(payment_row["PayrollPaymentID"]))
            context.tables["PayrollPayment"].loc[mask, "PaymentDate"] = target_date
            log_anomaly(
                context,
                "payroll_payment_before_approval",
                "PayrollPayment",
                int(payment_row["PayrollPaymentID"]),
                year,
                "Payroll payment date was moved before the payroll register approval date.",
                "Payroll control review for payroll payments dated before approval.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_missing_work_order_operations(context: GenerationContext, count_per_year: int) -> None:
    work_orders = context.tables["WorkOrder"]
    operations = context.tables["WorkOrderOperation"]
    schedules = context.tables["WorkOrderOperationSchedule"]
    if work_orders.empty or operations.empty or count_per_year <= 0:
        return

    items = context.tables["Item"][["ItemID", "SupplyMode"]].copy()
    manufactured_ids = set(items.loc[items["SupplyMode"].eq("Manufactured"), "ItemID"].astype(int))
    operation_counts = operations.groupby("WorkOrderID").size()
    for year in fiscal_years(context):
        year_orders = rows_for_year(work_orders, "ReleasedDate", year).copy()
        year_orders = year_orders[
            year_orders["ItemID"].astype(int).isin(manufactured_ids)
            & year_orders["WorkOrderID"].astype(int).isin(operation_counts.index.astype(int))
        ]
        used_ids = used_primary_keys(context, "WorkOrder", "missing_work_order_operations")
        if used_ids:
            year_orders = year_orders[~year_orders["WorkOrderID"].astype(int).isin(used_ids)]
        injected = 0
        for row in year_orders.itertuples(index=False):
            operation_ids = operations.loc[
                operations["WorkOrderID"].astype(int).eq(int(row.WorkOrderID)),
                "WorkOrderOperationID",
            ].astype(int).tolist()
            if not operation_ids:
                continue
            context.tables["WorkOrderOperation"] = context.tables["WorkOrderOperation"][
                ~context.tables["WorkOrderOperation"]["WorkOrderID"].astype(int).eq(int(row.WorkOrderID))
            ].reset_index(drop=True)
            if not schedules.empty:
                context.tables["WorkOrderOperationSchedule"] = context.tables["WorkOrderOperationSchedule"][
                    ~context.tables["WorkOrderOperationSchedule"]["WorkOrderOperationID"].astype(int).isin(operation_ids)
                ].reset_index(drop=True)
            log_anomaly(
                context,
                "missing_work_order_operations",
                "WorkOrder",
                int(row.WorkOrderID),
                year,
                "Manufactured work order no longer has any work-order operation rows.",
                "Missing routing or operation-link review for manufactured work orders without operations.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_invalid_direct_labor_operation_link(context: GenerationContext, count_per_year: int) -> None:
    labor_entries = context.tables["LaborTimeEntry"]
    if labor_entries.empty or count_per_year <= 0:
        return

    direct_labor = labor_entries[
        labor_entries["LaborType"].eq("Direct Manufacturing")
        & labor_entries["WorkOrderID"].notna()
        & labor_entries["WorkOrderOperationID"].notna()
    ].copy()
    for year in fiscal_years(context):
        year_entries = rows_for_year(direct_labor, "WorkDate", year).copy()
        used_ids = used_primary_keys(context, "LaborTimeEntry", "invalid_direct_labor_operation_link")
        if used_ids:
            year_entries = year_entries[~year_entries["LaborTimeEntryID"].astype(int).isin(used_ids)]
        for row in year_entries.head(count_per_year).itertuples(index=False):
            mask = context.tables["LaborTimeEntry"]["LaborTimeEntryID"].astype(int).eq(int(row.LaborTimeEntryID))
            context.tables["LaborTimeEntry"].loc[mask, "WorkOrderOperationID"] = None
            log_anomaly(
                context,
                "invalid_direct_labor_operation_link",
                "LaborTimeEntry",
                int(row.LaborTimeEntryID),
                year,
                "Direct manufacturing labor row is missing its work-order operation link.",
                "Missing routing or operation-link review for direct labor rows without operation linkage.",
            )


def inject_overlapping_operation_sequence(context: GenerationContext, count_per_year: int) -> None:
    operations = context.tables["WorkOrderOperation"]
    if operations.empty or count_per_year <= 0:
        return

    excluded_work_orders = {
        int(entry["primary_key_value"])
        for entry in context.anomaly_log
        if entry["table_name"] == "WorkOrder" and entry["anomaly_type"] == "missing_work_order_operations"
    }
    for year in fiscal_years(context):
        year_operations = rows_for_year(operations, "ActualStartDate", year).copy()
        year_operations = year_operations[
            year_operations["ActualStartDate"].notna() & year_operations["ActualEndDate"].notna()
        ]
        used_ids = used_primary_keys(context, "WorkOrderOperation", "overlapping_operation_sequence")
        if used_ids:
            year_operations = year_operations[~year_operations["WorkOrderOperationID"].astype(int).isin(used_ids)]
        injected = 0
        for work_order_id, work_order_rows in year_operations.groupby("WorkOrderID", sort=True):
            if int(work_order_id) in excluded_work_orders:
                continue
            work_order_rows = work_order_rows.sort_values(["OperationSequence", "WorkOrderOperationID"])
            if len(work_order_rows) < 2:
                continue
            prior_row = work_order_rows.iloc[0]
            target_row = work_order_rows.iloc[1]
            if pd.isna(prior_row["ActualEndDate"]) or pd.isna(target_row["ActualStartDate"]):
                continue
            target_date = (pd.Timestamp(prior_row["ActualEndDate"]) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            mask = context.tables["WorkOrderOperation"]["WorkOrderOperationID"].astype(int).eq(
                int(target_row["WorkOrderOperationID"])
            )
            context.tables["WorkOrderOperation"].loc[mask, "ActualStartDate"] = target_date
            log_anomaly(
                context,
                "overlapping_operation_sequence",
                "WorkOrderOperation",
                int(target_row["WorkOrderOperationID"]),
                year,
                "Work-order operation was moved to start before the prior operation finished.",
                "Operation sequence and final-completion review for overlapping routing operations.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_threshold_adjacent_entries(context: GenerationContext, count_per_year: int) -> None:
    requisitions = context.tables["PurchaseRequisition"]
    if requisitions.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        selected = rows_for_year(requisitions, "RequestDate", year).head(count_per_year)
        for offset, row in enumerate(selected.itertuples(index=False), start=1):
            quantity = float(row.Quantity) if float(row.Quantity) else 1.0
            target_total = 4995.00 - offset
            estimated_unit_cost = money(target_total / quantity)
            mask = context.tables["PurchaseRequisition"]["RequisitionID"].astype(int).eq(int(row.RequisitionID))
            context.tables["PurchaseRequisition"].loc[mask, "EstimatedUnitCost"] = estimated_unit_cost
            log_anomaly(
                context,
                "threshold_adjacent_requisition",
                "PurchaseRequisition",
                int(row.RequisitionID),
                year,
                "Requisition amount adjusted just below a common approval threshold.",
                "Requisition totals immediately below approval thresholds.",
            )


def inject_round_dollar_manual_journals(context: GenerationContext, count_per_year: int) -> None:
    if context.tables["JournalEntry"].empty or count_per_year <= 0:
        return

    candidate_types = {
        "Rent",
        "Utilities",
        "Factory Overhead",
        "Direct Labor Reclass",
        "Manufacturing Overhead Reclass",
        "Depreciation",
        "Year-End Close - Income Summary to Retained Earnings",
    }

    for year in fiscal_years(context):
        year_journals = journal_entries_for_year(
            context,
            year,
            entry_types=candidate_types,
            exclude_used=True,
        )
        injected = 0
        for row in year_journals.itertuples(index=False):
            gl_rows = journal_gl_rows(context, int(row.JournalEntryID))
            if len(gl_rows) != 2:
                continue

            total_debit = round(float(gl_rows["Debit"].sum()), 2)
            rounded_amount = float(round(total_debit))
            if rounded_amount <= 0 or rounded_amount == total_debit:
                continue

            debit_rows = gl_rows[gl_rows["Debit"].astype(float).gt(0)]
            credit_rows = gl_rows[gl_rows["Credit"].astype(float).gt(0)]
            if len(debit_rows) != 1 or len(credit_rows) != 1:
                continue

            debit_index = debit_rows.index[0]
            credit_index = credit_rows.index[0]
            context.tables["GLEntry"].loc[debit_index, "Debit"] = rounded_amount
            context.tables["GLEntry"].loc[debit_index, "Credit"] = 0.0
            context.tables["GLEntry"].loc[credit_index, "Debit"] = 0.0
            context.tables["GLEntry"].loc[credit_index, "Credit"] = rounded_amount
            journal_mask = context.tables["JournalEntry"]["JournalEntryID"].astype(int).eq(int(row.JournalEntryID))
            context.tables["JournalEntry"].loc[journal_mask, "TotalAmount"] = rounded_amount

            log_anomaly(
                context,
                "round_dollar_manual_journal",
                "JournalEntry",
                int(row.JournalEntryID),
                year,
                "Manual journal amount was rounded to a whole dollar amount.",
                "Round-dollar manual journal query using TotalAmount or linked GL lines.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_related_party_address_matches(context: GenerationContext, count_per_year: int) -> None:
    suppliers = context.tables["Supplier"]
    employees = context.tables["Employee"]
    if suppliers.empty or employees.empty or count_per_year <= 0:
        return

    total_needed = count_per_year * len(fiscal_years(context))
    supplier_rows = suppliers.head(total_needed)
    employee_rows = employees.sample(
        n=min(total_needed, len(employees)),
        random_state=context.settings.random_seed,
        replace=True,
    )
    years = fiscal_years(context)
    for index, (supplier_row, employee_row) in enumerate(
        zip(supplier_rows.itertuples(index=False), employee_rows.itertuples(index=False))
    ):
        year = years[index // count_per_year]
        mask = context.tables["Supplier"]["SupplierID"].astype(int).eq(int(supplier_row.SupplierID))
        context.tables["Supplier"].loc[mask, "Address"] = employee_row.Address
        context.tables["Supplier"].loc[mask, "City"] = employee_row.City
        context.tables["Supplier"].loc[mask, "State"] = employee_row.State
        log_anomaly(
            context,
            "related_party_address_match",
            "Supplier",
            int(supplier_row.SupplierID),
            year,
            "Supplier address intentionally matches an employee address.",
            "Supplier-to-employee address match query.",
        )


def inject_scheduled_on_nonworking_day(context: GenerationContext, count_per_year: int) -> None:
    schedules = context.tables["WorkOrderOperationSchedule"]
    calendars = context.tables["WorkCenterCalendar"]
    if schedules.empty or calendars.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        year_schedules = schedules[pd.to_datetime(schedules["ScheduleDate"]).dt.year.eq(year)].copy()
        used_ids = used_primary_keys(context, "WorkOrderOperationSchedule", "scheduled_on_nonworking_day")
        if used_ids:
            year_schedules = year_schedules[~year_schedules["WorkOrderOperationScheduleID"].astype(int).isin(used_ids)]
        for row in year_schedules.head(count_per_year).itertuples(index=False):
            nonworking = calendars[
                calendars["WorkCenterID"].astype(int).eq(int(row.WorkCenterID))
                & pd.to_datetime(calendars["CalendarDate"]).dt.year.eq(year)
                & calendars["IsWorkingDay"].astype(int).eq(0)
            ].sort_values("CalendarDate")
            if nonworking.empty:
                continue
            target_date = str(nonworking.iloc[0]["CalendarDate"])
            mask = context.tables["WorkOrderOperationSchedule"]["WorkOrderOperationScheduleID"].astype(int).eq(
                int(row.WorkOrderOperationScheduleID)
            )
            context.tables["WorkOrderOperationSchedule"].loc[mask, "ScheduleDate"] = target_date
            log_anomaly(
                context,
                "scheduled_on_nonworking_day",
                "WorkOrderOperationSchedule",
                int(row.WorkOrderOperationScheduleID),
                year,
                f"Operation schedule moved to non-working date {target_date}.",
                "Schedule rows that fall on work-center non-working days.",
            )


def inject_overbooked_work_center_day(context: GenerationContext, count_per_year: int) -> None:
    schedules = context.tables["WorkOrderOperationSchedule"]
    calendars = context.tables["WorkCenterCalendar"]
    if schedules.empty or calendars.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        year_schedules = schedules[pd.to_datetime(schedules["ScheduleDate"]).dt.year.eq(year)].copy()
        used_ids = used_primary_keys(context, "WorkOrderOperationSchedule", "overbooked_work_center_day")
        if used_ids:
            year_schedules = year_schedules[~year_schedules["WorkOrderOperationScheduleID"].astype(int).isin(used_ids)]
        injected = 0
        for row in year_schedules.itertuples(index=False):
            calendar_row = calendars[
                calendars["WorkCenterID"].astype(int).eq(int(row.WorkCenterID))
                & calendars["CalendarDate"].eq(str(row.ScheduleDate))
            ]
            if calendar_row.empty or float(calendar_row.iloc[0]["AvailableHours"]) <= 0:
                continue
            available_hours = float(calendar_row.iloc[0]["AvailableHours"])
            mask = context.tables["WorkOrderOperationSchedule"]["WorkOrderOperationScheduleID"].astype(int).eq(
                int(row.WorkOrderOperationScheduleID)
            )
            context.tables["WorkOrderOperationSchedule"].loc[mask, "ScheduledHours"] = money(available_hours + 1.0)
            log_anomaly(
                context,
                "overbooked_work_center_day",
                "WorkOrderOperationSchedule",
                int(row.WorkOrderOperationScheduleID),
                year,
                "Work-center day was intentionally overbooked beyond available hours.",
                "Work-center days where scheduled hours exceed available hours.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_completion_before_operation_end(context: GenerationContext, count_per_year: int) -> None:
    completions = context.tables["ProductionCompletion"]
    operations = context.tables["WorkOrderOperation"]
    if completions.empty or operations.empty or count_per_year <= 0:
        return

    latest_operation_end = (
        operations[operations["ActualEndDate"].notna()]
        .groupby("WorkOrderID")["ActualEndDate"]
        .max()
        .to_dict()
    )

    for year in fiscal_years(context):
        year_completions = completions[pd.to_datetime(completions["CompletionDate"]).dt.year.eq(year)].copy()
        year_completions = year_completions.sort_values(["WorkOrderID", "CompletionDate", "ProductionCompletionID"])
        used_ids = used_primary_keys(context, "ProductionCompletion", "completion_before_operation_end")
        if used_ids:
            year_completions = year_completions[~year_completions["ProductionCompletionID"].astype(int).isin(used_ids)]
        injected = 0
        for row in year_completions.itertuples(index=False):
            final_actual_end = latest_operation_end.get(int(row.WorkOrderID))
            if final_actual_end is None:
                continue
            target_date = pd.Timestamp(final_actual_end) - pd.Timedelta(days=1)
            if target_date >= pd.Timestamp(final_actual_end):
                target_date = pd.Timestamp(final_actual_end) - pd.Timedelta(days=1)
            mask = context.tables["ProductionCompletion"]["ProductionCompletionID"].astype(int).eq(
                int(row.ProductionCompletionID)
            )
            context.tables["ProductionCompletion"].loc[mask, "CompletionDate"] = target_date.strftime("%Y-%m-%d")
            log_anomaly(
                context,
                "completion_before_operation_end",
                "ProductionCompletion",
                int(row.ProductionCompletionID),
                year,
                "Production completion date was moved before the final operation end date.",
                "Production completions dated before final work-order operation end.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_missing_clock_out(context: GenerationContext, count_per_year: int) -> None:
    time_clocks = context.tables["TimeClockEntry"]
    if time_clocks.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        candidates = rows_for_year(time_clocks, "WorkDate", year).copy()
        used_ids = used_primary_keys(context, "TimeClockEntry", "missing_clock_out")
        if used_ids:
            candidates = candidates[~candidates["TimeClockEntryID"].astype(int).isin(used_ids)]
        for row in candidates.head(count_per_year).itertuples(index=False):
            mask = context.tables["TimeClockEntry"]["TimeClockEntryID"].astype(int).eq(int(row.TimeClockEntryID))
            context.tables["TimeClockEntry"].loc[mask, "ClockOutTime"] = None
            context.tables["TimeClockEntry"].loc[mask, "ClockStatus"] = "Pending"
            append_attendance_exception(
                context,
                int(row.EmployeeID),
                int(row.PayrollPeriodID),
                str(row.WorkDate),
                None if pd.isna(row.ShiftDefinitionID) else int(row.ShiftDefinitionID),
                int(row.TimeClockEntryID),
                "Missing Clock Out",
                "High",
                0.0,
            )
            log_anomaly(
                context,
                "missing_clock_out",
                "TimeClockEntry",
                int(row.TimeClockEntryID),
                year,
                "Time-clock entry is missing ClockOutTime.",
                "Time-clock records with null ClockOutTime.",
            )


def inject_duplicate_time_clock_day(context: GenerationContext, count_per_year: int) -> None:
    time_clocks = context.tables["TimeClockEntry"]
    if time_clocks.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        year_rows = rows_for_year(time_clocks, "WorkDate", year).copy()
        if year_rows.empty:
            continue
        used_ids = used_primary_keys(context, "TimeClockEntry", "duplicate_time_clock_day")
        if used_ids:
            year_rows = year_rows[~year_rows["TimeClockEntryID"].astype(int).isin(used_ids)]
        grouped = year_rows.groupby(["EmployeeID", "PayrollPeriodID"])
        injected = 0
        for (_, _), rows in grouped:
            if len(rows) < 2:
                continue
            first = rows.sort_values(["WorkDate", "TimeClockEntryID"]).iloc[0]
            second = rows.sort_values(["WorkDate", "TimeClockEntryID"]).iloc[1]
            target_date = str(first["WorkDate"])
            second_mask = context.tables["TimeClockEntry"]["TimeClockEntryID"].astype(int).eq(int(second["TimeClockEntryID"]))
            context.tables["TimeClockEntry"].loc[second_mask, "WorkDate"] = target_date
            context.tables["TimeClockEntry"].loc[second_mask, "ClockInTime"] = compose_timestamp(target_date, second["ClockInTime"], "08:00:00")
            context.tables["TimeClockEntry"].loc[second_mask, "ClockOutTime"] = compose_timestamp(target_date, second["ClockOutTime"], "16:00:00")
            append_attendance_exception(
                context,
                int(second["EmployeeID"]),
                int(second["PayrollPeriodID"]),
                target_date,
                None if pd.isna(second["ShiftDefinitionID"]) else int(second["ShiftDefinitionID"]),
                int(second["TimeClockEntryID"]),
                "Duplicate Clock Day",
                "High",
                0.0,
            )
            log_anomaly(
                context,
                "duplicate_time_clock_day",
                "TimeClockEntry",
                int(second["TimeClockEntryID"]),
                year,
                "Employee has more than one time-clock entry on the same work date.",
                "Duplicate time-clock day query by employee and WorkDate.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_off_shift_clocking(context: GenerationContext, count_per_year: int) -> None:
    time_clocks = context.tables["TimeClockEntry"]
    shifts = context.tables["ShiftDefinition"]
    if time_clocks.empty or shifts.empty or count_per_year <= 0:
        return

    shift_lookup = shifts.set_index("ShiftDefinitionID").to_dict("index")
    for year in fiscal_years(context):
        candidates = rows_for_year(time_clocks, "WorkDate", year).copy()
        used_ids = used_primary_keys(context, "TimeClockEntry", "off_shift_clocking")
        if used_ids:
            candidates = candidates[~candidates["TimeClockEntryID"].astype(int).isin(used_ids)]
        injected = 0
        for row in candidates.itertuples(index=False):
            if pd.isna(row.ShiftDefinitionID):
                continue
            shift = shift_lookup.get(int(row.ShiftDefinitionID))
            if shift is None:
                continue
            late_clock_in = pd.Timestamp(f"{row.WorkDate} {shift['StartTime']}") + pd.Timedelta(hours=2)
            total_minutes = int(round((float(row.RegularHours) + float(row.OvertimeHours)) * 60)) + int(row.BreakMinutes)
            late_clock_out = late_clock_in + pd.Timedelta(minutes=total_minutes)
            mask = context.tables["TimeClockEntry"]["TimeClockEntryID"].astype(int).eq(int(row.TimeClockEntryID))
            context.tables["TimeClockEntry"].loc[mask, "ClockInTime"] = late_clock_in.strftime("%Y-%m-%d %H:%M:%S")
            context.tables["TimeClockEntry"].loc[mask, "ClockOutTime"] = late_clock_out.strftime("%Y-%m-%d %H:%M:%S")
            append_attendance_exception(
                context,
                int(row.EmployeeID),
                int(row.PayrollPeriodID),
                str(row.WorkDate),
                int(row.ShiftDefinitionID),
                int(row.TimeClockEntryID),
                "Off Shift Clocking",
                "Medium",
                120.0,
            )
            log_anomaly(
                context,
                "off_shift_clocking",
                "TimeClockEntry",
                int(row.TimeClockEntryID),
                year,
                "Time-clock entry was moved materially outside its assigned shift.",
                "Clock-in or clock-out materially outside shift definition.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_paid_without_clock(context: GenerationContext, count_per_year: int) -> None:
    register_lines = context.tables["PayrollRegisterLine"]
    labor_entries = context.tables["LaborTimeEntry"]
    time_clocks = context.tables["TimeClockEntry"]
    if register_lines.empty or labor_entries.empty or time_clocks.empty or count_per_year <= 0:
        return

    labor_lookup = labor_entries.set_index("LaborTimeEntryID").to_dict("index")
    register_lookup = context.tables["PayrollRegister"].set_index("PayrollRegisterID").to_dict("index")
    candidates = register_lines[register_lines["LineType"].isin(["Regular Earnings", "Overtime Earnings"])].copy()

    for year in fiscal_years(context):
        year_candidates = []
        for row in candidates.itertuples(index=False):
            register = register_lookup.get(int(row.PayrollRegisterID))
            labor_entry = None if pd.isna(row.LaborTimeEntryID) else labor_lookup.get(int(row.LaborTimeEntryID))
            if register is None or labor_entry is None or pd.isna(labor_entry.get("TimeClockEntryID")):
                continue
            approved_date = pd.Timestamp(register["ApprovedDate"])
            if approved_date.year != year:
                continue
            year_candidates.append((row, register, labor_entry))
        injected = 0
        used_ids = used_primary_keys(context, "PayrollRegisterLine", "paid_without_clock")
        for row, register, labor_entry in year_candidates:
            if int(row.PayrollRegisterLineID) in used_ids:
                continue
            time_clock_id = int(labor_entry["TimeClockEntryID"])
            mask = context.tables["TimeClockEntry"]["TimeClockEntryID"].astype(int).eq(time_clock_id)
            context.tables["TimeClockEntry"].loc[mask, "ClockStatus"] = "Pending"
            context.tables["TimeClockEntry"].loc[mask, "ApprovedDate"] = None
            append_attendance_exception(
                context,
                int(labor_entry["EmployeeID"]),
                int(labor_entry["PayrollPeriodID"]),
                str(labor_entry["WorkDate"]),
                None,
                time_clock_id,
                "Paid Without Approved Clock",
                "High",
                0.0,
            )
            log_anomaly(
                context,
                "paid_without_clock",
                "PayrollRegisterLine",
                int(row.PayrollRegisterLineID),
                year,
                "Hourly payroll line remains paid while the supporting time clock is no longer approved.",
                "Hourly payroll earnings without approved time-clock support.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_labor_after_operation_close(context: GenerationContext, count_per_year: int) -> None:
    labor_entries = context.tables["LaborTimeEntry"]
    work_orders = context.tables["WorkOrder"]
    time_clocks = context.tables["TimeClockEntry"]
    if labor_entries.empty or work_orders.empty or time_clocks.empty or count_per_year <= 0:
        return

    work_order_lookup = work_orders.set_index("WorkOrderID").to_dict("index")
    valid_operation_ids = set(context.tables["WorkOrderOperation"]["WorkOrderOperationID"].astype(int))
    time_clock_mask_series = context.tables["TimeClockEntry"]["TimeClockEntryID"].astype(int)
    candidates = labor_entries[
        labor_entries["LaborType"].eq("Direct Manufacturing")
        & labor_entries["WorkOrderID"].notna()
        & labor_entries["WorkOrderOperationID"].notna()
        & labor_entries["TimeClockEntryID"].notna()
    ].copy()
    candidates = candidates[candidates["WorkOrderOperationID"].astype(int).isin(valid_operation_ids)]

    for year in fiscal_years(context):
        year_candidates = candidates[pd.to_datetime(candidates["WorkDate"]).dt.year.eq(year)].copy()
        used_ids = used_primary_keys(context, "LaborTimeEntry", "labor_after_operation_close")
        if used_ids:
            year_candidates = year_candidates[~year_candidates["LaborTimeEntryID"].astype(int).isin(used_ids)]
        injected = 0
        for row in year_candidates.itertuples(index=False):
            work_order = work_order_lookup.get(int(row.WorkOrderID))
            if work_order is None or pd.isna(work_order.get("ClosedDate")):
                continue
            shifted_date = (pd.Timestamp(work_order["ClosedDate"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            labor_mask = context.tables["LaborTimeEntry"]["LaborTimeEntryID"].astype(int).eq(int(row.LaborTimeEntryID))
            context.tables["LaborTimeEntry"].loc[labor_mask, "WorkDate"] = shifted_date
            time_clock_id = int(row.TimeClockEntryID)
            time_clock_mask = time_clock_mask_series.eq(time_clock_id)
            original_clock_in = context.tables["TimeClockEntry"].loc[time_clock_mask, "ClockInTime"].iloc[0]
            original_clock_out = context.tables["TimeClockEntry"].loc[time_clock_mask, "ClockOutTime"].iloc[0]
            context.tables["TimeClockEntry"].loc[time_clock_mask, "WorkDate"] = shifted_date
            context.tables["TimeClockEntry"].loc[time_clock_mask, "ClockInTime"] = compose_timestamp(shifted_date, original_clock_in, "08:00:00")
            context.tables["TimeClockEntry"].loc[time_clock_mask, "ClockOutTime"] = compose_timestamp(shifted_date, original_clock_out, "16:00:00")
            append_attendance_exception(
                context,
                int(row.EmployeeID),
                int(row.PayrollPeriodID),
                shifted_date,
                None,
                time_clock_id,
                "Labor After Close",
                "High",
                0.0,
            )
            log_anomaly(
                context,
                "labor_after_operation_close",
                "LaborTimeEntry",
                int(row.LaborTimeEntryID),
                year,
                "Direct labor date was moved after the related work order was closed.",
                "Direct labor or time-clock rows after work-order close.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_anomalies(context: GenerationContext) -> None:
    profile = load_anomaly_profile(context)
    if not profile.get("enabled", False):
        return

    inject_weekend_journal_entries(context, int(profile.get("weekend_journal_entries_per_year", 0)))
    inject_same_creator_approver(context, int(profile.get("same_creator_approver_per_year", 0)))
    inject_same_creator_approver_journals(context, int(profile.get("same_creator_approver_journals_per_year", 0)))
    inject_missing_approvals(context, int(profile.get("missing_approvals_per_year", 0)))
    inject_late_reversals(context, int(profile.get("late_reversals_per_year", 0)))
    inject_missing_reversal_links(context, int(profile.get("missing_reversal_links_per_year", 0)))
    inject_invoice_before_shipment(context, int(profile.get("invoice_before_shipment_per_year", 0)))
    inject_duplicate_vendor_payment_reference(context, int(profile.get("duplicate_vendor_payments_per_year", 0)))
    inject_duplicate_supplier_invoice_number(context, int(profile.get("duplicate_supplier_invoice_numbers_per_year", 0)))
    inject_threshold_adjacent_entries(context, int(profile.get("threshold_adjacent_entries_per_year", 0)))
    inject_round_dollar_manual_journals(context, int(profile.get("round_dollar_manual_journals_per_year", 0)))
    inject_related_party_address_matches(context, int(profile.get("related_party_address_matches_per_year", 0)))
    inject_missing_payroll_payment(context, int(profile.get("missing_payroll_payments_per_year", 0)))
    inject_payroll_payment_before_approval(context, int(profile.get("payroll_payment_before_approval_per_year", 0)))
    inject_missing_work_order_operations(context, int(profile.get("missing_work_order_operations_per_year", 0)))
    inject_invalid_direct_labor_operation_link(context, int(profile.get("invalid_direct_labor_operation_links_per_year", 0)))
    inject_overlapping_operation_sequence(context, int(profile.get("overlapping_operation_sequence_per_year", 0)))
    inject_scheduled_on_nonworking_day(context, int(profile.get("scheduled_on_nonworking_day_per_year", 0)))
    inject_overbooked_work_center_day(context, int(profile.get("overbooked_work_center_day_per_year", 0)))
    inject_completion_before_operation_end(context, int(profile.get("completion_before_operation_end_per_year", 0)))
    inject_missing_clock_out(context, int(profile.get("missing_clock_out_per_year", 0)))
    inject_duplicate_time_clock_day(context, int(profile.get("duplicate_time_clock_day_per_year", 0)))
    inject_off_shift_clocking(context, int(profile.get("off_shift_clocking_per_year", 0)))
    inject_paid_without_clock(context, int(profile.get("paid_without_clock_per_year", 0)))
    inject_labor_after_operation_close(context, int(profile.get("labor_after_operation_close_per_year", 0)))
    invalidate_all_caches(context)
