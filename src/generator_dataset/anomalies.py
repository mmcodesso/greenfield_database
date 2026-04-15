from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.settings import GenerationContext
from generator_dataset.utils import money, next_id, qty


APPROVAL_ROLE_FAMILIES_BY_DOCUMENT = {
    "Purchase Requisition": {"Finance and Accounting", "Executive Leadership"},
    "Purchase Order": {"Finance and Accounting", "Executive Leadership"},
    "Purchase Invoice": {"Finance and Accounting"},
    "Credit Memo": {"Finance and Accounting", "Executive Leadership"},
    "Customer Refund": {"Finance and Accounting", "Executive Leadership"},
    "Journal Entry": {"Finance and Accounting", "Executive Leadership"},
    "Payroll Register": {"Finance and Accounting", "Executive Leadership"},
}


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
    employee_shift_roster_id: int | None,
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
        "EmployeeShiftRosterID": employee_shift_roster_id,
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


def approval_document_rows(context: GenerationContext, year: int) -> pd.DataFrame:
    specs = [
        ("PurchaseOrder", "Purchase Order", "PurchaseOrderID", "OrderDate", "OrderTotal", "ApprovedByEmployeeID", "CreatedByEmployeeID", "PONumber"),
        ("PurchaseInvoice", "Purchase Invoice", "PurchaseInvoiceID", "ApprovedDate", "GrandTotal", "ApprovedByEmployeeID", None, "InvoiceNumber"),
        ("CreditMemo", "Credit Memo", "CreditMemoID", "ApprovedDate", "GrandTotal", "ApprovedByEmployeeID", None, "CreditMemoNumber"),
        ("CustomerRefund", "Customer Refund", "CustomerRefundID", "RefundDate", "Amount", "ApprovedByEmployeeID", None, "RefundNumber"),
        ("JournalEntry", "Journal Entry", "JournalEntryID", "ApprovedDate", "TotalAmount", "ApprovedByEmployeeID", "CreatedByEmployeeID", "EntryNumber"),
        ("PayrollRegister", "Payroll Register", "PayrollRegisterID", "ApprovedDate", "GrossPay", "ApprovedByEmployeeID", None, None),
    ]
    frames: list[pd.DataFrame] = []
    for table_name, document_type, pk_column, date_column, amount_column, approver_column, creator_column, document_number_column in specs:
        table = context.tables[table_name]
        if table.empty or approver_column not in table.columns:
            continue
        columns = [pk_column, date_column, amount_column, approver_column]
        if creator_column is not None:
            columns.append(creator_column)
        if document_number_column is not None:
            columns.append(document_number_column)
        rows = table[columns].copy()
        rows = rows[rows[approver_column].notna()]
        rows["EventDateValue"] = pd.to_datetime(rows[date_column], errors="coerce")
        rows = rows[rows["EventDateValue"].dt.year.eq(year) & rows["EventDateValue"].notna()]
        if rows.empty:
            continue
        rows["TableName"] = table_name
        rows["DocumentType"] = document_type
        rows["PrimaryKeyColumn"] = pk_column
        rows["PrimaryKeyValue"] = rows[pk_column].astype(int)
        rows["EventDate"] = rows[date_column].astype(str)
        rows["DocumentAmount"] = rows[amount_column].astype(float)
        rows["ApprovedByEmployeeIDValue"] = rows[approver_column].astype(int)
        rows["CreatorEmployeeIDValue"] = rows[creator_column].astype("Int64") if creator_column is not None else pd.Series(pd.NA, index=rows.index, dtype="Int64")
        rows["DocumentNumber"] = rows[document_number_column].astype(str) if document_number_column is not None else rows[pk_column].astype(str)
        frames.append(
            rows[
                [
                    "TableName",
                    "DocumentType",
                    "PrimaryKeyColumn",
                    "PrimaryKeyValue",
                    "DocumentNumber",
                    "EventDate",
                    "EventDateValue",
                    "DocumentAmount",
                    "ApprovedByEmployeeIDValue",
                    "CreatorEmployeeIDValue",
                ]
            ]
        )
    if not frames:
        return pd.DataFrame(
            columns=[
                "TableName",
                "DocumentType",
                "PrimaryKeyColumn",
                "PrimaryKeyValue",
                "DocumentNumber",
                "EventDate",
                "EventDateValue",
                "DocumentAmount",
                "ApprovedByEmployeeIDValue",
                "CreatorEmployeeIDValue",
            ]
        )
    documents = pd.concat(frames, ignore_index=True)
    return documents.sort_values(["EventDateValue", "TableName", "PrimaryKeyValue"]).reset_index(drop=True)


def approval_candidate_employees(
    context: GenerationContext,
    *,
    event_date: pd.Timestamp,
    current_approver_id: int,
    creator_employee_id: int | None,
) -> pd.DataFrame:
    employees = context.tables["Employee"].copy()
    if employees.empty:
        return employees
    hire_dates = pd.to_datetime(employees["HireDate"], errors="coerce")
    termination_dates = pd.to_datetime(employees["TerminationDate"], errors="coerce")
    employees = employees[
        hire_dates.le(pd.Timestamp(event_date))
        & (termination_dates.isna() | termination_dates.ge(pd.Timestamp(event_date)))
    ].copy()
    employees = employees[~employees["EmployeeID"].astype(int).eq(int(current_approver_id))]
    if creator_employee_id is not None:
        employees = employees[~employees["EmployeeID"].astype(int).eq(int(creator_employee_id))]
    return employees.copy()


def reassign_document_approver(
    context: GenerationContext,
    *,
    table_name: str,
    pk_column: str,
    pk_value: int,
    employee_id: int,
) -> None:
    mask = context.tables[table_name][pk_column].astype(int).eq(int(pk_value))
    context.tables[table_name].loc[mask, "ApprovedByEmployeeID"] = int(employee_id)


def current_state_inactive_employee_rows(context: GenerationContext) -> pd.DataFrame:
    employees = context.tables["Employee"]
    if employees.empty:
        return employees.head(0)
    rows = employees[
        employees["IsActive"].astype(int).eq(0)
        | employees["EmploymentStatus"].eq("Terminated")
    ].copy()
    if rows.empty:
        return rows
    rows["TerminationDateValue"] = pd.to_datetime(rows["TerminationDate"], errors="coerce")
    return rows.sort_values(["TerminationDateValue", "EmployeeID"], na_position="first").reset_index(drop=True)


