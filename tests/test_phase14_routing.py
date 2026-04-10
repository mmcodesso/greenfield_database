from __future__ import annotations

import pandas as pd

from greenfield_dataset.main import build_phase2, build_phase14
from greenfield_dataset.schema import TABLE_COLUMNS


def test_phase14_schema_extensions_exist() -> None:
    for table_name in [
        "WorkCenter",
        "Routing",
        "RoutingOperation",
        "WorkOrderOperation",
    ]:
        assert table_name in TABLE_COLUMNS

    assert "RoutingID" in TABLE_COLUMNS["Item"]
    assert "RoutingID" in TABLE_COLUMNS["WorkOrder"]
    assert "WorkOrderOperationID" in TABLE_COLUMNS["LaborTimeEntry"]


def test_phase14_master_data_generates_routings_and_work_centers() -> None:
    context = build_phase2()

    items = context.tables["Item"]
    manufactured = items[
        items["SupplyMode"].eq("Manufactured")
        & items["RevenueAccountID"].notna()
        & items["IsActive"].eq(1)
    ].copy()
    purchased_sellable = items[
        items["SupplyMode"].ne("Manufactured")
        & items["RevenueAccountID"].notna()
        & items["IsActive"].eq(1)
    ].copy()
    work_centers = context.tables["WorkCenter"]
    routings = context.tables["Routing"]
    routing_operations = context.tables["RoutingOperation"]

    assert len(work_centers) >= 4
    assert len(routings) == len(manufactured)
    assert manufactured["RoutingID"].notna().all()
    assert purchased_sellable["RoutingID"].isna().all()

    operation_counts = routing_operations.groupby("RoutingID").size()
    assert operation_counts.between(2, 4).all()


def test_phase14_helper_generates_clean_routing_dataset() -> None:
    context = build_phase14()
    phase14 = context.validation_results["phase14"]

    assert phase14["exceptions"] == []
    assert phase14["routing_controls"]["exception_count"] == 0
    assert len(context.tables["WorkOrderOperation"]) > len(context.tables["WorkOrder"])

    direct_entries = context.tables["LaborTimeEntry"][
        context.tables["LaborTimeEntry"]["LaborType"].eq("Direct Manufacturing")
    ].copy()
    assert len(direct_entries) > 0
    assert direct_entries["WorkOrderOperationID"].notna().all()

    work_order_operations = context.tables["WorkOrderOperation"].set_index("WorkOrderOperationID")
    assert (
        direct_entries["WorkOrderOperationID"].astype(int).map(work_order_operations["WorkOrderID"]).astype(int)
        == direct_entries["WorkOrderID"].astype(int)
    ).all()

    completed_operations = context.tables["WorkOrderOperation"][
        context.tables["WorkOrderOperation"]["ActualEndDate"].notna()
    ].copy()
    if not completed_operations.empty:
        completed_operations["ActualStartDate"] = pd.to_datetime(completed_operations["ActualStartDate"])
        completed_operations["ActualEndDate"] = pd.to_datetime(completed_operations["ActualEndDate"])
        for _, rows in completed_operations.sort_values(["WorkOrderID", "OperationSequence"]).groupby("WorkOrderID"):
            prior_end = None
            for row in rows.itertuples(index=False):
                if prior_end is not None:
                    assert pd.Timestamp(row.ActualStartDate) >= prior_end
                prior_end = pd.Timestamp(row.ActualEndDate)


def test_phase14_full_dataset_clean_validation(full_dataset_artifacts: dict[str, object]) -> None:
    context = full_dataset_artifacts["context"]
    phase14 = context.validation_results["phase14"]
    row_counts = phase14["row_counts"]

    assert phase14["exceptions"] == []
    assert phase14["gl_balance"]["exception_count"] == 0
    assert phase14["trial_balance_difference"] == 0
    assert phase14["account_rollforward"]["exception_count"] == 0
    assert phase14["o2c_controls"]["exception_count"] == 0
    assert phase14["p2p_controls"]["exception_count"] == 0
    assert phase14["journal_controls"]["exception_count"] == 0
    assert phase14["manufacturing_controls"]["exception_count"] == 0
    assert phase14["payroll_controls"]["exception_count"] == 0
    assert phase14["routing_controls"]["exception_count"] == 0

    assert row_counts["WorkCenter"] > 0
    assert row_counts["Routing"] > 0
    assert row_counts["RoutingOperation"] > row_counts["Routing"]
    assert row_counts["WorkOrderOperation"] > row_counts["WorkOrder"]
