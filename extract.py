"""Top-level extraction: choose between PDF text layer and OCR.

Mirrors the Vibe-Transaction-Convertor routing so the output matches what the
converter receives:

* ``text``   - use the pdf.js text layer for every page
* ``ocr``    - rasterize and OCR every page
* ``hybrid`` - text layer for pages that have text, OCR for the rest

The ``extraction_mode`` setting controls this:

* ``auto`` - detect a text layer and follow the routing above
* ``text`` - always use the text layer (error if unavailable)
* ``ocr``  - always OCR (ignore any text layer)
"""

from dataclasses import dataclass, field

import ocr
import settings
import textlayer


@dataclass
class PageResult:
    index: int
    method: str  # "text" | "ocr"
    text: str


@dataclass
class ExtractionResult:
    text: str
    method: str  # "text" | "ocr" | "hybrid" | "image"
    pages: list  # list[PageResult]
    analysis: dict | None = None
    notes: list = field(default_factory=list)

    def pages_summary(self) -> list:
        return [
            {"index": p.index, "method": p.method, "chars": len(p.text)}
            for p in self.pages
        ]


def _combine(page_results) -> str:
    texts = [p.text for p in page_results]
    if len(texts) <= 1:
        return texts[0] if texts else ""
    return "\n\n".join(texts)


def _page_text(analysis: textlayer.TextLayerAnalysis, idx: int) -> str:
    if 0 <= idx < len(analysis.page_texts):
        return analysis.page_texts[idx]
    return ""


def _ocr_pdf(data: bytes, notes: list, analysis=None) -> ExtractionResult:
    images = ocr._pdf_to_images(data)
    pages = [
        PageResult(i + 1, "ocr", ocr._ocr_image(img)) for i, img in enumerate(images)
    ]
    summary = analysis.summary() if analysis else None
    return ExtractionResult(_combine(pages), "ocr", pages, summary, notes)


def extract_pdf_bytes(data: bytes, mode: str) -> ExtractionResult:
    notes: list = []
    analysis = None

    if mode in ("auto", "text"):
        try:
            analysis = textlayer.analyze_pdf_bytes(data)
        except textlayer.TextLayerUnavailable:
            if mode == "text":
                raise
            notes.append("Text-layer extractor unavailable; fell back to OCR.")
        except textlayer.TextLayerError as exc:
            if mode == "text":
                raise
            notes.append(f"Text-layer detection failed ({exc}); fell back to OCR.")

    if analysis is None:
        return _ocr_pdf(data, notes)

    chosen = "text" if mode == "text" else analysis.route

    if chosen == "ocr":
        return _ocr_pdf(data, notes, analysis=analysis)

    if chosen == "text":
        pages = [
            PageResult(p["index"], "text", _page_text(analysis, idx))
            for idx, p in enumerate(analysis.pages)
        ]
        return ExtractionResult(_combine(pages), "text", pages, analysis.summary(), notes)

    # hybrid: text layer where present, OCR the scanned pages
    images = ocr._pdf_to_images(data)
    pages = []
    for idx, page in enumerate(analysis.pages):
        if page.get("hasText"):
            pages.append(PageResult(page["index"], "text", _page_text(analysis, idx)))
        else:
            img = images[idx] if idx < len(images) else None
            text = ocr._ocr_image(img) if img is not None else ""
            pages.append(PageResult(page["index"], "ocr", text))
    return ExtractionResult(_combine(pages), "hybrid", pages, analysis.summary(), notes)


def extract_image_bytes(data: bytes, extension: str) -> ExtractionResult:
    images = ocr._bytes_to_images(data, extension)
    text = ocr._ocr_image(images[0]) if images else ""
    return ExtractionResult(text, "image", [PageResult(1, "ocr", text)])


def extract(data: bytes, extension: str) -> ExtractionResult:
    extension = extension.lower().lstrip(".")
    mode = settings.get("extraction_mode")
    if extension == "pdf":
        return extract_pdf_bytes(data, mode)
    return extract_image_bytes(data, extension)