def item_activity_rows(context: GenerationContext, year: int) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    sales_order_headers = context.tables["SalesOrder"][["SalesOrderID", "OrderDate", "OrderNumber"]].copy()
    if not context.tables["SalesOrderLine"].empty and not sales_order_headers.empty:
        rows = context.tables["SalesOrderLine"][["SalesOrderLineID", "ItemID", "SalesOrderID"]].merge(
            sales_order_headers,
            on="SalesOrderID",
            how="left",
        )
        rows["ActivityDateValue"] = pd.to_datetime(rows["OrderDate"], errors="coerce")
        rows = rows[rows["ActivityDateValue"].dt.year.eq(year)]
        if not rows.empty:
            rows["TableName"] = "SalesOrderLine"
            rows["PrimaryKeyValue"] = rows["SalesOrderLineID"].astype(int)
            rows["DocumentNumber"] = rows["OrderNumber"].astype(str)
            frames.append(rows[["TableName", "PrimaryKeyValue", "DocumentNumber", "ItemID", "ActivityDateValue"]])

    purchase_order_headers = context.tables["PurchaseOrder"][["PurchaseOrderID", "OrderDate", "PONumber"]].copy()
    if not context.tables["PurchaseOrderLine"].empty and not purchase_order_headers.empty:
        rows = context.tables["PurchaseOrderLine"][["POLineID", "ItemID", "PurchaseOrderID"]].merge(
            purchase_order_headers,
            on="PurchaseOrderID",
            how="left",
        )
        rows["ActivityDateValue"] = pd.to_datetime(rows["OrderDate"], errors="coerce")
        rows = rows[rows["ActivityDateValue"].dt.year.eq(year)]
        if not rows.empty:
            rows["TableName"] = "PurchaseOrderLine"
            rows["PrimaryKeyValue"] = rows["POLineID"].astype(int)
            rows["DocumentNumber"] = rows["PONumber"].astype(str)
            frames.append(rows[["TableName", "PrimaryKeyValue", "DocumentNumber", "ItemID", "ActivityDateValue"]])

    work_orders = context.tables["WorkOrder"]
    if not work_orders.empty:
        rows = work_orders[["WorkOrderID", "WorkOrderNumber", "ItemID", "ReleasedDate"]].copy()
        rows["ActivityDateValue"] = pd.to_datetime(rows["ReleasedDate"], errors="coerce")
        rows = rows[rows["ActivityDateValue"].dt.year.eq(year)]
        if not rows.empty:
            rows["TableName"] = "WorkOrder"
            rows["PrimaryKeyValue"] = rows["WorkOrderID"].astype(int)
            rows["DocumentNumber"] = rows["WorkOrderNumber"].astype(str)
            frames.append(rows[["TableName", "PrimaryKeyValue", "DocumentNumber", "ItemID", "ActivityDateValue"]])

    shipment_headers = context.tables["Shipment"][["ShipmentID", "ShipmentDate", "ShipmentNumber"]].copy()
    if not context.tables["ShipmentLine"].empty and not shipment_headers.empty:
        rows = context.tables["ShipmentLine"][["ShipmentLineID", "ItemID", "ShipmentID"]].merge(
            shipment_headers,
            on="ShipmentID",
            how="left",
        )
        rows["ActivityDateValue"] = pd.to_datetime(rows["ShipmentDate"], errors="coerce")
        rows = rows[rows["ActivityDateValue"].dt.year.eq(year)]
        if not rows.empty:
            rows["TableName"] = "ShipmentLine"
            rows["PrimaryKeyValue"] = rows["ShipmentLineID"].astype(int)
            rows["DocumentNumber"] = rows["ShipmentNumber"].astype(str)
            frames.append(rows[["TableName", "PrimaryKeyValue", "DocumentNumber", "ItemID", "ActivityDateValue"]])

    invoice_headers = context.tables["SalesInvoice"][["SalesInvoiceID", "InvoiceDate", "InvoiceNumber"]].copy()
    if not context.tables["SalesInvoiceLine"].empty and not invoice_headers.empty:
        rows = context.tables["SalesInvoiceLine"][["SalesInvoiceLineID", "ItemID", "SalesInvoiceID"]].merge(
            invoice_headers,
            on="SalesInvoiceID",
            how="left",
        )
        rows["ActivityDateValue"] = pd.to_datetime(rows["InvoiceDate"], errors="coerce")
        rows = rows[rows["ActivityDateValue"].dt.year.eq(year)]
        if not rows.empty:
            rows["TableName"] = "SalesInvoiceLine"
            rows["PrimaryKeyValue"] = rows["SalesInvoiceLineID"].astype(int)
            rows["DocumentNumber"] = rows["InvoiceNumber"].astype(str)
            frames.append(rows[["TableName", "PrimaryKeyValue", "DocumentNumber", "ItemID", "ActivityDateValue"]])

    if not frames:
        return pd.DataFrame(columns=["TableName", "PrimaryKeyValue", "DocumentNumber", "ItemID", "ActivityDateValue"])
    return pd.concat(frames, ignore_index=True).sort_values(["ActivityDateValue", "TableName", "PrimaryKeyValue"]).reset_index(drop=True)


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
                None if pd.isna(row.EmployeeShiftRosterID) else int(row.EmployeeShiftRosterID),
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
                None if pd.isna(second["EmployeeShiftRosterID"]) else int(second["EmployeeShiftRosterID"]),
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
                None if pd.isna(row.EmployeeShiftRosterID) else int(row.EmployeeShiftRosterID),
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
                None if pd.isna(row.TimeClockEntryID) else int(context.tables["TimeClockEntry"].loc[time_clock_mask, "EmployeeShiftRosterID"].iloc[0]) if time_clock_mask.any() else None,
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


def terminated_employee_rows(context: GenerationContext) -> pd.DataFrame:
    employees = context.tables["Employee"]
    if employees.empty or "TerminationDate" not in employees.columns:
        return employees.head(0)
    terminated = employees[
        employees["EmploymentStatus"].eq("Terminated")
        & employees["TerminationDate"].notna()
    ].copy()
    if terminated.empty:
        return terminated
    terminated["TerminationDateValue"] = pd.to_datetime(terminated["TerminationDate"], errors="coerce")
    return terminated.sort_values(["TerminationDateValue", "EmployeeID"]).reset_index(drop=True)


