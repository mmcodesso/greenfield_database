from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal
from generator_dataset.settings import load_settings


INDIRECT_MONTHLY_QUERY_PATH = Path("queries/financial/33_cash_flow_statement_indirect_monthly.sql")
INDIRECT_QUARTERLY_QUERY_PATH = Path("queries/financial/34_cash_flow_statement_indirect_quarterly.sql")
INDIRECT_ANNUAL_QUERY_PATH = Path("queries/financial/35_cash_flow_statement_indirect_annual.sql")
DIRECT_MONTHLY_QUERY_PATH = Path("queries/financial/36_cash_flow_statement_direct_monthly.sql")
DIRECT_QUARTERLY_QUERY_PATH = Path("queries/financial/37_cash_flow_statement_direct_quarterly.sql")
DIRECT_ANNUAL_QUERY_PATH = Path("queries/financial/38_cash_flow_statement_direct_annual.sql")
BALANCE_SHEET_MONTHLY_QUERY_PATH = Path("queries/financial/30_balance_sheet_monthly.sql")
BALANCE_SHEET_QUARTERLY_QUERY_PATH = Path("queries/financial/31_balance_sheet_quarterly.sql")
BALANCE_SHEET_ANNUAL_QUERY_PATH = Path("queries/financial/32_balance_sheet_annual.sql")
OPERATING_SECTION_LABEL = "Operating Activities"
INVESTING_SECTION_LABEL = "Investing Activities"
FINANCING_SECTION_LABEL = "Financing Activities"
SECTION_TO_SUBTOTAL = {
    OPERATING_SECTION_LABEL: "Net Cash from Operating Activities",
    INVESTING_SECTION_LABEL: "Net Cash from Investing Activities",
    FINANCING_SECTION_LABEL: "Net Cash from Financing Activities",
}
DIRECT_LINE_LABELS = {
    "CashReceipt": "Cash Received from Customers",
    "CustomerRefund": "Cash Refunded to Customers",
    "DisbursementPayment": "Cash Paid to Suppliers",
    "PayrollPayment": "Cash Paid for Payroll",
    "PayrollLiabilityRemittance": "Cash Paid for Payroll Taxes and Withholdings",
}
OTHER_OPERATING_EXPENSE_LINE_LABEL = "Cash Paid for Other Operating Expenses"
INVESTING_LINE_LABEL = "Capital Expenditures and Asset Transactions"
FINANCING_LINE_LABEL = "Debt and Equity Cash"


def _read_sql_result(sqlite_path: Path, sql_path: Path) -> pd.DataFrame:
    sql_text = sql_path.read_text(encoding="utf-8")
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_text, connection)


def _read_sql_text_result(sqlite_path: Path, sql_text: str) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(sql_text, connection)


def _published_sqlite_path() -> Path:
    for candidate in [Path("outputs/CharlesRiver.sqlite"), Path("outputs/greenfield.sqlite")]:
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    raise AssertionError("No populated published SQLite file is available in outputs/.")


def _sort_columns(frame: pd.DataFrame, period_columns: list[str]) -> pd.DataFrame:
    order_columns = [*period_columns, "DisplayOrder", "StatementSection", "LineLabel", "LineType", "Amount"]
    sorted_frame = frame[order_columns].copy()
    sorted_frame["Amount"] = sorted_frame["Amount"].round(2)
    return sorted_frame.sort_values(order_columns[:-1]).reset_index(drop=True)


def _cash_reconciliation_assertions(frame: pd.DataFrame, period_columns: list[str]) -> None:
    subtotals = (
        frame[frame["LineLabel"].isin(["Beginning Cash", "Net Change in Cash", "Ending Cash"])]
        .pivot_table(
            index=period_columns,
            columns="LineLabel",
            values="Amount",
            aggfunc="first",
        )
        .reset_index()
    )

    assert not subtotals.empty
    assert (
        (subtotals["Beginning Cash"] + subtotals["Net Change in Cash"]).round(2)
        == subtotals["Ending Cash"].round(2)
    ).all()


