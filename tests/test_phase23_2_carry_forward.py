from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from greenfield_dataset.main import build_full_dataset, build_phase23
from greenfield_dataset.planning import manufacture_recommendations_for_month, purchase_recommendations_for_month
from greenfield_dataset.schema import TABLE_COLUMNS, create_empty_tables
from greenfield_dataset.settings import initialize_context, load_settings


def _recommendation_row(
    recommendation_id: int,
    recommendation_type: str,
    release_by_date: str,
    priority_code: str,
    *,
    recommended_quantity: float = 10.0,
    status: str = "Planned",
) -> dict[str, object]:
    row = {column_name: None for column_name in TABLE_COLUMNS["SupplyPlanRecommendation"]}
    row.update({
        "SupplyPlanRecommendationID": recommendation_id,
        "RecommendationDate": "2025-12-01",
        "BucketWeekStartDate": "2025-12-01",
        "BucketWeekEndDate": "2025-12-07",
        "ItemID": 1,
        "WarehouseID": 1,
        "RecommendationType": recommendation_type,
        "PriorityCode": priority_code,
        "SupplyMode": recommendation_type,
        "GrossRequirementQuantity": recommended_quantity,
        "ProjectedAvailableQuantity": 0.0,
        "NetRequirementQuantity": recommended_quantity,
        "RecommendedOrderQuantity": recommended_quantity,
        "NeedByDate": "2026-01-20",
        "ReleaseByDate": release_by_date,
        "RecommendationStatus": status,
        "DriverType": "Forecast",
        "PlannerEmployeeID": 1,
        "ConvertedDocumentType": None,
        "ConvertedDocumentID": None,
    })
    return row


def _selector_test_context() -> object:
    settings = load_settings("config/settings_validation.yaml")
    context = initialize_context(settings)
    create_empty_tables(context)
    return context


@pytest.fixture(scope="session")
def phase23_one_year_clean_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("phase23_one_year_clean")
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

    config_path = workdir / "settings_phase23_one_year.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    context = build_full_dataset(str(config_path))
    return {
        "context": context,
        "workdir": workdir,
        "generation_log_path": Path(payload["generation_log_path"]),
    }


def test_phase23_2_purchase_and_manufacture_select_overdue_rows() -> None:
    context = _selector_test_context()
    rows = [
        _recommendation_row(1, "Purchase", "2025-12-20", "Normal"),
        _recommendation_row(2, "Purchase", "2026-01-05", "Expedite"),
        _recommendation_row(3, "Purchase", "2026-03-01", "Normal"),
        _recommendation_row(4, "Manufacture", "2025-11-28", "Normal"),
        _recommendation_row(5, "Manufacture", "2026-01-05", "Expedite"),
        _recommendation_row(6, "Manufacture", "2026-01-05", "Normal"),
        _recommendation_row(7, "Manufacture", "2026-03-01", "Normal"),
    ]
    context.tables["SupplyPlanRecommendation"] = pd.DataFrame(rows, columns=TABLE_COLUMNS["SupplyPlanRecommendation"])

    purchase_rows = purchase_recommendations_for_month(context, 2026, 2)
    manufacture_rows = manufacture_recommendations_for_month(context, 2026, 2)

    assert purchase_rows["SupplyPlanRecommendationID"].astype(int).tolist() == [1, 2]
    assert manufacture_rows["SupplyPlanRecommendationID"].astype(int).tolist() == [4, 5, 6]


def test_phase23_2_january_picks_up_prefiscal_recommendations() -> None:
    context = _selector_test_context()
    rows = [
        _recommendation_row(10, "Purchase", "2025-11-30", "Normal"),
        _recommendation_row(11, "Manufacture", "2025-12-15", "Normal"),
        _recommendation_row(12, "Purchase", "2026-02-01", "Normal"),
        _recommendation_row(13, "Manufacture", "2026-02-01", "Normal"),
    ]
    context.tables["SupplyPlanRecommendation"] = pd.DataFrame(rows, columns=TABLE_COLUMNS["SupplyPlanRecommendation"])

    january_purchase = purchase_recommendations_for_month(context, 2026, 1)
    january_manufacture = manufacture_recommendations_for_month(context, 2026, 1)

    assert january_purchase["SupplyPlanRecommendationID"].astype(int).tolist() == [10]
    assert january_manufacture["SupplyPlanRecommendationID"].astype(int).tolist() == [11]


def test_phase23_2_clean_validation_build_stays_green() -> None:
    context = build_phase23("config/settings_validation.yaml", validation_scope="full")
    phase23 = context.validation_results["phase23"]

    assert phase23["exceptions"] == []
    assert phase23["planning_controls"]["exception_count"] == 0


def test_phase23_2_one_year_clean_build_clears_overdue_planned_recommendations(
    phase23_one_year_clean_artifacts: dict[str, object],
) -> None:
    context = phase23_one_year_clean_artifacts["context"]
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
    overdue_purchase = recommendations[
        overdue_mask & recommendations["RecommendationType"].eq("Purchase")
    ]
    overdue_manufacture = recommendations[
        overdue_mask & recommendations["RecommendationType"].eq("Manufacture")
    ]

    manufacture_rows = recommendations[recommendations["RecommendationType"].eq("Manufacture")].copy()
    manufacture_status_counts = manufacture_rows["RecommendationStatus"].value_counts().to_dict()

    assert phase23["exceptions"] == []
    assert overdue_purchase.empty
    assert overdue_manufacture.empty
    assert int(manufacture_status_counts.get("Converted", 0)) > 0


def test_phase23_2_generation_log_includes_conversion_diagnostics(
    phase23_one_year_clean_artifacts: dict[str, object],
) -> None:
    log_text = phase23_one_year_clean_artifacts["generation_log_path"].read_text(encoding="utf-8")

    assert "PURCHASE CONVERSION | 2026-01 | eligible_planned=" in log_text
    assert "MANUFACTURING CONVERSION | 2026-02 | eligible_planned=" in log_text
    assert "remaining_overdue_planned=" in log_text
    assert "OPENING PIPELINE | opening_candidates=" in log_text
