from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from generator_dataset.main import build_full_dataset
from generator_dataset.settings import load_settings


@pytest.fixture(scope="session")
def full_dataset_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("full_dataset")
    settings = load_settings("config/settings.yaml")
    payload = dict(vars(settings))
    payload.update({
        "anomaly_mode": "none",
        "export_sqlite": True,
        "export_excel": False,
        "export_support_excel": False,
        "export_csv_zip": False,
        "sqlite_path": str(workdir / "CharlesRiver.sqlite"),
        "excel_path": str(workdir / "CharlesRiver.xlsx"),
        "support_excel_path": str(workdir / "CharlesRiver_support.xlsx"),
        "csv_zip_path": str(workdir / "CharlesRiver_csv.zip"),
        "generation_log_path": str(workdir / "generation.log"),
    })

    config_path = workdir / "settings.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    context = build_full_dataset(config_path)
    return {
        "context": context,
        "workdir": workdir,
        "sqlite_path": Path(payload["sqlite_path"]),
        "support_excel_path": Path(payload["support_excel_path"]),
        "csv_zip_path": Path(payload["csv_zip_path"]),
        "generation_log_path": Path(payload["generation_log_path"]),
    }


@pytest.fixture(scope="session")
def default_anomaly_dataset_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("default_anomaly_dataset")
    settings = load_settings("config/settings.yaml")
    payload = dict(vars(settings))
    payload.update({
        "export_sqlite": True,
        "export_excel": False,
        "export_support_excel": False,
        "export_csv_zip": False,
        "sqlite_path": str(workdir / "CharlesRiver_default.sqlite"),
        "excel_path": str(workdir / "CharlesRiver_default.xlsx"),
        "support_excel_path": str(workdir / "CharlesRiver_default_support.xlsx"),
        "csv_zip_path": str(workdir / "CharlesRiver_default_csv.zip"),
        "generation_log_path": str(workdir / "generation_default.log"),
    })

    config_path = workdir / "settings.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    context = build_full_dataset(config_path)
    return {
        "context": context,
        "workdir": workdir,
        "sqlite_path": Path(payload["sqlite_path"]),
        "excel_path": Path(payload["excel_path"]),
        "support_excel_path": Path(payload["support_excel_path"]),
        "csv_zip_path": Path(payload["csv_zip_path"]),
        "generation_log_path": Path(payload["generation_log_path"]),
    }


@pytest.fixture(scope="session")
def clean_validation_dataset_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("clean_validation_dataset")
    settings = load_settings("config/settings_validation.yaml")
    payload = dict(vars(settings))
    payload.update({
        "export_sqlite": True,
        "export_excel": False,
        "export_support_excel": False,
        "export_csv_zip": False,
        "sqlite_path": str(workdir / "CharlesRiver_validation.sqlite"),
        "excel_path": str(workdir / "CharlesRiver_validation.xlsx"),
        "support_excel_path": str(workdir / "CharlesRiver_validation_support.xlsx"),
        "csv_zip_path": str(workdir / "CharlesRiver_validation_csv.zip"),
        "generation_log_path": str(workdir / "generation.log"),
    })

    config_path = workdir / "settings_validation.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    context = build_full_dataset(config_path)
    return {
        "context": context,
        "workdir": workdir,
        "sqlite_path": Path(payload["sqlite_path"]),
        "support_excel_path": Path(payload["support_excel_path"]),
        "csv_zip_path": Path(payload["csv_zip_path"]),
        "generation_log_path": Path(payload["generation_log_path"]),
    }


@pytest.fixture(scope="session")
def report_validation_dataset_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("report_validation_dataset")
    settings = load_settings("config/settings_validation.yaml")
    payload = dict(vars(settings))
    payload.update({
        "export_sqlite": True,
        "export_excel": False,
        "export_support_excel": False,
        "export_csv_zip": False,
        "export_reports": True,
        "anomaly_mode": "standard",
        "sqlite_path": str(workdir / "CharlesRiver_reports.sqlite"),
        "excel_path": str(workdir / "CharlesRiver_reports.xlsx"),
        "support_excel_path": str(workdir / "CharlesRiver_reports_support.xlsx"),
        "csv_zip_path": str(workdir / "CharlesRiver_reports_csv.zip"),
        "report_output_dir": str(workdir / "site" / "reports"),
        "report_preview_row_count": 25,
        "generation_log_path": str(workdir / "generation_reports.log"),
    })

    config_path = workdir / "settings_reports.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    context = build_full_dataset(config_path)
    return {
        "context": context,
        "workdir": workdir,
        "sqlite_path": Path(payload["sqlite_path"]),
        "report_output_dir": Path(payload["report_output_dir"]),
        "generation_log_path": Path(payload["generation_log_path"]),
    }
