from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.settings import GenerationContext
from greenfield_dataset.utils import format_doc_number, money, next_id, qty, random_date_in_month


SEGMENT_ORDER_WEIGHTS = {
    "Strategic": 4.0,
    "Wholesale": 2.5,
    "Design Trade": 1.7,
    "Small Business": 1.0,
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

CARRIERS = ["Greenfield Fleet", "FedEx Freight", "UPS Freight", "DHL Supply Chain"]
PAYMENT_METHODS = ["ACH", "Wire Transfer", "Check", "Credit Card"]


def append_rows(context: GenerationContext, table_name: str, rows: list[dict]) -> None:
    if not rows:
        return

    new_rows = pd.DataFrame(rows, columns=TABLE_COLUMNS[table_name])
    context.tables[table_name] = pd.concat(
        [context.tables[table_name], new_rows],
        ignore_index=True,
    )


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


def sales_cost_center_id(context: GenerationContext) -> int:
    cost_centers = context.tables["CostCenter"]
    matches = cost_centers.loc[cost_centers["CostCenterName"].eq("Sales"), "CostCenterID"]
    if matches.empty:
        raise ValueError("Sales cost center is required for sales order generation.")
    return int(matches.iloc[0])


def employee_ids_for_cost_center(context: GenerationContext, cost_center_name: str) -> list[int]:
    cost_centers = context.tables["CostCenter"]
    matches = cost_centers.loc[cost_centers["CostCenterName"].eq(cost_center_name), "CostCenterID"]
    if matches.empty:
        return context.tables["Employee"]["EmployeeID"].astype(int).tolist()

    employee_ids = context.tables["Employee"].loc[
        context.tables["Employee"]["CostCenterID"].eq(int(matches.iloc[0])),
        "EmployeeID",
    ].astype(int).tolist()
    return employee_ids or context.tables["Employee"]["EmployeeID"].astype(int).tolist()


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


def return_rng(context: GenerationContext, sales_invoice_id: int) -> np.random.Generator:
    return np.random.default_rng(context.settings.random_seed + int(sales_invoice_id) * 1009)


def returned_invoice_ids(context: GenerationContext) -> set[int]:
    credit_memos = context.tables["CreditMemo"]
    if credit_memos.empty:
        return set()
    return set(credit_memos["OriginalSalesInvoiceID"].astype(int).tolist())


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


def active_sellable_items(context: GenerationContext) -> pd.DataFrame:
    items = context.tables["Item"]
    sellable = items[
        items["IsActive"].eq(1)
        & items["ListPrice"].notna()
        & items["RevenueAccountID"].notna()
    ].copy()
    if sellable.empty:
        raise ValueError("Generate active sellable items before O2C transactions.")
    return sellable


def select_customer(context: GenerationContext) -> pd.Series:
    customers = context.tables["Customer"]
    active = customers[customers["IsActive"].eq(1)].copy()
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


def opening_inventory_map(context: GenerationContext) -> dict[tuple[int, int], float]:
    warehouse_list = warehouse_ids(context)
    items = context.tables["Item"]
    inventory: dict[tuple[int, int], float] = {}
    for item in items.itertuples(index=False):
        stock_rng = np.random.default_rng(context.settings.random_seed + int(item.ItemID) * 37)
        low, high = OPENING_STOCK_RANGES.get(str(item.ItemGroup), (80, 160))
        total_qty = int(stock_rng.integers(low, high + 1))
        if len(warehouse_list) == 1:
            inventory[(int(item.ItemID), warehouse_list[0])] = float(total_qty)
            continue
        primary_index = int(stock_rng.integers(0, len(warehouse_list)))
        primary_warehouse = warehouse_list[primary_index]
        secondary = [warehouse_id for warehouse_id in warehouse_list if warehouse_id != primary_warehouse]
        primary_qty = int(round(total_qty * 0.70))
        inventory[(int(item.ItemID), primary_warehouse)] = float(primary_qty)
        for warehouse_id in secondary:
            inventory[(int(item.ItemID), warehouse_id)] = float((total_qty - primary_qty) / len(secondary))
    return inventory


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
    return {
        int(line_id): round(float(quantity), 2)
        for line_id, quantity in shipment_lines.groupby("SalesOrderLineID")["QuantityShipped"].sum().items()
    }


def shipment_line_billed_quantities(context: GenerationContext) -> dict[int, float]:
    invoice_lines = context.tables["SalesInvoiceLine"]
    if invoice_lines.empty:
        return {}
    linked_lines = invoice_lines[invoice_lines["ShipmentLineID"].notna()]
    if linked_lines.empty:
        return {}
    return {
        int(line_id): round(float(quantity), 2)
        for line_id, quantity in linked_lines.groupby("ShipmentLineID")["Quantity"].sum().items()
    }


def shipment_line_returned_quantities(context: GenerationContext) -> dict[int, float]:
    return_lines = context.tables["SalesReturnLine"]
    if return_lines.empty:
        return {}
    return {
        int(line_id): round(float(quantity), 2)
        for line_id, quantity in return_lines.groupby("ShipmentLineID")["QuantityReturned"].sum().items()
    }


def receipt_applied_amounts(context: GenerationContext) -> dict[int, float]:
    applications = context.tables["CashReceiptApplication"]
    if applications.empty:
        return {}
    return {
        int(receipt_id): round(float(amount), 2)
        for receipt_id, amount in applications.groupby("CashReceiptID")["AppliedAmount"].sum().items()
    }


def invoice_cash_application_amounts(context: GenerationContext) -> dict[int, float]:
    applications = context.tables["CashReceiptApplication"]
    if applications.empty:
        return {}
    return {
        int(invoice_id): round(float(amount), 2)
        for invoice_id, amount in applications.groupby("SalesInvoiceID")["AppliedAmount"].sum().items()
    }


def credit_memo_refunded_amounts(context: GenerationContext) -> dict[int, float]:
    refunds = context.tables["CustomerRefund"]
    if refunds.empty:
        return {}
    return {
        int(credit_memo_id): round(float(amount), 2)
        for credit_memo_id, amount in refunds.groupby("CreditMemoID")["Amount"].sum().items()
    }


def credit_memo_allocation_map(context: GenerationContext) -> dict[int, dict[str, float]]:
    credit_memos = context.tables["CreditMemo"]
    if credit_memos.empty:
        return {}

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
    cash_applied = invoice_cash_application_amounts(context)
    credit_memo_amounts = invoice_credit_memo_amounts(context)
    invoice_ids = set(cash_applied) | set(credit_memo_amounts)
    return {
        int(invoice_id): round(float(cash_applied.get(invoice_id, 0.0)) + float(credit_memo_amounts.get(invoice_id, 0.0)), 2)
        for invoice_id in invoice_ids
    }


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
    sales_orders = context.tables["SalesOrder"]
    sales_order_lines = context.tables["SalesOrderLine"]
    sales_invoices = context.tables["SalesInvoice"]
    sales_returns = context.tables["SalesReturn"]
    credit_memos = context.tables["CreditMemo"]

    shipped_by_sales_line = sales_order_line_shipped_quantities(context)
    billed_by_shipment_line = shipment_line_billed_quantities(context)
    settled_by_invoice = invoice_settled_amounts(context)
    refunded_by_credit_memo = credit_memo_refunded_amounts(context)

    billed_by_sales_line: dict[int, float] = defaultdict(float)
    shipment_lines = context.tables["ShipmentLine"]
    if not shipment_lines.empty:
        shipment_sales_line_lookup = shipment_lines.set_index("ShipmentLineID")["SalesOrderLineID"].astype(int).to_dict()
        for shipment_line_id, billed_quantity in billed_by_shipment_line.items():
            sales_line_id = shipment_sales_line_lookup.get(int(shipment_line_id))
            if sales_line_id is not None:
                billed_by_sales_line[int(sales_line_id)] += float(billed_quantity)

    if not sales_orders.empty and not sales_order_lines.empty:
        line_metrics = sales_order_lines[["SalesOrderID", "SalesOrderLineID", "Quantity"]].copy()
        line_metrics["ShippedQuantity"] = line_metrics["SalesOrderLineID"].astype(int).map(shipped_by_sales_line).fillna(0.0)
        line_metrics["BilledQuantity"] = line_metrics["SalesOrderLineID"].astype(int).map(billed_by_sales_line).fillna(0.0)
        order_summaries = (
            line_metrics.groupby("SalesOrderID")[["Quantity", "ShippedQuantity", "BilledQuantity"]]
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


def o2c_open_state(context: GenerationContext) -> dict[str, float]:
    shipped_by_sales_line = sales_order_line_shipped_quantities(context)
    open_order_quantity = 0.0
    backordered_quantity = 0.0
    for line in context.tables["SalesOrderLine"].itertuples(index=False):
        shipped = float(shipped_by_sales_line.get(int(line.SalesOrderLineID), 0.0))
        remaining = max(0.0, round(float(line.Quantity) - shipped, 2))
        open_order_quantity += remaining
        if remaining > 0 and shipped > 0:
            backordered_quantity += remaining

    unbilled_shipment_quantity = 0.0
    billed_by_shipment = shipment_line_billed_quantities(context)
    for line in context.tables["ShipmentLine"].itertuples(index=False):
        unbilled_shipment_quantity += max(0.0, round(float(line.QuantityShipped) - float(billed_by_shipment.get(int(line.ShipmentLineID), 0.0)), 2))

    settled_by_invoice = invoice_settled_amounts(context)
    open_ar_amount = 0.0
    for invoice in context.tables["SalesInvoice"].itertuples(index=False):
        open_ar_amount += max(0.0, round(float(invoice.GrandTotal) - float(settled_by_invoice.get(int(invoice.SalesInvoiceID), 0.0)), 2))

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
    }


def generate_month_sales_orders(context: GenerationContext, year: int, month: int) -> None:
    sellable_items = active_sellable_items(context)
    sales_center_id = sales_cost_center_id(context)
    rng = context.rng
    order_count = int(rng.integers(95, 126))
    if month in [3, 4, 9, 10, 11]:
        order_count = int(order_count * 1.10)

    order_rows: list[dict] = []
    line_rows: list[dict] = []
    for _ in range(order_count):
        customer = select_customer(context)
        order_id = next_id(context, "SalesOrder")
        order_date = random_date_in_month(rng, year, month)
        requested_delivery_date = order_date + pd.Timedelta(days=int(rng.integers(3, 15)))
        segment = str(customer["CustomerSegment"])
        line_min, line_max = SEGMENT_LINE_RANGES[segment]
        line_count = int(rng.integers(line_min, line_max + 1))

        order_total = 0.0
        used_item_ids: set[int] = set()
        for line_number in range(1, line_count + 1):
            item = select_sales_item(context, sellable_items, segment)
            retry_count = 0
            while int(item["ItemID"]) in used_item_ids and retry_count < 5:
                item = select_sales_item(context, sellable_items, segment)
                retry_count += 1
            used_item_ids.add(int(item["ItemID"]))

            qty_min, qty_max = SEGMENT_QUANTITY_RANGES[segment]
            quantity = qty(int(rng.integers(qty_min, qty_max + 1)))
            unit_price = money(float(item["ListPrice"]) * rng.uniform(0.97, 1.04))
            discount = qty(rng.uniform(0.00, 0.12), "0.0001")
            if segment in ["Strategic", "Wholesale"]:
                discount = qty(rng.uniform(0.04, 0.18), "0.0001")
            line_total = money(quantity * unit_price * (1 - discount))
            order_total = money(order_total + line_total)

            line_rows.append({
                "SalesOrderLineID": next_id(context, "SalesOrderLine"),
                "SalesOrderID": order_id,
                "LineNumber": line_number,
                "ItemID": int(item["ItemID"]),
                "Quantity": quantity,
                "UnitPrice": unit_price,
                "Discount": discount,
                "LineTotal": line_total,
            })

        order_rows.append({
            "SalesOrderID": order_id,
            "OrderNumber": format_doc_number("SO", year, order_id),
            "OrderDate": order_date.strftime("%Y-%m-%d"),
            "CustomerID": int(customer["CustomerID"]),
            "RequestedDeliveryDate": requested_delivery_date.strftime("%Y-%m-%d"),
            "Status": "Open",
            "SalesRepEmployeeID": int(customer["SalesRepEmployeeID"]),
            "CostCenterID": sales_center_id,
            "OrderTotal": order_total,
            "Notes": None,
        })

    append_rows(context, "SalesOrder", order_rows)
    append_rows(context, "SalesOrderLine", line_rows)


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
    warehouses = warehouse_ids(context)

    receipt_headers = (
        context.tables["GoodsReceipt"].set_index("GoodsReceiptID")[["ReceiptDate", "WarehouseID"]].to_dict("index")
        if not context.tables["GoodsReceipt"].empty
        else {}
    )
    receipt_events: dict[pd.Timestamp, list[tuple[int, int, float]]] = defaultdict(list)
    for line in context.tables["GoodsReceiptLine"].itertuples(index=False):
        receipt = receipt_headers.get(int(line.GoodsReceiptID))
        if receipt is None:
            continue
        receipt_date = pd.Timestamp(receipt["ReceiptDate"])
        if month_start <= receipt_date <= month_end:
            receipt_events[receipt_date.normalize()].append((int(line.ItemID), int(receipt["WarehouseID"]), float(line.QuantityReceived)))

    open_order_lines = order_lines.copy()
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
        for receipt_date in sorted(date for date in receipt_events if date <= shipment_date):
            if receipt_date in processed_receipt_dates:
                continue
            for item_id, warehouse_id, quantity_received in receipt_events[receipt_date]:
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
        for line in related_lines.itertuples(index=False):
            available = max(0.0, round(float(inventory.get((int(line.ItemID), chosen_warehouse_id), 0.0)), 2))
            if available <= 0:
                continue

            remaining = float(line.RemainingQuantity)
            ship_cap = remaining
            if rng.random() <= 0.22:
                ship_cap = max(1.0, qty(remaining * rng.uniform(0.40, 0.85)))
            shipped_quantity = qty(min(remaining, available, ship_cap))
            if shipped_quantity <= 0:
                continue

            inventory[(int(line.ItemID), chosen_warehouse_id)] = round(available - shipped_quantity, 2)
            item = items[int(line.ItemID)]
            shipment_line_rows.append({
                "ShipmentLineID": next_id(context, "ShipmentLine"),
                "ShipmentID": shipment_id,
                "SalesOrderLineID": int(line.SalesOrderLineID),
                "LineNumber": line_number,
                "ItemID": int(line.ItemID),
                "QuantityShipped": shipped_quantity,
                "ExtendedStandardCost": money(shipped_quantity * float(item["StandardCost"])),
            })
            line_number += 1

        if line_number == 1:
            context.counters["Shipment"] -= 1
            continue

        preferred_ship_date = pd.Timestamp(shipment_date)
        delivery_date = clamp_date_to_month(preferred_ship_date + pd.Timedelta(days=int(rng.integers(1, 6))), year, month)
        shipment_rows.append({
            "ShipmentID": shipment_id,
            "ShipmentNumber": format_doc_number("SH", year, shipment_id),
            "SalesOrderID": int(order.SalesOrderID),
            "ShipmentDate": preferred_ship_date.strftime("%Y-%m-%d"),
            "WarehouseID": chosen_warehouse_id,
            "ShippedBy": str(rng.choice(CARRIERS)),
            "TrackingNumber": f"TRK{year}{shipment_id:08d}" if rng.random() > 0.04 else None,
            "Status": "Delivered" if rng.random() > 0.08 else "In Transit",
            "DeliveryDate": delivery_date.strftime("%Y-%m-%d"),
        })

    for receipt_date in sorted(date for date in receipt_events if date not in processed_receipt_dates):
        for item_id, warehouse_id, quantity_received in receipt_events[receipt_date]:
            inventory[(item_id, warehouse_id)] = round(
                float(inventory.get((item_id, warehouse_id), 0.0)) + float(quantity_received),
                2,
            )

    append_rows(context, "Shipment", shipment_rows)
    append_rows(context, "ShipmentLine", shipment_line_rows)


def generate_month_sales_invoices(context: GenerationContext, year: int, month: int) -> None:
    shipments = context.tables["Shipment"]
    shipment_lines = context.tables["ShipmentLine"]
    if shipments.empty or shipment_lines.empty:
        return

    rng = context.rng
    _, month_end = month_bounds(year, month)
    billed_quantities = shipment_line_billed_quantities(context)
    shipment_headers = shipments.set_index("ShipmentID").to_dict("index")
    sales_orders = context.tables["SalesOrder"].set_index("SalesOrderID").to_dict("index")
    sales_order_lines = context.tables["SalesOrderLine"].set_index("SalesOrderLineID").to_dict("index")
    customers = context.tables["Customer"].set_index("CustomerID").to_dict("index")

    groups: dict[tuple[int, str], list[Any]] = defaultdict(list)
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
            (shipment_date + pd.Timedelta(days=int(rng.integers(0, 5)))) if shipment_date.year == year and shipment_date.month == month else pd.Timestamp(year=year, month=month, day=1) + pd.Timedelta(days=int(rng.integers(0, 6))),
            year,
            month,
        )
        groups[(int(shipment["SalesOrderID"]), invoice_date.strftime("%Y-%m-%d"))].append((shipment_line, remaining_quantity))

    invoice_rows: list[dict[str, Any]] = []
    invoice_line_rows: list[dict[str, Any]] = []
    for (sales_order_id, invoice_date_str), grouped_lines in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0])):
        invoice_date = pd.Timestamp(invoice_date_str)
        sales_order = sales_orders[int(sales_order_id)]
        customer = customers[int(sales_order["CustomerID"])]
        invoice_id = next_id(context, "SalesInvoice")
        due_date = invoice_date + pd.Timedelta(days=payment_term_days(str(customer["PaymentTerms"])))
        subtotal = 0.0
        line_number = 1
        for shipment_line, remaining_quantity in grouped_lines:
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
                "UnitPrice": float(sales_line["UnitPrice"]),
                "Discount": float(sales_line["Discount"]),
                "LineTotal": line_total,
            })
            line_number += 1

        tax_amount = money(subtotal * context.settings.tax_rate)
        invoice_rows.append({
            "SalesInvoiceID": invoice_id,
            "InvoiceNumber": format_doc_number("SI", year, invoice_id),
            "InvoiceDate": invoice_date.strftime("%Y-%m-%d"),
            "DueDate": due_date.strftime("%Y-%m-%d"),
            "SalesOrderID": int(sales_order_id),
            "CustomerID": int(sales_order["CustomerID"]),
            "SubTotal": subtotal,
            "TaxAmount": tax_amount,
            "GrandTotal": money(subtotal + tax_amount),
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
    recorders = employee_ids_for_cost_center(context, "Customer Service")

    receipt_rows: list[dict[str, Any]] = []
    application_rows: list[dict[str, Any]] = []

    open_orders = sales_orders[
        pd.to_datetime(sales_orders["OrderDate"]).dt.year.eq(year)
        & pd.to_datetime(sales_orders["OrderDate"]).dt.month.eq(month)
        & sales_orders["OrderTotal"].astype(float).gt(2500.0)
    ].copy()
    for order in open_orders.itertuples(index=False):
        customer = customers[int(order.CustomerID)]
        probability = 0.06 if str(customer["CustomerSegment"]) == "Strategic" else 0.03
        if rng.random() > probability:
            continue
        receipt_id = next_id(context, "CashReceipt")
        receipt_date = clamp_date_to_month(pd.Timestamp(order.OrderDate) + pd.Timedelta(days=int(rng.integers(0, 6))), year, month)
        amount = money(float(order.OrderTotal) * rng.uniform(0.12, 0.35))
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
            "RecordedByEmployeeID": int(rng.choice(recorders)),
        })

    receipts_view = pd.concat(
        [context.tables["CashReceipt"], pd.DataFrame(receipt_rows, columns=TABLE_COLUMNS["CashReceipt"])],
        ignore_index=True,
    )
    current_applied_amounts = receipt_applied_amounts(context)
    settled_amounts = invoice_settled_amounts(context)

    for receipt in receipts_view.sort_values(["ReceiptDate", "CashReceiptID"]).itertuples(index=False):
        receipt_date = pd.Timestamp(receipt.ReceiptDate)
        if receipt_date > month_end:
            continue

        remaining_receipt_amount = round(float(receipt.Amount) - float(current_applied_amounts.get(int(receipt.CashReceiptID), 0.0)), 2)
        if remaining_receipt_amount <= 0:
            continue

        customer_invoices = sales_invoices[
            sales_invoices["CustomerID"].astype(int).eq(int(receipt.CustomerID))
            & pd.to_datetime(sales_invoices["InvoiceDate"]).le(month_end)
        ].copy()
        if customer_invoices.empty:
            continue
        customer_invoices["SettledAmount"] = customer_invoices["SalesInvoiceID"].map(settled_amounts).fillna(0.0)
        customer_invoices["OpenAmount"] = (customer_invoices["GrandTotal"].astype(float) - customer_invoices["SettledAmount"].astype(float)).round(2)
        customer_invoices = customer_invoices[customer_invoices["OpenAmount"].gt(0)].sort_values(["DueDate", "InvoiceDate", "SalesInvoiceID"])

        for invoice in customer_invoices.itertuples(index=False):
            if remaining_receipt_amount <= 0:
                break
            earliest_application_date = max(month_start, receipt_date, pd.Timestamp(invoice.InvoiceDate))
            if earliest_application_date > month_end:
                continue
            apply_probability = 0.92 if receipt_date.year == year and receipt_date.month == month else 0.98
            if rng.random() > apply_probability:
                continue
            applied_amount = min(remaining_receipt_amount, float(invoice.OpenAmount))
            if applied_amount <= 0:
                continue
            application_date = clamp_date_to_month(earliest_application_date + pd.Timedelta(days=int(rng.integers(0, 3))), year, month)
            application_rows.append({
                "CashReceiptApplicationID": next_id(context, "CashReceiptApplication"),
                "CashReceiptID": int(receipt.CashReceiptID),
                "SalesInvoiceID": int(invoice.SalesInvoiceID),
                "ApplicationDate": application_date.strftime("%Y-%m-%d"),
                "AppliedAmount": money(applied_amount),
                "AppliedByEmployeeID": int(rng.choice(recorders)),
            })
            current_applied_amounts[int(receipt.CashReceiptID)] = round(float(current_applied_amounts.get(int(receipt.CashReceiptID), 0.0)) + applied_amount, 2)
            settled_amounts[int(invoice.SalesInvoiceID)] = round(float(settled_amounts.get(int(invoice.SalesInvoiceID), 0.0)) + applied_amount, 2)
            remaining_receipt_amount = round(remaining_receipt_amount - applied_amount, 2)

    open_invoices = sales_invoices.copy()
    if not open_invoices.empty:
        open_invoices["SettledAmount"] = open_invoices["SalesInvoiceID"].map(settled_amounts).fillna(0.0)
        open_invoices["OpenAmount"] = (open_invoices["GrandTotal"].astype(float) - open_invoices["SettledAmount"].astype(float)).round(2)
        open_invoices = open_invoices[
            pd.to_datetime(open_invoices["InvoiceDate"]).le(month_end)
            & open_invoices["OpenAmount"].gt(0)
        ].copy()

    for customer_id, customer_invoices in open_invoices.groupby("CustomerID"):
        customer = customers[int(customer_id)]
        oldest_due = pd.Timestamp(customer_invoices.sort_values("DueDate").iloc[0]["DueDate"])
        collection_probability = 0.62 if oldest_due >= month_start else 0.86
        if rng.random() > collection_probability:
            continue

        invoice_sample = customer_invoices.sort_values(["DueDate", "InvoiceDate", "SalesInvoiceID"]).head(
            int(rng.integers(1, min(3, len(customer_invoices)) + 1))
        )
        target_amount = float(invoice_sample["OpenAmount"].sum())
        if target_amount <= 0:
            continue
        random_mode = rng.random()
        if random_mode <= 0.18:
            receipt_amount = money(target_amount * rng.uniform(0.45, 0.85))
        elif random_mode <= 0.26:
            receipt_amount = money(target_amount * rng.uniform(1.01, 1.18))
        else:
            receipt_amount = money(target_amount)

        receipt_date = clamp_date_to_month(
            oldest_due + pd.Timedelta(days=int(rng.choice([-5, -2, 0, 3, 7, 14], p=[0.08, 0.12, 0.42, 0.18, 0.14, 0.06]))),
            year,
            month,
        )
        receipt_id = next_id(context, "CashReceipt")
        receipt_rows.append({
            "CashReceiptID": receipt_id,
            "ReceiptNumber": format_doc_number("CR", year, receipt_id),
            "ReceiptDate": receipt_date.strftime("%Y-%m-%d"),
            "CustomerID": int(customer_id),
            "SalesInvoiceID": None,
            "Amount": receipt_amount,
            "PaymentMethod": str(rng.choice(PAYMENT_METHODS)),
            "ReferenceNumber": f"AR{receipt_id:08d}",
            "DepositDate": clamp_date_to_month(receipt_date + pd.Timedelta(days=int(rng.integers(0, 3))), year, month).strftime("%Y-%m-%d"),
            "RecordedByEmployeeID": int(rng.choice(recorders)),
        })

        remaining_receipt_amount = receipt_amount
        for invoice in invoice_sample.itertuples(index=False):
            if remaining_receipt_amount <= 0:
                break
            applied_amount = min(remaining_receipt_amount, float(invoice.OpenAmount))
            if applied_amount <= 0:
                continue
            application_date = clamp_date_to_month(max(receipt_date, pd.Timestamp(invoice.InvoiceDate)) + pd.Timedelta(days=int(rng.integers(0, 3))), year, month)
            application_rows.append({
                "CashReceiptApplicationID": next_id(context, "CashReceiptApplication"),
                "CashReceiptID": receipt_id,
                "SalesInvoiceID": int(invoice.SalesInvoiceID),
                "ApplicationDate": application_date.strftime("%Y-%m-%d"),
                "AppliedAmount": money(applied_amount),
                "AppliedByEmployeeID": int(rng.choice(recorders)),
            })
            remaining_receipt_amount = round(remaining_receipt_amount - applied_amount, 2)

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
    warehouse_receivers = employee_ids_for_cost_center(context, "Warehouse")
    approvers = employee_ids_for_cost_center(context, "Customer Service")
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
            "ReceivedByEmployeeID": int(invoice_rng.choice(warehouse_receivers)),
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
                "UnitPrice": float(line.UnitPrice),
                "LineTotal": line_total,
            })
            returned_quantities[shipment_line_id] = round(float(returned_quantities.get(shipment_line_id, 0.0)) + returned_quantity, 2)
            line_number += 1

        if line_number == 1:
            context.counters["SalesReturn"] -= 1
            context.counters["CreditMemo"] -= 1
            continue

        tax_amount = money(subtotal * context.settings.tax_rate)
        memo_rows.append({
            "CreditMemoID": credit_memo_id,
            "CreditMemoNumber": format_doc_number("CM", year, credit_memo_id),
            "CreditMemoDate": credit_memo_date.strftime("%Y-%m-%d"),
            "SalesReturnID": return_id,
            "SalesOrderID": int(invoice_record["SalesOrderID"]),
            "CustomerID": int(invoice_record["CustomerID"]),
            "OriginalSalesInvoiceID": int(sales_invoice_id),
            "SubTotal": subtotal,
            "TaxAmount": tax_amount,
            "GrandTotal": money(subtotal + tax_amount),
            "Status": "Issued",
            "ApprovedByEmployeeID": int(invoice_rng.choice(approvers)),
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
    approvers = employee_ids_for_cost_center(context, "Administration")
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
        refund_rows.append({
            "CustomerRefundID": refund_id,
            "RefundNumber": format_doc_number("RF", year, refund_id),
            "RefundDate": clamp_date_to_month(refund_date, year, month).strftime("%Y-%m-%d"),
            "CustomerID": int(credit_memo.CustomerID),
            "CreditMemoID": int(credit_memo.CreditMemoID),
            "Amount": money(refundable_amount),
            "PaymentMethod": str(rng.choice(PAYMENT_METHODS)),
            "ReferenceNumber": f"RF{refund_id:08d}",
            "ApprovedByEmployeeID": int(rng.choice(approvers)),
            "ClearedDate": clamp_date_to_month(refund_date + pd.Timedelta(days=int(rng.integers(0, 4))), year, month).strftime("%Y-%m-%d"),
        })

    append_rows(context, "CustomerRefund", refund_rows)
    refresh_o2c_statuses(context)


def generate_month_o2c(context: GenerationContext, year: int, month: int) -> None:
    generate_month_sales_orders(context, year, month)
