from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal
from generator_dataset.settings import load_settings


MONTHLY_QUERY_PATH = Path("queries/financial/30_balance_sheet_monthly.sql")
QUARTERLY_QUERY_PATH = Path("queries/financial/31_balance_sheet_quarterly.sql")
ANNUAL_QUERY_PATH = Path("queries/financial/32_balance_sheet_annual.sql")
CLOSE_ENTRY_TYPES = {
    "Year-End Close - P&L to Income Summary",
    "Year-End Close - Income Summary to Retained Earnings",
}
CONTRA_LINE_LABELS = {
    "Allowance for Doubtful Accounts",
    "Accumulated Depreciation - Furniture and Fixtures",
    "Accumulated Depreciation - Manufacturing Equipment",
    "Accumulated Depreciation - Warehouse Equipment",
    "Accumulated Depreciation - Office Equipment",
    "Dividends or Owner Distributions",
}


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    sql_text = sql_path.read_text(encoding="utf-8")
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_text, connection)


def _read_gl_details(sqlite_path: Path) -> pd.DataFrame:
    sql_text = """
    SELECT
        gl.FiscalYear,
        gl.FiscalPeriod,
        CAST(a.AccountNumber AS INTEGER) AS AccountNumber,
        a.AccountName,
        a.AccountType,
        a.AccountSubType,
        gl.Debit,
        gl.Credit,
        je.EntryType
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    """
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_text, connection)


def _published_sqlite_path() -> Path:
    for candidate in [Path("outputs/CharlesRiver.sqlite"), Path("outputs/greenfield.sqlite")]:
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    raise AssertionError("No populated published SQLite file is available in outputs/.")


def _sort_columns(frame: pd.DataFrame, period_columns: list[str]) -> pd.DataFrame:
    order_columns = [*period_columns, "DisplayOrder", "StatementSection", "LineLabel", "LineType", "Amount"]
    return frame[order_columns].sort_values(order_columns[:-1]).reset_index(drop=True)


def _balance_sheet_math_assertions(frame: pd.DataFrame, period_columns: list[str]) -> None:
    subtotals = (
        frame[frame["LineType"].eq("subtotal")]
        .pivot_table(
            index=period_columns,
            columns="LineLabel",
            values="Amount",
            aggfunc="first",
        )
        .reset_index()
    )

    assert not subtotals.empty
    assert (subtotals["Total Current Assets"].round(2) + subtotals["Total Noncurrent Assets"].round(2)).round(2).equals(
        subtotals["Total Assets"].round(2)
    )
    assert (subtotals["Total Current Liabilities"].round(2) + subtotals["Total Long-Term Liabilities"].round(2)).round(2).equals(
        subtotals["Total Liabilities"].round(2)
    )
    assert (subtotals["Total Liabilities"].round(2) + subtotals["Total Equity"].round(2)).round(2).equals(
        subtotals["Total Liabilities and Equity"].round(2)
    )
    assert subtotals["Total Assets"].round(2).equals(subtotals["Total Liabilities and Equity"].round(2))


def _monthly_period_grid(context) -> pd.DataFrame:
    years = range(
        pd.Timestamp(context.settings.fiscal_year_start).year,
        pd.Timestamp(context.settings.fiscal_year_end).year + 1,
    )
    return pd.MultiIndex.from_product(
        [list(years), list(range(1, 13))],
        names=["FiscalYear", "FiscalPeriod"],
    ).to_frame(index=False)


