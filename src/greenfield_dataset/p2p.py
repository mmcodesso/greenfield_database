from __future__ import annotations

from collections import defaultdict

import pandas as pd

from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.settings import GenerationContext
from greenfield_dataset.utils import format_doc_number, money, next_id, qty, random_date_in_month


ITEM_GROUP_REQUISITION_WEIGHTS = {
    "Furniture": 0.27,
    "Lighting": 0.15,
    "Textiles": 0.17,
    "Accessories": 0.18,
    "Packaging": 0.13,
    "Raw Materials": 0.10,
}

REQUISITION_COUNT_RANGE = (84, 109)
REQUISITION_APPROVAL_RATE = 0.96
PO_CONVERSION_RATE_CURRENT_MONTH = 0.90
PO_CONVERSION_RATE_AGED = 0.97
PO_BATCH_SIZE_CHOICES = [1, 2, 3, 4]
PO_BATCH_SIZE_WEIGHTS = [0.18, 0.34, 0.28, 0.20]
REQUEST_BATCH_WINDOW_DAYS = 5

RECEIPT_PROBABILITY_CURRENT_MONTH = 0.72
RECEIPT_PROBABILITY_NEXT_MONTH = 0.88
RECEIPT_PROBABILITY_LATE = 0.96

INVOICE_PROBABILITY_CURRENT_MONTH = 0.66
INVOICE_PROBABILITY_NEXT_MONTH = 0.84
INVOICE_PROBABILITY_LATE = 0.93

PAYMENT_PROBABILITY_EARLY = 0.10
PAYMENT_PROBABILITY_DUE_MONTH = 0.58
PAYMENT_PROBABILITY_LATE = 0.78
PAYMENT_PROBABILITY_VERY_LATE = 0.92

DISBURSEMENT_METHODS = ["ACH", "Check", "Wire Transfer"]

SUPPLIER_RISK_WEIGHT = {
    "Low": 1.00,
    "Medium": 0.72,
    "High": 0.32,
}

BASE_LEAD_DAYS_BY_ITEM_GROUP = {
    "Furniture": (9, 18),
    "Lighting": (7, 16),
    "Textiles": (6, 14),
    "Accessories": (5, 12),
    "Packaging": (4, 10),
    "Raw Materials": (5, 11),
}

SUPPLIER_RISK_LEAD_DAYS = {
    "Low": (0, 2),
    "Medium": (2, 4),
    "High": (4, 8),
}


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


def random_date_between(rng, start: pd.Timestamp, end: pd.Timestamp) -> pd.Timestamp:
    if end < start:
        end = start
    days = int((end - start).days)
    return start + pd.Timedelta(days=int(rng.integers(0, days + 1)))


def month_delta(anchor_date: pd.Timestamp, period_start: pd.Timestamp) -> int:
    anchor = pd.Timestamp(year=anchor_date.year, month=anchor_date.month, day=1)
    period = pd.Timestamp(year=period_start.year, month=period_start.month, day=1)
    return int((period.year - anchor.year) * 12 + (period.month - anchor.month))


def cost_center_id(context: GenerationContext, cost_center_name: str) -> int:
    cost_centers = context.tables["CostCenter"]
    matches = cost_centers.loc[cost_centers["CostCenterName"].eq(cost_center_name), "CostCenterID"]
    if matches.empty:
        raise ValueError(f"{cost_center_name} cost center is required for P2P generation.")
    return int(matches.iloc[0])


def employee_ids_for_cost_center(context: GenerationContext, cost_center_id_value: int) -> list[int]:
    employees = context.tables["Employee"]
    ids = employees.loc[employees["CostCenterID"].eq(cost_center_id_value), "EmployeeID"].astype(int).tolist()
    if not ids:
        ids = employees["EmployeeID"].astype(int).tolist()
    return ids


def approver_id(context: GenerationContext, minimum_amount: float = 0.0) -> int:
    employees = context.tables["Employee"].copy()
    eligible = employees[
        employees["AuthorizationLevel"].isin(["Manager", "Executive"])
        & (employees["MaxApprovalAmount"].astype(float) >= minimum_amount)
    ]
    if eligible.empty:
        eligible = employees[employees["AuthorizationLevel"].isin(["Manager", "Executive"])]
    if eligible.empty:
        eligible = employees
    return int(eligible.iloc[0]["EmployeeID"])


def payment_term_days(payment_terms: str) -> int:
    try:
        return int(str(payment_terms).split()[-1])
    except (ValueError, IndexError):
        return 30


def active_purchasable_items(context: GenerationContext) -> pd.DataFrame:
    items = context.tables["Item"]
    purchasable = items[
        items["IsActive"].eq(1)
        & items["InventoryAccountID"].notna()
        & items["StandardCost"].notna()
    ].copy()
    if purchasable.empty:
        raise ValueError("Generate active purchasable items before P2P transactions.")
    return purchasable


def select_requisition_item(context: GenerationContext, items: pd.DataFrame) -> pd.Series:
    weights = items["ItemGroup"].map(ITEM_GROUP_REQUISITION_WEIGHTS).fillna(0.01).astype(float)
    weights = weights / weights.sum()
    selected_index = context.rng.choice(items.index.to_numpy(), p=weights.to_numpy())
    return items.loc[selected_index]


