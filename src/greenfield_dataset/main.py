from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

import pandas as pd

from greenfield_dataset.anomalies import inject_anomalies
from greenfield_dataset.budgets import generate_budgets, generate_opening_balances
from greenfield_dataset.exporters import export_excel, export_sqlite, export_validation_report
from greenfield_dataset.journals import generate_recurring_manual_journals, generate_year_end_close_journals
from greenfield_dataset.master_data import (
    backfill_cost_center_managers,
    generate_cost_centers,
    generate_customers,
    generate_employees,
    generate_items,
    generate_suppliers,
    generate_warehouses,
    load_accounts,
)
from greenfield_dataset.o2c import (
    generate_month_cash_receipts,
    generate_month_o2c,
    generate_month_sales_invoices,
    generate_month_shipments,
)
from greenfield_dataset.p2p import (
    generate_month_disbursements,
    generate_month_goods_receipts,
    generate_month_p2p,
    generate_month_purchase_invoices,
    p2p_open_state,
)
from greenfield_dataset.posting_engine import post_all_transactions
from greenfield_dataset.schema import create_empty_tables
from greenfield_dataset.settings import GenerationContext, Settings, initialize_context, load_settings
from greenfield_dataset.validations import (
    validate_phase1,
    validate_phase2,
    validate_phase3,
    validate_phase4,
    validate_phase5,
    validate_phase6,
    validate_phase7,
    validate_phase8,
    validate_phase9,
)


LOGGER = logging.getLogger("greenfield_dataset")


def generation_log_path(context_or_settings: GenerationContext | Settings) -> Path:
    settings = getattr(context_or_settings, "settings", context_or_settings)
    return Path(settings.generation_log_path)


def configure_generation_logging(log_path: str | Path) -> None:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    for handler in list(LOGGER.handlers):
        LOGGER.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(path, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)

    LOGGER.addHandler(console_handler)
    LOGGER.addHandler(file_handler)


@contextmanager
def logged_step(name: str) -> Iterator[None]:
    started_at = time.perf_counter()
    LOGGER.info("START | %s", name)
    try:
        yield
    except Exception:
        elapsed = time.perf_counter() - started_at
        LOGGER.exception("FAIL | %s | elapsed_seconds=%.2f", name, elapsed)
        raise
    elapsed = time.perf_counter() - started_at
    LOGGER.info("DONE | %s | elapsed_seconds=%.2f", name, elapsed)


def log_settings(settings: Settings, config_path: str | Path) -> None:
    LOGGER.info("Config path: %s", Path(config_path))
    LOGGER.info("Company: %s", settings.company_name)
    LOGGER.info("Fiscal range: %s to %s", settings.fiscal_year_start, settings.fiscal_year_end)
    LOGGER.info("Random seed: %s", settings.random_seed)
    LOGGER.info("Anomaly mode: %s", settings.anomaly_mode)
    LOGGER.info("SQLite export enabled: %s | path=%s", settings.export_sqlite, settings.sqlite_path)
    LOGGER.info("Excel export enabled: %s | path=%s", settings.export_excel, settings.excel_path)
    LOGGER.info("Validation report path: %s", settings.validation_report_path)
    LOGGER.info("Generation log path: %s", generation_log_path(settings))


def log_table_counts(context: GenerationContext, table_names: Iterable[str], label: str) -> None:
    counts = ", ".join(f"{table_name}={len(context.tables[table_name]):,}" for table_name in table_names)
    LOGGER.info("ROW COUNTS | %s | %s", label, counts)


def log_all_table_counts(context: GenerationContext, label: str) -> None:
    counts = ", ".join(f"{table_name}={len(df):,}" for table_name, df in context.tables.items())
    LOGGER.info("ROW COUNTS | %s | %s", label, counts)


def log_validation_results(phase_name: str, results: dict[str, Any]) -> None:
    direct_exceptions = len(results.get("exceptions", []))
    LOGGER.info("VALIDATION | %s | direct_exceptions=%s", phase_name, direct_exceptions)

    for key, value in results.items():
        if isinstance(value, dict) and "exception_count" in value:
            LOGGER.info("VALIDATION | %s.%s | exception_count=%s", phase_name, key, value["exception_count"])


