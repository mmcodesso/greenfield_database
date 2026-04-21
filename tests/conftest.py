from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from generator_dataset.main import build_full_dataset
from generator_dataset.settings import GenerationContext, load_settings


def _build_dataset_artifacts(
    tmp_path_factory: pytest.TempPathFactory,
    *,
    temp_dir_name: str,
    source_config_path: str,
    config_name: str,
    output_stem: str,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp(temp_dir_name)
    settings = load_settings(source_config_path)
    payload = dict(vars(settings))
    payload.update(
        {
            "sqlite_path": str(workdir / f"{output_stem}.sqlite"),
            "excel_path": str(workdir / f"{output_stem}.xlsx"),
            "support_excel_path": str(workdir / f"{output_stem}_support.xlsx"),
            "csv_zip_path": str(workdir / f"{output_stem}_csv.zip"),
            "report_output_dir": str(workdir / "site" / "reports"),
            "generation_log_path": str(workdir / "generation.log"),
        }
    )
    if overrides:
        payload.update(overrides)

    config_path = workdir / config_name
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    context = build_full_dataset(config_path)
    return {
        "context": context,
        "workdir": workdir,
        "config_path": config_path,
        "sqlite_path": Path(payload["sqlite_path"]),
        "excel_path": Path(payload["excel_path"]),
        "support_excel_path": Path(payload["support_excel_path"]),
        "csv_zip_path": Path(payload["csv_zip_path"]),
        "report_output_dir": Path(payload["report_output_dir"]),
        "generation_log_path": Path(payload["generation_log_path"]),
    }


def _clone_generation_context(context: GenerationContext) -> GenerationContext:
    rng = np.random.default_rng()
    rng.bit_generator.state = copy.deepcopy(context.rng.bit_generator.state)
    return GenerationContext(
        settings=context.settings,
        rng=rng,
        calendar=context.calendar.copy(deep=True),
        tables={table_name: table.copy(deep=True) for table_name, table in context.tables.items()},
        counters=copy.deepcopy(context.counters),
        anomaly_log=copy.deepcopy(context.anomaly_log),
        validation_results=copy.deepcopy(context.validation_results),
    )


@pytest.fixture
def clone_generation_context():
    return _clone_generation_context


@pytest.fixture(scope="session")
def full_dataset_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    return _build_dataset_artifacts(
        tmp_path_factory,
        temp_dir_name="full_dataset",
        source_config_path="config/settings.yaml",
        config_name="settings.yaml",
        output_stem="CharlesRiver",
        overrides={
            "anomaly_mode": "none",
            "export_sqlite": True,
            "export_excel": False,
            "export_support_excel": False,
            "export_csv_zip": False,
            "export_reports": False,
        },
    )


@pytest.fixture(scope="session")
def default_anomaly_core_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    return _build_dataset_artifacts(
        tmp_path_factory,
        temp_dir_name="default_anomaly_core_dataset",
        source_config_path="config/settings.yaml",
        config_name="settings.yaml",
        output_stem="CharlesRiver_default",
        overrides={
            "anomaly_mode": "standard",
            "export_sqlite": True,
            "export_excel": False,
            "export_support_excel": False,
            "export_csv_zip": False,
            "export_reports": False,
        },
    )


@pytest.fixture(scope="session")
def default_anomaly_published_package_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    return _build_dataset_artifacts(
        tmp_path_factory,
        temp_dir_name="default_anomaly_published_package_dataset",
        source_config_path="config/settings.yaml",
        config_name="settings.yaml",
        output_stem="CharlesRiver_default_publish",
        overrides={
            "anomaly_mode": "standard",
            "export_sqlite": True,
            "export_excel": True,
            "export_support_excel": True,
            "export_csv_zip": True,
            "export_reports": False,
        },
    )


@pytest.fixture(scope="session")
def default_anomaly_dataset_artifacts(default_anomaly_core_artifacts: dict[str, object]) -> dict[str, object]:
    return default_anomaly_core_artifacts


@pytest.fixture(scope="session")
def clean_validation_dataset_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    return _build_dataset_artifacts(
        tmp_path_factory,
        temp_dir_name="clean_validation_dataset",
        source_config_path="config/settings_validation.yaml",
        config_name="settings_validation.yaml",
        output_stem="CharlesRiver_validation",
        overrides={
            "anomaly_mode": "none",
            "export_sqlite": True,
            "export_excel": False,
            "export_support_excel": False,
            "export_csv_zip": False,
            "export_reports": False,
        },
    )


@pytest.fixture(scope="session")
def one_year_clean_dataset_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    return _build_dataset_artifacts(
        tmp_path_factory,
        temp_dir_name="one_year_clean_dataset",
        source_config_path="config/settings.yaml",
        config_name="settings_one_year_clean.yaml",
        output_stem="CharlesRiver_2026_clean",
        overrides={
            "anomaly_mode": "none",
            "export_sqlite": False,
            "export_excel": False,
            "export_support_excel": False,
            "export_csv_zip": False,
            "export_reports": False,
            "fiscal_year_start": "2026-01-01",
            "fiscal_year_end": "2026-12-31",
        },
    )


@pytest.fixture(scope="session")
def validation_anomaly_dataset_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    return _build_dataset_artifacts(
        tmp_path_factory,
        temp_dir_name="validation_anomaly_dataset",
        source_config_path="config/settings_validation.yaml",
        config_name="settings_validation_anomaly.yaml",
        output_stem="CharlesRiver_validation_anomaly",
        overrides={
            "anomaly_mode": "standard",
            "export_sqlite": True,
            "export_excel": False,
            "export_support_excel": False,
            "export_csv_zip": False,
            "export_reports": False,
        },
    )


@pytest.fixture(scope="session")
def report_validation_dataset_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    return _build_dataset_artifacts(
        tmp_path_factory,
        temp_dir_name="report_validation_dataset",
        source_config_path="config/settings_validation.yaml",
        config_name="settings_reports.yaml",
        output_stem="CharlesRiver_reports",
        overrides={
            "anomaly_mode": "standard",
            "export_sqlite": True,
            "export_excel": False,
            "export_support_excel": False,
            "export_csv_zip": False,
            "export_reports": True,
            "report_preview_row_count": 25,
        },
    )
