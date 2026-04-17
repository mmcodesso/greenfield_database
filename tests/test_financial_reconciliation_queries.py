from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import yaml


RETAINED_EARNINGS_IMPACT_QUERY_PATH = Path("queries/financial/16_retained_earnings_and_close_entry_impact.sql")
ANNUAL_BRIDGE_QUERY_PATH = Path("queries/financial/39_annual_income_to_equity_bridge.sql")
POST_CLOSE_LEAKAGE_QUERY_PATH = Path("queries/financial/40_post_close_profit_and_loss_leakage_review.sql")
ANNUAL_NET_REVENUE_BRIDGE_QUERY_PATH = Path("queries/financial/42_annual_net_revenue_bridge.sql")
INVOICE_REVENUE_CUTOFF_SUMMARY_QUERY_PATH = Path("queries/financial/43_invoice_revenue_cutoff_exception_summary.sql")
INVOICE_REVENUE_CUTOFF_TRACE_QUERY_PATH = Path("queries/financial/44_invoice_revenue_cutoff_exception_trace.sql")


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    sql_text = sql_path.read_text(encoding="utf-8")
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_text, connection)


def _expected_years(context) -> set[int]:
    return set(
        range(
            pd.Timestamp(context.settings.fiscal_year_start).year,
            pd.Timestamp(context.settings.fiscal_year_end).year + 1,
        )
    )


def _assert_close_to_zero(series: pd.Series, tolerance: float = 0.005) -> None:
    assert series.fillna(0.0).abs().le(tolerance).all()


def test_reconciliation_config_is_a_clean_clone_of_default_settings() -> None:
    default_settings = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
    reconciliation_settings = yaml.safe_load(Path("config/settings_reconciliation.yaml").read_text(encoding="utf-8"))

    assert reconciliation_settings["anomaly_mode"] == "none"
    assert reconciliation_settings["sqlite_path"] == "outputs/{short_name}_clean.sqlite"
    assert reconciliation_settings["export_excel"] is False
    assert reconciliation_settings["export_support_excel"] is False
    assert reconciliation_settings["export_csv_zip"] is False
    assert reconciliation_settings["export_reports"] is False
    assert reconciliation_settings["generation_log_path"] == "outputs/{short_name}_clean_generation.log"

    changed_keys = {
        key
        for key in default_settings
        if reconciliation_settings.get(key) != default_settings.get(key)
    }
    assert changed_keys == {
        "anomaly_mode",
        "export_excel",
        "export_support_excel",
        "export_csv_zip",
        "export_reports",
        "sqlite_path",
        "generation_log_path",
    }


def test_retained_earnings_close_impact_query_ties_on_clean_full_build(
    full_dataset_artifacts: dict[str, object],
) -> None:
    context = full_dataset_artifacts["context"]
    sqlite_path = Path(full_dataset_artifacts["sqlite_path"])
    frame = _read_sql_result(sqlite_path, RETAINED_EARNINGS_IMPACT_QUERY_PATH).sort_values("FiscalYear").reset_index(drop=True)

    assert set(frame["FiscalYear"].astype(int)) == _expected_years(context)
    assert frame["IncomeStatementNetIncome"].round(2).ne(0).all()
    _assert_close_to_zero(frame["StatementToPreCloseVariance"])
    _assert_close_to_zero(frame["StatementToRetainedEarningsCloseVariance"])
    _assert_close_to_zero(frame["PreCloseNetIncome"] - frame["CloseStepPnLToIncomeSummary"])
    _assert_close_to_zero(frame["CloseStepPnLToIncomeSummary"] - frame["CloseStepIncomeSummaryToRetainedEarnings"])
    _assert_close_to_zero(frame["CloseStepIncomeSummaryToRetainedEarnings"] - frame["RetainedEarningsCloseAmount"])


def test_annual_income_to_equity_bridge_ties_on_clean_full_build(
    full_dataset_artifacts: dict[str, object],
) -> None:
    context = full_dataset_artifacts["context"]
    sqlite_path = Path(full_dataset_artifacts["sqlite_path"])
    frame = _read_sql_result(sqlite_path, ANNUAL_BRIDGE_QUERY_PATH).sort_values("FiscalYear").reset_index(drop=True)

    assert set(frame["FiscalYear"].astype(int)) == _expected_years(context)
    assert frame["IncomeStatementNetIncome"].round(2).ne(0).all()

    for column in [
        "StatementNetIncomeLessPreCloseGlVariance",
        "StatementNetIncomeLessRetainedEarningsCloseVariance",
        "PreCloseGlNetIncomeLessRetainedEarningsCloseVariance",
        "BalanceSheetCurrentYearEarningsResidual",
        "BalanceSheetOutOfBalance",
    ]:
        _assert_close_to_zero(frame[column])

    non_first_years = frame[frame["PriorYearEndingRetainedEarnings"].notna()].copy()
    assert not non_first_years.empty
    _assert_close_to_zero(non_first_years["RetainedEarningsMovementLessRetainedEarningsCloseVariance"])


