from __future__ import annotations

from collections import defaultdict
import hashlib
from typing import Any

import numpy as np
import pandas as pd

from generator_dataset.master_data import (
    DESIGN_SERVICE_COST_CENTER,
    DESIGN_SERVICE_SEGMENT,
    approver_employee_id,
    employee_active_mask,
    employee_ids_for_cost_center_as_of,
    eligible_item_mask,
)
from generator_dataset.payroll import implied_hourly_rate
from generator_dataset.planning import monthly_forecast_targets, opening_inventory_map as planning_opening_inventory_map
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.settings import GenerationContext
from generator_dataset.utils import format_doc_number, money, next_id, qty, random_date_in_month


SEGMENT_ORDER_WEIGHTS = {
    "Strategic": 4.0,
    "Wholesale": 2.5,
    "Design Trade": 1.7,
    "Small Business": 1.0,
    DESIGN_SERVICE_SEGMENT: 0.7,
}

SEGMENT_LINE_RANGES = {
    "Strategic": (3, 7),
    "Wholesale": (2, 6),
    "Design Trade": (2, 5),
    "Small Business": (1, 4),
}

SEGMENT_QUANTITY_RANGES = {
    "Strategic": (4, 18),
    "Wholesale": (3, 14),
    "Design Trade": (2, 9),
    "Small Business": (1, 6),
}

OPENING_STOCK_RANGES = {
    "Furniture": (45, 95),
    "Lighting": (90, 160),
    "Textiles": (120, 220),
    "Accessories": (140, 260),
    "Packaging": (180, 340),
    "Raw Materials": (220, 420),
}

RETURN_REASON_CODES = ["Damaged", "Wrong Item", "Customer Remorse", "Quality Concern", "Late Delivery"]
FULL_RETURN_REASON_CODES = {"Damaged", "Wrong Item"}

TARGET_INVOICE_RETURN_RATE = 0.03
TARGET_INVOICE_RETURN_RATE_MIN = 0.025
TARGET_INVOICE_RETURN_RATE_MAX = 0.035
RETURN_LAG_DAYS_RANGE = (7, 45)
RETURN_LINE_COUNT_PROBABILITIES = ((1, 0.82), (2, 0.18))
PARTIAL_RETURN_FRACTION_RANGE = (0.10, 0.40)
FULL_RETURN_REASON_PROBABILITY = 0.20

CARRIERS = ["Private Fleet", "FedEx Freight", "UPS Freight", "DHL Supply Chain"]
PAYMENT_METHODS = ["ACH", "Wire Transfer", "Check", "Credit Card"]
SALES_COMMISSION_PAYMENT_METHODS = ["ACH", "Direct Deposit"]
SALES_COMMISSION_REVENUE_TYPES = ("Merchandise", "Design Service")
SALES_COMMISSION_RATES = {
    ("Merchandise", "Strategic"): 0.0200,
    ("Merchandise", "Wholesale"): 0.0150,
    ("Merchandise", "Design Trade"): 0.0250,
    ("Merchandise", "Small Business"): 0.0300,
    ("Design Service", "Strategic"): 0.0300,
    ("Design Service", "Wholesale"): 0.0250,
    ("Design Service", "Design Trade"): 0.0400,
    ("Design Service", "Small Business"): 0.0350,
}
SEGMENT_PRICE_DISCOUNTS = {
    "Strategic": 0.12,
    "Wholesale": 0.10,
    "Design Trade": 0.06,
    "Small Business": 0.03,
}
SEGMENT_MIN_PRICE_FLOORS = {
    "Strategic": 0.82,
    "Wholesale": 0.84,
    "Design Trade": 0.88,
    "Small Business": 0.92,
}
CUSTOMER_PRICE_LIST_SHARE = 0.35
PRICE_BREAK_ITEM_GROUPS = {"Furniture", "Lighting", "Textiles", "Accessories"}
PROMOTION_MONTH_WINDOWS = [
    ((3, 4), 0.08),
    ((9, 10), 0.10),
    ((11, 11), 0.12),
]
OVERRIDE_REASON_CODES = ["Strategic Renewal", "Competitive Match", "Project Package", "Service Recovery"]
AR_AGING_BUCKET_ORDER = ["Not Due", "0-30", "31-60", "61-90", "90+"]
SEGMENT_COLLECTION_FACTORS = {
    "Strategic": 0.94,
    "Wholesale": 0.92,
    "Design Trade": 1.02,
    "Small Business": 1.05,
    DESIGN_SERVICE_SEGMENT: 0.97,
}
TERM_COLLECTION_FACTORS = {
    30: 1.00,
    45: 0.96,
    60: 0.92,
    90: 0.86,
}
DEPOSIT_PROBABILITIES = {
    "Strategic": 0.05,
    "Wholesale": 0.04,
    "Design Trade": 0.025,
    "Small Business": 0.02,
    DESIGN_SERVICE_SEGMENT: 0.06,
}
DEPOSIT_FRACTION_RANGES = {
    "Strategic": (0.10, 0.20),
    "Wholesale": (0.09, 0.18),
    "Design Trade": (0.07, 0.15),
    "Small Business": (0.06, 0.12),
    DESIGN_SERVICE_SEGMENT: (0.12, 0.22),
}
FREIGHT_TERMS_PASS_THROUGH_PROBABILITIES = {
    "Strategic": 0.30,
    "Wholesale": 0.50,
    "Design Trade": 0.65,
    "Small Business": 0.80,
}
FREIGHT_ITEM_WEIGHT_PROXIES = {
    "Furniture": 5.20,
    "Lighting": 2.85,
    "Textiles": 1.65,
    "Accessories": 0.75,
    "Packaging": 0.40,
    "Raw Materials": 1.20,
}
FREIGHT_CARRIER_RATE_TABLE = {
    "Private Fleet": {"base_charge": 24.0, "weight_rate": 1.08},
    "FedEx Freight": {"base_charge": 31.0, "weight_rate": 1.28},
    "UPS Freight": {"base_charge": 29.0, "weight_rate": 1.35},
    "DHL Supply Chain": {"base_charge": 27.0, "weight_rate": 1.24},
}
FREIGHT_REGION_MULTIPLIERS = {
    "Northeast": 1.00,
    "Midwest": 1.05,
    "South": 1.10,
    "West": 1.18,
}
FREIGHT_PARTIAL_SHIPMENT_SURCHARGE = 1.15
FREIGHT_BILLABLE_RATE_RANGE = (0.92, 1.08)
FREIGHT_BILLABLE_CAP_RATE = 0.12
FREIGHT_CREDIT_REASON_CODES = {"Damaged", "Wrong Item", "Quality Concern", "Late Delivery"}
DESIGN_SERVICE_MONTHLY_ENGAGEMENT_RANGE = (4, 9)
DESIGN_SERVICE_PLANNED_HOURS_RANGE = (24.0, 156.0)
DESIGN_SERVICE_MONTH_SPAN_OPTIONS = ((1, 0.38), (2, 0.42), (3, 0.20))
DESIGN_SERVICE_ASSIGNMENT_OPTIONS = ((1, 0.16), (2, 0.46), (3, 0.28), (4, 0.10))
DESIGN_SERVICE_NONBILLABLE_SHARE_RANGE = (0.00, 0.10)
DESIGN_SERVICE_WORKDAYS_PER_MONTH_RANGE = (2, 6)


def stable_seed(context: GenerationContext, *parts: object) -> int:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return (context.settings.random_seed + int.from_bytes(digest[:8], "big")) % (2**32 - 1)


def stable_rng(context: GenerationContext, *parts: object) -> np.random.Generator:
    return np.random.default_rng(stable_seed(context, *parts))


def stable_uniform(context: GenerationContext, low: float, high: float, *parts: object) -> float:
    return float(stable_rng(context, *parts).uniform(low, high))


def freight_pass_through_probability(customer_segment: str, order_total: float) -> float:
    probability = float(FREIGHT_TERMS_PASS_THROUGH_PROBABILITIES.get(str(customer_segment), 0.50))
    if float(order_total) > 20000.0:
        probability -= 0.10
    elif float(order_total) < 2500.0:
        probability += 0.10
    return float(np.clip(probability, 0.10, 0.90))


def freight_terms_for_order(
    context: GenerationContext,
    *,
    sales_order_id: int,
    customer_segment: str,
    order_total: float,
) -> str:
    pass_through_probability = freight_pass_through_probability(customer_segment, order_total)
    return (
        "Prepaid and Add"
        if float(stable_rng(context, "freight-terms", sales_order_id).random()) < pass_through_probability
        else "Prepaid"
    )


def shipment_invoice_schedule(
    context: GenerationContext,
    *,
    shipment_id: int,
    shipment_date: pd.Timestamp,
    year: int,
    month: int,
) -> tuple[bool, pd.Timestamp]:
    rng = stable_rng(context, "shipment-invoice", shipment_id, year, month)
    invoice_probability = 0.88 if shipment_date.year == year and shipment_date.month == month else 0.97
    if float(rng.random()) > invoice_probability:
        return False, shipment_date

    if shipment_date.year == year and shipment_date.month == month:
        invoice_date = clamp_date_to_month(
            shipment_date + pd.Timedelta(days=int(rng.integers(0, 5))),
            year,
            month,
        )
    else:
        invoice_date = clamp_date_to_month(
            pd.Timestamp(year=year, month=month, day=1) + pd.Timedelta(days=int(rng.integers(0, 7))),
            year,
            month,
        )
    return True, invoice_date


def shipment_freight_amounts(
    context: GenerationContext,
    *,
    shipment_id: int,
    customer_region: str,
    carrier_name: str,
    freight_terms: str,
    shipped_line_metrics: list[dict[str, float | str]],
    is_partial_shipment: bool,
) -> tuple[float, float]:
    if not shipped_line_metrics:
        return 0.0, 0.0

    carrier_profile = FREIGHT_CARRIER_RATE_TABLE.get(str(carrier_name), FREIGHT_CARRIER_RATE_TABLE["Private Fleet"])
    region_multiplier = float(FREIGHT_REGION_MULTIPLIERS.get(str(customer_region), 1.10))
    line_count_factor = 1.0 + max(len(shipped_line_metrics) - 1, 0) * 0.04
    partial_multiplier = FREIGHT_PARTIAL_SHIPMENT_SURCHARGE if is_partial_shipment else 1.0
    total_weight_units = 0.0
    merchandise_subtotal = 0.0
    for line_metric in shipped_line_metrics:
        item_group = str(line_metric["ItemGroup"])
        quantity_shipped = float(line_metric["QuantityShipped"])
        total_weight_units += quantity_shipped * float(FREIGHT_ITEM_WEIGHT_PROXIES.get(item_group, 1.0))
        merchandise_subtotal += float(line_metric["MerchandiseSubTotal"])

    cost_jitter = stable_uniform(context, 0.96, 1.05, "shipment-freight-cost", shipment_id)
    actual_cost = money(
        (
            float(carrier_profile["base_charge"])
            + total_weight_units * float(carrier_profile["weight_rate"])
        )
        * region_multiplier
        * line_count_factor
        * partial_multiplier
        * cost_jitter
    )

    billable_freight_amount = 0.0
    if str(freight_terms) == "Prepaid and Add" and merchandise_subtotal > 0 and actual_cost > 0:
        bill_factor = stable_uniform(context, FREIGHT_BILLABLE_RATE_RANGE[0], FREIGHT_BILLABLE_RATE_RANGE[1], "shipment-freight-bill", shipment_id)
        capped_amount = min(float(round(actual_cost * bill_factor)), merchandise_subtotal * FREIGHT_BILLABLE_CAP_RATE)
        billable_freight_amount = money(max(capped_amount, 0.0))

    return actual_cost, billable_freight_amount


def freight_credit_amount(
    *,
    invoice_subtotal: float,
    invoice_freight_amount: float,
    returned_subtotal: float,
    reason_code: str,
) -> float:
    if str(reason_code) not in FREIGHT_CREDIT_REASON_CODES:
        return 0.0
    if float(invoice_subtotal) <= 0 or float(invoice_freight_amount) <= 0 or float(returned_subtotal) <= 0:
        return 0.0
    pro_rata_credit = float(invoice_freight_amount) * (float(returned_subtotal) / float(invoice_subtotal))
    return money(min(float(invoice_freight_amount), pro_rata_credit))


def append_rows(context: GenerationContext, table_name: str, rows: list[dict]) -> None:
    if not rows:
        return

    new_rows = pd.DataFrame(rows, columns=TABLE_COLUMNS[table_name])
    context.tables[table_name] = pd.concat(
        [context.tables[table_name], new_rows],
        ignore_index=True,
    )
    invalidate_o2c_caches(context, table_name)


def drop_context_attributes(context: GenerationContext, attribute_names: list[str]) -> None:
    for attribute_name in attribute_names:
        if hasattr(context, attribute_name):
            delattr(context, attribute_name)


def invalidate_o2c_caches(context: GenerationContext, table_name: str) -> None:
    cache_map = {
        "ShipmentLine": ["_sales_order_line_shipped_quantities_cache"],
        "SalesInvoice": [
            "_o2c_receivables_metrics_cache",
            "_credit_memo_allocation_map_as_of_cache",
            "_invoice_settled_amounts_as_of_cache",
        ],
        "SalesInvoiceLine": [
            "_shipment_line_billed_quantities_cache",
            "_invoice_cash_application_amounts_cache",
            "_credit_memo_allocation_map_cache",
            "_invoice_settled_amounts_cache",
            "_o2c_receivables_metrics_cache",
            "_credit_memo_allocation_map_as_of_cache",
            "_invoice_settled_amounts_as_of_cache",
        ],
        "CashReceiptApplication": [
            "_receipt_applied_amounts_cache",
            "_invoice_cash_application_amounts_cache",
            "_credit_memo_allocation_map_cache",
            "_invoice_settled_amounts_cache",
            "_o2c_receivables_metrics_cache",
            "_credit_memo_allocation_map_as_of_cache",
            "_invoice_settled_amounts_as_of_cache",
        ],
        "CashReceipt": [
            "_o2c_receivables_metrics_cache",
            "_credit_memo_allocation_map_as_of_cache",
            "_invoice_settled_amounts_as_of_cache",
        ],
        "CustomerRefund": ["_credit_memo_refunded_amounts_cache"],
        "SalesReturnLine": ["_shipment_line_returned_quantities_cache"],
        "CreditMemo": [
            "_returned_invoice_ids_cache",
            "_credit_memo_allocation_map_cache",
            "_invoice_settled_amounts_cache",
            "_o2c_receivables_metrics_cache",
            "_credit_memo_allocation_map_as_of_cache",
            "_invoice_settled_amounts_as_of_cache",
        ],
        "PriceList": [
            "_price_list_lookup_cache",
            "_resolved_price_list_line_cache",
        ],
        "PriceListLine": [
            "_price_list_lookup_cache",
            "_resolved_price_list_line_cache",
        ],
        "PromotionProgram": [
            "_promotion_lookup_cache",
            "_resolved_promotion_cache",
        ],
    }
    drop_context_attributes(context, cache_map.get(table_name, []))


