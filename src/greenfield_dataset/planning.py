from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from greenfield_dataset.master_data import approver_employee_id, current_role_employee_id, eligible_item_mask
from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.settings import GenerationContext
from greenfield_dataset.utils import money, next_id, qty


OPENING_STOCK_RANGES = {
    "Furniture": (45, 95),
    "Lighting": (90, 160),
    "Textiles": (120, 220),
    "Accessories": (140, 260),
    "Packaging": (180, 340),
    "Raw Materials": (220, 420),
}

WAREHOUSE_FORECAST_SHARE_BY_RANK = [0.58, 0.27, 0.15]
LIFECYCLE_DEMAND_MULTIPLIER = {"Core": 1.0, "Seasonal": 1.18, "Discontinued": 0.0}
ITEM_GROUP_WEEKLY_BASE = {
    "Furniture": 8.0,
    "Lighting": 12.0,
    "Textiles": 14.0,
    "Accessories": 18.0,
}
SEASONAL_MONTH_MULTIPLIER = {
    1: 0.90,
    2: 0.92,
    3: 1.02,
    4: 1.06,
    5: 1.08,
    6: 1.04,
    7: 0.96,
    8: 0.98,
    9: 1.08,
    10: 1.14,
    11: 1.22,
    12: 1.16,
}
LEAD_TIME_DEFAULTS = {
    "Furniture": 12,
    "Lighting": 10,
    "Textiles": 9,
    "Accessories": 8,
    "Packaging": 7,
    "Raw Materials": 9,
}