def select_supplier(context: GenerationContext, item_group: str) -> pd.Series:
    suppliers = context.tables["Supplier"]
    approved = suppliers[suppliers["IsApproved"].eq(1)].copy()
    if approved.empty:
        raise ValueError("Generate approved suppliers before P2P transactions.")

    weights = []
    for supplier in approved.itertuples(index=False):
        category_weight = 1.0 if str(supplier.SupplierCategory) == item_group else 0.12
        risk_weight = SUPPLIER_RISK_WEIGHT.get(str(supplier.SupplierRiskRating), 0.50)
        weights.append(category_weight * risk_weight)

    weight_series = pd.Series(weights, index=approved.index, dtype=float)
    if weight_series.sum() <= 0:
        selected_index = context.rng.choice(approved.index.to_numpy())
    else:
        probabilities = (weight_series / weight_series.sum()).to_numpy()
        selected_index = context.rng.choice(approved.index.to_numpy(), p=probabilities)
    return approved.loc[selected_index]


def purchase_order_line_requisition_ids(context: GenerationContext) -> set[int]:
    po_lines = context.tables["PurchaseOrderLine"]
    if po_lines.empty or "RequisitionID" not in po_lines.columns:
        return set()
    return set(po_lines["RequisitionID"].dropna().astype(int).tolist())


def po_line_received_quantities(context: GenerationContext) -> dict[int, float]:
    receipt_lines = context.tables["GoodsReceiptLine"]
    if receipt_lines.empty:
        return {}
    return receipt_lines.groupby("POLineID")["QuantityReceived"].sum().round(2).to_dict()


def po_line_receipt_event_counts(context: GenerationContext) -> dict[int, int]:
    receipt_lines = context.tables["GoodsReceiptLine"]
    if receipt_lines.empty:
        return {}
    return receipt_lines.groupby("POLineID").size().astype(int).to_dict()


def goods_receipt_line_invoiced_quantities(context: GenerationContext) -> dict[int, float]:
    invoice_lines = context.tables["PurchaseInvoiceLine"]
    if invoice_lines.empty or "GoodsReceiptLineID" not in invoice_lines.columns:
        return {}
    matched_lines = invoice_lines[invoice_lines["GoodsReceiptLineID"].notna()]
    if matched_lines.empty:
        return {}
    return matched_lines.groupby("GoodsReceiptLineID")["Quantity"].sum().round(2).to_dict()


def goods_receipt_line_invoice_event_counts(context: GenerationContext) -> dict[int, int]:
    invoice_lines = context.tables["PurchaseInvoiceLine"]
    if invoice_lines.empty or "GoodsReceiptLineID" not in invoice_lines.columns:
        return {}
    matched_lines = invoice_lines[invoice_lines["GoodsReceiptLineID"].notna()]
    if matched_lines.empty:
        return {}
    return matched_lines.groupby("GoodsReceiptLineID").size().astype(int).to_dict()


def invoice_paid_amounts(context: GenerationContext) -> dict[int, float]:
    disbursements = context.tables["DisbursementPayment"]
    if disbursements.empty:
        return {}
    return disbursements.groupby("PurchaseInvoiceID")["Amount"].sum().round(2).to_dict()


def invoice_payment_event_counts(context: GenerationContext) -> dict[int, int]:
    disbursements = context.tables["DisbursementPayment"]
    if disbursements.empty:
        return {}
    return disbursements.groupby("PurchaseInvoiceID").size().astype(int).to_dict()


def purchase_order_line_cost_center_map(context: GenerationContext) -> dict[int, int | None]:
    po_lines = context.tables["PurchaseOrderLine"]
    if po_lines.empty:
        return {}

    requisition_cost_centers = context.tables["PurchaseRequisition"].set_index("RequisitionID")["CostCenterID"].to_dict()
    header_requisition_ids = context.tables["PurchaseOrder"].set_index("PurchaseOrderID")["RequisitionID"].to_dict()
    cost_center_map: dict[int, int | None] = {}

    for line in po_lines.itertuples(index=False):
        requisition_id_value = line.RequisitionID if "RequisitionID" in po_lines.columns else None
        if pd.isna(requisition_id_value):
            requisition_id_value = header_requisition_ids.get(int(line.PurchaseOrderID))
        if pd.isna(requisition_id_value):
            cost_center_map[int(line.POLineID)] = None
            continue
        cost_center_value = requisition_cost_centers.get(int(requisition_id_value))
        cost_center_map[int(line.POLineID)] = int(cost_center_value) if pd.notna(cost_center_value) else None

    return cost_center_map


def purchase_invoice_unique_cost_center_map(context: GenerationContext) -> dict[int, int | None]:
    invoice_line_cost_centers = purchase_invoice_line_cost_center_map(context)
    invoice_lines = context.tables["PurchaseInvoiceLine"]
    if invoice_lines.empty:
        return {}

    invoice_cost_centers: dict[int, int | None] = {}
    for invoice_id, rows in invoice_lines.groupby("PurchaseInvoiceID"):
        centers = {
            invoice_line_cost_centers.get(int(row.PILineID))
            for row in rows.itertuples(index=False)
            if invoice_line_cost_centers.get(int(row.PILineID)) is not None
        }
        invoice_cost_centers[int(invoice_id)] = next(iter(centers)) if len(centers) == 1 else None
    return invoice_cost_centers


