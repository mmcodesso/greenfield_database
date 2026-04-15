from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest
import yaml

from greenfield_dataset.main import build_full_dataset, build_phase1, build_phase23
from greenfield_dataset.master_data import STANDARD_LABOR_HOURS_RANGE, manufacturing_staffing_targets
from greenfield_dataset.settings import load_settings


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

    manufacture_rows = recommendations[recommendations["RecommendationType"].eq("Manufacture")].copy()
    manufacture_status_counts = manufacture_rows["RecommendationStatus"].value_counts().to_dict()
    total_manufacture = max(len(manufacture_rows), 1)
    expiry_rate = float(manufacture_status_counts.get("Expired", 0)) / float(total_manufacture)
    manufacture_release_dates = pd.to_datetime(manufacture_rows["ReleaseByDate"], errors="coerce")
    prefiscal_expired = manufacture_rows[
        manufacture_rows["RecommendationStatus"].eq("Expired")
        & manufacture_release_dates.lt(pd.Timestamp("2026-01-01"))
    ]

    assert phase23["exceptions"] == []
    assert overdue_purchase.empty
    assert overdue_manufacture.empty
    assert expiry_rate <= 0.02
    assert int(manufacture_status_counts.get("Expired", 0)) == 0
    assert prefiscal_expired.empty
    assert int(manufacture_status_counts.get("Converted", 0)) > int(manufacture_status_counts.get("Expired", 0))


def test_phase23_4_generation_log_contains_load_diagnostics_and_high_conversion(
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

    pattern = re.compile(
        r"MANUFACTURING CONVERSION \| 2026-(\d{2}) \| eligible_planned=(\d+) \| converted=(\d+) \| expired=(\d+) .*? conversion_rate=([0-9.]+)"
    )
    matches = pattern.findall(log_text)
    assert matches

    monthly_rates = {int(month): (int(eligible), int(converted), float(rate)) for month, eligible, converted, _, rate in matches}
    for month in range(2, 13):
        eligible, converted, rate = monthly_rates.get(month, (0, 0, 0.0))
        if eligible == 0:
            continue
        assert converted > 0
        assert rate >= 0.90
