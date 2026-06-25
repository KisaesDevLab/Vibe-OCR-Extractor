"""Tests for pdf.js text-layer detection/extraction and routing.

Tests that need the Node extractor are skipped when it is not installed.
"""

import os

import fitz  # PyMuPDF
import pytest

import extract as extractor
import ocr
import settings
import textlayer

NODE_AVAILABLE = textlayer.is_available()
needs_node = pytest.mark.skipif(
    not NODE_AVAILABLE, reason="pdf.js text-layer extractor not installed"
)


def _text_pdf(lines):
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=12)
        y += 24
    data = doc.tobytes()
    doc.close()
    return data


def _blank_pdf(pages=1):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture(autouse=True)
def _isolate_settings(tmp_path, monkeypatch):
    import config

    monkeypatch.setattr(config, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    settings.reset()
    yield
    settings.load()


@needs_node
def test_detects_text_layer():
    data = _text_pdf(
        [
            "Acme Bank Statement — Account 1234",
            "Date        Description              Amount",
            "01/02/2026  Coffee Shop               -4.50",
            "01/03/2026  Paycheck Deposit       2,000.00",
            "01/04/2026  Grocery Store            -82.13",
        ]
    )
    analysis = textlayer.analyze_pdf_bytes(data)
    assert analysis.page_count == 1
    assert analysis.has_text_layer is True
    assert analysis.route == "text"
    assert "Acme Bank Statement" in analysis.page_texts[0]


@needs_node
def test_blank_pdf_routes_to_ocr():
    analysis = textlayer.analyze_pdf_bytes(_blank_pdf(1))
    assert analysis.has_text_layer is False
    assert analysis.suspected_scan is True
    assert analysis.route == "ocr"


@needs_node
def test_extract_auto_uses_text_layer_without_ocr(monkeypatch):
    # If OCR were called, this would raise — proving the text path skips it.
    def boom(image):
        raise AssertionError("OCR should not run for a text-layer PDF")

    monkeypatch.setattr(ocr, "_ocr_image", boom)
    settings.update({"extraction_mode": "auto"})

    # Enough text per page (>100 chars avg) to satisfy the converter's
    # has-text-layer threshold and route to "text".
    data = _text_pdf(
        ["This is a sufficiently long line of statement text, row %d." % i for i in range(6)]
    )
    result = extractor.extract(data, "pdf")
    assert result.method == "text"
    assert "sufficiently long line" in result.text
    assert all(p.method == "text" for p in result.pages)


@needs_node
def test_text_mode_on_scan_returns_empty_text(monkeypatch):
    # In "text" mode we never OCR, even for a scan-like (blank) PDF.
    monkeypatch.setattr(
        ocr, "_ocr_image", lambda image: (_ for _ in ()).throw(AssertionError())
    )
    settings.update({"extraction_mode": "text"})
    result = extractor.extract(_blank_pdf(1), "pdf")
    assert result.method == "text"
    assert result.text == ""


def test_text_mode_unavailable_raises(monkeypatch):
    # Simulate the extractor being absent regardless of the real environment.
    monkeypatch.setattr(textlayer, "is_available", lambda: False)
    settings.update({"extraction_mode": "text"})
    with pytest.raises(textlayer.TextLayerUnavailable):
        extractor.extract(_blank_pdf(1), "pdf")


def test_auto_falls_back_to_ocr_when_unavailable(monkeypatch):
    monkeypatch.setattr(textlayer, "is_available", lambda: False)
    monkeypatch.setattr(ocr, "_ocr_image", lambda image: "OCR-FALLBACK")
    settings.update({"extraction_mode": "auto"})
    result = extractor.extract(_blank_pdf(1), "pdf")
    assert result.method == "ocr"
    assert "OCR-FALLBACK" in result.text
    assert result.notes  # a fallback note was recorded


def test_unavailable_via_missing_node_binary(monkeypatch, tmp_path):
    # is_available() true, but the node binary path is bogus -> Unavailable.
    if not NODE_AVAILABLE:
        pytest.skip("extractor dir not present")
    monkeypatch.setattr(textlayer, "NODE_BIN", "definitely-not-node-xyz")
    with pytest.raises(textlayer.TextLayerUnavailable):
        textlayer.analyze_pdf_bytes(_blank_pdf(1))


def test_extractor_path_constants():
    assert os.path.basename(textlayer.EXTRACTOR) == "extract.mjs"
