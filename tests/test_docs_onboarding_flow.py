from __future__ import annotations

from pathlib import Path


FLAGSHIP_DOCS: dict[Path, tuple[str, ...]] = {
    Path("docs/start-here/index.md"): (
        "business cycles",
        "How the Business Reaches Analysis",
        "## Next Steps",
    ),
    Path("docs/start-here/downloads.md"): (
        "same business",
        "How the Files Fit the Business Story",
        "## Next Steps",
    ),
    Path("docs/learn-the-business/company-story.md"): (
        "connected operating system",
        "How the Business Actually Works",
        "## Next Steps",
    ),
    Path("docs/learn-the-business/process-flows.md"): (
        "Process to Analysis Bridges",
        "business process first, accounting second, analysis third",
        "## Next Steps",
    ),
}


PROCESS_NEXT_STEP_LINKS: dict[Path, tuple[str, ...]] = {
    Path("docs/processes/o2c.md"): (
        "## Next Steps",
        "../analytics/reports/commercial-and-working-capital.md",
        "../analytics/cases/o2c-trace-case.md",
    ),
    Path("docs/processes/p2p.md"): (
        "## Next Steps",
        "../analytics/reports/commercial-and-working-capital.md",
        "../analytics/cases/p2p-accrual-settlement-case.md",
    ),
    Path("docs/processes/manufacturing.md"): (
        "## Next Steps",
        "../analytics/reports/operations-and-risk.md",
        "../analytics/cases/manufacturing-labor-cost-case.md",
    ),
    Path("docs/processes/payroll.md"): (
        "## Next Steps",
        "../analytics/reports/payroll-perspective.md",
        "../analytics/cases/workforce-cost-and-org-control-case.md",
    ),
}

FORBIDDEN_PUBLIC_COPY = (
    "Audience and Purpose",
    "Use this page when",
    "Use this case when",
    "Use this pack",
    "Use this perspective",
    "This perspective matters because",
    "Why this matters",
    "Why This Report Belongs",
    "Why it matters here",
    "This page matters because",
)

CASE_DOCS_WITH_BEFORE_YOU_START = (
    Path("docs/analytics/cases/working-capital-and-cash-conversion-case.md"),
    Path("docs/analytics/cases/financial-statement-bridge-case.md"),
    Path("docs/analytics/cases/capex-fixed-asset-lifecycle-case.md"),
    Path("docs/analytics/cases/pricing-and-margin-governance-case.md"),
    Path("docs/analytics/cases/product-portfolio-profitability-case.md"),
    Path("docs/analytics/cases/workforce-coverage-and-attendance-case.md"),
    Path("docs/analytics/cases/demand-planning-and-replenishment-case.md"),
    Path("docs/analytics/cases/master-data-and-workforce-audit-case.md"),
    Path("docs/analytics/cases/workforce-cost-and-org-control-case.md"),
    Path("docs/analytics/cases/audit-review-pack-case.md"),
    Path("docs/analytics/cases/attendance-control-audit-case.md"),
    Path("docs/analytics/cases/replenishment-support-audit-case.md"),
    Path("docs/analytics/cases/pricing-governance-audit-case.md"),
)


def _read(path: Path) -> str:
    assert path.exists(), f"Missing doc page: {path}"
    return path.read_text(encoding="utf-8")


def test_flagship_docs_keep_process_led_structure() -> None:
    for path, expected_snippets in FLAGSHIP_DOCS.items():
        text = _read(path)
        opening = "\n".join(text.splitlines()[:24]).lower()

        for snippet in expected_snippets:
            assert snippet in text, f"Missing expected snippet in {path}: {snippet}"

        assert "choose your path" not in opening
        assert "when to use it" not in opening
        assert "what this helps students do" not in opening


def test_process_pages_bridge_into_perspectives_reports_and_cases() -> None:
    for path, expected_snippets in PROCESS_NEXT_STEP_LINKS.items():
        text = _read(path)

        for snippet in expected_snippets:
            assert snippet in text, f"Missing expected snippet in {path}: {snippet}"


