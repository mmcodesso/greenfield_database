from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

import pandas as pd

from generator_dataset.anomalies import inject_anomalies, invalidate_all_caches
from generator_dataset.budgets import generate_budgets, generate_opening_balances
from generator_dataset.capex import generate_month_capex_activity, generate_opening_fixed_asset_records
from generator_dataset.exporters import (
    EXCEL_MAX_TABLE_DATA_ROWS,
    export_csv_zip,
    export_excel,
    export_reports,
    export_sqlite,
    export_support_excel,
    export_validation_report,
)
from generator_dataset.journals import (
    generate_accrual_adjustment_journals,
    generate_recurring_manual_journals,
    generate_year_end_close_journals,
)
from generator_dataset.manufacturing import (
    close_eligible_work_orders,
    generate_boms,
    generate_month_manufacturing_activity,
    generate_month_work_orders_and_requisitions,
    generate_work_center_calendars,
    generate_work_centers_and_routings,
    manufacturing_capacity_state,
    manufacturing_capacity_diagnostics_by_code,
    manufacturing_work_center_utilization_by_code,
    manufacturing_open_state,
    seed_opening_manufacturing_pipeline,
    sync_work_center_capacity_from_assignments,
)
from generator_dataset.master_data import (
    backfill_cost_center_managers,
    generate_cost_centers,
    generate_customers,
    generate_employees,
    generate_items,
    generate_suppliers,
    generate_warehouses,
    load_accounts,
)
from generator_dataset.o2c import (
    generate_price_lists,
    generate_promotions,
    generate_month_cash_receipts,
    generate_month_customer_refunds,
    generate_month_o2c,
    generate_month_sales_returns,
    generate_month_sales_invoices,
    generate_month_shipments,
    o2c_open_state,
)
from generator_dataset.p2p import (
    generate_accrued_service_settlements,
    generate_month_disbursements,
    generate_month_goods_receipts,
    generate_month_p2p,
    generate_month_purchase_orders,
    generate_month_requisitions,
    generate_month_purchase_invoices,
    p2p_open_state,
)
from generator_dataset.payroll import (
    generate_month_payroll,
    generate_payroll_periods,
    generate_shift_definitions_and_assignments,
    monthly_payroll_state,
)
from generator_dataset.planning import (
    generate_demand_forecasts,
    generate_inventory_policies,
    generate_month_planning,
    inventory_position_as_of,
    manufactured_late_year_sell_through_schedule,
    manufactured_policy_profile_schedule,
    manufactured_planning_diagnostics,
)
from generator_dataset.posting_engine import post_all_transactions
from generator_dataset.schema import create_empty_tables
from generator_dataset.settings import GenerationContext, Settings, initialize_context, load_settings
from generator_dataset.validations import (
    validate_phase1,
    validate_phase2,
    validate_phase3,
    validate_phase4,
    validate_phase5,
    validate_phase6,
    validate_phase7,
    validate_phase8,
    validate_phase9,
    validate_phase11,
    validate_phase12,
    validate_phase13,
    validate_phase14,
    validate_phase15,
    validate_phase15_2,
    validate_phase16,
    validate_phase17,
    validate_phase18,
    validate_phase19,
    validate_phase20,
    validate_phase21,
    validate_phase22,
    validate_phase23,
)


LOGGER = logging.getLogger("generator_dataset")
PREFERRED_EXCEL_GLENTRY_ROW_BUDGET = 1_000_000


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


def close_generation_logging() -> None:
    for handler in list(LOGGER.handlers):
        LOGGER.removeHandler(handler)
        handler.close()


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
    LOGGER.info("Support workbook enabled: %s | path=%s", settings.export_support_excel, settings.support_excel_path)
    LOGGER.info("CSV zip export enabled: %s | path=%s", settings.export_csv_zip, settings.csv_zip_path)
    LOGGER.info("Report export enabled: %s | path=%s", settings.export_reports, settings.report_output_dir)
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
            scalar_metrics: list[str] = []
            for metric_key, metric_value in value.items():
                if metric_key in {"exception_count", "exceptions"}:
                    continue
                if isinstance(metric_value, dict):
                    continue
                if isinstance(metric_value, list):
                    if not metric_value:
                        scalar_metrics.append(f"{metric_key}=[]")
                    else:
                        scalar_metrics.append(
                            f"{metric_key}={json.dumps(metric_value, default=str, ensure_ascii=True)}"
                        )
                    continue
                scalar_metrics.append(f"{metric_key}={metric_value}")
            if scalar_metrics:
                LOGGER.info("VALIDATION | %s.%s | %s", phase_name, key, " | ".join(scalar_metrics))


def _run_generation_step(
    context: GenerationContext,
    name: str,
    generator: Any,
    *,
    log_substeps: bool,
) -> None:
    if log_substeps:
        with logged_step(name):
            generator(context)
        return
    generator(context)


def _generate_phase2_master_data_and_planning(
    context: GenerationContext,
    *,
    log_substeps: bool,
) -> None:
    phase2_generators = [
        ("Generate phase 2 item master", generate_items),
        ("Generate phase 2 BOMs", generate_boms),
        ("Generate phase 2 routings and work centers", generate_work_centers_and_routings),
        ("Generate phase 2 customers", generate_customers),
        ("Generate phase 2 price lists", generate_price_lists),
        ("Generate phase 2 promotions", generate_promotions),
        ("Generate phase 2 suppliers", generate_suppliers),
        ("Generate phase 2 payroll periods", generate_payroll_periods),
        ("Generate phase 2 shift definitions and assignments", generate_shift_definitions_and_assignments),
        ("Synchronize phase 2 work-center capacity and calendars", synchronize_work_center_capacity_and_calendars),
        ("Generate phase 2 inventory policies", generate_inventory_policies),
        ("Generate phase 2 demand forecasts", generate_demand_forecasts),
        ("Generate phase 2 fixed asset opening records", generate_opening_fixed_asset_records),
        ("Generate phase 2 opening balances", generate_opening_balances),
        ("Generate phase 2 budgets", generate_budgets),
    ]
    for step_name, generator in phase2_generators:
        _run_generation_step(context, step_name, generator, log_substeps=log_substeps)


def synchronize_work_center_capacity_and_calendars(context: GenerationContext) -> None:
    sync_work_center_capacity_from_assignments(context, regenerate_calendar=True)


