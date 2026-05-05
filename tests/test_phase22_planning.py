from __future__ import annotations

from collections import Counter
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from generator_dataset.fixed_assets import fixed_asset_opening_profiles
from generator_dataset.main import build_phase2, build_phase22
from generator_dataset.planning import opening_inventory_diagnostics, projected_monthly_procurement_cost
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.validations import validate_phase22


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

@pytest.fixture(scope="module")
def phase22_clean_base_context():
    return build_phase22("config/settings_validation.yaml", validation_scope="full")


@pytest.fixture
def phase22_clean_context(clone_generation_context, phase22_clean_base_context):
    return clone_generation_context(phase22_clean_base_context)


@pytest.fixture(scope="module")
def phase22_phase2_base_context():
    return build_phase2("config/settings_validation.yaml")


@pytest.fixture
def phase22_phase2_context(clone_generation_context, phase22_phase2_base_context):
    return clone_generation_context(phase22_phase2_base_context)


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


def test_phase22_helper_generates_clean_dataset(phase22_clean_context) -> None:
    context = phase22_clean_context
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


def test_phase22_phase2_opening_balances_align_with_seeded_inventory(phase22_phase2_context) -> None:
    context = phase22_phase2_context
    fiscal_start = pd.Timestamp(context.settings.fiscal_year_start).normalize()
    voucher_number = f"JE-{fiscal_start.year}-000001"
    diagnostics = opening_inventory_diagnostics(context)
    opening_value_by_account = diagnostics["value_by_account_number"]
    accounts = context.tables["Account"][["AccountID", "AccountNumber"]].copy()
    opening_gl = context.tables["GLEntry"].merge(accounts, on="AccountID", how="left")
    opening_gl = opening_gl[opening_gl["VoucherNumber"].astype(str).eq(voucher_number)].copy()
    for account_number in ["1040", "1045"]:
        debit_amount = float(
            opening_gl.loc[opening_gl["AccountNumber"].astype(str).eq(account_number), "Debit"].sum()
        )
        assert round(debit_amount, 2) == round(float(opening_value_by_account.get(account_number, 0.0)), 2)

    projected_procurement = projected_monthly_procurement_cost(context)
    opening_cash = float(opening_gl.loc[opening_gl["AccountNumber"].astype(str).eq("1010"), "Debit"].sum())
    opening_ap = float(opening_gl.loc[opening_gl["AccountNumber"].astype(str).eq("2010"), "Credit"].sum())
    assert round(opening_cash, 2) >= round(projected_procurement, 2)
    assert round(opening_ap, 2) >= round(projected_procurement, 2)

    for profile in fixed_asset_opening_profiles().values():
        gross_debit = float(
            opening_gl.loc[opening_gl["AccountNumber"].astype(str).eq(profile.asset_account_number), "Debit"].sum()
        )
        assert round(gross_debit, 2) == round(float(profile.gross_opening_balance), 2)
        if profile.accumulated_depreciation_account_number:
            accumulated_credit = float(
                opening_gl.loc[
                    opening_gl["AccountNumber"].astype(str).eq(profile.accumulated_depreciation_account_number),
                    "Credit",
                ].sum()
            )
            assert round(accumulated_credit, 2) == round(float(profile.opening_accumulated_depreciation), 2)


def test_phase22_queries_execute_and_return_expected_rows(
    clean_validation_dataset_artifacts: dict[str, object],
    validation_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    clean_sqlite = Path(clean_validation_dataset_artifacts["sqlite_path"])
    anomaly_sqlite = Path(validation_anomaly_dataset_artifacts["sqlite_path"])

    for sql_path in [*PHASE22_FINANCIAL_QUERIES, *PHASE22_MANAGERIAL_QUERIES]:
        result = _read_sql_result(clean_sqlite, sql_path)
        assert not result.empty, f"Expected rows from {sql_path} on clean build"

    for sql_path in PHASE22_AUDIT_QUERIES:
        result = _read_sql_result(anomaly_sqlite, sql_path)
        assert not result.empty, f"Expected rows from {sql_path} on anomaly-enabled build"


def test_phase22_new_anomalies_are_logged_and_detected(
    validation_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    context = validation_anomaly_dataset_artifacts["context"]
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
    query_doc_collections = Path("src/generated/queryDocCollections.js").read_text(encoding="utf-8")
    sql_guide = Path("docs/analytics/sql-guide.md").read_text(encoding="utf-8")
    instructor_guide = Path("docs/teach-with-data/instructor-guide.md").read_text(encoding="utf-8")

    assert "## Audit Query Groups" in audit_guide
    assert "Planning-support, pricing-governance, and design-service controls" in query_doc_collections
    assert "42_forecast_approval_and_override_review.sql" in query_doc_collections
    assert "43_inactive_or_stale_inventory_policy_review.sql" in query_doc_collections
    assert "46_discontinued_or_prelaunch_planning_activity_review.sql" in query_doc_collections
    assert "Demand Planning and Replenishment Case" in managerial_guide
    assert "inventory coverage and projected stockout risk" in query_doc_collections.lower()
    assert "## Recommended teaching sequence" in instructor_guide


def test_phase22_demand_planning_case_uses_upgraded_walkthrough_shell() -> None:
    demand_case = Path("docs/analytics/cases/demand-planning-and-replenishment-case.md").read_text(encoding="utf-8")

    for snippet in (
        "## Before You Start",
        "## Step-by-Step Walkthrough",
        "## Required Student Output",
        "## Optional Excel Follow-Through",
        "## Wrap-Up Questions",
        "## Next Steps",
        "financial/23_forecast_vs_actual_demand_by_week_item_group_collection_lifecycle.sql",
        "managerial/45_forecast_error_and_bias_by_collection_style_family.sql",
        "managerial/46_supply_plan_driver_mix_by_collection_and_supply_mode.sql",
        "managerial/42_inventory_coverage_and_projected_stockout_risk.sql",
        "managerial/44_expedite_pressure_by_item_family_and_month.sql",
        "financial/24_recommendation_conversion_by_type_priority_planner.sql",
        "managerial/43_rough_cut_capacity_load_vs_available_hours.sql",
        "replenishment-support-audit-case.md",
        "../../processes/manufacturing.md",
    ):
        assert snippet in demand_case

    assert "## Key Data Sources" not in demand_case
    assert "## Recommended Query Sequence" not in demand_case


def test_phase22_replenishment_support_audit_case_uses_upgraded_walkthrough_shell() -> None:
    replenishment_case = Path("docs/analytics/cases/replenishment-support-audit-case.md").read_text(encoding="utf-8")

    for snippet in (
        "## Before You Start",
        "## Step-by-Step Walkthrough",
        "## Required Student Output",
        "## Optional Excel Follow-Through",
        "## Wrap-Up Questions",
        "## Next Steps",
        "audit/42_forecast_approval_and_override_review.sql",
        "audit/43_inactive_or_stale_inventory_policy_review.sql",
        "audit/44_requisitions_and_work_orders_without_planning_support.sql",
        "audit/45_recommendation_converted_after_need_by_date_review.sql",
        "audit/46_discontinued_or_prelaunch_planning_activity_review.sql",
        "demand-planning-and-replenishment-case.md",
        "../audit.md",
        "../reports/operations-and-risk.md",
    ):
        assert snippet in replenishment_case

    assert "## Key Data Sources" not in replenishment_case
    assert "## Recommended Query Sequence" not in replenishment_case
