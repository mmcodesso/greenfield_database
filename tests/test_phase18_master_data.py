from __future__ import annotations

from collections import Counter
import sqlite3
from pathlib import Path

import pandas as pd

from CharlesRiver_dataset.main import build_phase18
from CharlesRiver_dataset.schema import TABLE_COLUMNS


UNIQUE_ROLE_TITLES = [
    "Chief Executive Officer",
    "Chief Financial Officer",
    "Controller",
    "Production Manager",
    "Accounting Manager",
]


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_path.read_text(encoding="utf-8"), connection)


def test_phase18_schema_extensions_exist() -> None:
    for column_name in [
        "EmployeeNumber",
        "EmploymentStatus",
        "TerminationDate",
        "TerminationReason",
        "JobFamily",
        "JobLevel",
        "WorkLocation",
    ]:
        assert column_name in TABLE_COLUMNS["Employee"]

    for column_name in [
        "CollectionName",
        "StyleFamily",
        "PrimaryMaterial",
        "Finish",
        "Color",
        "SizeDescriptor",
        "LifecycleStatus",
        "LaunchDate",
    ]:
        assert column_name in TABLE_COLUMNS["Item"]


def test_phase18_helper_generates_clean_master_data_dataset() -> None:
    context = build_phase18("config/settings_validation.yaml", validation_scope="full")
    phase18 = context.validation_results["phase18"]
    employees = context.tables["Employee"]
    items = context.tables["Item"]

    assert phase18["exceptions"] == []
    assert phase18["master_data_controls"]["exception_count"] == 0
    assert employees["EmployeeNumber"].is_unique

    for job_title in UNIQUE_ROLE_TITLES:
        assert int(employees["JobTitle"].eq(job_title).sum()) == 1

    terminated_share = float(employees["EmploymentStatus"].eq("Terminated").sum()) / max(len(employees), 1)
    assert 0.08 <= terminated_share <= 0.15

    sellable_items = items[items["RevenueAccountID"].notna()].copy()
    assert not sellable_items["ItemName"].astype(str).str.fullmatch(r"(Furniture|Lighting|Textiles|Accessories) Item \d{4}").any()

    furniture = items[items["ItemGroup"].eq("Furniture")]
    lighting = items[items["ItemGroup"].eq("Lighting")]
    textiles = items[items["ItemGroup"].eq("Textiles")]
    accessories = items[items["ItemGroup"].eq("Accessories")]
    assert furniture[["CollectionName", "StyleFamily", "PrimaryMaterial", "Finish", "SizeDescriptor", "LifecycleStatus", "LaunchDate"]].notna().all().all()
    assert lighting[["CollectionName", "StyleFamily", "PrimaryMaterial", "Finish", "LifecycleStatus", "LaunchDate"]].notna().all().all()
    assert textiles[["CollectionName", "StyleFamily", "PrimaryMaterial", "Color", "SizeDescriptor", "LifecycleStatus", "LaunchDate"]].notna().all().all()
    assert accessories[["StyleFamily", "PrimaryMaterial", "Finish", "LifecycleStatus", "LaunchDate"]].notna().all().all()

    payroll_with_employee = context.tables["PayrollRegister"].merge(
        employees[["EmployeeID", "EmploymentStatus", "TerminationDate"]],
        on="EmployeeID",
        how="left",
    )
    terminated_payroll = payroll_with_employee[
        payroll_with_employee["EmploymentStatus"].eq("Terminated")
        & payroll_with_employee["TerminationDate"].notna()
    ]
    assert not (
        pd.to_datetime(terminated_payroll["ApprovedDate"], errors="coerce")
        > pd.to_datetime(terminated_payroll["TerminationDate"], errors="coerce")
    ).any()


