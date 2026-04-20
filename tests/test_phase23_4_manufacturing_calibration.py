from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest
import yaml

from generator_dataset.manufacturing import manufacturing_capacity_diagnostics_by_code
from generator_dataset.main import build_full_dataset, build_phase1, build_phase23
from generator_dataset.master_data import STANDARD_LABOR_HOURS_RANGE, manufacturing_staffing_targets
from generator_dataset.settings import load_settings
from generator_dataset.workforce_capacity import (
    DIRECT_MANUFACTURING_TITLES,
    STANDARD_MANUFACTURING_SHIFT_HOURS,
)


@pytest.fixture(scope="session")
def phase23_4_one_year_clean_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("phase23_4_one_year_clean")
    settings = load_settings("config/settings.yaml")
    payload = dict(vars(settings))
    payload.update({
        "anomaly_mode": "none",
        "export_sqlite": False,
        "export_excel": False,
        "export_support_excel": False,
        "export_csv_zip": False,
        "export_reports": False,
        "fiscal_year_end": "2026-12-31",
        "generation_log_path": str(workdir / "generation.log"),
    })

    config_path = workdir / "settings_phase23_4_one_year.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    context = build_full_dataset(str(config_path))
    return {
        "context": context,
        "workdir": workdir,
        "generation_log_path": Path(payload["generation_log_path"]),
    }


def test_phase23_4_phase1_staffing_targets_default_and_validation() -> None:
    default_context = build_phase1("config/settings.yaml")
    validation_context = build_phase1("config/settings_validation.yaml")

    for context in [default_context, validation_context]:
        expected = manufacturing_staffing_targets(int(context.settings.employee_count))
        assert expected is not None
        active_employees = context.tables["Employee"][context.tables["Employee"]["IsActive"].astype(int).eq(1)].copy()
        title_counts = active_employees["JobTitle"].value_counts().to_dict()
        for title, expected_count in expected.items():
            assert int(title_counts.get(title, 0)) == expected_count
        for title in ["Production Manager", "Production Supervisor", "Production Planner"]:
            assert int(title_counts.get(title, 0)) == 1


def test_phase23_4_manufactured_item_hours_and_conversion_costs_are_calibrated() -> None:
    context = build_phase23("config/settings_validation.yaml", validation_scope="full")
    items = context.tables["Item"].copy()
    manufactured_sellable = items[
        items["SupplyMode"].eq("Manufactured")
        & items["RevenueAccountID"].notna()
    ].copy()

    assert not manufactured_sellable.empty

    for row in manufactured_sellable.itertuples(index=False):
        item_group = str(row.ItemGroup)
        original_hours_high = float(STANDARD_LABOR_HOURS_RANGE[item_group][1])
        assert float(row.StandardLaborHoursPerUnit) <= round(original_hours_high * 0.95, 2) + 0.01
        expected_conversion_cost = round(
            float(row.StandardDirectLaborCost)
            + float(row.StandardVariableOverheadCost)
            + float(row.StandardFixedOverheadCost),
            2,
        )
        assert round(float(row.StandardConversionCost), 2) == expected_conversion_cost


def test_phase23_4_clean_validation_build_stays_green() -> None:
    context = build_phase23("config/settings_validation.yaml", validation_scope="full")
    phase23 = context.validation_results["phase23"]

    assert phase23["exceptions"] == []
    assert phase23["planning_controls"]["exception_count"] == 0