def inject_terminated_employee_on_payroll(context: GenerationContext, count_per_year: int) -> None:
    if count_per_year <= 0:
        return
    terminated = terminated_employee_rows(context)
    registers = context.tables["PayrollRegister"]
    periods = context.tables["PayrollPeriod"]
    if terminated.empty or registers.empty or periods.empty:
        return

    registers_with_periods = registers.merge(
        periods[["PayrollPeriodID", "PayDate"]],
        on="PayrollPeriodID",
        how="left",
    ).sort_values(["PayDate", "PayrollRegisterID"])
    period_lookup = periods.set_index("PayrollPeriodID")["PayDate"].to_dict()

    for year in fiscal_years(context):
        used_ids = used_primary_keys(context, "PayrollRegister", "terminated_employee_on_payroll")
        candidates = registers_with_periods[
            pd.to_datetime(registers_with_periods["PayDate"]).dt.year.eq(year)
            & ~registers_with_periods["PayrollRegisterID"].astype(int).isin(used_ids)
        ].copy()
        if candidates.empty:
            continue
        injected = 0
        for register in candidates.itertuples(index=False):
            pay_date = pd.Timestamp(register.PayDate)
            eligible_employees = terminated[
                terminated["TerminationDateValue"].lt(pay_date)
                & terminated["CostCenterID"].astype(int).eq(int(register.CostCenterID))
            ]
            if eligible_employees.empty:
                eligible_employees = terminated[terminated["TerminationDateValue"].lt(pay_date)]
            if eligible_employees.empty:
                continue
            employee_id = int(eligible_employees.iloc[0]["EmployeeID"])
            mask = context.tables["PayrollRegister"]["PayrollRegisterID"].astype(int).eq(int(register.PayrollRegisterID))
            context.tables["PayrollRegister"].loc[mask, "EmployeeID"] = employee_id
            log_anomaly(
                context,
                "terminated_employee_on_payroll",
                "PayrollRegister",
                int(register.PayrollRegisterID),
                year,
                "Payroll register employee was changed to an employee terminated before the pay date.",
                "Terminated employee payroll activity review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_terminated_employee_approval(context: GenerationContext, count_per_year: int) -> None:
    if count_per_year <= 0:
        return
    terminated = terminated_employee_rows(context)
    if terminated.empty:
        return

    approval_specs = [
        ("PurchaseOrder", "OrderDate", "ApprovedByEmployeeID", "purchase order approval after termination date"),
        ("PurchaseRequisition", "ApprovedDate", "ApprovedByEmployeeID", "requisition approval after termination date"),
        ("JournalEntry", "ApprovedDate", "ApprovedByEmployeeID", "journal approval after termination date"),
    ]
    for year in fiscal_years(context):
        injected = 0
        for table_name, date_column, employee_column, description in approval_specs:
            table = context.tables[table_name]
            if table.empty or employee_column not in table.columns or date_column not in table.columns:
                continue
            used_ids = used_primary_keys(context, table_name, "terminated_employee_approval")
            candidates = table[
                table[employee_column].notna()
                & pd.to_datetime(table[date_column], errors="coerce").dt.year.eq(year)
                & ~table.iloc[:, 0].astype(int).isin(used_ids)
            ].copy()
            if candidates.empty:
                continue
            for row in candidates.itertuples(index=False):
                event_date = pd.Timestamp(getattr(row, date_column))
                eligible_employees = terminated[terminated["TerminationDateValue"].lt(event_date)]
                if eligible_employees.empty:
                    continue
                employee_id = int(eligible_employees.iloc[0]["EmployeeID"])
                pk_column = table.columns[0]
                mask = context.tables[table_name][pk_column].astype(int).eq(int(getattr(row, pk_column)))
                context.tables[table_name].loc[mask, employee_column] = employee_id
                log_anomaly(
                    context,
                    "terminated_employee_approval",
                    table_name,
                    int(getattr(row, pk_column)),
                    year,
                    f"{table_name} approver was changed to an employee terminated before the approval date.",
                    "Approvals recorded after employee termination.",
                )
                injected += 1
                break
            if injected >= count_per_year:
                break


def inject_inactive_employee_time_or_labor(context: GenerationContext, count_per_year: int) -> None:
    if count_per_year <= 0:
        return
    terminated = terminated_employee_rows(context)
    time_clocks = context.tables["TimeClockEntry"]
    labor_entries = context.tables["LaborTimeEntry"]
    if terminated.empty or time_clocks.empty:
        return

    terminated_hourly = terminated[terminated["PayClass"].eq("Hourly")].copy()
    if terminated_hourly.empty:
        terminated_hourly = terminated

    for year in fiscal_years(context):
        used_ids = used_primary_keys(context, "TimeClockEntry", "inactive_employee_time_or_labor")
        candidates = time_clocks[
            pd.to_datetime(time_clocks["WorkDate"], errors="coerce").dt.year.eq(year)
            & ~time_clocks["TimeClockEntryID"].astype(int).isin(used_ids)
        ].copy()
        injected = 0
        for row in candidates.itertuples(index=False):
            work_date = pd.Timestamp(row.WorkDate)
            eligible_employees = terminated_hourly[terminated_hourly["TerminationDateValue"].lt(work_date)]
            if eligible_employees.empty:
                continue
            employee_id = int(eligible_employees.iloc[0]["EmployeeID"])
            time_clock_mask = context.tables["TimeClockEntry"]["TimeClockEntryID"].astype(int).eq(int(row.TimeClockEntryID))
            context.tables["TimeClockEntry"].loc[time_clock_mask, "EmployeeID"] = employee_id
            labor_mask = (
                labor_entries["TimeClockEntryID"].notna()
                & labor_entries["TimeClockEntryID"].astype(int).eq(int(row.TimeClockEntryID))
            ) if not labor_entries.empty else pd.Series(dtype=bool)
            if not labor_entries.empty and labor_mask.any():
                context.tables["LaborTimeEntry"].loc[labor_mask, "EmployeeID"] = employee_id
            log_anomaly(
                context,
                "inactive_employee_time_or_labor",
                "TimeClockEntry",
                int(row.TimeClockEntryID),
                year,
                "Time-clock and labor records were reassigned to an employee inactive as of the work date.",
                "Inactive employee time or labor activity review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_duplicate_executive_title_assignment(context: GenerationContext, count_per_year: int) -> None:
    if count_per_year <= 0:
        return
    employees = context.tables["Employee"]
    if employees.empty:
        return
    target_titles = [
        ("Chief Financial Officer", "Executive Leadership", "Executive", "Executive"),
        ("Controller", "Finance and Accounting", "Executive", "Executive"),
    ]
    current_role_ids = {
        title: employees.loc[employees["JobTitle"].eq(title), "EmployeeID"].astype(int).tolist()
        for title, _, _, _ in target_titles
    }

    for year in fiscal_years(context):
        used_ids = used_primary_keys(context, "Employee", "duplicate_executive_title_assignment")
        candidates = employees[
            employees["IsActive"].astype(int).eq(1)
            & ~employees["EmployeeID"].astype(int).isin(used_ids)
            & ~employees["EmployeeID"].astype(int).isin([employee_id for ids in current_role_ids.values() for employee_id in ids])
        ].sort_values("EmployeeID")
        injected = 0
        for row in candidates.itertuples(index=False):
            title, family, authorization_level, job_level = target_titles[injected % len(target_titles)]
            mask = context.tables["Employee"]["EmployeeID"].astype(int).eq(int(row.EmployeeID))
            context.tables["Employee"].loc[mask, "JobTitle"] = title
            context.tables["Employee"].loc[mask, "JobFamily"] = family
            context.tables["Employee"].loc[mask, "AuthorizationLevel"] = authorization_level
            context.tables["Employee"].loc[mask, "JobLevel"] = job_level
            context.tables["Employee"].loc[mask, "MaxApprovalAmount"] = 250000.0
            log_anomaly(
                context,
                "duplicate_executive_title_assignment",
                "Employee",
                int(row.EmployeeID),
                year,
                f"Employee title was changed to create a duplicate {title} assignment.",
                "Executive role uniqueness review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_missing_item_catalog_attribute(context: GenerationContext, count_per_year: int) -> None:
    if count_per_year <= 0:
        return
    items = context.tables["Item"]
    if items.empty:
        return
    required_columns_by_group = {
        "Furniture": "CollectionName",
        "Lighting": "Finish",
        "Textiles": "Color",
        "Accessories": "PrimaryMaterial",
    }

    for year in fiscal_years(context):
        used_ids = used_primary_keys(context, "Item", "missing_item_catalog_attribute")
        injected = 0
        for item_group, column_name in required_columns_by_group.items():
            candidates = items[
                items["ItemGroup"].eq(item_group)
                & items["IsActive"].astype(int).eq(1)
                & ~items["ItemID"].astype(int).isin(used_ids)
            ].sort_values("ItemID")
            if candidates.empty:
                continue
            row = candidates.iloc[0]
            mask = context.tables["Item"]["ItemID"].astype(int).eq(int(row["ItemID"]))
            context.tables["Item"].loc[mask, column_name] = None
            log_anomaly(
                context,
                "missing_item_catalog_attribute",
                "Item",
                int(row["ItemID"]),
                year,
                f"Item catalog attribute {column_name} was cleared for an active {item_group} item.",
                "Missing product catalog attribute review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_discontinued_item_in_new_activity(context: GenerationContext, count_per_year: int) -> None:
    if count_per_year <= 0:
        return
    sales_orders = context.tables["SalesOrder"]
    order_lines = context.tables["SalesOrderLine"]
    if sales_orders.empty or order_lines.empty:
        return

    order_dates = sales_orders.set_index("SalesOrderID")["OrderDate"].to_dict()
    item_usage = order_lines.copy()
    item_usage["OrderDate"] = item_usage["SalesOrderID"].astype(int).map(order_dates)

    for year in fiscal_years(context):
        used_ids = used_primary_keys(context, "Item", "discontinued_item_in_new_activity")
        candidates = item_usage[
            pd.to_datetime(item_usage["OrderDate"], errors="coerce").dt.year.eq(year)
            & ~item_usage["ItemID"].astype(int).isin(used_ids)
        ].sort_values(["OrderDate", "ItemID"])
        injected = 0
        for row in candidates.itertuples(index=False):
            mask = context.tables["Item"]["ItemID"].astype(int).eq(int(row.ItemID))
            item_rows = context.tables["Item"].loc[mask]
            if item_rows.empty or str(item_rows.iloc[0]["ItemGroup"]) not in {"Furniture", "Lighting", "Textiles", "Accessories"}:
                continue
            context.tables["Item"].loc[mask, "LifecycleStatus"] = "Discontinued"
            context.tables["Item"].loc[mask, "IsActive"] = 0
            log_anomaly(
                context,
                "discontinued_item_in_new_activity",
                "Item",
                int(row.ItemID),
                year,
                "Item was marked discontinued even though new operational activity still references it.",
                "Discontinued item activity review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_approval_above_authority_limit(context: GenerationContext, count_per_year: int) -> None:
    if count_per_year <= 0:
        return

    for year in fiscal_years(context):
        documents = approval_document_rows(context, year)
        if documents.empty:
            continue
        injected = 0
        for row in documents.itertuples(index=False):
            used_ids = used_primary_keys(context, str(row.TableName))
            if int(row.PrimaryKeyValue) in used_ids:
                continue
            if pd.isna(row.DocumentAmount) or float(row.DocumentAmount) <= 0:
                continue
            creator_employee_id = None if pd.isna(row.CreatorEmployeeIDValue) else int(row.CreatorEmployeeIDValue)
            candidates = approval_candidate_employees(
                context,
                event_date=pd.Timestamp(row.EventDateValue),
                current_approver_id=int(row.ApprovedByEmployeeIDValue),
                creator_employee_id=creator_employee_id,
            )
            if candidates.empty:
                continue
            candidates = candidates[candidates["MaxApprovalAmount"].astype(float) < float(row.DocumentAmount)]
            if candidates.empty:
                continue
            candidates = candidates.sort_values(["MaxApprovalAmount", "EmployeeID"], ascending=[False, True])
            selected = candidates.iloc[0]
            reassign_document_approver(
                context,
                table_name=str(row.TableName),
                pk_column=str(row.PrimaryKeyColumn),
                pk_value=int(row.PrimaryKeyValue),
                employee_id=int(selected["EmployeeID"]),
            )
            log_anomaly(
                context,
                "approval_above_authority_limit",
                str(row.TableName),
                int(row.PrimaryKeyValue),
                year,
                f"{row.DocumentType} approver was changed to an active employee whose approval limit is below the document amount.",
                "Approval authority limit review for document amounts above approver MaxApprovalAmount.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_unexpected_role_family_approval(context: GenerationContext, count_per_year: int) -> None:
    if count_per_year <= 0:
        return

    for year in fiscal_years(context):
        documents = approval_document_rows(context, year)
        if documents.empty:
            continue
        injected = 0
        for row in documents.itertuples(index=False):
            used_ids = used_primary_keys(context, str(row.TableName))
            if int(row.PrimaryKeyValue) in used_ids:
                continue
            creator_employee_id = None if pd.isna(row.CreatorEmployeeIDValue) else int(row.CreatorEmployeeIDValue)
            candidates = approval_candidate_employees(
                context,
                event_date=pd.Timestamp(row.EventDateValue),
                current_approver_id=int(row.ApprovedByEmployeeIDValue),
                creator_employee_id=creator_employee_id,
            )
            if candidates.empty:
                continue
            expected_families = APPROVAL_ROLE_FAMILIES_BY_DOCUMENT.get(str(row.DocumentType), set())
            candidates = candidates[~candidates["JobFamily"].isin(expected_families)]
            if candidates.empty:
                continue
            sufficient = candidates[candidates["MaxApprovalAmount"].astype(float) >= float(row.DocumentAmount)]
            selected_pool = sufficient if not sufficient.empty else candidates
            selected_pool = selected_pool.sort_values(["MaxApprovalAmount", "EmployeeID"], ascending=[True, True])
            selected = selected_pool.iloc[0]
            reassign_document_approver(
                context,
                table_name=str(row.TableName),
                pk_column=str(row.PrimaryKeyColumn),
                pk_value=int(row.PrimaryKeyValue),
                employee_id=int(selected["EmployeeID"]),
            )
            log_anomaly(
                context,
                "unexpected_role_family_approval",
                str(row.TableName),
                int(row.PrimaryKeyValue),
                year,
                f"{row.DocumentType} approver was changed to an active employee from an unexpected role family.",
                "Approval-role-family review using expected approver job-family guidance.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_inactive_employee_current_assignment(context: GenerationContext, count_per_year: int) -> None:
    if count_per_year <= 0:
        return

    inactive_employees = current_state_inactive_employee_rows(context)
    if inactive_employees.empty:
        return

    assignment_specs = [
        ("CostCenter", "ManagerID", "stale cost-center manager assignment"),
        ("Warehouse", "ManagerID", "stale warehouse manager assignment"),
        ("WorkCenter", "ManagerEmployeeID", "stale work-center manager assignment"),
        ("Customer", "SalesRepEmployeeID", "stale customer sales-rep assignment"),
    ]

    for year in fiscal_years(context):
        injected = 0
        for table_name, employee_column, assignment_label in assignment_specs:
            table = context.tables[table_name]
            if table.empty or employee_column not in table.columns:
                continue
            pk_column = table.columns[0]
            used_ids = used_primary_keys(context, table_name, "inactive_employee_current_assignment")
            candidates = table[
                table[employee_column].notna()
                & ~table[pk_column].astype(int).isin(used_ids)
            ].sort_values(pk_column)
            if candidates.empty:
                continue
            selected_row = candidates.iloc[0]
            employee_id = int(inactive_employees.iloc[(year - fiscal_years(context)[0] + injected) % len(inactive_employees)]["EmployeeID"])
            mask = context.tables[table_name][pk_column].astype(int).eq(int(selected_row[pk_column]))
            context.tables[table_name].loc[mask, employee_column] = employee_id
            log_anomaly(
                context,
                "inactive_employee_current_assignment",
                table_name,
                int(selected_row[pk_column]),
                year,
                f"{assignment_label.capitalize()} was reassigned to an inactive employee in the current-state master data.",
                "Current-state employee assignment review for inactive or terminated owners.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_prelaunch_item_in_new_activity(context: GenerationContext, count_per_year: int) -> None:
    if count_per_year <= 0:
        return

    items = context.tables["Item"]
    if items.empty:
        return
    sellable_groups = {"Furniture", "Lighting", "Textiles", "Accessories"}

    for year in fiscal_years(context):
        activity_rows = item_activity_rows(context, year)
        if activity_rows.empty:
            continue
        used_ids = used_primary_keys(context, "Item")
        injected = 0
        for row in activity_rows.itertuples(index=False):
            if int(row.ItemID) in used_ids:
                continue
            item_mask = context.tables["Item"]["ItemID"].astype(int).eq(int(row.ItemID))
            item_rows = context.tables["Item"].loc[item_mask]
            if item_rows.empty:
                continue
            item = item_rows.iloc[0]
            if str(item["ItemGroup"]) not in sellable_groups or int(item["IsActive"]) != 1:
                continue
            offset_days = 15 + (int(row.PrimaryKeyValue) % 31)
            launch_date = (pd.Timestamp(row.ActivityDateValue) + pd.Timedelta(days=offset_days)).strftime("%Y-%m-%d")
            context.tables["Item"].loc[item_mask, "LaunchDate"] = launch_date
            log_anomaly(
                context,
                "prelaunch_item_in_new_activity",
                "Item",
                int(row.ItemID),
                year,
                f"Item launch date was moved after {row.TableName} activity so the item appears in use before launch.",
                "Discontinued or pre-launch item activity review for activity dated before item LaunchDate.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_item_status_alignment_conflict(context: GenerationContext, count_per_year: int) -> None:
    if count_per_year <= 0:
        return

    items = context.tables["Item"]
    if items.empty:
        return
    sellable_groups = {"Furniture", "Lighting", "Textiles", "Accessories"}

    for year in fiscal_years(context):
        used_ids = used_primary_keys(context, "Item")
        candidates = items[
            items["ItemGroup"].isin(sellable_groups)
            & items["IsActive"].astype(int).eq(1)
            & ~items["ItemID"].astype(int).isin(used_ids)
        ].sort_values("ItemID")
        injected = 0
        for row in candidates.itertuples(index=False):
            mask = context.tables["Item"]["ItemID"].astype(int).eq(int(row.ItemID))
            context.tables["Item"].loc[mask, "LifecycleStatus"] = "Discontinued"
            context.tables["Item"].loc[mask, "IsActive"] = 1
            log_anomaly(
                context,
                "item_status_alignment_conflict",
                "Item",
                int(row.ItemID),
                year,
                "Item lifecycle status was set to Discontinued while the current-state IsActive flag remained 1.",
                "Item status alignment review for discontinued items still marked active.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_missing_final_punch(context: GenerationContext, count_per_year: int) -> None:
    punches = context.tables["TimeClockPunch"]
    time_clocks = context.tables["TimeClockEntry"]
    if punches.empty or time_clocks.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        used_ids = used_primary_keys(context, "TimeClockEntry", "missing_final_punch")
        year_entries = rows_for_year(time_clocks, "WorkDate", year)
        if used_ids:
            year_entries = year_entries[~year_entries["TimeClockEntryID"].astype(int).isin(used_ids)]
        injected = 0
        for row in year_entries.sort_values(["WorkDate", "TimeClockEntryID"]).itertuples(index=False):
            entry_punches = punches[
                punches["TimeClockEntryID"].astype(int).eq(int(row.TimeClockEntryID))
            ].sort_values(["SequenceNumber", "TimeClockPunchID"])
            clock_out_rows = entry_punches[entry_punches["PunchType"].eq("Clock Out")]
            if clock_out_rows.empty:
                continue
            target_punch_id = int(clock_out_rows.iloc[-1]["TimeClockPunchID"])
            context.tables["TimeClockPunch"] = context.tables["TimeClockPunch"][
                ~context.tables["TimeClockPunch"]["TimeClockPunchID"].astype(int).eq(target_punch_id)
            ].reset_index(drop=True)
            time_clock_mask = context.tables["TimeClockEntry"]["TimeClockEntryID"].astype(int).eq(int(row.TimeClockEntryID))
            context.tables["TimeClockEntry"].loc[time_clock_mask, "ClockOutTime"] = None
            context.tables["TimeClockEntry"].loc[time_clock_mask, "ClockStatus"] = "Pending"
            append_attendance_exception(
                context,
                int(row.EmployeeID),
                int(row.PayrollPeriodID),
                str(row.WorkDate),
                None if pd.isna(row.ShiftDefinitionID) else int(row.ShiftDefinitionID),
                None if pd.isna(row.EmployeeShiftRosterID) else int(row.EmployeeShiftRosterID),
                int(row.TimeClockEntryID),
                "Missing Final Punch",
                "High",
                0.0,
            )
            log_anomaly(
                context,
                "missing_final_punch",
                "TimeClockEntry",
                int(row.TimeClockEntryID),
                year,
                "Clock-out punch was removed from a worked day, leaving the time summary incomplete.",
                "Overlapping or incomplete punch review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_punch_without_roster(context: GenerationContext, count_per_year: int) -> None:
    punches = context.tables["TimeClockPunch"]
    if punches.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        year_rows = rows_for_year(punches, "WorkDate", year)
        used_ids = used_primary_keys(context, "TimeClockPunch", "punch_without_roster")
        if used_ids:
            year_rows = year_rows[~year_rows["TimeClockPunchID"].astype(int).isin(used_ids)]
        injected = 0
        for row in year_rows.sort_values(["WorkDate", "TimeClockPunchID"]).itertuples(index=False):
            if pd.isna(row.EmployeeShiftRosterID):
                continue
            punch_mask = context.tables["TimeClockPunch"]["TimeClockPunchID"].astype(int).eq(int(row.TimeClockPunchID))
            context.tables["TimeClockPunch"].loc[punch_mask, "EmployeeShiftRosterID"] = None
            log_anomaly(
                context,
                "punch_without_roster",
                "TimeClockPunch",
                int(row.TimeClockPunchID),
                year,
                "Raw punch row was detached from its scheduled roster row while the worked day remained otherwise intact.",
                "Scheduled-without-punch and punch-without-schedule review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_absence_with_worked_time(context: GenerationContext, count_per_year: int) -> None:
    time_clocks = context.tables["TimeClockEntry"]
    rosters = context.tables["EmployeeShiftRoster"]
    absences = context.tables["EmployeeAbsence"]
    if time_clocks.empty or rosters.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        year_rows = rows_for_year(time_clocks, "WorkDate", year)
        used_ids = used_primary_keys(context, "TimeClockEntry", "absence_with_worked_time")
        if used_ids:
            year_rows = year_rows[~year_rows["TimeClockEntryID"].astype(int).isin(used_ids)]
        injected = 0
        for row in year_rows.sort_values(["WorkDate", "TimeClockEntryID"]).itertuples(index=False):
            if pd.isna(row.EmployeeShiftRosterID):
                continue
            roster_id = int(row.EmployeeShiftRosterID)
            roster_mask = context.tables["EmployeeShiftRoster"]["EmployeeShiftRosterID"].astype(int).eq(roster_id)
            if not roster_mask.any():
                continue
            context.tables["EmployeeShiftRoster"].loc[roster_mask, "RosterStatus"] = "Absent"
            existing_absence = absences[
                absences["EmployeeShiftRosterID"].astype(float).eq(float(roster_id))
            ] if not absences.empty else absences
            if existing_absence.empty:
                context.tables["EmployeeAbsence"] = pd.concat(
                    [
                        context.tables["EmployeeAbsence"],
                        pd.DataFrame(
                            [{
                                "EmployeeAbsenceID": next_id(context, "EmployeeAbsence"),
                                "EmployeeID": int(row.EmployeeID),
                                "PayrollPeriodID": int(row.PayrollPeriodID),
                                "AbsenceDate": str(row.WorkDate),
                                "EmployeeShiftRosterID": roster_id,
                                "AbsenceType": "Sick",
                                "HoursAbsent": money(float(row.RegularHours) + float(row.OvertimeHours)),
                                "IsPaid": 1,
                                "ApprovedByEmployeeID": None if pd.isna(row.ApprovedByEmployeeID) else int(row.ApprovedByEmployeeID),
                                "ApprovedDate": str(row.WorkDate),
                                "Status": "Approved",
                            }],
                            columns=TABLE_COLUMNS["EmployeeAbsence"],
                        ),
                    ],
                    ignore_index=True,
                )
            log_anomaly(
                context,
                "absence_with_worked_time",
                "TimeClockEntry",
                int(row.TimeClockEntryID),
                year,
                "Roster status was changed to Absent and an absence row was added even though worked time remained recorded.",
                "Absence-with-worked-time review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_overtime_without_approval(context: GenerationContext, count_per_year: int) -> None:
    time_clocks = context.tables["TimeClockEntry"]
    if time_clocks.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        candidates = rows_for_year(time_clocks, "WorkDate", year)
        candidates = candidates[
            candidates["OvertimeApprovalID"].notna()
            & candidates["OvertimeHours"].astype(float).gt(0.5)
        ]
        used_ids = used_primary_keys(context, "TimeClockEntry", "overtime_without_approval")
        if used_ids:
            candidates = candidates[~candidates["TimeClockEntryID"].astype(int).isin(used_ids)]
        injected = 0
        for row in candidates.sort_values(["WorkDate", "TimeClockEntryID"]).itertuples(index=False):
            mask = context.tables["TimeClockEntry"]["TimeClockEntryID"].astype(int).eq(int(row.TimeClockEntryID))
            context.tables["TimeClockEntry"].loc[mask, "OvertimeApprovalID"] = None
            log_anomaly(
                context,
                "overtime_without_approval",
                "TimeClockEntry",
                int(row.TimeClockEntryID),
                year,
                "Recorded overtime remained on the time summary after the linked overtime approval was removed.",
                "Overtime without approval review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_roster_after_termination(context: GenerationContext, count_per_year: int) -> None:
    rosters = context.tables["EmployeeShiftRoster"]
    if rosters.empty or count_per_year <= 0:
        return
    terminated = terminated_employee_rows(context)
    terminated = terminated[terminated["PayClass"].eq("Hourly")].copy()
    if terminated.empty:
        return

    for year in fiscal_years(context):
        year_rows = rows_for_year(rosters, "RosterDate", year)
        used_ids = used_primary_keys(context, "EmployeeShiftRoster", "roster_after_termination")
        if used_ids:
            year_rows = year_rows[~year_rows["EmployeeShiftRosterID"].astype(int).isin(used_ids)]
        injected = 0
        for row in year_rows.sort_values(["RosterDate", "EmployeeShiftRosterID"]).itertuples(index=False):
            roster_date = pd.Timestamp(row.RosterDate)
            eligible = terminated[terminated["TerminationDateValue"].lt(roster_date)]
            if eligible.empty:
                continue
            employee_id = int(eligible.iloc[0]["EmployeeID"])
            roster_mask = context.tables["EmployeeShiftRoster"]["EmployeeShiftRosterID"].astype(int).eq(int(row.EmployeeShiftRosterID))
            context.tables["EmployeeShiftRoster"].loc[roster_mask, "EmployeeID"] = employee_id
            time_clock_mask = (
                context.tables["TimeClockEntry"]["EmployeeShiftRosterID"].notna()
                & context.tables["TimeClockEntry"]["EmployeeShiftRosterID"].astype(int).eq(int(row.EmployeeShiftRosterID))
            )
            if time_clock_mask.any():
                context.tables["TimeClockEntry"].loc[time_clock_mask, "EmployeeID"] = employee_id
                linked_time_clock_ids = context.tables["TimeClockEntry"].loc[time_clock_mask, "TimeClockEntryID"].astype(int).tolist()
                if linked_time_clock_ids:
                    punch_mask = (
                        context.tables["TimeClockPunch"]["TimeClockEntryID"].notna()
                        & context.tables["TimeClockPunch"]["TimeClockEntryID"].astype(int).isin(linked_time_clock_ids)
                    )
                    if punch_mask.any():
                        context.tables["TimeClockPunch"].loc[punch_mask, "EmployeeID"] = employee_id
                    labor_mask = (
                        context.tables["LaborTimeEntry"]["TimeClockEntryID"].notna()
                        & context.tables["LaborTimeEntry"]["TimeClockEntryID"].astype(int).isin(linked_time_clock_ids)
                    )
                    if labor_mask.any():
                        context.tables["LaborTimeEntry"].loc[labor_mask, "EmployeeID"] = employee_id
            absence_mask = (
                context.tables["EmployeeAbsence"]["EmployeeShiftRosterID"].notna()
                & context.tables["EmployeeAbsence"]["EmployeeShiftRosterID"].astype(int).eq(int(row.EmployeeShiftRosterID))
            ) if not context.tables["EmployeeAbsence"].empty else pd.Series(dtype=bool)
            if not context.tables["EmployeeAbsence"].empty and absence_mask.any():
                context.tables["EmployeeAbsence"].loc[absence_mask, "EmployeeID"] = employee_id
            overtime_mask = (
                context.tables["OvertimeApproval"]["EmployeeShiftRosterID"].notna()
                & context.tables["OvertimeApproval"]["EmployeeShiftRosterID"].astype(int).eq(int(row.EmployeeShiftRosterID))
            ) if not context.tables["OvertimeApproval"].empty else pd.Series(dtype=bool)
            if not context.tables["OvertimeApproval"].empty and overtime_mask.any():
                context.tables["OvertimeApproval"].loc[overtime_mask, "EmployeeID"] = employee_id
            log_anomaly(
                context,
                "roster_after_termination",
                "EmployeeShiftRoster",
                int(row.EmployeeShiftRosterID),
                year,
                "Shift roster and linked attendance rows were reassigned to an employee terminated before the roster date.",
                "Roster-after-termination review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_overlapping_punch_sequence(context: GenerationContext, count_per_year: int) -> None:
    punches = context.tables["TimeClockPunch"]
    if punches.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        year_rows = rows_for_year(punches, "WorkDate", year)
        if year_rows.empty:
            continue
        used_ids = used_primary_keys(context, "TimeClockEntry", "overlapping_punch_sequence")
        grouped = year_rows.sort_values(["TimeClockEntryID", "SequenceNumber", "TimeClockPunchID"]).groupby("TimeClockEntryID")
        injected = 0
        for time_clock_entry_id, group in grouped:
            if int(time_clock_entry_id) in used_ids or len(group) < 4:
                continue
            meal_start = group[group["PunchType"].eq("Meal Start")]
            meal_end = group[group["PunchType"].eq("Meal End")]
            if meal_start.empty or meal_end.empty:
                continue
            meal_start_row = meal_start.iloc[0]
            meal_end_row = meal_end.iloc[0]
            overlap_timestamp = (
                pd.Timestamp(meal_start_row["PunchTimestamp"]) - pd.Timedelta(minutes=10)
            ).strftime("%Y-%m-%d %H:%M:%S")
            punch_mask = context.tables["TimeClockPunch"]["TimeClockPunchID"].astype(int).eq(int(meal_end_row["TimeClockPunchID"]))
            context.tables["TimeClockPunch"].loc[punch_mask, "PunchTimestamp"] = overlap_timestamp
            log_anomaly(
                context,
                "overlapping_punch_sequence",
                "TimeClockEntry",
                int(time_clock_entry_id),
                year,
                "Meal-end punch was moved before meal-start punch so the raw punch sequence overlaps.",
                "Overlapping or incomplete punch review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_missing_forecast_approval(context: GenerationContext, count_per_year: int) -> None:
    forecasts = context.tables["DemandForecast"]
    if forecasts.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        year_rows = rows_for_year(forecasts, "ForecastWeekStartDate", year)
        used_ids = used_primary_keys(context, "DemandForecast", "missing_forecast_approval")
        year_rows = year_rows[~year_rows["DemandForecastID"].astype(int).isin(used_ids)]
        injected = 0
        for row in year_rows.sort_values(["ForecastWeekStartDate", "DemandForecastID"]).itertuples(index=False):
            mask = context.tables["DemandForecast"]["DemandForecastID"].astype(int).eq(int(row.DemandForecastID))
            context.tables["DemandForecast"].loc[mask, "ApprovedByEmployeeID"] = None
            context.tables["DemandForecast"].loc[mask, "ApprovedDate"] = None
            log_anomaly(
                context,
                "missing_forecast_approval",
                "DemandForecast",
                int(row.DemandForecastID),
                year,
                "Forecast approval fields were cleared from an active weekly demand forecast row.",
                "Forecast approval and override review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_inactive_policy_for_active_item(context: GenerationContext, count_per_year: int) -> None:
    policies = context.tables["InventoryPolicy"]
    if policies.empty or count_per_year <= 0:
        return

    items = context.tables["Item"]
    active_item_ids = set(
        items.loc[
            items["IsActive"].astype(int).eq(1)
            & items["InventoryAccountID"].notna(),
            "ItemID",
        ].astype(int).tolist()
    )
    candidates = policies[
        policies["IsActive"].astype(int).eq(1)
        & policies["ItemID"].astype(int).isin(active_item_ids)
    ].copy()
    if candidates.empty:
        return

    for year in fiscal_years(context):
        used_ids = used_primary_keys(context, "InventoryPolicy", "inactive_policy_for_active_item")
        injected = 0
        for row in candidates.sort_values(["ItemID", "WarehouseID", "InventoryPolicyID"]).itertuples(index=False):
            if int(row.InventoryPolicyID) in used_ids:
                continue
            mask = context.tables["InventoryPolicy"]["InventoryPolicyID"].astype(int).eq(int(row.InventoryPolicyID))
            context.tables["InventoryPolicy"].loc[mask, "IsActive"] = 0
            log_anomaly(
                context,
                "inactive_policy_for_active_item",
                "InventoryPolicy",
                int(row.InventoryPolicyID),
                year,
                "An active inventory item was left with an inactive planning policy row.",
                "Inactive or stale inventory policy review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_purchase_requisition_without_plan(context: GenerationContext, count_per_year: int) -> None:
    requisitions = context.tables["PurchaseRequisition"]
    if requisitions.empty or count_per_year <= 0 or "SupplyPlanRecommendationID" not in requisitions.columns:
        return

    for year in fiscal_years(context):
        year_rows = rows_for_year(requisitions, "RequestDate", year)
        candidates = year_rows[year_rows["SupplyPlanRecommendationID"].notna()].copy()
        used_ids = used_primary_keys(context, "PurchaseRequisition", "purchase_requisition_without_plan")
        injected = 0
        for row in candidates.sort_values(["RequestDate", "RequisitionID"]).itertuples(index=False):
            if int(row.RequisitionID) in used_ids:
                continue
            mask = context.tables["PurchaseRequisition"]["RequisitionID"].astype(int).eq(int(row.RequisitionID))
            recommendation_id = int(row.SupplyPlanRecommendationID)
            context.tables["PurchaseRequisition"].loc[mask, "SupplyPlanRecommendationID"] = None
            recommendation_mask = context.tables["SupplyPlanRecommendation"]["SupplyPlanRecommendationID"].astype(int).eq(recommendation_id)
            if recommendation_mask.any():
                context.tables["SupplyPlanRecommendation"].loc[recommendation_mask, "RecommendationStatus"] = "Planned"
                context.tables["SupplyPlanRecommendation"].loc[recommendation_mask, "ConvertedDocumentType"] = None
                context.tables["SupplyPlanRecommendation"].loc[recommendation_mask, "ConvertedDocumentID"] = None
            log_anomaly(
                context,
                "purchase_requisition_without_plan",
                "PurchaseRequisition",
                int(row.RequisitionID),
                year,
                "A requisition converted from the planning layer had its planning recommendation link removed.",
                "Requisitions and work orders without planning support review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_work_order_without_plan(context: GenerationContext, count_per_year: int) -> None:
    work_orders = context.tables["WorkOrder"]
    if work_orders.empty or count_per_year <= 0 or "SupplyPlanRecommendationID" not in work_orders.columns:
        return

    for year in fiscal_years(context):
        year_rows = rows_for_year(work_orders, "ReleasedDate", year)
        candidates = year_rows[year_rows["SupplyPlanRecommendationID"].notna()].copy()
        used_ids = used_primary_keys(context, "WorkOrder", "work_order_without_plan")
        injected = 0
        for row in candidates.sort_values(["ReleasedDate", "WorkOrderID"]).itertuples(index=False):
            if int(row.WorkOrderID) in used_ids:
                continue
            mask = context.tables["WorkOrder"]["WorkOrderID"].astype(int).eq(int(row.WorkOrderID))
            recommendation_id = int(row.SupplyPlanRecommendationID)
            context.tables["WorkOrder"].loc[mask, "SupplyPlanRecommendationID"] = None
            recommendation_mask = context.tables["SupplyPlanRecommendation"]["SupplyPlanRecommendationID"].astype(int).eq(recommendation_id)
            if recommendation_mask.any():
                context.tables["SupplyPlanRecommendation"].loc[recommendation_mask, "RecommendationStatus"] = "Planned"
                context.tables["SupplyPlanRecommendation"].loc[recommendation_mask, "ConvertedDocumentType"] = None
                context.tables["SupplyPlanRecommendation"].loc[recommendation_mask, "ConvertedDocumentID"] = None
            log_anomaly(
                context,
                "work_order_without_plan",
                "WorkOrder",
                int(row.WorkOrderID),
                year,
                "A work order created from the planning layer had its planning recommendation link removed.",
                "Requisitions and work orders without planning support review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_late_recommendation_conversion(context: GenerationContext, count_per_year: int) -> None:
    recommendations = context.tables["SupplyPlanRecommendation"]
    if recommendations.empty or count_per_year <= 0:
        return

    candidates = recommendations[recommendations["RecommendationStatus"].eq("Converted")].copy()
    if candidates.empty:
        return

    for year in fiscal_years(context):
        year_rows = rows_for_year(candidates, "ReleaseByDate", year)
        used_ids = used_primary_keys(context, "SupplyPlanRecommendation", "late_recommendation_conversion")
        injected = 0
        for row in year_rows.sort_values(["NeedByDate", "SupplyPlanRecommendationID"]).itertuples(index=False):
            if int(row.SupplyPlanRecommendationID) in used_ids:
                continue
            late_date = (pd.Timestamp(row.NeedByDate) + pd.Timedelta(days=5)).strftime("%Y-%m-%d")
            if str(row.ConvertedDocumentType) == "PurchaseRequisition" and pd.notna(row.ConvertedDocumentID):
                mask = context.tables["PurchaseRequisition"]["RequisitionID"].astype(int).eq(int(row.ConvertedDocumentID))
                if mask.any():
                    context.tables["PurchaseRequisition"].loc[mask, "RequestDate"] = late_date
                    context.tables["PurchaseRequisition"].loc[mask, "ApprovedDate"] = late_date
            elif str(row.ConvertedDocumentType) == "WorkOrder" and pd.notna(row.ConvertedDocumentID):
                mask = context.tables["WorkOrder"]["WorkOrderID"].astype(int).eq(int(row.ConvertedDocumentID))
                if mask.any():
                    context.tables["WorkOrder"].loc[mask, "ReleasedDate"] = late_date
            else:
                continue
            log_anomaly(
                context,
                "late_recommendation_conversion",
                "SupplyPlanRecommendation",
                int(row.SupplyPlanRecommendationID),
                year,
                "A converted planning recommendation was moved so the actual requisition or work-order release occurred after the need-by date.",
                "Recommendation converted after need-by date review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_forecast_override_outlier(context: GenerationContext, count_per_year: int) -> None:
    forecasts = context.tables["DemandForecast"]
    if forecasts.empty or count_per_year <= 0:
        return

    for year in fiscal_years(context):
        year_rows = rows_for_year(forecasts, "ForecastWeekStartDate", year)
        used_ids = used_primary_keys(context, "DemandForecast", "forecast_override_outlier")
        injected = 0
        for row in year_rows.sort_values(["ForecastWeekStartDate", "DemandForecastID"]).itertuples(index=False):
            if int(row.DemandForecastID) in used_ids:
                continue
            baseline = max(float(row.BaselineForecastQuantity), 1.0)
            override_quantity = qty(baseline * 3.10)
            mask = context.tables["DemandForecast"]["DemandForecastID"].astype(int).eq(int(row.DemandForecastID))
            context.tables["DemandForecast"].loc[mask, "ForecastQuantity"] = override_quantity
            context.tables["DemandForecast"].loc[mask, "ForecastMethod"] = "Planner Adjusted"
            log_anomaly(
                context,
                "forecast_override_outlier",
                "DemandForecast",
                int(row.DemandForecastID),
                year,
                "A weekly forecast was overridden far above its baseline so override reasonableness can be reviewed.",
                "Forecast approval and override review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def pricing_method_from_price_list_line(context: GenerationContext, price_list_line_id: int | None) -> str:
    if price_list_line_id is None or pd.isna(price_list_line_id):
        return "Base List"
    line_rows = context.tables["PriceListLine"][
        context.tables["PriceListLine"]["PriceListLineID"].astype(int).eq(int(price_list_line_id))
    ]
    if line_rows.empty:
        return "Base List"
    price_list_id = int(line_rows.iloc[0]["PriceListID"])
    header_rows = context.tables["PriceList"][
        context.tables["PriceList"]["PriceListID"].astype(int).eq(price_list_id)
    ]
    if header_rows.empty:
        return "Base List"
    return "Customer Price List" if str(header_rows.iloc[0]["ScopeType"]) == "Customer" else "Segment Price List"


def update_sales_pricing_lineage(
    context: GenerationContext,
    sales_order_line_id: int,
    updates: dict[str, Any],
) -> None:
    order_mask = context.tables["SalesOrderLine"]["SalesOrderLineID"].astype(int).eq(int(sales_order_line_id))
    if order_mask.any():
        for column_name, value in updates.items():
            context.tables["SalesOrderLine"].loc[order_mask, column_name] = value

    invoice_mask = context.tables["SalesInvoiceLine"]["SalesOrderLineID"].astype(int).eq(int(sales_order_line_id))
    if invoice_mask.any():
        for column_name, value in updates.items():
            if column_name in context.tables["SalesInvoiceLine"].columns:
                context.tables["SalesInvoiceLine"].loc[invoice_mask, column_name] = value


def inject_missing_price_override_approval(context: GenerationContext, count_per_year: int) -> None:
    approvals = context.tables["PriceOverrideApproval"]
    if approvals.empty or count_per_year <= 0:
        return

    order_lines = context.tables["SalesOrderLine"]
    for year in fiscal_years(context):
        year_lines = rows_for_year(
            order_lines.merge(context.tables["SalesOrder"][["SalesOrderID", "OrderDate"]], on="SalesOrderID", how="left"),
            "OrderDate",
            year,
        )
        candidates = year_lines[year_lines["PriceOverrideApprovalID"].notna()].copy()
        used_ids = used_primary_keys(context, "PriceOverrideApproval", "missing_price_override_approval")
        injected = 0
        for row in candidates.sort_values(["OrderDate", "SalesOrderLineID"]).itertuples(index=False):
            approval_id = int(row.PriceOverrideApprovalID)
            if approval_id in used_ids:
                continue
            mask = context.tables["PriceOverrideApproval"]["PriceOverrideApprovalID"].astype(int).eq(approval_id)
            if not mask.any():
                continue
            context.tables["PriceOverrideApproval"].loc[mask, "ApprovedByEmployeeID"] = None
            context.tables["PriceOverrideApproval"].loc[mask, "ApprovedDate"] = None
            context.tables["PriceOverrideApproval"].loc[mask, "Status"] = "Pending"
            log_anomaly(
                context,
                "missing_price_override_approval",
                "PriceOverrideApproval",
                approval_id,
                year,
                "A sales-price override approval record was left incomplete even though the sales line still references the override.",
                "Override approval completeness review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_expired_price_list_used(context: GenerationContext, count_per_year: int) -> None:
    order_lines = context.tables["SalesOrderLine"]
    sales_orders = context.tables["SalesOrder"]
    if order_lines.empty or sales_orders.empty or count_per_year <= 0:
        return

    used_lines = order_lines[order_lines["PriceListLineID"].notna()].merge(
        sales_orders[["SalesOrderID", "OrderDate"]],
        on="SalesOrderID",
        how="left",
    )
    price_list_lines = context.tables["PriceListLine"][["PriceListLineID", "PriceListID"]]
    used_lines = used_lines.merge(price_list_lines, on="PriceListLineID", how="left")
    for year in fiscal_years(context):
        year_rows = rows_for_year(used_lines, "OrderDate", year)
        used_ids = used_primary_keys(context, "PriceList", "expired_price_list_used")
        injected = 0
        for row in year_rows.sort_values(["OrderDate", "SalesOrderLineID"]).itertuples(index=False):
            price_list_id = int(row.PriceListID)
            if price_list_id in used_ids:
                continue
            mask = context.tables["PriceList"]["PriceListID"].astype(int).eq(price_list_id)
            if not mask.any():
                continue
            expired_end = (pd.Timestamp(row.OrderDate) - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
            context.tables["PriceList"].loc[mask, "EffectiveEndDate"] = expired_end
            context.tables["PriceList"].loc[mask, "Status"] = "Expired"
            log_anomaly(
                context,
                "expired_price_list_used",
                "PriceList",
                price_list_id,
                year,
                "A price list used on a sales line was back-dated to expire before the order date.",
                "Expired or overlapping price-list review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_overlapping_active_price_list(context: GenerationContext, count_per_year: int) -> None:
    price_lists = context.tables["PriceList"]
    if price_lists.empty or count_per_year <= 0:
        return

    segment_lists = price_lists[
        price_lists["ScopeType"].eq("Segment")
        & price_lists["Status"].eq("Active")
    ].sort_values(["CustomerSegment", "PriceListID"])
    if segment_lists.empty:
        return

    for year in fiscal_years(context):
        used_ids = used_primary_keys(context, "PriceList", "overlapping_active_price_list")
        injected = 0
        for row in segment_lists.itertuples(index=False):
            if int(row.PriceListID) in used_ids:
                continue
            duplicate_id = next_id(context, "PriceList")
            duplicate_row = {
                "PriceListID": duplicate_id,
                "PriceListName": f"{row.PriceListName} Overlap",
                "ScopeType": str(row.ScopeType),
                "CustomerID": None if pd.isna(row.CustomerID) else int(row.CustomerID),
                "CustomerSegment": str(row.CustomerSegment),
                "EffectiveStartDate": row.EffectiveStartDate,
                "EffectiveEndDate": row.EffectiveEndDate,
                "CurrencyCode": str(row.CurrencyCode),
                "Status": "Active",
                "ApprovedByEmployeeID": None if pd.isna(row.ApprovedByEmployeeID) else int(row.ApprovedByEmployeeID),
                "ApprovedDate": row.ApprovedDate,
            }
            context.tables["PriceList"] = pd.concat(
                [context.tables["PriceList"], pd.DataFrame([duplicate_row], columns=TABLE_COLUMNS["PriceList"])],
                ignore_index=True,
            )
            log_anomaly(
                context,
                "overlapping_active_price_list",
                "PriceList",
                duplicate_id,
                year,
                "A second active price list was created for the same segment scope and overlapping date range.",
                "Expired or overlapping price-list review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_promotion_outside_effective_dates(context: GenerationContext, count_per_year: int) -> None:
    order_lines = context.tables["SalesOrderLine"]
    sales_orders = context.tables["SalesOrder"]
    if order_lines.empty or sales_orders.empty or count_per_year <= 0:
        return

    used_lines = order_lines[order_lines["PromotionID"].notna()].merge(
        sales_orders[["SalesOrderID", "OrderDate"]],
        on="SalesOrderID",
        how="left",
    )
    for year in fiscal_years(context):
        year_rows = rows_for_year(used_lines, "OrderDate", year)
        used_ids = used_primary_keys(context, "PromotionProgram", "promotion_outside_effective_dates")
        injected = 0
        for row in year_rows.sort_values(["OrderDate", "SalesOrderLineID"]).itertuples(index=False):
            promotion_id = int(row.PromotionID)
            if promotion_id in used_ids:
                continue
            mask = context.tables["PromotionProgram"]["PromotionID"].astype(int).eq(promotion_id)
            if not mask.any():
                continue
            context.tables["PromotionProgram"].loc[mask, "EffectiveEndDate"] = (
                pd.Timestamp(row.OrderDate) - pd.Timedelta(days=2)
            ).strftime("%Y-%m-%d")
            log_anomaly(
                context,
                "promotion_outside_effective_dates",
                "PromotionProgram",
                promotion_id,
                year,
                "A promotion referenced on a sales line was changed to end before the order date.",
                "Promotion scope/date mismatch review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_sale_below_price_floor_without_approval(context: GenerationContext, count_per_year: int) -> None:
    order_lines = context.tables["SalesOrderLine"]
    sales_orders = context.tables["SalesOrder"]
    if order_lines.empty or sales_orders.empty or count_per_year <= 0:
        return

    candidates = order_lines[order_lines["PriceOverrideApprovalID"].notna()].merge(
        sales_orders[["SalesOrderID", "OrderDate"]],
        on="SalesOrderID",
        how="left",
    )
    for year in fiscal_years(context):
        year_rows = rows_for_year(candidates, "OrderDate", year)
        used_ids = used_primary_keys(context, "SalesOrderLine", "sale_below_price_floor_without_approval")
        injected = 0
        for row in year_rows.sort_values(["OrderDate", "SalesOrderLineID"]).itertuples(index=False):
            sales_order_line_id = int(row.SalesOrderLineID)
            if sales_order_line_id in used_ids:
                continue
            pricing_method = pricing_method_from_price_list_line(
                context,
                None if pd.isna(row.PriceListLineID) else int(row.PriceListLineID),
            )
            update_sales_pricing_lineage(
                context,
                sales_order_line_id,
                {
                    "PriceOverrideApprovalID": None,
                    "PricingMethod": pricing_method,
                },
            )
            log_anomaly(
                context,
                "sale_below_price_floor_without_approval",
                "SalesOrderLine",
                sales_order_line_id,
                year,
                "A below-floor sales price remained on the line after the override-approval link was removed.",
                "Sales below floor without approval review.",
            )
            injected += 1
            if injected >= count_per_year:
                break


def inject_customer_specific_price_bypass(context: GenerationContext, count_per_year: int) -> None:
    customers = context.tables["Customer"][["CustomerID", "CustomerSegment"]]
    order_lines = context.tables["SalesOrderLine"]
    sales_orders = context.tables["SalesOrder"][["SalesOrderID", "CustomerID", "OrderDate"]]
    price_list_lines = context.tables["PriceListLine"][["PriceListLineID", "PriceListID", "ItemID", "MinimumQuantity"]]
    price_lists = context.tables["PriceList"][["PriceListID", "ScopeType", "CustomerID", "CustomerSegment"]]
    if order_lines.empty or sales_orders.empty or count_per_year <= 0:
        return

    merged = order_lines.merge(sales_orders, on="SalesOrderID", how="left").merge(customers, on="CustomerID", how="left")
    line_scope = price_list_lines.merge(price_lists, on="PriceListID", how="left")
    customer_specific_lines = line_scope[line_scope["ScopeType"].eq("Customer")].copy()
    segment_lines = line_scope[line_scope["ScopeType"].eq("Segment")].copy()
    if customer_specific_lines.empty or segment_lines.empty:
        return

    customer_specific_keys = set(
        zip(
            customer_specific_lines["CustomerID"].astype(int),
            customer_specific_lines["ItemID"].astype(int),
        )
    )
    segment_line_lookup: dict[tuple[str, int], int] = {}
    for row in segment_lines.sort_values(["CustomerSegment", "ItemID", "MinimumQuantity", "PriceListLineID"]).itertuples(index=False):
        cache_key = (str(row.CustomerSegment), int(row.ItemID))
        segment_line_lookup.setdefault(cache_key, int(row.PriceListLineID))

    candidates = merged[
        merged["PricingMethod"].eq("Customer Price List")
        & merged.apply(lambda row: (int(row.CustomerID), int(row.ItemID)) in customer_specific_keys, axis=1)
    ].copy()
    for year in fiscal_years(context):
        year_rows = rows_for_year(candidates, "OrderDate", year)
        used_ids = used_primary_keys(context, "SalesOrderLine", "customer_specific_price_bypass")
        injected = 0
        for row in year_rows.sort_values(["OrderDate", "SalesOrderLineID"]).itertuples(index=False):
            sales_order_line_id = int(row.SalesOrderLineID)
            if sales_order_line_id in used_ids:
                continue
            segment_line_id = segment_line_lookup.get((str(row.CustomerSegment), int(row.ItemID)))
            if segment_line_id is None:
                continue
            update_sales_pricing_lineage(
                context,
                sales_order_line_id,
                {
                    "PriceListLineID": segment_line_id,
                    "PricingMethod": "Segment Price List",
                },
            )
            log_anomaly(
                context,
                "customer_specific_price_bypass",
                "SalesOrderLine",
                sales_order_line_id,
                year,
                "A customer eligible for customer-specific pricing was switched to a non-customer-specific pricing path.",
                "Customer-specific price-list bypass review.",
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
    inject_terminated_employee_on_payroll(context, int(profile.get("terminated_employee_on_payroll_per_year", 0)))
    inject_terminated_employee_approval(context, int(profile.get("terminated_employee_approval_per_year", 0)))
    inject_inactive_employee_time_or_labor(context, int(profile.get("inactive_employee_time_or_labor_per_year", 0)))
    inject_duplicate_executive_title_assignment(context, int(profile.get("duplicate_executive_title_assignment_per_year", 0)))
    inject_missing_item_catalog_attribute(context, int(profile.get("missing_item_catalog_attribute_per_year", 0)))
    inject_discontinued_item_in_new_activity(context, int(profile.get("discontinued_item_in_new_activity_per_year", 0)))
    inject_approval_above_authority_limit(context, int(profile.get("approval_above_authority_limit_per_year", 0)))
    inject_unexpected_role_family_approval(context, int(profile.get("unexpected_role_family_approval_per_year", 0)))
    inject_inactive_employee_current_assignment(context, int(profile.get("inactive_employee_current_assignment_per_year", 0)))
    inject_prelaunch_item_in_new_activity(context, int(profile.get("prelaunch_item_in_new_activity_per_year", 0)))
    inject_item_status_alignment_conflict(context, int(profile.get("item_status_alignment_conflict_per_year", 0)))
    inject_missing_final_punch(context, int(profile.get("missing_final_punch_per_year", 0)))
    inject_punch_without_roster(context, int(profile.get("punch_without_roster_per_year", 0)))
    inject_absence_with_worked_time(context, int(profile.get("absence_with_worked_time_per_year", 0)))
    inject_overtime_without_approval(context, int(profile.get("overtime_without_approval_per_year", 0)))
    inject_roster_after_termination(context, int(profile.get("roster_after_termination_per_year", 0)))
    inject_overlapping_punch_sequence(context, int(profile.get("overlapping_punch_sequence_per_year", 0)))
    inject_missing_forecast_approval(context, int(profile.get("missing_forecast_approval_per_year", 0)))
    inject_inactive_policy_for_active_item(context, int(profile.get("inactive_policy_for_active_item_per_year", 0)))
    inject_purchase_requisition_without_plan(context, int(profile.get("purchase_requisition_without_plan_per_year", 0)))
    inject_work_order_without_plan(context, int(profile.get("work_order_without_plan_per_year", 0)))
    inject_late_recommendation_conversion(context, int(profile.get("late_recommendation_conversion_per_year", 0)))
    inject_forecast_override_outlier(context, int(profile.get("forecast_override_outlier_per_year", 0)))
    inject_missing_price_override_approval(context, int(profile.get("missing_price_override_approval_per_year", 0)))
    inject_expired_price_list_used(context, int(profile.get("expired_price_list_used_per_year", 0)))
    inject_overlapping_active_price_list(context, int(profile.get("overlapping_active_price_list_per_year", 0)))
    inject_promotion_outside_effective_dates(context, int(profile.get("promotion_outside_effective_dates_per_year", 0)))
    inject_sale_below_price_floor_without_approval(context, int(profile.get("sale_below_price_floor_without_approval_per_year", 0)))
    inject_customer_specific_price_bypass(context, int(profile.get("customer_specific_price_bypass_per_year", 0)))
    invalidate_all_caches(context)
