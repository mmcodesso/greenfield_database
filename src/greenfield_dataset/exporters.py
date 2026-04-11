from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from greenfield_dataset.settings import GenerationContext


ANOMALY_LOG_COLUMNS = [
    "anomaly_type",
    "table_name",
    "primary_key_value",
    "fiscal_year",
    "description",
    "expected_detection_test",
]


def anomaly_log_dataframe(context: GenerationContext) -> pd.DataFrame:
    if context.anomaly_log:
        return pd.DataFrame(context.anomaly_log, columns=ANOMALY_LOG_COLUMNS)
    return pd.DataFrame(columns=ANOMALY_LOG_COLUMNS)


def validation_summary_dataframe(context: GenerationContext) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "stage": stage,
            "exception_count": len(details.get("exceptions", [])) if isinstance(details, dict) else None,
            "details": str(details),
        }
        for stage, details in context.validation_results.items()
    ])


def export_sqlite(context: GenerationContext) -> None:
    path = Path(context.settings.sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        for table_name, df in context.tables.items():
            df.to_sql(table_name, connection, if_exists="replace", index=False)
        anomaly_log_dataframe(context).to_sql("AnomalyLog", connection, if_exists="replace", index=False)
        validation_summary_dataframe(context).to_sql("ValidationSummary", connection, if_exists="replace", index=False)


def export_excel(context: GenerationContext) -> None:
    path = Path(context.settings.excel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for table_name, df in context.tables.items():
            df.to_excel(writer, sheet_name=table_name[:31], index=False)
        anomaly_log_dataframe(context).to_excel(writer, sheet_name="AnomalyLog", index=False)
        validation_summary_dataframe(context).to_excel(writer, sheet_name="ValidationSummary", index=False)


def export_validation_report(context: GenerationContext) -> None:
    path = Path(context.settings.validation_report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "validation_results": context.validation_results,
        "anomaly_log": context.anomaly_log,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