def _section_subtotal_assertions(frame: pd.DataFrame, period_columns: list[str]) -> None:
    detail = frame[frame["LineType"].eq("account")].copy()
    detail_sums = (
        detail[detail["StatementSection"].isin(SECTION_TO_SUBTOTAL.keys())]
        .groupby([*period_columns, "StatementSection"], as_index=False)["Amount"]
        .sum()
    )
    detail_sums["Amount"] = detail_sums["Amount"].round(2)
    detail_sums["LineLabel"] = detail_sums["StatementSection"].map(SECTION_TO_SUBTOTAL)

    subtotals = frame[frame["LineLabel"].isin(SECTION_TO_SUBTOTAL.values())][
        [*period_columns, "LineLabel", "Amount"]
    ].copy()
    subtotals["Amount"] = subtotals["Amount"].round(2)

    merged = detail_sums.merge(subtotals, on=[*period_columns, "LineLabel"], suffixes=("_expected", "_actual"))
    assert not merged.empty
    assert (merged["Amount_expected"].round(2) == merged["Amount_actual"].round(2)).all()


def _net_change_subtotal_assertions(frame: pd.DataFrame, period_columns: list[str]) -> None:
    subtotals = (
        frame[frame["LineLabel"].isin([
            "Net Cash from Operating Activities",
            "Net Cash from Investing Activities",
            "Net Cash from Financing Activities",
            "Net Change in Cash",
        ])]
        .pivot_table(
            index=period_columns,
            columns="LineLabel",
            values="Amount",
            aggfunc="first",
        )
        .reset_index()
    )

    assert not subtotals.empty
    calculated = (
        subtotals["Net Cash from Operating Activities"]
        + subtotals["Net Cash from Investing Activities"]
        + subtotals["Net Cash from Financing Activities"]
    ).round(2)
    assert calculated.equals(subtotals["Net Change in Cash"].round(2))