def log_opening_state_shock_diagnostics(context: GenerationContext) -> None:
    fiscal_start = pd.Timestamp(context.settings.fiscal_year_start).normalize()
    first_period_label = fiscal_start.strftime("%Y-%m")
    comparison_periods = [
        (fiscal_start + pd.DateOffset(months=offset)).strftime("%Y-%m")
        for offset in range(1, 6)
    ]

    def steady_state_median(values: dict[str, float]) -> float:
        series = [float(values.get(period, 0.0)) for period in comparison_periods if float(values.get(period, 0.0)) > 0]
        if not series:
            return 0.0
        return round(float(pd.Series(series).median()), 2)

    purchase_orders = context.tables["PurchaseOrder"]
    po_monthly = {}
    if not purchase_orders.empty:
        po_monthly = {
            str(period): round(float(amount), 2)
            for period, amount in purchase_orders.groupby(
                purchase_orders["OrderDate"].astype(str).str.slice(0, 7)
            )["OrderTotal"].sum().items()
        }

    goods_receipts = context.tables["GoodsReceipt"]
    goods_receipt_lines = context.tables["GoodsReceiptLine"]
    gr_monthly = {}
    if not goods_receipts.empty and not goods_receipt_lines.empty:
        gr = goods_receipt_lines.merge(
            goods_receipts[["GoodsReceiptID", "ReceiptDate"]],
            on="GoodsReceiptID",
            how="left",
        )
        gr_monthly = {
            str(period): round(float(amount), 2)
            for period, amount in gr.groupby(gr["ReceiptDate"].astype(str).str.slice(0, 7))["ExtendedStandardCost"].sum().items()
        }

    purchase_invoices = context.tables["PurchaseInvoice"]
    pi_monthly = {}
    if not purchase_invoices.empty:
        pi_monthly = {
            str(period): round(float(amount), 2)
            for period, amount in purchase_invoices.groupby(
                purchase_invoices["InvoiceDate"].astype(str).str.slice(0, 7)
            )["GrandTotal"].sum().items()
        }

    disbursements = context.tables["DisbursementPayment"]
    disbursement_monthly = {}
    if not disbursements.empty:
        disbursement_monthly = {
            str(period): round(float(amount), 2)
            for period, amount in disbursements.groupby(
                disbursements["PaymentDate"].astype(str).str.slice(0, 7)
            )["Amount"].sum().items()
        }

    gl = context.tables["GLEntry"]
    accounts = context.tables["Account"][["AccountID", "AccountNumber"]].copy()
    gl_accounts = gl.merge(accounts, on="AccountID", how="left") if not gl.empty else gl.head(0).copy()
    journal_entries = context.tables["JournalEntry"][["JournalEntryID", "EntryType"]].copy()
    if not gl_accounts.empty and not journal_entries.empty:
        gl_accounts = gl_accounts.merge(
            journal_entries.rename(columns={"JournalEntryID": "SourceDocumentID", "EntryType": "JournalEntryType"}),
            on="SourceDocumentID",
            how="left",
        )
    if not gl_accounts.empty:
        gl_accounts = gl_accounts[
            ~(
                gl_accounts["SourceDocumentType"].eq("JournalEntry")
                & gl_accounts.get("JournalEntryType", pd.Series(index=gl_accounts.index, dtype=object)).eq("Opening")
            )
        ].copy()

    supplier_cash_monthly = {}
    ap_activity_monthly = {}
    fg_activity_monthly = {}
    materials_activity_monthly = {}
    if not gl_accounts.empty:
        supplier_cash_rows = gl_accounts[
            gl_accounts["AccountNumber"].astype(str).eq("1010")
            & gl_accounts["SourceDocumentType"].eq("DisbursementPayment")
        ].copy()
        supplier_cash_monthly = {
            str(period): round(float(-amount), 2)
            for period, amount in supplier_cash_rows.groupby(
                supplier_cash_rows["PostingDate"].astype(str).str.slice(0, 7)
            ).apply(lambda rows: (rows["Debit"].astype(float) - rows["Credit"].astype(float)).sum()).items()
        }

        for account_number, target in [("2010", ap_activity_monthly), ("1040", fg_activity_monthly), ("1045", materials_activity_monthly)]:
            target_rows = gl_accounts[gl_accounts["AccountNumber"].astype(str).eq(account_number)].copy()
            if target_rows.empty:
                continue
            if account_number == "2010":
                grouped = target_rows.groupby(target_rows["PostingDate"].astype(str).str.slice(0, 7)).apply(
                    lambda rows: (rows["Credit"].astype(float) - rows["Debit"].astype(float)).sum()
                )
            else:
                grouped = target_rows.groupby(target_rows["PostingDate"].astype(str).str.slice(0, 7)).apply(
                    lambda rows: (rows["Debit"].astype(float) - rows["Credit"].astype(float)).sum()
                )
            target.update({str(period): round(float(amount), 2) for period, amount in grouped.items()})

    metric_map = {
        "purchase_order_total": po_monthly,
        "goods_receipt_cost": gr_monthly,
        "purchase_invoice_total": pi_monthly,
        "disbursement_total": disbursement_monthly,
        "supplier_cash_gl": supplier_cash_monthly,
        "ap_gl_activity": ap_activity_monthly,
        "fg_inventory_gl_activity": fg_activity_monthly,
        "materials_inventory_gl_activity": materials_activity_monthly,
    }
    for metric_name, values in metric_map.items():
        first_value = round(float(values.get(first_period_label, 0.0)), 2)
        median_value = steady_state_median(values)
        ratio = round(first_value / median_value, 2) if median_value > 0 else 0.0
        LOGGER.info(
            "OPENING STATE SHOCK | metric=%s | first_period=%s | first_value=%s | steady_state_median=%s | ratio=%s",
            metric_name,
            first_period_label,
            first_value,
            median_value,
            ratio,
        )

    items = context.tables["Item"][["ItemID", "ItemGroup", "SupplyMode"]].copy()
    if not items.empty and not goods_receipts.empty and not goods_receipt_lines.empty and not purchase_orders.empty:
        first_period_purchase_lines = context.tables["PurchaseOrderLine"].merge(
            purchase_orders[["PurchaseOrderID", "OrderDate"]],
            on="PurchaseOrderID",
            how="left",
        ).merge(items, on="ItemID", how="left")
        first_period_purchase_lines = first_period_purchase_lines[
            first_period_purchase_lines["OrderDate"].astype(str).str.slice(0, 7).eq(first_period_label)
        ].copy()
        purchase_mix = first_period_purchase_lines.groupby(["ItemGroup", "SupplyMode"])["LineTotal"].sum().sort_values(ascending=False)
        for (item_group, supply_mode), amount in purchase_mix.head(8).items():
            LOGGER.info(
                "OPENING STATE MIX | period=%s | activity=purchase_order | item_group=%s | supply_mode=%s | amount=%s",
                first_period_label,
                item_group,
                supply_mode,
                round(float(amount), 2),
            )

        first_period_receipts = goods_receipt_lines.merge(
            goods_receipts[["GoodsReceiptID", "ReceiptDate"]],
            on="GoodsReceiptID",
            how="left",
        ).merge(items, on="ItemID", how="left")
        first_period_receipts = first_period_receipts[
            first_period_receipts["ReceiptDate"].astype(str).str.slice(0, 7).eq(first_period_label)
        ].copy()
        receipt_mix = first_period_receipts.groupby(["ItemGroup", "SupplyMode"])["ExtendedStandardCost"].sum().sort_values(ascending=False)
        for (item_group, supply_mode), amount in receipt_mix.head(8).items():
            LOGGER.info(
                "OPENING STATE MIX | period=%s | activity=goods_receipt | item_group=%s | supply_mode=%s | amount=%s",
                first_period_label,
                item_group,
                supply_mode,
                round(float(amount), 2),
            )

    recommendations = context.tables["SupplyPlanRecommendation"]
    if not recommendations.empty and not items.empty:
        driver_window_start = (fiscal_start - pd.DateOffset(months=1)).replace(day=1)
        driver_window_end = (fiscal_start + pd.offsets.MonthEnd(2)).normalize()
        driver_rows = recommendations.merge(items[["ItemID", "ItemGroup"]], on="ItemID", how="left")
        driver_rows["ReleaseByDateTS"] = pd.to_datetime(driver_rows["ReleaseByDate"], errors="coerce")
        driver_rows = driver_rows[
            driver_rows["ReleaseByDateTS"].notna()
            & driver_rows["ReleaseByDateTS"].between(driver_window_start, driver_window_end)
        ].copy()
        if not driver_rows.empty:
            driver_mix = driver_rows.groupby(
                ["DriverType", "RecommendationType", "ItemGroup", "SupplyMode"]
            )["RecommendedOrderQuantity"].sum().sort_values(ascending=False)
            for (driver_type, recommendation_type, item_group, supply_mode), quantity in driver_mix.head(12).items():
                LOGGER.info(
                    "OPENING STATE DRIVER MIX | window=%s_to_%s | driver_type=%s | recommendation_type=%s | item_group=%s | supply_mode=%s | quantity=%s",
                    driver_window_start.strftime("%Y-%m"),
                    driver_window_end.strftime("%Y-%m"),
                    driver_type,
                    recommendation_type,
                    item_group,
                    supply_mode,
                    round(float(quantity), 2),
                )


