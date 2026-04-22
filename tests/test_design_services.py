from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


SERVICE_QUERY_PATHS = [
    Path("queries/financial/57_design_service_revenue_and_billed_hours_by_customer_month.sql"),
    Path("queries/managerial/52_design_service_engagement_utilization_and_labor_margin.sql"),
    Path("queries/audit/54_design_service_approved_vs_billed_hours_review.sql"),
]


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_path.read_text(encoding="utf-8"), connection)


def test_design_service_queries_return_rows_on_clean_build(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    assert sqlite_path.exists()

    for sql_path in SERVICE_QUERY_PATHS:
        result = _read_sql_result(sqlite_path, sql_path)
        assert not result.empty, f"Expected rows from {sql_path}"


def test_design_service_docs_and_manifests_are_present() -> None:
    company_story = Path("docs/learn-the-business/company-story.md").read_text(encoding="utf-8")
    process_flows = Path("docs/learn-the-business/process-flows.md").read_text(encoding="utf-8")
    dataset_guide = Path("docs/start-here/dataset-overview.md").read_text(encoding="utf-8")
    schema_guide = Path("docs/reference/schema.md").read_text(encoding="utf-8")
    posting_guide = Path("docs/reference/posting.md").read_text(encoding="utf-8")
    o2c_guide = Path("docs/processes/o2c.md").read_text(encoding="utf-8")
    payroll_guide = Path("docs/processes/payroll.md").read_text(encoding="utf-8")
    reports_hub = Path("docs/analytics/reports/index.md").read_text(encoding="utf-8")
    sidebar_text = Path("sidebars.js").read_text(encoding="utf-8")
    query_manifest = Path("src/generated/queryManifest.js").read_text(encoding="utf-8")
    query_doc_collections = Path("src/generated/queryDocCollections.js").read_text(encoding="utf-8")
    report_catalog = Path("config/report_catalog.yaml").read_text(encoding="utf-8")
    report_pack_catalog = Path("config/report_pack_catalog.yaml").read_text(encoding="utf-8")

    assert Path("docs/processes/design-services.md").exists()
    assert "Design Services" in company_story
    assert "[Design Services](../processes/design-services.md)" in process_flows
    assert "processes/design-services" in sidebar_text
    assert "**73 tables**" in dataset_guide
    assert "ServiceEngagement" in dataset_guide
    assert "77 implemented tables" in schema_guide
    assert "ServiceBillingLine" in schema_guide
    assert "4080" in posting_guide
    assert "ServiceBillingLine" in o2c_guide
    assert "ServiceTimeEntry" in payroll_guide
    assert "design services" in reports_hub.lower()
    assert "design-service-revenue-and-billed-hours" in report_catalog
    assert "design-service-revenue-and-billed-hours" in report_pack_catalog

    for query_path in SERVICE_QUERY_PATHS:
        query_key = query_path.as_posix().replace("queries/", "")
        assert query_key in query_manifest
        assert query_key in query_doc_collections