def test_phase23_4_one_year_clean_build_hits_manufacturing_targets(
    phase23_4_one_year_clean_artifacts: dict[str, object],
) -> None:
    context = phase23_4_one_year_clean_artifacts["context"]
    phase23 = context.validation_results["phase23"]
    recommendations = context.tables["SupplyPlanRecommendation"].copy()
    fiscal_year_end = pd.Timestamp("2026-12-31")
    release_dates = pd.to_datetime(recommendations["ReleaseByDate"], errors="coerce")
    recommended_quantities = pd.to_numeric(recommendations["RecommendedOrderQuantity"], errors="coerce").fillna(0.0)

    overdue_mask = (
        recommendations["RecommendationStatus"].eq("Planned")
        & release_dates.notna()
        & release_dates.le(fiscal_year_end)
        & recommended_quantities.gt(0)
    )
    overdue_purchase = recommendations[overdue_mask & recommendations["RecommendationType"].eq("Purchase")]
    overdue_manufacture = recommendations[overdue_mask & recommendations["RecommendationType"].eq("Manufacture")]

    assert phase23["planning_controls"]["exception_count"] == 0
    assert phase23["workforce_planning_controls"]["exception_count"] == 0
    assert phase23["time_clock_controls"]["exception_count"] == 0
    assert overdue_purchase.empty
    assert overdue_manufacture.empty

    active_direct_workers = context.tables["Employee"][
        context.tables["Employee"]["IsActive"].astype(int).eq(1)
        & context.tables["Employee"]["PayClass"].eq("Hourly")
        & context.tables["Employee"]["JobTitle"].isin(DIRECT_MANUFACTURING_TITLES)
    ].copy()
    work_centers = context.tables["WorkCenter"].copy()
    nominal_capacity = work_centers.set_index("WorkCenterCode")["NominalDailyCapacityHours"].astype(float).to_dict()
    total_nominal_capacity = sum(nominal_capacity.values())
    expected_nominal_capacity = float(len(active_direct_workers)) * STANDARD_MANUFACTURING_SHIFT_HOURS

    assert expected_nominal_capacity > 0
    assert abs(total_nominal_capacity - expected_nominal_capacity) / expected_nominal_capacity <= 0.05

    target_share_bands = {
        "ASSEMBLY": (0.40, 0.50),
        "FINISH": (0.22, 0.30),
        "CUT": (0.15, 0.22),
        "PACK": (0.08, 0.12),
        "QA": (0.03, 0.06),
    }
    for work_center_code, (low, high) in target_share_bands.items():
        share = float(nominal_capacity.get(work_center_code, 0.0)) / total_nominal_capacity
        assert low <= share <= high

    monthly_diagnostics = {
        month: manufacturing_capacity_diagnostics_by_code(context, 2026, month)
        for month in range(1, 13)
    }
    assembly_median = float(pd.Series([
        monthly_diagnostics[month]["ASSEMBLY"]["monthly_utilization_pct"]
        for month in range(1, 13)
    ]).median())
    finish_median = float(pd.Series([
        monthly_diagnostics[month]["FINISH"]["monthly_utilization_pct"]
        for month in range(1, 13)
    ]).median())
    pack_median = float(pd.Series([
        monthly_diagnostics[month]["PACK"]["monthly_utilization_pct"]
        for month in range(1, 13)
    ]).median())

    assert 85.0 <= assembly_median <= 95.0
    assert 85.0 <= finish_median <= 95.0
    assert 25.0 <= pack_median < 85.0


def test_phase23_4_generation_log_contains_load_diagnostics_and_conversion_logging(
    phase23_4_one_year_clean_artifacts: dict[str, object],
) -> None:
    log_text = phase23_4_one_year_clean_artifacts["generation_log_path"].read_text(encoding="utf-8")

    assert "OPENING PIPELINE | opening_candidates=" in log_text
    assert "MANUFACTURING LOAD | 2026-02 |" in log_text
    assert "converted_load_assembly=" in log_text
    assert "converted_load_pack=" in log_text
    assert "expired_load_assembly=" in log_text
    assert "available_hours_assembly=" in log_text
    assert "available_hours_pack=" in log_text
    assert "opening_fg_seeded_from_prefiscal=" in log_text
    assert "CAPACITY DIAGNOSTIC | 2026-01 | work_center=ASSEMBLY |" in log_text
    assert "CAPACITY DIAGNOSTIC | 2026-01 | work_center=FINISH |" in log_text
    assert "nominal_daily_capacity_share=" in log_text
    assert "monthly_utilization_pct=" in log_text

    pattern = re.compile(
        r"MANUFACTURING CONVERSION \| 2026-(\d{2}) \| eligible_planned=(\d+) \| converted=(\d+) \| expired=(\d+) .*? conversion_rate=([0-9.]+)"
    )
    matches = pattern.findall(log_text)
    assert matches

    for month, eligible, converted, expired, rate in matches:
        eligible_count = int(eligible)
        converted_count = int(converted)
        expired_count = int(expired)
        conversion_rate = float(rate)
        assert 0.0 <= conversion_rate <= 1.0
        assert converted_count + expired_count <= eligible_count