def month_bounds(year: int, month: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(year=year, month=month, day=1)
    end = start + pd.offsets.MonthEnd(1)
    return start, end


def clamp_date_to_month(value: pd.Timestamp, year: int, month: int) -> pd.Timestamp:
    start, end = month_bounds(year, month)
    if value < start:
        return start
    if value > end:
        return end
    return value


def next_business_day(value: pd.Timestamp) -> pd.Timestamp:
    candidate = pd.Timestamp(value).normalize()
    while candidate.day_name() in {"Saturday", "Sunday"}:
        candidate = candidate + pd.Timedelta(days=1)
    return candidate


def nth_business_day(year: int, month: int, business_day_number: int) -> pd.Timestamp:
    if business_day_number <= 0:
        raise ValueError("business_day_number must be positive.")
    candidate = pd.Timestamp(year=year, month=month, day=1)
    seen = 0
    while True:
        if candidate.day_name() not in {"Saturday", "Sunday"}:
            seen += 1
            if seen == business_day_number:
                return candidate
        candidate = candidate + pd.Timedelta(days=1)


def sales_cost_center_id(context: GenerationContext) -> int:
    cost_centers = context.tables["CostCenter"]
    matches = cost_centers.loc[cost_centers["CostCenterName"].eq("Sales"), "CostCenterID"]
    if matches.empty:
        raise ValueError("Sales cost center is required for sales order generation.")
    return int(matches.iloc[0])


def employee_ids_for_cost_center(
    context: GenerationContext,
    cost_center_name: str,
    event_date: pd.Timestamp | str | None = None,
) -> list[int]:
    return employee_ids_for_cost_center_as_of(context, cost_center_name, event_date)


def commission_accounting_approver_id(context: GenerationContext, event_date: pd.Timestamp | str) -> int:
    return approver_employee_id(
        context,
        event_date,
        preferred_titles=("Accounting Manager", "Controller", "Chief Financial Officer"),
        fallback_cost_center_name="Administration",
    )


def warehouse_ids(context: GenerationContext) -> list[int]:
    warehouse_table = context.tables["Warehouse"]
    if warehouse_table.empty:
        raise ValueError("Generate warehouses before O2C inventory activity.")
    return sorted(warehouse_table["WarehouseID"].astype(int).tolist())


def payment_term_days(payment_terms: str) -> int:
    try:
        return int(str(payment_terms).split()[-1])
    except (ValueError, IndexError):
        return 30


def current_o2c_as_of_date(context: GenerationContext) -> pd.Timestamp:
    date_candidates: list[pd.Timestamp] = []
    date_columns = [
        ("SalesOrder", "OrderDate"),
        ("Shipment", "ShipmentDate"),
        ("SalesInvoice", "InvoiceDate"),
        ("CashReceipt", "ReceiptDate"),
        ("SalesReturn", "ReturnDate"),
        ("CustomerRefund", "RefundDate"),
    ]
    for table_name, column_name in date_columns:
        table = context.tables[table_name]
        if table.empty or column_name not in table.columns:
            continue
        dates = pd.to_datetime(table[column_name], errors="coerce").dropna()
        if not dates.empty:
            date_candidates.append(pd.Timestamp(dates.max()).normalize())
    if date_candidates:
        return max(date_candidates)
    return pd.Timestamp(context.settings.fiscal_year_end).normalize()


def aging_bucket_label(days_past_due: int) -> str:
    if days_past_due < 0:
        return "Not Due"
    if days_past_due <= 30:
        return "0-30"
    if days_past_due <= 60:
        return "31-60"
    if days_past_due <= 90:
        return "61-90"
    return "90+"


def receivables_open_invoices(
    context: GenerationContext,
    *,
    as_of_date: pd.Timestamp | str | None = None,
    customer_id: int | None = None,
    settled_amounts: dict[int, float] | None = None,
) -> pd.DataFrame:
    sales_invoices = context.tables["SalesInvoice"]
    if sales_invoices.empty:
        return pd.DataFrame(
            columns=[
                "SalesInvoiceID",
                "CustomerID",
                "InvoiceDate",
                "DueDate",
                "GrandTotal",
                "SettledAmount",
                "OpenAmount",
                "InvoiceDateTS",
                "DueDateTS",
                "DaysPastDue",
                "DaysOpen",
                "AgingBucket",
            ]
        )

    effective_as_of = pd.Timestamp(as_of_date).normalize() if as_of_date is not None else current_o2c_as_of_date(context)
    if settled_amounts is None:
        settled_amounts = (
            invoice_settled_amounts_as_of(context, effective_as_of)
            if as_of_date is not None
            else invoice_settled_amounts(context)
        )

    open_invoices = sales_invoices.copy()
    open_invoices["InvoiceDateTS"] = pd.to_datetime(open_invoices["InvoiceDate"], errors="coerce")
    open_invoices["DueDateTS"] = pd.to_datetime(open_invoices["DueDate"], errors="coerce")
    open_invoices = open_invoices[open_invoices["InvoiceDateTS"].notna() & open_invoices["DueDateTS"].notna()].copy()
    open_invoices = open_invoices[open_invoices["InvoiceDateTS"].le(effective_as_of)].copy()
    if customer_id is not None:
        open_invoices = open_invoices[open_invoices["CustomerID"].astype(int).eq(int(customer_id))].copy()
    if open_invoices.empty:
        return open_invoices

    open_invoices["SettledAmount"] = open_invoices["SalesInvoiceID"].astype(int).map(settled_amounts).fillna(0.0)
    open_invoices["OpenAmount"] = (
        open_invoices["GrandTotal"].astype(float) - open_invoices["SettledAmount"].astype(float)
    ).round(2)
    open_invoices = open_invoices[open_invoices["OpenAmount"].gt(0)].copy()
    if open_invoices.empty:
        return open_invoices

    open_invoices["DaysPastDue"] = (
        effective_as_of - open_invoices["DueDateTS"]
    ).dt.days.astype(int)
    open_invoices["DaysOpen"] = (
        effective_as_of - open_invoices["InvoiceDateTS"]
    ).dt.days.astype(int)
    open_invoices["AgingBucket"] = open_invoices["DaysPastDue"].map(aging_bucket_label)
    return open_invoices.sort_values(["DueDateTS", "InvoiceDateTS", "SalesInvoiceID"]).reset_index(drop=True)


def o2c_receivables_metrics(
    context: GenerationContext,
    *,
    as_of_date: pd.Timestamp | str | None = None,
) -> dict[str, float | int | str]:
    effective_as_of = pd.Timestamp(as_of_date).normalize() if as_of_date is not None else current_o2c_as_of_date(context)
    metrics_cache = getattr(context, "_o2c_receivables_metrics_cache", None)
    if metrics_cache is None:
        metrics_cache = {}
        setattr(context, "_o2c_receivables_metrics_cache", metrics_cache)
    cache_key = effective_as_of.strftime("%Y-%m-%d")
    if cache_key in metrics_cache:
        return metrics_cache[cache_key]

    open_invoices = receivables_open_invoices(context, as_of_date=effective_as_of)

    open_ar_amount = round(float(open_invoices["OpenAmount"].sum()), 2) if not open_invoices.empty else 0.0
    trailing_start = effective_as_of - pd.Timedelta(days=364)
    trailing_invoices = context.tables["SalesInvoice"]
    trailing_twelve_month_sales = 0.0
    if not trailing_invoices.empty:
        invoice_dates = pd.to_datetime(trailing_invoices["InvoiceDate"], errors="coerce")
        trailing_mask = invoice_dates.between(trailing_start, effective_as_of)
        trailing_twelve_month_sales = round(float(trailing_invoices.loc[trailing_mask, "GrandTotal"].astype(float).sum()), 2)

    implied_dso = round((open_ar_amount / trailing_twelve_month_sales) * 365.0, 2) if trailing_twelve_month_sales > 0 else 0.0

    metrics: dict[str, float | int | str] = {
        "as_of_date": effective_as_of.strftime("%Y-%m-%d"),
        "open_ar_amount": open_ar_amount,
        "trailing_twelve_month_sales": trailing_twelve_month_sales,
        "implied_dso": implied_dso,
        "open_invoice_count": int(len(open_invoices)),
        "open_invoices_gt_365_count": int(open_invoices["DaysOpen"].gt(365).sum()) if not open_invoices.empty else 0,
        "open_invoices_gt_365_amount": round(float(open_invoices.loc[open_invoices["DaysOpen"].gt(365), "OpenAmount"].sum()), 2) if not open_invoices.empty else 0.0,
    }

    aging_amounts: dict[str, float] = {}
    aging_counts: dict[str, int] = {}
    for bucket in AR_AGING_BUCKET_ORDER:
        bucket_rows = open_invoices[open_invoices["AgingBucket"].eq(bucket)] if not open_invoices.empty else open_invoices
        bucket_key = bucket.lower().replace("+", "plus").replace("-", "_").replace(" ", "_")
        aging_amount = round(float(bucket_rows["OpenAmount"].sum()), 2) if not bucket_rows.empty else 0.0
        aging_count = int(len(bucket_rows))
        metrics[f"aging_{bucket_key}_amount"] = aging_amount
        metrics[f"aging_{bucket_key}_share"] = round(float(aging_amount / open_ar_amount), 4) if open_ar_amount else 0.0
        metrics[f"aging_{bucket_key}_count"] = aging_count
        aging_amounts[bucket] = aging_amount
        aging_counts[bucket] = aging_count

    current_to_sixty_amount = aging_amounts["Not Due"] + aging_amounts["0-30"] + aging_amounts["31-60"]
    metrics["aging_current_to_60_amount"] = round(current_to_sixty_amount, 2)
    metrics["aging_current_to_60_share"] = round(float(current_to_sixty_amount / open_ar_amount), 4) if open_ar_amount else 0.0
    metrics["aging_90_plus_amount"] = aging_amounts["90+"]
    metrics["aging_90_plus_share"] = round(float(aging_amounts["90+"] / open_ar_amount), 4) if open_ar_amount else 0.0
    metrics["aging_90_plus_count"] = aging_counts["90+"]
    metrics_cache[cache_key] = metrics
    return metrics


def customer_collection_factor(customer_segment: str, payment_terms: str) -> float:
    segment_factor = float(SEGMENT_COLLECTION_FACTORS.get(str(customer_segment), 1.0))
    term_factor = float(TERM_COLLECTION_FACTORS.get(payment_term_days(str(payment_terms)), 0.90))
    return segment_factor * term_factor


def invoice_collection_target_ratio(
    days_past_due: int,
    *,
    customer_segment: str,
    payment_terms: str,
    rng: np.random.Generator,
) -> float:
    if days_past_due < 0:
        days_to_due = abs(int(days_past_due))
        if days_to_due <= 7:
            base_ratio = 0.26
        elif days_to_due <= 15:
            base_ratio = 0.16
        elif days_to_due <= 30:
            base_ratio = 0.08
        else:
            base_ratio = 0.02
    elif days_past_due <= 30:
        base_ratio = 0.72
    elif days_past_due <= 60:
        base_ratio = 0.86
    elif days_past_due <= 90:
        base_ratio = 0.94
    else:
        base_ratio = 0.98

    ratio = base_ratio * customer_collection_factor(customer_segment, payment_terms) * float(rng.uniform(0.94, 1.06))
    return float(np.clip(ratio, 0.0, 0.995))


def collection_receipt_dates(
    month_end: pd.Timestamp,
    *,
    receipt_count: int,
    max_days_past_due: int,
    rng: np.random.Generator,
) -> list[pd.Timestamp]:
    if receipt_count <= 0:
        return []

    if max_days_past_due > 90:
        anchor_days = [5, 14, 24]
    elif max_days_past_due > 60:
        anchor_days = [8, 18, 26]
    elif max_days_past_due > 30:
        anchor_days = [12, 21, 27]
    elif max_days_past_due >= 0:
        anchor_days = [18, 24, 28]
    else:
        anchor_days = [22, 26, month_end.day]

    month_start = month_end.replace(day=1)
    selected_anchors = anchor_days[:receipt_count]
    dates: list[pd.Timestamp] = []
    for anchor_day in selected_anchors:
        anchor = month_start + pd.Timedelta(days=max(0, min(anchor_day, month_end.day) - 1))
        offset = int(rng.integers(-2, 3))
        dates.append(min(month_end, max(month_start, anchor + pd.Timedelta(days=offset))))
    return sorted(dates)


def apply_receipt_oldest_first(
    context: GenerationContext,
    *,
    receipt_id: int,
    receipt_date: pd.Timestamp,
    customer_invoices: pd.DataFrame,
    receipt_amount: float,
    current_applied_amounts: dict[int, float],
    settled_amounts: dict[int, float],
    application_rows: list[dict[str, Any]],
    year: int,
    month: int,
) -> None:
    remaining_receipt_amount = money(receipt_amount)
    if remaining_receipt_amount <= 0 or customer_invoices.empty:
        return

    for invoice in customer_invoices.itertuples(index=False):
        if remaining_receipt_amount <= 0:
            break
        applied_amount = min(remaining_receipt_amount, float(invoice.OpenAmount))
        if applied_amount <= 0:
            continue
        application_date = clamp_date_to_month(
            max(receipt_date, pd.Timestamp(invoice.InvoiceDateTS)) + pd.Timedelta(days=int(context.rng.integers(0, 3))),
            year,
            month,
        )
        application_recorders = employee_ids_for_cost_center(context, "Customer Service", application_date)
        application_rows.append({
            "CashReceiptApplicationID": next_id(context, "CashReceiptApplication"),
            "CashReceiptID": int(receipt_id),
            "SalesInvoiceID": int(invoice.SalesInvoiceID),
            "ApplicationDate": application_date.strftime("%Y-%m-%d"),
            "AppliedAmount": money(applied_amount),
            "AppliedByEmployeeID": int(context.rng.choice(application_recorders)),
        })
        current_applied_amounts[int(receipt_id)] = round(
            float(current_applied_amounts.get(int(receipt_id), 0.0)) + float(applied_amount),
            2,
        )
        settled_amounts[int(invoice.SalesInvoiceID)] = round(
            float(settled_amounts.get(int(invoice.SalesInvoiceID), 0.0)) + float(applied_amount),
            2,
        )
        remaining_receipt_amount = money(remaining_receipt_amount - applied_amount)


def return_rng(context: GenerationContext, sales_invoice_id: int) -> np.random.Generator:
    return np.random.default_rng(context.settings.random_seed + int(sales_invoice_id) * 1009)


def returned_invoice_ids(context: GenerationContext) -> set[int]:
    credit_memos = context.tables["CreditMemo"]
    if credit_memos.empty:
        return set()
    cached = getattr(context, "_returned_invoice_ids_cache", None)
    if cached is not None:
        return cached
    cached = set(credit_memos["OriginalSalesInvoiceID"].astype(int).tolist())
    setattr(context, "_returned_invoice_ids_cache", cached)
    return cached


def invoice_return_plan(context: GenerationContext, sales_invoice_id: int, invoice: dict[str, Any]) -> dict[str, Any] | None:
    invoice_id = int(sales_invoice_id)
    rng = return_rng(context, invoice_id)
    if float(rng.random()) > TARGET_INVOICE_RETURN_RATE:
        return None

    invoice_date = pd.Timestamp(invoice["InvoiceDate"])
    lag_days = int(rng.integers(RETURN_LAG_DAYS_RANGE[0], RETURN_LAG_DAYS_RANGE[1] + 1))
    return_date = invoice_date + pd.Timedelta(days=lag_days)
    fiscal_end = pd.Timestamp(context.settings.fiscal_year_end)
    if return_date > fiscal_end:
        return None

    return {
        "rng": rng,
        "return_date": return_date,
    }


def select_return_line_count(rng: np.random.Generator, max_available_lines: int) -> int:
    if max_available_lines <= 1:
        return 1

    desired_counts = [count for count, _ in RETURN_LINE_COUNT_PROBABILITIES]
    probabilities = np.array([probability for _, probability in RETURN_LINE_COUNT_PROBABILITIES], dtype=float)
    probabilities = probabilities / probabilities.sum()
    selected_count = int(rng.choice(np.array(desired_counts), p=probabilities))
    return max(1, min(selected_count, max_available_lines))


def select_return_quantity(
    rng: np.random.Generator,
    eligible_quantity: float,
    reason_code: str,
) -> float:
    if eligible_quantity <= 0:
        return 0.0

    eligible_quantity = round(float(eligible_quantity), 2)
    full_return = reason_code in FULL_RETURN_REASON_CODES and float(rng.random()) < FULL_RETURN_REASON_PROBABILITY
    if full_return:
        return qty(eligible_quantity)

    partial_fraction = float(rng.uniform(PARTIAL_RETURN_FRACTION_RANGE[0], PARTIAL_RETURN_FRACTION_RANGE[1]))
    returned_quantity = qty(min(eligible_quantity, max(1.0, eligible_quantity * partial_fraction)))
    if eligible_quantity > 1.0 and returned_quantity >= eligible_quantity:
        returned_quantity = qty(max(1.0, eligible_quantity - 1.0))
    return min(qty(returned_quantity), qty(eligible_quantity))


def active_sellable_items(context: GenerationContext, event_date: pd.Timestamp | str | None = None) -> pd.DataFrame:
    items = context.tables["Item"]
    sellable = items[
        eligible_item_mask(items, event_date)
        & items["ListPrice"].notna()
        & items["RevenueAccountID"].notna()
    ].copy()
    if sellable.empty:
        raise ValueError("Generate active sellable items before O2C transactions.")
    return sellable


def active_goods_sellable_items(context: GenerationContext, event_date: pd.Timestamp | str | None = None) -> pd.DataFrame:
    sellable = active_sellable_items(context, event_date)
    goods = sellable[sellable["ItemGroup"].ne("Services")].copy()
    if goods.empty:
        raise ValueError("Generate active sellable goods before O2C transactions.")
    return goods


def active_design_service_items(context: GenerationContext, event_date: pd.Timestamp | str | None = None) -> pd.DataFrame:
    sellable = active_sellable_items(context, event_date)
    service_items = sellable[sellable["ItemGroup"].eq("Services")].copy()
    if service_items.empty:
        raise ValueError("Generate active sellable design-service items before service transactions.")
    return service_items.sort_values("ItemID").reset_index(drop=True)


def pricing_sellable_items(context: GenerationContext) -> pd.DataFrame:
    items = context.tables["Item"]
    sellable = items[
        items["IsActive"].astype(int).eq(1)
        & items["ListPrice"].notna()
        & items["RevenueAccountID"].notna()
        & items["ItemGroup"].ne("Services")
    ].copy()
    if sellable.empty:
        raise ValueError("Generate active sellable items before pricing masters.")
    return sellable.sort_values("ItemID").reset_index(drop=True)


def design_services_cost_center_id(context: GenerationContext) -> int:
    cost_centers = context.tables["CostCenter"]
    matches = cost_centers.loc[cost_centers["CostCenterName"].eq(DESIGN_SERVICE_COST_CENTER), "CostCenterID"]
    if matches.empty:
        raise ValueError("Design Services cost center is required for service generation.")
    return int(matches.iloc[0])


def active_design_service_customers(context: GenerationContext) -> pd.DataFrame:
    customers = context.tables["Customer"]
    active = customers[
        customers["IsActive"].astype(int).eq(1)
        & customers["CustomerSegment"].eq(DESIGN_SERVICE_SEGMENT)
    ].copy()
    if active.empty:
        raise ValueError("Generate active design-service customers before service transactions.")
    return active.sort_values("CustomerID").reset_index(drop=True)


def sales_pricing_approver_id(context: GenerationContext, event_date: pd.Timestamp | str) -> int:
    return approver_employee_id(
        context,
        event_date,
        preferred_titles=["Sales Manager", "Chief Financial Officer"],
        fallback_cost_center_name="Sales",
    )


def customer_specific_price_list_customer_ids(context: GenerationContext) -> set[int]:
    cached = getattr(context, "_customer_specific_price_list_customer_ids_cache", None)
    if cached is not None:
        return cached

    customers = context.tables["Customer"]
    strategic = customers[
        customers["IsActive"].astype(int).eq(1)
        & customers["CustomerSegment"].eq("Strategic")
    ].sort_values("CustomerID")
    if strategic.empty:
        cached = set()
    else:
        target_count = max(1, int(round(len(strategic) * CUSTOMER_PRICE_LIST_SHARE)))
        cached = set(strategic.head(target_count)["CustomerID"].astype(int).tolist())
    setattr(context, "_customer_specific_price_list_customer_ids_cache", cached)
    return cached


def generate_price_lists(context: GenerationContext) -> None:
    if not context.tables["PriceList"].empty or not context.tables["PriceListLine"].empty:
        return

    start_date = pd.Timestamp(context.settings.fiscal_year_start)
    end_date = pd.Timestamp(context.settings.fiscal_year_end)
    approved_by_employee_id = sales_pricing_approver_id(context, start_date)
    items = pricing_sellable_items(context)
    customers = context.tables["Customer"].sort_values("CustomerID").copy()

    header_rows: list[dict[str, Any]] = []
    line_rows: list[dict[str, Any]] = []

    for segment in ["Strategic", "Wholesale", "Design Trade", "Small Business"]:
        price_list_id = next_id(context, "PriceList")
        header_rows.append({
            "PriceListID": price_list_id,
            "PriceListName": f"{segment} Segment Price List",
            "ScopeType": "Segment",
            "CustomerID": None,
            "CustomerSegment": segment,
            "EffectiveStartDate": start_date.strftime("%Y-%m-%d"),
            "EffectiveEndDate": end_date.strftime("%Y-%m-%d"),
            "CurrencyCode": "USD",
            "Status": "Active",
            "ApprovedByEmployeeID": approved_by_employee_id,
            "ApprovedDate": start_date.strftime("%Y-%m-%d"),
        })

    customer_specific_ids = customer_specific_price_list_customer_ids(context)
    for customer in customers.itertuples(index=False):
        customer_id = int(customer.CustomerID)
        if customer_id not in customer_specific_ids:
            continue
        price_list_id = next_id(context, "PriceList")
        header_rows.append({
            "PriceListID": price_list_id,
            "PriceListName": f"Customer {customer_id:04d} Strategic Price List",
            "ScopeType": "Customer",
            "CustomerID": customer_id,
            "CustomerSegment": str(customer.CustomerSegment),
            "EffectiveStartDate": start_date.strftime("%Y-%m-%d"),
            "EffectiveEndDate": end_date.strftime("%Y-%m-%d"),
            "CurrencyCode": "USD",
            "Status": "Active",
            "ApprovedByEmployeeID": approved_by_employee_id,
            "ApprovedDate": start_date.strftime("%Y-%m-%d"),
        })

    append_rows(context, "PriceList", header_rows)

    for price_list in context.tables["PriceList"].itertuples(index=False):
        customer_discount_extra = 0.0
        base_segment = str(price_list.CustomerSegment) if pd.notna(price_list.CustomerSegment) else "Small Business"
        if str(price_list.ScopeType) == "Customer" and pd.notna(price_list.CustomerID):
            customer_discount_extra = 0.02 + ((int(price_list.CustomerID) % 3) * 0.01)
        base_discount = float(SEGMENT_PRICE_DISCOUNTS.get(base_segment, 0.03)) + customer_discount_extra
        floor_ratio = float(SEGMENT_MIN_PRICE_FLOORS.get(base_segment, 0.92))

        for item in items.itertuples(index=False):
            list_price = float(item.ListPrice)
            unit_price = money(max(list_price * floor_ratio, list_price * (1 - base_discount)))
            minimum_unit_price = money(list_price * floor_ratio)
            line_rows.append({
                "PriceListLineID": next_id(context, "PriceListLine"),
                "PriceListID": int(price_list.PriceListID),
                "ItemID": int(item.ItemID),
                "MinimumQuantity": 1,
                "UnitPrice": unit_price,
                "MinimumUnitPrice": minimum_unit_price,
                "Status": "Active",
            })

            if (
                str(price_list.ScopeType) == "Segment"
                and base_segment in {"Strategic", "Wholesale"}
                and str(item.ItemGroup) in PRICE_BREAK_ITEM_GROUPS
                and int(item.ItemID) % (5 if base_segment == "Strategic" else 7) == 0
            ):
                break_quantity = 5 if base_segment == "Strategic" else 10
                break_unit_price = money(max(minimum_unit_price, unit_price * 0.97))
                line_rows.append({
                    "PriceListLineID": next_id(context, "PriceListLine"),
                    "PriceListID": int(price_list.PriceListID),
                    "ItemID": int(item.ItemID),
                    "MinimumQuantity": break_quantity,
                    "UnitPrice": break_unit_price,
                    "MinimumUnitPrice": minimum_unit_price,
                    "Status": "Active",
                })

    append_rows(context, "PriceListLine", line_rows)


def generate_promotions(context: GenerationContext) -> None:
    if not context.tables["PromotionProgram"].empty:
        return

    items = pricing_sellable_items(context)
    finished_goods = items[items["ItemGroup"].isin(["Furniture", "Lighting", "Textiles", "Accessories"])].copy()
    if finished_goods.empty:
        return

    seasonal = finished_goods[finished_goods["LifecycleStatus"].eq("Seasonal")].copy()
    approved_by_employee_id = sales_pricing_approver_id(context, context.settings.fiscal_year_start)
    rows: list[dict[str, Any]] = []
    collections = sorted(collection for collection in seasonal["CollectionName"].dropna().astype(str).unique().tolist() if collection)
    item_groups = ["Textiles", "Accessories", "Lighting", "Furniture"]
    segments = ["Design Trade", "Wholesale", "Strategic", "Small Business"]

    fiscal_start_year = pd.Timestamp(context.settings.fiscal_year_start).year
    fiscal_end_year = pd.Timestamp(context.settings.fiscal_year_end).year
    promotion_sequence = 1
    for year in range(int(fiscal_start_year), int(fiscal_end_year) + 1):
        for window_index, ((start_month, end_month), discount_pct) in enumerate(PROMOTION_MONTH_WINDOWS):
            scope_type = ["Collection", "ItemGroup", "Segment"][window_index % 3]
            start_date = pd.Timestamp(year=year, month=start_month, day=1)
            end_date = pd.Timestamp(year=year, month=end_month, day=1) + pd.offsets.MonthEnd(1)
            row = {
                "PromotionID": next_id(context, "PromotionProgram"),
                "PromotionCode": f"PROMO-{year}-{promotion_sequence:03d}",
                "PromotionName": "",
                "ScopeType": scope_type,
                "CustomerSegment": None,
                "ItemGroup": None,
                "CollectionName": None,
                "DiscountPct": qty(discount_pct, "0.0001"),
                "EffectiveStartDate": start_date.strftime("%Y-%m-%d"),
                "EffectiveEndDate": end_date.strftime("%Y-%m-%d"),
                "Status": "Expired" if end_date < pd.Timestamp(context.settings.fiscal_year_end) else "Active",
                "ApprovedByEmployeeID": approved_by_employee_id,
                "ApprovedDate": start_date.strftime("%Y-%m-%d"),
            }
            if scope_type == "Collection" and collections:
                collection_name = collections[(promotion_sequence - 1) % len(collections)]
                row["CollectionName"] = collection_name
                row["PromotionName"] = f"{collection_name} Collection Promotion"
            elif scope_type == "ItemGroup":
                item_group = item_groups[(promotion_sequence - 1) % len(item_groups)]
                row["ItemGroup"] = item_group
                row["PromotionName"] = f"{item_group} Seasonal Promotion"
            else:
                customer_segment = segments[(promotion_sequence - 1) % len(segments)]
                row["CustomerSegment"] = customer_segment
                row["PromotionName"] = f"{customer_segment} Customer Promotion"
            rows.append(row)
            promotion_sequence += 1

    append_rows(context, "PromotionProgram", rows)


def generate_sales_commission_rates(context: GenerationContext) -> None:
    if not context.tables["SalesCommissionRate"].empty:
        return

    start_date = pd.Timestamp(context.settings.fiscal_year_start).normalize()
    end_date = pd.Timestamp(context.settings.fiscal_year_end).normalize()
    approved_by_employee_id = commission_accounting_approver_id(context, start_date)
    rows: list[dict[str, Any]] = []
    for (revenue_type, customer_segment), rate_pct in sorted(SALES_COMMISSION_RATES.items()):
        rows.append({
            "SalesCommissionRateID": next_id(context, "SalesCommissionRate"),
            "RevenueType": revenue_type,
            "CustomerSegment": customer_segment,
            "RatePct": qty(rate_pct, "0.0001"),
            "EffectiveStartDate": start_date.strftime("%Y-%m-%d"),
            "EffectiveEndDate": end_date.strftime("%Y-%m-%d"),
            "Status": "Active",
            "ApprovedByEmployeeID": approved_by_employee_id,
            "ApprovedDate": start_date.strftime("%Y-%m-%d"),
        })

    append_rows(context, "SalesCommissionRate", rows)


def sales_commission_rate_lookup(context: GenerationContext) -> dict[tuple[str, str], dict[str, Any]]:
    rates = context.tables["SalesCommissionRate"]
    if rates.empty:
        raise ValueError("Generate sales commission rates before commission accruals.")
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    active = rates[rates["Status"].astype(str).eq("Active")].copy()
    for row in active.itertuples(index=False):
        lookup[(str(row.RevenueType), str(row.CustomerSegment))] = {
            "SalesCommissionRateID": int(row.SalesCommissionRateID),
            "RatePct": float(row.RatePct),
            "EffectiveStartDate": pd.Timestamp(row.EffectiveStartDate).normalize(),
            "EffectiveEndDate": pd.Timestamp(row.EffectiveEndDate).normalize(),
        }
    return lookup


def commission_revenue_type_by_invoice_line(context: GenerationContext) -> dict[int, str]:
    mapping: dict[int, str] = {}
    service_billing_lines = context.tables["ServiceBillingLine"]
    if not service_billing_lines.empty:
        for sales_invoice_line_id in service_billing_lines["SalesInvoiceLineID"].dropna().astype(int).tolist():
            mapping[int(sales_invoice_line_id)] = "Design Service"
    return mapping


def selected_sales_commission_rate(
    context: GenerationContext,
    *,
    revenue_type: str,
    customer_segment: str,
    event_date: pd.Timestamp,
) -> dict[str, Any]:
    lookup = sales_commission_rate_lookup(context)
    key = (str(revenue_type), str(customer_segment))
    rate = lookup.get(key)
    if rate is None and str(customer_segment) == DESIGN_SERVICE_SEGMENT:
        rate = lookup.get((str(revenue_type), "Design Trade"))
    if rate is None:
        raise ValueError(f"Missing sales commission rate for {key}.")
    if not (rate["EffectiveStartDate"] <= event_date.normalize() <= rate["EffectiveEndDate"]):
        raise ValueError(f"Sales commission rate for {key} is not active on {event_date:%Y-%m-%d}.")
    return rate


def price_list_lookup(context: GenerationContext) -> dict[str, Any]:
    cached = getattr(context, "_price_list_lookup_cache", None)
    if cached is not None:
        return cached

    headers = context.tables["PriceList"]
    lines = context.tables["PriceListLine"]
    header_by_id: dict[int, dict[str, Any]] = {}
    customer_price_lists: dict[int, list[int]] = defaultdict(list)
    segment_price_lists: dict[str, list[int]] = defaultdict(list)

    for row in headers.itertuples(index=False):
        price_list_id = int(row.PriceListID)
        header_by_id[price_list_id] = {
            "PriceListID": price_list_id,
            "ScopeType": str(row.ScopeType),
            "CustomerID": None if pd.isna(row.CustomerID) else int(row.CustomerID),
            "CustomerSegment": None if pd.isna(row.CustomerSegment) else str(row.CustomerSegment),
            "EffectiveStartDate": pd.Timestamp(row.EffectiveStartDate),
            "EffectiveEndDate": pd.Timestamp(row.EffectiveEndDate),
            "Status": str(row.Status),
        }
        if str(row.ScopeType) == "Customer" and pd.notna(row.CustomerID):
            customer_price_lists[int(row.CustomerID)].append(price_list_id)
        elif str(row.ScopeType) == "Segment" and pd.notna(row.CustomerSegment):
            segment_price_lists[str(row.CustomerSegment)].append(price_list_id)

    lines_by_price_list_item: dict[tuple[int, int], tuple[dict[str, Any], ...]] = {}
    if not lines.empty:
        grouped = lines.groupby(["PriceListID", "ItemID"], dropna=False)
        for (price_list_id, item_id), rows in grouped:
            sorted_rows = rows.sort_values(["MinimumQuantity", "PriceListLineID"], ascending=[False, True])
            lines_by_price_list_item[(int(price_list_id), int(item_id))] = tuple(
                {
                    "PriceListLineID": int(line.PriceListLineID),
                    "PriceListID": int(line.PriceListID),
                    "ItemID": int(line.ItemID),
                    "MinimumQuantity": float(line.MinimumQuantity),
                    "UnitPrice": float(line.UnitPrice),
                    "MinimumUnitPrice": float(line.MinimumUnitPrice),
                    "Status": str(line.Status),
                }
                for line in sorted_rows.itertuples(index=False)
            )

    cached = {
        "header_by_id": header_by_id,
        "customer_price_lists": {key: tuple(value) for key, value in customer_price_lists.items()},
        "segment_price_lists": {key: tuple(value) for key, value in segment_price_lists.items()},
        "lines_by_price_list_item": lines_by_price_list_item,
    }
    setattr(context, "_price_list_lookup_cache", cached)
    return cached


def resolve_price_list_line(
    context: GenerationContext,
    customer_id: int,
    customer_segment: str,
    item_id: int,
    quantity: float,
    event_date: pd.Timestamp | str,
) -> dict[str, Any] | None:
    date_key = pd.Timestamp(event_date).normalize().strftime("%Y-%m-%d")
    cache = getattr(context, "_resolved_price_list_line_cache", None)
    if cache is None:
        cache = {}
        setattr(context, "_resolved_price_list_line_cache", cache)
    cache_key = (date_key, int(customer_id), str(customer_segment), int(item_id), round(float(quantity), 2))
    if cache_key in cache:
        return cache[cache_key]

    lookup = price_list_lookup(context)
    event_timestamp = pd.Timestamp(event_date)
    candidate_ids = list(lookup["customer_price_lists"].get(int(customer_id), ()))
    if not candidate_ids:
        candidate_ids = list(lookup["segment_price_lists"].get(str(customer_segment), ()))

    resolved: dict[str, Any] | None = None
    for price_list_id in candidate_ids:
        header = lookup["header_by_id"].get(int(price_list_id))
        if header is None:
            continue
        if event_timestamp < header["EffectiveStartDate"] or event_timestamp > header["EffectiveEndDate"]:
            continue
        lines = lookup["lines_by_price_list_item"].get((int(price_list_id), int(item_id)), ())
        for line in lines:
            if float(quantity) >= float(line["MinimumQuantity"]):
                resolved = {
                    **line,
                    "ScopeType": header["ScopeType"],
                    "CustomerID": header["CustomerID"],
                    "CustomerSegment": header["CustomerSegment"],
                    "PricingMethod": "Customer Price List" if header["ScopeType"] == "Customer" else "Segment Price List",
                }
                break
        if resolved is not None:
            break

    cache[cache_key] = resolved
    return resolved


def promotion_lookup(context: GenerationContext) -> tuple[dict[str, Any], ...]:
    cached = getattr(context, "_promotion_lookup_cache", None)
    if cached is not None:
        return cached

    promotions = context.tables["PromotionProgram"].sort_values(["EffectiveStartDate", "PromotionID"])
    cached = tuple(
        {
            "PromotionID": int(row.PromotionID),
            "ScopeType": str(row.ScopeType),
            "CustomerSegment": None if pd.isna(row.CustomerSegment) else str(row.CustomerSegment),
            "ItemGroup": None if pd.isna(row.ItemGroup) else str(row.ItemGroup),
            "CollectionName": None if pd.isna(row.CollectionName) else str(row.CollectionName),
            "DiscountPct": float(row.DiscountPct),
            "EffectiveStartDate": pd.Timestamp(row.EffectiveStartDate),
            "EffectiveEndDate": pd.Timestamp(row.EffectiveEndDate),
            "Status": str(row.Status),
        }
        for row in promotions.itertuples(index=False)
    )
    setattr(context, "_promotion_lookup_cache", cached)
    return cached


def resolve_promotion(
    context: GenerationContext,
    customer_segment: str,
    item_group: str,
    collection_name: str | None,
    event_date: pd.Timestamp | str,
) -> dict[str, Any] | None:
    date_key = pd.Timestamp(event_date).normalize().strftime("%Y-%m-%d")
    cache = getattr(context, "_resolved_promotion_cache", None)
    if cache is None:
        cache = {}
        setattr(context, "_resolved_promotion_cache", cache)
    cache_key = (date_key, str(customer_segment), str(item_group), str(collection_name or ""))
    if cache_key in cache:
        return cache[cache_key]

    event_timestamp = pd.Timestamp(event_date)
    resolved = None
    for promotion in promotion_lookup(context):
        if event_timestamp < promotion["EffectiveStartDate"] or event_timestamp > promotion["EffectiveEndDate"]:
            continue
        scope_type = str(promotion["ScopeType"])
        if scope_type == "Segment" and promotion["CustomerSegment"] == str(customer_segment):
            resolved = promotion
            break
        if scope_type == "ItemGroup" and promotion["ItemGroup"] == str(item_group):
            resolved = promotion
            break
        if scope_type == "Collection" and promotion["CollectionName"] == str(collection_name or ""):
            resolved = promotion
            break

    cache[cache_key] = resolved
    return resolved


def resolve_sales_line_pricing(
    context: GenerationContext,
    customer: pd.Series,
    item: pd.Series,
    quantity: float,
    order_date: pd.Timestamp,
    sales_order_line_id: int,
    sales_rep_id: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    price_list_line = resolve_price_list_line(
        context,
        int(customer["CustomerID"]),
        str(customer["CustomerSegment"]),
        int(item["ItemID"]),
        float(quantity),
        order_date,
    )
    base_list_price = money(float(item["ListPrice"]))
    unit_price = base_list_price
    minimum_unit_price = base_list_price
    price_list_line_id = None
    pricing_method = "Base List"
    if price_list_line is not None:
        unit_price = money(float(price_list_line["UnitPrice"]))
        minimum_unit_price = money(float(price_list_line["MinimumUnitPrice"]))
        price_list_line_id = int(price_list_line["PriceListLineID"])
        pricing_method = str(price_list_line["PricingMethod"])

    promotion = resolve_promotion(
        context,
        str(customer["CustomerSegment"]),
        str(item["ItemGroup"]),
        None if pd.isna(item["CollectionName"]) else str(item["CollectionName"]),
        order_date,
    )
    discount = qty(float(promotion["DiscountPct"]), "0.0001") if promotion is not None else 0.0
    promotion_id = int(promotion["PromotionID"]) if promotion is not None else None

    override_row = None
    override_id = None
    if (
        str(customer["CustomerSegment"]) in {"Strategic", "Wholesale"}
        and price_list_line_id is not None
        and (
            (str(customer["CustomerSegment"]) == "Strategic" and (int(sales_order_line_id) + int(item["ItemID"])) % 29 == 0)
            or (str(customer["CustomerSegment"]) == "Wholesale" and (int(sales_order_line_id) + int(customer["CustomerID"])) % 53 == 0)
        )
    ):
        requested_unit_price = money(minimum_unit_price * 0.95)
        approved_unit_price = money(minimum_unit_price * (0.96 if str(customer["CustomerSegment"]) == "Strategic" else 0.98))
        override_id = next_id(context, "PriceOverrideApproval")
        override_row = {
            "PriceOverrideApprovalID": override_id,
            "SalesOrderLineID": int(sales_order_line_id),
            "CustomerID": int(customer["CustomerID"]),
            "ItemID": int(item["ItemID"]),
            "RequestedByEmployeeID": int(sales_rep_id),
            "ApprovedByEmployeeID": sales_pricing_approver_id(context, order_date),
            "RequestDate": order_date.strftime("%Y-%m-%d"),
            "ApprovedDate": order_date.strftime("%Y-%m-%d"),
            "ReferenceUnitPrice": unit_price,
            "RequestedUnitPrice": requested_unit_price,
            "ApprovedUnitPrice": approved_unit_price,
            "ReasonCode": OVERRIDE_REASON_CODES[(int(sales_order_line_id) + int(item["ItemID"])) % len(OVERRIDE_REASON_CODES)],
            "Status": "Approved",
        }
        unit_price = approved_unit_price
        pricing_method = "Approved Override"

    pricing = {
        "BaseListPrice": base_list_price,
        "UnitPrice": unit_price,
        "Discount": discount,
        "PriceListLineID": price_list_line_id,
        "PromotionID": promotion_id,
        "PriceOverrideApprovalID": override_id,
        "PricingMethod": pricing_method,
        "LineTotal": money(float(quantity) * unit_price * (1 - float(discount))),
        "MinimumUnitPrice": minimum_unit_price,
    }
    return pricing, override_row


def sales_rep_employee_id(context: GenerationContext, customer: pd.Series, event_date: pd.Timestamp | str) -> int:
    employees = context.tables["Employee"].copy()
    valid_mask = employee_active_mask(employees, event_date)
    preferred_id = int(customer["SalesRepEmployeeID"])
    preferred_rows = employees[valid_mask & employees["EmployeeID"].astype(int).eq(preferred_id)]
    if not preferred_rows.empty:
        return preferred_id
    sales_rep_ids = employee_ids_for_cost_center(context, "Sales", event_date)
    if sales_rep_ids:
        return int(sales_rep_ids[0])
    return int(employees.sort_values("EmployeeID").iloc[0]["EmployeeID"])


def select_customer(
    context: GenerationContext,
    *,
    eligible_segments: tuple[str, ...] | list[str] | None = None,
) -> pd.Series:
    customers = context.tables["Customer"]
    active = customers[customers["IsActive"].eq(1)].copy()
    if eligible_segments is not None:
        active = active[active["CustomerSegment"].isin([str(segment) for segment in eligible_segments])].copy()
    if active.empty:
        raise ValueError("Generate active customers before O2C transactions.")

    weights = active["CustomerSegment"].map(SEGMENT_ORDER_WEIGHTS).astype(float)
    weights = weights / weights.sum()
    selected_index = context.rng.choice(active.index.to_numpy(), p=weights.to_numpy())
    return active.loc[selected_index]


def select_sales_item(context: GenerationContext, sellable_items: pd.DataFrame, customer_segment: str) -> pd.Series:
    group_preferences = {
        "Strategic": {"Furniture": 0.42, "Lighting": 0.18, "Textiles": 0.20, "Accessories": 0.20},
        "Wholesale": {"Furniture": 0.35, "Lighting": 0.20, "Textiles": 0.20, "Accessories": 0.25},
        "Design Trade": {"Furniture": 0.30, "Lighting": 0.24, "Textiles": 0.26, "Accessories": 0.20},
        "Small Business": {"Furniture": 0.25, "Lighting": 0.22, "Textiles": 0.22, "Accessories": 0.31},
    }
    preferences = group_preferences[customer_segment]
    weights = sellable_items["ItemGroup"].map(preferences).fillna(0.01).astype(float)
    weights = weights / weights.sum()
    selected_index = context.rng.choice(sellable_items.index.to_numpy(), p=weights.to_numpy())
    return sellable_items.loc[selected_index]


def select_design_service_item(context: GenerationContext, service_items: pd.DataFrame) -> pd.Series:
    weights = service_items["ListPrice"].astype(float)
    weights = weights / weights.sum()
    selected_index = context.rng.choice(service_items.index.to_numpy(), p=weights.to_numpy())
    return service_items.loc[selected_index]


def opening_inventory_map(context: GenerationContext) -> dict[tuple[int, int], float]:
    return planning_opening_inventory_map(context)


def shadow_inventory_state(context: GenerationContext) -> dict[tuple[int, int], float]:
    inventory = getattr(context, "_o2c_shadow_inventory", None)
    if inventory is None:
        inventory = opening_inventory_map(context)
        setattr(context, "_o2c_shadow_inventory", inventory)
    return inventory


def sales_order_line_shipped_quantities(context: GenerationContext) -> dict[int, float]:
    shipment_lines = context.tables["ShipmentLine"]
    if shipment_lines.empty:
        return {}
    cached = getattr(context, "_sales_order_line_shipped_quantities_cache", None)
    if cached is not None:
        return cached
    cached = {
        int(line_id): round(float(quantity), 2)
        for line_id, quantity in shipment_lines.groupby("SalesOrderLineID")["QuantityShipped"].sum().items()
    }
    setattr(context, "_sales_order_line_shipped_quantities_cache", cached)
    return cached


def shipment_line_billed_quantities(context: GenerationContext) -> dict[int, float]:
    invoice_lines = context.tables["SalesInvoiceLine"]
    if invoice_lines.empty:
        return {}
    cached = getattr(context, "_shipment_line_billed_quantities_cache", None)
    if cached is not None:
        return cached
    linked_lines = invoice_lines[invoice_lines["ShipmentLineID"].notna()]
    if linked_lines.empty:
        return {}
    cached = {
        int(line_id): round(float(quantity), 2)
        for line_id, quantity in linked_lines.groupby("ShipmentLineID")["Quantity"].sum().items()
    }
    setattr(context, "_shipment_line_billed_quantities_cache", cached)
    return cached


def shipment_line_returned_quantities(context: GenerationContext) -> dict[int, float]:
    return_lines = context.tables["SalesReturnLine"]
    if return_lines.empty:
        return {}
    cached = getattr(context, "_shipment_line_returned_quantities_cache", None)
    if cached is not None:
        return cached
    cached = {
        int(line_id): round(float(quantity), 2)
        for line_id, quantity in return_lines.groupby("ShipmentLineID")["QuantityReturned"].sum().items()
    }
    setattr(context, "_shipment_line_returned_quantities_cache", cached)
    return cached


def receipt_applied_amounts(context: GenerationContext) -> dict[int, float]:
    applications = context.tables["CashReceiptApplication"]
    if applications.empty:
        return {}
    cached = getattr(context, "_receipt_applied_amounts_cache", None)
    if cached is not None:
        return cached
    cached = {
        int(receipt_id): round(float(amount), 2)
        for receipt_id, amount in applications.groupby("CashReceiptID")["AppliedAmount"].sum().items()
    }
    setattr(context, "_receipt_applied_amounts_cache", cached)
    return cached


def invoice_cash_application_amounts(context: GenerationContext) -> dict[int, float]:
    applications = context.tables["CashReceiptApplication"]
    if applications.empty:
        return {}
    cached = getattr(context, "_invoice_cash_application_amounts_cache", None)
    if cached is not None:
        return cached
    cached = {
        int(invoice_id): round(float(amount), 2)
        for invoice_id, amount in applications.groupby("SalesInvoiceID")["AppliedAmount"].sum().items()
    }
    setattr(context, "_invoice_cash_application_amounts_cache", cached)
    return cached


def credit_memo_refunded_amounts(context: GenerationContext) -> dict[int, float]:
    refunds = context.tables["CustomerRefund"]
    if refunds.empty:
        return {}
    cached = getattr(context, "_credit_memo_refunded_amounts_cache", None)
    if cached is not None:
        return cached
    cached = {
        int(credit_memo_id): round(float(amount), 2)
        for credit_memo_id, amount in refunds.groupby("CreditMemoID")["Amount"].sum().items()
    }
    setattr(context, "_credit_memo_refunded_amounts_cache", cached)
    return cached


def credit_memo_allocation_map(context: GenerationContext) -> dict[int, dict[str, float]]:
    credit_memos = context.tables["CreditMemo"]
    if credit_memos.empty:
        return {}
    cached = getattr(context, "_credit_memo_allocation_map_cache", None)
    if cached is not None:
        return cached

    applications = context.tables["CashReceiptApplication"]
    invoice_totals = context.tables["SalesInvoice"].set_index("SalesInvoiceID")["GrandTotal"].astype(float).to_dict()
    applications_by_invoice: dict[int, float] = defaultdict(float)
    for application in applications.itertuples(index=False):
        applications_by_invoice[int(application.SalesInvoiceID)] += float(application.AppliedAmount)

    prior_credit_totals: dict[int, float] = defaultdict(float)
    allocations: dict[int, dict[str, float]] = {}
    for memo in credit_memos.sort_values(["CreditMemoDate", "CreditMemoID"]).itertuples(index=False):
        invoice_id = int(memo.OriginalSalesInvoiceID)
        applications_before = round(float(applications_by_invoice.get(invoice_id, 0.0)), 2)
        invoice_total = float(invoice_totals.get(invoice_id, 0.0))
        open_balance = max(0.0, round(invoice_total - applications_before - prior_credit_totals[invoice_id], 2))
        ar_amount = min(float(memo.GrandTotal), open_balance)
        allocations[int(memo.CreditMemoID)] = {
            "ar_amount": round(ar_amount, 2),
            "customer_credit_amount": round(float(memo.GrandTotal) - ar_amount, 2),
        }
        prior_credit_totals[invoice_id] = round(prior_credit_totals[invoice_id] + float(memo.GrandTotal), 2)
    setattr(context, "_credit_memo_allocation_map_cache", allocations)
    return allocations


def invoice_credit_memo_amounts(context: GenerationContext) -> dict[int, float]:
    credit_memos = context.tables["CreditMemo"]
    if credit_memos.empty:
        return {}
    allocations = credit_memo_allocation_map(context)
    invoice_amounts: dict[int, float] = defaultdict(float)
    for credit_memo in credit_memos.itertuples(index=False):
        invoice_amounts[int(credit_memo.OriginalSalesInvoiceID)] += float(
            allocations.get(int(credit_memo.CreditMemoID), {}).get("ar_amount", 0.0)
        )
    return {invoice_id: round(amount, 2) for invoice_id, amount in invoice_amounts.items()}


def invoice_settled_amounts(context: GenerationContext) -> dict[int, float]:
    cached = getattr(context, "_invoice_settled_amounts_cache", None)
    if cached is not None:
        return cached
    cash_applied = invoice_cash_application_amounts(context)
    credit_memo_amounts = invoice_credit_memo_amounts(context)
    invoice_ids = set(cash_applied) | set(credit_memo_amounts)
    cached = {
        int(invoice_id): round(float(cash_applied.get(invoice_id, 0.0)) + float(credit_memo_amounts.get(invoice_id, 0.0)), 2)
        for invoice_id in invoice_ids
    }
    setattr(context, "_invoice_settled_amounts_cache", cached)
    return cached


def credit_memo_allocation_map_as_of(
    context: GenerationContext,
    as_of_date: pd.Timestamp | str,
) -> dict[int, dict[str, float]]:
    as_of_key = pd.Timestamp(as_of_date).normalize().strftime("%Y-%m-%d")
    cached = getattr(context, "_credit_memo_allocation_map_as_of_cache", None)
    if cached is None:
        cached = {}
        setattr(context, "_credit_memo_allocation_map_as_of_cache", cached)
    if as_of_key in cached:
        return cached[as_of_key]

    credit_memos = context.tables["CreditMemo"]
    if credit_memos.empty:
        cached[as_of_key] = {}
        return cached[as_of_key]

    effective_as_of = pd.Timestamp(as_of_date).normalize()
    filtered_credit_memos = credit_memos.copy()
    filtered_credit_memos["CreditMemoDateTS"] = pd.to_datetime(filtered_credit_memos["CreditMemoDate"], errors="coerce")
    filtered_credit_memos = filtered_credit_memos[
        filtered_credit_memos["CreditMemoDateTS"].notna()
        & filtered_credit_memos["CreditMemoDateTS"].le(effective_as_of)
    ].copy()
    if filtered_credit_memos.empty:
        cached[as_of_key] = {}
        return cached[as_of_key]

    applications = context.tables["CashReceiptApplication"]
    application_lookup: dict[int, pd.DataFrame] = {}
    if not applications.empty:
        filtered_applications = applications.copy()
        filtered_applications["ApplicationDateTS"] = pd.to_datetime(filtered_applications["ApplicationDate"], errors="coerce")
        filtered_applications = filtered_applications[
            filtered_applications["ApplicationDateTS"].notna()
            & filtered_applications["ApplicationDateTS"].le(effective_as_of)
        ].copy()
        for invoice_id, rows in filtered_applications.groupby("SalesInvoiceID"):
            application_lookup[int(invoice_id)] = rows.sort_values(["ApplicationDateTS", "CashReceiptApplicationID"]).copy()

    invoice_totals = context.tables["SalesInvoice"].set_index("SalesInvoiceID")["GrandTotal"].astype(float).to_dict()
    prior_credit_totals: dict[int, float] = defaultdict(float)
    allocations: dict[int, dict[str, float]] = {}

    for memo in filtered_credit_memos.sort_values(["CreditMemoDateTS", "CreditMemoID"]).itertuples(index=False):
        invoice_id = int(memo.OriginalSalesInvoiceID)
        invoice_applications = application_lookup.get(invoice_id)
        applications_before = 0.0
        if invoice_applications is not None and not invoice_applications.empty:
            applications_before = round(
                float(
                    invoice_applications.loc[
                        invoice_applications["ApplicationDateTS"].le(pd.Timestamp(memo.CreditMemoDateTS)),
                        "AppliedAmount",
                    ].sum()
                ),
                2,
            )
        invoice_total = float(invoice_totals.get(invoice_id, 0.0))
        open_balance = max(0.0, round(invoice_total - applications_before - prior_credit_totals[invoice_id], 2))
        ar_amount = min(float(memo.GrandTotal), open_balance)
        allocations[int(memo.CreditMemoID)] = {
            "ar_amount": round(ar_amount, 2),
            "customer_credit_amount": round(float(memo.GrandTotal) - ar_amount, 2),
        }
        prior_credit_totals[invoice_id] = round(prior_credit_totals[invoice_id] + float(memo.GrandTotal), 2)

    cached[as_of_key] = allocations
    return allocations


def invoice_settled_amounts_as_of(
    context: GenerationContext,
    as_of_date: pd.Timestamp | str,
) -> dict[int, float]:
    as_of_key = pd.Timestamp(as_of_date).normalize().strftime("%Y-%m-%d")
    cached = getattr(context, "_invoice_settled_amounts_as_of_cache", None)
    if cached is None:
        cached = {}
        setattr(context, "_invoice_settled_amounts_as_of_cache", cached)
    if as_of_key in cached:
        return cached[as_of_key]

    effective_as_of = pd.Timestamp(as_of_date).normalize()
    applications = context.tables["CashReceiptApplication"]
    cash_applied: dict[int, float] = {}
    if not applications.empty:
        filtered_applications = applications.copy()
        filtered_applications["ApplicationDateTS"] = pd.to_datetime(filtered_applications["ApplicationDate"], errors="coerce")
        filtered_applications = filtered_applications[
            filtered_applications["ApplicationDateTS"].notna()
            & filtered_applications["ApplicationDateTS"].le(effective_as_of)
        ].copy()
        cash_applied = {
            int(invoice_id): round(float(amount), 2)
            for invoice_id, amount in filtered_applications.groupby("SalesInvoiceID")["AppliedAmount"].sum().items()
        }

    credit_memo_allocations = credit_memo_allocation_map_as_of(context, effective_as_of)
    credit_memo_amounts: dict[int, float] = defaultdict(float)
    for credit_memo in context.tables["CreditMemo"].itertuples(index=False):
        credit_memo_date = pd.Timestamp(credit_memo.CreditMemoDate)
        if credit_memo_date > effective_as_of:
            continue
        allocation = credit_memo_allocations.get(int(credit_memo.CreditMemoID), {})
        credit_memo_amounts[int(credit_memo.OriginalSalesInvoiceID)] += float(allocation.get("ar_amount", 0.0))

    invoice_ids = set(cash_applied) | set(credit_memo_amounts)
    settled = {
        int(invoice_id): round(
            float(cash_applied.get(invoice_id, 0.0)) + float(credit_memo_amounts.get(invoice_id, 0.0)),
            2,
        )
        for invoice_id in invoice_ids
    }
    cached[as_of_key] = settled
    return settled


def weighted_option_value(
    rng: np.random.Generator,
    options: tuple[tuple[int, float], ...],
) -> int:
    values = np.array([int(value) for value, _ in options])
    probabilities = np.array([float(probability) for _, probability in options], dtype=float)
    probabilities = probabilities / probabilities.sum()
    return int(rng.choice(values, p=probabilities))


def inclusive_month_count(start_date: pd.Timestamp | str, end_date: pd.Timestamp | str) -> int:
    start = pd.Timestamp(start_date).normalize().replace(day=1)
    end = pd.Timestamp(end_date).normalize().replace(day=1)
    return max(((int(end.year) - int(start.year)) * 12) + int(end.month) - int(start.month) + 1, 1)


def design_service_employee_pool(context: GenerationContext, event_date: pd.Timestamp | str) -> pd.DataFrame:
    employees = context.tables["Employee"].copy()
    if employees.empty:
        raise ValueError("Generate employees before design-service activity.")
    cost_center_id = design_services_cost_center_id(context)
    valid_mask = employee_active_mask(employees, event_date)
    pool = employees[
        valid_mask
        & employees["CostCenterID"].astype(int).eq(int(cost_center_id))
    ].copy()
    if pool.empty:
        raise ValueError("No active design-service employees are available for service generation.")
    return pool.sort_values(["JobTitle", "EmployeeID"]).reset_index(drop=True)


def design_service_approver_id(context: GenerationContext, event_date: pd.Timestamp | str) -> int:
    return approver_employee_id(
        context,
        event_date,
        preferred_titles=["Design Services Manager", "Chief Financial Officer"],
        fallback_cost_center_name=DESIGN_SERVICE_COST_CENTER,
    )


def service_assignment_billable_hours(context: GenerationContext) -> dict[int, float]:
    time_entries = context.tables["ServiceTimeEntry"]
    if time_entries.empty:
        return {}
    return {
        int(assignment_id): round(float(hours), 2)
        for assignment_id, hours in time_entries.groupby("ServiceEngagementAssignmentID")["BillableHours"].sum().items()
    }


def service_engagement_billable_hours(context: GenerationContext) -> dict[int, float]:
    time_entries = context.tables["ServiceTimeEntry"]
    if time_entries.empty:
        return {}
    return {
        int(engagement_id): round(float(hours), 2)
        for engagement_id, hours in time_entries.groupby("ServiceEngagementID")["BillableHours"].sum().items()
    }


def service_billed_hours_by_engagement(context: GenerationContext) -> dict[int, float]:
    billing_lines = context.tables["ServiceBillingLine"]
    if billing_lines.empty:
        return {}
    return {
        int(engagement_id): round(float(hours), 2)
        for engagement_id, hours in billing_lines.groupby("ServiceEngagementID")["BilledHours"].sum().items()
    }


def refresh_service_engagement_statuses(context: GenerationContext) -> None:
    engagements = context.tables["ServiceEngagement"]
    assignments = context.tables["ServiceEngagementAssignment"]
    if engagements.empty:
        return

    approved_hours = service_engagement_billable_hours(context)
    billed_hours = service_billed_hours_by_engagement(context)
    assignment_hours = service_assignment_billable_hours(context)

    engagement_status_map: dict[int, str] = {}
    for engagement in engagements.itertuples(index=False):
        planned_hours = round(float(engagement.PlannedHours), 2)
        approved = round(float(approved_hours.get(int(engagement.ServiceEngagementID), 0.0)), 2)
        billed = round(float(billed_hours.get(int(engagement.ServiceEngagementID), 0.0)), 2)
        if billed >= planned_hours and approved >= planned_hours:
            status = "Billed"
        elif approved >= planned_hours:
            status = "Completed"
        elif approved > 0:
            status = "In Progress"
        else:
            status = "Scheduled"
        engagement_status_map[int(engagement.ServiceEngagementID)] = status

    engagement_ids = engagements["ServiceEngagementID"].astype(int)
    context.tables["ServiceEngagement"]["Status"] = engagement_ids.map(engagement_status_map)

    if assignments.empty:
        return

    assignment_status_map: dict[int, str] = {}
    for assignment in assignments.itertuples(index=False):
        planned_hours = round(float(assignment.AssignedHours), 2)
        approved = round(float(assignment_hours.get(int(assignment.ServiceEngagementAssignmentID), 0.0)), 2)
        if approved >= planned_hours:
            status = "Completed"
        elif approved > 0:
            status = "In Progress"
        else:
            status = "Assigned"
        assignment_status_map[int(assignment.ServiceEngagementAssignmentID)] = status

    assignment_ids = assignments["ServiceEngagementAssignmentID"].astype(int)
    context.tables["ServiceEngagementAssignment"]["Status"] = assignment_ids.map(assignment_status_map)


def inventory_position_before_month(context: GenerationContext, year: int, month: int) -> dict[tuple[int, int], float]:
    start, _ = month_bounds(year, month)
    inventory = opening_inventory_map(context)

    goods_receipts = context.tables["GoodsReceipt"]
    if not goods_receipts.empty and not context.tables["GoodsReceiptLine"].empty:
        receipt_headers = goods_receipts.set_index("GoodsReceiptID")[["ReceiptDate", "WarehouseID"]].to_dict("index")
        for line in context.tables["GoodsReceiptLine"].itertuples(index=False):
            receipt = receipt_headers.get(int(line.GoodsReceiptID))
            if receipt is None or pd.Timestamp(receipt["ReceiptDate"]) >= start:
                continue
            key = (int(line.ItemID), int(receipt["WarehouseID"]))
            inventory[key] = round(float(inventory.get(key, 0.0)) + float(line.QuantityReceived), 2)

    shipments = context.tables["Shipment"]
    if not shipments.empty and not context.tables["ShipmentLine"].empty:
        shipment_headers = shipments.set_index("ShipmentID")[["ShipmentDate", "WarehouseID"]].to_dict("index")
        for line in context.tables["ShipmentLine"].itertuples(index=False):
            shipment = shipment_headers.get(int(line.ShipmentID))
            if shipment is None or pd.Timestamp(shipment["ShipmentDate"]) >= start:
                continue
            key = (int(line.ItemID), int(shipment["WarehouseID"]))
            inventory[key] = round(float(inventory.get(key, 0.0)) - float(line.QuantityShipped), 2)

    sales_returns = context.tables["SalesReturn"]
    if not sales_returns.empty and not context.tables["SalesReturnLine"].empty:
        return_headers = sales_returns.set_index("SalesReturnID")[["ReturnDate", "WarehouseID"]].to_dict("index")
        for line in context.tables["SalesReturnLine"].itertuples(index=False):
            sales_return = return_headers.get(int(line.SalesReturnID))
            if sales_return is None or pd.Timestamp(sales_return["ReturnDate"]) >= start:
                continue
            key = (int(line.ItemID), int(sales_return["WarehouseID"]))
            inventory[key] = round(float(inventory.get(key, 0.0)) + float(line.QuantityReturned), 2)

    completions = context.tables["ProductionCompletion"]
    if not completions.empty and not context.tables["ProductionCompletionLine"].empty:
        completion_headers = completions.set_index("ProductionCompletionID")[["CompletionDate", "WarehouseID"]].to_dict("index")
        for line in context.tables["ProductionCompletionLine"].itertuples(index=False):
            completion = completion_headers.get(int(line.ProductionCompletionID))
            if completion is None or pd.Timestamp(completion["CompletionDate"]) >= start:
                continue
            key = (int(line.ItemID), int(completion["WarehouseID"]))
            inventory[key] = round(float(inventory.get(key, 0.0)) + float(line.QuantityCompleted), 2)

    return inventory


def refresh_cash_receipt_links(context: GenerationContext) -> None:
    receipts = context.tables["CashReceipt"]
    applications = context.tables["CashReceiptApplication"]
    if receipts.empty:
        return

    applications_by_receipt: dict[int, list[Any]] = defaultdict(list)
    if not applications.empty:
        for application in applications.sort_values(["CashReceiptID", "ApplicationDate", "CashReceiptApplicationID"]).itertuples(index=False):
            applications_by_receipt[int(application.CashReceiptID)].append(application)

    linked_invoice_map: dict[int, int | None] = {}
    for receipt in receipts.itertuples(index=False):
        related = applications_by_receipt.get(int(receipt.CashReceiptID), [])
        linked_invoice_id = None
        if len(related) == 1:
            application = related[0]
            if round(float(application.AppliedAmount), 2) == round(float(receipt.Amount), 2) and str(application.ApplicationDate) == str(receipt.ReceiptDate):
                linked_invoice_id = int(application.SalesInvoiceID)
        linked_invoice_map[int(receipt.CashReceiptID)] = linked_invoice_id

    receipt_ids = context.tables["CashReceipt"]["CashReceiptID"].astype(int)
    context.tables["CashReceipt"]["SalesInvoiceID"] = receipt_ids.map(linked_invoice_map)


def refresh_o2c_statuses(context: GenerationContext) -> None:
    refresh_service_engagement_statuses(context)
    sales_orders = context.tables["SalesOrder"]
    sales_order_lines = context.tables["SalesOrderLine"]
    sales_invoices = context.tables["SalesInvoice"]
    sales_returns = context.tables["SalesReturn"]
    credit_memos = context.tables["CreditMemo"]

    shipped_by_sales_line = sales_order_line_shipped_quantities(context)
    settled_by_invoice = invoice_settled_amounts(context)
    refunded_by_credit_memo = credit_memo_refunded_amounts(context)
    item_groups = context.tables["Item"].set_index("ItemID")["ItemGroup"].astype(str).to_dict() if not context.tables["Item"].empty else {}
    billed_by_sales_line: dict[int, float] = defaultdict(float)
    if not context.tables["SalesInvoiceLine"].empty:
        for sales_order_line_id, billed_quantity in (
            context.tables["SalesInvoiceLine"].groupby("SalesOrderLineID")["Quantity"].sum().items()
        ):
            billed_by_sales_line[int(sales_order_line_id)] = round(float(billed_quantity), 2)

    if not sales_orders.empty and not sales_order_lines.empty:
        sales_order_line_item_ids = sales_order_lines.set_index("SalesOrderLineID")["ItemID"].astype(int).to_dict()
        line_metrics = sales_order_lines[["SalesOrderID", "SalesOrderLineID", "Quantity"]].copy()
        line_metrics["IsServiceLine"] = line_metrics["SalesOrderLineID"].astype(int).map(
            lambda sales_order_line_id: str(item_groups.get(int(sales_order_line_item_ids.get(int(sales_order_line_id), 0)), "")) == "Services"
        )
        line_metrics["ShippedQuantity"] = line_metrics["SalesOrderLineID"].astype(int).map(shipped_by_sales_line).fillna(0.0)
        line_metrics["BilledQuantity"] = line_metrics["SalesOrderLineID"].astype(int).map(billed_by_sales_line).fillna(0.0)
        order_summaries = (
            line_metrics.groupby("SalesOrderID")[["Quantity", "ShippedQuantity", "BilledQuantity", "IsServiceLine"]]
            .sum()
            .round(2)
            .to_dict("index")
        )
        invoice_summaries: dict[int, dict[str, float]] = {}
        if not sales_invoices.empty:
            invoice_metrics = sales_invoices[["SalesOrderID", "SalesInvoiceID", "GrandTotal"]].copy()
            invoice_metrics["SettledAmount"] = invoice_metrics["SalesInvoiceID"].astype(int).map(settled_by_invoice).fillna(0.0)
            invoice_summaries = (
                invoice_metrics.groupby("SalesOrderID")[["GrandTotal", "SettledAmount"]]
                .sum()
                .round(2)
                .to_dict("index")
            )

        as_of_date = pd.Timestamp(context.settings.fiscal_year_end).normalize()
        order_status_map: dict[int, str] = {}
        for order in sales_orders.itertuples(index=False):
            order_summary = order_summaries.get(int(order.SalesOrderID), {})
            invoice_summary = invoice_summaries.get(int(order.SalesOrderID), {})
            ordered_qty = round(float(order_summary.get("Quantity", 0.0)), 2)
            shipped_qty = round(float(order_summary.get("ShippedQuantity", 0.0)), 2)
            billed_qty = round(float(order_summary.get("BilledQuantity", 0.0)), 2)
            service_line_count = int(order_summary.get("IsServiceLine", 0.0) or 0)
            line_count = int(sales_order_lines[sales_order_lines["SalesOrderID"].astype(int).eq(int(order.SalesOrderID))].shape[0])
            is_service_order = line_count > 0 and service_line_count == line_count
            invoiced_amount = round(float(invoice_summary.get("GrandTotal", 0.0)), 2)
            settled_amount = round(float(invoice_summary.get("SettledAmount", 0.0)), 2)

            requested_date = pd.Timestamp(order.RequestedDeliveryDate)
            status = "Open"
            if ordered_qty > 0 and settled_amount >= invoiced_amount and billed_qty >= ordered_qty:
                status = "Closed"
            elif billed_qty >= ordered_qty:
                status = "Invoiced"
            elif billed_qty > 0:
                status = "Partially Invoiced"
            elif is_service_order:
                status = "Open"
            elif shipped_qty >= ordered_qty:
                status = "Shipped"
            elif shipped_qty > 0:
                status = "Backordered" if as_of_date >= requested_date else "Partially Shipped"
            elif as_of_date > requested_date:
                status = "Backordered"
            order_status_map[int(order.SalesOrderID)] = status

        sales_order_ids = context.tables["SalesOrder"]["SalesOrderID"].astype(int)
        context.tables["SalesOrder"]["Status"] = sales_order_ids.map(order_status_map).fillna(context.tables["SalesOrder"]["Status"])

    if not sales_invoices.empty:
        application_dates = (
            context.tables["CashReceiptApplication"]
            .sort_values(["ApplicationDate", "CashReceiptApplicationID"])
            .groupby("SalesInvoiceID")["ApplicationDate"]
            .max()
            .to_dict()
            if not context.tables["CashReceiptApplication"].empty
            else {}
        )
        credit_memos_by_invoice = invoice_credit_memo_amounts(context)
        cash_applied_by_invoice = invoice_cash_application_amounts(context)
        invoice_status_map: dict[int, str] = {}
        for invoice in sales_invoices.itertuples(index=False):
            settled_amount = round(float(cash_applied_by_invoice.get(int(invoice.SalesInvoiceID), 0.0)) + float(credit_memos_by_invoice.get(int(invoice.SalesInvoiceID), 0.0)), 2)
            status = "Submitted"
            if settled_amount >= round(float(invoice.GrandTotal), 2):
                status = "Settled"
            elif settled_amount > 0:
                status = "Partially Settled"
            invoice_status_map[int(invoice.SalesInvoiceID)] = status
        sales_invoice_ids = context.tables["SalesInvoice"]["SalesInvoiceID"].astype(int)
        context.tables["SalesInvoice"]["Status"] = sales_invoice_ids.map(invoice_status_map).fillna(context.tables["SalesInvoice"]["Status"])
        context.tables["SalesInvoice"]["PaymentDate"] = sales_invoice_ids.map(application_dates)

    if not sales_returns.empty:
        allocations = credit_memo_allocation_map(context)
        credit_memo_by_return = credit_memos.set_index("SalesReturnID")["CreditMemoID"].astype(int).to_dict() if not credit_memos.empty else {}
        sales_return_status_map: dict[int, str] = {}
        for sales_return in sales_returns.itertuples(index=False):
            status = "Received"
            credit_memo_id = credit_memo_by_return.get(int(sales_return.SalesReturnID))
            if credit_memo_id is not None:
                status = "Credited"
                if round(float(refunded_by_credit_memo.get(credit_memo_id, 0.0)), 2) >= round(float(allocations.get(credit_memo_id, {}).get("customer_credit_amount", 0.0)), 2) and round(float(allocations.get(credit_memo_id, {}).get("customer_credit_amount", 0.0)), 2) > 0:
                    status = "Refunded"
            sales_return_status_map[int(sales_return.SalesReturnID)] = status
        sales_return_ids = context.tables["SalesReturn"]["SalesReturnID"].astype(int)
        context.tables["SalesReturn"]["Status"] = sales_return_ids.map(sales_return_status_map).fillna(context.tables["SalesReturn"]["Status"])

    if not credit_memos.empty:
        allocations = credit_memo_allocation_map(context)
        credit_memo_status_map: dict[int, str] = {}
        for credit_memo in credit_memos.itertuples(index=False):
            allocation = allocations.get(int(credit_memo.CreditMemoID), {"customer_credit_amount": 0.0})
            status = "Applied"
            if round(float(allocation["customer_credit_amount"]), 2) > 0:
                status = "Issued"
                if round(float(refunded_by_credit_memo.get(int(credit_memo.CreditMemoID), 0.0)), 2) >= round(float(allocation["customer_credit_amount"]), 2):
                    status = "Refunded"
            credit_memo_status_map[int(credit_memo.CreditMemoID)] = status
        credit_memo_ids = context.tables["CreditMemo"]["CreditMemoID"].astype(int)
        context.tables["CreditMemo"]["Status"] = credit_memo_ids.map(credit_memo_status_map).fillna(context.tables["CreditMemo"]["Status"])


def o2c_open_state(
    context: GenerationContext,
    *,
    as_of_date: pd.Timestamp | str | None = None,
) -> dict[str, float | int | str]:
    shipped_by_sales_line = sales_order_line_shipped_quantities(context)
    item_groups = context.tables["Item"].set_index("ItemID")["ItemGroup"].astype(str).to_dict() if not context.tables["Item"].empty else {}
    open_order_quantity = 0.0
    backordered_quantity = 0.0
    for line in context.tables["SalesOrderLine"].itertuples(index=False):
        if str(item_groups.get(int(line.ItemID), "")) == "Services":
            continue
        shipped = float(shipped_by_sales_line.get(int(line.SalesOrderLineID), 0.0))
        remaining = max(0.0, round(float(line.Quantity) - shipped, 2))
        open_order_quantity += remaining
        if remaining > 0 and shipped > 0:
            backordered_quantity += remaining

    unbilled_shipment_quantity = 0.0
    billed_by_shipment = shipment_line_billed_quantities(context)
    for line in context.tables["ShipmentLine"].itertuples(index=False):
        unbilled_shipment_quantity += max(0.0, round(float(line.QuantityShipped) - float(billed_by_shipment.get(int(line.ShipmentLineID), 0.0)), 2))

    receivables_metrics = o2c_receivables_metrics(context, as_of_date=as_of_date)
    open_ar_amount = float(receivables_metrics["open_ar_amount"])

    applied_by_receipt = receipt_applied_amounts(context)
    unapplied_cash_amount = 0.0
    for receipt in context.tables["CashReceipt"].itertuples(index=False):
        unapplied_cash_amount += max(0.0, round(float(receipt.Amount) - float(applied_by_receipt.get(int(receipt.CashReceiptID), 0.0)), 2))

    allocations = credit_memo_allocation_map(context)
    refunded = credit_memo_refunded_amounts(context)
    customer_credit_amount = 0.0
    for credit_memo_id, allocation in allocations.items():
        customer_credit_amount += max(0.0, round(float(allocation["customer_credit_amount"]) - float(refunded.get(int(credit_memo_id), 0.0)), 2))

    distinct_returned_invoices = len(returned_invoice_ids(context))
    invoice_count = len(context.tables["SalesInvoice"])
    shipped_quantity = round(float(context.tables["ShipmentLine"]["QuantityShipped"].sum()), 2) if not context.tables["ShipmentLine"].empty else 0.0
    returned_quantity = round(float(context.tables["SalesReturnLine"]["QuantityReturned"].sum()), 2) if not context.tables["SalesReturnLine"].empty else 0.0
    sales_subtotal = round(float(context.tables["SalesInvoice"]["SubTotal"].sum()), 2) if not context.tables["SalesInvoice"].empty else 0.0
    credit_subtotal = round(float(context.tables["CreditMemo"]["SubTotal"].sum()), 2) if not context.tables["CreditMemo"].empty else 0.0

    return {
        "open_order_quantity": round(open_order_quantity, 2),
        "backordered_quantity": round(backordered_quantity, 2),
        "unbilled_shipment_quantity": round(unbilled_shipment_quantity, 2),
        "open_ar_amount": round(open_ar_amount, 2),
        "unapplied_cash_amount": round(unapplied_cash_amount, 2),
        "customer_credit_amount": round(customer_credit_amount, 2),
        "distinct_returned_invoices": int(distinct_returned_invoices),
        "invoice_return_incidence_ratio": round(float(distinct_returned_invoices / invoice_count), 4) if invoice_count else 0.0,
        "return_quantity_ratio": round(float(returned_quantity / shipped_quantity), 4) if shipped_quantity else 0.0,
        "credit_memo_subtotal_ratio": round(float(credit_subtotal / sales_subtotal), 4) if sales_subtotal else 0.0,
        "trailing_twelve_month_sales": float(receivables_metrics["trailing_twelve_month_sales"]),
        "implied_dso": float(receivables_metrics["implied_dso"]),
        "aging_not_due_amount": float(receivables_metrics["aging_not_due_amount"]),
        "aging_0_30_amount": float(receivables_metrics["aging_0_30_amount"]),
        "aging_31_60_amount": float(receivables_metrics["aging_31_60_amount"]),
        "aging_61_90_amount": float(receivables_metrics["aging_61_90_amount"]),
        "aging_90_plus_amount": float(receivables_metrics["aging_90_plus_amount"]),
        "aging_90_plus_share": float(receivables_metrics["aging_90_plus_share"]),
        "aging_current_to_60_share": float(receivables_metrics["aging_current_to_60_share"]),
        "open_invoices_gt_365_count": int(receivables_metrics["open_invoices_gt_365_count"]),
        "open_invoices_gt_365_amount": float(receivables_metrics["open_invoices_gt_365_amount"]),
    }


def generate_month_sales_orders(context: GenerationContext, year: int, month: int) -> None:
    sales_center_id = sales_cost_center_id(context)
    rng = context.rng
    forecast_targets = monthly_forecast_targets(context, year, month)
    planned_actual_targets = {
        int(item_id): max(0.0, qty(float(target_quantity) * rng.uniform(0.88, 1.12)))
        for item_id, target_quantity in forecast_targets.items()
    }
    total_target_quantity = float(sum(planned_actual_targets.values()))
    order_count = int(rng.integers(95, 126))
    if total_target_quantity > 0:
        order_count = int(np.clip(round(total_target_quantity / 6.8), 90, 155))
    elif month in [3, 4, 9, 10, 11]:
        order_count = int(order_count * 1.10)

    order_rows: list[dict] = []
    line_rows: list[dict] = []
    override_rows: list[dict] = []
    for _ in range(order_count):
        customer = select_customer(
            context,
            eligible_segments=("Strategic", "Wholesale", "Design Trade", "Small Business"),
        )
        order_id = next_id(context, "SalesOrder")
        order_date = random_date_in_month(rng, year, month)
        sellable_items = active_goods_sellable_items(context, order_date)
        requested_delivery_date = order_date + pd.Timedelta(days=int(rng.integers(3, 15)))
        segment = str(customer["CustomerSegment"])
        sales_rep_id = sales_rep_employee_id(context, customer, order_date)
        line_min, line_max = SEGMENT_LINE_RANGES[segment]
        line_count = int(rng.integers(line_min, line_max + 1))

        order_total = 0.0
        used_item_ids: set[int] = set()
        for line_number in range(1, line_count + 1):
            item = select_sales_item(context, sellable_items, segment)
            if planned_actual_targets:
                target_items = sellable_items[
                    sellable_items["ItemID"].astype(int).map(lambda item_id: planned_actual_targets.get(int(item_id), 0.0)).gt(0)
                ].copy()
                if not target_items.empty:
                    target_weights = target_items["ItemID"].astype(int).map(
                        lambda item_id: max(float(planned_actual_targets.get(int(item_id), 0.0)), 0.01)
                    ).astype(float)
                    target_weights = target_weights / target_weights.sum()
                    selected_index = rng.choice(target_items.index.to_numpy(), p=target_weights.to_numpy())
                    item = target_items.loc[selected_index]
            retry_count = 0
            while int(item["ItemID"]) in used_item_ids and retry_count < 5:
                if planned_actual_targets:
                    target_items = sellable_items[
                        sellable_items["ItemID"].astype(int).map(lambda item_id: planned_actual_targets.get(int(item_id), 0.0)).gt(0)
                    ].copy()
                    if not target_items.empty:
                        target_weights = target_items["ItemID"].astype(int).map(
                            lambda item_id: max(float(planned_actual_targets.get(int(item_id), 0.0)), 0.01)
                        ).astype(float)
                        target_weights = target_weights / target_weights.sum()
                        selected_index = rng.choice(target_items.index.to_numpy(), p=target_weights.to_numpy())
                        item = target_items.loc[selected_index]
                    else:
                        item = select_sales_item(context, sellable_items, segment)
                else:
                    item = select_sales_item(context, sellable_items, segment)
                retry_count += 1
            used_item_ids.add(int(item["ItemID"]))

            qty_min, qty_max = SEGMENT_QUANTITY_RANGES[segment]
            quantity = qty(int(rng.integers(qty_min, qty_max + 1)))
            planned_remaining = float(planned_actual_targets.get(int(item["ItemID"]), 0.0))
            if planned_remaining > 0:
                lower_bound = min(quantity, max(1.0, planned_remaining * 0.12))
                upper_bound = min(max(float(qty_max), lower_bound), max(float(qty_min), planned_remaining * 0.45))
                if upper_bound >= lower_bound:
                    quantity = qty(rng.uniform(lower_bound, upper_bound))
            sales_order_line_id = next_id(context, "SalesOrderLine")
            pricing, override_row = resolve_sales_line_pricing(
                context,
                customer,
                item,
                quantity,
                order_date,
                sales_order_line_id,
                sales_rep_id,
            )
            line_total = money(float(pricing["LineTotal"]))
            order_total = money(order_total + line_total)
            if int(item["ItemID"]) in planned_actual_targets:
                planned_actual_targets[int(item["ItemID"])] = max(
                    0.0,
                    qty(float(planned_actual_targets[int(item["ItemID"])]) - quantity),
                )

            line_rows.append({
                "SalesOrderLineID": sales_order_line_id,
                "SalesOrderID": order_id,
                "LineNumber": line_number,
                "ItemID": int(item["ItemID"]),
                "Quantity": quantity,
                "BaseListPrice": float(pricing["BaseListPrice"]),
                "UnitPrice": float(pricing["UnitPrice"]),
                "Discount": float(pricing["Discount"]),
                "LineTotal": line_total,
                "PriceListLineID": pricing["PriceListLineID"],
                "PromotionID": pricing["PromotionID"],
                "PriceOverrideApprovalID": pricing["PriceOverrideApprovalID"],
                "PricingMethod": pricing["PricingMethod"],
            })
            if override_row is not None:
                override_rows.append(override_row)

        freight_terms = freight_terms_for_order(
            context,
            sales_order_id=order_id,
            customer_segment=segment,
            order_total=order_total,
        )
        order_rows.append({
            "SalesOrderID": order_id,
            "OrderNumber": format_doc_number("SO", year, order_id),
            "OrderDate": order_date.strftime("%Y-%m-%d"),
            "CustomerID": int(customer["CustomerID"]),
            "RequestedDeliveryDate": requested_delivery_date.strftime("%Y-%m-%d"),
            "Status": "Open",
            "SalesRepEmployeeID": sales_rep_id,
            "CostCenterID": sales_center_id,
            "OrderTotal": order_total,
            "FreightTerms": freight_terms,
            "Notes": None,
        })

    append_rows(context, "SalesOrder", order_rows)
    append_rows(context, "SalesOrderLine", line_rows)
    append_rows(context, "PriceOverrideApproval", override_rows)


def generate_month_design_service_orders(context: GenerationContext, year: int, month: int) -> None:
    customers = active_design_service_customers(context)
    service_items = active_design_service_items(context, pd.Timestamp(year=year, month=month, day=1))
    rng = context.rng
    month_start, month_end = month_bounds(year, month)
    fiscal_end = pd.Timestamp(context.settings.fiscal_year_end).normalize()
    design_cost_center_id = design_services_cost_center_id(context)

    desired_count = int(
        np.clip(
            round(len(customers) * rng.uniform(0.24, 0.42)),
            DESIGN_SERVICE_MONTHLY_ENGAGEMENT_RANGE[0],
            DESIGN_SERVICE_MONTHLY_ENGAGEMENT_RANGE[1],
        )
    )
    engagement_count = min(max(desired_count, 1), len(customers))
    if engagement_count <= 0:
        return

    selected_customer_indexes = np.atleast_1d(
        rng.choice(customers.index.to_numpy(), size=engagement_count, replace=False)
    )

    order_rows: list[dict[str, Any]] = []
    line_rows: list[dict[str, Any]] = []
    engagement_rows: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []

    for customer_index in selected_customer_indexes.tolist():
        customer = customers.loc[int(customer_index)]
        service_item = select_design_service_item(context, service_items)
        start_date = random_date_in_month(rng, year, month).normalize()
        duration_months = weighted_option_value(rng, DESIGN_SERVICE_MONTH_SPAN_OPTIONS)
        projected_end = (
            pd.Timestamp(start_date).replace(day=1)
            + pd.DateOffset(months=duration_months - 1)
            + pd.offsets.MonthEnd(1)
        ).normalize()
        end_date = min(projected_end, fiscal_end)
        if end_date < start_date:
            end_date = start_date

        if duration_months == 1:
            planned_hours = qty(rng.uniform(24.0, 72.0))
        elif duration_months == 2:
            planned_hours = qty(rng.uniform(60.0, 120.0))
        else:
            planned_hours = qty(rng.uniform(96.0, DESIGN_SERVICE_PLANNED_HOURS_RANGE[1]))

        hourly_rate = money(float(service_item["ListPrice"]))
        sales_order_id = next_id(context, "SalesOrder")
        sales_order_line_id = next_id(context, "SalesOrderLine")
        service_engagement_id = next_id(context, "ServiceEngagement")
        order_date = max(month_start, start_date - pd.Timedelta(days=int(rng.integers(0, 8))))
        sales_rep_id = sales_rep_employee_id(context, customer, order_date)
        order_total = money(planned_hours * hourly_rate)

        design_team = design_service_employee_pool(context, start_date)
        lead_pool = design_team[
            design_team["JobTitle"].isin(["Senior Designer", "Design Services Manager", "Designer"])
        ].copy()
        lead_weights = lead_pool["JobTitle"].map({
            "Senior Designer": 0.50,
            "Design Services Manager": 0.32,
            "Designer": 0.18,
        }).astype(float)
        lead_weights = lead_weights / lead_weights.sum()
        lead_index = int(rng.choice(lead_pool.index.to_numpy(), p=lead_weights.to_numpy()))
        lead_employee = lead_pool.loc[lead_index]

        assignment_target = min(
            weighted_option_value(rng, DESIGN_SERVICE_ASSIGNMENT_OPTIONS),
            len(design_team),
        )
        remaining_team = design_team[design_team["EmployeeID"].astype(int).ne(int(lead_employee["EmployeeID"]))].copy()
        selected_team = [lead_employee]
        if assignment_target > 1 and not remaining_team.empty:
            sample_count = min(assignment_target - 1, len(remaining_team))
            sample_weights = remaining_team["JobTitle"].map({
                "Senior Designer": 0.36,
                "Design Services Manager": 0.12,
                "Designer": 0.52,
            }).fillna(0.20).astype(float)
            sample_weights = sample_weights / sample_weights.sum()
            sampled_indexes = np.atleast_1d(
                rng.choice(
                    remaining_team.index.to_numpy(),
                    size=sample_count,
                    replace=False,
                    p=sample_weights.to_numpy(),
                )
            )
            for sampled_index in sampled_indexes.tolist():
                selected_team.append(remaining_team.loc[int(sampled_index)])

        alpha = np.array([
            1.85 if int(member["EmployeeID"]) == int(lead_employee["EmployeeID"]) else (
                1.45 if str(member["JobTitle"]) == "Senior Designer" else 1.10
            )
            for member in selected_team
        ], dtype=float)
        allocation_weights = rng.dirichlet(alpha)
        assigned_hours = [qty(planned_hours * float(weight)) for weight in allocation_weights]
        assigned_hours[-1] = qty(assigned_hours[-1] + money(planned_hours - sum(assigned_hours)))

        order_rows.append({
            "SalesOrderID": sales_order_id,
            "OrderNumber": format_doc_number("SO", year, sales_order_id),
            "OrderDate": order_date.strftime("%Y-%m-%d"),
            "CustomerID": int(customer["CustomerID"]),
            "RequestedDeliveryDate": start_date.strftime("%Y-%m-%d"),
            "Status": "Open",
            "SalesRepEmployeeID": sales_rep_id,
            "CostCenterID": design_cost_center_id,
            "OrderTotal": order_total,
            "FreightTerms": "Prepaid",
            "Notes": f"{service_item['ItemName']} engagement",
        })
        line_rows.append({
            "SalesOrderLineID": sales_order_line_id,
            "SalesOrderID": sales_order_id,
            "LineNumber": 1,
            "ItemID": int(service_item["ItemID"]),
            "Quantity": planned_hours,
            "BaseListPrice": hourly_rate,
            "UnitPrice": hourly_rate,
            "Discount": 0.0,
            "LineTotal": order_total,
            "PriceListLineID": None,
            "PromotionID": None,
            "PriceOverrideApprovalID": None,
            "PricingMethod": "Base List",
        })
        engagement_rows.append({
            "ServiceEngagementID": service_engagement_id,
            "EngagementNumber": format_doc_number("SE", year, service_engagement_id),
            "CustomerID": int(customer["CustomerID"]),
            "SalesOrderID": sales_order_id,
            "SalesOrderLineID": sales_order_line_id,
            "ItemID": int(service_item["ItemID"]),
            "LeadEmployeeID": int(lead_employee["EmployeeID"]),
            "StartDate": start_date.strftime("%Y-%m-%d"),
            "EndDate": end_date.strftime("%Y-%m-%d"),
            "PlannedHours": planned_hours,
            "HourlyRate": hourly_rate,
            "Status": "Scheduled",
        })

        for team_member, member_hours in zip(selected_team, assigned_hours):
            assignment_rows.append({
                "ServiceEngagementAssignmentID": next_id(context, "ServiceEngagementAssignment"),
                "ServiceEngagementID": service_engagement_id,
                "EmployeeID": int(team_member["EmployeeID"]),
                "AssignedRole": str(team_member["JobTitle"]),
                "AssignedHours": member_hours,
                "Status": "Assigned",
            })

    append_rows(context, "SalesOrder", order_rows)
    append_rows(context, "SalesOrderLine", line_rows)
    append_rows(context, "ServiceEngagement", engagement_rows)
    append_rows(context, "ServiceEngagementAssignment", assignment_rows)


def generate_month_service_time_entries(context: GenerationContext, year: int, month: int) -> None:
    engagements = context.tables["ServiceEngagement"]
    assignments = context.tables["ServiceEngagementAssignment"]
    if engagements.empty or assignments.empty:
        return

    rng = context.rng
    month_start, month_end = month_bounds(year, month)
    employee_lookup = context.tables["Employee"].set_index("EmployeeID").to_dict("index") if not context.tables["Employee"].empty else {}
    assignment_groups = {int(key): value.copy() for key, value in assignments.groupby("ServiceEngagementID")}
    billable_by_assignment = service_assignment_billable_hours(context)
    time_entry_rows: list[dict[str, Any]] = []

    for engagement in engagements.itertuples(index=False):
        engagement_start = pd.Timestamp(engagement.StartDate)
        engagement_end = pd.Timestamp(engagement.EndDate)
        if engagement_end < month_start or engagement_start > month_end:
            continue

        active_start = max(engagement_start, month_start)
        active_end = min(engagement_end, month_end)
        if active_end < active_start:
            continue

        assignment_rows = assignment_groups.get(int(engagement.ServiceEngagementID))
        if assignment_rows is None or assignment_rows.empty:
            continue

        remaining_months = inclusive_month_count(month_start, engagement_end)
        for assignment in assignment_rows.itertuples(index=False):
            assigned_hours = round(float(assignment.AssignedHours), 2)
            consumed_hours = round(float(billable_by_assignment.get(int(assignment.ServiceEngagementAssignmentID), 0.0)), 2)
            remaining_hours = round(assigned_hours - consumed_hours, 2)
            if remaining_hours <= 0:
                continue

            planned_month_hours = remaining_hours
            if remaining_months > 1:
                target_share = remaining_hours / float(remaining_months)
                planned_month_hours = qty(
                    min(
                        remaining_hours,
                        max(2.0, target_share * rng.uniform(0.88, 1.14)),
                    )
                )
            planned_month_hours = min(qty(planned_month_hours), qty(remaining_hours))
            if planned_month_hours <= 0:
                continue

            employee = employee_lookup.get(int(assignment.EmployeeID))
            if employee is None:
                continue
            employee_hire_date = pd.Timestamp(employee["HireDate"])
            employee_termination_date = (
                pd.Timestamp(employee["TerminationDate"])
                if pd.notna(employee.get("TerminationDate"))
                else None
            )
            employee_active_start = max(active_start, employee_hire_date)
            employee_active_end = active_end
            if employee_termination_date is not None:
                employee_active_end = min(employee_active_end, employee_termination_date)
            if employee_active_end < employee_active_start:
                continue

            workdays = pd.date_range(start=employee_active_start, end=employee_active_end, freq="B")
            if len(workdays) == 0:
                workdays = pd.date_range(start=employee_active_start, end=employee_active_end, freq="D")
            if len(workdays) == 0:
                continue

            desired_workdays = min(
                len(workdays),
                int(
                    np.clip(
                        round(planned_month_hours / 7.5),
                        DESIGN_SERVICE_WORKDAYS_PER_MONTH_RANGE[0],
                        DESIGN_SERVICE_WORKDAYS_PER_MONTH_RANGE[1],
                    )
                ),
            )
            selected_workdays = sorted(
                pd.Timestamp(value).normalize()
                for value in np.atleast_1d(
                    rng.choice(workdays.to_numpy(), size=max(desired_workdays, 1), replace=False)
                ).tolist()
            )
            billable_weights = rng.dirichlet(np.ones(len(selected_workdays)))
            billable_parts = [qty(planned_month_hours * float(weight)) for weight in billable_weights]
            billable_parts[-1] = qty(billable_parts[-1] + money(planned_month_hours - sum(billable_parts)))

            nonbillable_total = qty(min(4.0, planned_month_hours * rng.uniform(*DESIGN_SERVICE_NONBILLABLE_SHARE_RANGE)))
            if nonbillable_total > 0:
                nonbillable_weights = rng.dirichlet(np.ones(len(selected_workdays)))
                nonbillable_parts = [qty(nonbillable_total * float(weight)) for weight in nonbillable_weights]
                nonbillable_parts[-1] = qty(nonbillable_parts[-1] + money(nonbillable_total - sum(nonbillable_parts)))
            else:
                nonbillable_parts = [0.0 for _ in selected_workdays]

            cost_rate_used = implied_hourly_rate(employee, int(pd.Timestamp(employee_active_start).year))

            for work_date, billable_hours, nonbillable_hours in zip(selected_workdays, billable_parts, nonbillable_parts):
                approval_date = clamp_date_to_month(
                    pd.Timestamp(work_date) + pd.Timedelta(days=int(rng.integers(0, 4))),
                    year,
                    month,
                )
                total_cost_hours = float(billable_hours) + float(nonbillable_hours)
                time_entry_rows.append({
                    "ServiceTimeEntryID": next_id(context, "ServiceTimeEntry"),
                    "ServiceEngagementID": int(engagement.ServiceEngagementID),
                    "ServiceEngagementAssignmentID": int(assignment.ServiceEngagementAssignmentID),
                    "EmployeeID": int(assignment.EmployeeID),
                    "WorkDate": pd.Timestamp(work_date).strftime("%Y-%m-%d"),
                    "BillableHours": billable_hours,
                    "NonBillableHours": nonbillable_hours,
                    "CostRateUsed": cost_rate_used,
                    "ExtendedCost": money(total_cost_hours * float(cost_rate_used)),
                    "ApprovedByEmployeeID": design_service_approver_id(context, work_date),
                    "ApprovedDate": approval_date.strftime("%Y-%m-%d"),
                    "BillingStatus": "Unbilled",
                })

    append_rows(context, "ServiceTimeEntry", time_entry_rows)
    refresh_service_engagement_statuses(context)


def generate_month_shipments(context: GenerationContext, year: int, month: int) -> None:
    orders = context.tables["SalesOrder"]
    order_lines = context.tables["SalesOrderLine"]
    if orders.empty or order_lines.empty:
        return

    rng = context.rng
    month_start, month_end = month_bounds(year, month)
    shipped_quantities = sales_order_line_shipped_quantities(context)
    inventory = shadow_inventory_state(context)
    items = context.tables["Item"].set_index("ItemID").to_dict("index")
    customers = context.tables["Customer"].set_index("CustomerID").to_dict("index")
    sales_order_lookup = orders.set_index("SalesOrderID").to_dict("index")
    sales_order_line_lookup = order_lines.set_index("SalesOrderLineID").to_dict("index")
    warehouses = warehouse_ids(context)

    receipt_headers = (
        context.tables["GoodsReceipt"].set_index("GoodsReceiptID")[["ReceiptDate", "WarehouseID"]].to_dict("index")
        if not context.tables["GoodsReceipt"].empty
        else {}
    )
    availability_events: dict[pd.Timestamp, list[tuple[int, int, float]]] = defaultdict(list)
    for line in context.tables["GoodsReceiptLine"].itertuples(index=False):
        receipt = receipt_headers.get(int(line.GoodsReceiptID))
        if receipt is None:
            continue
        receipt_date = pd.Timestamp(receipt["ReceiptDate"])
        if month_start <= receipt_date <= month_end:
            availability_events[receipt_date.normalize()].append((int(line.ItemID), int(receipt["WarehouseID"]), float(line.QuantityReceived)))

    completion_headers = (
        context.tables["ProductionCompletion"].set_index("ProductionCompletionID")[["CompletionDate", "WarehouseID"]].to_dict("index")
        if not context.tables["ProductionCompletion"].empty
        else {}
    )
    for line in context.tables["ProductionCompletionLine"].itertuples(index=False):
        completion = completion_headers.get(int(line.ProductionCompletionID))
        if completion is None:
            continue
        completion_date = pd.Timestamp(completion["CompletionDate"])
        if month_start <= completion_date <= month_end:
            availability_events[completion_date.normalize()].append((int(line.ItemID), int(completion["WarehouseID"]), float(line.QuantityCompleted)))

    open_order_lines = order_lines.copy()
    if not context.tables["Item"].empty:
        item_groups = context.tables["Item"].set_index("ItemID")["ItemGroup"].astype(str).to_dict()
        open_order_lines = open_order_lines[
            open_order_lines["ItemID"].astype(int).map(lambda item_id: item_groups.get(int(item_id), "")).ne("Services")
        ].copy()
    open_order_lines["ShippedQuantity"] = open_order_lines["SalesOrderLineID"].map(shipped_quantities).fillna(0.0)
    open_order_lines["RemainingQuantity"] = (open_order_lines["Quantity"].astype(float) - open_order_lines["ShippedQuantity"].astype(float)).round(2)
    open_order_lines = open_order_lines[open_order_lines["RemainingQuantity"].gt(0)].copy()
    if open_order_lines.empty:
        return

    candidate_orders = orders[
        pd.to_datetime(orders["OrderDate"]).le(month_end)
        & orders["SalesOrderID"].astype(int).isin(open_order_lines["SalesOrderID"].astype(int))
    ].copy()
    candidate_orders["RequestedDeliveryDateTS"] = pd.to_datetime(candidate_orders["RequestedDeliveryDate"])
    candidate_orders["OrderDateTS"] = pd.to_datetime(candidate_orders["OrderDate"])
    candidate_orders = candidate_orders.sort_values(["RequestedDeliveryDateTS", "OrderDateTS", "SalesOrderID"])

    shipment_rows: list[dict[str, Any]] = []
    shipment_line_rows: list[dict[str, Any]] = []
    processed_receipt_dates: set[pd.Timestamp] = set()
    shipment_plans: list[tuple[pd.Timestamp, int, Any, pd.DataFrame]] = []

    for order in candidate_orders.itertuples(index=False):
        related_lines = open_order_lines[open_order_lines["SalesOrderID"].astype(int).eq(int(order.SalesOrderID))]
        if related_lines.empty:
            continue

        earliest_ship_date = max(month_start, pd.Timestamp(order.OrderDate) + pd.Timedelta(days=1))
        preferred_ship_date = clamp_date_to_month(
            earliest_ship_date + pd.Timedelta(days=int(rng.integers(0, 10))),
            year,
            month,
        )
        ship_probability = 0.70 if pd.Timestamp(order.RequestedDeliveryDate) >= month_start else 0.93
        if rng.random() > ship_probability:
            continue

        shipment_plans.append((preferred_ship_date.normalize(), int(order.SalesOrderID), order, related_lines))

    for shipment_date, _, order, related_lines in sorted(shipment_plans, key=lambda item: (item[0], item[1])):
        for receipt_date in sorted(date for date in availability_events if date <= shipment_date):
            if receipt_date in processed_receipt_dates:
                continue
            for item_id, warehouse_id, quantity_received in availability_events[receipt_date]:
                inventory[(item_id, warehouse_id)] = round(
                    float(inventory.get((item_id, warehouse_id), 0.0)) + float(quantity_received),
                    2,
                )
            processed_receipt_dates.add(receipt_date)

        warehouse_scores = {
            warehouse_id: round(
                sum(float(inventory.get((int(line.ItemID), warehouse_id), 0.0)) for line in related_lines.itertuples(index=False)),
                2,
            )
            for warehouse_id in warehouses
        }
        chosen_warehouse_id = max(warehouse_scores, key=warehouse_scores.get)
        if warehouse_scores[chosen_warehouse_id] <= 0:
            continue

        shipment_id = next_id(context, "Shipment")
        line_number = 1
        remaining_after_shipment = 0.0
        shipped_line_metrics: list[dict[str, float | str]] = []
        for line in related_lines.itertuples(index=False):
            available = max(0.0, round(float(inventory.get((int(line.ItemID), chosen_warehouse_id), 0.0)), 2))
            remaining = float(line.RemainingQuantity)
            if available <= 0:
                remaining_after_shipment = round(remaining_after_shipment + remaining, 2)
                continue

            ship_cap = remaining
            if rng.random() <= 0.22:
                ship_cap = max(1.0, qty(remaining * rng.uniform(0.40, 0.85)))
            shipped_quantity = qty(min(remaining, available, ship_cap))
            if shipped_quantity <= 0:
                remaining_after_shipment = round(remaining_after_shipment + remaining, 2)
                continue

            inventory[(int(line.ItemID), chosen_warehouse_id)] = round(available - shipped_quantity, 2)
            item = items[int(line.ItemID)]
            sales_order_line = sales_order_line_lookup[int(line.SalesOrderLineID)]
            merchandise_subtotal = money(
                shipped_quantity
                * float(sales_order_line["UnitPrice"])
                * (1 - float(sales_order_line["Discount"]))
            )
            shipment_line_rows.append({
                "ShipmentLineID": next_id(context, "ShipmentLine"),
                "ShipmentID": shipment_id,
                "SalesOrderLineID": int(line.SalesOrderLineID),
                "LineNumber": line_number,
                "ItemID": int(line.ItemID),
                "QuantityShipped": shipped_quantity,
                "ExtendedStandardCost": money(shipped_quantity * float(item["StandardCost"])),
            })
            shipped_line_metrics.append({
                "ItemGroup": str(item["ItemGroup"]),
                "QuantityShipped": shipped_quantity,
                "MerchandiseSubTotal": merchandise_subtotal,
            })
            remaining_after_shipment = round(remaining_after_shipment + max(0.0, remaining - shipped_quantity), 2)
            line_number += 1

        if line_number == 1:
            context.counters["Shipment"] -= 1
            continue

        preferred_ship_date = pd.Timestamp(shipment_date)
        delivery_date = clamp_date_to_month(preferred_ship_date + pd.Timedelta(days=int(rng.integers(1, 6))), year, month)
        sales_order = sales_order_lookup[int(order.SalesOrderID)]
        customer = customers[int(sales_order["CustomerID"])]
        carrier_name = str(rng.choice(CARRIERS))
        freight_cost, billable_freight_amount = shipment_freight_amounts(
            context,
            shipment_id=shipment_id,
            customer_region=str(customer["Region"]),
            carrier_name=carrier_name,
            freight_terms=str(sales_order.get("FreightTerms") or "Prepaid"),
            shipped_line_metrics=shipped_line_metrics,
            is_partial_shipment=remaining_after_shipment > 0,
        )
        shipment_rows.append({
            "ShipmentID": shipment_id,
            "ShipmentNumber": format_doc_number("SH", year, shipment_id),
            "SalesOrderID": int(order.SalesOrderID),
            "ShipmentDate": preferred_ship_date.strftime("%Y-%m-%d"),
            "WarehouseID": chosen_warehouse_id,
            "ShippedBy": carrier_name,
            "TrackingNumber": f"TRK{year}{shipment_id:08d}" if rng.random() > 0.04 else None,
            "Status": "Delivered" if rng.random() > 0.08 else "In Transit",
            "DeliveryDate": delivery_date.strftime("%Y-%m-%d"),
            "FreightCost": freight_cost,
            "BillableFreightAmount": billable_freight_amount,
        })

    for receipt_date in sorted(date for date in availability_events if date not in processed_receipt_dates):
        for item_id, warehouse_id, quantity_received in availability_events[receipt_date]:
            inventory[(item_id, warehouse_id)] = round(
                float(inventory.get((item_id, warehouse_id), 0.0)) + float(quantity_received),
                2,
            )

    append_rows(context, "Shipment", shipment_rows)
    append_rows(context, "ShipmentLine", shipment_line_rows)


def generate_month_sales_invoices(context: GenerationContext, year: int, month: int) -> None:
    shipments = context.tables["Shipment"]
    shipment_lines = context.tables["ShipmentLine"]
    rng = context.rng
    month_start, month_end = month_bounds(year, month)
    invoice_rows: list[dict[str, Any]] = []
    invoice_line_rows: list[dict[str, Any]] = []
    service_billing_rows: list[dict[str, Any]] = []

    sales_orders = context.tables["SalesOrder"].set_index("SalesOrderID").to_dict("index") if not context.tables["SalesOrder"].empty else {}
    sales_order_lines = context.tables["SalesOrderLine"].set_index("SalesOrderLineID").to_dict("index") if not context.tables["SalesOrderLine"].empty else {}
    customers = context.tables["Customer"].set_index("CustomerID").to_dict("index") if not context.tables["Customer"].empty else {}

    if not shipments.empty and not shipment_lines.empty:
        billed_quantities = shipment_line_billed_quantities(context)
        shipment_headers = shipments.set_index("ShipmentID").to_dict("index")
        existing_invoice_lines = context.tables["SalesInvoiceLine"]
        already_billed_shipment_ids: set[int] = set()
        if not existing_invoice_lines.empty:
            existing_shipment_links = existing_invoice_lines[existing_invoice_lines["ShipmentLineID"].notna()][
                ["ShipmentLineID"]
            ].merge(
                shipment_lines[["ShipmentLineID", "ShipmentID"]],
                on="ShipmentLineID",
                how="left",
            )
            already_billed_shipment_ids = set(
                existing_shipment_links["ShipmentID"].dropna().astype(int).tolist()
            )

        groups: dict[tuple[int, str], list[tuple[Any, float]]] = defaultdict(list)
        for shipment_line in shipment_lines.itertuples(index=False):
            billed_quantity = float(billed_quantities.get(int(shipment_line.ShipmentLineID), 0.0))
            remaining_quantity = round(float(shipment_line.QuantityShipped) - billed_quantity, 2)
            shipment = shipment_headers.get(int(shipment_line.ShipmentID))
            if shipment is None or remaining_quantity <= 0:
                continue
            shipment_date = pd.Timestamp(shipment["ShipmentDate"])
            if shipment_date > month_end:
                continue
            invoice_probability = 0.88 if shipment_date.year == year and shipment_date.month == month else 0.97
            if rng.random() > invoice_probability:
                continue
            invoice_date = clamp_date_to_month(
                (
                    shipment_date + pd.Timedelta(days=int(rng.integers(0, 5)))
                ) if shipment_date.year == year and shipment_date.month == month else (
                    pd.Timestamp(year=year, month=month, day=1) + pd.Timedelta(days=int(rng.integers(0, 6)))
                ),
                year,
                month,
            )
            groups[(int(shipment["SalesOrderID"]), invoice_date.strftime("%Y-%m-%d"))].append((shipment_line, remaining_quantity))

        billed_shipment_ids = set(already_billed_shipment_ids)
        for (sales_order_id, invoice_date_str), grouped_lines in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0])):
            invoice_date = pd.Timestamp(invoice_date_str)
            sales_order = sales_orders[int(sales_order_id)]
            customer = customers[int(sales_order["CustomerID"])]
            invoice_id = next_id(context, "SalesInvoice")
            due_date = invoice_date + pd.Timedelta(days=payment_term_days(str(customer["PaymentTerms"])))
            subtotal = 0.0
            freight_amount = 0.0
            line_number = 1
            for shipment_line, remaining_quantity in grouped_lines:
                shipment = shipment_headers[int(shipment_line.ShipmentID)]
                shipment_id = int(shipment_line.ShipmentID)
                if shipment_id not in billed_shipment_ids:
                    shipment_freight_amount = shipment.get("BillableFreightAmount")
                    if pd.notna(shipment_freight_amount):
                        freight_amount = money(freight_amount + float(shipment_freight_amount))
                    billed_shipment_ids.add(shipment_id)

                sales_line = sales_order_lines[int(shipment_line.SalesOrderLineID)]
                quantity = qty(remaining_quantity)
                line_total = money(quantity * float(sales_line["UnitPrice"]) * (1 - float(sales_line["Discount"])))
                subtotal = money(subtotal + line_total)
                invoice_line_rows.append({
                    "SalesInvoiceLineID": next_id(context, "SalesInvoiceLine"),
                    "SalesInvoiceID": invoice_id,
                    "SalesOrderLineID": int(shipment_line.SalesOrderLineID),
                    "ShipmentLineID": int(shipment_line.ShipmentLineID),
                    "LineNumber": line_number,
                    "ItemID": int(shipment_line.ItemID),
                    "Quantity": quantity,
                    "BaseListPrice": float(sales_line["BaseListPrice"]),
                    "UnitPrice": float(sales_line["UnitPrice"]),
                    "Discount": float(sales_line["Discount"]),
                    "LineTotal": line_total,
                    "PriceListLineID": None if pd.isna(sales_line["PriceListLineID"]) else int(sales_line["PriceListLineID"]),
                    "PromotionID": None if pd.isna(sales_line["PromotionID"]) else int(sales_line["PromotionID"]),
                    "PriceOverrideApprovalID": None if pd.isna(sales_line["PriceOverrideApprovalID"]) else int(sales_line["PriceOverrideApprovalID"]),
                    "PricingMethod": str(sales_line["PricingMethod"]),
                })
                line_number += 1

            tax_amount = money((subtotal + freight_amount) * context.settings.tax_rate)
            invoice_rows.append({
                "SalesInvoiceID": invoice_id,
                "InvoiceNumber": format_doc_number("SI", year, invoice_id),
                "InvoiceDate": invoice_date.strftime("%Y-%m-%d"),
                "DueDate": due_date.strftime("%Y-%m-%d"),
                "SalesOrderID": int(sales_order_id),
                "CustomerID": int(sales_order["CustomerID"]),
                "SubTotal": subtotal,
                "FreightAmount": freight_amount,
                "TaxAmount": tax_amount,
                "GrandTotal": money(subtotal + freight_amount + tax_amount),
                "Status": "Submitted",
                "PaymentDate": None,
            })

    service_time_entries = context.tables["ServiceTimeEntry"]
    service_engagements = context.tables["ServiceEngagement"]
    if not service_time_entries.empty and not service_engagements.empty:
        engagement_lookup = service_engagements.set_index("ServiceEngagementID").to_dict("index")
        unbilled_entries = service_time_entries.copy()
        unbilled_entries["WorkDateTS"] = pd.to_datetime(unbilled_entries["WorkDate"], errors="coerce")
        unbilled_entries = unbilled_entries[
            unbilled_entries["BillingStatus"].astype(str).ne("Billed")
            & unbilled_entries["WorkDateTS"].between(month_start, month_end)
            & unbilled_entries["BillableHours"].astype(float).gt(0.0)
        ].copy()

        billed_time_entry_ids: list[int] = []
        for service_engagement_id, rows in unbilled_entries.groupby("ServiceEngagementID"):
            engagement = engagement_lookup.get(int(service_engagement_id))
            if engagement is None:
                continue
            sales_order = sales_orders.get(int(engagement["SalesOrderID"]))
            sales_line = sales_order_lines.get(int(engagement["SalesOrderLineID"]))
            customer = customers.get(int(engagement["CustomerID"]))
            if sales_order is None or sales_line is None or customer is None:
                continue

            billed_hours = qty(float(rows["BillableHours"].astype(float).sum()))
            if billed_hours <= 0:
                continue

            billing_period_start = pd.Timestamp(rows["WorkDateTS"].min()).normalize()
            billing_period_end = pd.Timestamp(rows["WorkDateTS"].max()).normalize()
            invoice_date = clamp_date_to_month(max(billing_period_end, month_end), year, month)
            due_date = invoice_date + pd.Timedelta(days=payment_term_days(str(customer["PaymentTerms"])))
            invoice_id = next_id(context, "SalesInvoice")
            line_total = money(billed_hours * float(engagement["HourlyRate"]))
            sales_invoice_line_id = next_id(context, "SalesInvoiceLine")

            invoice_rows.append({
                "SalesInvoiceID": invoice_id,
                "InvoiceNumber": format_doc_number("SI", year, invoice_id),
                "InvoiceDate": invoice_date.strftime("%Y-%m-%d"),
                "DueDate": due_date.strftime("%Y-%m-%d"),
                "SalesOrderID": int(engagement["SalesOrderID"]),
                "CustomerID": int(engagement["CustomerID"]),
                "SubTotal": line_total,
                "FreightAmount": 0.0,
                "TaxAmount": money(line_total * context.settings.tax_rate),
                "GrandTotal": money(line_total + money(line_total * context.settings.tax_rate)),
                "Status": "Submitted",
                "PaymentDate": None,
            })
            invoice_line_rows.append({
                "SalesInvoiceLineID": sales_invoice_line_id,
                "SalesInvoiceID": invoice_id,
                "SalesOrderLineID": int(engagement["SalesOrderLineID"]),
                "ShipmentLineID": None,
                "LineNumber": 1,
                "ItemID": int(engagement["ItemID"]),
                "Quantity": billed_hours,
                "BaseListPrice": float(sales_line["BaseListPrice"]),
                "UnitPrice": float(engagement["HourlyRate"]),
                "Discount": 0.0,
                "LineTotal": line_total,
                "PriceListLineID": None,
                "PromotionID": None,
                "PriceOverrideApprovalID": None,
                "PricingMethod": "Base List",
            })
            service_billing_rows.append({
                "ServiceBillingLineID": next_id(context, "ServiceBillingLine"),
                "ServiceEngagementID": int(service_engagement_id),
                "SalesInvoiceLineID": sales_invoice_line_id,
                "BillingPeriodStartDate": billing_period_start.strftime("%Y-%m-%d"),
                "BillingPeriodEndDate": billing_period_end.strftime("%Y-%m-%d"),
                "BilledHours": billed_hours,
                "HourlyRate": float(engagement["HourlyRate"]),
                "LineAmount": line_total,
                "Status": "Invoiced",
            })
            billed_time_entry_ids.extend(rows["ServiceTimeEntryID"].astype(int).tolist())

        if billed_time_entry_ids:
            billed_mask = context.tables["ServiceTimeEntry"]["ServiceTimeEntryID"].astype(int).isin(billed_time_entry_ids)
            context.tables["ServiceTimeEntry"].loc[billed_mask, "BillingStatus"] = "Billed"

    if not invoice_rows and not invoice_line_rows and not service_billing_rows:
        return

    append_rows(context, "SalesInvoice", invoice_rows)
    append_rows(context, "SalesInvoiceLine", invoice_line_rows)
    append_rows(context, "ServiceBillingLine", service_billing_rows)
    refresh_service_engagement_statuses(context)
    _, month_end = month_bounds(year, month)
    billed_quantities = shipment_line_billed_quantities(context)
    shipment_headers = shipments.set_index("ShipmentID").to_dict("index")
    sales_orders = context.tables["SalesOrder"].set_index("SalesOrderID").to_dict("index")
    sales_order_lines = context.tables["SalesOrderLine"].set_index("SalesOrderLineID").to_dict("index")
    customers = context.tables["Customer"].set_index("CustomerID").to_dict("index")
    existing_invoice_lines = context.tables["SalesInvoiceLine"]
    already_billed_shipment_ids: set[int] = set()
    if not existing_invoice_lines.empty:
        existing_shipment_links = existing_invoice_lines[existing_invoice_lines["ShipmentLineID"].notna()][
            ["ShipmentLineID"]
        ].merge(
            shipment_lines[["ShipmentLineID", "ShipmentID"]],
            on="ShipmentLineID",
            how="left",
        )
        already_billed_shipment_ids = set(
            existing_shipment_links["ShipmentID"].dropna().astype(int).tolist()
        )

    groups: dict[tuple[int, str], list[tuple[Any, float]]] = defaultdict(list)
    for shipment_line in shipment_lines.itertuples(index=False):
        billed_quantity = float(billed_quantities.get(int(shipment_line.ShipmentLineID), 0.0))
        remaining_quantity = round(float(shipment_line.QuantityShipped) - billed_quantity, 2)
        shipment = shipment_headers.get(int(shipment_line.ShipmentID))
        if shipment is None or remaining_quantity <= 0:
            continue
        shipment_date = pd.Timestamp(shipment["ShipmentDate"])
        if shipment_date > month_end:
            continue
        invoice_probability = 0.88 if shipment_date.year == year and shipment_date.month == month else 0.97
        if rng.random() > invoice_probability:
            continue
        invoice_date = clamp_date_to_month(
            (
                shipment_date + pd.Timedelta(days=int(rng.integers(0, 5)))
            ) if shipment_date.year == year and shipment_date.month == month else (
                pd.Timestamp(year=year, month=month, day=1) + pd.Timedelta(days=int(rng.integers(0, 6)))
            ),
            year,
            month,
        )
        groups[(int(shipment["SalesOrderID"]), invoice_date.strftime("%Y-%m-%d"))].append((shipment_line, remaining_quantity))

    invoice_rows: list[dict[str, Any]] = []
    invoice_line_rows: list[dict[str, Any]] = []
    billed_shipment_ids = set(already_billed_shipment_ids)
    for (sales_order_id, invoice_date_str), grouped_lines in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0])):
        invoice_date = pd.Timestamp(invoice_date_str)
        sales_order = sales_orders[int(sales_order_id)]
        customer = customers[int(sales_order["CustomerID"])]
        invoice_id = next_id(context, "SalesInvoice")
        due_date = invoice_date + pd.Timedelta(days=payment_term_days(str(customer["PaymentTerms"])))
        subtotal = 0.0
        freight_amount = 0.0
        line_number = 1
        for shipment_line, remaining_quantity in grouped_lines:
            shipment = shipment_headers[int(shipment_line.ShipmentID)]
            shipment_id = int(shipment_line.ShipmentID)
            if shipment_id not in billed_shipment_ids:
                shipment_freight_amount = shipment.get("BillableFreightAmount")
                if pd.notna(shipment_freight_amount):
                    freight_amount = money(freight_amount + float(shipment_freight_amount))
                billed_shipment_ids.add(shipment_id)

            sales_line = sales_order_lines[int(shipment_line.SalesOrderLineID)]
            quantity = qty(remaining_quantity)
            line_total = money(quantity * float(sales_line["UnitPrice"]) * (1 - float(sales_line["Discount"])))
            subtotal = money(subtotal + line_total)
            invoice_line_rows.append({
                "SalesInvoiceLineID": next_id(context, "SalesInvoiceLine"),
                "SalesInvoiceID": invoice_id,
                "SalesOrderLineID": int(shipment_line.SalesOrderLineID),
                "ShipmentLineID": int(shipment_line.ShipmentLineID),
                "LineNumber": line_number,
                "ItemID": int(shipment_line.ItemID),
                "Quantity": quantity,
                "BaseListPrice": float(sales_line["BaseListPrice"]),
                "UnitPrice": float(sales_line["UnitPrice"]),
                "Discount": float(sales_line["Discount"]),
                "LineTotal": line_total,
                "PriceListLineID": None if pd.isna(sales_line["PriceListLineID"]) else int(sales_line["PriceListLineID"]),
                "PromotionID": None if pd.isna(sales_line["PromotionID"]) else int(sales_line["PromotionID"]),
                "PriceOverrideApprovalID": None if pd.isna(sales_line["PriceOverrideApprovalID"]) else int(sales_line["PriceOverrideApprovalID"]),
                "PricingMethod": str(sales_line["PricingMethod"]),
            })
            line_number += 1

        tax_amount = money((subtotal + freight_amount) * context.settings.tax_rate)
        invoice_rows.append({
            "SalesInvoiceID": invoice_id,
            "InvoiceNumber": format_doc_number("SI", year, invoice_id),
            "InvoiceDate": invoice_date.strftime("%Y-%m-%d"),
            "DueDate": due_date.strftime("%Y-%m-%d"),
            "SalesOrderID": int(sales_order_id),
            "CustomerID": int(sales_order["CustomerID"]),
            "SubTotal": subtotal,
            "FreightAmount": freight_amount,
            "TaxAmount": tax_amount,
            "GrandTotal": money(subtotal + freight_amount + tax_amount),
            "Status": "Submitted",
            "PaymentDate": None,
        })

    append_rows(context, "SalesInvoice", invoice_rows)
    append_rows(context, "SalesInvoiceLine", invoice_line_rows)


