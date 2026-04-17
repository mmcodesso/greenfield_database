from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


AR_DETAIL_QUERY_PATH = Path("queries/financial/45_monthly_ar_aging_detail.sql")
AR_SUMMARY_QUERY_PATH = Path("queries/financial/46_monthly_ar_aging_summary.sql")
AP_DETAIL_QUERY_PATH = Path("queries/financial/47_monthly_ap_aging_detail.sql")
AP_SUMMARY_QUERY_PATH = Path("queries/financial/48_monthly_ap_aging_summary.sql")


def _read_sql_result(sqlite_path: Path, query_path: Path) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(query_path.read_text(encoding="utf-8"), connection)


def _build_monthly_aging_fixture(sqlite_path: Path) -> None:
    with sqlite3.connect(sqlite_path) as connection:
        pd.DataFrame(
            [
                {"CustomerID": 1, "CustomerName": "Atlas Retail", "Region": "East", "CustomerSegment": "Wholesale"},
                {"CustomerID": 2, "CustomerName": "Beacon Design", "Region": "West", "CustomerSegment": "Design Trade"},
            ]
        ).to_sql("Customer", connection, index=False, if_exists="replace")

        pd.DataFrame(
            [
                {
                    "SalesInvoiceID": 101,
                    "InvoiceNumber": "SI-AR-001",
                    "InvoiceDate": "2026-01-10",
                    "DueDate": "2026-01-31",
                    "CustomerID": 1,
                    "GrandTotal": 1000.0,
                },
                {
                    "SalesInvoiceID": 102,
                    "InvoiceNumber": "SI-AR-002",
                    "InvoiceDate": "2026-02-25",
                    "DueDate": "2026-04-10",
                    "CustomerID": 2,
                    "GrandTotal": 500.0,
                },
            ]
        ).to_sql("SalesInvoice", connection, index=False, if_exists="replace")

        pd.DataFrame(
            [
                {
                    "CashReceiptApplicationID": 201,
                    "CashReceiptID": 301,
                    "SalesInvoiceID": 101,
                    "ApplicationDate": "2026-02-15",
                    "AppliedAmount": 200.0,
                },
                {
                    "CashReceiptApplicationID": 202,
                    "CashReceiptID": 302,
                    "SalesInvoiceID": 101,
                    "ApplicationDate": "2026-04-05",
                    "AppliedAmount": 650.0,
                },
            ]
        ).to_sql("CashReceiptApplication", connection, index=False, if_exists="replace")

        pd.DataFrame(
            [
                {
                    "CreditMemoID": 401,
                    "CreditMemoNumber": "CM-AR-001",
                    "CreditMemoDate": "2026-03-20",
                    "OriginalSalesInvoiceID": 101,
                    "GrandTotal": 150.0,
                }
            ]
        ).to_sql("CreditMemo", connection, index=False, if_exists="replace")

        pd.DataFrame(
            [
                {"SupplierID": 11, "SupplierName": "Cobalt Supply", "SupplierCategory": "Materials", "SupplierRiskRating": "Low"},
                {"SupplierID": 12, "SupplierName": "Delta Components", "SupplierCategory": "Lighting", "SupplierRiskRating": "Medium"},
            ]
        ).to_sql("Supplier", connection, index=False, if_exists="replace")

        pd.DataFrame(
            [
                {
                    "PurchaseInvoiceID": 501,
                    "InvoiceNumber": "PI-AP-001",
                    "InvoiceDate": "2026-01-05",
                    "DueDate": "2026-01-31",
                    "SupplierID": 11,
                    "GrandTotal": 1200.0,
                },
                {
                    "PurchaseInvoiceID": 502,
                    "InvoiceNumber": "PI-AP-002",
                    "InvoiceDate": "2026-02-18",
                    "DueDate": "2026-04-05",
                    "SupplierID": 12,
                    "GrandTotal": 400.0,
                },
            ]
        ).to_sql("PurchaseInvoice", connection, index=False, if_exists="replace")

        pd.DataFrame(
            [
                {
                    "DisbursementID": 601,
                    "PaymentNumber": "DP-001",
                    "PaymentDate": "2026-02-20",
                    "PurchaseInvoiceID": 501,
                    "SupplierID": 11,
                    "Amount": 300.0,
                },
                {
                    "DisbursementID": 602,
                    "PaymentNumber": "DP-002",
                    "PaymentDate": "2026-04-10",
                    "PurchaseInvoiceID": 501,
                    "SupplierID": 11,
                    "Amount": 900.0,
                },
            ]
        ).to_sql("DisbursementPayment", connection, index=False, if_exists="replace")


def _monthly_aging_sqlite_path(tmp_path: Path) -> Path:
    sqlite_path = tmp_path / "monthly_aging.sqlite"
    _build_monthly_aging_fixture(sqlite_path)
    return sqlite_path


