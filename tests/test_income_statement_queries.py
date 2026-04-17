from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal


MONTHLY_QUERY_PATH = Path("queries/financial/27_income_statement_monthly.sql")
QUARTERLY_QUERY_PATH = Path("queries/financial/28_income_statement_quarterly.sql")
ANNUAL_QUERY_PATH = Path("queries/financial/29_income_statement_annual.sql")
CLOSE_ENTRY_FILTER = """
COALESCE(je.EntryType, '') NOT IN (
    'Year-End Close - P&L to Income Summary',
    'Year-End Close - Income Summary to Retained Earnings'
)
"""


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    sql_text = sql_path.read_text(encoding="utf-8")
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_text, connection)


def _read_sql_text_result(sqlite_path: Path, sql_text: str) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_text, connection)


def _statement_math_assertions(frame: pd.DataFrame, period_columns: list[str]) -> None:
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
    assert (subtotals["Net Revenue"].round(2) == (subtotals["Operating Revenue"] + subtotals["Contra Revenue"]).round(2)).all()
    assert (subtotals["Gross Profit"].round(2) == (subtotals["Net Revenue"] - subtotals["Cost of Goods Sold"]).round(2)).all()
    assert (subtotals["Operating Income"].round(2) == (subtotals["Gross Profit"] - subtotals["Operating Expenses"]).round(2)).all()
    assert (subtotals["Net Income"].round(2) == (subtotals["Operating Income"] + subtotals["Other Income and Expense"]).round(2)).all()


def _sort_columns(frame: pd.DataFrame, period_columns: list[str]) -> pd.DataFrame:
    order_columns = [*period_columns, "DisplayOrder", "StatementSection", "LineLabel", "LineType", "Amount"]
    return frame[order_columns].sort_values(order_columns[:-1]).reset_index(drop=True)


def test_income_statement_queries_return_rows_on_clean_build(
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


def test_income_statement_statement_math_ties_for_each_period(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])

    monthly = _read_sql_result(sqlite_path, MONTHLY_QUERY_PATH)
    quarterly = _read_sql_result(sqlite_path, QUARTERLY_QUERY_PATH)
    annual = _read_sql_result(sqlite_path, ANNUAL_QUERY_PATH)

    _statement_math_assertions(monthly, ["FiscalYear", "FiscalPeriod"])
    _statement_math_assertions(quarterly, ["FiscalYear", "FiscalQuarter"])
    _statement_math_assertions(annual, ["FiscalYear"])


def test_quarterly_income_statement_matches_monthly_rollup(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    monthly = _read_sql_result(sqlite_path, MONTHLY_QUERY_PATH)
    quarterly = _read_sql_result(sqlite_path, QUARTERLY_QUERY_PATH)

    monthly_rollup = (
        monthly.assign(FiscalQuarter=((monthly["FiscalPeriod"].astype(int) - 1) // 3) + 1)
        .groupby(
            [
                "FiscalYear",
                "FiscalQuarter",
                "StatementSection",
                "LineLabel",
                "LineType",
                "DisplayOrder",
            ],
            as_index=False,
        )["Amount"]
        .sum()
    )
    monthly_rollup["Amount"] = monthly_rollup["Amount"].round(2)

    assert_frame_equal(
        _sort_columns(monthly_rollup, ["FiscalYear", "FiscalQuarter"]),
        _sort_columns(quarterly, ["FiscalYear", "FiscalQuarter"]),
    )


def test_annual_income_statement_matches_monthly_rollup(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    monthly = _read_sql_result(sqlite_path, MONTHLY_QUERY_PATH)
    annual = _read_sql_result(sqlite_path, ANNUAL_QUERY_PATH)

    monthly_rollup = (
        monthly.groupby(
            [
                "FiscalYear",
                "StatementSection",
                "LineLabel",
                "LineType",
                "DisplayOrder",
            ],
            as_index=False,
        )["Amount"]
        .sum()
    )
    monthly_rollup["Amount"] = monthly_rollup["Amount"].round(2)

    assert_frame_equal(
        _sort_columns(monthly_rollup, ["FiscalYear"]),
        _sort_columns(annual, ["FiscalYear"]),
    )


def test_annual_net_income_matches_pre_close_gl_activity(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    context = clean_validation_dataset_artifacts["context"]
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    expected_years = set(
        range(
            pd.Timestamp(context.settings.fiscal_year_start).year,
            pd.Timestamp(context.settings.fiscal_year_end).year + 1,
        )
    )
    annual = _read_sql_result(sqlite_path, ANNUAL_QUERY_PATH)

    annual_net_income = (
        annual[
            annual["LineType"].eq("subtotal")
            & annual["LineLabel"].eq("Net Income")
        ][["FiscalYear", "Amount"]]
        .sort_values("FiscalYear")
        .reset_index(drop=True)
    )

    assert set(annual_net_income["FiscalYear"].astype(int)) == expected_years
    assert annual_net_income["Amount"].round(2).ne(0).all()

    pre_close_sql = f"""
    SELECT
        gl.FiscalYear,
        ROUND(SUM(
            CASE
                WHEN a.AccountType = 'Revenue' THEN gl.Credit - gl.Debit
                WHEN a.AccountType = 'Expense' THEN -(gl.Debit - gl.Credit)
                ELSE 0
            END
        ), 2) AS Amount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountType IN ('Revenue', 'Expense')
      AND a.AccountSubType <> 'Header'
      AND {CLOSE_ENTRY_FILTER}
    GROUP BY gl.FiscalYear
    ORDER BY gl.FiscalYear
    """
    pre_close_net_income = _read_sql_text_result(sqlite_path, pre_close_sql)

    assert_frame_equal(annual_net_income, pre_close_net_income)


def test_income_statement_docs_and_catalog_entries_exist() -> None:
    query_manifest = Path("src/generated/queryManifest.js").read_text(encoding="utf-8")
    query_doc_collections = Path("src/generated/queryDocCollections.js").read_text(encoding="utf-8")
    financial_guide = Path("docs/analytics/financial.md").read_text(encoding="utf-8")

    for query_key in [
        "financial/27_income_statement_monthly.sql",
        "financial/28_income_statement_quarterly.sql",
        "financial/29_income_statement_annual.sql",
    ]:
        assert query_key in query_manifest
        assert query_key in query_doc_collections

    assert "Monthly income statement" in query_doc_collections
    assert "Quarterly income statement" in query_doc_collections
    assert "Annual income statement" in query_doc_collections
    assert "Income statement reporting" in financial_guide
    assert "pre-close P&L activity" in financial_guide
