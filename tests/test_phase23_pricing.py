from __future__ import annotations

from collections import Counter
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
import yaml

from generator_dataset.main import build_full_dataset, build_phase23
from generator_dataset.schema import TABLE_COLUMNS
from generator_dataset.settings import load_settings
from generator_dataset.validations import validate_phase23


PHASE23_FINANCIAL_QUERIES = [
    Path("queries/financial/25_price_realization_vs_list_by_segment_customer_region_collection_style.sql"),
    Path("queries/financial/26_gross_margin_impact_of_promotions_vs_nonpromotion_sales.sql"),
]

PHASE23_MANAGERIAL_QUERIES = [
    Path("queries/managerial/47_sales_rep_override_rate_and_discount_dispersion.sql"),
    Path("queries/managerial/48_collection_revenue_margin_before_after_promotions.sql"),
    Path("queries/managerial/49_customer_specific_pricing_concentration_and_dependency.sql"),
    Path("queries/managerial/50_monthly_price_floor_pressure_and_override_concentration.sql"),
]

PHASE23_AUDIT_QUERIES = [
    Path("queries/audit/47_sales_below_floor_without_approval.sql"),
    Path("queries/audit/48_expired_or_overlapping_price_list_review.sql"),
    Path("queries/audit/49_promotion_scope_and_date_mismatch_review.sql"),
    Path("queries/audit/50_customer_specific_price_list_bypass_review.sql"),
    Path("queries/audit/51_override_approval_completeness_review.sql"),
]


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_path.read_text(encoding="utf-8"), connection)


def _values_match(left: object, right: object, *, numeric: bool = False) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    if numeric:
        return round(float(left), 4) == round(float(right), 4)
    return str(left) == str(right)


@pytest.fixture(scope="session")
def phase23_anomaly_validation_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("phase23_anomaly_validation")
    settings = load_settings("config/settings_validation.yaml")
    payload = dict(vars(settings))
    payload.update({
        "anomaly_mode": "standard",
        "export_sqlite": True,
        "export_excel": False,
        "export_support_excel": False,
        "export_csv_zip": False,
        "sqlite_path": str(workdir / "CharlesRiver_phase23_anomaly.sqlite"),
        "excel_path": str(workdir / "CharlesRiver_phase23_anomaly.xlsx"),
        "support_excel_path": str(workdir / "CharlesRiver_phase23_anomaly_support.xlsx"),
        "csv_zip_path": str(workdir / "CharlesRiver_phase23_anomaly_csv.zip"),
        "generation_log_path": str(workdir / "generation.log"),
    })

    config_path = workdir / "settings_phase23_anomaly.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    context = build_full_dataset(config_path)
    return {
        "context": context,
        "workdir": workdir,
        "sqlite_path": Path(payload["sqlite_path"]),
    }