def _expected_current_year_earnings(context, gl_details: pd.DataFrame) -> pd.DataFrame:
    periods = _monthly_period_grid(context)

    pnl = gl_details[
        gl_details["AccountType"].isin(["Revenue", "Expense"])
        & gl_details["AccountSubType"].ne("Header")
        & ~gl_details["EntryType"].fillna("").isin(CLOSE_ENTRY_TYPES)
    ].copy()
    pnl["Amount"] = pnl["Credit"].astype(float) - pnl["Debit"].astype(float)
    pnl = (
        pnl.groupby(["FiscalYear", "FiscalPeriod"], as_index=False)["Amount"]
        .sum()
        .rename(columns={"Amount": "PnlAmount"})
    )

    reclose = gl_details[
        gl_details["AccountNumber"].astype(int).eq(3030)
        & gl_details["EntryType"].fillna("").eq("Year-End Close - Income Summary to Retained Earnings")
    ].copy()
    reclose["Amount"] = reclose["Credit"].astype(float) - reclose["Debit"].astype(float)
    reclose = (
        reclose.groupby(["FiscalYear", "FiscalPeriod"], as_index=False)["Amount"]
        .sum()
        .rename(columns={"Amount": "RetainedEarningsCloseAmount"})
    )

    posted_3050 = gl_details[gl_details["AccountNumber"].astype(int).eq(3050)].copy()
    posted_3050["Amount"] = posted_3050["Credit"].astype(float) - posted_3050["Debit"].astype(float)
    posted_3050 = (
        posted_3050.groupby(["FiscalYear", "FiscalPeriod"], as_index=False)["Amount"]
        .sum()
        .rename(columns={"Amount": "Posted3050Amount"})
    )

    expected = periods.merge(pnl, on=["FiscalYear", "FiscalPeriod"], how="left")
    expected = expected.merge(reclose, on=["FiscalYear", "FiscalPeriod"], how="left")
    expected = expected.merge(posted_3050, on=["FiscalYear", "FiscalPeriod"], how="left")
    expected[["PnlAmount", "RetainedEarningsCloseAmount", "Posted3050Amount"]] = expected[
        ["PnlAmount", "RetainedEarningsCloseAmount", "Posted3050Amount"]
    ].fillna(0.0)
    expected["PnlYTD"] = expected.groupby("FiscalYear")["PnlAmount"].cumsum()
    expected["RetainedEarningsCloseYTD"] = expected.groupby("FiscalYear")["RetainedEarningsCloseAmount"].cumsum()
    expected["Posted3050Cumulative"] = expected["Posted3050Amount"].cumsum()
    expected["Amount"] = (
        expected["PnlYTD"]
        - expected["RetainedEarningsCloseYTD"]
        + expected["Posted3050Cumulative"]
    ).round(2)

    return expected[["FiscalYear", "FiscalPeriod", "Amount"]]


def _expected_retained_earnings_year_end(context, gl_details: pd.DataFrame) -> pd.DataFrame:
    periods = _monthly_period_grid(context)
    retained_earnings = gl_details[gl_details["AccountNumber"].astype(int).eq(3030)].copy()
    retained_earnings["Amount"] = retained_earnings["Credit"].astype(float) - retained_earnings["Debit"].astype(float)
    retained_earnings = (
        retained_earnings.groupby(["FiscalYear", "FiscalPeriod"], as_index=False)["Amount"]
        .sum()
    )
    expected = periods.merge(retained_earnings, on=["FiscalYear", "FiscalPeriod"], how="left")
    expected["Amount"] = expected["Amount"].fillna(0.0)
    expected["Amount"] = expected["Amount"].cumsum().round(2)

    return (
        expected[expected["FiscalPeriod"].eq(12)][["FiscalYear", "Amount"]]
        .reset_index(drop=True)
    )


