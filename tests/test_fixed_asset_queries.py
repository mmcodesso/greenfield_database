from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


ROLLFORWARD_QUERY_PATH = Path("queries/financial/54_fixed_asset_rollforward_by_behavior_group.sql")
ACTIVITY_QUERY_PATH = Path("queries/financial/55_capex_acquisitions_financing_and_disposals.sql")
DEBT_QUERY_PATH = Path("queries/financial/56_debt_amortization_and_cash_impact.sql")


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    sql_text = sql_path.read_text(encoding="utf-8")
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_text, connection)


def test_fixed_asset_queries_return_rows_on_clean_build(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    context = clean_validation_dataset_artifacts["context"]
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    month_count = len(pd.period_range(context.settings.fiscal_year_start, context.settings.fiscal_year_end, freq="M"))

    rollforward = _read_sql_result(sqlite_path, ROLLFORWARD_QUERY_PATH)
    activity = _read_sql_result(sqlite_path, ACTIVITY_QUERY_PATH)
    debt = _read_sql_result(sqlite_path, DEBT_QUERY_PATH)

    assert not rollforward.empty
    assert not activity.empty
    assert not debt.empty

    assert list(rollforward.columns) == [
        "FiscalYear",
        "FiscalPeriod",
        "BehaviorGroup",
        "OpeningGrossCost",
        "AdditionsAndImprovements",
        "DisposalsAtCost",
        "EndingGrossCost",
        "OpeningAccumulatedDepreciation",
        "DepreciationExpense",
        "AccumulatedDepreciationRelievedOnDisposal",
        "EndingAccumulatedDepreciation",
        "EndingNetBookValue",
    ]
    assert list(activity.columns) == [
        "EventDate",
        "FiscalYear",
        "FiscalPeriod",
        "BehaviorGroup",
        "AssetCategory",
        "AssetCode",
        "AssetDescription",
        "EventType",
        "FinancingType",
        "EventAmount",
        "CashPaidAmount",
        "NotesPrincipalAmount",
        "DisposalProceedsAmount",
        "RequisitionNumber",
        "PONumber",
        "InvoiceNumber",
        "PaymentNumber",
        "AgreementNumber",
        "AnnualInterestRate",
        "TermMonths",
        "ScheduledPaymentAmount",
        "LinkedJournalEntryNumber",
    ]
    assert list(debt.columns) == [
        "AgreementNumber",
        "AssetCode",
        "AssetDescription",
        "BehaviorGroup",
        "PaymentDate",
        "FiscalYear",
        "FiscalPeriod",
        "PaymentSequence",
        "BeginningPrincipal",
        "PrincipalAmount",
        "InterestAmount",
        "PaymentAmount",
        "EndingPrincipal",
        "CumulativePrincipalPaid",
        "CumulativeInterestPaid",
        "ScheduleStatus",
    ]

    assert rollforward[["FiscalYear", "FiscalPeriod"]].drop_duplicates().shape[0] == month_count
    assert set(rollforward["BehaviorGroup"].astype(str)) == {"Manufacturing", "Office", "Warehouse"}
    assert activity["EventType"].isin(["Acquisition", "Improvement", "Disposal"]).all()
    assert {"Note", "None"}.issubset(set(activity["FinancingType"].astype(str)))

    assert (
        rollforward["OpeningGrossCost"]
        + rollforward["AdditionsAndImprovements"]
        - rollforward["DisposalsAtCost"]
    ).round(2).equals(rollforward["EndingGrossCost"].round(2))
    assert (
        rollforward["OpeningAccumulatedDepreciation"]
        + rollforward["DepreciationExpense"]
        - rollforward["AccumulatedDepreciationRelievedOnDisposal"]
    ).round(2).equals(rollforward["EndingAccumulatedDepreciation"].round(2))
    assert (
        rollforward["EndingGrossCost"] - rollforward["EndingAccumulatedDepreciation"]
    ).round(2).equals(rollforward["EndingNetBookValue"].round(2))

    assert (debt["PaymentAmount"].round(2) == (debt["PrincipalAmount"] + debt["InterestAmount"]).round(2)).all()
    cumulative_principal_step = debt.groupby("AgreementNumber", sort=False)["CumulativePrincipalPaid"].diff().fillna(
        debt["CumulativePrincipalPaid"]
    )
    cumulative_interest_step = debt.groupby("AgreementNumber", sort=False)["CumulativeInterestPaid"].diff().fillna(
        debt["CumulativeInterestPaid"]
    )
    assert cumulative_principal_step.round(2).equals(debt["PrincipalAmount"].round(2))
    assert cumulative_interest_step.round(2).equals(debt["InterestAmount"].round(2))


def test_fixed_asset_queries_capture_cash_and_note_activity_on_full_horizon(
    full_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(full_dataset_artifacts["sqlite_path"])
    activity = _read_sql_result(sqlite_path, ACTIVITY_QUERY_PATH)

    financing_types = set(activity["FinancingType"].astype(str))
    fiscal_years = set(activity["FiscalYear"].astype(int))

    assert {"Cash", "Note", "None"}.issubset(financing_types)
    assert fiscal_years == {2024, 2025, 2026}


def test_fixed_asset_docs_and_catalog_entries_exist() -> None:
    query_manifest = Path("src/generated/queryManifest.js").read_text(encoding="utf-8")
    query_doc_collections = Path("src/generated/queryDocCollections.js").read_text(encoding="utf-8")
    financial_guide = Path("docs/analytics/financial.md").read_text(encoding="utf-8")
    case_index = Path("docs/analytics/cases/index.md").read_text(encoding="utf-8")
    case_doc = Path("docs/analytics/cases/capex-fixed-asset-lifecycle-case.md").read_text(encoding="utf-8")
    posting_reference = Path("docs/reference/posting.md").read_text(encoding="utf-8")
    schema_reference = Path("docs/reference/schema.md").read_text(encoding="utf-8")
    sidebar_text = Path("sidebars.js").read_text(encoding="utf-8")

    for query_key in [
        "financial/54_fixed_asset_rollforward_by_behavior_group.sql",
        "financial/55_capex_acquisitions_financing_and_disposals.sql",
        "financial/56_debt_amortization_and_cash_impact.sql",
    ]:
        assert query_key in query_manifest
        assert query_key in query_doc_collections

    assert "Fixed-asset rollforward by behavior group" in query_doc_collections
    assert "CAPEX acquisitions, financing, and disposals" in query_doc_collections
    assert "Debt amortization and cash impact" in query_doc_collections
    assert "CAPEX and Fixed Asset Path" in financial_guide
    assert "CAPEX and Fixed Asset Lifecycle Case" in case_index
    assert "CAPEX and Fixed Asset Lifecycle Case" in case_doc
    assert "## The Problem to Solve" in case_doc
    assert "## What You Need to Develop" in case_doc
    assert "## Before You Start" in case_doc
    assert "## Step-by-Step Walkthrough" in case_doc
    assert "## Required Student Output" in case_doc
    assert "## Optional Excel Follow-Through" in case_doc
    assert "## Wrap-Up Questions" in case_doc
    assert "financial/54_fixed_asset_rollforward_by_behavior_group.sql" in case_doc
    assert "financial/55_capex_acquisitions_financing_and_disposals.sql" in case_doc
    assert "financial/56_debt_amortization_and_cash_impact.sql" in case_doc
    assert "financial/17_manufacturing_cost_component_bridge.sql" in case_doc
    assert "financial/33_cash_flow_statement_indirect_monthly.sql" in case_doc
    assert "## Recommended Query Sequence" not in case_doc
    assert "Then compare the plan to the budget roll-forward with" not in query_doc_collections
    assert "analytics/cases/capex-fixed-asset-lifecycle-case" in sidebar_text
    assert "Debt reclass" in posting_reference
    assert "Fixed Assets and Financing" in schema_reference