def test_phase23_schema_and_clean_build() -> None:
    for table_name in [
        "PriceList",
        "PriceListLine",
        "PromotionProgram",
        "PriceOverrideApproval",
    ]:
        assert table_name in TABLE_COLUMNS

    for column_name in ["BaseListPrice", "PriceListLineID", "PromotionID", "PriceOverrideApprovalID", "PricingMethod"]:
        assert column_name in TABLE_COLUMNS["SalesOrderLine"]
        assert column_name in TABLE_COLUMNS["SalesInvoiceLine"]
        assert column_name in TABLE_COLUMNS["CreditMemoLine"]
    assert "Discount" in TABLE_COLUMNS["CreditMemoLine"]

    context = build_phase23("config/settings_validation.yaml", validation_scope="full")
    phase23 = context.validation_results["phase23"]

    assert phase23["exceptions"] == []
    assert phase23["validation_scope"] == "full"
    assert phase23["pricing_controls"]["exception_count"] == 0
    assert context.validation_results["phase22"]["exceptions"] == []

    price_lists = context.tables["PriceList"]
    price_list_lines = context.tables["PriceListLine"]
    promotions = context.tables["PromotionProgram"]
    overrides = context.tables["PriceOverrideApproval"]
    customers = context.tables["Customer"][["CustomerID", "CustomerSegment"]]
    items = context.tables["Item"][["ItemID", "ItemGroup", "ListPrice"]]
    order_lines = context.tables["SalesOrderLine"]
    invoice_lines = context.tables["SalesInvoiceLine"]
    credit_lines = context.tables["CreditMemoLine"]

    assert not price_lists.empty
    assert not price_list_lines.empty
    assert not promotions.empty
    assert not overrides.empty

    assert set(price_lists.loc[price_lists["ScopeType"].eq("Segment"), "CustomerSegment"].astype(str)) == {
        "Strategic",
        "Wholesale",
        "Design Trade",
        "Small Business",
    }
    customer_specific = price_lists[price_lists["ScopeType"].eq("Customer")].merge(customers, on="CustomerID", how="left")
    assert not customer_specific.empty
    assert customer_specific["CustomerSegment_y"].eq("Strategic").all()
    assert price_lists["CurrencyCode"].eq("USD").all()

    line_lookup = price_list_lines.set_index("PriceListLineID")[["UnitPrice", "MinimumUnitPrice"]].to_dict("index")
    merged_order_lines = order_lines.merge(items, on="ItemID", how="left")

    service_lines = merged_order_lines[merged_order_lines["ItemGroup"].eq("Services")]
    if not service_lines.empty:
        assert service_lines["PricingMethod"].eq("Base List").all()
        assert service_lines["PromotionID"].isna().all()
        assert service_lines["BaseListPrice"].astype(float).round(2).eq(service_lines["UnitPrice"].astype(float).round(2)).all()

    standard_lines = merged_order_lines[
        merged_order_lines["ItemGroup"].ne("Services")
        & merged_order_lines["PriceOverrideApprovalID"].isna()
        & merged_order_lines["PriceListLineID"].notna()
    ]
    assert not standard_lines.empty
    for row in standard_lines.itertuples(index=False):
        lookup_row = line_lookup[int(row.PriceListLineID)]
        assert round(float(row.UnitPrice), 2) == round(float(lookup_row["UnitPrice"]), 2)
        assert str(row.PricingMethod) in {"Segment Price List", "Customer Price List"}

    override_lines = merged_order_lines[merged_order_lines["PriceOverrideApprovalID"].notna()]
    assert not override_lines.empty
    assert override_lines["PricingMethod"].eq("Approved Override").all()
    assert override_lines["PriceListLineID"].notna().all()
    for row in override_lines.itertuples(index=False):
        lookup_row = line_lookup[int(row.PriceListLineID)]
        assert round(float(row.UnitPrice), 2) <= round(float(lookup_row["MinimumUnitPrice"]), 2)

    assert order_lines["PromotionID"].notna().any()

    order_line_lookup = order_lines.set_index("SalesOrderLineID").to_dict("index")
    for line in invoice_lines.itertuples(index=False):
        source = order_line_lookup[int(line.SalesOrderLineID)]
        for column_name in [
            "BaseListPrice",
            "UnitPrice",
            "Discount",
            "PriceListLineID",
            "PromotionID",
            "PriceOverrideApprovalID",
            "PricingMethod",
        ]:
            assert _values_match(
                getattr(line, column_name),
                source[column_name],
                numeric=column_name in {"BaseListPrice", "UnitPrice", "Discount"},
            )

    if not credit_lines.empty:
        return_lines = context.tables["SalesReturnLine"].set_index("SalesReturnLineID").to_dict("index")
        invoice_by_shipment = invoice_lines.groupby("ShipmentLineID", dropna=False).first().to_dict("index")
        checked_credit_lines = 0
        for line in credit_lines.itertuples(index=False):
            return_line = return_lines.get(int(line.SalesReturnLineID))
            if return_line is None:
                continue
            original_invoice_line = invoice_by_shipment.get(int(return_line["ShipmentLineID"]))
            if original_invoice_line is None:
                continue
            checked_credit_lines += 1
            for column_name in [
                "BaseListPrice",
                "UnitPrice",
                "Discount",
                "PriceListLineID",
                "PromotionID",
                "PriceOverrideApprovalID",
                "PricingMethod",
            ]:
                assert _values_match(
                    getattr(line, column_name),
                    original_invoice_line[column_name],
                    numeric=column_name in {"BaseListPrice", "UnitPrice", "Discount"},
                )
        assert checked_credit_lines > 0

    revalidated = validate_phase23(context, scope="full", store=False)
    assert revalidated["exceptions"] == []
    assert revalidated["pricing_controls"]["exception_count"] == 0