def goods_receipt_line_cost_center_map(context: GenerationContext) -> dict[int, int | None]:
    receipt_lines = context.tables["GoodsReceiptLine"]
    if receipt_lines.empty:
        return {}

    po_line_cost_centers = purchase_order_line_cost_center_map(context)
    cost_center_map: dict[int, int | None] = {}
    for line in receipt_lines.itertuples(index=False):
        cost_center_map[int(line.GoodsReceiptLineID)] = po_line_cost_centers.get(int(line.POLineID))
    return cost_center_map


def purchase_invoice_line_cost_center_map(context: GenerationContext) -> dict[int, int | None]:
    invoice_lines = context.tables["PurchaseInvoiceLine"]
    if invoice_lines.empty:
        return {}

    po_line_cost_centers = purchase_order_line_cost_center_map(context)
    receipt_line_cost_centers = goods_receipt_line_cost_center_map(context)
    cost_center_map: dict[int, int | None] = {}
    for line in invoice_lines.itertuples(index=False):
        goods_receipt_line_id = None if pd.isna(line.GoodsReceiptLineID) else int(line.GoodsReceiptLineID)
        cost_center_value = (
            receipt_line_cost_centers.get(goods_receipt_line_id)
            if goods_receipt_line_id is not None
            else None
        )
        if cost_center_value is None:
            cost_center_value = po_line_cost_centers.get(int(line.POLineID))
        cost_center_map[int(line.PILineID)] = cost_center_value
    return cost_center_map


def purchase_invoice_line_matched_basis_map(context: GenerationContext) -> dict[int, float]:
    invoice_lines = context.tables["PurchaseInvoiceLine"]
    if invoice_lines.empty:
        return {}

    po_unit_costs = context.tables["PurchaseOrderLine"].set_index("POLineID")["UnitCost"].astype(float).to_dict()
    receipt_lines = context.tables["GoodsReceiptLine"].set_index("GoodsReceiptLineID").to_dict("index")

    matched_basis: dict[int, float] = {}
    for line in invoice_lines.itertuples(index=False):
        unit_basis = float(po_unit_costs.get(int(line.POLineID), line.UnitCost))
        goods_receipt_line_id = None if pd.isna(line.GoodsReceiptLineID) else int(line.GoodsReceiptLineID)
        if goods_receipt_line_id is not None:
            receipt_line = receipt_lines.get(goods_receipt_line_id)
            if receipt_line is not None and qty(float(receipt_line["QuantityReceived"])) > 0:
                unit_basis = float(receipt_line["ExtendedStandardCost"]) / float(receipt_line["QuantityReceived"])
        matched_basis[int(line.PILineID)] = money(float(line.Quantity) * unit_basis)

    return matched_basis


def p2p_open_state(context: GenerationContext) -> dict[str, float]:
    requisitions = context.tables["PurchaseRequisition"]
    po_lines = context.tables["PurchaseOrderLine"]
    receipt_lines = context.tables["GoodsReceiptLine"]
    invoices = context.tables["PurchaseInvoice"]

    open_requisitions = int(requisitions["Status"].eq("Approved").sum()) if not requisitions.empty else 0

    received_quantities = po_line_received_quantities(context)
    open_po_lines = 0
    open_po_quantity = 0.0
    for line in po_lines.itertuples(index=False):
        remaining = qty(float(line.Quantity) - float(received_quantities.get(int(line.POLineID), 0.0)))
        if remaining > 0:
            open_po_lines += 1
            open_po_quantity += remaining

    invoiced_quantities = goods_receipt_line_invoiced_quantities(context)
    open_receipt_lines = 0
    open_receipt_quantity = 0.0
    for line in receipt_lines.itertuples(index=False):
        remaining = qty(float(line.QuantityReceived) - float(invoiced_quantities.get(int(line.GoodsReceiptLineID), 0.0)))
        if remaining > 0:
            open_receipt_lines += 1
            open_receipt_quantity += remaining

    paid_amounts = invoice_paid_amounts(context)
    open_invoice_count = 0
    open_invoice_amount = 0.0
    for invoice in invoices.itertuples(index=False):
        outstanding = money(float(invoice.GrandTotal) - float(paid_amounts.get(int(invoice.PurchaseInvoiceID), 0.0)))
        if outstanding > 0:
            open_invoice_count += 1
            open_invoice_amount += outstanding

    return {
        "open_requisitions": float(open_requisitions),
        "open_po_lines": float(open_po_lines),
        "open_po_quantity": money(open_po_quantity),
        "open_receipt_lines": float(open_receipt_lines),
        "open_receipt_quantity": money(open_receipt_quantity),
        "open_invoice_count": float(open_invoice_count),
        "open_invoice_amount": money(open_invoice_amount),
    }


def convert_probability_for_requisition(request_date: pd.Timestamp, current_month_start: pd.Timestamp) -> float:
    return PO_CONVERSION_RATE_CURRENT_MONTH if month_delta(request_date, current_month_start) == 0 else PO_CONVERSION_RATE_AGED