def generate_month_cash_receipts(context: GenerationContext, year: int, month: int) -> None:
    rng = context.rng
    month_start, month_end = month_bounds(year, month)
    customers = context.tables["Customer"].set_index("CustomerID").to_dict("index")
    sales_orders = context.tables["SalesOrder"]
    sales_invoices = context.tables["SalesInvoice"]

    receipt_rows: list[dict[str, Any]] = []
    application_rows: list[dict[str, Any]] = []

    open_orders = sales_orders[
        pd.to_datetime(sales_orders["OrderDate"]).dt.year.eq(year)
        & pd.to_datetime(sales_orders["OrderDate"]).dt.month.eq(month)
        & sales_orders["OrderTotal"].astype(float).gt(7500.0)
    ].copy()
    for order in open_orders.itertuples(index=False):
        customer = customers[int(order.CustomerID)]
        customer_segment = str(customer["CustomerSegment"])
        payment_terms = str(customer["PaymentTerms"])
        probability = float(DEPOSIT_PROBABILITIES.get(customer_segment, 0.02))
        if payment_term_days(payment_terms) >= 60:
            probability += 0.01
        if rng.random() > probability:
            continue
        receipt_id = next_id(context, "CashReceipt")
        receipt_date = clamp_date_to_month(pd.Timestamp(order.OrderDate) + pd.Timedelta(days=int(rng.integers(0, 6))), year, month)
        deposit_low, deposit_high = DEPOSIT_FRACTION_RANGES.get(customer_segment, (0.06, 0.12))
        amount = money(float(order.OrderTotal) * rng.uniform(deposit_low, deposit_high))
        receipt_recorders = employee_ids_for_cost_center(context, "Customer Service", receipt_date)
        receipt_rows.append({
            "CashReceiptID": receipt_id,
            "ReceiptNumber": format_doc_number("CR", year, receipt_id),
            "ReceiptDate": receipt_date.strftime("%Y-%m-%d"),
            "CustomerID": int(order.CustomerID),
            "SalesInvoiceID": None,
            "Amount": amount,
            "PaymentMethod": str(rng.choice(PAYMENT_METHODS)),
            "ReferenceNumber": f"DEP{receipt_id:08d}",
            "DepositDate": receipt_date.strftime("%Y-%m-%d"),
            "RecordedByEmployeeID": int(rng.choice(receipt_recorders)),
        })

    receipts_view = pd.concat(
        [context.tables["CashReceipt"], pd.DataFrame(receipt_rows, columns=TABLE_COLUMNS["CashReceipt"])],
        ignore_index=True,
    )
    current_applied_amounts = receipt_applied_amounts(context)
    settled_amounts = invoice_settled_amounts(context)
    sales_invoices_view = sales_invoices.copy()
    if not sales_invoices_view.empty:
        sales_invoices_view["InvoiceDateTS"] = pd.to_datetime(sales_invoices_view["InvoiceDate"], errors="coerce")
        sales_invoices_view["DueDateTS"] = pd.to_datetime(sales_invoices_view["DueDate"], errors="coerce")
        sales_invoices_view = sales_invoices_view[
            sales_invoices_view["InvoiceDateTS"].notna()
            & sales_invoices_view["DueDateTS"].notna()
            & sales_invoices_view["InvoiceDateTS"].le(month_end)
        ].copy()

    for receipt in receipts_view.sort_values(["ReceiptDate", "CashReceiptID"]).itertuples(index=False):
        receipt_date = pd.Timestamp(receipt.ReceiptDate)
        if receipt_date > month_end:
            continue

        remaining_receipt_amount = round(float(receipt.Amount) - float(current_applied_amounts.get(int(receipt.CashReceiptID), 0.0)), 2)
        if remaining_receipt_amount <= 0:
            continue

        customer_invoices = sales_invoices_view[
            sales_invoices_view["CustomerID"].astype(int).eq(int(receipt.CustomerID))
        ].copy()
        if customer_invoices.empty:
            continue
        customer_invoices["SettledAmount"] = customer_invoices["SalesInvoiceID"].astype(int).map(settled_amounts).fillna(0.0)
        customer_invoices["OpenAmount"] = (customer_invoices["GrandTotal"].astype(float) - customer_invoices["SettledAmount"].astype(float)).round(2)
        customer_invoices = customer_invoices[customer_invoices["OpenAmount"].gt(0)].sort_values(["DueDateTS", "InvoiceDateTS", "SalesInvoiceID"])
        apply_receipt_oldest_first(
            context,
            receipt_id=int(receipt.CashReceiptID),
            receipt_date=receipt_date,
            customer_invoices=customer_invoices,
            receipt_amount=remaining_receipt_amount,
            current_applied_amounts=current_applied_amounts,
            settled_amounts=settled_amounts,
            application_rows=application_rows,
            year=year,
            month=month,
        )

    open_invoices = receivables_open_invoices(context, as_of_date=month_end, settled_amounts=settled_amounts)

    for customer_id, customer_invoices in open_invoices.groupby("CustomerID"):
        customer = customers[int(customer_id)]
        payment_terms = str(customer["PaymentTerms"])
        customer_segment = str(customer["CustomerSegment"])
        open_balance = round(float(customer_invoices["OpenAmount"].sum()), 2)
        if open_balance <= 0:
            continue

        target_amount = 0.0
        max_days_past_due = int(customer_invoices["DaysPastDue"].max())
        for invoice in customer_invoices.itertuples(index=False):
            target_amount += float(invoice.OpenAmount) * invoice_collection_target_ratio(
                int(invoice.DaysPastDue),
                customer_segment=customer_segment,
                payment_terms=payment_terms,
                rng=rng,
            )

        target_amount = money(min(open_balance * 1.01, target_amount))
        if target_amount < min(150.0, open_balance * 0.08):
            continue

        receipt_count = 1
        if target_amount >= 60000 and len(customer_invoices) >= 8:
            receipt_count = 2
        if target_amount >= 180000 and len(customer_invoices) >= 15:
            receipt_count = 3

        if receipt_count == 1:
            receipt_amounts = [target_amount]
        else:
            raw_weights = rng.dirichlet(np.ones(receipt_count))
            receipt_amounts = [money(target_amount * float(weight)) for weight in raw_weights]
            remainder = money(target_amount - sum(receipt_amounts))
            receipt_amounts[-1] = money(receipt_amounts[-1] + remainder)

        receipt_dates = collection_receipt_dates(
            month_end,
            receipt_count=receipt_count,
            max_days_past_due=max_days_past_due,
            rng=rng,
        )

        for receipt_amount, receipt_date in zip(receipt_amounts, receipt_dates):
            if receipt_amount <= 0:
                continue
            customer_invoices = receivables_open_invoices(
                context,
                as_of_date=month_end,
                customer_id=int(customer_id),
                settled_amounts=settled_amounts,
            )
            if customer_invoices.empty:
                break
            open_balance_remaining = round(float(customer_invoices["OpenAmount"].sum()), 2)
            if open_balance_remaining <= 0:
                break
            planned_receipt_amount = money(min(open_balance_remaining * 1.01, receipt_amount))
            if planned_receipt_amount <= 0:
                continue

            receipt_id = next_id(context, "CashReceipt")
            receipt_recorders = employee_ids_for_cost_center(context, "Customer Service", receipt_date)
            receipt_rows.append({
                "CashReceiptID": receipt_id,
                "ReceiptNumber": format_doc_number("CR", year, receipt_id),
                "ReceiptDate": receipt_date.strftime("%Y-%m-%d"),
                "CustomerID": int(customer_id),
                "SalesInvoiceID": None,
                "Amount": planned_receipt_amount,
                "PaymentMethod": str(rng.choice(PAYMENT_METHODS)),
                "ReferenceNumber": f"AR{receipt_id:08d}",
                "DepositDate": clamp_date_to_month(
                    receipt_date + pd.Timedelta(days=int(rng.integers(0, 3))),
                    year,
                    month,
                ).strftime("%Y-%m-%d"),
                "RecordedByEmployeeID": int(rng.choice(receipt_recorders)),
            })
            apply_receipt_oldest_first(
                context,
                receipt_id=receipt_id,
                receipt_date=receipt_date,
                customer_invoices=customer_invoices,
                receipt_amount=planned_receipt_amount,
                current_applied_amounts=current_applied_amounts,
                settled_amounts=settled_amounts,
                application_rows=application_rows,
                year=year,
                month=month,
            )

    append_rows(context, "CashReceipt", receipt_rows)
    append_rows(context, "CashReceiptApplication", application_rows)
    refresh_cash_receipt_links(context)


