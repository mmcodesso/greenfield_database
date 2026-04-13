from __future__ import annotations

from collections import Counter
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
import yaml

from greenfield_dataset.main import build_full_dataset
from greenfield_dataset.main import build_phase22
from greenfield_dataset.settings import load_settings
from greenfield_dataset.schema import TABLE_COLUMNS
from greenfield_dataset.validations import validate_phase22


PHASE22_FINANCIAL_QUERIES = [
    Path("queries/financial/23_forecast_vs_actual_demand_by_week_item_group_collection_lifecycle.sql"),
    Path("queries/financial/24_recommendation_conversion_by_type_priority_planner.sql"),
]

PHASE22_MANAGERIAL_QUERIES = [
    Path("queries/managerial/42_inventory_coverage_and_projected_stockout_risk.sql"),
    Path("queries/managerial/43_rough_cut_capacity_load_vs_available_hours.sql"),
    Path("queries/managerial/44_expedite_pressure_by_item_family_and_month.sql"),
    Path("queries/managerial/45_forecast_error_and_bias_by_collection_style_family.sql"),
    Path("queries/managerial/46_supply_plan_driver_mix_by_collection_and_supply_mode.sql"),
]

PHASE22_AUDIT_QUERIES = [
    Path("queries/audit/42_forecast_approval_and_override_review.sql"),
    Path("queries/audit/43_inactive_or_stale_inventory_policy_review.sql"),
    Path("queries/audit/44_requisitions_and_work_orders_without_planning_support.sql"),
    Path("queries/audit/45_recommendation_converted_after_need_by_date_review.sql"),
    Path("queries/audit/46_discontinued_or_prelaunch_planning_activity_review.sql"),
]


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_path.read_text(encoding="utf-8"), connection)


@pytest.fixture(scope="session")
def phase22_anomaly_validation_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("phase22_anomaly_validation")
    settings = load_settings("config/settings_validation.yaml")
    payload = dict(vars(settings))
    payload.update({
        "anomaly_mode": "standard",
        "export_sqlite": True,
        "export_excel": False,
        "export_support_excel": False,
        "export_csv_zip": False,
        "sqlite_path": str(workdir / "greenfield_phase22_anomaly.sqlite"),
        "excel_path": str(workdir / "greenfield_phase22_anomaly.xlsx"),
        "support_excel_path": str(workdir / "greenfield_phase22_anomaly_support.xlsx"),
        "csv_zip_path": str(workdir / "greenfield_phase22_anomaly_csv.zip"),
        "generation_log_path": str(workdir / "generation.log"),
    })

    config_path = workdir / "settings_phase22_anomaly.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    context = build_full_dataset(config_path)
    return {
        "context": context,
        "workdir": workdir,
        "sqlite_path": Path(payload["sqlite_path"]),
    }


def test_phase22_schema_extensions_exist() -> None:
    for table_name in [
        "DemandForecast",
        "InventoryPolicy",
        "SupplyPlanRecommendation",
        "MaterialRequirementPlan",
        "RoughCutCapacityPlan",
    ]:
        assert table_name in TABLE_COLUMNS

    assert "SupplyPlanRecommendationID" in TABLE_COLUMNS["PurchaseRequisition"]
    assert "SupplyPlanRecommendationID" in TABLE_COLUMNS["WorkOrder"]