def receipt_probability(expected_delivery_date: pd.Timestamp, current_month_start: pd.Timestamp, current_month_end: pd.Timestamp) -> float:
    if expected_delivery_date > current_month_end:
        return 0.0
    delay_months = month_delta(expected_delivery_date, current_month_start)
    if delay_months <= 0:
        return RECEIPT_PROBABILITY_CURRENT_MONTH
    if delay_months == 1:
        return RECEIPT_PROBABILITY_NEXT_MONTH
    return RECEIPT_PROBABILITY_LATE


def invoice_probability(receipt_date: pd.Timestamp, current_month_start: pd.Timestamp, current_month_end: pd.Timestamp) -> float:
    if receipt_date > current_month_end:
        return 0.0
    delay_months = month_delta(receipt_date, current_month_start)
    if delay_months <= 0:
        return INVOICE_PROBABILITY_CURRENT_MONTH
    if delay_months == 1:
        return INVOICE_PROBABILITY_NEXT_MONTH
    return INVOICE_PROBABILITY_LATE


def payment_probability(due_date: pd.Timestamp, current_month_start: pd.Timestamp, current_month_end: pd.Timestamp) -> float:
    if due_date > current_month_end:
        return PAYMENT_PROBABILITY_EARLY
    delay_months = month_delta(due_date, current_month_start)
    if delay_months <= 0:
        return PAYMENT_PROBABILITY_DUE_MONTH
    if delay_months == 1:
        return PAYMENT_PROBABILITY_LATE
    return PAYMENT_PROBABILITY_VERY_LATE


def choose_partial_quantity(rng, remaining_quantity: float, prior_event_count: int) -> float:
    if remaining_quantity <= 1.0 or prior_event_count >= 2:
        return qty(remaining_quantity)

    if prior_event_count == 0 and rng.random() <= 0.55:
        partial_quantity = qty(max(1.0, remaining_quantity * rng.uniform(0.35, 0.70)))
        return min(partial_quantity, qty(remaining_quantity))

    if prior_event_count == 1 and rng.random() <= 0.25:
        partial_quantity = qty(max(1.0, remaining_quantity * rng.uniform(0.45, 0.80)))
        return min(partial_quantity, qty(remaining_quantity))

    return qty(remaining_quantity)


def choose_invoice_quantity(rng, remaining_quantity: float, prior_event_count: int) -> float:
    if remaining_quantity <= 1.0 or prior_event_count >= 2:
        return qty(remaining_quantity)

    if prior_event_count == 0 and rng.random() <= 0.35:
        partial_quantity = qty(max(1.0, remaining_quantity * rng.uniform(0.40, 0.80)))
        return min(partial_quantity, qty(remaining_quantity))

    if prior_event_count == 1 and rng.random() <= 0.20:
        partial_quantity = qty(max(1.0, remaining_quantity * rng.uniform(0.50, 0.90)))
        return min(partial_quantity, qty(remaining_quantity))

    return qty(remaining_quantity)


def choose_payment_amount(rng, outstanding_amount: float, prior_event_count: int) -> float:
    if outstanding_amount <= 1000.0 or prior_event_count >= 2:
        return money(outstanding_amount)

    partial_probability = 0.28 if prior_event_count == 0 else 0.38
    if rng.random() > partial_probability:
        return money(outstanding_amount)

    partial_amount = money(outstanding_amount * rng.uniform(0.35, 0.80))
    if partial_amount >= outstanding_amount:
        return money(outstanding_amount)
    if money(outstanding_amount - partial_amount) < 50.0:
        return money(outstanding_amount)
    return partial_amount


def estimated_delivery_date_for_batch(rng, supplier: pd.Series, item_groups: list[str], order_date: pd.Timestamp) -> pd.Timestamp:
    base_days = [BASE_LEAD_DAYS_BY_ITEM_GROUP.get(item_group, (6, 14)) for item_group in item_groups]
    base_low = max(days[0] for days in base_days)
    base_high = max(days[1] for days in base_days)
    risk_low, risk_high = SUPPLIER_RISK_LEAD_DAYS.get(str(supplier["SupplierRiskRating"]), (1, 3))
    lead_days = int(rng.integers(base_low + risk_low, base_high + risk_high + 1))
    return order_date + pd.Timedelta(days=lead_days)


def update_purchase_order_statuses(context: GenerationContext) -> None:
    purchase_orders = context.tables["PurchaseOrder"]
    purchase_order_lines = context.tables["PurchaseOrderLine"]
    if purchase_orders.empty or purchase_order_lines.empty:
        return

    received_quantities = po_line_received_quantities(context)
    status_updates: dict[int, str] = {}

    for purchase_order in purchase_orders.itertuples(index=False):
        related_lines = purchase_order_lines[
            purchase_order_lines["PurchaseOrderID"].astype(int).eq(int(purchase_order.PurchaseOrderID))
        ]
        if related_lines.empty:
            continue

        received_total = 0.0
        all_fully_received = True
        for line in related_lines.itertuples(index=False):
            received_quantity = float(received_quantities.get(int(line.POLineID), 0.0))
            received_total += received_quantity
            if qty(received_quantity) < qty(float(line.Quantity)):
                all_fully_received = False

        if qty(received_total) <= 0:
            status_updates[int(purchase_order.PurchaseOrderID)] = "Open"
        elif all_fully_received:
            status_updates[int(purchase_order.PurchaseOrderID)] = "Received"
        else:
            status_updates[int(purchase_order.PurchaseOrderID)] = "Partially Received"

    for purchase_order_id, status in status_updates.items():
        mask = context.tables["PurchaseOrder"]["PurchaseOrderID"].astype(int).eq(purchase_order_id)
        context.tables["PurchaseOrder"].loc[mask, "Status"] = status