def test_phase18_clean_build_outputs_queries_and_current_state_refs(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    context = clean_validation_dataset_artifacts["context"]
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    phase18 = context.validation_results["phase18"]
    employees = context.tables["Employee"]

    assert phase18["exceptions"] == []
    assert phase18["master_data_controls"]["exception_count"] == 0
    assert sqlite_path.exists()

    active_employee_ids = set(employees.loc[employees["IsActive"].astype(int).eq(1), "EmployeeID"].astype(int))
    for table_name, column_name in [
        ("CostCenter", "ManagerID"),
        ("Warehouse", "ManagerID"),
        ("WorkCenter", "ManagerEmployeeID"),
        ("Customer", "SalesRepEmployeeID"),
    ]:
        table = context.tables[table_name]
        populated = table[table[column_name].notna()]
        assert set(populated[column_name].astype(int)).issubset(active_employee_ids)

    for sql_name in [
        "queries/managerial/29_headcount_by_cost_center_job_family_status.sql",
        "queries/managerial/30_sales_margin_by_collection_style_material.sql",
        "queries/audit/28_approval_role_review_by_org_position.sql",
    ]:
        result = _read_sql_result(sqlite_path, Path(sql_name))
        assert not result.empty


def test_phase18_new_anomalies_are_logged_and_detectable(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    context = default_anomaly_dataset_artifacts["context"]
    sqlite_path = Path(default_anomaly_dataset_artifacts["sqlite_path"])
    anomaly_counts = Counter(entry["anomaly_type"] for entry in context.anomaly_log)

    for anomaly_type in [
        "terminated_employee_on_payroll",
        "terminated_employee_approval",
        "inactive_employee_time_or_labor",
        "duplicate_executive_title_assignment",
        "missing_item_catalog_attribute",
        "discontinued_item_in_new_activity",
    ]:
        assert anomaly_counts[anomaly_type] > 0

    assert context.validation_results["phase8"]["master_data_controls"]["exception_count"] > 0

    employees = context.tables["Employee"]
    executive_duplicates = employees["JobTitle"].value_counts()
    assert executive_duplicates.get("Chief Financial Officer", 0) > 1 or executive_duplicates.get("Controller", 0) > 1

    payroll_after_termination = context.tables["PayrollRegister"].merge(
        employees[["EmployeeID", "EmploymentStatus", "TerminationDate"]],
        on="EmployeeID",
        how="left",
    )
    payroll_after_termination = payroll_after_termination[
        payroll_after_termination["EmploymentStatus"].eq("Terminated")
        & payroll_after_termination["TerminationDate"].notna()
    ]
    assert (
        pd.to_datetime(payroll_after_termination["ApprovedDate"], errors="coerce")
        > pd.to_datetime(payroll_after_termination["TerminationDate"], errors="coerce")
    ).any()

    labor_after_termination = context.tables["LaborTimeEntry"].merge(
        employees[["EmployeeID", "EmploymentStatus", "TerminationDate"]],
        on="EmployeeID",
        how="left",
    )
    labor_after_termination = labor_after_termination[
        labor_after_termination["EmploymentStatus"].eq("Terminated")
        & labor_after_termination["TerminationDate"].notna()
    ]
    assert (
        pd.to_datetime(labor_after_termination["WorkDate"], errors="coerce")
        > pd.to_datetime(labor_after_termination["TerminationDate"], errors="coerce")
    ).any()

    items = context.tables["Item"]
    assert not items[
        items["ItemGroup"].eq("Furniture")
        & items["IsActive"].astype(int).eq(1)
        & items["CollectionName"].isna()
    ].empty

    sales_order_lines = context.tables["SalesOrderLine"].merge(
        items[["ItemID", "LifecycleStatus", "IsActive"]],
        on="ItemID",
        how="left",
    )
    assert not sales_order_lines[
        sales_order_lines["LifecycleStatus"].eq("Discontinued")
        & sales_order_lines["IsActive"].astype(int).eq(0)
    ].empty

    terminated_activity_review = _read_sql_result(sqlite_path, Path("queries/audit/27_terminated_employee_activity_review.sql"))
    approval_role_review = _read_sql_result(sqlite_path, Path("queries/audit/28_approval_role_review_by_org_position.sql"))
    assert not terminated_activity_review.empty
    assert not approval_role_review.empty


def test_phase18_cases_and_sidebar_entries_exist() -> None:
    for path in [
        Path("docs/analytics/cases/master-data-and-workforce-audit-case.md"),
        Path("docs/analytics/cases/product-portfolio-and-lifecycle-case.md"),
    ]:
        assert path.exists(), f"Missing Phase 18 case doc: {path}"

    sidebar_text = Path("sidebars.js").read_text(encoding="utf-8")
    assert "analytics/cases/master-data-and-workforce-audit-case" in sidebar_text
    assert "analytics/cases/product-portfolio-and-lifecycle-case" in sidebar_text