def generate_month_sales_returns(context: GenerationContext, year: int, month: int) -> None:
    month_start, month_end = month_bounds(year, month)
    sales_invoices = context.tables["SalesInvoice"]
    sales_invoice_lines = context.tables["SalesInvoiceLine"]
    if sales_invoices.empty or sales_invoice_lines.empty or context.tables["ShipmentLine"].empty:
        return

    shipment_headers = context.tables["Shipment"].set_index("ShipmentID").to_dict("index") if not context.tables["Shipment"].empty else {}
    shipment_line_lookup = context.tables["ShipmentLine"].set_index("ShipmentLineID").to_dict("index")
    invoice_lookup = sales_invoices.set_index("SalesInvoiceID").to_dict("index")
    invoice_lines_by_invoice = {
        int(invoice_id): rows.copy()
        for invoice_id, rows in sales_invoice_lines[sales_invoice_lines["ShipmentLineID"].notna()].groupby("SalesInvoiceID")
    }
    returned_quantities = shipment_line_returned_quantities(context)
    already_returned_invoices = returned_invoice_ids(context)

    return_rows: list[dict[str, Any]] = []
    return_line_rows: list[dict[str, Any]] = []
    memo_rows: list[dict[str, Any]] = []
    memo_line_rows: list[dict[str, Any]] = []

    for invoice in sales_invoices.sort_values(["InvoiceDate", "SalesInvoiceID"]).itertuples(index=False):
        sales_invoice_id = int(invoice.SalesInvoiceID)
        if sales_invoice_id in already_returned_invoices:
            continue

        lines = invoice_lines_by_invoice.get(sales_invoice_id)
        if lines is None or lines.empty:
            continue

        invoice_record = invoice_lookup[sales_invoice_id]
        plan = invoice_return_plan(context, sales_invoice_id, invoice_record)
        if plan is None:
            continue

        return_date = pd.Timestamp(plan["return_date"])
        if return_date < month_start or return_date > month_end:
            continue

        invoice_rng = plan["rng"]
        reason_code = str(invoice_rng.choice(RETURN_REASON_CODES))
        return_id = next_id(context, "SalesReturn")
        first_shipment_line = shipment_line_lookup[int(lines.iloc[0]["ShipmentLineID"])]
        first_shipment = shipment_headers[int(first_shipment_line["ShipmentID"])]
        return_rows.append({
            "SalesReturnID": return_id,
            "ReturnNumber": format_doc_number("SR", year, return_id),
            "ReturnDate": return_date.strftime("%Y-%m-%d"),
            "CustomerID": int(invoice_record["CustomerID"]),
            "SalesOrderID": int(invoice_record["SalesOrderID"]),
            "WarehouseID": int(first_shipment["WarehouseID"]),
            "ReceivedByEmployeeID": int(invoice_rng.choice(employee_ids_for_cost_center(context, "Warehouse", return_date))),
            "ReasonCode": reason_code,
            "Status": "Received",
        })

        credit_memo_id = next_id(context, "CreditMemo")
        credit_memo_date = clamp_date_to_month(return_date + pd.Timedelta(days=int(invoice_rng.integers(0, 4))), year, month)
        subtotal = 0.0
        line_number = 1
        eligible_lines: list[dict[str, Any]] = []
        for line in lines.itertuples(index=False):
            shipment_line_id = int(line.ShipmentLineID)
            eligible_quantity = round(float(line.Quantity) - float(returned_quantities.get(shipment_line_id, 0.0)), 2)
            if eligible_quantity <= 0:
                continue
            eligible_lines.append({"line": line, "eligible_quantity": eligible_quantity})

        if not eligible_lines:
            context.counters["SalesReturn"] -= 1
            context.counters["CreditMemo"] -= 1
            continue

        selected_count = select_return_line_count(invoice_rng, len(eligible_lines))
        selected_indexes = invoice_rng.choice(np.arange(len(eligible_lines)), size=selected_count, replace=False)
        selected_indexes = np.atleast_1d(selected_indexes).astype(int).tolist()

        for selected_index in selected_indexes:
            selected_entry = eligible_lines[int(selected_index)]
            line = selected_entry["line"]
            shipment_line_id = int(line.ShipmentLineID)
            shipment_line = shipment_line_lookup[shipment_line_id]
            eligible_quantity = float(selected_entry["eligible_quantity"])
            returned_quantity = select_return_quantity(invoice_rng, eligible_quantity, reason_code)
            if returned_quantity <= 0:
                continue

            sales_return_line_id = next_id(context, "SalesReturnLine")
            return_line_rows.append({
                "SalesReturnLineID": sales_return_line_id,
                "SalesReturnID": return_id,
                "ShipmentLineID": shipment_line_id,
                "LineNumber": line_number,
                "ItemID": int(line.ItemID),
                "QuantityReturned": returned_quantity,
                "ExtendedStandardCost": money(
                    returned_quantity
                    * (float(shipment_line["ExtendedStandardCost"]) / max(float(shipment_line["QuantityShipped"]), 1.0))
                ),
            })

            line_total = money(returned_quantity * float(line.UnitPrice) * (1 - float(line.Discount)))
            subtotal = money(subtotal + line_total)
            memo_line_rows.append({
                "CreditMemoLineID": next_id(context, "CreditMemoLine"),
                "CreditMemoID": credit_memo_id,
                "SalesReturnLineID": sales_return_line_id,
                "LineNumber": line_number,
                "ItemID": int(line.ItemID),
                "Quantity": returned_quantity,
                "BaseListPrice": float(line.BaseListPrice),
                "UnitPrice": float(line.UnitPrice),
                "Discount": float(line.Discount),
                "LineTotal": line_total,
                "PriceListLineID": None if pd.isna(line.PriceListLineID) else int(line.PriceListLineID),
                "PromotionID": None if pd.isna(line.PromotionID) else int(line.PromotionID),
                "PriceOverrideApprovalID": None if pd.isna(line.PriceOverrideApprovalID) else int(line.PriceOverrideApprovalID),
                "PricingMethod": str(line.PricingMethod),
            })
            returned_quantities[shipment_line_id] = round(float(returned_quantities.get(shipment_line_id, 0.0)) + returned_quantity, 2)
            line_number += 1

        if line_number == 1:
            context.counters["SalesReturn"] -= 1
            context.counters["CreditMemo"] -= 1
            continue

        freight_credit_value = freight_credit_amount(
            invoice_subtotal=float(invoice_record["SubTotal"]),
            invoice_freight_amount=0.0 if pd.isna(invoice_record.get("FreightAmount")) else float(invoice_record["FreightAmount"]),
            returned_subtotal=subtotal,
            reason_code=reason_code,
        )
        tax_amount = money((subtotal + freight_credit_value) * context.settings.tax_rate)
        memo_rows.append({
            "CreditMemoID": credit_memo_id,
            "CreditMemoNumber": format_doc_number("CM", year, credit_memo_id),
            "CreditMemoDate": credit_memo_date.strftime("%Y-%m-%d"),
            "SalesReturnID": return_id,
            "SalesOrderID": int(invoice_record["SalesOrderID"]),
            "CustomerID": int(invoice_record["CustomerID"]),
            "OriginalSalesInvoiceID": int(sales_invoice_id),
            "SubTotal": subtotal,
            "FreightCreditAmount": freight_credit_value,
            "TaxAmount": tax_amount,
            "GrandTotal": money(subtotal + freight_credit_value + tax_amount),
            "Status": "Issued",
            "ApprovedByEmployeeID": int(invoice_rng.choice(employee_ids_for_cost_center(context, "Customer Service", credit_memo_date))),
            "ApprovedDate": credit_memo_date.strftime("%Y-%m-%d"),
        })
        already_returned_invoices.add(sales_invoice_id)

    append_rows(context, "SalesReturn", return_rows)
    append_rows(context, "SalesReturnLine", return_line_rows)
    append_rows(context, "CreditMemo", memo_rows)
    append_rows(context, "CreditMemoLine", memo_line_rows)

    inventory = getattr(context, "_o2c_shadow_inventory", None)
    if inventory is not None:
        return_warehouse_lookup = {int(row["SalesReturnID"]): int(row["WarehouseID"]) for row in return_rows}
        for row in return_line_rows:
            warehouse_id = return_warehouse_lookup.get(int(row["SalesReturnID"]))
            if warehouse_id is None:
                continue
            key = (int(row["ItemID"]), warehouse_id)
            inventory[key] = round(float(inventory.get(key, 0.0)) + float(row["QuantityReturned"]), 2)


