from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from greenfield_dataset.master_data import ITEM_GROUP_CONFIG
from greenfield_dataset.o2c import opening_inventory_map, sales_order_line_shipped_quantities, shadow_inventory_state
from greenfield_dataset.payroll import (
    labor_time_direct_cost_by_work_order,
    next_business_day,
    work_order_overhead_cost_map,
)
from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.settings import GenerationContext
from greenfield_dataset.utils import format_doc_number, money, next_id, qty


MANUFACTURED_ITEM_SHARE_MIN = 0.35
MANUFACTURED_ITEM_SHARE_MAX = 0.45

BOM_LINE_COUNT_RANGE = {
    "Furniture": (3, 5),
    "Lighting": (2, 4),
    "Textiles": (2, 4),
    "Accessories": (2, 3),
}

RAW_COMPONENT_QUANTITY_RANGE = {
    "Furniture": (1.10, 3.60),
    "Lighting": (0.80, 2.25),
    "Textiles": (1.20, 3.25),
    "Accessories": (0.60, 1.85),
}

PACKAGING_QUANTITY_RANGE = {
    "Furniture": (1.00, 1.30),
    "Lighting": (1.00, 1.20),
    "Textiles": (1.00, 1.40),
    "Accessories": (1.00, 1.15),
}

SCRAP_FACTOR_RANGE = {
    "Raw Materials": (0.00, 0.07),
    "Packaging": (0.00, 0.02),
}

FINISHED_GOODS_BUFFER_RANGE = {
    "Furniture": (8.0, 20.0),
    "Lighting": (12.0, 28.0),
    "Textiles": (10.0, 24.0),
    "Accessories": (6.0, 16.0),
}

WORK_ORDER_SAME_MONTH_COMPLETION_PROBABILITY = 0.78
WORK_ORDER_PARTIAL_COMPLETION_RANGE = (0.45, 0.82)
ISSUE_EVENT_COUNT_PROBABILITIES = ((1, 0.68), (2, 0.32))
COMPLETION_EVENT_COUNT_PROBABILITIES = ((1, 0.72), (2, 0.28))
ISSUE_FACTOR_RANGE = (0.98, 1.04)
MATERIAL_REQUISITION_BUFFER_FACTOR = (1.03, 1.08)

WORK_CENTER_DEFINITIONS = (
    {
        "WorkCenterCode": "CUT",
        "WorkCenterName": "Cutting Work Center",
        "Department": "Manufacturing",
        "ManagerTitles": ("Production Supervisor", "Production Manager"),
    },
    {
        "WorkCenterCode": "ASSEMBLY",
        "WorkCenterName": "Assembly Work Center",
        "Department": "Manufacturing",
        "ManagerTitles": ("Production Supervisor", "Production Manager"),
    },
    {
        "WorkCenterCode": "FINISH",
        "WorkCenterName": "Finishing and Test Work Center",
        "Department": "Manufacturing",
        "ManagerTitles": ("Production Supervisor", "Production Manager"),
    },
    {
        "WorkCenterCode": "PACK",
        "WorkCenterName": "Packing Work Center",
        "Department": "Manufacturing",
        "ManagerTitles": ("Production Planner", "Production Supervisor", "Production Manager"),
    },
    {
        "WorkCenterCode": "QA",
        "WorkCenterName": "Quality Assurance Work Center",
        "Department": "Manufacturing",
        "ManagerTitles": ("Production Manager", "Quality Technician"),
    },
)

ROUTING_PATTERN_BY_GROUP = {
    "Furniture": [
        ("CUT", "Cut Components"),
        ("ASSEMBLY", "Assemble Units"),
        ("FINISH", "Finish and Inspect"),
        ("PACK", "Pack Finished Goods"),
    ],
    "Lighting": [
        ("ASSEMBLY", "Assemble Lighting Units"),
        ("FINISH", "Test and Finish"),
        ("PACK", "Pack Finished Goods"),
    ],
    "Textiles": [
        ("CUT", "Cut Fabric"),
        ("ASSEMBLY", "Sew and Assemble"),
        ("PACK", "Pack Finished Goods"),
    ],
    "Accessories": [
        ("ASSEMBLY", "Assemble Units"),
        ("PACK", "Pack Finished Goods"),
    ],
}

OPERATION_LABOR_WEIGHT = {
    "CUT": 0.20,
    "ASSEMBLY": 0.42,
    "FINISH": 0.25,
    "PACK": 0.09,
    "QA": 0.04,
}

OPERATION_SETUP_HOURS_RANGE = {
    "CUT": (0.30, 0.70),
    "ASSEMBLY": (0.25, 0.55),
    "FINISH": (0.20, 0.45),
    "PACK": (0.08, 0.20),
    "QA": (0.10, 0.22),
}

OPERATION_QUEUE_DAY_OPTIONS = {
    "CUT": (0, 1),
    "ASSEMBLY": (0, 1),
    "FINISH": (1, 2),
    "PACK": (0, 1),
    "QA": (0, 1),
}

LABOR_BEARING_OPERATION_CODES = {"ASSEMBLY", "FINISH", "QA", "CUT"}


