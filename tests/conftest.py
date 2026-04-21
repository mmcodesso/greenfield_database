from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import yaml

from generator_dataset.anomalies import inject_anomalies, invalidate_all_caches
from generator_dataset.exporters import export_csv_zip, export_excel, export_reports, export_sqlite, export_support_excel
from generator_dataset.main import build_full_dataset
from generator_dataset.settings import GenerationContext, load_settings
from generator_dataset.validations import validate_phase8


def _artifact_paths(workdir: Path, output_stem: str) -> dict[str, Path]:
    return {
        "sqlite_path": workdir / f"{output_stem}.sqlite",
        "excel_path": workdir / f"{output_stem}.xlsx",
        "support_excel_path": workdir / f"{output_stem}_support.xlsx",
        "csv_zip_path": workdir / f"{output_stem}_csv.zip",
        "report_output_dir": workdir / "site" / "reports",
        "generation_log_path": workdir / "generation.log",
    }


def _artifact_result(
    *,
    context: GenerationContext,
    workdir: Path,
    paths: dict[str, Path],
    config_path: Path | None = None,
) -> dict[str, object]:
    return {
        "context": context,
        "workdir": workdir,
        "config_path": config_path,
        "sqlite_path": paths["sqlite_path"],
        "excel_path": paths["excel_path"],
        "support_excel_path": paths["support_excel_path"],
        "csv_zip_path": paths["csv_zip_path"],
        "report_output_dir": paths["report_output_dir"],
        "generation_log_path": paths["generation_log_path"],
    }


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
    paths = _artifact_paths(workdir, output_stem)
    settings = load_settings(source_config_path)
    payload = dict(vars(settings))
    payload.update({key: str(value) for key, value in paths.items()})
    if overrides:
        payload.update(overrides)

    config_path = workdir / config_name
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    context = build_full_dataset(config_path)
    return _artifact_result(context=context, workdir=workdir, paths=paths, config_path=config_path)


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