def append_rows(context: GenerationContext, table_name: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    new_rows = pd.DataFrame(rows, columns=TABLE_COLUMNS[table_name])
    context.tables[table_name] = pd.concat([context.tables[table_name], new_rows], ignore_index=True)
    invalidate_planning_caches(context, table_name)


def drop_context_attributes(context: GenerationContext, attribute_names: list[str]) -> None:
    for attribute_name in attribute_names:
        if hasattr(context, attribute_name):
            delattr(context, attribute_name)


def invalidate_planning_caches(context: GenerationContext, table_name: str) -> None:
    cache_map = {
        "DemandForecast": [
            "_planning_monthly_forecast_targets_cache",
            "_planning_weekly_forecast_map_cache",
        ],
        "InventoryPolicy": ["_planning_active_policy_lookup_cache"],
        "SupplyPlanRecommendation": ["_planning_recommendation_lookup_cache"],
        "MaterialRequirementPlan": [],
        "RoughCutCapacityPlan": [],
        "PurchaseRequisition": ["_planning_recommendation_lookup_cache"],
        "WorkOrder": ["_planning_recommendation_lookup_cache"],
    }
    drop_context_attributes(context, cache_map.get(table_name, []))


def month_bounds(year: int, month: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(year=year, month=month, day=1)
    end = start + pd.offsets.MonthEnd(1)
    return start, end


def week_start(value: pd.Timestamp | str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value).normalize()
    return timestamp - pd.Timedelta(days=int(timestamp.weekday()))


def week_end(value: pd.Timestamp | str) -> pd.Timestamp:
    return week_start(value) + pd.Timedelta(days=6)


def fiscal_bounds(context: GenerationContext) -> tuple[pd.Timestamp, pd.Timestamp]:
    return pd.Timestamp(context.settings.fiscal_year_start), pd.Timestamp(context.settings.fiscal_year_end)


def warehouse_ids(context: GenerationContext) -> list[int]:
    warehouses = context.tables["Warehouse"]
    if warehouses.empty:
        return []
    return sorted(warehouses["WarehouseID"].astype(int).tolist())


def opening_inventory_map(context: GenerationContext) -> dict[tuple[int, int], float]:
    cached = getattr(context, "_planning_opening_inventory_cache", None)
    if cached is not None:
        return dict(cached)

    warehouse_list = warehouse_ids(context)
    if not warehouse_list:
        return {}

    items = context.tables["Item"][context.tables["Item"]["InventoryAccountID"].notna()].copy()
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
            inventory[(int(item.ItemID), warehouse_id)] = float((total_qty - primary_qty) / max(len(secondary), 1))

    setattr(context, "_planning_opening_inventory_cache", dict(inventory))
    return inventory


def planning_items(context: GenerationContext) -> pd.DataFrame:
    items = context.tables["Item"]
    if items.empty:
        return items.head(0).copy()
    return items[
        items["InventoryAccountID"].notna()
        & items["ItemGroup"].ne("Services")
    ].copy()


def active_sellable_planning_items(context: GenerationContext) -> pd.DataFrame:
    items = context.tables["Item"]
    if items.empty:
        return items.head(0).copy()
    return items[
        items["IsActive"].astype(int).eq(1)
        & items["LaunchDate"].notna()
        & items["RevenueAccountID"].notna()
        & items["ListPrice"].notna()
    ].copy()


def primary_warehouse_rank(context: GenerationContext, item_id: int) -> list[int]:
    warehouses = warehouse_ids(context)
    if not warehouses:
        return []
    return sorted(
        warehouses,
        key=lambda warehouse_id: ((int(item_id) + int(warehouse_id)) % len(warehouses), int(warehouse_id)),
    )


def forecast_planner_id(context: GenerationContext, supply_mode: str, event_date: pd.Timestamp) -> int:
    if str(supply_mode) == "Manufactured":
        for title in ["Production Planner", "Production Manager"]:
            employee_id = current_role_employee_id(context, title)
            if employee_id is not None:
                return int(employee_id)
        return approver_employee_id(
            context,
            event_date,
            preferred_titles=["Production Manager", "Chief Financial Officer"],
            fallback_cost_center_name="Manufacturing",
        )
    for title in ["Buyer", "Purchasing Manager", "Procurement Analyst"]:
        employee_id = current_role_employee_id(context, title)
        if employee_id is not None:
            return int(employee_id)
    return approver_employee_id(
        context,
        event_date,
        preferred_titles=["Purchasing Manager", "Chief Financial Officer"],
        fallback_cost_center_name="Purchasing",
    )


def forecast_approver_id(context: GenerationContext, supply_mode: str, event_date: pd.Timestamp) -> int:
    if str(supply_mode) == "Manufactured":
        return approver_employee_id(
            context,
            event_date,
            preferred_titles=["Production Manager", "Chief Financial Officer"],
            fallback_cost_center_name="Manufacturing",
        )
    return approver_employee_id(
        context,
        event_date,
        preferred_titles=["Purchasing Manager", "Chief Financial Officer", "Controller"],
        fallback_cost_center_name="Purchasing",
    )


def week_starts_in_fiscal_range(context: GenerationContext) -> list[pd.Timestamp]:
    cached = getattr(context, "_planning_week_starts_cache", None)
    if cached is not None:
        return list(cached)

    fiscal_start, fiscal_end = fiscal_bounds(context)
    current = week_start(fiscal_start)
    week_starts: list[pd.Timestamp] = []
    while current <= fiscal_end:
        week_starts.append(current)
        current = current + pd.Timedelta(days=7)

    setattr(context, "_planning_week_starts_cache", list(week_starts))
    return week_starts


def first_forecast_week_start(launch_date: pd.Timestamp | str) -> pd.Timestamp:
    launch_ts = pd.Timestamp(launch_date).normalize()
    launch_week = week_start(launch_ts)
    if int(launch_ts.weekday()) == 0:
        return launch_week
    return launch_week + pd.Timedelta(days=7)


def active_policy_lookup(context: GenerationContext) -> dict[tuple[int, int], dict[str, Any]]:
    cached = getattr(context, "_planning_active_policy_lookup_cache", None)
    if cached is not None:
        return cached

    policies = context.tables["InventoryPolicy"]
    lookup: dict[tuple[int, int], dict[str, Any]] = {}
    if not policies.empty:
        active = policies[policies["IsActive"].astype(int).eq(1)]
        for row in active.itertuples(index=False):
            lookup[(int(row.ItemID), int(row.WarehouseID))] = row._asdict()

    setattr(context, "_planning_active_policy_lookup_cache", lookup)
    return lookup


def weekly_forecast_map(context: GenerationContext) -> dict[tuple[str, int, int], float]:
    cached = getattr(context, "_planning_weekly_forecast_map_cache", None)
    if cached is not None:
        return cached

    forecasts = context.tables["DemandForecast"]
    lookup: dict[tuple[str, int, int], float] = {}
    if not forecasts.empty:
        for row in forecasts.itertuples(index=False):
            key = (str(row.ForecastWeekStartDate), int(row.ItemID), int(row.WarehouseID))
            lookup[key] = float(row.ForecastQuantity)

    setattr(context, "_planning_weekly_forecast_map_cache", lookup)
    return lookup


def monthly_forecast_targets(context: GenerationContext, year: int, month: int) -> dict[int, float]:
    cached = getattr(context, "_planning_monthly_forecast_targets_cache", None)
    if cached is None:
        cached = {}
    cache_key = (int(year), int(month))
    if cache_key in cached:
        return dict(cached[cache_key])

    forecasts = context.tables["DemandForecast"]
    if forecasts.empty:
        cached[cache_key] = {}
        setattr(context, "_planning_monthly_forecast_targets_cache", cached)
        return {}

    month_start, month_end = month_bounds(year, month)
    rows = forecasts[
        pd.to_datetime(forecasts["ForecastWeekStartDate"]).le(month_end)
        & pd.to_datetime(forecasts["ForecastWeekEndDate"]).ge(month_start)
    ].copy()
    if rows.empty:
        cached[cache_key] = {}
        setattr(context, "_planning_monthly_forecast_targets_cache", cached)
        return {}

    targets = rows.groupby("ItemID")["ForecastQuantity"].sum().round(2).to_dict()
    normalized = {int(item_id): float(quantity) for item_id, quantity in targets.items() if float(quantity) > 0}
    cached[cache_key] = normalized
    setattr(context, "_planning_monthly_forecast_targets_cache", cached)
    return dict(normalized)


def inventory_position_as_of(context: GenerationContext, as_of_date: pd.Timestamp) -> dict[tuple[int, int], float]:
    cache = getattr(context, "_planning_inventory_position_cache", None)
    cache_key = str(pd.Timestamp(as_of_date).normalize().date())
    if cache is not None and cache_key in cache:
        return dict(cache[cache_key])

    position = opening_inventory_map(context)

    if not context.tables["GoodsReceipt"].empty and not context.tables["GoodsReceiptLine"].empty:
        headers = context.tables["GoodsReceipt"][["GoodsReceiptID", "ReceiptDate", "WarehouseID"]].copy()
        headers["ReceiptDateTS"] = pd.to_datetime(headers["ReceiptDate"], errors="coerce")
        lines = context.tables["GoodsReceiptLine"][["GoodsReceiptID", "ItemID", "QuantityReceived"]].copy()
        receipts = lines.merge(headers, on="GoodsReceiptID", how="left")
        receipts = receipts[receipts["ReceiptDateTS"].le(as_of_date)]
        for row in receipts.itertuples(index=False):
            key = (int(row.ItemID), int(row.WarehouseID))
            position[key] = round(float(position.get(key, 0.0)) + float(row.QuantityReceived), 2)

    if not context.tables["ProductionCompletion"].empty and not context.tables["ProductionCompletionLine"].empty:
        headers = context.tables["ProductionCompletion"][["ProductionCompletionID", "CompletionDate", "WarehouseID"]].copy()
        headers["CompletionDateTS"] = pd.to_datetime(headers["CompletionDate"], errors="coerce")
        lines = context.tables["ProductionCompletionLine"][["ProductionCompletionID", "ItemID", "QuantityCompleted"]].copy()
        completions = lines.merge(headers, on="ProductionCompletionID", how="left")
        completions = completions[completions["CompletionDateTS"].le(as_of_date)]
        for row in completions.itertuples(index=False):
            key = (int(row.ItemID), int(row.WarehouseID))
            position[key] = round(float(position.get(key, 0.0)) + float(row.QuantityCompleted), 2)

    if not context.tables["SalesReturn"].empty and not context.tables["SalesReturnLine"].empty:
        headers = context.tables["SalesReturn"][["SalesReturnID", "ReturnDate", "WarehouseID"]].copy()
        headers["ReturnDateTS"] = pd.to_datetime(headers["ReturnDate"], errors="coerce")
        lines = context.tables["SalesReturnLine"][["SalesReturnID", "ItemID", "QuantityReturned"]].copy()
        returns = lines.merge(headers, on="SalesReturnID", how="left")
        returns = returns[returns["ReturnDateTS"].le(as_of_date)]
        for row in returns.itertuples(index=False):
            key = (int(row.ItemID), int(row.WarehouseID))
            position[key] = round(float(position.get(key, 0.0)) + float(row.QuantityReturned), 2)

    if not context.tables["Shipment"].empty and not context.tables["ShipmentLine"].empty:
        headers = context.tables["Shipment"][["ShipmentID", "ShipmentDate", "WarehouseID"]].copy()
        headers["ShipmentDateTS"] = pd.to_datetime(headers["ShipmentDate"], errors="coerce")
        lines = context.tables["ShipmentLine"][["ShipmentID", "ItemID", "QuantityShipped"]].copy()
        shipments = lines.merge(headers, on="ShipmentID", how="left")
        shipments = shipments[shipments["ShipmentDateTS"].le(as_of_date)]
        for row in shipments.itertuples(index=False):
            key = (int(row.ItemID), int(row.WarehouseID))
            position[key] = round(float(position.get(key, 0.0)) - float(row.QuantityShipped), 2)

    if not context.tables["MaterialIssue"].empty and not context.tables["MaterialIssueLine"].empty:
        headers = context.tables["MaterialIssue"][["MaterialIssueID", "IssueDate", "WarehouseID"]].copy()
        headers["IssueDateTS"] = pd.to_datetime(headers["IssueDate"], errors="coerce")
        lines = context.tables["MaterialIssueLine"][["MaterialIssueID", "ItemID", "QuantityIssued"]].copy()
        issues = lines.merge(headers, on="MaterialIssueID", how="left")
        issues = issues[issues["IssueDateTS"].le(as_of_date)]
        for row in issues.itertuples(index=False):
            key = (int(row.ItemID), int(row.WarehouseID))
            position[key] = round(float(position.get(key, 0.0)) - float(row.QuantityIssued), 2)

    if cache is None:
        cache = {}
    cache[cache_key] = dict(position)
    setattr(context, "_planning_inventory_position_cache", cache)
    return position


def open_sales_backlog_by_item_week(context: GenerationContext) -> dict[tuple[str, int], float]:
    orders = context.tables["SalesOrder"]
    lines = context.tables["SalesOrderLine"]
    shipments = context.tables["ShipmentLine"]
    if orders.empty or lines.empty:
        return {}

    shipped_by_line: dict[int, float] = {}
    if not shipments.empty:
        shipped_by_line = shipments.groupby("SalesOrderLineID")["QuantityShipped"].sum().to_dict()
    order_headers = orders.set_index("SalesOrderID")[["RequestedDeliveryDate"]].to_dict("index")
    backlog: dict[tuple[str, int], float] = defaultdict(float)
    for row in lines.itertuples(index=False):
        header = order_headers.get(int(row.SalesOrderID))
        if header is None:
            continue
        remaining = round(float(row.Quantity) - float(shipped_by_line.get(int(row.SalesOrderLineID), 0.0)), 2)
        if remaining <= 0:
            continue
        bucket = week_start(header["RequestedDeliveryDate"]).strftime("%Y-%m-%d")
        backlog[(bucket, int(row.ItemID))] += remaining
    return {key: round(value, 2) for key, value in backlog.items()}


def open_purchase_supply_by_item_warehouse_week(context: GenerationContext) -> dict[tuple[str, int, int], float]:
    purchase_orders = context.tables["PurchaseOrder"]
    po_lines = context.tables["PurchaseOrderLine"]
    receipts = context.tables["GoodsReceiptLine"]
    if purchase_orders.empty or po_lines.empty:
        return {}

    received_by_line: dict[int, float] = {}
    if not receipts.empty:
        received_by_line = receipts.groupby("POLineID")["QuantityReceived"].sum().to_dict()
    order_headers = purchase_orders.set_index("PurchaseOrderID")[["ExpectedDeliveryDate"]].to_dict("index")
    warehouses = warehouse_ids(context)
    supply: dict[tuple[str, int, int], float] = defaultdict(float)
    for row in po_lines.itertuples(index=False):
        header = order_headers.get(int(row.PurchaseOrderID))
        if header is None:
            continue
        remaining = round(float(row.Quantity) - float(received_by_line.get(int(row.POLineID), 0.0)), 2)
        if remaining <= 0:
            continue
        warehouse_id = warehouses[(int(row.ItemID) + int(row.PurchaseOrderID)) % len(warehouses)] if warehouses else 1
        bucket = week_start(header["ExpectedDeliveryDate"]).strftime("%Y-%m-%d")
        supply[(bucket, int(row.ItemID), int(warehouse_id))] += remaining
    return {key: round(value, 2) for key, value in supply.items()}


def open_work_order_supply_by_item_warehouse_week(context: GenerationContext) -> dict[tuple[str, int, int], float]:
    work_orders = context.tables["WorkOrder"]
    completion_headers = context.tables["ProductionCompletion"]
    completions = context.tables["ProductionCompletionLine"]
    if work_orders.empty:
        return {}

    completed_by_work_order: dict[int, float] = {}
    if not completion_headers.empty and not completions.empty:
        merged = completions.merge(
            completion_headers[["ProductionCompletionID", "WorkOrderID"]],
            on="ProductionCompletionID",
            how="left",
        )
        merged = merged[merged["WorkOrderID"].notna()].copy()
        if not merged.empty:
            completed_by_work_order = merged.groupby("WorkOrderID")["QuantityCompleted"].sum().to_dict()
    supply: dict[tuple[str, int, int], float] = defaultdict(float)
    for row in work_orders.itertuples(index=False):
        remaining = round(float(row.PlannedQuantity) - float(completed_by_work_order.get(int(row.WorkOrderID), 0.0)), 2)
        if remaining <= 0:
            continue
        bucket = week_start(row.DueDate).strftime("%Y-%m-%d")
        supply[(bucket, int(row.ItemID), int(row.WarehouseID))] += remaining
    return {key: round(value, 2) for key, value in supply.items()}


def _adjust_recommendation_quantity(policy_type: str, reorder_quantity: float, net_requirement: float) -> float:
    if net_requirement <= 0:
        return 0.0
    if str(policy_type) == "Lot-for-Lot":
        return qty(net_requirement)
    reorder_quantity = max(float(reorder_quantity), 1.0)
    multiple = int(np.ceil(float(net_requirement) / reorder_quantity))
    return qty(multiple * reorder_quantity)


def generate_inventory_policies(context: GenerationContext) -> None:
    if not context.tables["InventoryPolicy"].empty:
        return

    fiscal_start, fiscal_end = fiscal_bounds(context)
    items = planning_items(context)
    warehouses = warehouse_ids(context)
    if items.empty or not warehouses:
        return

    rows: list[dict[str, Any]] = []
    for item in items.sort_values("ItemID").itertuples(index=False):
        if str(item.ItemGroup) == "Services":
            continue
        planner_id = forecast_planner_id(context, str(item.SupplyMode), fiscal_start)
        buyer_id = forecast_planner_id(context, "Purchased", fiscal_start)
        for warehouse_id in warehouses:
            target_days = 21
            safety_stock = 20.0
            reorder_quantity = 40.0
            lifecycle_status = str(getattr(item, "LifecycleStatus", "Core"))
            if str(item.ItemGroup) in {"Raw Materials", "Packaging"}:
                target_days = 18
                safety_stock = 45.0 if str(item.ItemGroup) == "Raw Materials" else 65.0
                reorder_quantity = 85.0 if str(item.ItemGroup) == "Raw Materials" else 120.0
            elif lifecycle_status == "Seasonal":
                target_days = 28
                safety_stock = 24.0
                reorder_quantity = 48.0
            elif lifecycle_status == "Core":
                target_days = 24
                safety_stock = 18.0
                reorder_quantity = 36.0

            if str(item.SupplyMode) == "Manufactured":
                policy_type = "Lot-for-Lot"
                planning_lead_time_days = max(int(item.ProductionLeadTimeDays or 0), 5)
            else:
                policy_type = "Min-Max"
                planning_lead_time_days = LEAD_TIME_DEFAULTS.get(str(item.ItemGroup), 9)

            if str(item.LifecycleStatus) == "Discontinued" and int(item.IsActive) != 1:
                continue

            rows.append({
                "InventoryPolicyID": next_id(context, "InventoryPolicy"),
                "ItemID": int(item.ItemID),
                "WarehouseID": int(warehouse_id),
                "PlanningGroup": f"{item.ItemGroup} - {item.SupplyMode}",
                "PolicyType": policy_type,
                "SafetyStockQuantity": qty(safety_stock),
                "ReorderPointQuantity": qty(safety_stock * 1.35),
                "ReorderQuantity": qty(reorder_quantity),
                "TargetDaysSupply": int(target_days),
                "PlanningLeadTimeDays": int(planning_lead_time_days),
                "PlannerEmployeeID": int(planner_id),
                "BuyerEmployeeID": int(buyer_id),
                "EffectiveStartDate": fiscal_start.strftime("%Y-%m-%d"),
                "EffectiveEndDate": fiscal_end.strftime("%Y-%m-%d"),
                "IsActive": 1,
            })

    append_rows(context, "InventoryPolicy", rows)


def generate_demand_forecasts(context: GenerationContext) -> None:
    if not context.tables["DemandForecast"].empty:
        return

    items = active_sellable_planning_items(context)
    warehouses = warehouse_ids(context)
    if items.empty or not warehouses:
        return

    rows: list[dict[str, Any]] = []
    weeks = week_starts_in_fiscal_range(context)
    fiscal_start, _ = fiscal_bounds(context)
    for item in items.sort_values("ItemID").itertuples(index=False):
        item_launch = pd.Timestamp(item.LaunchDate)
        first_week = first_forecast_week_start(item_launch)
        lifecycle_multiplier = LIFECYCLE_DEMAND_MULTIPLIER.get(str(item.LifecycleStatus), 1.0)
        base_demand = ITEM_GROUP_WEEKLY_BASE.get(str(item.ItemGroup), 10.0)
        warehouse_rank = primary_warehouse_rank(context, int(item.ItemID))
        for week_index, bucket_start in enumerate(weeks):
            if bucket_start < first_week:
                continue
            month_multiplier = SEASONAL_MONTH_MULTIPLIER.get(int(bucket_start.month), 1.0)
            week_seed = context.settings.random_seed + int(item.ItemID) * 100_003 + week_index * 97
            rng = np.random.default_rng(week_seed)
            style_multiplier = 1.0 + ((int(item.ItemID) % 5) - 2) * 0.035
            launch_ramp = 1.0
            weeks_since_launch = max(int((bucket_start - first_week).days // 7), 0)
            if weeks_since_launch < 8:
                launch_ramp = min(1.0, 0.45 + weeks_since_launch * 0.07)
            baseline_total = max(
                0.0,
                qty(
                    base_demand
                    * lifecycle_multiplier
                    * month_multiplier
                    * style_multiplier
                    * launch_ramp
                    * rng.uniform(0.92, 1.08)
                ),
            )
            if baseline_total <= 0:
                continue

            week_end_date = week_end(bucket_start)
            for warehouse_rank_index, warehouse_id in enumerate(warehouse_rank):
                share = WAREHOUSE_FORECAST_SHARE_BY_RANK[min(warehouse_rank_index, len(WAREHOUSE_FORECAST_SHARE_BY_RANK) - 1)]
                baseline = qty(baseline_total * share)
                adjustment = qty(baseline * rng.uniform(-0.08, 0.10))
                forecast = max(0.0, qty(baseline + adjustment))
                if forecast <= 0:
                    continue
                if abs(adjustment) > max(1.0, baseline * 0.04):
                    forecast_method = "Planner Adjusted"
                elif str(item.LifecycleStatus) == "Seasonal":
                    forecast_method = "Lifecycle Adjusted"
                else:
                    forecast_method = "Seasonal Trend"
                planner_id = forecast_planner_id(context, str(item.SupplyMode), bucket_start)
                approved_by = forecast_approver_id(context, str(item.SupplyMode), bucket_start)
                approved_date = max(fiscal_start, bucket_start - pd.Timedelta(days=10))
                rows.append({
                    "DemandForecastID": next_id(context, "DemandForecast"),
                    "ForecastWeekStartDate": bucket_start.strftime("%Y-%m-%d"),
                    "ForecastWeekEndDate": week_end_date.strftime("%Y-%m-%d"),
                    "ItemID": int(item.ItemID),
                    "WarehouseID": int(warehouse_id),
                    "BaselineForecastQuantity": baseline,
                    "ForecastQuantity": forecast,
                    "ForecastMethod": forecast_method,
                    "ForecastVersion": "Current Weekly Plan",
                    "PlannerEmployeeID": int(planner_id),
                    "ApprovedByEmployeeID": int(approved_by),
                    "ApprovedDate": approved_date.strftime("%Y-%m-%d"),
                    "IsCurrent": 1,
                })

    append_rows(context, "DemandForecast", rows)


def _routing_operations_lookup(context: GenerationContext) -> dict[int, pd.DataFrame]:
    routing_operations = context.tables["RoutingOperation"]
    if routing_operations.empty:
        return {}
    return {
        int(routing_id): rows.copy()
        for routing_id, rows in routing_operations.groupby("RoutingID")
    }


def _active_bom_lookup(context: GenerationContext) -> tuple[dict[int, dict[str, Any]], dict[int, pd.DataFrame]]:
    boms = context.tables["BillOfMaterial"]
    bom_lines = context.tables["BillOfMaterialLine"]
    active_bom_by_parent: dict[int, dict[str, Any]] = {}
    if not boms.empty:
        for row in boms.sort_values(["ParentItemID", "VersionNumber", "BOMID"]).itertuples(index=False):
            if str(row.Status) == "Active":
                active_bom_by_parent[int(row.ParentItemID)] = row._asdict()
    bom_lines_by_bom: dict[int, pd.DataFrame] = {}
    if not bom_lines.empty:
        bom_lines_by_bom = {
            int(bom_id): rows.copy()
            for bom_id, rows in bom_lines.groupby("BOMID")
        }
    return active_bom_by_parent, bom_lines_by_bom


def _active_routing_lookup(context: GenerationContext) -> dict[int, dict[str, Any]]:
    routings = context.tables["Routing"]
    active: dict[int, dict[str, Any]] = {}
    if not routings.empty:
        for row in routings.sort_values(["ParentItemID", "VersionNumber", "RoutingID"]).itertuples(index=False):
            if str(row.Status) == "Active":
                active[int(row.ParentItemID)] = row._asdict()
    return active


def _available_hours_by_work_center_week(context: GenerationContext) -> dict[tuple[str, int], float]:
    calendar = context.tables["WorkCenterCalendar"]
    if calendar.empty:
        return {}
    frame = calendar.copy()
    frame["WeekStart"] = pd.to_datetime(frame["CalendarDate"], errors="coerce").map(week_start)
    summary = frame.groupby(["WeekStart", "WorkCenterID"])["AvailableHours"].sum().round(2)
    return {(str(index[0].strftime("%Y-%m-%d")), int(index[1])): float(value) for index, value in summary.items()}


def _scheduled_component_supply_by_item_warehouse_week(
    purchase_supply: dict[tuple[str, int, int], float],
) -> dict[tuple[str, int, int], float]:
    return dict(purchase_supply)


def generate_month_planning(context: GenerationContext, year: int, month: int) -> None:
    if context.tables["InventoryPolicy"].empty:
        generate_inventory_policies(context)
    if context.tables["DemandForecast"].empty:
        generate_demand_forecasts(context)

    month_start, month_end = month_bounds(year, month)
    current_week_start = week_start(month_start)
    horizon_starts = [current_week_start + pd.Timedelta(days=7 * offset) for offset in range(12)]
    if not horizon_starts:
        return

    items = context.tables["Item"].set_index("ItemID").to_dict("index")
    policies = active_policy_lookup(context)
    weekly_forecast = weekly_forecast_map(context)
    backlog = open_sales_backlog_by_item_week(context)
    open_purchase_supply = open_purchase_supply_by_item_warehouse_week(context)
    open_work_order_supply = open_work_order_supply_by_item_warehouse_week(context)
    available_hours = _available_hours_by_work_center_week(context)
    inventory_state = inventory_position_as_of(context, month_start - pd.Timedelta(days=1))
    active_bom_by_parent, bom_lines_by_bom = _active_bom_lookup(context)
    active_routing_by_parent = _active_routing_lookup(context)
    routing_ops_by_routing = _routing_operations_lookup(context)

    warehouses = warehouse_ids(context)
    if not warehouses:
        return

    recommendation_rows: list[dict[str, Any]] = []
    material_plan_rows: list[dict[str, Any]] = []
    rough_cut_rows: list[dict[str, Any]] = []

    cumulative_capacity: dict[tuple[str, int], float] = defaultdict(float)
    component_projected: dict[tuple[int, int], float] = defaultdict(float)
    for key, value in inventory_state.items():
        component_projected[key] = float(value)

    sellable_items = context.tables["Item"][
        context.tables["Item"]["RevenueAccountID"].notna()
        & context.tables["Item"]["IsActive"].astype(int).eq(1)
        & context.tables["Item"]["LaunchDate"].notna()
    ].copy()

    manufacture_recommendations: list[dict[str, Any]] = []
    for item in sellable_items.sort_values("ItemID").itertuples(index=False):
        launch_date = pd.Timestamp(item.LaunchDate)
        ranked_warehouses = primary_warehouse_rank(context, int(item.ItemID))
        for warehouse_id in ranked_warehouses:
            policy = policies.get((int(item.ItemID), int(warehouse_id)))
            if policy is None:
                continue
            projected_available = float(inventory_state.get((int(item.ItemID), int(warehouse_id)), 0.0))
            planning_lead_time_days = int(policy["PlanningLeadTimeDays"])
            safety_stock = float(policy["SafetyStockQuantity"])
            reorder_qty = float(policy["ReorderQuantity"])
            policy_type = str(policy["PolicyType"])
            for bucket_start in horizon_starts:
                if bucket_start < week_start(launch_date):
                    continue
                bucket_end = week_end(bucket_start)
                forecast_qty = float(weekly_forecast.get((bucket_start.strftime("%Y-%m-%d"), int(item.ItemID), int(warehouse_id)), 0.0))
                backlog_qty = 0.0
                if int(warehouse_id) == int(ranked_warehouses[0]):
                    backlog_qty = float(backlog.get((bucket_start.strftime("%Y-%m-%d"), int(item.ItemID)), 0.0))
                gross_requirement = round(forecast_qty + backlog_qty, 2)
                scheduled_supply = round(
                    float(open_purchase_supply.get((bucket_start.strftime("%Y-%m-%d"), int(item.ItemID), int(warehouse_id)), 0.0))
                    + float(open_work_order_supply.get((bucket_start.strftime("%Y-%m-%d"), int(item.ItemID), int(warehouse_id)), 0.0)),
                    2,
                )
                projected_after_demand = round(projected_available + scheduled_supply - gross_requirement, 2)
                net_requirement = max(0.0, round(safety_stock - projected_after_demand, 2))
                recommended_order_quantity = _adjust_recommendation_quantity(policy_type, reorder_qty, net_requirement)
                projected_available = round(projected_after_demand + recommended_order_quantity, 2)
                if recommended_order_quantity <= 0:
                    continue

                recommendation_type = "Manufacture" if str(item.SupplyMode) == "Manufactured" else "Purchase"
                need_by_date = bucket_end
                release_by_date = max(
                    need_by_date - pd.Timedelta(days=planning_lead_time_days),
                    launch_date.normalize(),
                )
                priority = "Expedite" if (release_by_date <= month_end or projected_after_demand < 0) else "Normal"
                if backlog_qty > forecast_qty and backlog_qty > 0:
                    driver_type = "Sales Backlog"
                elif gross_requirement <= 0:
                    driver_type = "Safety Stock"
                else:
                    driver_type = "Forecast"

                recommendation = {
                    "SupplyPlanRecommendationID": next_id(context, "SupplyPlanRecommendation"),
                    "RecommendationDate": month_start.strftime("%Y-%m-%d"),
                    "BucketWeekStartDate": bucket_start.strftime("%Y-%m-%d"),
                    "BucketWeekEndDate": bucket_end.strftime("%Y-%m-%d"),
                    "ItemID": int(item.ItemID),
                    "WarehouseID": int(warehouse_id),
                    "RecommendationType": recommendation_type,
                    "PriorityCode": priority,
                    "SupplyMode": str(item.SupplyMode),
                    "GrossRequirementQuantity": qty(gross_requirement),
                    "ProjectedAvailableQuantity": qty(max(projected_after_demand, 0.0)),
                    "NetRequirementQuantity": qty(net_requirement),
                    "RecommendedOrderQuantity": qty(recommended_order_quantity),
                    "NeedByDate": need_by_date.strftime("%Y-%m-%d"),
                    "ReleaseByDate": release_by_date.strftime("%Y-%m-%d"),
                    "RecommendationStatus": "Planned",
                    "DriverType": driver_type,
                    "PlannerEmployeeID": int(policy["PlannerEmployeeID"]),
                    "ConvertedDocumentType": None,
                    "ConvertedDocumentID": None,
                }
                recommendation_rows.append(recommendation)
                if recommendation_type == "Manufacture":
                    manufacture_recommendations.append(recommendation)

    component_scheduled_supply = _scheduled_component_supply_by_item_warehouse_week(open_purchase_supply)
    for recommendation in sorted(
        manufacture_recommendations,
        key=lambda row: (row["BucketWeekStartDate"], row["ItemID"], row["WarehouseID"], row["SupplyPlanRecommendationID"]),
    ):
        item_id = int(recommendation["ItemID"])
        warehouse_id = int(recommendation["WarehouseID"])
        routing = active_routing_by_parent.get(item_id)
        bom = active_bom_by_parent.get(item_id)
        if routing is not None:
            operations = routing_ops_by_routing.get(int(routing["RoutingID"]), pd.DataFrame())
            week_key = str(recommendation["BucketWeekStartDate"])
            for operation in operations.itertuples(index=False):
                load_hours = qty(
                    float(operation.StandardSetupHours)
                    + float(operation.StandardRunHoursPerUnit) * float(recommendation["RecommendedOrderQuantity"])
                )
                capacity_key = (week_key, int(operation.WorkCenterID))
                cumulative_capacity[capacity_key] += load_hours
                available = float(available_hours.get(capacity_key, 0.0))
                utilization = round(float(cumulative_capacity[capacity_key]) / available, 4) if available > 0 else 0.0
                if utilization > 1.0:
                    status = "Over Capacity"
                elif utilization >= 0.90:
                    status = "Tight"
                else:
                    status = "Within Capacity"
                rough_cut_rows.append({
                    "RoughCutCapacityPlanID": next_id(context, "RoughCutCapacityPlan"),
                    "BucketWeekStartDate": recommendation["BucketWeekStartDate"],
                    "BucketWeekEndDate": recommendation["BucketWeekEndDate"],
                    "WorkCenterID": int(operation.WorkCenterID),
                    "ItemID": item_id,
                    "SupplyPlanRecommendationID": int(recommendation["SupplyPlanRecommendationID"]),
                    "PlannedLoadHours": load_hours,
                    "AvailableHours": qty(available),
                    "UtilizationPct": utilization,
                    "CapacityStatus": status,
                })
        if bom is None:
            continue
        bom_lines = bom_lines_by_bom.get(int(bom["BOMID"]), pd.DataFrame())
        if bom_lines.empty:
            continue
        week_key = str(recommendation["BucketWeekStartDate"])
        for bom_line in bom_lines.itertuples(index=False):
            component_item = items.get(int(bom_line.ComponentItemID))
            if component_item is None:
                continue
            gross_requirement = qty(
                float(recommendation["RecommendedOrderQuantity"])
                * float(bom_line.QuantityPerUnit)
                * (1 + float(bom_line.ScrapFactorPct))
            )
            policy = policies.get((int(bom_line.ComponentItemID), warehouse_id))
            scheduled_supply = float(component_scheduled_supply.get((week_key, int(bom_line.ComponentItemID), warehouse_id), 0.0))
            current_projected = float(component_projected.get((int(bom_line.ComponentItemID), warehouse_id), 0.0))
            safety_stock = float(policy["SafetyStockQuantity"]) if policy is not None else 0.0
            reorder_qty = float(policy["ReorderQuantity"]) if policy is not None else gross_requirement
            policy_type = str(policy["PolicyType"]) if policy is not None else "Lot-for-Lot"
            projected_after_demand = round(current_projected + scheduled_supply - gross_requirement, 2)
            net_requirement = max(0.0, round(safety_stock - projected_after_demand, 2))
            recommended_order_quantity = _adjust_recommendation_quantity(policy_type, reorder_qty, net_requirement)
            component_projected[(int(bom_line.ComponentItemID), warehouse_id)] = round(
                projected_after_demand + recommended_order_quantity,
                2,
            )
            material_plan_rows.append({
                "MaterialRequirementPlanID": next_id(context, "MaterialRequirementPlan"),
                "BucketWeekStartDate": recommendation["BucketWeekStartDate"],
                "BucketWeekEndDate": recommendation["BucketWeekEndDate"],
                "ParentItemID": item_id,
                "ComponentItemID": int(bom_line.ComponentItemID),
                "WarehouseID": warehouse_id,
                "SupplyPlanRecommendationID": int(recommendation["SupplyPlanRecommendationID"]),
                "GrossRequirementQuantity": gross_requirement,
                "ScheduledSupplyQuantity": qty(scheduled_supply),
                "ProjectedAvailableQuantity": qty(max(projected_after_demand, 0.0)),
                "NetRequirementQuantity": qty(net_requirement),
                "RecommendedOrderQuantity": qty(recommended_order_quantity),
            })
            if recommended_order_quantity <= 0:
                continue
            if str(component_item.get("SupplyMode", "Purchased")) != "Purchased":
                continue
            release_by_date = pd.Timestamp(recommendation["BucketWeekEndDate"]) - pd.Timedelta(
                days=int(policy["PlanningLeadTimeDays"]) if policy is not None else LEAD_TIME_DEFAULTS.get(str(component_item.get("ItemGroup", "")), 7)
            )
            priority = "Expedite" if release_by_date <= month_end else "Normal"
            planner_id = int(policy["PlannerEmployeeID"]) if policy is not None else forecast_planner_id(context, "Purchased", month_start)
            recommendation_rows.append({
                "SupplyPlanRecommendationID": next_id(context, "SupplyPlanRecommendation"),
                "RecommendationDate": month_start.strftime("%Y-%m-%d"),
                "BucketWeekStartDate": recommendation["BucketWeekStartDate"],
                "BucketWeekEndDate": recommendation["BucketWeekEndDate"],
                "ItemID": int(bom_line.ComponentItemID),
                "WarehouseID": warehouse_id,
                "RecommendationType": "Purchase",
                "PriorityCode": priority,
                "SupplyMode": str(component_item.get("SupplyMode", "Purchased")),
                "GrossRequirementQuantity": gross_requirement,
                "ProjectedAvailableQuantity": qty(max(projected_after_demand, 0.0)),
                "NetRequirementQuantity": qty(net_requirement),
                "RecommendedOrderQuantity": qty(recommended_order_quantity),
                "NeedByDate": recommendation["NeedByDate"],
                "ReleaseByDate": release_by_date.strftime("%Y-%m-%d"),
                "RecommendationStatus": "Planned",
                "DriverType": "Component Demand",
                "PlannerEmployeeID": planner_id,
                "ConvertedDocumentType": None,
                "ConvertedDocumentID": None,
            })

    append_rows(context, "SupplyPlanRecommendation", recommendation_rows)
    append_rows(context, "MaterialRequirementPlan", material_plan_rows)
    append_rows(context, "RoughCutCapacityPlan", rough_cut_rows)


def purchase_recommendations_for_month(context: GenerationContext, year: int, month: int) -> pd.DataFrame:
    recommendations = context.tables["SupplyPlanRecommendation"]
    if recommendations.empty:
        return recommendations.head(0).copy()
    release_dates = pd.to_datetime(recommendations["ReleaseByDate"], errors="coerce")
    rows = recommendations[
        recommendations["RecommendationType"].eq("Purchase")
        & recommendations["RecommendationStatus"].eq("Planned")
        & release_dates.dt.year.eq(year)
        & release_dates.dt.month.eq(month)
        & recommendations["RecommendedOrderQuantity"].astype(float).gt(0)
    ].copy()
    return rows.sort_values(["ReleaseByDate", "PriorityCode", "SupplyPlanRecommendationID"]).reset_index(drop=True)


def manufacture_recommendations_for_month(context: GenerationContext, year: int, month: int) -> pd.DataFrame:
    recommendations = context.tables["SupplyPlanRecommendation"]
    if recommendations.empty:
        return recommendations.head(0).copy()
    release_dates = pd.to_datetime(recommendations["ReleaseByDate"], errors="coerce")
    rows = recommendations[
        recommendations["RecommendationType"].eq("Manufacture")
        & recommendations["RecommendationStatus"].eq("Planned")
        & release_dates.dt.year.eq(year)
        & release_dates.dt.month.eq(month)
        & recommendations["RecommendedOrderQuantity"].astype(float).gt(0)
    ].copy()
    return rows.sort_values(["ReleaseByDate", "PriorityCode", "SupplyPlanRecommendationID"]).reset_index(drop=True)


def update_recommendation_conversion(
    context: GenerationContext,
    mapping: dict[int, tuple[str, int]],
) -> None:
    if not mapping:
        return
    recommendation_ids = pd.to_numeric(
        context.tables["SupplyPlanRecommendation"]["SupplyPlanRecommendationID"],
        errors="coerce",
    ).astype("Int64")
    for recommendation_id, (document_type, document_id) in mapping.items():
        mask = recommendation_ids.eq(int(recommendation_id))
        context.tables["SupplyPlanRecommendation"].loc[mask, "RecommendationStatus"] = "Converted"
        context.tables["SupplyPlanRecommendation"].loc[mask, "ConvertedDocumentType"] = str(document_type)
        context.tables["SupplyPlanRecommendation"].loc[mask, "ConvertedDocumentID"] = int(document_id)
    invalidate_planning_caches(context, "SupplyPlanRecommendation")