def append_rows(context: GenerationContext, table_name: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    new_rows = pd.DataFrame(rows, columns=TABLE_COLUMNS[table_name])
    context.tables[table_name] = pd.concat([context.tables[table_name], new_rows], ignore_index=True)


def month_bounds(year: int, month: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(year=year, month=month, day=1)
    end = start + pd.offsets.MonthEnd(1)
    return start, end


def random_date_between(rng: np.random.Generator, start: pd.Timestamp, end: pd.Timestamp) -> pd.Timestamp:
    if end < start:
        end = start
    days = int((end - start).days)
    return start + pd.Timedelta(days=int(rng.integers(0, days + 1)))


def cost_center_id(context: GenerationContext, cost_center_name: str) -> int:
    cost_centers = context.tables["CostCenter"]
    matches = cost_centers.loc[cost_centers["CostCenterName"].eq(cost_center_name), "CostCenterID"]
    if matches.empty:
        raise ValueError(f"{cost_center_name} cost center is required for manufacturing.")
    return int(matches.iloc[0])


def employee_ids_for_cost_center(context: GenerationContext, cost_center_name: str) -> list[int]:
    cc_id = cost_center_id(context, cost_center_name)
    employees = context.tables["Employee"]
    ids = employees.loc[employees["CostCenterID"].eq(cc_id), "EmployeeID"].astype(int).tolist()
    return ids or employees["EmployeeID"].astype(int).tolist()


def approver_id(context: GenerationContext, minimum_amount: float = 0.0) -> int:
    employees = context.tables["Employee"].copy()
    eligible = employees[
        employees["AuthorizationLevel"].isin(["Manager", "Executive"])
        & (employees["MaxApprovalAmount"].astype(float) >= float(minimum_amount))
    ]
    if eligible.empty:
        eligible = employees[employees["AuthorizationLevel"].isin(["Manager", "Executive"])]
    if eligible.empty:
        eligible = employees
    return int(eligible.iloc[0]["EmployeeID"])


def warehouse_ids(context: GenerationContext) -> list[int]:
    warehouse_table = context.tables["Warehouse"]
    if warehouse_table.empty:
        raise ValueError("Generate warehouses before manufacturing.")
    return sorted(warehouse_table["WarehouseID"].astype(int).tolist())


def choose_count(rng: np.random.Generator, options: tuple[tuple[int, float], ...]) -> int:
    values = np.array([value for value, _ in options], dtype=int)
    probabilities = np.array([probability for _, probability in options], dtype=float)
    probabilities = probabilities / probabilities.sum()
    return int(rng.choice(values, p=probabilities))


def manufactured_items(context: GenerationContext) -> pd.DataFrame:
    items = context.tables["Item"]
    rows = items[
        items["SupplyMode"].eq("Manufactured")
        & items["RevenueAccountID"].notna()
        & items["IsActive"].eq(1)
    ].copy()
    return rows.sort_values("ItemID").reset_index(drop=True)


def bom_lookup(context: GenerationContext) -> dict[int, dict[str, Any]]:
    if context.tables["BillOfMaterial"].empty:
        return {}
    return context.tables["BillOfMaterial"].set_index("ParentItemID").to_dict("index")


def bom_lines_by_bom(context: GenerationContext) -> dict[int, pd.DataFrame]:
    bom_lines = context.tables["BillOfMaterialLine"]
    if bom_lines.empty:
        return {}
    return {
        int(bom_id): rows.sort_values("LineNumber").reset_index(drop=True)
        for bom_id, rows in bom_lines.groupby("BOMID")
    }


def active_routing_by_item(context: GenerationContext) -> dict[int, dict[str, Any]]:
    routings = context.tables["Routing"]
    if routings.empty:
        return {}
    active = routings[routings["Status"].eq("Active")].copy()
    if active.empty:
        return {}
    active = active.sort_values(["ParentItemID", "RoutingID"]).drop_duplicates("ParentItemID", keep="first")
    return active.set_index("ParentItemID").to_dict("index")


def routing_operations_by_routing(context: GenerationContext) -> dict[int, pd.DataFrame]:
    operations = context.tables["RoutingOperation"]
    if operations.empty:
        return {}
    return {
        int(routing_id): rows.sort_values("OperationSequence").reset_index(drop=True)
        for routing_id, rows in operations.groupby("RoutingID")
    }


def work_order_operations_by_work_order(context: GenerationContext) -> dict[int, pd.DataFrame]:
    operations = context.tables["WorkOrderOperation"]
    if operations.empty:
        return {}
    return {
        int(work_order_id): rows.sort_values("OperationSequence").reset_index(drop=True)
        for work_order_id, rows in operations.groupby("WorkOrderID")
    }


def work_center_id_by_code(context: GenerationContext) -> dict[str, int]:
    work_centers = context.tables["WorkCenter"]
    if work_centers.empty:
        return {}
    return {
        str(row.WorkCenterCode): int(row.WorkCenterID)
        for row in work_centers.itertuples(index=False)
    }


def manager_for_titles(context: GenerationContext, titles: tuple[str, ...]) -> int:
    employees = context.tables["Employee"]
    for title in titles:
        matches = employees.loc[employees["JobTitle"].eq(title), "EmployeeID"]
        if not matches.empty:
            return int(matches.iloc[0])
    manufacturing_ids = employee_ids_for_cost_center(context, "Manufacturing")
    if manufacturing_ids:
        return int(manufacturing_ids[0])
    return int(employees.iloc[0]["EmployeeID"])


def routing_pattern_for_item(context: GenerationContext, item_group: str, item_id: int) -> list[tuple[str, str]]:
    pattern = list(ROUTING_PATTERN_BY_GROUP.get(str(item_group), ROUTING_PATTERN_BY_GROUP["Accessories"]))
    if str(item_group) == "Lighting" and (context.settings.random_seed + int(item_id)) % 4 == 0:
        pattern.insert(len(pattern) - 1, ("QA", "Quality Check"))
    return pattern


def normalized_operation_run_hours(
    item_standard_labor_hours: float,
    operation_codes: list[str],
) -> list[float]:
    weights = [float(OPERATION_LABOR_WEIGHT.get(code, 0.10)) for code in operation_codes]
    total_weight = sum(weights) or 1.0
    allocated = 0.0
    run_hours: list[float] = []
    for index, weight in enumerate(weights, start=1):
        if index == len(weights):
            value = money(max(float(item_standard_labor_hours) - allocated, 0.0))
        else:
            value = money(float(item_standard_labor_hours) * weight / total_weight)
            allocated = money(allocated + value)
        run_hours.append(value)
    return run_hours


def sequential_operation_windows(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    operation_count: int,
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    if operation_count <= 0:
        return []

    start = pd.Timestamp(start_date)
    finish = pd.Timestamp(end_date)
    if finish < start:
        finish = start
    total_days = max(int((finish - start).days), 0)
    breakpoints = [int(round(total_days * index / operation_count)) for index in range(operation_count + 1)]
    windows: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for index in range(operation_count):
        window_start = start + pd.Timedelta(days=breakpoints[index])
        window_end = start + pd.Timedelta(days=breakpoints[index + 1])
        if window_end < window_start:
            window_end = window_start
        windows.append((window_start, window_end))
    return windows


def manufactured_item_group_share(context: GenerationContext) -> float:
    items = context.tables["Item"]
    sellable = items[items["RevenueAccountID"].notna() & items["ListPrice"].notna()]
    if sellable.empty:
        return 0.0
    manufactured = sellable[sellable["SupplyMode"].eq("Manufactured")]
    return round(len(manufactured) / len(sellable), 4)


def generate_boms(context: GenerationContext) -> None:
    if not context.tables["BillOfMaterial"].empty or not context.tables["BillOfMaterialLine"].empty:
        raise ValueError("BOM master data has already been generated.")

    items = context.tables["Item"].copy()
    raw_materials = items[items["ItemGroup"].eq("Raw Materials") & items["IsActive"].eq(1)].copy()
    packaging = items[items["ItemGroup"].eq("Packaging") & items["IsActive"].eq(1)].copy()
    if raw_materials.empty or packaging.empty:
        raise ValueError("Raw materials and packaging items are required before generating BOMs.")

    manufactured = manufactured_items(context)
    bom_rows: list[dict[str, Any]] = []
    bom_line_rows: list[dict[str, Any]] = []

    items = items.set_index("ItemID")
    for item in manufactured.itertuples(index=False):
        rng = np.random.default_rng(context.settings.random_seed + int(item.ItemID) * 101)
        bom_id = next_id(context, "BillOfMaterial")
        bom_rows.append({
            "BOMID": bom_id,
            "ParentItemID": int(item.ItemID),
            "VersionNumber": 1,
            "EffectiveStartDate": context.settings.fiscal_year_start,
            "EffectiveEndDate": None,
            "Status": "Active",
            "StandardBatchQuantity": 1.0,
        })

        min_lines, max_lines = BOM_LINE_COUNT_RANGE.get(str(item.ItemGroup), (2, 4))
        line_target = int(rng.integers(min_lines, max_lines + 1))
        packaging_item = packaging.iloc[int(rng.integers(0, len(packaging)))]
        raw_component_target = max(1, line_target - 1)
        raw_component_indexes = rng.choice(
            raw_materials.index.to_numpy(),
            size=min(raw_component_target, len(raw_materials)),
            replace=False,
        )
        component_rows = [raw_materials.loc[int(index)] for index in np.atleast_1d(raw_component_indexes)]
        component_rows.append(packaging_item)

        material_cost = 0.0
        for line_number, component in enumerate(component_rows, start=1):
            component_group = str(component["ItemGroup"])
            if component_group == "Packaging":
                qty_low, qty_high = PACKAGING_QUANTITY_RANGE[str(item.ItemGroup)]
            else:
                qty_low, qty_high = RAW_COMPONENT_QUANTITY_RANGE[str(item.ItemGroup)]
            quantity_per_unit = qty(rng.uniform(qty_low, qty_high))
            scrap_low, scrap_high = SCRAP_FACTOR_RANGE[component_group]
            scrap_factor = qty(rng.uniform(scrap_low, scrap_high), places="0.0001")
            material_cost += float(component["StandardCost"]) * quantity_per_unit * (1 + scrap_factor)
            bom_line_rows.append({
                "BOMLineID": next_id(context, "BillOfMaterialLine"),
                "BOMID": bom_id,
                "ComponentItemID": int(component["ItemID"]),
                "LineNumber": line_number,
                "QuantityPerUnit": quantity_per_unit,
                "ScrapFactorPct": scrap_factor,
            })

        new_standard_cost = money(material_cost + float(item.StandardConversionCost))
        prior_standard_cost = max(float(item.StandardCost), 0.01)
        markup_ratio = max(float(item.ListPrice) / prior_standard_cost, 1.10)
        items.loc[int(item.ItemID), "StandardCost"] = new_standard_cost
        items.loc[int(item.ItemID), "ListPrice"] = money(new_standard_cost * markup_ratio)

    context.tables["Item"] = items.reset_index()[TABLE_COLUMNS["Item"]]
    append_rows(context, "BillOfMaterial", bom_rows)
    append_rows(context, "BillOfMaterialLine", bom_line_rows)


def generate_work_centers_and_routings(context: GenerationContext) -> None:
    if (
        not context.tables["WorkCenter"].empty
        or not context.tables["Routing"].empty
        or not context.tables["RoutingOperation"].empty
    ):
        return

    manufactured = manufactured_items(context)
    if manufactured.empty:
        return

    warehouses = warehouse_ids(context)
    work_center_rows: list[dict[str, Any]] = []
    for index, definition in enumerate(WORK_CENTER_DEFINITIONS):
        work_center_rows.append({
            "WorkCenterID": next_id(context, "WorkCenter"),
            "WorkCenterCode": definition["WorkCenterCode"],
            "WorkCenterName": definition["WorkCenterName"],
            "Department": definition["Department"],
            "WarehouseID": int(warehouses[index % len(warehouses)]),
            "ManagerEmployeeID": manager_for_titles(context, definition["ManagerTitles"]),
            "IsActive": 1,
        })
    append_rows(context, "WorkCenter", work_center_rows)

    work_center_ids = {row["WorkCenterCode"]: int(row["WorkCenterID"]) for row in work_center_rows}
    items = context.tables["Item"].copy()
    routing_rows: list[dict[str, Any]] = []
    routing_operation_rows: list[dict[str, Any]] = []

    for item in manufactured.itertuples(index=False):
        rng = np.random.default_rng(context.settings.random_seed + int(item.ItemID) * 313)
        routing_id = next_id(context, "Routing")
        routing_rows.append({
            "RoutingID": routing_id,
            "ParentItemID": int(item.ItemID),
            "VersionNumber": 1,
            "EffectiveStartDate": context.settings.fiscal_year_start,
            "EffectiveEndDate": None,
            "Status": "Active",
        })

        pattern = routing_pattern_for_item(context, str(item.ItemGroup), int(item.ItemID))
        operation_codes = [operation_code for operation_code, _ in pattern]
        run_hours = normalized_operation_run_hours(float(item.StandardLaborHoursPerUnit), operation_codes)
        for sequence, ((operation_code, operation_name), operation_run_hours) in enumerate(zip(pattern, run_hours, strict=False), start=1):
            setup_low, setup_high = OPERATION_SETUP_HOURS_RANGE[operation_code]
            queue_options = OPERATION_QUEUE_DAY_OPTIONS[operation_code]
            routing_operation_rows.append({
                "RoutingOperationID": next_id(context, "RoutingOperation"),
                "RoutingID": routing_id,
                "OperationSequence": sequence,
                "OperationCode": operation_code,
                "OperationName": operation_name,
                "WorkCenterID": int(work_center_ids[operation_code]),
                "StandardSetupHours": money(float(rng.uniform(setup_low, setup_high))),
                "StandardRunHoursPerUnit": money(float(operation_run_hours)),
                "StandardQueueDays": int(rng.integers(queue_options[0], queue_options[1] + 1)),
            })

        item_mask = items["ItemID"].astype(int).eq(int(item.ItemID))
        items.loc[item_mask, "RoutingID"] = int(routing_id)

    context.tables["Item"] = items[TABLE_COLUMNS["Item"]]
    append_rows(context, "Routing", routing_rows)
    append_rows(context, "RoutingOperation", routing_operation_rows)


def material_inventory_state(context: GenerationContext) -> dict[tuple[int, int], float]:
    inventory = getattr(context, "_manufacturing_material_inventory", None)
    if inventory is None:
        opening_inventory = opening_inventory_map(context)
        material_item_ids = set(
            context.tables["Item"].loc[
                context.tables["Item"]["ItemGroup"].isin(["Raw Materials", "Packaging"]),
                "ItemID",
            ].astype(int).tolist()
        )
        inventory = {
            (item_id, warehouse_id): float(quantity)
            for (item_id, warehouse_id), quantity in opening_inventory.items()
            if int(item_id) in material_item_ids
        }
        setattr(context, "_manufacturing_material_inventory", inventory)
        setattr(context, "_manufacturing_processed_receipt_lines", set())
    return inventory


def sync_material_inventory_receipts(context: GenerationContext, year: int, month: int) -> None:
    inventory = material_inventory_state(context)
    processed_ids: set[int] = getattr(context, "_manufacturing_processed_receipt_lines", set())
    goods_receipts = context.tables["GoodsReceipt"]
    goods_receipt_lines = context.tables["GoodsReceiptLine"]
    if goods_receipts.empty or goods_receipt_lines.empty:
        return

    receipt_headers = goods_receipts.set_index("GoodsReceiptID")[["ReceiptDate", "WarehouseID"]].to_dict("index")
    item_groups = context.tables["Item"].set_index("ItemID")["ItemGroup"].to_dict()
    month_start, month_end = month_bounds(year, month)

    for line in goods_receipt_lines.itertuples(index=False):
        goods_receipt_line_id = int(line.GoodsReceiptLineID)
        if goods_receipt_line_id in processed_ids:
            continue
        header = receipt_headers.get(int(line.GoodsReceiptID))
        if header is None:
            continue
        receipt_date = pd.Timestamp(header["ReceiptDate"])
        if not month_start <= receipt_date <= month_end:
            continue
        if str(item_groups.get(int(line.ItemID))) not in {"Raw Materials", "Packaging"}:
            continue
        key = (int(line.ItemID), int(header["WarehouseID"]))
        inventory[key] = round(float(inventory.get(key, 0.0)) + float(line.QuantityReceived), 2)
        processed_ids.add(goods_receipt_line_id)

    setattr(context, "_manufacturing_processed_receipt_lines", processed_ids)


def work_order_completed_quantity_map(context: GenerationContext) -> dict[int, float]:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completions.empty or completion_lines.empty:
        return {}
    work_order_lookup = completions.set_index("ProductionCompletionID")["WorkOrderID"].astype(int).to_dict()
    totals: dict[int, float] = defaultdict(float)
    for line in completion_lines.itertuples(index=False):
        work_order_id = work_order_lookup.get(int(line.ProductionCompletionID))
        if work_order_id is None:
            continue
        totals[int(work_order_id)] += float(line.QuantityCompleted)
    return {key: qty(value) for key, value in totals.items()}


def work_order_material_issue_cost_map(context: GenerationContext) -> dict[int, float]:
    issues = context.tables["MaterialIssue"]
    issue_lines = context.tables["MaterialIssueLine"]
    if issues.empty or issue_lines.empty:
        return {}
    work_order_lookup = issues.set_index("MaterialIssueID")["WorkOrderID"].astype(int).to_dict()
    totals: dict[int, float] = defaultdict(float)
    for line in issue_lines.itertuples(index=False):
        work_order_id = work_order_lookup.get(int(line.MaterialIssueID))
        if work_order_id is None:
            continue
        totals[int(work_order_id)] += float(line.ExtendedStandardCost)
    return {key: money(value) for key, value in totals.items()}


def work_order_standard_material_cost_map(context: GenerationContext) -> dict[int, float]:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completions.empty or completion_lines.empty:
        return {}
    work_order_lookup = completions.set_index("ProductionCompletionID")["WorkOrderID"].astype(int).to_dict()
    totals: dict[int, float] = defaultdict(float)
    for line in completion_lines.itertuples(index=False):
        work_order_id = work_order_lookup.get(int(line.ProductionCompletionID))
        if work_order_id is None:
            continue
        totals[int(work_order_id)] += float(line.ExtendedStandardMaterialCost)
    return {key: money(value) for key, value in totals.items()}


def work_order_standard_conversion_cost_map(context: GenerationContext) -> dict[int, float]:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completions.empty or completion_lines.empty:
        return {}
    work_order_lookup = completions.set_index("ProductionCompletionID")["WorkOrderID"].astype(int).to_dict()
    totals: dict[int, float] = defaultdict(float)
    for line in completion_lines.itertuples(index=False):
        work_order_id = work_order_lookup.get(int(line.ProductionCompletionID))
        if work_order_id is None:
            continue
        totals[int(work_order_id)] += float(line.ExtendedStandardConversionCost)
    return {key: money(value) for key, value in totals.items()}


def work_order_standard_direct_labor_cost_map(context: GenerationContext) -> dict[int, float]:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completions.empty or completion_lines.empty:
        return {}

    work_order_lookup = completions.set_index("ProductionCompletionID")["WorkOrderID"].astype(int).to_dict()
    totals: dict[int, float] = defaultdict(float)
    for line in completion_lines.itertuples(index=False):
        work_order_id = work_order_lookup.get(int(line.ProductionCompletionID))
        if work_order_id is None:
            continue
        totals[int(work_order_id)] += float(line.ExtendedStandardDirectLaborCost)
    return {key: money(value) for key, value in totals.items()}


def work_order_standard_overhead_cost_map(context: GenerationContext) -> dict[int, float]:
    completions = context.tables["ProductionCompletion"]
    completion_lines = context.tables["ProductionCompletionLine"]
    if completions.empty or completion_lines.empty:
        return {}

    work_order_lookup = completions.set_index("ProductionCompletionID")["WorkOrderID"].astype(int).to_dict()
    totals: dict[int, float] = defaultdict(float)
    for line in completion_lines.itertuples(index=False):
        work_order_id = work_order_lookup.get(int(line.ProductionCompletionID))
        if work_order_id is None:
            continue
        totals[int(work_order_id)] += (
            float(line.ExtendedStandardVariableOverheadCost)
            + float(line.ExtendedStandardFixedOverheadCost)
        )
    return {key: money(value) for key, value in totals.items()}


def work_order_actual_conversion_cost_map(context: GenerationContext) -> dict[int, float]:
    direct_labor = labor_time_direct_cost_by_work_order(context)
    overhead = work_order_overhead_cost_map(context)
    totals: dict[int, float] = defaultdict(float)
    for work_order_id in set(direct_labor) | set(overhead):
        totals[int(work_order_id)] = money(
            float(direct_labor.get(int(work_order_id), 0.0))
            + float(overhead.get(int(work_order_id), 0.0))
        )
    return {key: money(value) for key, value in totals.items()}


def open_work_order_remaining_quantity_map(context: GenerationContext) -> dict[int, float]:
    work_orders = context.tables["WorkOrder"]
    if work_orders.empty:
        return {}
    completed_map = work_order_completed_quantity_map(context)
    remaining: dict[int, float] = {}
    for work_order in work_orders.itertuples(index=False):
        remaining_quantity = qty(float(work_order.PlannedQuantity) - float(completed_map.get(int(work_order.WorkOrderID), 0.0)))
        if remaining_quantity > 0 and str(work_order.Status) != "Closed":
            remaining[int(work_order.WorkOrderID)] = remaining_quantity
    return remaining


def standard_material_unit_cost(context: GenerationContext, bom_id: int) -> float:
    items = context.tables["Item"].set_index("ItemID")
    bom_lines = bom_lines_by_bom(context).get(int(bom_id))
    if bom_lines is None or bom_lines.empty:
        return 0.0
    return money(sum(
        float(items.loc[int(line.ComponentItemID), "StandardCost"]) * float(line.QuantityPerUnit) * (1 + float(line.ScrapFactorPct))
        for line in bom_lines.itertuples(index=False)
    ))


def manufacturing_open_state(context: GenerationContext) -> dict[str, float]:
    work_orders = context.tables["WorkOrder"]
    closes = context.tables["WorkOrderClose"]
    issue_cost = work_order_material_issue_cost_map(context)
    standard_material = work_order_standard_material_cost_map(context)
    actual_conversion = work_order_actual_conversion_cost_map(context)
    standard_conversion = work_order_standard_conversion_cost_map(context)

    material_close = closes.set_index("WorkOrderID")["MaterialVarianceAmount"].astype(float).to_dict() if not closes.empty else {}
    conversion_close = closes.set_index("WorkOrderID")["ConversionVarianceAmount"].astype(float).to_dict() if not closes.empty else {}

    wip_balance = sum(
        float(issue_cost.get(work_order_id, 0.0))
        - float(standard_material.get(work_order_id, 0.0))
        - float(material_close.get(work_order_id, 0.0))
        for work_order_id in set(issue_cost) | set(standard_material) | set(material_close)
    )
    clearing_balance = sum(
        float(actual_conversion.get(work_order_id, 0.0))
        - float(standard_conversion.get(work_order_id, 0.0))
        - float(conversion_close.get(work_order_id, 0.0))
        for work_order_id in set(actual_conversion) | set(standard_conversion) | set(conversion_close)
    )
    variance_posted = float(closes["TotalVarianceAmount"].sum()) if not closes.empty else 0.0
    open_work_orders = int(work_orders["Status"].isin(["Released", "In Progress", "Completed"]).sum()) if not work_orders.empty else 0

    return {
        "manufactured_item_count": float(len(manufactured_items(context))),
        "bom_count": float(len(context.tables["BillOfMaterial"])),
        "bom_line_count": float(len(context.tables["BillOfMaterialLine"])),
        "work_center_count": float(len(context.tables["WorkCenter"])),
        "routing_count": float(len(context.tables["Routing"])),
        "routing_operation_count": float(len(context.tables["RoutingOperation"])),
        "work_order_operation_count": float(len(context.tables["WorkOrderOperation"])),
        "open_work_order_count": float(open_work_orders),
        "wip_balance": money(wip_balance),
        "manufacturing_clearing_balance": money(clearing_balance),
        "manufacturing_variance_posted": money(variance_posted),
    }


def finished_goods_shortage_by_item(context: GenerationContext, month_end: pd.Timestamp) -> dict[int, dict[str, float]]:
    inventory = shadow_inventory_state(context)
    manufactured = manufactured_items(context)
    if manufactured.empty:
        return {}

    sales_orders = context.tables["SalesOrder"]
    sales_order_lines = context.tables["SalesOrderLine"]
    shipped_quantities = sales_order_line_shipped_quantities(context)
    if sales_orders.empty or sales_order_lines.empty:
        return {}

    open_lines = sales_order_lines.copy()
    open_lines["ShippedQuantity"] = open_lines["SalesOrderLineID"].astype(int).map(shipped_quantities).fillna(0.0)
    open_lines["RemainingQuantity"] = (open_lines["Quantity"].astype(float) - open_lines["ShippedQuantity"].astype(float)).round(2)
    open_lines = open_lines[open_lines["RemainingQuantity"].gt(0)]
    if open_lines.empty:
        return {}

    order_lookup = sales_orders.set_index("SalesOrderID")[["OrderDate"]].to_dict("index")
    open_lines["OrderDate"] = open_lines["SalesOrderID"].astype(int).map(
        lambda sales_order_id: order_lookup.get(int(sales_order_id), {}).get("OrderDate")
    )
    open_lines = open_lines[pd.to_datetime(open_lines["OrderDate"]).le(month_end)]
    if open_lines.empty:
        return {}

    demand_by_item = open_lines.groupby("ItemID")["RemainingQuantity"].sum().round(2).to_dict()
    open_work_order_qty = open_work_order_remaining_quantity_map(context)
    open_work_orders = context.tables["WorkOrder"]
    open_completion_by_item: dict[int, float] = defaultdict(float)
    if not open_work_orders.empty:
        for work_order in open_work_orders.itertuples(index=False):
            remaining_quantity = float(open_work_order_qty.get(int(work_order.WorkOrderID), 0.0))
            if remaining_quantity <= 0 or str(work_order.Status) == "Closed":
                continue
            open_completion_by_item[int(work_order.ItemID)] += remaining_quantity

    shortages: dict[int, dict[str, float]] = {}
    for item in manufactured.itertuples(index=False):
        item_id = int(item.ItemID)
        backlog = float(demand_by_item.get(item_id, 0.0))
        if backlog <= 0:
            continue
        item_rng = np.random.default_rng(context.settings.random_seed + item_id * 811)
        buffer_low, buffer_high = FINISHED_GOODS_BUFFER_RANGE.get(str(item.ItemGroup), (6.0, 16.0))
        target_buffer = qty(item_rng.uniform(buffer_low, buffer_high))
        on_hand = round(
            sum(float(quantity) for (inventory_item_id, _), quantity in inventory.items() if int(inventory_item_id) == item_id),
            2,
        )
        scheduled_completion = round(float(open_completion_by_item.get(item_id, 0.0)), 2)
        shortage = qty(backlog + target_buffer - on_hand - scheduled_completion)
        if shortage > 0:
            shortages[item_id] = {
                "backlog": qty(backlog),
                "buffer": target_buffer,
                "on_hand": qty(on_hand),
                "scheduled_completion": qty(scheduled_completion),
                "shortage": shortage,
            }
    return shortages


def build_work_order_operations(
    context: GenerationContext,
    work_order_id: int,
    routing_id: int,
    planned_quantity: float,
    release_date: pd.Timestamp,
    due_date: pd.Timestamp,
) -> list[dict[str, Any]]:
    routing_rows = routing_operations_by_routing(context).get(int(routing_id))
    if routing_rows is None or routing_rows.empty:
        return []

    planning_anchor = pd.Timestamp(release_date)
    due = pd.Timestamp(due_date)
    if due < planning_anchor:
        due = planning_anchor

    operation_hours = [
        float(row.StandardSetupHours) + float(row.StandardRunHoursPerUnit) * float(planned_quantity)
        for row in routing_rows.itertuples(index=False)
    ]
    total_hours = sum(operation_hours) or float(len(operation_hours))
    total_days = max(int((due - planning_anchor).days), len(operation_hours) - 1, 0)
    current_start = planning_anchor
    rows: list[dict[str, Any]] = []

    for index, row in enumerate(routing_rows.itertuples(index=False), start=1):
        if index == len(operation_hours):
            planned_end = max(current_start, due)
        else:
            proportion = float(operation_hours[index - 1]) / total_hours
            duration_days = max(0, int(round(total_days * proportion)))
            remaining_slots = len(operation_hours) - index
            max_end = due - pd.Timedelta(days=remaining_slots)
            planned_end = current_start + pd.Timedelta(days=duration_days)
            if planned_end > max_end:
                planned_end = max(current_start, max_end)
        rows.append({
            "WorkOrderOperationID": next_id(context, "WorkOrderOperation"),
            "WorkOrderID": int(work_order_id),
            "RoutingOperationID": int(row.RoutingOperationID),
            "OperationSequence": int(row.OperationSequence),
            "WorkCenterID": int(row.WorkCenterID),
            "PlannedQuantity": qty(float(planned_quantity)),
            "PlannedStartDate": current_start.strftime("%Y-%m-%d"),
            "PlannedEndDate": planned_end.strftime("%Y-%m-%d"),
            "ActualStartDate": None,
            "ActualEndDate": None,
            "Status": "Released",
        })
        queue_days = int(row.StandardQueueDays)
        current_start = max(planned_end, current_start) + pd.Timedelta(days=queue_days)
        if current_start > due:
            current_start = due

    return rows


def set_work_order_operation_activity(
    context: GenerationContext,
    work_order_id: int,
    activity_start: pd.Timestamp,
    activity_end: pd.Timestamp,
    final_complete: bool,
) -> None:
    mask = context.tables["WorkOrderOperation"]["WorkOrderID"].astype(int).eq(int(work_order_id))
    work_order_operations = context.tables["WorkOrderOperation"].loc[mask].sort_values("OperationSequence").copy()
    if work_order_operations.empty:
        return

    start = pd.Timestamp(activity_start)
    end = pd.Timestamp(activity_end)
    if final_complete:
        windows = sequential_operation_windows(start, end, len(work_order_operations))
        for (row_index, _), (window_start, window_end) in zip(work_order_operations.iterrows(), windows, strict=False):
            context.tables["WorkOrderOperation"].loc[row_index, "ActualStartDate"] = window_start.strftime("%Y-%m-%d")
            context.tables["WorkOrderOperation"].loc[row_index, "ActualEndDate"] = window_end.strftime("%Y-%m-%d")
            context.tables["WorkOrderOperation"].loc[row_index, "Status"] = "Completed"
        return

    if len(work_order_operations) == 1:
        row_index = work_order_operations.index[0]
        context.tables["WorkOrderOperation"].loc[row_index, "ActualStartDate"] = start.strftime("%Y-%m-%d")
        context.tables["WorkOrderOperation"].loc[row_index, "ActualEndDate"] = None
        context.tables["WorkOrderOperation"].loc[row_index, "Status"] = "In Progress"
        return

    completed_windows = sequential_operation_windows(start, end, len(work_order_operations) - 1)
    for (row_index, _), (window_start, window_end) in zip(
        work_order_operations.iloc[:-1].iterrows(),
        completed_windows,
        strict=False,
    ):
        context.tables["WorkOrderOperation"].loc[row_index, "ActualStartDate"] = window_start.strftime("%Y-%m-%d")
        context.tables["WorkOrderOperation"].loc[row_index, "ActualEndDate"] = window_end.strftime("%Y-%m-%d")
        context.tables["WorkOrderOperation"].loc[row_index, "Status"] = "Completed"

    final_row_index = work_order_operations.index[-1]
    final_start = completed_windows[-1][1] if completed_windows else start
    context.tables["WorkOrderOperation"].loc[final_row_index, "ActualStartDate"] = final_start.strftime("%Y-%m-%d")
    context.tables["WorkOrderOperation"].loc[final_row_index, "ActualEndDate"] = None
    context.tables["WorkOrderOperation"].loc[final_row_index, "Status"] = "In Progress"


def generate_month_work_orders_and_requisitions(context: GenerationContext, year: int, month: int) -> None:
    manufactured = manufactured_items(context)
    if manufactured.empty or context.tables["BillOfMaterial"].empty:
        return

    rng = context.rng
    month_start, month_end = month_bounds(year, month)
    shortages = finished_goods_shortage_by_item(context, month_end)
    if not shortages:
        return

    manufacturing_employee_ids = employee_ids_for_cost_center(context, "Manufacturing")
    manufacturing_cost_center = cost_center_id(context, "Manufacturing")
    bom_by_parent = bom_lookup(context)
    bom_lines_lookup = bom_lines_by_bom(context)
    routing_by_parent = active_routing_by_item(context)
    material_items = context.tables["Item"].set_index("ItemID").to_dict("index")
    material_inventory = material_inventory_state(context).copy()
    warehouse_list = warehouse_ids(context)
    requisition_rows: list[dict[str, Any]] = []
    work_order_rows: list[dict[str, Any]] = []
    work_order_operation_rows: list[dict[str, Any]] = []

    for item in manufactured.sort_values("ItemID").itertuples(index=False):
        shortage = shortages.get(int(item.ItemID))
        bom = bom_by_parent.get(int(item.ItemID))
        routing = routing_by_parent.get(int(item.ItemID))
        if shortage is None or bom is None or routing is None:
            continue

        release_date = random_date_between(rng, month_start, min(month_end, month_start + pd.Timedelta(days=9)))
        lead_days = max(int(item.ProductionLeadTimeDays), 1)
        due_date = release_date + pd.Timedelta(days=lead_days)
        if due_date > month_end and rng.random() <= WORK_ORDER_SAME_MONTH_COMPLETION_PROBABILITY:
            due_date = month_end - pd.Timedelta(days=int(rng.integers(0, 3)))
        elif due_date <= month_end and rng.random() > WORK_ORDER_SAME_MONTH_COMPLETION_PROBABILITY:
            due_date = month_end + pd.Timedelta(days=int(rng.integers(3, 15)))

        work_order_id = next_id(context, "WorkOrder")
        warehouse_id = warehouse_list[int((int(item.ItemID) + year + month) % len(warehouse_list))]
        planned_quantity = qty(float(shortage["shortage"]) * rng.uniform(1.00, 1.12))
        work_order_number = format_doc_number("WO", year, work_order_id)
        work_order_rows.append({
            "WorkOrderID": work_order_id,
            "WorkOrderNumber": work_order_number,
            "ItemID": int(item.ItemID),
            "BOMID": int(bom["BOMID"]),
            "RoutingID": int(routing["RoutingID"]),
            "WarehouseID": int(warehouse_id),
            "PlannedQuantity": planned_quantity,
            "ReleasedDate": release_date.strftime("%Y-%m-%d"),
            "DueDate": due_date.strftime("%Y-%m-%d"),
            "CompletedDate": None,
            "ClosedDate": None,
            "Status": "Released",
            "CostCenterID": manufacturing_cost_center,
            "ReleasedByEmployeeID": int(rng.choice(manufacturing_employee_ids)),
            "ClosedByEmployeeID": None,
        })
        work_order_operation_rows.extend(
            build_work_order_operations(
                context,
                work_order_id,
                int(routing["RoutingID"]),
                planned_quantity,
                release_date,
                due_date,
            )
        )

        bom_lines = bom_lines_lookup.get(int(bom["BOMID"]))
        if bom_lines is None or bom_lines.empty:
            continue
        for bom_line in bom_lines.itertuples(index=False):
            component = material_items[int(bom_line.ComponentItemID)]
            required_quantity = qty(planned_quantity * float(bom_line.QuantityPerUnit) * (1 + float(bom_line.ScrapFactorPct)))
            key = (int(bom_line.ComponentItemID), int(warehouse_id))
            available_quantity = qty(material_inventory.get(key, 0.0))
            if available_quantity >= required_quantity:
                material_inventory[key] = qty(available_quantity - required_quantity)
                continue

            shortage_quantity = qty(required_quantity - available_quantity)
            material_inventory[key] = 0.0
            requisition_quantity = qty(shortage_quantity * rng.uniform(*MATERIAL_REQUISITION_BUFFER_FACTOR))
            estimated_unit_cost = money(float(component["StandardCost"]) * rng.uniform(0.98, 1.05))
            requisition_id = next_id(context, "PurchaseRequisition")
            requisition_rows.append({
                "RequisitionID": requisition_id,
                "RequisitionNumber": format_doc_number("PR", year, requisition_id),
                "RequestDate": release_date.strftime("%Y-%m-%d"),
                "RequestedByEmployeeID": int(rng.choice(manufacturing_employee_ids)),
                "CostCenterID": manufacturing_cost_center,
                "ItemID": int(bom_line.ComponentItemID),
                "Quantity": requisition_quantity,
                "EstimatedUnitCost": estimated_unit_cost,
                "Justification": f"Manufacturing replenishment for {work_order_number}",
                "ApprovedByEmployeeID": approver_id(context, requisition_quantity * estimated_unit_cost),
                "ApprovedDate": release_date.strftime("%Y-%m-%d"),
                "Status": "Approved",
            })

    append_rows(context, "WorkOrder", work_order_rows)
    append_rows(context, "WorkOrderOperation", work_order_operation_rows)
    append_rows(context, "PurchaseRequisition", requisition_rows)


def work_orders_due_for_month(context: GenerationContext, year: int, month: int) -> pd.DataFrame:
    work_orders = context.tables["WorkOrder"]
    if work_orders.empty:
        return work_orders.copy()
    _, month_end = month_bounds(year, month)
    remaining = open_work_order_remaining_quantity_map(context)
    candidates = work_orders[
        pd.to_datetime(work_orders["ReleasedDate"]).le(month_end)
        & work_orders["Status"].ne("Closed")
    ].copy()
    candidates["RemainingQuantity"] = candidates["WorkOrderID"].astype(int).map(remaining).fillna(0.0)
    candidates = candidates[candidates["RemainingQuantity"].gt(0)].copy()
    return candidates.sort_values(["DueDate", "ReleasedDate", "WorkOrderID"]).reset_index(drop=True)


def update_work_order_row(
    context: GenerationContext,
    work_order_id: int,
    status: str,
    completed_date: str | None = None,
    closed_date: str | None = None,
    closed_by_employee_id: int | None = None,
) -> None:
    mask = context.tables["WorkOrder"]["WorkOrderID"].astype(int).eq(int(work_order_id))
    context.tables["WorkOrder"].loc[mask, "Status"] = status
    if completed_date is not None:
        context.tables["WorkOrder"].loc[mask, "CompletedDate"] = completed_date
    if closed_date is not None:
        context.tables["WorkOrder"].loc[mask, "ClosedDate"] = closed_date
    if closed_by_employee_id is not None:
        context.tables["WorkOrder"].loc[mask, "ClosedByEmployeeID"] = int(closed_by_employee_id)


def split_quantities(total_quantity: float, event_count: int, rng: np.random.Generator) -> list[float]:
    if event_count <= 1:
        return [qty(total_quantity)]
    if total_quantity <= 0:
        return [0.0 for _ in range(event_count)]

    remaining = qty(total_quantity)
    quantities: list[float] = []
    for event_index in range(event_count - 1):
        remaining_slots = event_count - event_index - 1
        if remaining <= 0:
            quantities.append(0.0)
            continue
        minimum_reserved = 0.01 * remaining_slots
        if remaining <= minimum_reserved:
            quantities.append(0.0)
            continue
        share = rng.uniform(0.40, 0.65) if event_count == 2 else rng.uniform(0.18, 0.52)
        current_quantity = qty(min(remaining - minimum_reserved, remaining * share))
        quantities.append(current_quantity)
        remaining = qty(remaining - current_quantity)

    quantities.append(qty(max(remaining, 0.0)))
    while len(quantities) < event_count:
        quantities.append(0.0)
    return quantities[:event_count]


def generate_month_manufacturing_activity(context: GenerationContext, year: int, month: int) -> None:
    candidates = work_orders_due_for_month(context, year, month)
    if candidates.empty:
        return

    rng = context.rng
    month_start, month_end = month_bounds(year, month)
    sync_material_inventory_receipts(context, year, month)
    material_inventory = material_inventory_state(context)
    fg_inventory = shadow_inventory_state(context)
    items = context.tables["Item"].set_index("ItemID").to_dict("index")
    bom_lines_lookup = bom_lines_by_bom(context)
    manufacturing_employee_ids = employee_ids_for_cost_center(context, "Manufacturing")
    completed_quantities = work_order_completed_quantity_map(context)
    issue_headers: list[dict[str, Any]] = []
    issue_lines: list[dict[str, Any]] = []
    completion_headers: list[dict[str, Any]] = []
    completion_lines: list[dict[str, Any]] = []

    for work_order in candidates.itertuples(index=False):
        work_order_id = int(work_order.WorkOrderID)
        remaining_quantity = qty(float(work_order.RemainingQuantity))
        if remaining_quantity <= 0:
            continue

        bom_lines = bom_lines_lookup.get(int(work_order.BOMID))
        if bom_lines is None or bom_lines.empty:
            continue

        release_date = pd.Timestamp(work_order.ReleasedDate)
        work_order_age_months = (year - release_date.year) * 12 + (month - release_date.month)
        if work_order_age_months >= 1:
            target_completion_quantity = remaining_quantity
        else:
            if rng.random() <= WORK_ORDER_SAME_MONTH_COMPLETION_PROBABILITY:
                target_completion_quantity = remaining_quantity
            else:
                target_completion_quantity = qty(remaining_quantity * rng.uniform(*WORK_ORDER_PARTIAL_COMPLETION_RANGE))

        max_material_supported_quantity = remaining_quantity
        for bom_line in bom_lines.itertuples(index=False):
            required_per_unit = float(bom_line.QuantityPerUnit) * (1 + float(bom_line.ScrapFactorPct))
            available_quantity = float(material_inventory.get((int(bom_line.ComponentItemID), int(work_order.WarehouseID)), 0.0))
            supported_quantity = available_quantity / required_per_unit if required_per_unit > 0 else remaining_quantity
            max_material_supported_quantity = min(max_material_supported_quantity, supported_quantity)

        completion_quantity = qty(min(target_completion_quantity, max_material_supported_quantity))
        if completion_quantity <= 0:
            update_work_order_row(context, work_order_id, "Released")
            continue

        issue_event_count = choose_count(rng, ISSUE_EVENT_COUNT_PROBABILITIES)
        issue_dates = [
            random_date_between(rng, max(month_start, release_date), min(month_end, pd.Timestamp(work_order.DueDate)))
            for _ in range(issue_event_count)
        ]
        issue_dates = sorted(issue_dates)
        issue_quantities_by_line = {
            int(bom_line.BOMLineID): split_quantities(
                qty(
                    completion_quantity
                    * float(bom_line.QuantityPerUnit)
                    * (1 + float(bom_line.ScrapFactorPct))
                    * rng.uniform(*ISSUE_FACTOR_RANGE)
                ),
                issue_event_count,
                rng,
            )
            for bom_line in bom_lines.itertuples(index=False)
        }

        issue_line_number_by_header: dict[int, int] = {}
        for event_index, issue_date in enumerate(issue_dates):
            material_issue_id = next_id(context, "MaterialIssue")
            issue_headers.append({
                "MaterialIssueID": material_issue_id,
                "IssueNumber": format_doc_number("MI", year, material_issue_id),
                "WorkOrderID": work_order_id,
                "IssueDate": issue_date.strftime("%Y-%m-%d"),
                "WarehouseID": int(work_order.WarehouseID),
                "IssuedByEmployeeID": int(rng.choice(manufacturing_employee_ids)),
                "Status": "Issued",
            })
            issue_line_number_by_header[material_issue_id] = 1

            for bom_line in bom_lines.itertuples(index=False):
                issue_quantity = qty(issue_quantities_by_line[int(bom_line.BOMLineID)][event_index])
                if issue_quantity <= 0:
                    continue
                key = (int(bom_line.ComponentItemID), int(work_order.WarehouseID))
                available_quantity = qty(material_inventory.get(key, 0.0))
                issue_quantity = min(issue_quantity, available_quantity)
                if issue_quantity <= 0:
                    continue
                material_inventory[key] = qty(available_quantity - issue_quantity)
                component = items[int(bom_line.ComponentItemID)]
                issue_lines.append({
                    "MaterialIssueLineID": next_id(context, "MaterialIssueLine"),
                    "MaterialIssueID": material_issue_id,
                    "BOMLineID": int(bom_line.BOMLineID),
                    "LineNumber": issue_line_number_by_header[material_issue_id],
                    "ItemID": int(bom_line.ComponentItemID),
                    "QuantityIssued": issue_quantity,
                    "ExtendedStandardCost": money(issue_quantity * float(component["StandardCost"])),
                })
                issue_line_number_by_header[material_issue_id] += 1

        completion_event_count = choose_count(rng, COMPLETION_EVENT_COUNT_PROBABILITIES)
        due_date = pd.Timestamp(work_order.DueDate)
        completion_dates = [
            random_date_between(rng, max(issue_dates[-1] if issue_dates else month_start, month_start), min(month_end, due_date if due_date <= month_end else month_end))
            for _ in range(completion_event_count)
        ]
        completion_dates = sorted(completion_dates)
        completion_quantities = split_quantities(completion_quantity, completion_event_count, rng)
        item = items[int(work_order.ItemID)]
        standard_material_unit = standard_material_unit_cost(context, int(work_order.BOMID))

        for completion_date, completion_qty in zip(completion_dates, completion_quantities):
            if completion_qty <= 0:
                continue
            completion_id = next_id(context, "ProductionCompletion")
            completion_headers.append({
                "ProductionCompletionID": completion_id,
                "CompletionNumber": format_doc_number("PC", year, completion_id),
                "WorkOrderID": work_order_id,
                "CompletionDate": completion_date.strftime("%Y-%m-%d"),
                "WarehouseID": int(work_order.WarehouseID),
                "ReceivedByEmployeeID": int(rng.choice(manufacturing_employee_ids)),
                "Status": "Completed",
            })
            standard_material_cost = money(completion_qty * standard_material_unit)
            standard_direct_labor_cost = money(completion_qty * float(item["StandardDirectLaborCost"]))
            standard_variable_overhead_cost = money(completion_qty * float(item["StandardVariableOverheadCost"]))
            standard_fixed_overhead_cost = money(completion_qty * float(item["StandardFixedOverheadCost"]))
            standard_conversion_cost = money(
                standard_direct_labor_cost
                + standard_variable_overhead_cost
                + standard_fixed_overhead_cost
            )
            total_cost = money(standard_material_cost + standard_conversion_cost)
            completion_lines.append({
                "ProductionCompletionLineID": next_id(context, "ProductionCompletionLine"),
                "ProductionCompletionID": completion_id,
                "LineNumber": 1,
                "ItemID": int(work_order.ItemID),
                "QuantityCompleted": completion_qty,
                "ExtendedStandardMaterialCost": standard_material_cost,
                "ExtendedStandardDirectLaborCost": standard_direct_labor_cost,
                "ExtendedStandardVariableOverheadCost": standard_variable_overhead_cost,
                "ExtendedStandardFixedOverheadCost": standard_fixed_overhead_cost,
                "ExtendedStandardConversionCost": standard_conversion_cost,
                "ExtendedStandardTotalCost": total_cost,
            })
            fg_key = (int(work_order.ItemID), int(work_order.WarehouseID))
            fg_inventory[fg_key] = qty(float(fg_inventory.get(fg_key, 0.0)) + completion_qty)

        completed_total = qty(float(completed_quantities.get(work_order_id, 0.0)) + sum(completion_quantities))
        activity_start = issue_dates[0] if issue_dates else max(month_start, release_date)
        if completed_total >= qty(float(work_order.PlannedQuantity)):
            set_work_order_operation_activity(
                context,
                work_order_id,
                activity_start,
                completion_dates[-1],
                final_complete=True,
            )
            update_work_order_row(
                context,
                work_order_id,
                "Completed",
                completed_date=completion_dates[-1].strftime("%Y-%m-%d"),
            )
        else:
            set_work_order_operation_activity(
                context,
                work_order_id,
                activity_start,
                completion_dates[-1],
                final_complete=False,
            )
            update_work_order_row(context, work_order_id, "In Progress")

    append_rows(context, "MaterialIssue", issue_headers)
    append_rows(context, "MaterialIssueLine", issue_lines)
    append_rows(context, "ProductionCompletion", completion_headers)
    append_rows(context, "ProductionCompletionLine", completion_lines)


def final_work_order_activity_dates(context: GenerationContext) -> dict[int, pd.Timestamp]:
    final_dates: dict[int, pd.Timestamp] = {}
    issues = context.tables["MaterialIssue"]
    completions = context.tables["ProductionCompletion"]
    operations = context.tables["WorkOrderOperation"]
    for issue in issues.itertuples(index=False):
        final_dates[int(issue.WorkOrderID)] = max(
            final_dates.get(int(issue.WorkOrderID), pd.Timestamp.min),
            pd.Timestamp(issue.IssueDate),
        )
    for completion in completions.itertuples(index=False):
        final_dates[int(completion.WorkOrderID)] = max(
            final_dates.get(int(completion.WorkOrderID), pd.Timestamp.min),
            pd.Timestamp(completion.CompletionDate),
        )
    for operation in operations.itertuples(index=False):
        if pd.notna(operation.ActualEndDate):
            final_dates[int(operation.WorkOrderID)] = max(
                final_dates.get(int(operation.WorkOrderID), pd.Timestamp.min),
                pd.Timestamp(operation.ActualEndDate),
            )
    return final_dates


def close_eligible_work_orders(context: GenerationContext, year: int, month: int) -> None:
    work_orders = context.tables["WorkOrder"]
    if work_orders.empty:
        return

    month_start, month_end = month_bounds(year, month)
    completed_map = work_order_completed_quantity_map(context)
    issue_cost_map = work_order_material_issue_cost_map(context)
    standard_material_map = work_order_standard_material_cost_map(context)
    standard_direct_labor_map = work_order_standard_direct_labor_cost_map(context)
    standard_overhead_map = work_order_standard_overhead_cost_map(context)
    actual_direct_labor_map = labor_time_direct_cost_by_work_order(context)
    actual_overhead_map = work_order_overhead_cost_map(context)
    activity_dates = final_work_order_activity_dates(context)
    manufacturing_employee_ids = employee_ids_for_cost_center(context, "Manufacturing")
    close_rows: list[dict[str, Any]] = []

    for work_order in work_orders.sort_values("WorkOrderID").itertuples(index=False):
        if str(work_order.Status) == "Closed":
            continue
        if pd.isna(work_order.CompletedDate):
            continue
        completed_quantity = float(completed_map.get(int(work_order.WorkOrderID), 0.0))
        if round(completed_quantity, 2) < round(float(work_order.PlannedQuantity), 2):
            continue

        completed_date = pd.Timestamp(work_order.CompletedDate)
        if completed_date > month_end:
            continue
        if int(work_order.WorkOrderID) not in actual_direct_labor_map:
            continue

        activity_date = max(activity_dates.get(int(work_order.WorkOrderID), completed_date), completed_date)
        close_date = min(month_end, next_business_day(activity_date + pd.Timedelta(days=2)))
        if close_date < month_start:
            close_date = month_start

        material_variance = money(
            float(issue_cost_map.get(int(work_order.WorkOrderID), 0.0))
            - float(standard_material_map.get(int(work_order.WorkOrderID), 0.0))
        )
        direct_labor_variance = money(
            float(actual_direct_labor_map.get(int(work_order.WorkOrderID), 0.0))
            - float(standard_direct_labor_map.get(int(work_order.WorkOrderID), 0.0))
        )
        overhead_variance = money(
            float(actual_overhead_map.get(int(work_order.WorkOrderID), 0.0))
            - float(standard_overhead_map.get(int(work_order.WorkOrderID), 0.0))
        )
        conversion_variance = money(direct_labor_variance + overhead_variance)
        close_rows.append({
            "WorkOrderCloseID": next_id(context, "WorkOrderClose"),
            "WorkOrderID": int(work_order.WorkOrderID),
            "CloseDate": close_date.strftime("%Y-%m-%d"),
            "MaterialVarianceAmount": material_variance,
            "DirectLaborVarianceAmount": direct_labor_variance,
            "OverheadVarianceAmount": overhead_variance,
            "ConversionVarianceAmount": conversion_variance,
            "TotalVarianceAmount": money(material_variance + conversion_variance),
            "Status": "Closed",
            "ClosedByEmployeeID": int(
                manufacturing_employee_ids[(int(work_order.WorkOrderID) + year + month) % len(manufacturing_employee_ids)]
            ),
        })
        update_work_order_row(
            context,
            int(work_order.WorkOrderID),
            "Closed",
            completed_date=completed_date.strftime("%Y-%m-%d"),
            closed_date=close_date.strftime("%Y-%m-%d"),
            closed_by_employee_id=int(close_rows[-1]["ClosedByEmployeeID"]),
        )

    append_rows(context, "WorkOrderClose", close_rows)