def test_monthly_ar_aging_detail_reconstructs_month_end_positions(tmp_path: Path) -> None:
    sqlite_path = _monthly_aging_sqlite_path(tmp_path)
    detail = _read_sql_result(sqlite_path, AR_DETAIL_QUERY_PATH)

    assert sorted(detail["MonthEndDate"].unique().tolist()) == [
        "2026-01-31",
        "2026-02-28",
        "2026-03-31",
        "2026-04-30",
    ]

    atlas_rows = detail.loc[detail["InvoiceNumber"].eq("SI-AR-001"), [
        "MonthEndDate",
        "DaysFromDueAtMonthEnd",
        "AgingBucket",
        "CashAppliedAsOfMonthEnd",
        "CreditMemoAppliedAsOfMonthEnd",
        "OpenAmountAsOfMonthEnd",
    ]].sort_values("MonthEndDate").reset_index(drop=True)

    assert atlas_rows.to_dict(orient="records") == [
        {
            "MonthEndDate": "2026-01-31",
            "DaysFromDueAtMonthEnd": 0,
            "AgingBucket": "Current",
            "CashAppliedAsOfMonthEnd": 0.0,
            "CreditMemoAppliedAsOfMonthEnd": 0.0,
            "OpenAmountAsOfMonthEnd": 1000.0,
        },
        {
            "MonthEndDate": "2026-02-28",
            "DaysFromDueAtMonthEnd": 28,
            "AgingBucket": "1-30 Days",
            "CashAppliedAsOfMonthEnd": 200.0,
            "CreditMemoAppliedAsOfMonthEnd": 0.0,
            "OpenAmountAsOfMonthEnd": 800.0,
        },
        {
            "MonthEndDate": "2026-03-31",
            "DaysFromDueAtMonthEnd": 59,
            "AgingBucket": "31-60 Days",
            "CashAppliedAsOfMonthEnd": 200.0,
            "CreditMemoAppliedAsOfMonthEnd": 150.0,
            "OpenAmountAsOfMonthEnd": 650.0,
        },
    ]

    beacon_feb = detail.loc[
        detail["InvoiceNumber"].eq("SI-AR-002") & detail["MonthEndDate"].eq("2026-02-28")
    ].iloc[0]
    assert int(beacon_feb["DaysFromDueAtMonthEnd"]) == -41
    assert beacon_feb["AgingBucket"] == "Current"
    assert float(beacon_feb["OpenAmountAsOfMonthEnd"]) == 500.0

    assert detail.loc[
        detail["InvoiceNumber"].eq("SI-AR-001") & detail["MonthEndDate"].eq("2026-04-30")
    ].empty


def test_monthly_ar_aging_summary_matches_detail_rollup(tmp_path: Path) -> None:
    sqlite_path = _monthly_aging_sqlite_path(tmp_path)
    detail = _read_sql_result(sqlite_path, AR_DETAIL_QUERY_PATH)
    summary = _read_sql_result(sqlite_path, AR_SUMMARY_QUERY_PATH)

    detail_rollup = (
        detail.groupby(["MonthEndDate", "CustomerName", "Region", "CustomerSegment"], dropna=False)
        .agg(
            OpenInvoiceCount=("InvoiceNumber", "count"),
            TotalOpenAmount=("OpenAmountAsOfMonthEnd", "sum"),
            CurrentAmount=("OpenAmountAsOfMonthEnd", lambda s: round(float(s[detail.loc[s.index, "DaysFromDueAtMonthEnd"] <= 0].sum()), 2)),
            Days1To30Amount=("OpenAmountAsOfMonthEnd", lambda s: round(float(s[detail.loc[s.index, "DaysFromDueAtMonthEnd"].between(1, 30)].sum()), 2)),
            Days31To60Amount=("OpenAmountAsOfMonthEnd", lambda s: round(float(s[detail.loc[s.index, "DaysFromDueAtMonthEnd"].between(31, 60)].sum()), 2)),
            Days61To90Amount=("OpenAmountAsOfMonthEnd", lambda s: round(float(s[detail.loc[s.index, "DaysFromDueAtMonthEnd"].between(61, 90)].sum()), 2)),
            Days90PlusAmount=("OpenAmountAsOfMonthEnd", lambda s: round(float(s[detail.loc[s.index, "DaysFromDueAtMonthEnd"] > 90].sum()), 2)),
            PastDueAmount=("OpenAmountAsOfMonthEnd", lambda s: round(float(s[detail.loc[s.index, "DaysFromDueAtMonthEnd"] > 0].sum()), 2)),
            OldestDaysPastDue=("DaysFromDueAtMonthEnd", lambda s: float(s[s > 0].max()) if (s > 0).any() else None),
        )
        .reset_index()
        .sort_values(["MonthEndDate", "CustomerName"])
        .reset_index(drop=True)
    )

    detail_rollup["OldestDaysPastDue"] = pd.to_numeric(detail_rollup["OldestDaysPastDue"], errors="coerce")
    summary["OldestDaysPastDue"] = pd.to_numeric(summary["OldestDaysPastDue"], errors="coerce")
    pd.testing.assert_frame_equal(
        summary.sort_values(["MonthEndDate", "CustomerName"]).reset_index(drop=True),
        detail_rollup,
        check_dtype=False,
    )