def generate_month_customer_refunds(context: GenerationContext, year: int, month: int) -> None:
    rng = context.rng
    credit_memos = context.tables["CreditMemo"]
    if credit_memos.empty:
        refresh_o2c_statuses(context)
        return

    month_start, month_end = month_bounds(year, month)
    allocations = credit_memo_allocation_map(context)
    refunded_amounts = credit_memo_refunded_amounts(context)
    refund_rows: list[dict[str, Any]] = []

    for credit_memo in credit_memos.sort_values(["CreditMemoDate", "CreditMemoID"]).itertuples(index=False):
        refundable_amount = round(float(allocations.get(int(credit_memo.CreditMemoID), {}).get("customer_credit_amount", 0.0)) - float(refunded_amounts.get(int(credit_memo.CreditMemoID), 0.0)), 2)
        if refundable_amount <= 0:
            continue
        refund_date = pd.Timestamp(credit_memo.CreditMemoDate) + pd.Timedelta(days=int(rng.integers(2, 13)))
        if refund_date > month_end:
            continue
        if refund_date < month_start:
            refund_date = month_start + pd.Timedelta(days=int(rng.integers(0, 5)))
        if rng.random() > 0.84:
            continue
        refund_id = next_id(context, "CustomerRefund")
        refund_approvers = employee_ids_for_cost_center(context, "Administration", refund_date)
        refund_rows.append({
            "CustomerRefundID": refund_id,
            "RefundNumber": format_doc_number("RF", year, refund_id),
            "RefundDate": clamp_date_to_month(refund_date, year, month).strftime("%Y-%m-%d"),
            "CustomerID": int(credit_memo.CustomerID),
            "CreditMemoID": int(credit_memo.CreditMemoID),
            "Amount": money(refundable_amount),
            "PaymentMethod": str(rng.choice(PAYMENT_METHODS)),
            "ReferenceNumber": f"RF{refund_id:08d}",
            "ApprovedByEmployeeID": int(rng.choice(refund_approvers)),
            "ClearedDate": clamp_date_to_month(refund_date + pd.Timedelta(days=int(rng.integers(0, 4))), year, month).strftime("%Y-%m-%d"),
        })

    append_rows(context, "CustomerRefund", refund_rows)
    refresh_o2c_statuses(context)