def test_start_here_and_process_flows_point_into_the_same_learning_sequence() -> None:
    start_here = _read(Path("docs/start-here/index.md"))
    process_flows = _read(Path("docs/learn-the-business/process-flows.md"))

    for snippet in (
        "../learn-the-business/company-story.md",
        "../learn-the-business/process-flows.md",
        "../processes/design-services.md",
        "../analytics/index.md",
        "../analytics/reports/index.md",
        "../analytics/cases/index.md",
    ):
        assert snippet in start_here

    for snippet in (
        "../processes/o2c.md",
        "../processes/p2p.md",
        "../processes/manufacturing.md",
        "../processes/payroll.md",
        "../analytics/index.md",
        "../analytics/reports/index.md",
        "../analytics/cases/index.md",
    ):
        assert snippet in process_flows


def test_company_story_keeps_required_story_anchors_and_links() -> None:
    company_story = _read(Path("docs/learn-the-business/company-story.md"))

    for snippet in (
        "Charles River",
        "greater Boston area",
        "buys some finished goods",
        "manufactures a selected subset",
        "Design Services",
        "connected operating system",
        "## How the Business Actually Works",
        "## Next Steps",
        "process-flows.md",
        "../processes/design-services.md",
        "../analytics/index.md",
        "../analytics/reports/index.md",
    ):
        assert snippet in company_story


def test_analyze_data_sidebar_uses_new_labels_and_keeps_cases_above_tracks() -> None:
    sidebar_text = _read(Path("sidebars.js"))
    analytics_page = _read(Path("docs/analytics/index.md"))
    tracks_page = _read(Path("docs/analytics/analysis-tracks.md"))
    cases_page = _read(Path("docs/analytics/cases/index.md"))

    assert 'label: "Analyze the Data"' in sidebar_text
    assert 'label: "Cases"' in sidebar_text
    assert 'label: "Analysis Tracks"' in sidebar_text
    assert 'title: Analyze the Data' in analytics_page
    assert 'sidebar_label: Analyze the Data' in analytics_page
    assert 'title: Analysis Tracks' in tracks_page
    assert 'sidebar_label: Analysis Tracks' in tracks_page
    assert 'title: Cases' in cases_page
    assert 'sidebar_label: Cases' in cases_page
    for snippet in (
        "sql-guide.md",
        "excel-guide.md",
        "reports/index.md",
        "cases/index.md",
        "analysis-tracks.md",
    ):
        assert snippet in analytics_page
    assert "How Cases Fit the Learning Path" in cases_page
    assert "## Next Steps" in cases_page

    cases_position = sidebar_text.index('label: "Cases"')
    guides_position = sidebar_text.index('label: "Analysis Tracks"')
    assert cases_position < guides_position


def test_public_docs_and_generated_manifest_drop_template_style_phrasing() -> None:
    doc_paths = Path("docs").rglob("*.md")

    for path in doc_paths:
        text = _read(path)
        for forbidden in FORBIDDEN_PUBLIC_COPY:
            assert forbidden not in text, f"Found forbidden copy in {path}: {forbidden}"

    manifest_text = Path("src/generated/reportPackManifest.js").read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_PUBLIC_COPY:
        assert forbidden not in manifest_text, f"Found forbidden copy in generated manifest: {forbidden}"


def test_case_detail_pages_no_longer_use_old_case_shell_sections() -> None:
    for path in Path("docs/analytics/cases").glob("*.md"):
        if path.name == "index.md":
            continue
        text = _read(path)
        assert "## Key Data Sources" not in text, f"Old Key Data Sources label still present in {path}"
        assert "## Recommended Query Sequence" not in text, f"Old Recommended Query Sequence label still present in {path}"
        assert "## Main Tables" not in text, f"Old Main Tables label still present in {path}"
        assert "## Main Tables and Worksheets" not in text, f"Old Main Tables and Worksheets label still present in {path}"
        assert "## Query Sequence" not in text, f"Old Query Sequence label still present in {path}"


def test_upgraded_case_walkthroughs_use_before_you_start_instead_of_old_case_sections() -> None:
    for path in CASE_DOCS_WITH_BEFORE_YOU_START:
        text = _read(path)
        assert "## Before You Start" in text, f"Missing Before You Start in {path}"
        assert "## Next Steps" in text, f"Missing Next Steps in {path}"
        assert "## Key Data Sources" not in text, f"Old Key Data Sources label still present in {path}"
        assert "## Recommended Query Sequence" not in text, f"Old Recommended Query Sequence label still present in {path}"
