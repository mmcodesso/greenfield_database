from __future__ import annotations

from pathlib import Path

import pandas as pd

from generator_dataset.manufacturing import work_order_schedule_bounds


def test_phase23_6_inventory_policies_use_execution_window(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    context = clean_validation_dataset_artifacts["context"]
    items = context.tables["Item"][["ItemID", "ItemGroup", "SupplyMode"]].copy()
    policies = context.tables["InventoryPolicy"].merge(items, on="ItemID", how="left")

    manufactured = policies[policies["SupplyMode"].eq("Manufactured")].copy()
    assert not manufactured.empty
    assert manufactured["PlanningLeadTimeDays"].astype(int).between(21, 42).all()

    raw_materials = policies[policies["ItemGroup"].eq("Raw Materials")].copy()
    packaging = policies[policies["ItemGroup"].eq("Packaging")].copy()
    assert not raw_materials.empty
    assert not packaging.empty
    assert raw_materials["PlanningLeadTimeDays"].astype(int).ge(24).all()
    assert packaging["PlanningLeadTimeDays"].astype(int).ge(21).all()


def test_phase23_6_released_work_orders_stay_close_to_schedule(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    context = clean_validation_dataset_artifacts["context"]
    work_orders = context.tables["WorkOrder"].copy()
    released = work_orders[work_orders["Status"].eq("Released")].copy()
    if released.empty:
        return

    schedule_bounds = work_order_schedule_bounds(context)
    released["FirstScheduledDate"] = released["WorkOrderID"].astype(int).map(
        lambda work_order_id: schedule_bounds.get(int(work_order_id), (pd.NaT, pd.NaT))[0]
    )
    released["ReleasedDateTS"] = pd.to_datetime(released["ReleasedDate"], errors="coerce")
    released["FirstScheduledDateTS"] = pd.to_datetime(released["FirstScheduledDate"], errors="coerce")

    assert released["FirstScheduledDateTS"].notna().all()
    lead_days = (released["FirstScheduledDateTS"] - released["ReleasedDateTS"]).dt.days
    assert lead_days.le(45).all()


def test_phase23_6_generation_log_includes_backlog_diagnostics(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    log_text = Path(clean_validation_dataset_artifacts["generation_log_path"]).read_text(encoding="utf-8")
    assert "MANUFACTURING BACKLOG | 2026-01 |" in log_text
    for field_name in [
        "open_released_work_orders",
        "open_released_no_actual_start",
        "avg_days_release_to_first_sched_open",
        "oldest_open_due_date",
        "open_due_before_month_end",
        "open_due_before_year_end",
    ]:
        assert f"{field_name}=" in log_text