def update_purchase_invoice_statuses(context: GenerationContext) -> None:
    invoices = context.tables["PurchaseInvoice"]
    if invoices.empty:
        return

    paid_amounts = invoice_paid_amounts(context)
    for invoice in invoices.itertuples(index=False):
        paid_amount = float(paid_amounts.get(int(invoice.PurchaseInvoiceID), 0.0))
        outstanding_amount = money(float(invoice.GrandTotal) - paid_amount)
        if paid_amount <= 0:
            status = "Approved"
        elif outstanding_amount <= 0:
            status = "Paid"
        else:
            status = "Partially Paid"
        mask = context.tables["PurchaseInvoice"]["PurchaseInvoiceID"].astype(int).eq(int(invoice.PurchaseInvoiceID))
        context.tables["PurchaseInvoice"].loc[mask, "Status"] = status


def generate_month_requisitions(context: GenerationContext, year: int, month: int) -> None:
    rng = context.rng
    items = active_purchasable_items(context)
    warehouse_id = cost_center_id(context, "Warehouse")
    purchasing_id = cost_center_id(context, "Purchasing")
    administration_id = cost_center_id(context, "Administration")
    cost_center_choices = [warehouse_id, purchasing_id, administration_id]
    cost_center_weights = [0.55, 0.30, 0.15]
    requisition_count = int(rng.integers(*REQUISITION_COUNT_RANGE))

    rows: list[dict] = []
    for _ in range(requisition_count):
        item = select_requisition_item(context, items)
        cost_center = int(rng.choice(cost_center_choices, p=cost_center_weights))
        requestors = employee_ids_for_cost_center(context, cost_center)
        request_date = random_date_in_month(rng, year, month)
        quantity_range = (16, 95) if item["ItemGroup"] in ["Packaging", "Raw Materials"] else (4, 30)
        quantity = qty(int(rng.integers(*quantity_range)))
        estimated_unit_cost = money(float(item["StandardCost"]) * rng.uniform(0.96, 1.06))
        estimated_total = quantity * estimated_unit_cost
        approved = rng.random() <= REQUISITION_APPROVAL_RATE
        requisition_id = next_id(context, "PurchaseRequisition")

        rows.append({
            "RequisitionID": requisition_id,
            "RequisitionNumber": format_doc_number("PR", year, requisition_id),
            "RequestDate": request_date.strftime("%Y-%m-%d"),
            "RequestedByEmployeeID": int(rng.choice(requestors)),
            "CostCenterID": cost_center,
            "ItemID": int(item["ItemID"]),
            "Quantity": quantity,
            "EstimatedUnitCost": estimated_unit_cost,
            "Justification": f"Monthly replenishment for {item['ItemGroup']}",
            "ApprovedByEmployeeID": approver_id(context, estimated_total) if approved else None,
            "ApprovedDate": (
                request_date + pd.Timedelta(days=int(rng.integers(0, 3)))
            ).strftime("%Y-%m-%d") if approved else None,
            "Status": "Approved" if approved else "Pending",
        })

    append_rows(context, "PurchaseRequisition", rows)


