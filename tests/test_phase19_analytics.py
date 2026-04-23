from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from generator_dataset.main import build_phase19


PHASE19_FINANCIAL_QUERIES = [
    Path("queries/financial/19_working_capital_bridge_by_month.sql"),
    Path("queries/financial/20_cash_conversion_timing_review.sql"),
    Path("queries/financial/21_revenue_and_gross_margin_by_collection_style_lifecycle_supply_mode.sql"),
    Path("queries/financial/22_payroll_and_people_cost_mix_by_cost_center_job_family_level.sql"),
]

PHASE19_MANAGERIAL_QUERIES = [
    Path("queries/managerial/31_product_portfolio_mix_by_collection_style_lifecycle_supply_mode.sql"),
    Path("queries/managerial/32_contribution_margin_by_collection_material_lifecycle_supply_mode.sql"),
    Path("queries/managerial/33_customer_service_impact_by_collection_style.sql"),
    Path("queries/managerial/34_labor_and_headcount_by_work_location_job_family_cost_center.sql"),
    Path("queries/managerial/35_portfolio_return_refund_impact_by_collection_lifecycle.sql"),
]

PHASE19_AUDIT_QUERIES = [
    Path("queries/audit/29_executive_role_uniqueness_and_control_assignment_review.sql"),
    Path("queries/audit/30_item_master_completeness_review.sql"),
    Path("queries/audit/31_discontinued_or_prelaunch_item_activity_review.sql"),
    Path("queries/audit/32_approval_authority_review_by_expected_role_family.sql"),
    Path("queries/audit/33_terminated_employee_activity_rollup_by_process_area.sql"),
]


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_path.read_text(encoding="utf-8"), connection)


def test_phase19_helper_generates_clean_dataset() -> None:
    context = build_phase19("config/settings_validation.yaml", validation_scope="full")
    phase19 = context.validation_results["phase19"]

    assert phase19["exceptions"] == []
    assert phase19["validation_scope"] == "full"
    assert phase19["master_data_controls"]["exception_count"] == 0
    assert context.validation_results["phase18"]["exceptions"] == []


def test_phase19_new_financial_and_managerial_queries_return_rows_on_clean_build(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    assert sqlite_path.exists()

    for sql_path in [*PHASE19_FINANCIAL_QUERIES, *PHASE19_MANAGERIAL_QUERIES]:
        result = _read_sql_result(sqlite_path, sql_path)
        assert not result.empty, f"Expected rows from {sql_path}"


def test_phase19_new_audit_queries_return_rows_on_default_build(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(default_anomaly_dataset_artifacts["sqlite_path"])
    assert sqlite_path.exists()

    for sql_path in PHASE19_AUDIT_QUERIES:
        result = _read_sql_result(sqlite_path, sql_path)
        assert not result.empty, f"Expected rows from {sql_path}"


def test_phase19_case_docs_and_sidebar_entries_exist() -> None:
    required_case_paths = [
        Path("docs/analytics/cases/working-capital-and-cash-conversion-case.md"),
        Path("docs/analytics/cases/financial-statement-bridge-case.md"),
        Path("docs/analytics/cases/product-portfolio-profitability-case.md"),
        Path("docs/analytics/cases/workforce-cost-and-org-control-case.md"),
        Path("docs/analytics/cases/audit-review-pack-case.md"),
    ]
    for path in required_case_paths:
        assert path.exists(), f"Missing Phase 19 case doc: {path}"

    sidebar_text = Path("sidebars.js").read_text(encoding="utf-8")
    assert "analytics/cases/working-capital-and-cash-conversion-case" in sidebar_text
    assert "analytics/cases/financial-statement-bridge-case" in sidebar_text
    assert "analytics/cases/product-portfolio-profitability-case" in sidebar_text
    assert "analytics/cases/workforce-cost-and-org-control-case" in sidebar_text
    assert "analytics/cases/audit-review-pack-case" in sidebar_text


def test_phase19_docs_reference_new_query_and_case_flow() -> None:
    analytics_hub = Path("docs/analytics/index.md").read_text(encoding="utf-8")
    analysis_tracks = Path("docs/analytics/analysis-tracks.md").read_text(encoding="utf-8")
    instructor_guide = Path("docs/teach-with-data/instructor-guide.md").read_text(encoding="utf-8")
    sql_guide = Path("docs/analytics/sql-guide.md").read_text(encoding="utf-8")

    assert "Analysis Tracks" in analytics_hub
    assert "Financial Analytics" in analysis_tracks
    assert "Product Portfolio Profitability Case" not in analytics_hub
    assert "## Recommended teaching sequence" in instructor_guide
    assert "working-capital bridge by month" in sql_guide.lower()