def test_phase22_helper_generates_clean_dataset() -> None:
    context = build_phase22("config/settings_validation.yaml", validation_scope="full")
    phase22 = context.validation_results["phase22"]

    assert phase22["exceptions"] == []
    assert phase22["validation_scope"] == "full"
    assert phase22["planning_controls"]["exception_count"] == 0
    assert context.validation_results["phase21"]["exceptions"] == []

    forecasts = context.tables["DemandForecast"]
    policies = context.tables["InventoryPolicy"]
    recommendations = context.tables["SupplyPlanRecommendation"]
    material_plans = context.tables["MaterialRequirementPlan"]
    rough_cut = context.tables["RoughCutCapacityPlan"]
    requisitions = context.tables["PurchaseRequisition"]
    work_orders = context.tables["WorkOrder"]

    assert not forecasts.empty
    assert not policies.empty
    assert not recommendations.empty
    assert not material_plans.empty
    assert not rough_cut.empty

    assert forecasts["ApprovedByEmployeeID"].notna().all()
    assert recommendations["NetRequirementQuantity"].astype(float).ge(0).all()
    assert recommendations["RecommendedOrderQuantity"].astype(float).ge(0).all()

    converted = recommendations[recommendations["RecommendationStatus"].eq("Converted")].copy()
    assert not converted.empty
    assert converted["ConvertedDocumentType"].notna().all()
    assert converted["ConvertedDocumentID"].notna().all()

    if not requisitions.empty:
        planned_requisitions = requisitions[requisitions["SupplyPlanRecommendationID"].notna()].copy()
        assert not planned_requisitions.empty

    if not work_orders.empty:
        planned_work_orders = work_orders[work_orders["SupplyPlanRecommendationID"].notna()].copy()
        assert not planned_work_orders.empty

    revalidated = validate_phase22(context, scope="full", store=False)
    assert revalidated["exceptions"] == []
    assert revalidated["planning_controls"]["exception_count"] == 0


def test_phase22_queries_execute_and_return_expected_rows(
    clean_validation_dataset_artifacts: dict[str, object],
    phase22_anomaly_validation_artifacts: dict[str, object],
) -> None:
    clean_sqlite = Path(clean_validation_dataset_artifacts["sqlite_path"])
    anomaly_sqlite = Path(phase22_anomaly_validation_artifacts["sqlite_path"])

    for sql_path in [*PHASE22_FINANCIAL_QUERIES, *PHASE22_MANAGERIAL_QUERIES]:
        result = _read_sql_result(clean_sqlite, sql_path)
        assert not result.empty, f"Expected rows from {sql_path} on clean build"

    for sql_path in PHASE22_AUDIT_QUERIES:
        result = _read_sql_result(anomaly_sqlite, sql_path)
        assert not result.empty, f"Expected rows from {sql_path} on anomaly-enabled build"


def test_phase22_new_anomalies_are_logged_and_detected(
    phase22_anomaly_validation_artifacts: dict[str, object],
) -> None:
    context = phase22_anomaly_validation_artifacts["context"]
    anomaly_counts = Counter(entry["anomaly_type"] for entry in context.anomaly_log)

    for anomaly_type in [
        "missing_forecast_approval",
        "inactive_policy_for_active_item",
        "purchase_requisition_without_plan",
        "work_order_without_plan",
        "late_recommendation_conversion",
        "forecast_override_outlier",
    ]:
        assert anomaly_counts[anomaly_type] > 0

    assert context.validation_results["phase8"]["planning_controls"]["exception_count"] > 0


def test_phase22_docs_and_sidebar_entries_exist() -> None:
    for path in [
        Path("docs/analytics/cases/demand-planning-and-replenishment-case.md"),
        Path("docs/analytics/cases/replenishment-support-audit-case.md"),
    ]:
        assert path.exists(), f"Missing Phase 22 case doc: {path}"

    sidebar_text = Path("sidebars.js").read_text(encoding="utf-8")
    assert "analytics/cases/demand-planning-and-replenishment-case" in sidebar_text
    assert "analytics/cases/replenishment-support-audit-case" in sidebar_text

    audit_guide = Path("docs/analytics/audit.md").read_text(encoding="utf-8")
    managerial_guide = Path("docs/analytics/managerial.md").read_text(encoding="utf-8")
    sql_guide = Path("docs/analytics/sql-guide.md").read_text(encoding="utf-8")
    instructor_guide = Path("docs/instructor-guide.md").read_text(encoding="utf-8")

    assert "42_forecast_approval_and_override_review.sql" in audit_guide
    assert "43_inactive_or_stale_inventory_policy_review.sql" in audit_guide
    assert "46_discontinued_or_prelaunch_planning_activity_review.sql" in audit_guide
    assert "Demand Planning and Replenishment Case" in managerial_guide
    assert "inventory coverage and projected stockout risk" in sql_guide.lower()
    assert "Recommended Phase 19 to Phase 22 Classroom Sequence" in instructor_guide