def manufactured_fg_flow_diagnostics(context: GenerationContext) -> list[dict[str, Any]]:
    items = context.tables["Item"][["ItemID", "ItemGroup", "SupplyMode", "RevenueAccountID", "StandardCost"]].copy()
    items = items[
        items["SupplyMode"].eq("Manufactured")
        & items["RevenueAccountID"].notna()
    ].copy()
    if items.empty:
        return []

    items["ItemID"] = items["ItemID"].astype(int)
    item_lookup = items.set_index("ItemID").to_dict("index")
    completion_grouped: dict[tuple[str, str], dict[str, float]] = {}
    shipment_grouped: dict[tuple[str, str], dict[str, float]] = {}

    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if not completions.empty and not completion_lines.empty:
        completion_rows = completion_lines.merge(
            completions[["ProductionCompletionID", "CompletionDate"]],
            on="ProductionCompletionID",
            how="left",
        )
        completion_rows["Period"] = completion_rows["CompletionDate"].astype(str).str.slice(0, 7)
        completion_rows = completion_rows[completion_rows["ItemID"].astype(int).isin(item_lookup)].copy()
        if not completion_rows.empty:
            completion_rows["ItemGroup"] = completion_rows["ItemID"].astype(int).map(
                lambda item_id: str(item_lookup[int(item_id)]["ItemGroup"])
            )
            grouped = completion_rows.groupby(["Period", "ItemGroup"]).agg(
                CompletionQuantity=("QuantityCompleted", lambda values: round(float(pd.to_numeric(values, errors="coerce").fillna(0.0).sum()), 2)),
                CompletionCost=("ExtendedStandardTotalCost", lambda values: round(float(pd.to_numeric(values, errors="coerce").fillna(0.0).sum()), 2)),
            )
            completion_grouped = {
                (str(period), str(item_group)): {
                    "completion_quantity": float(row["CompletionQuantity"]),
                    "completion_cost": float(row["CompletionCost"]),
                }
                for (period, item_group), row in grouped.iterrows()
            }

    shipments = context.tables["Shipment"]
    shipment_lines = context.tables["ShipmentLine"]
    if not shipments.empty and not shipment_lines.empty:
        shipment_rows = shipment_lines.merge(
            shipments[["ShipmentID", "ShipmentDate"]],
            on="ShipmentID",
            how="left",
        )
        shipment_rows["Period"] = shipment_rows["ShipmentDate"].astype(str).str.slice(0, 7)
        shipment_rows = shipment_rows[shipment_rows["ItemID"].astype(int).isin(item_lookup)].copy()
        if not shipment_rows.empty:
            shipment_rows["ItemGroup"] = shipment_rows["ItemID"].astype(int).map(
                lambda item_id: str(item_lookup[int(item_id)]["ItemGroup"])
            )
            grouped = shipment_rows.groupby(["Period", "ItemGroup"]).agg(
                ShipmentQuantity=("QuantityShipped", lambda values: round(float(pd.to_numeric(values, errors="coerce").fillna(0.0).sum()), 2)),
                ShipmentCost=("ExtendedStandardCost", lambda values: round(float(pd.to_numeric(values, errors="coerce").fillna(0.0).sum()), 2)),
            )
            shipment_grouped = {
                (str(period), str(item_group)): {
                    "shipment_quantity": float(row["ShipmentQuantity"]),
                    "shipment_cost": float(row["ShipmentCost"]),
                }
                for (period, item_group), row in grouped.iterrows()
            }

    results: list[dict[str, Any]] = []
    fiscal_start = pd.Timestamp(context.settings.fiscal_year_start).normalize()
    fiscal_end = pd.Timestamp(context.settings.fiscal_year_end).normalize()
    for month_start in pd.date_range(fiscal_start.replace(day=1), fiscal_end.replace(day=1), freq="MS"):
        month_end = month_start + pd.offsets.MonthEnd(1)
        opening_position = inventory_position_as_of(context, month_start - pd.Timedelta(days=1))
        ending_position = inventory_position_as_of(context, month_end)
        period_label = month_start.strftime("%Y-%m")
        for item_group in sorted(items["ItemGroup"].astype(str).unique()):
            item_ids = items.loc[items["ItemGroup"].astype(str).eq(item_group), "ItemID"].astype(int).tolist()
            opening_quantity = 0.0
            opening_value = 0.0
            ending_quantity = 0.0
            ending_value = 0.0
            for item_id in item_ids:
                standard_cost = float(item_lookup[int(item_id)]["StandardCost"] or 0.0)
                for (position_item_id, _warehouse_id), quantity in opening_position.items():
                    if int(position_item_id) != int(item_id):
                        continue
                    opening_quantity += float(quantity)
                    opening_value += float(quantity) * standard_cost
                for (position_item_id, _warehouse_id), quantity in ending_position.items():
                    if int(position_item_id) != int(item_id):
                        continue
                    ending_quantity += float(quantity)
                    ending_value += float(quantity) * standard_cost
            completion_metrics = completion_grouped.get((period_label, item_group), {})
            shipment_metrics = shipment_grouped.get((period_label, item_group), {})
            completion_quantity = round(float(completion_metrics.get("completion_quantity", 0.0)), 2)
            completion_cost = round(float(completion_metrics.get("completion_cost", 0.0)), 2)
            shipment_quantity = round(float(shipment_metrics.get("shipment_quantity", 0.0)), 2)
            shipment_cost = round(float(shipment_metrics.get("shipment_cost", 0.0)), 2)
            results.append({
                "Period": period_label,
                "ItemGroup": item_group,
                "OpeningFGQuantity": round(opening_quantity, 2),
                "OpeningFGValue": round(opening_value, 2),
                "CompletionQuantity": completion_quantity,
                "CompletionCost": completion_cost,
                "ShipmentQuantity": shipment_quantity,
                "ShipmentCost": shipment_cost,
                "EndingFGQuantity": round(ending_quantity, 2),
                "EndingFGValue": round(ending_value, 2),
                "ProductionToShipmentRatio": round(completion_cost / shipment_cost, 2) if shipment_cost > 0 else 0.0,
                "QuantityGap": round(completion_quantity - shipment_quantity, 2),
                "CostGap": round(completion_cost - shipment_cost, 2),
            })
    return results


def annual_manufactured_fg_flow_diagnostics(context: GenerationContext) -> list[dict[str, Any]]:
    monthly_rows = pd.DataFrame(manufactured_fg_flow_diagnostics(context))
    if monthly_rows.empty:
        return []

    monthly_rows["FiscalYear"] = monthly_rows["Period"].astype(str).str.slice(0, 4).astype(int)
    results: list[dict[str, Any]] = []
    for (fiscal_year, item_group), rows in monthly_rows.groupby(["FiscalYear", "ItemGroup"], dropna=False):
        ordered = rows.sort_values("Period").reset_index(drop=True)
        completion_quantity = round(float(ordered["CompletionQuantity"].astype(float).sum()), 2)
        completion_cost = round(float(ordered["CompletionCost"].astype(float).sum()), 2)
        shipment_quantity = round(float(ordered["ShipmentQuantity"].astype(float).sum()), 2)
        shipment_cost = round(float(ordered["ShipmentCost"].astype(float).sum()), 2)
        results.append({
            "FiscalYear": int(fiscal_year),
            "ItemGroup": str(item_group),
            "OpeningFGQuantity": round(float(ordered.iloc[0]["OpeningFGQuantity"]), 2),
            "OpeningFGValue": round(float(ordered.iloc[0]["OpeningFGValue"]), 2),
            "CompletionQuantity": completion_quantity,
            "CompletionCost": completion_cost,
            "ShipmentQuantity": shipment_quantity,
            "ShipmentCost": shipment_cost,
            "EndingFGQuantity": round(float(ordered.iloc[-1]["EndingFGQuantity"]), 2),
            "EndingFGValue": round(float(ordered.iloc[-1]["EndingFGValue"]), 2),
            "ProductionToShipmentRatio": round(completion_cost / shipment_cost, 2) if shipment_cost > 0 else 0.0,
            "QuantityGap": round(completion_quantity - shipment_quantity, 2),
            "CostGap": round(completion_cost - shipment_cost, 2),
        })
    return sorted(results, key=lambda row: (int(row["FiscalYear"]), str(row["ItemGroup"])))