def generate_month_sales_commission_accruals(context: GenerationContext, year: int, month: int) -> None:
    generate_sales_commission_rates(context)
    _, month_end = month_bounds(year, month)
    invoices = context.tables["SalesInvoice"]
    invoice_lines = context.tables["SalesInvoiceLine"]
    if invoices.empty or invoice_lines.empty:
        return

    existing_line_ids = set(
        context.tables["SalesCommissionAccrual"]["SalesInvoiceLineID"].dropna().astype(int).tolist()
    )
    invoice_lookup = invoices.set_index("SalesInvoiceID").to_dict("index")
    sales_order_lookup = context.tables["SalesOrder"].set_index("SalesOrderID").to_dict("index")
    customer_lookup = context.tables["Customer"].set_index("CustomerID").to_dict("index")
    revenue_type_by_line = commission_revenue_type_by_invoice_line(context)
    accrual_rows: list[dict[str, Any]] = []

    for line in invoice_lines.sort_values(["SalesInvoiceID", "LineNumber", "SalesInvoiceLineID"]).itertuples(index=False):
        sales_invoice_line_id = int(line.SalesInvoiceLineID)
        if sales_invoice_line_id in existing_line_ids:
            continue
        invoice = invoice_lookup.get(int(line.SalesInvoiceID))
        if invoice is None:
            continue
        invoice_date = pd.Timestamp(invoice["InvoiceDate"]).normalize()
        if invoice_date > month_end:
            continue
        commission_base_amount = money(float(line.LineTotal))
        if commission_base_amount <= 0:
            continue

        sales_order = sales_order_lookup[int(invoice["SalesOrderID"])]
        customer = customer_lookup[int(invoice["CustomerID"])]
        customer_segment = str(customer["CustomerSegment"])
        revenue_type = revenue_type_by_line.get(sales_invoice_line_id, "Merchandise")
        rate_segment = "Design Trade" if customer_segment == DESIGN_SERVICE_SEGMENT else customer_segment
        rate = selected_sales_commission_rate(
            context,
            revenue_type=revenue_type,
            customer_segment=rate_segment,
            event_date=invoice_date,
        )
        commission_amount = money(commission_base_amount * float(rate["RatePct"]))
        if commission_amount <= 0:
            continue

        accrual_id = next_id(context, "SalesCommissionAccrual")
        accrual_rows.append({
            "SalesCommissionAccrualID": accrual_id,
            "AccrualNumber": format_doc_number("SCAC", int(invoice_date.year), accrual_id),
            "AccrualDate": invoice_date.strftime("%Y-%m-%d"),
            "SalesInvoiceID": int(line.SalesInvoiceID),
            "SalesInvoiceLineID": sales_invoice_line_id,
            "SalesOrderID": int(invoice["SalesOrderID"]),
            "CustomerID": int(invoice["CustomerID"]),
            "SalesRepEmployeeID": int(sales_order["SalesRepEmployeeID"]),
            "SalesCommissionRateID": int(rate["SalesCommissionRateID"]),
            "RevenueType": revenue_type,
            "CustomerSegment": customer_segment,
            "CommissionBaseAmount": commission_base_amount,
            "CommissionRatePct": qty(float(rate["RatePct"]), "0.0001"),
            "CommissionAmount": commission_amount,
            "Status": "Accrued",
            "CreatedByEmployeeID": commission_accounting_approver_id(context, invoice_date),
            "CreatedDate": f"{invoice_date.strftime('%Y-%m-%d')} 12:00:00",
        })
        existing_line_ids.add(sales_invoice_line_id)

    append_rows(context, "SalesCommissionAccrual", accrual_rows)