def _append_validation_log(log_path: Path, phase_name: str, results: dict[str, object]) -> None:
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\nVALIDATION | {phase_name} | direct_exceptions={len(results.get('exceptions', []))}\n")
        for key, value in results.items():
            if not isinstance(value, dict) or "exception_count" not in value:
                continue
            handle.write(f"VALIDATION | {phase_name}.{key} | exception_count={value['exception_count']}")
            scalar_metrics: list[str] = []
            for metric_key, metric_value in value.items():
                if metric_key in {"exception_count", "exceptions"}:
                    continue
                if isinstance(metric_value, dict):
                    continue
                scalar_metrics.append(f"{metric_key}={metric_value}")
            if scalar_metrics:
                handle.write(f" | {' | '.join(scalar_metrics)}")
            handle.write("\n")


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
def default_anomaly_core_artifacts(
    full_dataset_artifacts: dict[str, object],
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("default_anomaly_core_dataset")
    paths = _artifact_paths(workdir, "CharlesRiver_default")
    context = _clone_generation_context(full_dataset_artifacts["context"])
    context.settings = replace(
        context.settings,
        anomaly_mode="standard",
        export_sqlite=True,
        export_excel=False,
        export_support_excel=False,
        export_csv_zip=False,
        export_reports=False,
        sqlite_path=str(paths["sqlite_path"]),
        excel_path=str(paths["excel_path"]),
        support_excel_path=str(paths["support_excel_path"]),
        csv_zip_path=str(paths["csv_zip_path"]),
        report_output_dir=str(paths["report_output_dir"]),
        generation_log_path=str(paths["generation_log_path"]),
    )

    inject_anomalies(context)
    invalidate_all_caches(context)
    validate_phase8(context, scope="full")
    export_sqlite(context)

    base_log_path = Path(full_dataset_artifacts["generation_log_path"])
    paths["generation_log_path"].write_text(base_log_path.read_text(encoding="utf-8"), encoding="utf-8")
    with paths["generation_log_path"].open("a", encoding="utf-8") as handle:
        handle.write(f"\nANOMALIES | total_count={len(context.anomaly_log)}\n")
    _append_validation_log(paths["generation_log_path"], "phase8", context.validation_results["phase8"])

    return _artifact_result(context=context, workdir=workdir, paths=paths)


@pytest.fixture(scope="session")
def default_anomaly_published_package_artifacts(
    default_anomaly_core_artifacts: dict[str, object],
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("default_anomaly_published_package_dataset")
    paths = _artifact_paths(workdir, "CharlesRiver_default_publish")
    context = _clone_generation_context(default_anomaly_core_artifacts["context"])
    sqlite_path = Path(default_anomaly_core_artifacts["sqlite_path"])
    generation_log_path = Path(default_anomaly_core_artifacts["generation_log_path"])
    context.settings = replace(
        context.settings,
        export_sqlite=True,
        export_excel=True,
        export_support_excel=True,
        export_csv_zip=True,
        export_reports=False,
        sqlite_path=str(sqlite_path),
        excel_path=str(paths["excel_path"]),
        support_excel_path=str(paths["support_excel_path"]),
        csv_zip_path=str(paths["csv_zip_path"]),
        report_output_dir=str(paths["report_output_dir"]),
        generation_log_path=str(generation_log_path),
    )

    export_excel(context)
    export_support_excel(context)
    export_csv_zip(context)

    published_paths = dict(paths)
    published_paths["sqlite_path"] = sqlite_path
    published_paths["generation_log_path"] = generation_log_path
    return _artifact_result(context=context, workdir=workdir, paths=published_paths)


@pytest.fixture(scope="session")
def default_anomaly_dataset_artifacts(default_anomaly_core_artifacts: dict[str, object]) -> dict[str, object]:
    return default_anomaly_core_artifacts


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
def validation_anomaly_dataset_artifacts(
    clean_validation_dataset_artifacts: dict[str, object],
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("validation_anomaly_dataset")
    paths = _artifact_paths(workdir, "CharlesRiver_validation_anomaly")
    context = _clone_generation_context(clean_validation_dataset_artifacts["context"])
    context.settings = replace(
        context.settings,
        anomaly_mode="standard",
        export_sqlite=True,
        export_excel=False,
        export_support_excel=False,
        export_csv_zip=False,
        export_reports=False,
        sqlite_path=str(paths["sqlite_path"]),
        excel_path=str(paths["excel_path"]),
        support_excel_path=str(paths["support_excel_path"]),
        csv_zip_path=str(paths["csv_zip_path"]),
        report_output_dir=str(paths["report_output_dir"]),
        generation_log_path=str(paths["generation_log_path"]),
    )

    inject_anomalies(context)
    invalidate_all_caches(context)
    validate_phase8(context, scope="full")
    export_sqlite(context)

    base_log_path = Path(clean_validation_dataset_artifacts["generation_log_path"])
    paths["generation_log_path"].write_text(base_log_path.read_text(encoding="utf-8"), encoding="utf-8")
    with paths["generation_log_path"].open("a", encoding="utf-8") as handle:
        handle.write(f"\nANOMALIES | total_count={len(context.anomaly_log)}\n")
    _append_validation_log(paths["generation_log_path"], "phase8", context.validation_results["phase8"])

    return _artifact_result(context=context, workdir=workdir, paths=paths)


@pytest.fixture(scope="session")
def report_validation_dataset_artifacts(
    validation_anomaly_dataset_artifacts: dict[str, object],
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    workdir = tmp_path_factory.mktemp("report_validation_dataset")
    paths = _artifact_paths(workdir, "CharlesRiver_reports")
    context = _clone_generation_context(validation_anomaly_dataset_artifacts["context"])
    sqlite_path = Path(validation_anomaly_dataset_artifacts["sqlite_path"])
    generation_log_path = Path(validation_anomaly_dataset_artifacts["generation_log_path"])
    context.settings = replace(
        context.settings,
        export_sqlite=True,
        export_excel=False,
        export_support_excel=False,
        export_csv_zip=False,
        export_reports=True,
        sqlite_path=str(sqlite_path),
        excel_path=str(paths["excel_path"]),
        support_excel_path=str(paths["support_excel_path"]),
        csv_zip_path=str(paths["csv_zip_path"]),
        report_output_dir=str(paths["report_output_dir"]),
        report_preview_row_count=25,
        generation_log_path=str(generation_log_path),
    )

    export_reports(context)

    report_paths = dict(paths)
    report_paths["sqlite_path"] = sqlite_path
    report_paths["generation_log_path"] = generation_log_path
    return _artifact_result(context=context, workdir=workdir, paths=report_paths)