def _rollup_cash_flow_monthly_to_quarterly(monthly: pd.DataFrame) -> pd.DataFrame:
    aggregated = monthly[~monthly["LineLabel"].isin(["Beginning Cash", "Ending Cash"])].copy()
    aggregated["FiscalQuarter"] = ((aggregated["FiscalPeriod"].astype(int) - 1) // 3) + 1
    aggregated = (
        aggregated.groupby(
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
    aggregated["Amount"] = aggregated["Amount"].round(2)

    beginning = monthly[
        monthly["LineLabel"].eq("Beginning Cash")
        & monthly["FiscalPeriod"].astype(int).isin([1, 4, 7, 10])
    ].copy()
    beginning["FiscalQuarter"] = ((beginning["FiscalPeriod"].astype(int) - 1) // 3) + 1
    beginning = beginning.drop(columns=["FiscalPeriod"])

    ending = monthly[
        monthly["LineLabel"].eq("Ending Cash")
        & monthly["FiscalPeriod"].astype(int).isin([3, 6, 9, 12])
    ].copy()
    ending["FiscalQuarter"] = ((ending["FiscalPeriod"].astype(int) - 1) // 3) + 1
    ending = ending.drop(columns=["FiscalPeriod"])

    return pd.concat([aggregated, beginning, ending], ignore_index=True)


def _rollup_cash_flow_monthly_to_annual(monthly: pd.DataFrame) -> pd.DataFrame:
    aggregated = monthly[~monthly["LineLabel"].isin(["Beginning Cash", "Ending Cash"])].copy()
    aggregated = (
        aggregated.groupby(
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
    aggregated["Amount"] = aggregated["Amount"].round(2)

    beginning = monthly[
        monthly["LineLabel"].eq("Beginning Cash")
        & monthly["FiscalPeriod"].astype(int).eq(1)
    ].drop(columns=["FiscalPeriod"])
    ending = monthly[
        monthly["LineLabel"].eq("Ending Cash")
        & monthly["FiscalPeriod"].astype(int).eq(12)
    ].drop(columns=["FiscalPeriod"])

    return pd.concat([aggregated, beginning, ending], ignore_index=True)


def _query_period_counts(context) -> tuple[int, int, int]:
    month_count = len(pd.period_range(context.settings.fiscal_year_start, context.settings.fiscal_year_end, freq="M"))
    quarter_count = len(pd.period_range(context.settings.fiscal_year_start, context.settings.fiscal_year_end, freq="Q-DEC"))
    year_count = (
        pd.Timestamp(context.settings.fiscal_year_end).year
        - pd.Timestamp(context.settings.fiscal_year_start).year
        + 1
    )
    return month_count, quarter_count, year_count


def test_cash_flow_statement_queries_return_rows_on_clean_build(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    context = clean_validation_dataset_artifacts["context"]
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    month_count, quarter_count, year_count = _query_period_counts(context)

    indirect_monthly = _read_sql_result(sqlite_path, INDIRECT_MONTHLY_QUERY_PATH)
    indirect_quarterly = _read_sql_result(sqlite_path, INDIRECT_QUARTERLY_QUERY_PATH)
    indirect_annual = _read_sql_result(sqlite_path, INDIRECT_ANNUAL_QUERY_PATH)
    direct_monthly = _read_sql_result(sqlite_path, DIRECT_MONTHLY_QUERY_PATH)
    direct_quarterly = _read_sql_result(sqlite_path, DIRECT_QUARTERLY_QUERY_PATH)
    direct_annual = _read_sql_result(sqlite_path, DIRECT_ANNUAL_QUERY_PATH)

    for frame in [
        indirect_monthly,
        indirect_quarterly,
        indirect_annual,
        direct_monthly,
        direct_quarterly,
        direct_annual,
    ]:
        assert not frame.empty

    assert list(indirect_monthly.columns) == [
        "FiscalYear",
        "FiscalPeriod",
        "StatementSection",
        "LineLabel",
        "LineType",
        "DisplayOrder",
        "Amount",
    ]
    assert list(indirect_quarterly.columns) == [
        "FiscalYear",
        "FiscalQuarter",
        "StatementSection",
        "LineLabel",
        "LineType",
        "DisplayOrder",
        "Amount",
    ]
    assert list(indirect_annual.columns) == [
        "FiscalYear",
        "StatementSection",
        "LineLabel",
        "LineType",
        "DisplayOrder",
        "Amount",
    ]
    assert list(direct_monthly.columns) == list(indirect_monthly.columns)
    assert list(direct_quarterly.columns) == list(indirect_quarterly.columns)
    assert list(direct_annual.columns) == list(indirect_annual.columns)

    assert indirect_monthly[["FiscalYear", "FiscalPeriod"]].drop_duplicates().shape[0] == month_count
    assert direct_monthly[["FiscalYear", "FiscalPeriod"]].drop_duplicates().shape[0] == month_count
    assert indirect_quarterly[["FiscalYear", "FiscalQuarter"]].drop_duplicates().shape[0] == quarter_count
    assert direct_quarterly[["FiscalYear", "FiscalQuarter"]].drop_duplicates().shape[0] == quarter_count
    assert indirect_annual[["FiscalYear"]].drop_duplicates().shape[0] == year_count
    assert direct_annual[["FiscalYear"]].drop_duplicates().shape[0] == year_count

    assert indirect_monthly.groupby(["FiscalYear", "FiscalPeriod"]).size().nunique() == 1
    assert direct_monthly.groupby(["FiscalYear", "FiscalPeriod"]).size().nunique() == 1
    assert indirect_quarterly.groupby(["FiscalYear", "FiscalQuarter"]).size().nunique() == 1
    assert direct_quarterly.groupby(["FiscalYear", "FiscalQuarter"]).size().nunique() == 1
    assert indirect_annual.groupby(["FiscalYear"]).size().nunique() == 1
    assert direct_annual.groupby(["FiscalYear"]).size().nunique() == 1


def test_cash_flow_monthly_excludes_post_horizon_spillover_years() -> None:
    settings = load_settings("config/settings.yaml")
    sqlite_path = _published_sqlite_path()
    expected_years = set(
        range(
            pd.Timestamp(settings.fiscal_year_start).year,
            pd.Timestamp(settings.fiscal_year_end).year + 1,
        )
    )

    indirect_monthly = _read_sql_result(sqlite_path, INDIRECT_MONTHLY_QUERY_PATH)
    direct_monthly = _read_sql_result(sqlite_path, DIRECT_MONTHLY_QUERY_PATH)

    for frame in [indirect_monthly, direct_monthly]:
        years = set(frame["FiscalYear"].astype(int))
        assert years == expected_years
        assert 2031 not in years
        assert frame[["FiscalYear", "FiscalPeriod"]].drop_duplicates().shape[0] == len(expected_years) * 12


def test_cash_flow_statement_math_ties_for_each_period(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])

    for sql_path, period_columns in [
        (INDIRECT_MONTHLY_QUERY_PATH, ["FiscalYear", "FiscalPeriod"]),
        (INDIRECT_QUARTERLY_QUERY_PATH, ["FiscalYear", "FiscalQuarter"]),
        (INDIRECT_ANNUAL_QUERY_PATH, ["FiscalYear"]),
        (DIRECT_MONTHLY_QUERY_PATH, ["FiscalYear", "FiscalPeriod"]),
        (DIRECT_QUARTERLY_QUERY_PATH, ["FiscalYear", "FiscalQuarter"]),
        (DIRECT_ANNUAL_QUERY_PATH, ["FiscalYear"]),
    ]:
        frame = _read_sql_result(sqlite_path, sql_path)
        _cash_reconciliation_assertions(frame, period_columns)
        _section_subtotal_assertions(frame, period_columns)
        _net_change_subtotal_assertions(frame, period_columns)


def test_quarterly_and_annual_cash_flow_match_monthly_rollups(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])

    indirect_monthly = _read_sql_result(sqlite_path, INDIRECT_MONTHLY_QUERY_PATH)
    indirect_quarterly = _read_sql_result(sqlite_path, INDIRECT_QUARTERLY_QUERY_PATH)
    indirect_annual = _read_sql_result(sqlite_path, INDIRECT_ANNUAL_QUERY_PATH)
    direct_monthly = _read_sql_result(sqlite_path, DIRECT_MONTHLY_QUERY_PATH)
    direct_quarterly = _read_sql_result(sqlite_path, DIRECT_QUARTERLY_QUERY_PATH)
    direct_annual = _read_sql_result(sqlite_path, DIRECT_ANNUAL_QUERY_PATH)

    assert_frame_equal(
        _sort_columns(_rollup_cash_flow_monthly_to_quarterly(indirect_monthly), ["FiscalYear", "FiscalQuarter"]),
        _sort_columns(indirect_quarterly, ["FiscalYear", "FiscalQuarter"]),
    )
    assert_frame_equal(
        _sort_columns(_rollup_cash_flow_monthly_to_annual(indirect_monthly), ["FiscalYear"]),
        _sort_columns(indirect_annual, ["FiscalYear"]),
    )
    assert_frame_equal(
        _sort_columns(_rollup_cash_flow_monthly_to_quarterly(direct_monthly), ["FiscalYear", "FiscalQuarter"]),
        _sort_columns(direct_quarterly, ["FiscalYear", "FiscalQuarter"]),
    )
    assert_frame_equal(
        _sort_columns(_rollup_cash_flow_monthly_to_annual(direct_monthly), ["FiscalYear"]),
        _sort_columns(direct_annual, ["FiscalYear"]),
    )


def test_direct_and_indirect_methods_match_for_net_change_and_ending_cash(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])

    comparisons = [
        (INDIRECT_MONTHLY_QUERY_PATH, DIRECT_MONTHLY_QUERY_PATH, ["FiscalYear", "FiscalPeriod"]),
        (INDIRECT_QUARTERLY_QUERY_PATH, DIRECT_QUARTERLY_QUERY_PATH, ["FiscalYear", "FiscalQuarter"]),
        (INDIRECT_ANNUAL_QUERY_PATH, DIRECT_ANNUAL_QUERY_PATH, ["FiscalYear"]),
    ]

    for indirect_path, direct_path, period_columns in comparisons:
        indirect = _read_sql_result(sqlite_path, indirect_path)
        direct = _read_sql_result(sqlite_path, direct_path)
        labels = ["Net Change in Cash", "Ending Cash"]

        indirect_subset = indirect[indirect["LineLabel"].isin(labels)].copy()
        direct_subset = direct[direct["LineLabel"].isin(labels)].copy()

        assert_frame_equal(
            _sort_columns(indirect_subset, period_columns),
            _sort_columns(direct_subset, period_columns),
        )


def test_ending_cash_matches_balance_sheet_cash_line(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])

    comparisons = [
        (
            DIRECT_MONTHLY_QUERY_PATH,
            INDIRECT_MONTHLY_QUERY_PATH,
            BALANCE_SHEET_MONTHLY_QUERY_PATH,
            ["FiscalYear", "FiscalPeriod"],
        ),
        (
            DIRECT_QUARTERLY_QUERY_PATH,
            INDIRECT_QUARTERLY_QUERY_PATH,
            BALANCE_SHEET_QUARTERLY_QUERY_PATH,
            ["FiscalYear", "FiscalQuarter"],
        ),
        (
            DIRECT_ANNUAL_QUERY_PATH,
            INDIRECT_ANNUAL_QUERY_PATH,
            BALANCE_SHEET_ANNUAL_QUERY_PATH,
            ["FiscalYear"],
        ),
    ]

    for direct_path, indirect_path, balance_sheet_path, period_columns in comparisons:
        direct = _read_sql_result(sqlite_path, direct_path)
        indirect = _read_sql_result(sqlite_path, indirect_path)
        balance_sheet = _read_sql_result(sqlite_path, balance_sheet_path)

        direct_cash = (
            direct[direct["LineLabel"].eq("Ending Cash")][[*period_columns, "Amount"]]
            .rename(columns={"Amount": "DirectEndingCash"})
            .sort_values(period_columns)
            .reset_index(drop=True)
        )
        indirect_cash = (
            indirect[indirect["LineLabel"].eq("Ending Cash")][[*period_columns, "Amount"]]
            .rename(columns={"Amount": "IndirectEndingCash"})
            .sort_values(period_columns)
            .reset_index(drop=True)
        )
        balance_sheet_cash = (
            balance_sheet[balance_sheet["LineLabel"].eq("Cash and Cash Equivalents")][[*period_columns, "Amount"]]
            .rename(columns={"Amount": "BalanceSheetCash"})
            .sort_values(period_columns)
            .reset_index(drop=True)
        )

        merged = direct_cash.merge(indirect_cash, on=period_columns).merge(balance_sheet_cash, on=period_columns)
        assert (merged["DirectEndingCash"].round(2) == merged["BalanceSheetCash"].round(2)).all()
        assert (merged["IndirectEndingCash"].round(2) == merged["BalanceSheetCash"].round(2)).all()


def test_opening_balance_seed_affects_beginning_cash_but_not_flow_sections(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    direct_monthly = _read_sql_result(sqlite_path, DIRECT_MONTHLY_QUERY_PATH)
    first_period = direct_monthly[["FiscalYear", "FiscalPeriod"]].drop_duplicates().sort_values(["FiscalYear", "FiscalPeriod"]).iloc[0]
    first_year = int(first_period["FiscalYear"])
    first_period_number = int(first_period["FiscalPeriod"])

    statement_lines = direct_monthly[
        direct_monthly["FiscalYear"].astype(int).eq(first_year)
        & direct_monthly["FiscalPeriod"].astype(int).eq(first_period_number)
    ]

    opening_cash_sql = """
    SELECT ROUND(SUM(gl.Debit - gl.Credit), 2) AS Amount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountNumber = '1010'
      AND je.EntryType = 'Opening'
    """
    period_cash_excluding_opening_sql = f"""
    SELECT ROUND(SUM(
        CASE
            WHEN COALESCE(je.EntryType, '') = 'Opening' THEN 0
            ELSE gl.Debit - gl.Credit
        END
    ), 2) AS Amount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountNumber = '1010'
      AND gl.FiscalYear = {first_year}
      AND gl.FiscalPeriod = {first_period_number}
      AND COALESCE(je.EntryType, '') NOT IN (
            'Year-End Close - P&L to Income Summary',
            'Year-End Close - Income Summary to Retained Earnings'
      )
    """
    opening_cash = float(_read_sql_text_result(sqlite_path, opening_cash_sql).iloc[0]["Amount"])
    cash_change_excluding_opening = float(_read_sql_text_result(sqlite_path, period_cash_excluding_opening_sql).iloc[0]["Amount"])

    beginning_cash = float(statement_lines[statement_lines["LineLabel"].eq("Beginning Cash")]["Amount"].iloc[0])
    net_change = float(statement_lines[statement_lines["LineLabel"].eq("Net Change in Cash")]["Amount"].iloc[0])
    section_total = float(
        statement_lines[
            statement_lines["LineLabel"].isin([
                "Net Cash from Operating Activities",
                "Net Cash from Investing Activities",
                "Net Cash from Financing Activities",
            ])
        ]["Amount"].sum()
    )

    assert round(beginning_cash, 2) == round(opening_cash, 2)
    assert round(net_change, 2) == round(cash_change_excluding_opening, 2)
    assert round(section_total, 2) == round(cash_change_excluding_opening, 2)


def test_investing_and_financing_rows_are_preserved_when_activity_is_zero(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])

    for sql_path in [
        INDIRECT_MONTHLY_QUERY_PATH,
        INDIRECT_QUARTERLY_QUERY_PATH,
        INDIRECT_ANNUAL_QUERY_PATH,
        DIRECT_MONTHLY_QUERY_PATH,
        DIRECT_QUARTERLY_QUERY_PATH,
        DIRECT_ANNUAL_QUERY_PATH,
    ]:
        frame = _read_sql_result(sqlite_path, sql_path)
        investing = frame[frame["LineLabel"].eq(INVESTING_LINE_LABEL)].copy()
        financing = frame[frame["LineLabel"].eq(FINANCING_LINE_LABEL)].copy()

        assert not investing.empty
        assert not financing.empty
        assert investing["Amount"].round(2).eq(0).all()
        assert financing["Amount"].round(2).eq(0).all()


def test_direct_method_classifies_known_cash_sources(
    clean_validation_dataset_artifacts: dict[str, object],
) -> None:
    sqlite_path = Path(clean_validation_dataset_artifacts["sqlite_path"])
    direct_monthly = _read_sql_result(sqlite_path, DIRECT_MONTHLY_QUERY_PATH)
    direct_totals = (
        direct_monthly.groupby("LineLabel", as_index=False)["Amount"]
        .sum()
        .assign(Amount=lambda df: df["Amount"].round(2))
    )

    raw_source_sql = """
    WITH closed_years AS (
        SELECT
            CAST(substr(PostingDate, 1, 4) AS INTEGER) AS FiscalYear
        FROM JournalEntry
        WHERE EntryType IN (
            'Year-End Close - P&L to Income Summary',
            'Year-End Close - Income Summary to Retained Earnings'
        )
        GROUP BY CAST(substr(PostingDate, 1, 4) AS INTEGER)
        HAVING COUNT(DISTINCT EntryType) = 2
    )
    SELECT
        gl.SourceDocumentType AS SourceDocumentType,
        ROUND(SUM(gl.Debit - gl.Credit), 2) AS Amount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountNumber = '1010'
      AND gl.FiscalYear IN (SELECT FiscalYear FROM closed_years)
      AND COALESCE(je.EntryType, '') NOT IN (
            'Opening',
            'Year-End Close - P&L to Income Summary',
            'Year-End Close - Income Summary to Retained Earnings'
      )
      AND gl.SourceDocumentType IN (
            'CashReceipt',
            'CustomerRefund',
            'DisbursementPayment',
            'PayrollPayment',
            'PayrollLiabilityRemittance'
      )
    GROUP BY gl.SourceDocumentType
    """
    raw_sources = _read_sql_text_result(sqlite_path, raw_source_sql)

    for source_document_type, line_label in DIRECT_LINE_LABELS.items():
        expected_amount = float(
            raw_sources[raw_sources["SourceDocumentType"].eq(source_document_type)]["Amount"].iloc[0]
        )
        actual_amount = float(direct_totals[direct_totals["LineLabel"].eq(line_label)]["Amount"].iloc[0])
        assert round(actual_amount, 2) == round(expected_amount, 2)

    raw_other_operating_sql = """
    WITH closed_years AS (
        SELECT
            CAST(substr(PostingDate, 1, 4) AS INTEGER) AS FiscalYear
        FROM JournalEntry
        WHERE EntryType IN (
            'Year-End Close - P&L to Income Summary',
            'Year-End Close - Income Summary to Retained Earnings'
        )
        GROUP BY CAST(substr(PostingDate, 1, 4) AS INTEGER)
        HAVING COUNT(DISTINCT EntryType) = 2
    )
    SELECT ROUND(SUM(gl.Debit - gl.Credit), 2) AS Amount
    FROM GLEntry AS gl
    JOIN Account AS a
        ON a.AccountID = gl.AccountID
    LEFT JOIN JournalEntry AS je
        ON je.JournalEntryID = gl.SourceDocumentID
       AND gl.SourceDocumentType = 'JournalEntry'
    WHERE a.AccountNumber = '1010'
      AND gl.FiscalYear IN (SELECT FiscalYear FROM closed_years)
      AND gl.SourceDocumentType = 'JournalEntry'
      AND je.EntryType IN ('Rent', 'Utilities', 'Factory Overhead')
    """
    raw_other_operating = float(_read_sql_text_result(sqlite_path, raw_other_operating_sql).iloc[0]["Amount"])
    direct_other_operating = float(
        direct_totals[direct_totals["LineLabel"].eq(OTHER_OPERATING_EXPENSE_LINE_LABEL)]["Amount"].iloc[0]
    )
    assert round(direct_other_operating, 2) == round(raw_other_operating, 2)


def test_cash_flow_docs_and_catalog_entries_exist() -> None:
    query_manifest = Path("src/generated/queryManifest.js").read_text(encoding="utf-8")
    query_doc_collections = Path("src/generated/queryDocCollections.js").read_text(encoding="utf-8")
    financial_guide = Path("docs/analytics/financial.md").read_text(encoding="utf-8")

    for query_key in [
        "financial/33_cash_flow_statement_indirect_monthly.sql",
        "financial/34_cash_flow_statement_indirect_quarterly.sql",
        "financial/35_cash_flow_statement_indirect_annual.sql",
        "financial/36_cash_flow_statement_direct_monthly.sql",
        "financial/37_cash_flow_statement_direct_quarterly.sql",
        "financial/38_cash_flow_statement_direct_annual.sql",
    ]:
        assert query_key in query_manifest
        assert query_key in query_doc_collections

    assert "Monthly indirect cash flow statement" in query_doc_collections
    assert "Quarterly indirect cash flow statement" in query_doc_collections
    assert "Annual indirect cash flow statement" in query_doc_collections
    assert "Monthly direct cash flow statement" in query_doc_collections
    assert "Quarterly direct cash flow statement" in query_doc_collections
    assert "Annual direct cash flow statement" in query_doc_collections
    assert "Cash flow reporting" in financial_guide
    assert "indirect-method cash flow starter queries" in financial_guide
    assert "direct-method cash flow starter queries" in financial_guide
    assert "Beginning Cash" in financial_guide