def generate_month_sales_commission_adjustments(context: GenerationContext, year: int, month: int) -> None:
    _, month_end = month_bounds(year, month)
    credit_memos = context.tables["CreditMemo"]
    credit_memo_lines = context.tables["CreditMemoLine"]
    accruals = context.tables["SalesCommissionAccrual"]
    if credit_memos.empty or credit_memo_lines.empty or accruals.empty:
        return

    existing_credit_line_ids = set(
        context.tables["SalesCommissionAdjustment"]["CreditMemoLineID"].dropna().astype(int).tolist()
    )
    credit_lookup = credit_memos.set_index("CreditMemoID").to_dict("index")
    return_line_lookup = context.tables["SalesReturnLine"].set_index("SalesReturnLineID").to_dict("index")
    shipment_line_lookup = context.tables["ShipmentLine"].set_index("ShipmentLineID").to_dict("index")
    invoice_lines = context.tables["SalesInvoiceLine"]
    invoice_line_by_invoice_order_line: dict[tuple[int, int, int], dict[str, Any]] = {}
    for invoice_line in invoice_lines.itertuples(index=False):
        invoice_line_by_invoice_order_line[
            (int(invoice_line.SalesInvoiceID), int(invoice_line.SalesOrderLineID), int(invoice_line.ItemID))
        ] = invoice_line._asdict()
    accrual_by_invoice_line = accruals.set_index("SalesInvoiceLineID").to_dict("index")
    adjustment_rows: list[dict[str, Any]] = []

    for line in credit_memo_lines.sort_values(["CreditMemoID", "LineNumber", "CreditMemoLineID"]).itertuples(index=False):
        credit_memo_line_id = int(line.CreditMemoLineID)
        if credit_memo_line_id in existing_credit_line_ids:
            continue
        credit_memo = credit_lookup.get(int(line.CreditMemoID))
        if credit_memo is None:
            continue
        adjustment_date = pd.Timestamp(credit_memo["CreditMemoDate"]).normalize()
        if adjustment_date > month_end:
            continue
        return_line = return_line_lookup.get(int(line.SalesReturnLineID))
        if return_line is None:
            continue
        shipment_line = shipment_line_lookup.get(int(return_line["ShipmentLineID"]))
        if shipment_line is None:
            continue
        invoice_line = invoice_line_by_invoice_order_line.get(
            (
                int(credit_memo["OriginalSalesInvoiceID"]),
                int(shipment_line["SalesOrderLineID"]),
                int(line.ItemID),
            )
        )
        if invoice_line is None:
            continue
        accrual = accrual_by_invoice_line.get(int(invoice_line["SalesInvoiceLineID"]))
        if accrual is None:
            continue

        base_reduction = money(float(line.LineTotal))
        adjustment_amount = money(base_reduction * float(accrual["CommissionRatePct"]))
        if adjustment_amount <= 0:
            continue

        adjustment_id = next_id(context, "SalesCommissionAdjustment")
        adjustment_rows.append({
            "SalesCommissionAdjustmentID": adjustment_id,
            "AdjustmentNumber": format_doc_number("SCAJ", int(adjustment_date.year), adjustment_id),
            "AdjustmentDate": adjustment_date.strftime("%Y-%m-%d"),
            "SalesCommissionAccrualID": int(accrual["SalesCommissionAccrualID"]),
            "CreditMemoID": int(line.CreditMemoID),
            "CreditMemoLineID": credit_memo_line_id,
            "SalesInvoiceID": int(credit_memo["OriginalSalesInvoiceID"]),
            "SalesInvoiceLineID": int(invoice_line["SalesInvoiceLineID"]),
            "SalesOrderID": int(credit_memo["SalesOrderID"]),
            "CustomerID": int(credit_memo["CustomerID"]),
            "SalesRepEmployeeID": int(accrual["SalesRepEmployeeID"]),
            "CommissionBaseReductionAmount": base_reduction,
            "CommissionRatePct": qty(float(accrual["CommissionRatePct"]), "0.0001"),
            "CommissionAdjustmentAmount": adjustment_amount,
            "Status": "Clawback",
            "ApprovedByEmployeeID": int(credit_memo["ApprovedByEmployeeID"]),
            "ApprovedDate": str(credit_memo["ApprovedDate"]),
        })
        existing_credit_line_ids.add(credit_memo_line_id)

    append_rows(context, "SalesCommissionAdjustment", adjustment_rows)


