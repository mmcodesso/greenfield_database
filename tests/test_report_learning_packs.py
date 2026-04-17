from __future__ import annotations

from pathlib import Path

import yaml

from generator_dataset.reports import load_report_catalog


EXPECTED_PACK_SLUGS = [
    "executive-overview",
    "commercial-and-working-capital",
    "operations-and-risk",
]

EXPECTED_PACK_PAGES = [
    Path("docs/analytics/reports/lens-packs.md"),
    Path("docs/analytics/reports/executive-overview.md"),
    Path("docs/analytics/reports/commercial-and-working-capital.md"),
    Path("docs/analytics/reports/operations-and-risk.md"),
]


def _load_pack_catalog() -> list[dict[str, object]]:
    with Path("config/report_pack_catalog.yaml").open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    packs = raw.get("packs", [])
    assert isinstance(packs, list)
    return packs


def _resolve_doc_link(href: str) -> Path | None:
    if not href.startswith("/"):
        return None

    normalized = href.lstrip("/")
    if normalized.startswith("docs/"):
        normalized = normalized[len("docs/") :]
    return Path("docs") / f"{normalized}.md"


def test_report_pack_catalog_references_valid_reports_and_docs() -> None:
    packs = _load_pack_catalog()
    report_slugs = {report.slug for report in load_report_catalog()}

    assert [pack["slug"] for pack in packs] == EXPECTED_PACK_SLUGS

    for pack in packs:
        assert pack["title"]
        assert pack["summary"]
        assert pack["opening_paragraphs"]
        assert len(pack["opening_paragraphs"]) >= 2
        assert pack["approach_guidance"]
        assert len(pack["approach_guidance"]) >= 3
        assert pack["core_questions"]
        assert pack["where_to_go_next"]
        assert pack["reports"]

        report_sequence = [entry["report_slug"] for entry in pack["reports"]]
        assert len(report_sequence) == len(set(report_sequence))

        for link in pack["where_to_go_next"]:
            assert link["label"]
            assert link["href"]
            resolved = _resolve_doc_link(str(link["href"]))
            if resolved is not None:
                assert resolved.exists(), f"Missing linked doc: {resolved}"

        for entry in pack["reports"]:
            assert entry["report_slug"] in report_slugs
            assert entry["teaching_role"] in {"anchor", "drill-down"}
            assert entry["why_it_matters"]
            assert entry["discussion_questions"]
            assert entry["suggested_analysis"]

            related_link = entry.get("related_link")
            if related_link:
                assert related_link["label"]
                assert related_link["href"]
                resolved = _resolve_doc_link(str(related_link["href"]))
                if resolved is not None:
                    assert resolved.exists(), f"Missing related doc: {resolved}"


def test_report_learning_pages_and_sidebar_are_wired() -> None:
    sidebar_text = Path("sidebars.js").read_text(encoding="utf-8")
    reports_hub = Path("docs/analytics/reports/index.md").read_text(encoding="utf-8")
    perspectives_hub = Path("docs/analytics/reports/lens-packs.md").read_text(encoding="utf-8")

    for path in EXPECTED_PACK_PAGES:
        assert path.exists(), f"Missing learning pack page: {path}"

    assert 'label: "Business Perspectives"' in sidebar_text
    assert 'label: "Report Library"' in sidebar_text
    assert '"analytics/reports/lens-packs"' in sidebar_text
    assert '"analytics/reports/executive-overview"' in sidebar_text
    assert '"analytics/reports/commercial-and-working-capital"' in sidebar_text
    assert '"analytics/reports/operations-and-risk"' in sidebar_text
    assert "Business Perspectives" in reports_hub
    assert "Report Library" in reports_hub
    assert "Business Perspectives Hub" in perspectives_hub


def test_report_pack_manifest_and_component_render_expected_sections() -> None:
    manifest_text = Path("src/generated/reportPackManifest.js").read_text(encoding="utf-8")
    component_text = Path("src/components/ReportLearningPack/index.jsx").read_text(encoding="utf-8")

    for pack_slug in EXPECTED_PACK_SLUGS:
        assert pack_slug in manifest_text

    assert "How to Approach This Perspective" in component_text
    assert "Core Questions" in component_text
    assert "Recommended Report Sequence" in component_text
    assert "Report Blocks" in component_text
    assert "Where to Go Next" in component_text
    assert "Audience and Purpose" not in component_text
    assert "Business Lens" not in component_text
    assert "Why This Report Belongs in the Perspective" in component_text
    assert "Why This Report Belongs in the Lens" not in component_text

    for path in EXPECTED_PACK_PAGES[1:]:
        page_text = path.read_text(encoding="utf-8")
        assert 'import { ReportLearningPack } from "@site/src/components/ReportLearningPack";' in page_text
        assert 'import reportPackManifest from "@site/src/generated/reportPackManifest";' in page_text
        assert "<ReportLearningPack" in page_text
        assert "Use this pack when" not in page_text
