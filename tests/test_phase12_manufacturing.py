from __future__ import annotations

from generator_dataset.main import build_phase2, build_phase12
from generator_dataset.manufacturing import MANUFACTURED_ITEM_SHARE_MAX, MANUFACTURED_ITEM_SHARE_MIN
from generator_dataset.schema import TABLE_COLUMNS


def test_phase12_schema_extensions_exist() -> None:
    assert "SupplyMode" in TABLE_COLUMNS["Item"]
    assert "ProductionLeadTimeDays" in TABLE_COLUMNS["Item"]
    assert "StandardConversionCost" in TABLE_COLUMNS["Item"]

    for table_name in [
        "BillOfMaterial",
        "BillOfMaterialLine",
        "WorkOrder",
        "MaterialIssue",
        "MaterialIssueLine",
        "ProductionCompletion",
        "ProductionCompletionLine",
        "WorkOrderClose",
    ]:
        assert table_name in TABLE_COLUMNS


def test_phase12_master_data_generates_manufactured_items_and_boms() -> None:
    context = build_phase2()

    items = context.tables["Item"]
    active_sellable = items[items["RevenueAccountID"].notna() & items["IsActive"].eq(1)].copy()
    manufactured = active_sellable[active_sellable["SupplyMode"].eq("Manufactured")].copy()
    boms = context.tables["BillOfMaterial"]
    bom_lines = context.tables["BillOfMaterialLine"]

    manufactured_share = len(manufactured) / max(len(active_sellable), 1)
    assert MANUFACTURED_ITEM_SHARE_MIN <= manufactured_share <= MANUFACTURED_ITEM_SHARE_MAX
    assert len(boms) == len(manufactured)
    assert boms["ParentItemID"].astype(int).is_unique

    active_bom_parent_ids = set(boms.loc[boms["Status"].eq("Active"), "ParentItemID"].astype(int))
    assert set(manufactured["ItemID"].astype(int)) == active_bom_parent_ids

    item_groups = items.set_index("ItemID")["ItemGroup"].to_dict()
    assert bom_lines["ComponentItemID"].map(item_groups).isin(["Raw Materials", "Packaging"]).all()


def test_phase12_helper_generates_clean_multimonth_manufacturing_dataset() -> None:
    context = build_phase12()
    phase12 = context.validation_results["phase12"]

    assert phase12["exceptions"] == []
    assert phase12["manufacturing_controls"]["exception_count"] == 0
    assert len(context.tables["WorkOrder"]) > 0
    assert len(context.tables["MaterialIssueLine"]) > 0
    assert len(context.tables["ProductionCompletionLine"]) > 0
    assert len(context.tables["WorkOrderClose"]) > 0

    items = context.tables["Item"].set_index("ItemID")
    work_orders = context.tables["WorkOrder"]
    assert work_orders["ItemID"].map(items["SupplyMode"]).eq("Manufactured").all()

    completed_by_work_order = (
        context.tables["ProductionCompletionLine"]
        .merge(context.tables["ProductionCompletion"][["ProductionCompletionID", "WorkOrderID"]], on="ProductionCompletionID", how="left")
        .groupby("WorkOrderID")["QuantityCompleted"]
        .sum()
    )
    planned_by_work_order = work_orders.set_index("WorkOrderID")["PlannedQuantity"].astype(float)
    assert all(
        round(float(completed_by_work_order.get(work_order_id, 0.0)), 2) <= round(float(planned_quantity), 2)
        for work_order_id, planned_quantity in planned_by_work_order.items()
    )


def test_phase12_full_dataset_clean_validation(full_dataset_artifacts: dict[str, object]) -> None:
    context = full_dataset_artifacts["context"]
    phase12 = context.validation_results["phase12"]
    row_counts = phase12["row_counts"]

    assert phase12["exceptions"] == []
    assert phase12["gl_balance"]["exception_count"] == 0
    assert phase12["trial_balance_difference"] == 0
    assert phase12["account_rollforward"]["exception_count"] == 0
    assert phase12["o2c_controls"]["exception_count"] == 0
    assert phase12["p2p_controls"]["exception_count"] == 0
    assert phase12["journal_controls"]["exception_count"] == 0
    assert phase12["manufacturing_controls"]["exception_count"] == 0

    assert row_counts["BillOfMaterial"] > 0
    assert row_counts["BillOfMaterialLine"] > row_counts["BillOfMaterial"]
    assert row_counts["WorkOrder"] > 0
    assert row_counts["MaterialIssueLine"] > 0
    assert row_counts["ProductionCompletionLine"] > 0
    assert row_counts["WorkOrderClose"] > 0