def test_balance_sheet_queries_return_rows_on_clean_build(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    context = clean_validation_dataset_artifacts["context"]
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    month_count = len(pd.period_range(context.settings.fiscal_year_start, context.settings.fiscal_year_end, freq="M"))
    quarter_count = len(pd.period_range(context.settings.fiscal_year_start, context.settings.fiscal_year_end, freq="Q-DEC"))
    year_count = (
        pd.Timestamp(context.settings.fiscal_year_end).year
        - pd.Timestamp(context.settings.fiscal_year_start).year
        + 1
    )

    monthly = _read_sql_result(sqlite_path, MONTHLY_QUERY_PATH)
    quarterly = _read_sql_result(sqlite_path, QUARTERLY_QUERY_PATH)
    annual = _read_sql_result(sqlite_path, ANNUAL_QUERY_PATH)

    assert not monthly.empty
    assert not quarterly.empty
    assert not annual.empty

    assert list(monthly.columns) == [
        "FiscalYear",
        "FiscalPeriod",
        "StatementSection",
        "LineLabel",
        "LineType",
        "DisplayOrder",
        "Amount",
    ]
    assert list(quarterly.columns) == [
        "FiscalYear",
        "FiscalQuarter",
        "StatementSection",
        "LineLabel",
        "LineType",
        "DisplayOrder",
        "Amount",
    ]
    assert list(annual.columns) == [
        "FiscalYear",
        "StatementSection",
        "LineLabel",
        "LineType",
        "DisplayOrder",
        "Amount",
    ]

    assert monthly[["FiscalYear", "FiscalPeriod"]].drop_duplicates().shape[0] == month_count
    assert quarterly[["FiscalYear", "FiscalQuarter"]].drop_duplicates().shape[0] == quarter_count
    assert annual[["FiscalYear"]].drop_duplicates().shape[0] == year_count

    assert monthly.groupby(["FiscalYear", "FiscalPeriod"]).size().nunique() == 1
    assert quarterly.groupby(["FiscalYear", "FiscalQuarter"]).size().nunique() == 1
    assert annual.groupby(["FiscalYear"]).size().nunique() == 1


def test_monthly_balance_sheet_excludes_post_horizon_spillover_periods() -> None:
    settings = load_settings("config/settings.yaml")
    sqlite_path = _published_sqlite_path()
    expected_years = set(
        range(
            pd.Timestamp(settings.fiscal_year_start).year,
            pd.Timestamp(settings.fiscal_year_end).year + 1,
        )
    )

    assert sqlite_path.exists()
    monthly = _read_sql_result(sqlite_path, MONTHLY_QUERY_PATH)
    years = set(monthly["FiscalYear"].astype(int))

    assert years == expected_years
    assert 2031 not in years
    assert monthly[["FiscalYear", "FiscalPeriod"]].drop_duplicates().shape[0] == len(expected_years) * 12


def test_balance_sheet_statement_math_ties_for_each_snapshot(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])

    monthly = _read_sql_result(sqlite_path, MONTHLY_QUERY_PATH)
    quarterly = _read_sql_result(sqlite_path, QUARTERLY_QUERY_PATH)
    annual = _read_sql_result(sqlite_path, ANNUAL_QUERY_PATH)

    _balance_sheet_math_assertions(monthly, ["FiscalYear", "FiscalPeriod"])
    _balance_sheet_math_assertions(quarterly, ["FiscalYear", "FiscalQuarter"])
    _balance_sheet_math_assertions(annual, ["FiscalYear"])


