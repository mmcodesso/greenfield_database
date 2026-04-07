from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from greenfield_dataset.calendar import build_calendar


@dataclass(frozen=True)
class Settings:
    random_seed: int
    fiscal_year_start: str
    fiscal_year_end: str
    company_name: str
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
    validation_report_path: str
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

    return Settings(**raw)


def initialize_context(settings: Settings) -> GenerationContext:
    rng = np.random.default_rng(settings.random_seed)
    calendar = build_calendar(settings.fiscal_year_start, settings.fiscal_year_end)
    return GenerationContext(settings=settings, rng=rng, calendar=calendar)
