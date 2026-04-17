from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from generator_dataset.exporters import export_reports
from generator_dataset.settings import Settings, initialize_context, load_settings


def build_settings(
    config_path: str | Path,
    *,
    sqlite_path: str | Path,
    report_output_dir: str | Path | None,
    report_preview_row_count: int | None,
) -> Settings:
    base_settings = load_settings(config_path)
    payload = dict(vars(base_settings))
    payload.update({
        "sqlite_path": str(Path(sqlite_path)),
        "export_sqlite": True,
        "export_reports": True,
    })

    if report_output_dir is not None:
        payload["report_output_dir"] = str(Path(report_output_dir))

    if report_preview_row_count is not None:
        payload["report_preview_row_count"] = int(report_preview_row_count)

    return Settings(**payload)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate site report assets from an existing SQLite database.",
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Settings YAML used to load report configuration defaults.",
    )
    parser.add_argument(
        "--sqlite-path",
        required=True,
        help="Path to the existing SQLite database used to build report artifacts.",
    )
    parser.add_argument(
        "--report-output-dir",
        default=None,
        help="Optional override for the report output directory.",
    )
    parser.add_argument(
        "--report-preview-row-count",
        type=int,
        default=None,
        help="Optional override for the site preview row limit.",
    )
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

    settings = build_settings(
        args.config,
        sqlite_path=sqlite_path,
        report_output_dir=args.report_output_dir,
        report_preview_row_count=args.report_preview_row_count,
    )
    context = initialize_context(settings)
    export_reports(context)
    print(settings.report_output_dir)


if __name__ == "__main__":
    main()
