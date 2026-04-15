from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from CharlesRiver_dataset.budgets import generate_budgets, generate_opening_balances
from CharlesRiver_dataset.main import (
    _generate_phase2_master_data_and_planning,
    build_phase22,
    close_generation_logging,
    configure_generation_logging,
    logged_step,
)
from CharlesRiver_dataset.manufacturing import (
    generate_boms,
    generate_work_center_calendars,
    generate_work_centers_and_routings,
)
from CharlesRiver_dataset.master_data import (
    approver_employee_id,
    backfill_cost_center_managers,
    current_role_employee_id,
    generate_cost_centers,
    generate_customers,
    generate_employees,
    generate_items,
    generate_suppliers,
    generate_warehouses,
    load_accounts,
)
from CharlesRiver_dataset.payroll import generate_payroll_periods, generate_shift_definitions_and_assignments
from CharlesRiver_dataset.planning import (
    forecast_approver_id,
    forecast_planner_id,
    generate_demand_forecasts,
    generate_inventory_policies,
    week_starts_in_fiscal_range,
)
from CharlesRiver_dataset.schema import create_empty_tables
from CharlesRiver_dataset.settings import initialize_context, load_settings
from CharlesRiver_dataset.validations import validate_phase1


def _prepare_forecast_context(config_path: str) -> object:
    settings = load_settings(config_path)
    context = initialize_context(settings)
    create_empty_tables(context)
    generate_cost_centers(context)
    load_accounts(context, accounts_path="config/accounts.csv")
    generate_employees(context)
    backfill_cost_center_managers(context)
    generate_warehouses(context)
    generate_items(context)
    generate_boms(context)
    generate_work_centers_and_routings(context)
    generate_work_center_calendars(context)
    generate_customers(context)
    generate_suppliers(context)
    generate_opening_balances(context)
    generate_budgets(context)
    generate_payroll_periods(context)
    generate_shift_definitions_and_assignments(context)
    generate_inventory_policies(context)
    return context


def _expected_forecast_roles(context: object, supply_mode: str, event_date: pd.Timestamp) -> tuple[int, int]:
    if supply_mode == "Manufactured":
        planner_id = None
        for title in ["Production Planner", "Production Manager"]:
            planner_id = current_role_employee_id(context, title)
            if planner_id is not None:
                break
        if planner_id is None:
            planner_id = approver_employee_id(
                context,
                event_date,
                preferred_titles=["Production Manager", "Chief Financial Officer"],
                fallback_cost_center_name="Manufacturing",
            )
        approver_id = approver_employee_id(
            context,
            event_date,
            preferred_titles=["Production Manager", "Chief Financial Officer"],
            fallback_cost_center_name="Manufacturing",
        )
        return int(planner_id), int(approver_id)

    planner_id = None
    for title in ["Buyer", "Purchasing Manager", "Procurement Analyst"]:
        planner_id = current_role_employee_id(context, title)
        if planner_id is not None:
            break
    if planner_id is None:
        planner_id = approver_employee_id(
            context,
            event_date,
            preferred_titles=["Purchasing Manager", "Chief Financial Officer"],
            fallback_cost_center_name="Purchasing",
        )
    approver_id = approver_employee_id(
        context,
        event_date,
        preferred_titles=["Purchasing Manager", "Chief Financial Officer", "Controller"],
        fallback_cost_center_name="Purchasing",
    )
    return int(planner_id), int(approver_id)


def test_phase22_1_forecasts_complete_quickly_on_validation_profile() -> None:
    context = _prepare_forecast_context("config/settings_validation.yaml")

    started_at = time.perf_counter()
    generate_demand_forecasts(context)
    elapsed = time.perf_counter() - started_at

    assert elapsed < 15.0
    assert not context.tables["DemandForecast"].empty


def test_phase22_1_forecasts_are_deterministic() -> None:
    context_one = _prepare_forecast_context("config/settings_validation.yaml")
    context_two = _prepare_forecast_context("config/settings_validation.yaml")

    generate_demand_forecasts(context_one)
    generate_demand_forecasts(context_two)

    pd.testing.assert_frame_equal(
        context_one.tables["DemandForecast"].reset_index(drop=True),
        context_two.tables["DemandForecast"].reset_index(drop=True),
        check_dtype=False,
    )


def test_phase22_1_cached_role_resolution_matches_existing_rules() -> None:
    context = _prepare_forecast_context("config/settings_validation.yaml")
    weeks = week_starts_in_fiscal_range(context)
    sample_weeks = [weeks[0], weeks[len(weeks) // 2], weeks[-1]]

    planner_role_cache: dict[tuple[str, str], tuple[int, int]] = {}
    approver_role_cache: dict[tuple[str, str], tuple[int, int]] = {}
    for supply_mode in ["Manufactured", "Purchased"]:
        for bucket_start in sample_weeks:
            expected_planner_id, expected_approver_id = _expected_forecast_roles(context, supply_mode, bucket_start)
            actual_planner_id = forecast_planner_id(context, supply_mode, bucket_start, role_cache=planner_role_cache)
            actual_approver_id = forecast_approver_id(context, supply_mode, bucket_start, role_cache=approver_role_cache)

            assert actual_planner_id == expected_planner_id
            assert actual_approver_id == expected_approver_id


def test_phase22_1_logged_phase2_substeps_and_progress_markers(tmp_path: Path) -> None:
    settings = load_settings("config/settings.yaml")
    log_path = tmp_path / "phase2_default.log"
    context = initialize_context(settings)

    configure_generation_logging(log_path)
    try:
        with logged_step("Create empty schema"):
            create_empty_tables(context)
        with logged_step("Generate phase 1 master data"):
            generate_cost_centers(context)
            load_accounts(context, accounts_path="config/accounts.csv")
            generate_employees(context)
            backfill_cost_center_managers(context)
            generate_warehouses(context)
        with logged_step("Validate phase 1"):
            validate_phase1(context)
        with logged_step("Generate phase 2 master data and planning data"):
            _generate_phase2_master_data_and_planning(context, log_substeps=True)
    finally:
        close_generation_logging()

    log_text = log_path.read_text(encoding="utf-8")
    assert "START | Generate phase 2 item master" in log_text
    assert "DONE | Generate phase 2 demand forecasts" in log_text
    assert "DEMAND FORECAST PROGRESS |" in log_text


def test_phase22_1_clean_build_still_validates() -> None:
    context = build_phase22("config/settings_validation.yaml", validation_scope="full")
    phase22 = context.validation_results["phase22"]

    assert phase22["exceptions"] == []
    assert phase22["planning_controls"]["exception_count"] == 0
