from __future__ import annotations

from pathlib import Path


OVERLAY_COMPONENT = Path("src/components/ReportPreviewOverlay/index.jsx")
REPORT_CATALOG_COMPONENT = Path("src/components/ReportCatalog/index.jsx")
REPORT_LEARNING_COMPONENT = Path("src/components/ReportLearningPack/index.jsx")


def _read(path: Path) -> str:
    assert path.exists(), f"Missing file: {path}"
    return path.read_text(encoding="utf-8")


def test_overlay_component_supports_modal_preview_behavior() -> None:
    text = _read(OVERLAY_COMPONENT)

    assert 'role="dialog"' in text
    assert 'aria-modal="true"' in text
    assert 'event.key === "Escape"' in text
    assert 'document.body.style.overflow = "hidden"' in text
    assert 'event.target === event.currentTarget' in text
    assert "Loading preview..." in text
    assert "Could not load this preview." in text
    assert "await fetch(previewUrl)" in text
    assert "if (!isOpen || preview)" in text


def test_report_catalog_uses_shared_overlay_instead_of_inline_preview() -> None:
    text = _read(REPORT_CATALOG_COMPONENT)

    assert "ReportPreviewOverlay" in text
    assert 'aria-haspopup="dialog"' in text
    assert "previewUrl={previewUrl}" in text
    assert "title={entry.title}" in text
    assert "previewPanel" not in text
    assert "Loading preview..." not in text
    assert "Could not load this preview." not in text


def test_report_learning_pack_uses_shared_overlay_instead_of_inline_preview() -> None:
    text = _read(REPORT_LEARNING_COMPONENT)

    assert "ReportPreviewOverlay" in text
    assert 'aria-haspopup="dialog"' in text
    assert "previewUrl={previewUrl}" in text
    assert "title={reportEntry.title}" in text
    assert "previewPanel" not in text
    assert "Loading preview..." not in text
    assert "Could not load this preview." not in text