def test_phase23_queries_execute_and_return_rows(
    clean_validation_dataset_artifacts: dict[str, object],
    phase23_anomaly_validation_artifacts: dict[str, object],
) -> None:
    clean_sqlite = Path(clean_validation_dataset_artifacts["sqlite_path"])
    anomaly_sqlite = Path(phase23_anomaly_validation_artifacts["sqlite_path"])

    for sql_path in [*PHASE23_FINANCIAL_QUERIES, *PHASE23_MANAGERIAL_QUERIES]:
        result = _read_sql_result(clean_sqlite, sql_path)
        assert not result.empty, f"Expected rows from {sql_path} on clean build"

    for sql_path in PHASE23_AUDIT_QUERIES:
        result = _read_sql_result(anomaly_sqlite, sql_path)
        assert not result.empty, f"Expected rows from {sql_path} on anomaly-enabled build"


def test_phase23_anomalies_are_logged_and_detected(
    phase23_anomaly_validation_artifacts: dict[str, object],
) -> None:
    context = phase23_anomaly_validation_artifacts["context"]
    anomaly_counts = Counter(entry["anomaly_type"] for entry in context.anomaly_log)

    for anomaly_type in [
        "missing_price_override_approval",
        "expired_price_list_used",
        "overlapping_active_price_list",
        "promotion_outside_effective_dates",
        "sale_below_price_floor_without_approval",
        "customer_specific_price_bypass",
    ]:
        assert anomaly_counts[anomaly_type] > 0
        matching_entries = [entry for entry in context.anomaly_log if entry["anomaly_type"] == anomaly_type]
        assert matching_entries
        assert all(str(entry.get("description", "")).strip() for entry in matching_entries)
        assert all(str(entry.get("expected_detection_test", "")).strip() for entry in matching_entries)

    assert context.validation_results["phase8"]["pricing_controls"]["exception_count"] > 0


def test_phase23_docs_and_sidebar_entries_exist() -> None:
    for path in [
        Path("docs/analytics/cases/pricing-and-margin-governance-case.md"),
        Path("docs/analytics/cases/pricing-governance-audit-case.md"),
    ]:
        assert path.exists(), f"Missing Phase 23 case doc: {path}"

    sidebar_text = Path("sidebars.js").read_text(encoding="utf-8")
    assert "analytics/cases/pricing-and-margin-governance-case" in sidebar_text
    assert "analytics/cases/pricing-governance-audit-case" in sidebar_text

    financial_guide = Path("docs/analytics/financial.md").read_text(encoding="utf-8")
    managerial_guide = Path("docs/analytics/managerial.md").read_text(encoding="utf-8")
    audit_guide = Path("docs/analytics/audit.md").read_text(encoding="utf-8")
    sql_guide = Path("docs/analytics/sql-guide.md").read_text(encoding="utf-8")
    instructor_guide = Path("docs/teach-with-data/instructor-guide.md").read_text(encoding="utf-8")
    o2c_guide = Path("docs/processes/o2c.md").read_text(encoding="utf-8")
    returns_guide = Path("docs/processes/o2c-returns-credits-refunds.md").read_text(encoding="utf-8")
    schema_guide = Path("docs/reference/schema.md").read_text(encoding="utf-8")
    dataset_guide = Path("docs/start-here/dataset-overview.md").read_text(encoding="utf-8")

    assert "25_price_realization_vs_list_by_segment_customer_region_collection_style.sql" in financial_guide
    assert "26_gross_margin_impact_of_promotions_vs_nonpromotion_sales.sql" in financial_guide
    assert "47_sales_rep_override_rate_and_discount_dispersion.sql" in managerial_guide
    assert "50_monthly_price_floor_pressure_and_override_concentration.sql" in managerial_guide
    assert "47_sales_below_floor_without_approval.sql" in audit_guide
    assert "51_override_approval_completeness_review.sql" in audit_guide
    assert "Pricing and Margin Governance Case" in sql_guide
    assert "Recommended Phase 19 to Phase 23 Classroom Sequence" in instructor_guide
    assert "PriceList" in o2c_guide
    assert "CreditMemoLine` now preserves the original pricing lineage" in returns_guide
    assert "PriceOverrideApproval" in schema_guide
    assert "**68 tables**" in dataset_guide