def test_monthly_ap_aging_detail_uses_month_end_cutoff(tmp_path: Path) -> None:
    sqlite_path = _monthly_aging_sqlite_path(tmp_path)
    detail = _read_sql_result(sqlite_path, AP_DETAIL_QUERY_PATH)

    assert sorted(detail["MonthEndDate"].unique().tolist()) == [
        "2026-01-31",
        "2026-02-28",
        "2026-03-31",
        "2026-04-30",
    ]

    cobalt_rows = detail.loc[detail["InvoiceNumber"].eq("PI-AP-001"), [
        "MonthEndDate",
        "DaysFromDueAtMonthEnd",
        "AgingBucket",
        "CashPaidAsOfMonthEnd",
        "OpenAmountAsOfMonthEnd",
    ]].sort_values("MonthEndDate").reset_index(drop=True)

    assert cobalt_rows.to_dict(orient="records") == [
        {
            "MonthEndDate": "2026-01-31",
            "DaysFromDueAtMonthEnd": 0,
            "AgingBucket": "Current",
            "CashPaidAsOfMonthEnd": 0.0,
            "OpenAmountAsOfMonthEnd": 1200.0,
        },
        {
            "MonthEndDate": "2026-02-28",
            "DaysFromDueAtMonthEnd": 28,
            "AgingBucket": "1-30 Days",
            "CashPaidAsOfMonthEnd": 300.0,
            "OpenAmountAsOfMonthEnd": 900.0,
        },
        {
            "MonthEndDate": "2026-03-31",
            "DaysFromDueAtMonthEnd": 59,
            "AgingBucket": "31-60 Days",
            "CashPaidAsOfMonthEnd": 300.0,
            "OpenAmountAsOfMonthEnd": 900.0,
        },
    ]

    delta_april = detail.loc[
        detail["InvoiceNumber"].eq("PI-AP-002") & detail["MonthEndDate"].eq("2026-04-30")
    ].iloc[0]
    assert int(delta_april["DaysFromDueAtMonthEnd"]) == 25
    assert delta_april["AgingBucket"] == "1-30 Days"
    assert float(delta_april["OpenAmountAsOfMonthEnd"]) == 400.0

    assert detail.loc[
        detail["InvoiceNumber"].eq("PI-AP-001") & detail["MonthEndDate"].eq("2026-04-30")
    ].empty


def test_monthly_ap_aging_summary_matches_detail_rollup(tmp_path: Path) -> None:
    sqlite_path = _monthly_aging_sqlite_path(tmp_path)
    detail = _read_sql_result(sqlite_path, AP_DETAIL_QUERY_PATH)
    summary = _read_sql_result(sqlite_path, AP_SUMMARY_QUERY_PATH)

    detail_rollup = (
        detail.groupby(["MonthEndDate", "SupplierName", "SupplierCategory", "SupplierRiskRating"], dropna=False)
        .agg(
            OpenInvoiceCount=("InvoiceNumber", "count"),
            TotalOpenAmount=("OpenAmountAsOfMonthEnd", "sum"),
            CurrentAmount=("OpenAmountAsOfMonthEnd", lambda s: round(float(s[detail.loc[s.index, "DaysFromDueAtMonthEnd"] <= 0].sum()), 2)),
            Days1To30Amount=("OpenAmountAsOfMonthEnd", lambda s: round(float(s[detail.loc[s.index, "DaysFromDueAtMonthEnd"].between(1, 30)].sum()), 2)),
            Days31To60Amount=("OpenAmountAsOfMonthEnd", lambda s: round(float(s[detail.loc[s.index, "DaysFromDueAtMonthEnd"].between(31, 60)].sum()), 2)),
            Days61To90Amount=("OpenAmountAsOfMonthEnd", lambda s: round(float(s[detail.loc[s.index, "DaysFromDueAtMonthEnd"].between(61, 90)].sum()), 2)),
            Days90PlusAmount=("OpenAmountAsOfMonthEnd", lambda s: round(float(s[detail.loc[s.index, "DaysFromDueAtMonthEnd"] > 90].sum()), 2)),
            PastDueAmount=("OpenAmountAsOfMonthEnd", lambda s: round(float(s[detail.loc[s.index, "DaysFromDueAtMonthEnd"] > 0].sum()), 2)),
            OldestDaysPastDue=("DaysFromDueAtMonthEnd", lambda s: float(s[s > 0].max()) if (s > 0).any() else None),
        )
        .reset_index()
        .sort_values(["MonthEndDate", "SupplierName"])
        .reset_index(drop=True)
    )

    detail_rollup["OldestDaysPastDue"] = pd.to_numeric(detail_rollup["OldestDaysPastDue"], errors="coerce")
    summary["OldestDaysPastDue"] = pd.to_numeric(summary["OldestDaysPastDue"], errors="coerce")
    pd.testing.assert_frame_equal(
        summary.sort_values(["MonthEndDate", "SupplierName"]).reset_index(drop=True),
        detail_rollup,
        check_dtype=False,
    )
