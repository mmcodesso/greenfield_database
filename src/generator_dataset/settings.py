from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd
import yaml

from generator_dataset.calendar import build_calendar

OPERATIONAL_HORIZON_BUFFER_DAYS = 84


def derive_short_name(company_name: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9]+", " ", company_name).strip()
    tokens = compact.split()
    legal_suffixes = {"inc", "incorporated", "llc", "ltd", "corp", "corporation", "co", "company"}
    filtered = [token for token in tokens if token.lower() not in legal_suffixes]
    return "".join(filtered[:2] or tokens[:1] or ["Dataset"])


def interpolate_path_template(value: str | None, *, short_name: str) -> str | None:
    if value is None:
        return None
    display_short_name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", short_name).strip()
    return str(value).format(
        short_name=short_name,
        short_name_lower=short_name.lower(),
        short_name_display=display_short_name,
    )


def derive_base_url(short_name: str) -> str:
    return f"https://{short_name.lower()}.accountinganalyticshub.com"


@dataclass(frozen=True)
class Settings:
    random_seed: int
    fiscal_year_start: str
    fiscal_year_end: str
    company_name: str
    short_name: str
    base_url: str
    tax_rate: float
    employee_count: int
    customer_count: int
    supplier_count: int
    item_count: int
    warehouse_count: int
    export_sqlite: bool
    export_excel: bool
    anomaly_mode: str
    sqlite_path: str
    excel_path: str
    export_support_excel: bool = False
    support_excel_path: str = "outputs/{short_name}_support.xlsx"
    export_csv_zip: bool = False
    csv_zip_path: str = "outputs/{short_name}_csv.zip"
    export_reports: bool = False
    report_output_dir: str = "outputs/reports"
    report_preview_row_count: int = 25
    published_sqlite_url: str | None = None
    validation_report_path: str | None = None
    generation_log_path: str = "outputs/generation.log"


@dataclass
class GenerationContext:
    settings: Settings
    rng: np.random.Generator
    calendar: pd.DataFrame
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=dict)
    anomaly_log: list[dict[str, Any]] = field(default_factory=list)
    validation_results: dict[str, Any] = field(default_factory=dict)


def load_settings(config_path: str | Path) -> Settings:
    with Path(config_path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise ValueError(f"Settings file must contain a mapping: {config_path}")

    normalized = dict(raw)
    normalized.setdefault("short_name", derive_short_name(str(normalized["company_name"])))
    normalized.setdefault("base_url", derive_base_url(str(normalized["short_name"])))
    legacy_validation_path = normalized.get("validation_report_path")

    short_name = str(normalized["short_name"])

    if "sqlite_path" not in normalized:
        normalized["sqlite_path"] = "outputs/{short_name}.sqlite"

    if "excel_path" not in normalized:
        normalized["excel_path"] = "outputs/{short_name}.xlsx"

    if "support_excel_path" not in normalized:
        if legacy_validation_path:
            normalized["support_excel_path"] = str(Path(legacy_validation_path).with_suffix(".xlsx"))
        else:
            excel_path = Path(str(normalized.get("excel_path", "outputs/{short_name}.xlsx")))
            normalized["support_excel_path"] = str(excel_path.with_name(f"{excel_path.stem}_support.xlsx"))

    if "csv_zip_path" not in normalized:
        excel_path = Path(str(normalized.get("excel_path", "outputs/{short_name}.xlsx")))
        normalized["csv_zip_path"] = str(excel_path.with_name(f"{excel_path.stem}_csv.zip"))

    if "export_support_excel" not in normalized:
        normalized["export_support_excel"] = bool(legacy_validation_path)

    if "export_csv_zip" not in normalized:
        normalized["export_csv_zip"] = False

    if "export_reports" not in normalized:
        normalized["export_reports"] = False

    if "report_output_dir" not in normalized:
        normalized["report_output_dir"] = "outputs/reports"

    if "report_preview_row_count" not in normalized:
        normalized["report_preview_row_count"] = 25

    for path_key in [
        "sqlite_path",
        "excel_path",
        "support_excel_path",
        "csv_zip_path",
        "report_output_dir",
        "published_sqlite_url",
        "generation_log_path",
        "validation_report_path",
    ]:
        normalized[path_key] = interpolate_path_template(
            normalized.get(path_key),
            short_name=short_name,
        )

    if normalized["export_reports"] and not normalized["export_sqlite"]:
        raise ValueError("export_reports requires export_sqlite to be enabled.")

    if int(normalized["report_preview_row_count"]) <= 0:
        raise ValueError("report_preview_row_count must be greater than zero.")

    return Settings(**normalized)


def initialize_context(settings: Settings) -> GenerationContext:
    rng = np.random.default_rng(settings.random_seed)
    operational_calendar_end = (
        pd.Timestamp(settings.fiscal_year_end).normalize() + pd.Timedelta(days=OPERATIONAL_HORIZON_BUFFER_DAYS)
    )
    calendar = build_calendar(settings.fiscal_year_start, operational_calendar_end.strftime("%Y-%m-%d"))
    return GenerationContext(settings=settings, rng=rng, calendar=calendar)