def test_quarterly_balance_sheet_matches_monthly_quarter_end_snapshots(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    monthly = _read_sql_result(sqlite_path, MONTHLY_QUERY_PATH)
    quarterly = _read_sql_result(sqlite_path, QUARTERLY_QUERY_PATH)

    month_end_snapshots = monthly[monthly["FiscalPeriod"].astype(int).isin([3, 6, 9, 12])].copy()
    month_end_snapshots["FiscalQuarter"] = ((month_end_snapshots["FiscalPeriod"].astype(int) - 1) // 3) + 1
    month_end_snapshots = month_end_snapshots.drop(columns=["FiscalPeriod"])

    assert_frame_equal(
        _sort_columns(month_end_snapshots, ["FiscalYear", "FiscalQuarter"]),
        _sort_columns(quarterly, ["FiscalYear", "FiscalQuarter"]),
    )


def test_annual_balance_sheet_matches_monthly_period_twelve_snapshots(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    monthly = _read_sql_result(sqlite_path, MONTHLY_QUERY_PATH)
    annual = _read_sql_result(sqlite_path, ANNUAL_QUERY_PATH)

    period_twelve = monthly[monthly["FiscalPeriod"].astype(int).eq(12)].drop(columns=["FiscalPeriod"])

    assert_frame_equal(
        _sort_columns(period_twelve, ["FiscalYear"]),
        _sort_columns(annual, ["FiscalYear"]),
    )


def test_current_year_earnings_behaves_as_expected_across_monthly_snapshots(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    context = clean_validation_dataset_artifacts["context"]
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    monthly = _read_sql_result(sqlite_path, MONTHLY_QUERY_PATH)
    gl_details = _read_gl_details(sqlite_path)

    actual = (
        monthly[monthly["LineLabel"].eq("Current Year Earnings")][["FiscalYear", "FiscalPeriod", "Amount"]]
        .sort_values(["FiscalYear", "FiscalPeriod"])
        .reset_index(drop=True)
    )
    expected = _expected_current_year_earnings(context, gl_details)

    assert_frame_equal(actual, expected)
    assert actual[actual["FiscalPeriod"].astype(int).lt(12)]["Amount"].round(2).ne(0).any()
    assert actual[actual["FiscalPeriod"].astype(int).eq(12)]["Amount"].round(2).eq(0).all()


def test_annual_balance_sheet_reflects_retained_earnings_close_and_zero_current_year_earnings(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    context = clean_validation_dataset_artifacts["context"]
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    annual = _read_sql_result(sqlite_path, ANNUAL_QUERY_PATH)
    gl_details = _read_gl_details(sqlite_path)

    annual_current_year_earnings = (
        annual[annual["LineLabel"].eq("Current Year Earnings")][["FiscalYear", "Amount"]]
        .sort_values("FiscalYear")
        .reset_index(drop=True)
    )
    annual_retained_earnings = (
        annual[annual["LineLabel"].eq("Retained Earnings")][["FiscalYear", "Amount"]]
        .sort_values("FiscalYear")
        .reset_index(drop=True)
    )
    expected_retained_earnings = _expected_retained_earnings_year_end(context, gl_details)

    assert annual_current_year_earnings["Amount"].round(2).eq(0).all()
    assert_frame_equal(annual_retained_earnings, expected_retained_earnings)


def test_balance_sheet_contra_accounts_remain_negative_or_zero(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    monthly = _read_sql_result(sqlite_path, MONTHLY_QUERY_PATH)

    contra_lines = monthly[
        monthly["LineType"].eq("account")
        & monthly["LineLabel"].isin(CONTRA_LINE_LABELS)
    ].copy()

    assert set(contra_lines["LineLabel"]) == CONTRA_LINE_LABELS
    assert contra_lines["Amount"].round(2).le(0).all()


def test_balance_sheet_docs_and_catalog_entries_exist() -> None:
    query_manifest = Path("src/generated/queryManifest.js").read_text(encoding="utf-8")
    query_doc_collections = Path("src/generated/queryDocCollections.js").read_text(encoding="utf-8")
    financial_guide = Path("docs/analytics/financial.md").read_text(encoding="utf-8")

    for query_key in [
        "financial/30_balance_sheet_monthly.sql",
        "financial/31_balance_sheet_quarterly.sql",
        "financial/32_balance_sheet_annual.sql",
    ]:
        assert query_key in query_manifest
        assert query_key in query_doc_collections

    assert "Monthly balance sheet" in query_doc_collections
    assert "Quarterly balance sheet" in query_doc_collections
    assert "Annual balance sheet" in query_doc_collections
    assert "Balance sheet reporting" in financial_guide
    assert "point-in-time ending-balance statements" in financial_guide
    assert "Current Year Earnings" in financial_guide