def generate_month_purchase_orders(context: GenerationContext, year: int, month: int) -> None:
    rng = context.rng
    month_start, month_end = month_bounds(year, month)
    requisitions = context.tables["PurchaseRequisition"]
    if requisitions.empty:
        return

    existing_line_requisition_ids = purchase_order_line_requisition_ids(context)
    candidates = requisitions[
        requisitions["Status"].eq("Approved")
        & pd.to_datetime(requisitions["RequestDate"]).le(month_end)
        & ~requisitions["RequisitionID"].astype(int).isin(existing_line_requisition_ids)
    ].copy()
    if candidates.empty:
        return

    item_map = context.tables["Item"].set_index("ItemID").to_dict("index")
    purchasing_agents = employee_ids_for_cost_center(context, cost_center_id(context, "Purchasing"))

    prepared_requisitions: list[dict] = []
    for requisition in candidates.sort_values(["RequestDate", "RequisitionID"]).itertuples(index=False):
        request_date = pd.Timestamp(requisition.RequestDate)
        if rng.random() > convert_probability_for_requisition(request_date, month_start):
            continue

        item = item_map[int(requisition.ItemID)]
        supplier = select_supplier(context, str(item["ItemGroup"]))
        window_start = pd.Timestamp(
            year=request_date.year,
            month=request_date.month,
            day=((request_date.day - 1) // REQUEST_BATCH_WINDOW_DAYS) * REQUEST_BATCH_WINDOW_DAYS + 1,
        )
        prepared_requisitions.append({
            "requisition": requisition,
            "item": item,
            "supplier": supplier,
            "batch_key": (int(supplier["SupplierID"]), int(requisition.CostCenterID), window_start.strftime("%Y-%m-%d")),
        })

    if not prepared_requisitions:
        return

    grouped_requisitions: dict[tuple[int, int, str], list[dict]] = defaultdict(list)
    for prepared in prepared_requisitions:
        grouped_requisitions[prepared["batch_key"]].append(prepared)

    po_rows: list[dict] = []
    po_line_rows: list[dict] = []
    converted_requisition_ids: list[int] = []

    for _, grouped in sorted(grouped_requisitions.items(), key=lambda entry: entry[0]):
        index = 0
        while index < len(grouped):
            desired_batch_size = int(rng.choice(PO_BATCH_SIZE_CHOICES, p=PO_BATCH_SIZE_WEIGHTS))
            batch = grouped[index: index + desired_batch_size]
            if not batch:
                break

            supplier = batch[0]["supplier"]
            request_dates = [pd.Timestamp(entry["requisition"].RequestDate) for entry in batch]
            lower_bound = max(month_start, max(request_dates))
            upper_bound = min(month_end, lower_bound + pd.Timedelta(days=4))
            order_date = random_date_between(rng, lower_bound, upper_bound)
            expected_delivery_date = estimated_delivery_date_for_batch(
                rng,
                supplier,
                [str(entry["item"]["ItemGroup"]) for entry in batch],
                order_date,
            )

            purchase_order_id = next_id(context, "PurchaseOrder")
            order_total = 0.0
            requisition_ids_in_batch: set[int] = set()

            for line_number, entry in enumerate(batch, start=1):
                requisition = entry["requisition"]
                item = entry["item"]
                unit_cost = money(float(requisition.EstimatedUnitCost) * rng.uniform(0.97, 1.04))
                line_total = money(float(requisition.Quantity) * unit_cost)
                order_total = money(order_total + line_total)
                requisition_id_value = int(requisition.RequisitionID)
                requisition_ids_in_batch.add(requisition_id_value)

                po_line_rows.append({
                    "POLineID": next_id(context, "PurchaseOrderLine"),
                    "PurchaseOrderID": purchase_order_id,
                    "RequisitionID": requisition_id_value,
                    "LineNumber": line_number,
                    "ItemID": int(requisition.ItemID),
                    "Quantity": float(requisition.Quantity),
                    "UnitCost": unit_cost,
                    "LineTotal": line_total,
                })
                converted_requisition_ids.append(requisition_id_value)

            po_rows.append({
                "PurchaseOrderID": purchase_order_id,
                "PONumber": format_doc_number("PO", year, purchase_order_id),
                "OrderDate": order_date.strftime("%Y-%m-%d"),
                "SupplierID": int(supplier["SupplierID"]),
                "RequisitionID": next(iter(requisition_ids_in_batch)) if len(requisition_ids_in_batch) == 1 else None,
                "ExpectedDeliveryDate": expected_delivery_date.strftime("%Y-%m-%d"),
                "Status": "Open",
                "CreatedByEmployeeID": int(rng.choice(purchasing_agents)),
                "ApprovedByEmployeeID": approver_id(context, order_total),
                "OrderTotal": order_total,
            })
            index += len(batch)

    append_rows(context, "PurchaseOrder", po_rows)
    append_rows(context, "PurchaseOrderLine", po_line_rows)

    if converted_requisition_ids:
        mask = context.tables["PurchaseRequisition"]["RequisitionID"].astype(int).isin(converted_requisition_ids)
        context.tables["PurchaseRequisition"].loc[mask, "Status"] = "Converted to PO"


def generate_month_goods_receipts(context: GenerationContext, year: int, month: int) -> None:
    rng = context.rng
    month_start, month_end = month_bounds(year, month)
    purchase_orders = context.tables["PurchaseOrder"]
    purchase_order_lines = context.tables["PurchaseOrderLine"]
    warehouses = context.tables["Warehouse"]
    if purchase_orders.empty or purchase_order_lines.empty:
        return
    if warehouses.empty:
        raise ValueError("Generate warehouses before goods receipts.")

    warehouse_ids = warehouses["WarehouseID"].astype(int).tolist()
    receivers = employee_ids_for_cost_center(context, cost_center_id(context, "Warehouse"))
    received_quantities = po_line_received_quantities(context)
    receipt_event_counts = po_line_receipt_event_counts(context)

    merged_lines = purchase_order_lines.merge(
        purchase_orders[["PurchaseOrderID", "OrderDate", "ExpectedDeliveryDate"]],
        on="PurchaseOrderID",
        how="left",
    )
    merged_lines = merged_lines[
        pd.to_datetime(merged_lines["OrderDate"]).le(month_end)
    ].sort_values(["ExpectedDeliveryDate", "PurchaseOrderID", "POLineID"])
    if merged_lines.empty:
        return

    receipt_headers: dict[tuple[int, str], dict[str, object]] = {}
    header_partial_flags: dict[tuple[int, str], bool] = {}
    receipt_line_rows: list[dict] = []

    for line in merged_lines.itertuples(index=False):
        remaining_quantity = qty(float(line.Quantity) - float(received_quantities.get(int(line.POLineID), 0.0)))
        if remaining_quantity <= 0:
            continue

        expected_delivery_date = pd.Timestamp(line.ExpectedDeliveryDate)
        probability = receipt_probability(expected_delivery_date, month_start, month_end)
        if probability <= 0 or rng.random() > probability:
            continue

        prior_event_count = int(receipt_event_counts.get(int(line.POLineID), 0))
        quantity_received = choose_partial_quantity(rng, remaining_quantity, prior_event_count)
        if quantity_received <= 0:
            continue

        receipt_date = random_date_between(rng, max(month_start, expected_delivery_date), month_end)
        header_key = (int(line.PurchaseOrderID), receipt_date.strftime("%Y-%m-%d"))
        if header_key not in receipt_headers:
            goods_receipt_id = next_id(context, "GoodsReceipt")
            receipt_headers[header_key] = {
                "GoodsReceiptID": goods_receipt_id,
                "ReceiptNumber": format_doc_number("GR", year, goods_receipt_id),
                "ReceiptDate": receipt_date.strftime("%Y-%m-%d"),
                "PurchaseOrderID": int(line.PurchaseOrderID),
                "WarehouseID": int(rng.choice(warehouse_ids)),
                "ReceivedByEmployeeID": int(rng.choice(receivers)),
                "Status": "Received",
                "_next_line_number": 1,
            }
            header_partial_flags[header_key] = False

        header = receipt_headers[header_key]
        line_number = int(header["_next_line_number"])
        header["_next_line_number"] = line_number + 1
        if qty(quantity_received) < qty(remaining_quantity):
            header_partial_flags[header_key] = True

        receipt_line_rows.append({
            "GoodsReceiptLineID": next_id(context, "GoodsReceiptLine"),
            "GoodsReceiptID": int(header["GoodsReceiptID"]),
            "POLineID": int(line.POLineID),
            "LineNumber": line_number,
            "ItemID": int(line.ItemID),
            "QuantityReceived": quantity_received,
            "ExtendedStandardCost": money(quantity_received * float(line.UnitCost)),
        })

    if not receipt_line_rows:
        return

    receipt_rows = []
    for key in sorted(receipt_headers):
        header = dict(receipt_headers[key])
        header["Status"] = "Partially Received" if header_partial_flags[key] else "Received"
        header.pop("_next_line_number", None)
        receipt_rows.append(header)

    append_rows(context, "GoodsReceipt", receipt_rows)
    append_rows(context, "GoodsReceiptLine", receipt_line_rows)
    update_purchase_order_statuses(context)


def generate_month_purchase_invoices(context: GenerationContext, year: int, month: int) -> None:
    rng = context.rng
    month_start, month_end = month_bounds(year, month)
    goods_receipts = context.tables["GoodsReceipt"]
    goods_receipt_lines = context.tables["GoodsReceiptLine"]
    purchase_orders = context.tables["PurchaseOrder"]
    purchase_order_lines = context.tables["PurchaseOrderLine"]
    suppliers = context.tables["Supplier"]
    if goods_receipts.empty or goods_receipt_lines.empty:
        return

    invoiced_quantities = goods_receipt_line_invoiced_quantities(context)
    invoice_event_counts = goods_receipt_line_invoice_event_counts(context)

    receipt_line_frame = goods_receipt_lines.merge(
        goods_receipts[["GoodsReceiptID", "PurchaseOrderID", "ReceiptDate"]],
        on="GoodsReceiptID",
        how="left",
    ).merge(
        purchase_order_lines[["POLineID", "ItemID", "UnitCost"]],
        on=["POLineID", "ItemID"],
        how="left",
    ).merge(
        purchase_orders[["PurchaseOrderID", "SupplierID"]],
        on="PurchaseOrderID",
        how="left",
    ).sort_values(["ReceiptDate", "PurchaseOrderID", "GoodsReceiptLineID"])
    receipt_line_frame = receipt_line_frame[pd.to_datetime(receipt_line_frame["ReceiptDate"]).le(month_end)]
    if receipt_line_frame.empty:
        return

    supplier_lookup = suppliers.set_index("SupplierID").to_dict("index")
    invoice_headers: dict[tuple[int, str], dict[str, object]] = {}
    invoice_line_rows: list[dict] = []

    for receipt_line in receipt_line_frame.itertuples(index=False):
        remaining_quantity = qty(
            float(receipt_line.QuantityReceived)
            - float(invoiced_quantities.get(int(receipt_line.GoodsReceiptLineID), 0.0))
        )
        if remaining_quantity <= 0:
            continue

        receipt_date = pd.Timestamp(receipt_line.ReceiptDate)
        probability = invoice_probability(receipt_date, month_start, month_end)
        if probability <= 0 or rng.random() > probability:
            continue

        prior_event_count = int(invoice_event_counts.get(int(receipt_line.GoodsReceiptLineID), 0))
        quantity_invoiced = choose_invoice_quantity(rng, remaining_quantity, prior_event_count)
        if quantity_invoiced <= 0:
            continue

        invoice_date = random_date_between(rng, max(month_start, receipt_date), month_end)
        header_key = (int(receipt_line.PurchaseOrderID), invoice_date.strftime("%Y-%m-%d"))
        if header_key not in invoice_headers:
            purchase_invoice_id = next_id(context, "PurchaseInvoice")
            supplier = supplier_lookup[int(receipt_line.SupplierID)]
            received_date = min(invoice_date + pd.Timedelta(days=int(rng.integers(0, 3))), month_end)
            due_date = invoice_date + pd.Timedelta(days=payment_term_days(str(supplier["PaymentTerms"])))
            invoice_headers[header_key] = {
                "PurchaseInvoiceID": purchase_invoice_id,
                "InvoiceNumber": f"V{int(receipt_line.SupplierID):04d}-{year}-{purchase_invoice_id:06d}",
                "InvoiceDate": invoice_date.strftime("%Y-%m-%d"),
                "ReceivedDate": received_date.strftime("%Y-%m-%d"),
                "DueDate": due_date.strftime("%Y-%m-%d"),
                "PurchaseOrderID": int(receipt_line.PurchaseOrderID),
                "SupplierID": int(receipt_line.SupplierID),
                "Status": "Approved",
                "ApprovedByEmployeeID": None,
                "ApprovedDate": received_date.strftime("%Y-%m-%d"),
                "_next_line_number": 1,
                "_sub_total": 0.0,
                "_tax_applicable": rng.random() <= 0.20,
            }

        header = invoice_headers[header_key]
        line_number = int(header["_next_line_number"])
        header["_next_line_number"] = line_number + 1
        unit_cost = money(float(receipt_line.UnitCost) * rng.uniform(0.985, 1.025))
        line_total = money(quantity_invoiced * unit_cost)
        header["_sub_total"] = money(float(header["_sub_total"]) + line_total)

        invoice_line_rows.append({
            "PILineID": next_id(context, "PurchaseInvoiceLine"),
            "PurchaseInvoiceID": int(header["PurchaseInvoiceID"]),
            "POLineID": int(receipt_line.POLineID),
            "GoodsReceiptLineID": int(receipt_line.GoodsReceiptLineID),
            "LineNumber": line_number,
            "ItemID": int(receipt_line.ItemID),
            "Quantity": quantity_invoiced,
            "UnitCost": unit_cost,
            "LineTotal": line_total,
        })

    if not invoice_line_rows:
        return

    invoice_rows = []
    for key in sorted(invoice_headers):
        header = dict(invoice_headers[key])
        subtotal = money(float(header.pop("_sub_total")))
        tax_applicable = bool(header.pop("_tax_applicable"))
        header.pop("_next_line_number", None)
        tax_amount = money(subtotal * 0.015) if tax_applicable else 0.0
        grand_total = money(subtotal + tax_amount)
        header["SubTotal"] = subtotal
        header["TaxAmount"] = tax_amount
        header["GrandTotal"] = grand_total
        header["ApprovedByEmployeeID"] = approver_id(context, grand_total)
        invoice_rows.append(header)

    append_rows(context, "PurchaseInvoice", invoice_rows)
    append_rows(context, "PurchaseInvoiceLine", invoice_line_rows)
    update_purchase_invoice_statuses(context)


def generate_month_disbursements(context: GenerationContext, year: int, month: int) -> None:
    rng = context.rng
    month_start, month_end = month_bounds(year, month)
    invoices = context.tables["PurchaseInvoice"]
    if invoices.empty:
        return

    paid_amounts = invoice_paid_amounts(context)
    payment_event_counts = invoice_payment_event_counts(context)
    candidates = invoices[pd.to_datetime(invoices["InvoiceDate"]).le(month_end)].copy()
    if candidates.empty:
        return

    payment_rows: list[dict] = []
    for invoice in candidates.sort_values(["DueDate", "PurchaseInvoiceID"]).itertuples(index=False):
        outstanding_amount = money(float(invoice.GrandTotal) - float(paid_amounts.get(int(invoice.PurchaseInvoiceID), 0.0)))
        if outstanding_amount <= 0:
            continue

        probability = payment_probability(pd.Timestamp(invoice.DueDate), month_start, month_end)
        if rng.random() > probability:
            continue

        amount = choose_payment_amount(rng, outstanding_amount, int(payment_event_counts.get(int(invoice.PurchaseInvoiceID), 0)))
        if amount <= 0:
            continue

        due_date = pd.Timestamp(invoice.DueDate)
        lower_bound = max(month_start, due_date - pd.Timedelta(days=5))
        upper_bound = min(month_end, due_date + pd.Timedelta(days=10))
        payment_date = random_date_between(rng, lower_bound, upper_bound)
        disbursement_id = next_id(context, "DisbursementPayment")
        payment_method = str(rng.choice(DISBURSEMENT_METHODS, p=[0.60, 0.30, 0.10]))
        payment_rows.append({
            "DisbursementID": disbursement_id,
            "PaymentNumber": format_doc_number("DP", year, disbursement_id),
            "PaymentDate": payment_date.strftime("%Y-%m-%d"),
            "SupplierID": int(invoice.SupplierID),
            "PurchaseInvoiceID": int(invoice.PurchaseInvoiceID),
            "Amount": amount,
            "PaymentMethod": payment_method,
            "CheckNumber": f"CHK{disbursement_id:07d}" if payment_method == "Check" else None,
            "ApprovedByEmployeeID": approver_id(context, amount),
            "ClearedDate": (payment_date + pd.Timedelta(days=int(rng.integers(1, 5)))).strftime("%Y-%m-%d"),
        })

    append_rows(context, "DisbursementPayment", payment_rows)
    update_purchase_invoice_statuses(context)


def generate_month_p2p(context: GenerationContext, year: int, month: int) -> None:
    generate_month_requisitions(context, year, month)
    generate_month_purchase_orders(context, year, month)