def build_phase1(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    settings = load_settings(config_path)
    context = initialize_context(settings)

    create_empty_tables(context)
    generate_cost_centers(context)
    load_accounts(context, accounts_path="config/accounts.csv")
    generate_employees(context)
    backfill_cost_center_managers(context)
    generate_warehouses(context)
    validate_phase1(context)
    export_validation_report(context)

    return context


def build_phase2(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase1(config_path)

    generate_items(context)
    generate_customers(context)
    generate_suppliers(context)
    generate_opening_balances(context)
    generate_budgets(context)
    validate_phase2(context)
    export_validation_report(context)

    return context


def build_phase3(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase2(config_path)

    generate_month_o2c(context, 2026, 1)
    generate_month_p2p(context, 2026, 1)
    validate_phase3(context)
    export_validation_report(context)

    return context


def build_phase4(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase3(config_path)

    generate_month_shipments(context, 2026, 1)
    generate_month_goods_receipts(context, 2026, 1)
    validate_phase4(context)
    export_validation_report(context)

    return context


def build_phase5(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase4(config_path)

    generate_month_sales_invoices(context, 2026, 1)
    generate_month_cash_receipts(context, 2026, 1)
    generate_month_purchase_invoices(context, 2026, 1)
    generate_month_disbursements(context, 2026, 1)
    validate_phase5(context)
    export_validation_report(context)

    return context


def build_phase6(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase5(config_path)

    post_all_transactions(context)
    validate_phase6(context)
    export_validation_report(context)

    return context


def build_phase7(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase6(config_path)

    inject_anomalies(context)
    validate_phase7(context)
    if context.settings.export_sqlite:
        export_sqlite(context)
    if context.settings.export_excel:
        export_excel(context)
    export_validation_report(context)

    return context


def build_phase8(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase5(config_path)

    generate_recurring_manual_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    inject_anomalies(context)
    validate_phase8(context)
    if context.settings.export_sqlite:
        export_sqlite(context)
    if context.settings.export_excel:
        export_excel(context)
    export_validation_report(context)

    return context


def build_phase9(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase5(config_path)

    generate_recurring_manual_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase9(context)
    export_validation_report(context)

    return context


def fiscal_months(context: GenerationContext) -> Iterable[tuple[int, int]]:
    start = pd.Timestamp(context.settings.fiscal_year_start)
    end = pd.Timestamp(context.settings.fiscal_year_end)
    current = pd.Timestamp(year=start.year, month=start.month, day=1)
    final = pd.Timestamp(year=end.year, month=end.month, day=1)

    while current <= final:
        yield int(current.year), int(current.month)
        current = current + pd.DateOffset(months=1)


def generate_all_months(context: GenerationContext) -> None:
    for year, month in fiscal_months(context):
        generate_month_o2c(context, year, month)
        generate_month_p2p(context, year, month)
        generate_month_shipments(context, year, month)
        generate_month_goods_receipts(context, year, month)
        generate_month_sales_invoices(context, year, month)
        generate_month_cash_receipts(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_disbursements(context, year, month)


def build_full_dataset(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    settings = load_settings(config_path)
    configure_generation_logging(generation_log_path(settings))
    LOGGER.info("Starting Greenfield dataset generation.")
    log_settings(settings, config_path)
    context = initialize_context(settings)

    with logged_step("Create empty schema"):
        create_empty_tables(context)
        log_all_table_counts(context, "empty schema")

    with logged_step("Generate phase 1 master data"):
        generate_cost_centers(context)
        load_accounts(context, accounts_path="config/accounts.csv")
        generate_employees(context)
        backfill_cost_center_managers(context)
        generate_warehouses(context)
        log_table_counts(context, ("Account", "CostCenter", "Employee", "Warehouse"), "phase 1")

    with logged_step("Validate phase 1"):
        log_validation_results("phase1", validate_phase1(context))

    with logged_step("Generate phase 2 master data and planning data"):
        generate_items(context)
        generate_customers(context)
        generate_suppliers(context)
        generate_opening_balances(context)
        generate_budgets(context)
        log_table_counts(
            context,
            ("Item", "Customer", "Supplier", "JournalEntry", "GLEntry", "Budget"),
            "phase 2",
        )

    with logged_step("Validate phase 2"):
        log_validation_results("phase2", validate_phase2(context))

    with logged_step("Generate all configured monthly subledger transactions"):
        generated_months = list(fiscal_months(context))
        LOGGER.info(
            "MONTH RANGE | count=%s | first=%s-%02d | last=%s-%02d",
            len(generated_months),
            *generated_months[0],
            *generated_months[-1],
        )
        for year, month in generated_months:
            LOGGER.info("MONTH START | %s-%02d", year, month)
            month_started_at = time.perf_counter()
            requisitions_converted_before = int(context.tables["PurchaseRequisition"]["Status"].eq("Converted to PO").sum())
            po_line_count_before = len(context.tables["PurchaseOrderLine"])
            receipt_line_count_before = len(context.tables["GoodsReceiptLine"])
            invoice_line_count_before = len(context.tables["PurchaseInvoiceLine"])
            disbursement_count_before = len(context.tables["DisbursementPayment"])
            generate_month_o2c(context, year, month)
            generate_month_p2p(context, year, month)
            generate_month_shipments(context, year, month)
            generate_month_goods_receipts(context, year, month)
            generate_month_sales_invoices(context, year, month)
            generate_month_cash_receipts(context, year, month)
            generate_month_purchase_invoices(context, year, month)
            generate_month_disbursements(context, year, month)
            requisitions_converted_after = int(context.tables["PurchaseRequisition"]["Status"].eq("Converted to PO").sum())
            new_receipt_lines = context.tables["GoodsReceiptLine"].iloc[receipt_line_count_before:]
            new_invoice_lines = context.tables["PurchaseInvoiceLine"].iloc[invoice_line_count_before:]
            new_disbursements = context.tables["DisbursementPayment"].iloc[disbursement_count_before:]
            open_state = p2p_open_state(context)
            LOGGER.info(
                "P2P CHECKPOINT | %s-%02d | converted_requisitions=%s | po_lines_created=%s | receipt_lines_created=%s | receipt_quantity=%s | invoice_lines_created=%s | invoiced_quantity=%s | disbursements_created=%s | amount_paid=%s | open_requisitions=%s | open_po_quantity=%s | open_receipt_quantity=%s | open_invoice_amount=%s",
                year,
                month,
                requisitions_converted_after - requisitions_converted_before,
                len(context.tables["PurchaseOrderLine"]) - po_line_count_before,
                len(new_receipt_lines),
                round(float(new_receipt_lines["QuantityReceived"].sum()), 2) if not new_receipt_lines.empty else 0.0,
                len(new_invoice_lines),
                round(float(new_invoice_lines["Quantity"].sum()), 2) if not new_invoice_lines.empty else 0.0,
                len(new_disbursements),
                round(float(new_disbursements["Amount"].sum()), 2) if not new_disbursements.empty else 0.0,
                int(open_state["open_requisitions"]),
                open_state["open_po_quantity"],
                open_state["open_receipt_quantity"],
                open_state["open_invoice_amount"],
            )
            LOGGER.info(
                "MONTH DONE | %s-%02d | elapsed_seconds=%.2f",
                year,
                month,
                time.perf_counter() - month_started_at,
            )
        log_table_counts(
            context,
            (
                "SalesOrder",
                "SalesOrderLine",
                "PurchaseRequisition",
                "PurchaseOrder",
                "Shipment",
                "GoodsReceipt",
                "SalesInvoice",
                "CashReceipt",
                "PurchaseInvoice",
                "DisbursementPayment",
            ),
            "monthly transactions",
        )

    with logged_step("Validate operational subledger data"):
        log_validation_results("phase5", validate_phase5(context))

    with logged_step("Generate recurring manual journals"):
        generate_recurring_manual_journals(context)
        log_table_counts(context, ("JournalEntry", "GLEntry"), "manual journals")

    with logged_step("Post transactions to general ledger"):
        post_all_transactions(context)
        log_table_counts(context, ("JournalEntry", "GLEntry"), "posting")

    with logged_step("Generate year-end close journals"):
        generate_year_end_close_journals(context)
        log_table_counts(context, ("JournalEntry", "GLEntry"), "year-end close")

    with logged_step("Validate clean final dataset"):
        log_validation_results("phase9", validate_phase9(context))

    with logged_step("Inject configured anomalies"):
        inject_anomalies(context)
        journal_anomaly_count = sum(
            1
            for anomaly in context.anomaly_log
            if anomaly["table_name"] == "JournalEntry" or anomaly["anomaly_type"].endswith("_manual_journal")
        )
        LOGGER.info("ANOMALIES | total_count=%s | journal_anomaly_count=%s", len(context.anomaly_log), journal_anomaly_count)

    with logged_step("Validate anomaly-enriched dataset"):
        log_validation_results("phase8", validate_phase8(context))

    if context.settings.export_sqlite:
        with logged_step("Export SQLite database"):
            export_sqlite(context)
            LOGGER.info("EXPORT | sqlite | path=%s", context.settings.sqlite_path)
    else:
        LOGGER.info("SKIP | SQLite export disabled.")

    if context.settings.export_excel:
        with logged_step("Export Excel workbook"):
            export_excel(context)
            LOGGER.info("EXPORT | excel | path=%s", context.settings.excel_path)
    else:
        LOGGER.info("SKIP | Excel export disabled.")

    with logged_step("Export validation report"):
        export_validation_report(context)
        LOGGER.info("EXPORT | validation_report | path=%s", context.settings.validation_report_path)

    log_all_table_counts(context, "final")
    LOGGER.info("Finished Greenfield dataset generation.")

    return context


def print_summary(context: GenerationContext) -> None:
    row_counts = context.validation_results["phase9"]["row_counts"]
    print("Full dataset generated.")
    print(f"Fiscal range: {context.settings.fiscal_year_start} to {context.settings.fiscal_year_end}")
    print(f"Accounts: {row_counts['Account']}")
    print(f"Cost centers: {row_counts['CostCenter']}")
    print(f"Employees: {row_counts['Employee']}")
    print(f"Warehouses: {row_counts['Warehouse']}")
    print(f"Items: {row_counts['Item']}")
    print(f"Customers: {row_counts['Customer']}")
    print(f"Suppliers: {row_counts['Supplier']}")
    print(f"Journal entries: {row_counts['JournalEntry']}")
    print(f"Budget rows: {row_counts['Budget']}")
    print(f"Sales orders: {row_counts['SalesOrder']}")
    print(f"Sales order lines: {row_counts['SalesOrderLine']}")
    print(f"Purchase requisitions: {row_counts['PurchaseRequisition']}")
    print(f"Purchase orders: {row_counts['PurchaseOrder']}")
    print(f"Purchase order lines: {row_counts['PurchaseOrderLine']}")
    print(f"Shipments: {row_counts['Shipment']}")
    print(f"Shipment lines: {row_counts['ShipmentLine']}")
    print(f"Goods receipts: {row_counts['GoodsReceipt']}")
    print(f"Goods receipt lines: {row_counts['GoodsReceiptLine']}")
    print(f"Sales invoices: {row_counts['SalesInvoice']}")
    print(f"Sales invoice lines: {row_counts['SalesInvoiceLine']}")
    print(f"Cash receipts: {row_counts['CashReceipt']}")
    print(f"Purchase invoices: {row_counts['PurchaseInvoice']}")
    print(f"Purchase invoice lines: {row_counts['PurchaseInvoiceLine']}")
    print(f"Disbursements: {row_counts['DisbursementPayment']}")
    print(f"GL entries: {row_counts['GLEntry']}")
    print(f"GL balance exceptions: {context.validation_results['phase9']['gl_balance']['exception_count']}")
    print(f"Anomalies logged: {len(context.anomaly_log)}")
    print(f"SQLite export: {context.settings.sqlite_path}")
    print(f"Excel export: {context.settings.excel_path}")
    print(f"Validation report: {context.settings.validation_report_path}")
    print(f"Generation log: {generation_log_path(context)}")


def main() -> None:
    print_summary(build_full_dataset())


if __name__ == "__main__":
    main()