def annual_capacity_utilization_diagnostics(
    context: GenerationContext,
    work_center_codes: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    fiscal_start = pd.Timestamp(context.settings.fiscal_year_start).normalize()
    fiscal_end = pd.Timestamp(context.settings.fiscal_year_end).normalize()
    fiscal_months: dict[int, list[int]] = {}
    current_month_start = fiscal_start.replace(day=1)
    last_month_start = fiscal_end.replace(day=1)
    while current_month_start <= last_month_start:
        fiscal_months.setdefault(int(current_month_start.year), []).append(int(current_month_start.month))
        current_month_start = current_month_start + pd.DateOffset(months=1)

    selected_codes = [str(code) for code in (work_center_codes or ["ASSEMBLY", "FINISH", "PACK"])]
    results: list[dict[str, Any]] = []
    for fiscal_year, months in sorted(fiscal_months.items()):
        monthly_rows = {
            int(month): manufacturing_capacity_diagnostics_by_code(context, fiscal_year, int(month))
            for month in months
        }
        for work_center_code in selected_codes:
            utilizations = [
                float(monthly_rows[int(month)].get(work_center_code, {}).get("monthly_utilization_pct", 0.0))
                for month in months
            ]
            if not utilizations:
                continue
            results.append({
                "FiscalYear": int(fiscal_year),
                "WorkCenterCode": work_center_code,
                "MedianMonthlyUtilizationPct": round(float(pd.Series(utilizations).median()), 2),
                "PeakMonthlyUtilizationPct": round(float(max(utilizations)), 2),
                "MonthsAtOrAbove85Pct": int(sum(1 for value in utilizations if float(value) >= 85.0)),
            })
    return results


def log_manufactured_load_calibration(context: GenerationContext) -> None:
    for row in manufactured_late_year_sell_through_schedule(context):
        LOGGER.info(
            "MANUFACTURED LOAD CALIBRATION | fiscal_year=%s | sell_through_uplift_factor=%s",
            row["FiscalYear"],
            row["SellThroughUpliftFactor"],
        )
    for row in manufactured_policy_profile_schedule(context):
        LOGGER.info(
            "MANUFACTURED FG POLICY | fiscal_year=%s | lifecycle_status=%s | policy_phase=%s | target_days_supply=%s | safety_stock_quantity=%s",
            row["FiscalYear"],
            row["LifecycleStatus"],
            row["PolicyPhase"],
            row["TargetDaysSupply"],
            row["SafetyStockQuantity"],
        )


def log_manufactured_planning_diagnostics(context: GenerationContext) -> None:
    for row in manufactured_planning_diagnostics(context):
        LOGGER.info(
            "MANUFACTURED PLANNING DIAGNOSTIC | recommendation_month=%s | bucket_week_start=%s | item_id=%s | warehouse_id=%s | item_group=%s | lifecycle_status=%s | forecast_quantity=%s | backlog_quantity=%s | gross_requirement_quantity=%s | projected_available_before_replenishment=%s | target_days_supply=%s | safety_stock_target_quantity=%s | net_requirement_quantity=%s | recommended_order_quantity=%s | lot_size_uplift_quantity=%s | policy_type=%s | policy_phase=%s | sell_through_uplift_factor=%s",
            row["RecommendationMonth"],
            row["BucketWeekStartDate"],
            row["ItemID"],
            row["WarehouseID"],
            row["ItemGroup"],
            row["LifecycleStatus"],
            row["ForecastQuantity"],
            row["BacklogQuantity"],
            row["GrossRequirementQuantity"],
            row["ProjectedAvailableBeforeReplenishment"],
            row["TargetDaysSupply"],
            row["SafetyStockTargetQuantity"],
            row["NetRequirementQuantity"],
            row["RecommendedOrderQuantity"],
            row["LotSizeUpliftQuantity"],
            row["PolicyType"],
            row["PolicyPhase"],
            row["ManufacturedSellThroughUpliftFactor"],
        )


def log_manufactured_flow_diagnostics(context: GenerationContext) -> None:
    for row in manufactured_fg_flow_diagnostics(context):
        LOGGER.info(
            "MANUFACTURED FG FLOW | period=%s | item_group=%s | opening_fg_quantity=%s | opening_fg_value=%s | completions_quantity=%s | completions_cost=%s | shipments_quantity=%s | shipments_cost=%s | ending_fg_quantity=%s | ending_fg_value=%s | production_to_shipment_ratio=%s | quantity_gap=%s | cost_gap=%s",
            row["Period"],
            row["ItemGroup"],
            row["OpeningFGQuantity"],
            row["OpeningFGValue"],
            row["CompletionQuantity"],
            row["CompletionCost"],
            row["ShipmentQuantity"],
            row["ShipmentCost"],
            row["EndingFGQuantity"],
            row["EndingFGValue"],
            row["ProductionToShipmentRatio"],
            row["QuantityGap"],
            row["CostGap"],
        )
    for row in annual_manufactured_fg_flow_diagnostics(context):
        LOGGER.info(
            "MANUFACTURED FG FLOW ANNUAL | fiscal_year=%s | item_group=%s | opening_fg_quantity=%s | opening_fg_value=%s | completions_quantity=%s | completions_cost=%s | shipments_quantity=%s | shipments_cost=%s | ending_fg_quantity=%s | ending_fg_value=%s | production_to_shipment_ratio=%s | quantity_gap=%s | cost_gap=%s",
            row["FiscalYear"],
            row["ItemGroup"],
            row["OpeningFGQuantity"],
            row["OpeningFGValue"],
            row["CompletionQuantity"],
            row["CompletionCost"],
            row["ShipmentQuantity"],
            row["ShipmentCost"],
            row["EndingFGQuantity"],
            row["EndingFGValue"],
            row["ProductionToShipmentRatio"],
            row["QuantityGap"],
            row["CostGap"],
        )


def log_annual_capacity_diagnostics(context: GenerationContext) -> None:
    for row in annual_capacity_utilization_diagnostics(context):
        LOGGER.info(
            "CAPACITY ANNUAL SUMMARY | fiscal_year=%s | work_center=%s | median_monthly_utilization_pct=%s | peak_monthly_utilization_pct=%s | months_at_or_above_85_pct=%s",
            row["FiscalYear"],
            row["WorkCenterCode"],
            row["MedianMonthlyUtilizationPct"],
            row["PeakMonthlyUtilizationPct"],
            row["MonthsAtOrAbove85Pct"],
        )


def gl_row_budget_diagnostics(context: GenerationContext) -> dict[str, Any]:
    gl = context.tables["GLEntry"]
    if gl.empty:
        return {
            "total_rows": 0,
            "preferred_max_rows": PREFERRED_EXCEL_GLENTRY_ROW_BUDGET,
            "hard_max_rows": EXCEL_MAX_TABLE_DATA_ROWS,
            "preferred_ok": True,
            "hard_ok": True,
            "payroll_gl_summary_mode": getattr(context, "payroll_gl_summary_mode", {}),
            "by_source_type": [],
            "by_fiscal_year": [],
        }

    posting_dates = pd.to_datetime(gl["PostingDate"], errors="coerce")
    source_type_summary = (
        gl.groupby("SourceDocumentType", dropna=False)
        .agg(
            RowCount=("GLEntryID", "size"),
            VoucherCount=("VoucherNumber", "nunique"),
        )
        .reset_index()
        .sort_values(["RowCount", "SourceDocumentType"], ascending=[False, True])
    )
    fiscal_year_summary = (
        gl.assign(FiscalYear=posting_dates.dt.year)
        .dropna(subset=["FiscalYear"])
        .groupby("FiscalYear", dropna=False)["GLEntryID"]
        .size()
        .reset_index(name="RowCount")
        .sort_values("FiscalYear")
    )

    total_rows = int(len(gl.index))
    return {
        "total_rows": total_rows,
        "preferred_max_rows": PREFERRED_EXCEL_GLENTRY_ROW_BUDGET,
        "hard_max_rows": EXCEL_MAX_TABLE_DATA_ROWS,
        "preferred_ok": total_rows <= PREFERRED_EXCEL_GLENTRY_ROW_BUDGET,
        "hard_ok": total_rows <= EXCEL_MAX_TABLE_DATA_ROWS,
        "payroll_gl_summary_mode": getattr(context, "payroll_gl_summary_mode", {}),
        "by_source_type": source_type_summary.to_dict(orient="records"),
        "by_fiscal_year": [
            {
                "FiscalYear": int(row["FiscalYear"]),
                "RowCount": int(row["RowCount"]),
            }
            for row in fiscal_year_summary.to_dict(orient="records")
        ],
    }


def log_gl_row_budget_diagnostics(context: GenerationContext) -> None:
    diagnostics = gl_row_budget_diagnostics(context)
    payroll_summary_mode = diagnostics.get("payroll_gl_summary_mode", {})
    LOGGER.info(
        "GL ROW BUDGET | total_rows=%s | preferred_max_rows=%s | hard_max_rows=%s | preferred_ok=%s | hard_ok=%s | payroll_register_mode=%s | payroll_payment_mode=%s",
        diagnostics["total_rows"],
        diagnostics["preferred_max_rows"],
        diagnostics["hard_max_rows"],
        diagnostics["preferred_ok"],
        diagnostics["hard_ok"],
        payroll_summary_mode.get("register", "detail"),
        payroll_summary_mode.get("payment", "detail"),
    )
    for row in diagnostics["by_source_type"]:
        LOGGER.info(
            "GL ROW BUDGET | source_document_type=%s | row_count=%s | voucher_count=%s",
            row["SourceDocumentType"],
            row["RowCount"],
            row["VoucherCount"],
        )
    for row in diagnostics["by_fiscal_year"]:
        LOGGER.info(
            "GL ROW BUDGET | fiscal_year=%s | row_count=%s",
            row["FiscalYear"],
            row["RowCount"],
        )


def _run_month_step(
    context: GenerationContext,
    year: int,
    month: int,
    step_name: str,
    generator: Any,
) -> Any:
    started_at = time.perf_counter()
    result = generator(context, year, month)
    LOGGER.info(
        "MONTH STEP | %s-%02d | %s | elapsed_seconds=%.2f",
        year,
        month,
        step_name,
        time.perf_counter() - started_at,
    )
    return result


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
    _generate_phase2_master_data_and_planning(context, log_substeps=False)
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
    generate_month_capex_activity(context, 2026, 1)
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
    context = build_phase23(config_path)
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
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase9(context)
    export_validation_report(context)

    return context


def build_phase11(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase5(config_path)

    generate_month_sales_returns(context, 2026, 1)
    generate_month_customer_refunds(context, 2026, 1)
    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase11(context)
    export_validation_report(context)

    return context


def build_phase12(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase2(config_path)
    generate_payroll_periods(context)

    for year, month in [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]:
        generate_month_o2c(context, year, month)
        generate_month_requisitions(context, year, month)
        generate_month_work_orders_and_requisitions(context, year, month)
        generate_month_purchase_orders(context, year, month)
        generate_month_goods_receipts(context, year, month)
        generate_month_manufacturing_activity(context, year, month)
        generate_month_payroll(context, year, month)
        close_eligible_work_orders(context, year, month)
        generate_month_shipments(context, year, month)
        generate_month_sales_invoices(context, year, month)
        generate_month_cash_receipts(context, year, month)
        generate_month_sales_returns(context, year, month)
        generate_month_customer_refunds(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_capex_activity(context, year, month)
        generate_month_disbursements(context, year, month)
    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase12(context)
    export_validation_report(context)

    return context


def build_phase13(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase2(config_path)
    generate_payroll_periods(context)

    for year, month in [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]:
        generate_month_o2c(context, year, month)
        generate_month_requisitions(context, year, month)
        generate_month_work_orders_and_requisitions(context, year, month)
        generate_month_purchase_orders(context, year, month)
        generate_month_goods_receipts(context, year, month)
        generate_month_manufacturing_activity(context, year, month)
        generate_month_payroll(context, year, month)
        close_eligible_work_orders(context, year, month)
        generate_month_shipments(context, year, month)
        generate_month_sales_invoices(context, year, month)
        generate_month_cash_receipts(context, year, month)
        generate_month_sales_returns(context, year, month)
        generate_month_customer_refunds(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_capex_activity(context, year, month)
        generate_month_disbursements(context, year, month)
    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase13(context)
    export_validation_report(context)

    return context


def build_phase14(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase2(config_path)
    generate_payroll_periods(context)

    for year, month in [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]:
        generate_month_o2c(context, year, month)
        generate_month_requisitions(context, year, month)
        generate_month_work_orders_and_requisitions(context, year, month)
        generate_month_purchase_orders(context, year, month)
        generate_month_goods_receipts(context, year, month)
        generate_month_manufacturing_activity(context, year, month)
        generate_month_payroll(context, year, month)
        close_eligible_work_orders(context, year, month)
        generate_month_shipments(context, year, month)
        generate_month_sales_invoices(context, year, month)
        generate_month_cash_receipts(context, year, month)
        generate_month_sales_returns(context, year, month)
        generate_month_customer_refunds(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_capex_activity(context, year, month)
        generate_month_disbursements(context, year, month)
    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase14(context)
    export_validation_report(context)

    return context


def build_phase15(config_path: str | Path = "config/settings.yaml") -> GenerationContext:
    context = build_phase2(config_path)
    generate_payroll_periods(context)

    for year, month in [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]:
        generate_month_o2c(context, year, month)
        generate_month_requisitions(context, year, month)
        generate_month_work_orders_and_requisitions(context, year, month)
        generate_month_purchase_orders(context, year, month)
        generate_month_goods_receipts(context, year, month)
        generate_month_manufacturing_activity(context, year, month)
        generate_month_payroll(context, year, month)
        close_eligible_work_orders(context, year, month)
        generate_month_shipments(context, year, month)
        generate_month_sales_invoices(context, year, month)
        generate_month_cash_receipts(context, year, month)
        generate_month_sales_returns(context, year, month)
        generate_month_customer_refunds(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_capex_activity(context, year, month)
        generate_month_disbursements(context, year, month)
    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase15(context)
    export_validation_report(context)

    return context


def build_phase15_2(
    config_path: str | Path = "config/settings.yaml",
    validation_scope: str = "full",
) -> GenerationContext:
    context = build_phase2(config_path)
    generate_payroll_periods(context)

    for year, month in [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]:
        generate_month_o2c(context, year, month)
        generate_month_requisitions(context, year, month)
        generate_month_work_orders_and_requisitions(context, year, month)
        generate_month_purchase_orders(context, year, month)
        generate_month_goods_receipts(context, year, month)
        generate_month_manufacturing_activity(context, year, month)
        generate_month_payroll(context, year, month)
        close_eligible_work_orders(context, year, month)
        generate_month_shipments(context, year, month)
        generate_month_sales_invoices(context, year, month)
        generate_month_cash_receipts(context, year, month)
        generate_month_sales_returns(context, year, month)
        generate_month_customer_refunds(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_disbursements(context, year, month)
    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase15_2(context, scope=validation_scope)
    export_validation_report(context)

    return context


def build_phase16(
    config_path: str | Path = "config/settings.yaml",
    validation_scope: str = "full",
) -> GenerationContext:
    context = build_phase2(config_path)
    generate_payroll_periods(context)
    generate_shift_definitions_and_assignments(context)

    for year, month in [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]:
        generate_month_o2c(context, year, month)
        generate_month_requisitions(context, year, month)
        generate_month_work_orders_and_requisitions(context, year, month)
        generate_month_purchase_orders(context, year, month)
        generate_month_goods_receipts(context, year, month)
        generate_month_manufacturing_activity(context, year, month)
        generate_month_payroll(context, year, month)
        close_eligible_work_orders(context, year, month)
        generate_month_shipments(context, year, month)
        generate_month_sales_invoices(context, year, month)
        generate_month_cash_receipts(context, year, month)
        generate_month_sales_returns(context, year, month)
        generate_month_customer_refunds(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_disbursements(context, year, month)
    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase16(context, scope=validation_scope)
    export_validation_report(context)

    return context


def build_phase17(
    config_path: str | Path = "config/settings.yaml",
    validation_scope: str = "full",
) -> GenerationContext:
    context = build_phase2(config_path)
    generate_payroll_periods(context)
    generate_shift_definitions_and_assignments(context)

    for year, month in [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]:
        generate_month_o2c(context, year, month)
        generate_month_requisitions(context, year, month)
        generate_month_work_orders_and_requisitions(context, year, month)
        generate_month_purchase_orders(context, year, month)
        generate_month_goods_receipts(context, year, month)
        generate_month_manufacturing_activity(context, year, month)
        generate_month_payroll(context, year, month)
        close_eligible_work_orders(context, year, month)
        generate_month_shipments(context, year, month)
        generate_month_sales_invoices(context, year, month)
        generate_month_cash_receipts(context, year, month)
        generate_month_sales_returns(context, year, month)
        generate_month_customer_refunds(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_disbursements(context, year, month)
    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase17(context, scope=validation_scope)
    export_validation_report(context)

    return context


def build_phase18(
    config_path: str | Path = "config/settings.yaml",
    validation_scope: str = "full",
) -> GenerationContext:
    context = build_phase2(config_path)
    generate_payroll_periods(context)
    generate_shift_definitions_and_assignments(context)

    for year, month in [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]:
        generate_month_o2c(context, year, month)
        generate_month_requisitions(context, year, month)
        generate_month_work_orders_and_requisitions(context, year, month)
        generate_month_purchase_orders(context, year, month)
        generate_month_goods_receipts(context, year, month)
        generate_month_manufacturing_activity(context, year, month)
        generate_month_payroll(context, year, month)
        close_eligible_work_orders(context, year, month)
        generate_month_shipments(context, year, month)
        generate_month_sales_invoices(context, year, month)
        generate_month_cash_receipts(context, year, month)
        generate_month_sales_returns(context, year, month)
        generate_month_customer_refunds(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_disbursements(context, year, month)
    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase18(context, scope=validation_scope)
    export_validation_report(context)

    return context


def build_phase19(
    config_path: str | Path = "config/settings.yaml",
    validation_scope: str = "full",
) -> GenerationContext:
    context = build_phase18(config_path, validation_scope=validation_scope)
    validate_phase19(context, scope=validation_scope)
    export_validation_report(context)
    return context


def build_phase20(
    config_path: str | Path = "config/settings.yaml",
    validation_scope: str = "full",
) -> GenerationContext:
    context = build_phase19(config_path, validation_scope=validation_scope)
    validate_phase20(context, scope=validation_scope)
    export_validation_report(context)
    return context


def build_phase21(
    config_path: str | Path = "config/settings.yaml",
    validation_scope: str = "full",
) -> GenerationContext:
    context = build_phase20(config_path, validation_scope=validation_scope)
    validate_phase21(context, scope=validation_scope)
    export_validation_report(context)
    return context


def build_phase22(
    config_path: str | Path = "config/settings.yaml",
    validation_scope: str = "full",
) -> GenerationContext:
    context = build_phase2(config_path)
    generate_payroll_periods(context)
    generate_shift_definitions_and_assignments(context)
    synchronize_work_center_capacity_and_calendars(context)
    generate_all_months(context)
    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase22(context, scope=validation_scope)
    export_validation_report(context)
    return context


def build_phase23(
    config_path: str | Path = "config/settings.yaml",
    validation_scope: str = "full",
) -> GenerationContext:
    context = build_phase2(config_path)
    generate_price_lists(context)
    generate_promotions(context)
    generate_payroll_periods(context)
    generate_shift_definitions_and_assignments(context)
    synchronize_work_center_capacity_and_calendars(context)
    generate_all_months(context)
    generate_recurring_manual_journals(context)
    generate_accrued_service_settlements(context)
    generate_accrual_adjustment_journals(context)
    post_all_transactions(context)
    generate_year_end_close_journals(context)
    validate_phase23(context, scope=validation_scope)
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
    fiscal_start = pd.Timestamp(context.settings.fiscal_year_start)
    for year, month in fiscal_months(context):
        generate_month_o2c(context, year, month)
        generate_month_planning(context, year, month)
        if year == int(fiscal_start.year) and month == int(fiscal_start.month):
            seed_opening_manufacturing_pipeline(context)
            generate_month_planning(context, year, month)
            seed_opening_manufacturing_pipeline(context)
        generate_month_requisitions(context, year, month)
        generate_month_work_orders_and_requisitions(context, year, month)
        generate_month_purchase_orders(context, year, month)
        generate_month_goods_receipts(context, year, month)
        replenishment_requisitions_created = generate_month_manufacturing_activity(context, year, month)
        if replenishment_requisitions_created:
            generate_month_purchase_orders(context, year, month)
            generate_month_goods_receipts(context, year, month)
            generate_month_manufacturing_activity(context, year, month)
        generate_month_payroll(context, year, month)
        close_eligible_work_orders(context, year, month)
        generate_month_shipments(context, year, month)
        generate_month_sales_invoices(context, year, month)
        generate_month_cash_receipts(context, year, month)
        generate_month_sales_returns(context, year, month)
        generate_month_customer_refunds(context, year, month)
        generate_month_purchase_invoices(context, year, month)
        generate_month_disbursements(context, year, month)


def _phase8_results_from_phase23_results(
    context: GenerationContext,
    phase23_results: dict[str, Any],
) -> dict[str, Any]:
    exceptions = list(phase23_results["exceptions"])
    if context.settings.anomaly_mode != "none" and not context.anomaly_log:
        exceptions.append("Anomaly mode is enabled but no anomalies were logged.")

    return {
        "row_counts": {table: int(len(df)) for table, df in context.tables.items()},
        "exceptions": exceptions,
        "gl_balance": phase23_results["gl_balance"],
        "trial_balance_difference": phase23_results["trial_balance_difference"],
        "account_rollforward": phase23_results["account_rollforward"],
        "anomaly_count": len(context.anomaly_log),
        "o2c_controls": phase23_results["o2c_controls"],
        "p2p_controls": phase23_results["p2p_controls"],
        "journal_controls": phase23_results["journal_controls"],
        "manufacturing_controls": phase23_results["manufacturing_controls"],
        "manufacturing_audit_seeds": phase23_results.get(
            "manufacturing_audit_seeds",
            {"exception_count": 0, "exceptions": []},
        ),
        "payroll_controls": phase23_results["payroll_controls"],
        "routing_controls": phase23_results["routing_controls"],
        "capacity_controls": phase23_results["capacity_controls"],
        "time_clock_controls": phase23_results.get("time_clock_controls", {"exception_count": 0, "exceptions": []}),
        "master_data_controls": phase23_results.get("master_data_controls", {"exception_count": 0, "exceptions": []}),
        "workforce_planning_controls": phase23_results.get(
            "workforce_planning_controls",
            {"exception_count": 0, "exceptions": []},
        ),
        "planning_controls": phase23_results.get("planning_controls", {"exception_count": 0, "exceptions": []}),
        "pricing_controls": phase23_results.get("pricing_controls", {"exception_count": 0, "exceptions": []}),
    }


def build_full_dataset(
    config_path: str | Path = "config/settings.yaml",
    validation_scope: str = "full",
) -> GenerationContext:
    settings = load_settings(config_path)
    configure_generation_logging(generation_log_path(settings))
    LOGGER.info("Starting dataset generation for %s.", settings.company_name)
    log_settings(settings, config_path)
    LOGGER.info("Validation scope: %s", validation_scope)
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
        _generate_phase2_master_data_and_planning(context, log_substeps=True)
        log_table_counts(
            context,
            (
                "Item",
                "BillOfMaterial",
                "BillOfMaterialLine",
                "WorkCenter",
                "WorkCenterCalendar",
                "Routing",
                "RoutingOperation",
                "Customer",
                "Supplier",
                "JournalEntry",
                "GLEntry",
                "Budget",
                "BudgetLine",
                "PayrollPeriod",
                "ShiftDefinition",
                "EmployeeShiftAssignment",
                "InventoryPolicy",
                "DemandForecast",
            ),
            "phase 2",
        )

    with logged_step("Validate phase 2"):
        log_validation_results("phase2", validate_phase2(context))

    with logged_step("Generate all configured monthly subledger transactions"):
        generated_months = list(fiscal_months(context))
        fiscal_start = pd.Timestamp(context.settings.fiscal_year_start)
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
            shipment_line_count_before = len(context.tables["ShipmentLine"])
            invoice_line_count_before = len(context.tables["PurchaseInvoiceLine"])
            disbursement_count_before = len(context.tables["DisbursementPayment"])
            work_order_count_before = len(context.tables["WorkOrder"])
            work_order_operation_count_before = len(context.tables["WorkOrderOperation"])
            work_order_operation_schedule_count_before = len(context.tables["WorkOrderOperationSchedule"])
            issue_line_count_before = len(context.tables["MaterialIssueLine"])
            completion_line_count_before = len(context.tables["ProductionCompletionLine"])
            work_order_close_count_before = len(context.tables["WorkOrderClose"])
            shift_roster_count_before = len(context.tables["EmployeeShiftRoster"])
            absence_count_before = len(context.tables["EmployeeAbsence"])
            overtime_approval_count_before = len(context.tables["OvertimeApproval"])
            time_clock_count_before = len(context.tables["TimeClockEntry"])
            time_clock_punch_count_before = len(context.tables["TimeClockPunch"])
            labor_entry_count_before = len(context.tables["LaborTimeEntry"])
            payroll_register_count_before = len(context.tables["PayrollRegister"])
            payroll_payment_count_before = len(context.tables["PayrollPayment"])
            payroll_remittance_count_before = len(context.tables["PayrollLiabilityRemittance"])
            recommendation_count_before = len(context.tables["SupplyPlanRecommendation"])
            material_plan_count_before = len(context.tables["MaterialRequirementPlan"])
            rough_cut_count_before = len(context.tables["RoughCutCapacityPlan"])
            _run_month_step(context, year, month, "generate_month_o2c", generate_month_o2c)
            _run_month_step(context, year, month, "generate_month_planning", generate_month_planning)
            if year == int(fiscal_start.year) and month == int(fiscal_start.month):
                _run_month_step(
                    context,
                    year,
                    month,
                    "seed_opening_manufacturing_pipeline",
                    lambda generation_context, _year, _month: seed_opening_manufacturing_pipeline(generation_context),
                )
                _run_month_step(
                    context,
                    year,
                    month,
                    "generate_month_planning_after_opening_pipeline",
                    generate_month_planning,
                )
                _run_month_step(
                    context,
                    year,
                    month,
                    "seed_opening_manufacturing_pipeline_followup",
                    lambda generation_context, _year, _month: seed_opening_manufacturing_pipeline(generation_context),
                )
            _run_month_step(context, year, month, "generate_month_requisitions", generate_month_requisitions)
            _run_month_step(
                context,
                year,
                month,
                "generate_month_work_orders_and_requisitions",
                generate_month_work_orders_and_requisitions,
            )
            _run_month_step(context, year, month, "generate_month_purchase_orders", generate_month_purchase_orders)
            _run_month_step(context, year, month, "generate_month_goods_receipts", generate_month_goods_receipts)
            replenishment_requisitions_created = _run_month_step(
                context,
                year,
                month,
                "generate_month_manufacturing_activity",
                generate_month_manufacturing_activity,
            )
            if replenishment_requisitions_created:
                _run_month_step(
                    context,
                    year,
                    month,
                    "generate_month_purchase_orders_followup",
                    generate_month_purchase_orders,
                )
                _run_month_step(
                    context,
                    year,
                    month,
                    "generate_month_goods_receipts_followup",
                    generate_month_goods_receipts,
                )
                _run_month_step(
                    context,
                    year,
                    month,
                    "generate_month_manufacturing_activity_followup",
                    generate_month_manufacturing_activity,
                )
            _run_month_step(context, year, month, "generate_month_payroll", generate_month_payroll)
            _run_month_step(context, year, month, "close_eligible_work_orders", close_eligible_work_orders)
            _run_month_step(context, year, month, "generate_month_shipments", generate_month_shipments)
            _run_month_step(context, year, month, "generate_month_sales_invoices", generate_month_sales_invoices)
            _run_month_step(context, year, month, "generate_month_cash_receipts", generate_month_cash_receipts)
            _run_month_step(context, year, month, "generate_month_sales_returns", generate_month_sales_returns)
            _run_month_step(
                context,
                year,
                month,
                "generate_month_customer_refunds",
                generate_month_customer_refunds,
            )
            _run_month_step(context, year, month, "generate_month_purchase_invoices", generate_month_purchase_invoices)
            _run_month_step(context, year, month, "generate_month_capex_activity", generate_month_capex_activity)
            _run_month_step(context, year, month, "generate_month_disbursements", generate_month_disbursements)
            requisitions_converted_after = int(context.tables["PurchaseRequisition"]["Status"].eq("Converted to PO").sum())
            new_shipment_lines = context.tables["ShipmentLine"].iloc[shipment_line_count_before:]
            new_receipt_lines = context.tables["GoodsReceiptLine"].iloc[receipt_line_count_before:]
            new_invoice_lines = context.tables["PurchaseInvoiceLine"].iloc[invoice_line_count_before:]
            new_disbursements = context.tables["DisbursementPayment"].iloc[disbursement_count_before:]
            new_work_orders = context.tables["WorkOrder"].iloc[work_order_count_before:]
            new_work_order_operations = context.tables["WorkOrderOperation"].iloc[work_order_operation_count_before:]
            new_work_order_operation_schedules = context.tables["WorkOrderOperationSchedule"].iloc[work_order_operation_schedule_count_before:]
            new_issue_lines = context.tables["MaterialIssueLine"].iloc[issue_line_count_before:]
            new_completion_lines = context.tables["ProductionCompletionLine"].iloc[completion_line_count_before:]
            new_work_order_closes = context.tables["WorkOrderClose"].iloc[work_order_close_count_before:]
            new_recommendations = context.tables["SupplyPlanRecommendation"].iloc[recommendation_count_before:]
            new_material_plans = context.tables["MaterialRequirementPlan"].iloc[material_plan_count_before:]
            new_rough_cut = context.tables["RoughCutCapacityPlan"].iloc[rough_cut_count_before:]
            payroll_state = monthly_payroll_state(context, year, month)
            open_state = p2p_open_state(context)
            revenue_state = o2c_open_state(
                context,
                as_of_date=pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(1),
            )
            manufacturing_state = manufacturing_open_state(context)
            capacity_state = manufacturing_capacity_state(context, year, month)
            bottleneck_state = manufacturing_work_center_utilization_by_code(context, year, month)
            capacity_diagnostics = manufacturing_capacity_diagnostics_by_code(context, year, month)
            new_cash_receipts = context.tables["CashReceipt"][
                pd.to_datetime(context.tables["CashReceipt"]["ReceiptDate"]).dt.year.eq(year)
                & pd.to_datetime(context.tables["CashReceipt"]["ReceiptDate"]).dt.month.eq(month)
            ]
            new_sales_returns = context.tables["SalesReturn"][
                pd.to_datetime(context.tables["SalesReturn"]["ReturnDate"]).dt.year.eq(year)
                & pd.to_datetime(context.tables["SalesReturn"]["ReturnDate"]).dt.month.eq(month)
            ]
            new_credit_memos = context.tables["CreditMemo"][
                pd.to_datetime(context.tables["CreditMemo"]["CreditMemoDate"]).dt.year.eq(year)
                & pd.to_datetime(context.tables["CreditMemo"]["CreditMemoDate"]).dt.month.eq(month)
            ]
            new_refunds = context.tables["CustomerRefund"][
                pd.to_datetime(context.tables["CustomerRefund"]["RefundDate"]).dt.year.eq(year)
                & pd.to_datetime(context.tables["CustomerRefund"]["RefundDate"]).dt.month.eq(month)
            ]
            LOGGER.info(
                "O2C CHECKPOINT | %s-%02d | shipment_lines_created=%s | shipped_quantity=%s | cash_receipts_created=%s | cash_received=%s | returns_created=%s | credit_memos_created=%s | refunds_created=%s | distinct_returned_invoices=%s | invoice_return_incidence_ratio=%s | return_quantity_ratio=%s | credit_memo_subtotal_ratio=%s | open_order_quantity=%s | backordered_quantity=%s | unbilled_shipment_quantity=%s | open_ar_amount=%s | trailing_twelve_month_sales=%s | implied_dso=%s | aging_not_due_amount=%s | aging_0_30_amount=%s | aging_31_60_amount=%s | aging_61_90_amount=%s | aging_90_plus_amount=%s | aging_90_plus_share=%s | aging_current_to_60_share=%s | open_invoices_gt_365_count=%s | unapplied_cash_amount=%s | customer_credit_amount=%s",
                year,
                month,
                len(new_shipment_lines),
                round(float(new_shipment_lines["QuantityShipped"].sum()), 2) if not new_shipment_lines.empty else 0.0,
                len(new_cash_receipts),
                round(float(new_cash_receipts["Amount"].sum()), 2) if not new_cash_receipts.empty else 0.0,
                len(new_sales_returns),
                len(new_credit_memos),
                len(new_refunds),
                revenue_state["distinct_returned_invoices"],
                revenue_state["invoice_return_incidence_ratio"],
                revenue_state["return_quantity_ratio"],
                revenue_state["credit_memo_subtotal_ratio"],
                revenue_state["open_order_quantity"],
                revenue_state["backordered_quantity"],
                revenue_state["unbilled_shipment_quantity"],
                revenue_state["open_ar_amount"],
                revenue_state["trailing_twelve_month_sales"],
                revenue_state["implied_dso"],
                revenue_state["aging_not_due_amount"],
                revenue_state["aging_0_30_amount"],
                revenue_state["aging_31_60_amount"],
                revenue_state["aging_61_90_amount"],
                revenue_state["aging_90_plus_amount"],
                revenue_state["aging_90_plus_share"],
                revenue_state["aging_current_to_60_share"],
                revenue_state["open_invoices_gt_365_count"],
                revenue_state["unapplied_cash_amount"],
                revenue_state["customer_credit_amount"],
            )
            LOGGER.info(
                "MFG CHECKPOINT | %s-%02d | manufactured_items=%s | work_centers=%s | work_center_calendar_rows=%s | routing_count=%s | routing_operation_count=%s | bom_count=%s | bom_line_count=%s | work_orders_released=%s | work_order_operations_created=%s | work_order_operation_schedule_rows_created=%s | issue_lines_created=%s | issue_cost=%s | completion_lines_created=%s | completed_quantity=%s | work_orders_closed=%s | open_work_order_count=%s | wip_balance=%s | manufacturing_clearing_balance=%s | manufacturing_variance_posted=%s",
                year,
                month,
                int(manufacturing_state["manufactured_item_count"]),
                int(manufacturing_state["work_center_count"]),
                int(manufacturing_state["work_center_calendar_count"]),
                int(manufacturing_state["routing_count"]),
                int(manufacturing_state["routing_operation_count"]),
                int(manufacturing_state["bom_count"]),
                int(manufacturing_state["bom_line_count"]),
                len(new_work_orders),
                len(new_work_order_operations),
                len(new_work_order_operation_schedules),
                len(new_issue_lines),
                round(float(new_issue_lines["ExtendedStandardCost"].sum()), 2) if not new_issue_lines.empty else 0.0,
                len(new_completion_lines),
                round(float(new_completion_lines["QuantityCompleted"].sum()), 2) if not new_completion_lines.empty else 0.0,
                len(new_work_order_closes),
                int(manufacturing_state["open_work_order_count"]),
                manufacturing_state["wip_balance"],
                manufacturing_state["manufacturing_clearing_balance"],
                manufacturing_state["manufacturing_variance_posted"],
            )
            LOGGER.info(
                "CAPACITY CHECKPOINT | %s-%02d | available_hours=%s | scheduled_hours=%s | utilization_pct=%s | assembly_utilization=%s | cut_utilization=%s | finish_utilization=%s | fully_booked_days=%s | late_operations=%s | late_work_orders=%s | open_backlog_hours=%s",
                year,
                month,
                capacity_state["available_work_center_hours"],
                capacity_state["scheduled_work_center_hours"],
                capacity_state["utilization_pct"],
                bottleneck_state["ASSEMBLY"],
                bottleneck_state["CUT"],
                bottleneck_state["FINISH"],
                int(capacity_state["fully_booked_days"]),
                int(capacity_state["late_operations"]),
                int(capacity_state["late_work_orders"]),
                capacity_state["open_backlog_hours"],
            )
            for work_center_code in ["ASSEMBLY", "FINISH", "CUT", "PACK", "QA"]:
                diagnostic = capacity_diagnostics.get(work_center_code, {})
                LOGGER.info(
                    "CAPACITY DIAGNOSTIC | %s-%02d | work_center=%s | assigned_direct_worker_count=%s | assigned_direct_worker_share=%s | nominal_daily_capacity_hours=%s | nominal_daily_capacity_share=%s | rostered_hours=%s | scheduled_hours=%s | monthly_available_hours=%s | monthly_utilization_pct=%s",
                    year,
                    month,
                    work_center_code,
                    round(float(diagnostic.get("assigned_direct_worker_count", 0.0)), 2),
                    diagnostic.get("assigned_direct_worker_share", 0.0),
                    diagnostic.get("nominal_daily_capacity_hours", 0.0),
                    diagnostic.get("nominal_daily_capacity_share", 0.0),
                    diagnostic.get("rostered_hours", 0.0),
                    diagnostic.get("scheduled_hours", 0.0),
                    diagnostic.get("monthly_available_hours", 0.0),
                    diagnostic.get("monthly_utilization_pct", 0.0),
                )
            LOGGER.info(
                "PAYROLL CHECKPOINT | %s-%02d | periods_processed=%s | shift_rosters_created=%s | absences_created=%s | overtime_approvals_created=%s | time_clock_entries_created=%s | punch_rows_created=%s | labor_entries_created=%s | payroll_registers_created=%s | payroll_payments_created=%s | liability_remittances_created=%s | fallback_direct_allocations=%s | direct_labor_reclass_amount=%s | manufacturing_overhead_reclass_amount=%s",
                year,
                month,
                int(payroll_state["periods_processed"]),
                len(context.tables["EmployeeShiftRoster"]) - shift_roster_count_before,
                len(context.tables["EmployeeAbsence"]) - absence_count_before,
                len(context.tables["OvertimeApproval"]) - overtime_approval_count_before,
                len(context.tables["TimeClockEntry"]) - time_clock_count_before,
                len(context.tables["TimeClockPunch"]) - time_clock_punch_count_before,
                len(context.tables["LaborTimeEntry"]) - labor_entry_count_before,
                len(context.tables["PayrollRegister"]) - payroll_register_count_before,
                len(context.tables["PayrollPayment"]) - payroll_payment_count_before,
                len(context.tables["PayrollLiabilityRemittance"]) - payroll_remittance_count_before,
                int(payroll_state["fallback_direct_allocations"]),
                payroll_state["direct_labor_reclass_amount"],
                payroll_state["manufacturing_overhead_reclass_amount"],
            )
            LOGGER.info(
                "PLANNING CHECKPOINT | %s-%02d | recommendations_created=%s | planned_quantity=%s | material_plan_rows_created=%s | rough_cut_rows_created=%s | expedite_recommendations=%s",
                year,
                month,
                len(new_recommendations),
                round(float(new_recommendations["RecommendedOrderQuantity"].astype(float).sum()), 2) if not new_recommendations.empty else 0.0,
                len(new_material_plans),
                len(new_rough_cut),
                int(new_recommendations["PriorityCode"].eq("Expedite").sum()) if not new_recommendations.empty else 0,
            )
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
                "WorkOrder",
                "WorkOrderOperation",
                "WorkOrderOperationSchedule",
                "EmployeeShiftRoster",
                "EmployeeAbsence",
                "OvertimeApproval",
                "TimeClockEntry",
                "TimeClockPunch",
                "LaborTimeEntry",
                "PayrollRegister",
                "DemandForecast",
                "InventoryPolicy",
                "SupplyPlanRecommendation",
                "MaterialRequirementPlan",
                "RoughCutCapacityPlan",
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

    with logged_step("Generate accrued expense settlement invoices and payments"):
        generate_accrued_service_settlements(context)
        log_table_counts(
            context,
            ("PurchaseInvoice", "PurchaseInvoiceLine", "DisbursementPayment"),
            "accrued expense settlements",
        )

    with logged_step("Generate accrual adjustment journals"):
        generate_accrual_adjustment_journals(context)
        log_table_counts(context, ("JournalEntry", "GLEntry"), "accrual adjustments")

    with logged_step("Post transactions to general ledger"):
        post_all_transactions(context)
        log_table_counts(context, ("JournalEntry", "GLEntry"), "posting")

    with logged_step("Generate year-end close journals"):
        generate_year_end_close_journals(context)
        log_table_counts(context, ("JournalEntry", "GLEntry"), "year-end close")

    with logged_step("Log opening-state diagnostics"):
        log_opening_state_shock_diagnostics(context)
        log_manufactured_load_calibration(context)
        log_manufactured_planning_diagnostics(context)
        log_manufactured_flow_diagnostics(context)
        log_annual_capacity_diagnostics(context)

    with logged_step("Validate clean final dataset"):
        log_validation_results("phase23", validate_phase23(context, scope=validation_scope))
    phase23_results = context.validation_results["phase23"]

    if context.settings.anomaly_mode == "none":
        with logged_step("Skip anomaly injection for clean dataset"):
            LOGGER.info("ANOMALIES | skipped because anomaly_mode=none")

        with logged_step("Reuse clean validation results for phase 8"):
            phase8_results = _phase8_results_from_phase23_results(context, phase23_results)
            context.validation_results["phase8"] = phase8_results
            log_validation_results("phase8", phase8_results)
    else:
        with logged_step("Inject configured anomalies"):
            inject_anomalies(context)
            invalidate_all_caches(context)
            journal_anomaly_count = sum(
                1
                for anomaly in context.anomaly_log
                if anomaly["table_name"] == "JournalEntry" or anomaly["anomaly_type"].endswith("_manual_journal")
            )
            LOGGER.info(
                "ANOMALIES | total_count=%s | journal_anomaly_count=%s",
                len(context.anomaly_log),
                journal_anomaly_count,
            )

        with logged_step("Validate anomaly-enriched dataset"):
            log_validation_results("phase8", validate_phase8(context, scope=validation_scope))

    with logged_step("Log GL row-budget diagnostics"):
        log_gl_row_budget_diagnostics(context)

    if context.settings.export_sqlite:
        with logged_step("Export SQLite database"):
            export_sqlite(context)
            LOGGER.info("EXPORT | sqlite | path=%s", context.settings.sqlite_path)
    else:
        LOGGER.info("SKIP | SQLite export disabled.")

    if context.settings.export_reports:
        with logged_step("Export curated reports"):
            export_reports(context)
            LOGGER.info("EXPORT | reports | path=%s", context.settings.report_output_dir)
    else:
        LOGGER.info("SKIP | Report export disabled.")

    if context.settings.export_excel:
        with logged_step("Export Excel workbook"):
            export_excel(context)
            LOGGER.info("EXPORT | excel | path=%s", context.settings.excel_path)
    else:
        LOGGER.info("SKIP | Excel export disabled.")

    if context.settings.export_support_excel:
        with logged_step("Export support workbook"):
            export_support_excel(context)
            LOGGER.info("EXPORT | support_excel | path=%s", context.settings.support_excel_path)
    else:
        LOGGER.info("SKIP | Support workbook export disabled.")

    if context.settings.export_csv_zip:
        with logged_step("Export CSV zip package"):
            export_csv_zip(context)
            LOGGER.info("EXPORT | csv_zip | path=%s", context.settings.csv_zip_path)
    else:
        LOGGER.info("SKIP | CSV zip export disabled.")

    log_all_table_counts(context, "final")
    LOGGER.info("Finished dataset generation for %s.", context.settings.company_name)
    close_generation_logging()

    return context


def print_summary(context: GenerationContext) -> None:
    row_counts = context.validation_results["phase23"]["row_counts"]
    print("Full dataset generated.")
    print(f"Fiscal range: {context.settings.fiscal_year_start} to {context.settings.fiscal_year_end}")
    print(f"Accounts: {row_counts['Account']}")
    print(f"Cost centers: {row_counts['CostCenter']}")
    print(f"Employees: {row_counts['Employee']}")
    print(f"Warehouses: {row_counts['Warehouse']}")
    print(f"Items: {row_counts['Item']}")
    print(f"Work centers: {row_counts['WorkCenter']}")
    print(f"Work-center calendar rows: {row_counts['WorkCenterCalendar']}")
    print(f"Routings: {row_counts['Routing']}")
    print(f"Routing operations: {row_counts['RoutingOperation']}")
    print(f"Shift definitions: {row_counts['ShiftDefinition']}")
    print(f"Employee shift assignments: {row_counts['EmployeeShiftAssignment']}")
    print(f"Employee shift rosters: {row_counts['EmployeeShiftRoster']}")
    print(f"Employee absences: {row_counts['EmployeeAbsence']}")
    print(f"Overtime approvals: {row_counts['OvertimeApproval']}")
    print(f"Demand forecasts: {row_counts['DemandForecast']}")
    print(f"Inventory policies: {row_counts['InventoryPolicy']}")
    print(f"Supply plan recommendations: {row_counts['SupplyPlanRecommendation']}")
    print(f"Material requirement plan rows: {row_counts['MaterialRequirementPlan']}")
    print(f"Rough-cut capacity rows: {row_counts['RoughCutCapacityPlan']}")
    print(f"Customers: {row_counts['Customer']}")
    print(f"Price lists: {row_counts['PriceList']}")
    print(f"Price list lines: {row_counts['PriceListLine']}")
    print(f"Promotion programs: {row_counts['PromotionProgram']}")
    print(f"Price override approvals: {row_counts['PriceOverrideApproval']}")
    print(f"Suppliers: {row_counts['Supplier']}")
    print(f"Journal entries: {row_counts['JournalEntry']}")
    print(f"Budget rows: {row_counts['Budget']}")
    print(f"Budget detail rows: {row_counts['BudgetLine']}")
    print(f"Sales orders: {row_counts['SalesOrder']}")
    print(f"Sales order lines: {row_counts['SalesOrderLine']}")
    print(f"Purchase requisitions: {row_counts['PurchaseRequisition']}")
    print(f"Purchase orders: {row_counts['PurchaseOrder']}")
    print(f"Purchase order lines: {row_counts['PurchaseOrderLine']}")
    print(f"Work orders: {row_counts['WorkOrder']}")
    print(f"Work order operations: {row_counts['WorkOrderOperation']}")
    print(f"Work order operation schedules: {row_counts['WorkOrderOperationSchedule']}")
    print(f"Shipments: {row_counts['Shipment']}")
    print(f"Shipment lines: {row_counts['ShipmentLine']}")
    print(f"Goods receipts: {row_counts['GoodsReceipt']}")
    print(f"Goods receipt lines: {row_counts['GoodsReceiptLine']}")
    print(f"Sales invoices: {row_counts['SalesInvoice']}")
    print(f"Sales invoice lines: {row_counts['SalesInvoiceLine']}")
    print(f"Cash receipts: {row_counts['CashReceipt']}")
    print(f"Cash receipt applications: {row_counts['CashReceiptApplication']}")
    print(f"Sales returns: {row_counts['SalesReturn']}")
    print(f"Sales return lines: {row_counts['SalesReturnLine']}")
    print(f"Credit memos: {row_counts['CreditMemo']}")
    print(f"Credit memo lines: {row_counts['CreditMemoLine']}")
    print(f"Customer refunds: {row_counts['CustomerRefund']}")
    print(f"Purchase invoices: {row_counts['PurchaseInvoice']}")
    print(f"Purchase invoice lines: {row_counts['PurchaseInvoiceLine']}")
    print(f"Disbursements: {row_counts['DisbursementPayment']}")
    print(f"Payroll periods: {row_counts['PayrollPeriod']}")
    print(f"Time-clock entries: {row_counts['TimeClockEntry']}")
    print(f"Time-clock punches: {row_counts['TimeClockPunch']}")
    print(f"Labor time entries: {row_counts['LaborTimeEntry']}")
    print(f"Payroll registers: {row_counts['PayrollRegister']}")
    print(f"Payroll register lines: {row_counts['PayrollRegisterLine']}")
    print(f"Payroll payments: {row_counts['PayrollPayment']}")
    print(f"Payroll liability remittances: {row_counts['PayrollLiabilityRemittance']}")
    print(f"GL entries: {row_counts['GLEntry']}")
    print(f"GL balance exceptions: {context.validation_results['phase23']['gl_balance']['exception_count']}")
    print(f"Anomalies logged: {len(context.anomaly_log)}")
    print(f"SQLite export: {context.settings.sqlite_path}")
    print(f"Excel export: {context.settings.excel_path}")
    if context.settings.export_reports:
        print(f"Report output directory: {context.settings.report_output_dir}")
    print(f"Support workbook: {context.settings.support_excel_path}")
    print(f"CSV zip export: {context.settings.csv_zip_path}")
    print(f"Generation log: {generation_log_path(context)}")


def main(config_path: str | Path = "config/settings.yaml", validation_scope: str = "full") -> None:
    print_summary(build_full_dataset(config_path, validation_scope=validation_scope))


if __name__ == "__main__":
    main()