def test_annual_income_to_equity_bridge_still_ties_on_default_anomaly_build(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(default_anomaly_dataset_artifacts["sqlite_path"])
    frame = _read_sql_result(sqlite_path, ANNUAL_BRIDGE_QUERY_PATH).sort_values("FiscalYear").reset_index(drop=True)

    for column in [
        "StatementNetIncomeLessPreCloseGlVariance",
        "StatementNetIncomeLessRetainedEarningsCloseVariance",
        "PreCloseGlNetIncomeLessRetainedEarningsCloseVariance",
        "BalanceSheetCurrentYearEarningsResidual",
        "BalanceSheetOutOfBalance",
    ]:
        _assert_close_to_zero(frame[column])


def test_post_close_leakage_review_is_empty_on_clean_full_build(
    full_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(full_dataset_artifacts["sqlite_path"])
    frame = _read_sql_result(sqlite_path, POST_CLOSE_LEAKAGE_QUERY_PATH)

    assert frame.empty


def test_post_close_leakage_review_is_empty_on_default_anomaly_build(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(default_anomaly_dataset_artifacts["sqlite_path"])
    frame = _read_sql_result(sqlite_path, POST_CLOSE_LEAKAGE_QUERY_PATH)

    assert frame.empty


def test_annual_net_revenue_bridge_ties_on_clean_full_build(
    full_dataset_artifacts: dict[str, object],
) -> None:
    context = full_dataset_artifacts["context"]
    sqlite_path = Path(full_dataset_artifacts["sqlite_path"])
    frame = _read_sql_result(sqlite_path, ANNUAL_NET_REVENUE_BRIDGE_QUERY_PATH).sort_values("FiscalYear").reset_index(drop=True)

    assert set(frame["FiscalYear"].astype(int)) == _expected_years(context)
    _assert_close_to_zero(frame["OperationalToPreCloseGlNetRevenueVariance"])
    _assert_close_to_zero(frame["PreCloseGlToIncomeStatementNetRevenueVariance"])


def test_invoice_revenue_cutoff_summary_is_empty_on_clean_full_build(
    full_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(full_dataset_artifacts["sqlite_path"])
    frame = _read_sql_result(sqlite_path, INVOICE_REVENUE_CUTOFF_SUMMARY_QUERY_PATH)

    assert frame.empty


def test_invoice_revenue_cutoff_trace_is_empty_on_clean_full_build(
    full_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(full_dataset_artifacts["sqlite_path"])
    frame = _read_sql_result(sqlite_path, INVOICE_REVENUE_CUTOFF_TRACE_QUERY_PATH)

    assert frame.empty


def test_invoice_revenue_cutoff_summary_explains_anomaly_year_mismatch_population(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(default_anomaly_dataset_artifacts["sqlite_path"])
    frame = _read_sql_result(sqlite_path, INVOICE_REVENUE_CUTOFF_SUMMARY_QUERY_PATH)

    assert len(frame) == 13
    assert frame["InvoiceBeforeShipmentFlag"].astype(int).eq(1).all()
    assert frame["InvoiceYearVsGlYearFlag"].astype(int).eq(1).all()
    assert frame["RevenueGlIncompleteFlag"].astype(int).eq(0).all()
    assert frame["ExceptionType"].eq("seeded anomaly").all()

    grouped = (
        frame.groupby(["InvoiceYear", "RevenueGlFiscalYear"], dropna=False)
        .agg(
            InvoiceCount=("SalesInvoiceID", "nunique"),
            RevenueAmount=("RevenueAmount", "sum"),
        )
        .reset_index()
        .sort_values(["InvoiceYear", "RevenueGlFiscalYear"], kind="stable")
    )
    grouped["RevenueAmount"] = grouped["RevenueAmount"].round(2)

    expected = pd.DataFrame([
        {"InvoiceYear": 2025, "RevenueGlFiscalYear": 2026, "InvoiceCount": 1, "RevenueAmount": 1858.96},
        {"InvoiceYear": 2026, "RevenueGlFiscalYear": 2027, "InvoiceCount": 3, "RevenueAmount": 11915.23},
        {"InvoiceYear": 2027, "RevenueGlFiscalYear": 2028, "InvoiceCount": 3, "RevenueAmount": 2544.87},
        {"InvoiceYear": 2028, "RevenueGlFiscalYear": 2029, "InvoiceCount": 3, "RevenueAmount": 3521.75},
        {"InvoiceYear": 2029, "RevenueGlFiscalYear": 2030, "InvoiceCount": 3, "RevenueAmount": 3051.83},
    ])

    pd.testing.assert_frame_equal(grouped.reset_index(drop=True), expected, check_dtype=False)


def test_invoice_revenue_cutoff_trace_ties_exception_invoices_to_revenue_gl_years(
    default_anomaly_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(default_anomaly_dataset_artifacts["sqlite_path"])
    summary = _read_sql_result(sqlite_path, INVOICE_REVENUE_CUTOFF_SUMMARY_QUERY_PATH)
    trace = _read_sql_result(sqlite_path, INVOICE_REVENUE_CUTOFF_TRACE_QUERY_PATH)

    assert not trace.empty
    assert set(trace["SalesInvoiceID"].astype(int)) == set(summary["SalesInvoiceID"].astype(int))
    assert trace["TraceClassification"].eq("seeded anomaly").all()

    non_null_trace = trace[trace["GLEntryID"].notna()].copy()
    assert not non_null_trace.empty
    _assert_close_to_zero(non_null_trace["InvoiceLineToRevenueGlVariance"])

    summary_year_map = summary.set_index(summary["SalesInvoiceID"].astype(int))["RevenueGlFiscalYear"].astype(int).to_dict()
    trace_year_map = non_null_trace.groupby("SalesInvoiceID")["FiscalYear"].nunique()
    assert trace_year_map.eq(1).all()
    assert non_null_trace.apply(
        lambda row: int(row["FiscalYear"]) == summary_year_map[int(row["SalesInvoiceID"])],
        axis=1,
    ).all()


def test_standard_anomaly_profile_disables_round_dollar_manual_journal_seed() -> None:
    anomaly_profile = yaml.safe_load(Path("config/anomaly_profile.yaml").read_text(encoding="utf-8"))

    assert anomaly_profile["profiles"]["standard"]["round_dollar_manual_journals_per_year"] == 0


def test_reconciliation_queries_are_in_catalog_and_docs() -> None:
    query_manifest = Path("src/generated/queryManifest.js").read_text(encoding="utf-8")
    query_doc_collections = Path("src/generated/queryDocCollections.js").read_text(encoding="utf-8")
    financial_guide = Path("docs/analytics/financial.md").read_text(encoding="utf-8")

    for query_key in [
        "financial/39_annual_income_to_equity_bridge.sql",
        "financial/40_post_close_profit_and_loss_leakage_review.sql",
        "financial/41_round_dollar_manual_journal_close_sensitivity_review.sql",
        "financial/42_annual_net_revenue_bridge.sql",
        "financial/43_invoice_revenue_cutoff_exception_summary.sql",
        "financial/44_invoice_revenue_cutoff_exception_trace.sql",
    ]:
        assert query_key in query_manifest
        assert query_key in query_doc_collections

    assert "Annual net-income-to-equity bridge" in query_doc_collections
    assert "Post-close P&L leakage review" in query_doc_collections
    assert "Round-dollar manual-journal close-sensitivity review" in query_doc_collections
    assert "Annual net revenue bridge" in query_doc_collections
    assert "Invoice revenue cutoff exception summary" in query_doc_collections
    assert "Invoice revenue cutoff exception trace" in query_doc_collections
    assert "config/settings_reconciliation.yaml" in financial_guide
    assert "anomaly-enriched comparison set" in financial_guide
    assert "financial/39_annual_income_to_equity_bridge.sql" in financial_guide
    assert "financial/42_annual_net_revenue_bridge.sql" in financial_guide
    assert "financial/43_invoice_revenue_cutoff_exception_summary.sql" in financial_guide
    assert "financial/44_invoice_revenue_cutoff_exception_trace.sql" in financial_guide
    assert "separate clean SQLite and generation-log outputs" in financial_guide
    assert "default `standard` anomaly profile no longer uses this anomaly" in financial_guide