def generate_month_sales_commission_payments(context: GenerationContext, year: int, month: int) -> None:
    accruals = context.tables["SalesCommissionAccrual"]
    if accruals.empty:
        return

    current_month_start, _ = month_bounds(year, month)
    period_start = current_month_start - pd.DateOffset(months=1)
    period_end = period_start + pd.offsets.MonthEnd(1)
    payment_date = nth_business_day(year, month, 10)
    payment_lines = context.tables["SalesCommissionPaymentLine"]
    settled_sources = {
        (str(row.SourceDocumentType), int(row.SourceDocumentID))
        for row in payment_lines.itertuples(index=False)
    } if not payment_lines.empty else set()

    source_rows: list[dict[str, Any]] = []
    accrual_candidates = accruals.copy()
    accrual_candidates["AccrualDateTS"] = pd.to_datetime(accrual_candidates["AccrualDate"], errors="coerce")
    accrual_candidates = accrual_candidates[accrual_candidates["AccrualDateTS"].le(period_end)].copy()
    for row in accrual_candidates.sort_values(["AccrualDate", "SalesCommissionAccrualID"]).itertuples(index=False):
        source_key = ("SalesCommissionAccrual", int(row.SalesCommissionAccrualID))
        if source_key in settled_sources:
            continue
        source_rows.append({
            "SourceDocumentType": "SalesCommissionAccrual",
            "SourceDocumentID": int(row.SalesCommissionAccrualID),
            "SourceLineID": int(row.SalesInvoiceLineID),
            "SalesRepEmployeeID": int(row.SalesRepEmployeeID),
            "Amount": money(float(row.CommissionAmount)),
        })

    adjustments = context.tables["SalesCommissionAdjustment"]
    if not adjustments.empty:
        adjustment_candidates = adjustments.copy()
        adjustment_candidates["AdjustmentDateTS"] = pd.to_datetime(adjustment_candidates["AdjustmentDate"], errors="coerce")
        adjustment_candidates = adjustment_candidates[adjustment_candidates["AdjustmentDateTS"].le(period_end)].copy()
        for row in adjustment_candidates.sort_values(["AdjustmentDate", "SalesCommissionAdjustmentID"]).itertuples(index=False):
            source_key = ("SalesCommissionAdjustment", int(row.SalesCommissionAdjustmentID))
            if source_key in settled_sources:
                continue
            source_rows.append({
                "SourceDocumentType": "SalesCommissionAdjustment",
                "SourceDocumentID": int(row.SalesCommissionAdjustmentID),
                "SourceLineID": int(row.CreditMemoLineID),
                "SalesRepEmployeeID": int(row.SalesRepEmployeeID),
                "Amount": -money(float(row.CommissionAdjustmentAmount)),
            })

    if not source_rows:
        return

    payment_rows: list[dict[str, Any]] = []
    payment_line_rows: list[dict[str, Any]] = []
    rng = stable_rng(context, "sales-commission-payment", year, month)
    for sales_rep_id in sorted({int(row["SalesRepEmployeeID"]) for row in source_rows}):
        rep_sources = [row for row in source_rows if int(row["SalesRepEmployeeID"]) == sales_rep_id]
        gross_accrual_amount = money(sum(float(row["Amount"]) for row in rep_sources if float(row["Amount"]) > 0))
        adjustment_amount = money(-sum(float(row["Amount"]) for row in rep_sources if float(row["Amount"]) < 0))
        net_payment_amount = money(gross_accrual_amount - adjustment_amount)
        if net_payment_amount <= 0:
            continue

        payment_id = next_id(context, "SalesCommissionPayment")
        payment_number = format_doc_number("SCPAY", int(payment_date.year), payment_id)
        approver_id = commission_accounting_approver_id(context, payment_date)
        payment_rows.append({
            "SalesCommissionPaymentID": payment_id,
            "PaymentNumber": payment_number,
            "PaymentDate": payment_date.strftime("%Y-%m-%d"),
            "SalesRepEmployeeID": sales_rep_id,
            "PeriodStartDate": period_start.strftime("%Y-%m-%d"),
            "PeriodEndDate": period_end.strftime("%Y-%m-%d"),
            "GrossAccrualAmount": gross_accrual_amount,
            "AdjustmentAmount": adjustment_amount,
            "NetPaymentAmount": net_payment_amount,
            "PaymentMethod": str(rng.choice(SALES_COMMISSION_PAYMENT_METHODS)),
            "ReferenceNumber": f"SCP{payment_id:08d}",
            "Status": "Paid",
            "ApprovedByEmployeeID": approver_id,
            "ClearedDate": next_business_day(payment_date + pd.Timedelta(days=int(rng.integers(0, 3)))).strftime("%Y-%m-%d"),
        })
        for source in rep_sources:
            payment_line_rows.append({
                "SalesCommissionPaymentLineID": next_id(context, "SalesCommissionPaymentLine"),
                "SalesCommissionPaymentID": payment_id,
                "SourceDocumentType": str(source["SourceDocumentType"]),
                "SourceDocumentID": int(source["SourceDocumentID"]),
                "SourceLineID": int(source["SourceLineID"]),
                "SalesRepEmployeeID": sales_rep_id,
                "Amount": money(float(source["Amount"])),
            })

    append_rows(context, "SalesCommissionPayment", payment_rows)
    append_rows(context, "SalesCommissionPaymentLine", payment_line_rows)


def generate_month_sales_commissions(context: GenerationContext, year: int, month: int) -> None:
    generate_month_sales_commission_accruals(context, year, month)
    generate_month_sales_commission_adjustments(context, year, month)
    generate_month_sales_commission_payments(context, year, month)


def generate_month_o2c(context: GenerationContext, year: int, month: int) -> None:
    generate_month_sales_orders(context, year, month)
    generate_month_design_service_orders(context, year, month)
    generate_month_service_time_entries(context, year, month)
