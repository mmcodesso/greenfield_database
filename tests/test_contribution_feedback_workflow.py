from __future__ import annotations

from pathlib import Path


def _read(path: Path) -> str:
    assert path.exists(), f"Missing file: {path}"
    return path.read_text(encoding="utf-8")


def test_contributing_doc_exposes_feedback_workflow() -> None:
    text = _read(Path("docs/technical/contributing.md"))

    for snippet in (
        "## Report an error",
        "## Suggest an improvement",
        "## How we use feedback",
        'kind="error"',
        'kind="recommendation"',
        "Report an Error in GitHub Issues",
        "Suggest an Improvement in GitHub Discussions",
    ):
        assert snippet in text, f"Missing expected contribution workflow copy: {snippet}"


def test_feedback_templates_exist() -> None:
    for path in (
        Path(".github/ISSUE_TEMPLATE/01-report-error.yml"),
        Path(".github/ISSUE_TEMPLATE/config.yml"),
        Path(".github/DISCUSSION_TEMPLATE/recommendations.yml"),
    ):
        assert path.exists(), f"Missing feedback workflow file: {path}"


def test_feedback_branding_urls_are_canonical() -> None:
    text = _read(Path("config/loadSiteBranding.cjs"))

    for snippet in (
        "https://github.com/mmcodesso/CharlesRiver_Database",
        "issues/new/choose",
        "issues/new?template=01-report-error.yml",
        "discussions/new?category=recommendations",
    ):
        assert snippet in text, f"Missing branding URL: {snippet}"


def test_doc_footer_override_prefills_issue_context() -> None:
    text = _read(Path("src/theme/DocItem/Footer/index.jsx"))

    for snippet in (
        '"page_url"',
        '"page_title"',
        '"source_file"',
        '"section_context"',
        "Report an error on this page",
    ):
        assert snippet in text, f"Missing footer feedback behavior: {snippet}"
