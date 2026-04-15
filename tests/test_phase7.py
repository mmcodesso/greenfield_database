from dataclasses import replace
from pathlib import Path
import sqlite3
from zipfile import ZipFile

from openpyxl import load_workbook

from generator_dataset.anomalies import inject_anomalies
from generator_dataset.exporters import export_csv_zip, export_excel, export_sqlite, export_support_excel
from generator_dataset.main import build_phase6
from generator_dataset.validations import validate_phase7


def test_phase7_anomalies_and_exports(tmp_path: Path) -> None:
    context = build_phase6()
    context.settings = replace(
        context.settings,
        export_support_excel=True,
        export_csv_zip=True,
        sqlite_path=str(tmp_path / "CharlesRiver.sqlite"),
        excel_path=str(tmp_path / "CharlesRiver.xlsx"),
        support_excel_path=str(tmp_path / "CharlesRiver_support.xlsx"),
        csv_zip_path=str(tmp_path / "CharlesRiver_csv.zip"),
    )

    inject_anomalies(context)
    results = validate_phase7(context)
    export_sqlite(context)
    export_excel(context)
    export_support_excel(context)
    export_csv_zip(context)

    assert results["exceptions"] == []
    assert results["anomaly_count"] > 0
    assert results["gl_balance"]["exception_count"] == 0
    assert (tmp_path / "CharlesRiver.sqlite").exists()
    assert (tmp_path / "CharlesRiver.xlsx").exists()
    assert (tmp_path / "CharlesRiver_support.xlsx").exists()
    assert (tmp_path / "CharlesRiver_csv.zip").exists()

    with sqlite3.connect(tmp_path / "CharlesRiver.sqlite") as connection:
        exported_tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert "AnomalyLog" not in exported_tables
    assert "ValidationSummary" not in exported_tables

    dataset_workbook = load_workbook(tmp_path / "CharlesRiver.xlsx")
    support_workbook = load_workbook(tmp_path / "CharlesRiver_support.xlsx")

    assert "AnomalyLog" not in dataset_workbook.sheetnames
    assert "ValidationStages" not in dataset_workbook.sheetnames
    for sheet_name in ["Account", "SalesOrder", "GLEntry"]:
        assert len(dataset_workbook[sheet_name].tables) >= 1

    assert {"Overview", "AnomalyLog", "ValidationStages", "ValidationChecks", "ValidationExceptions"}.issubset(
        set(support_workbook.sheetnames)
    )
    for sheet_name in ["Overview", "AnomalyLog", "ValidationStages", "ValidationChecks", "ValidationExceptions"]:
        assert len(support_workbook[sheet_name].tables) >= 1

    with ZipFile(tmp_path / "CharlesRiver_csv.zip") as archive:
        zip_members = set(archive.namelist())
    assert zip_members == {f"{table_name}.csv" for table_name in context.tables}
