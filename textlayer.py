"""Detect and extract a PDF's text layer using pdf.js.

This shells out to ``pdf_text/extract.mjs`` (Node + pdfjs-dist), which mirrors
the Vibe-Transaction-Convertor preprocessing exactly, so the text returned here
is what the converter actually receives from a PDF's text layer.

If Node or the pdf.js dependency is unavailable, ``analyze_pdf_bytes`` raises
``TextLayerUnavailable`` and callers can fall back to OCR.
"""

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACTOR = os.path.join(HERE, "pdf_text", "extract.mjs")
NODE_MODULES = os.path.join(HERE, "pdf_text", "node_modules")
NODE_BIN = os.environ.get("NODE_BIN", "node")
TEXT_LAYER_TIMEOUT = int(os.environ.get("TEXT_LAYER_TIMEOUT", "120"))


class TextLayerError(Exception):
    """Raised when text-layer extraction fails."""


class TextLayerUnavailable(TextLayerError):
    """Raised when the pdf.js extractor (Node / deps) is not installed."""


@dataclass
class TextLayerAnalysis:
    page_count: int
    has_text_layer: bool
    text_layer_coverage: float
    avg_chars_per_page: float
    suspected_scan: bool
    route: str  # "text" | "ocr" | "hybrid"
    pages: list  # [{"index", "hasText", "charCount"}]
    page_texts: list  # extracted text per page (parallel to pages)

    def summary(self) -> dict:
        """JSON-friendly analysis without the full per-page text."""
        return {
            "page_count": self.page_count,
            "has_text_layer": self.has_text_layer,
            "text_layer_coverage": self.text_layer_coverage,
            "avg_chars_per_page": self.avg_chars_per_page,
            "suspected_scan": self.suspected_scan,
            "route": self.route,
            "pages": self.pages,
        }


def is_available() -> bool:
    """True if the pdf.js extractor and its dependencies are installed."""
    return os.path.isdir(NODE_MODULES) and os.path.isfile(EXTRACTOR)


def _run_extractor(path: str) -> dict:
    if not is_available():
        raise TextLayerUnavailable(
            "The pdf.js text-layer extractor is not installed. Run "
            "'npm install' in the pdf_text/ directory (or use the Docker image)."
        )
    try:
        proc = subprocess.run(
            [NODE_BIN, EXTRACTOR, path],
            capture_output=True,
            timeout=TEXT_LAYER_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise TextLayerUnavailable(
            f"Node.js ('{NODE_BIN}') is required for text-layer extraction but "
            "was not found. Set NODE_BIN or use the Docker image."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise TextLayerError("Text-layer extraction timed out.") from exc

    if proc.returncode != 0:
        message = proc.stderr.decode("utf-8", "replace").strip()
        raise TextLayerError(message[:500] or "pdf.js extractor failed.")

    try:
        return json.loads(proc.stdout.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise TextLayerError("Could not parse extractor output.") from exc


def analyze_pdf_bytes(data: bytes) -> TextLayerAnalysis:
    """Analyze raw PDF bytes and return text-layer analysis + extracted text."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
        handle.write(data)
        temp_path = handle.name
    try:
        raw = _run_extractor(temp_path)
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    return TextLayerAnalysis(
        page_count=raw.get("pageCount", 0),
        has_text_layer=raw.get("hasTextLayer", False),
        text_layer_coverage=raw.get("textLayerCoverage", 0.0),
        avg_chars_per_page=raw.get("avgCharsPerPage", 0.0),
        suspected_scan=raw.get("suspectedScan", False),
        route=raw.get("route", "ocr"),
        pages=raw.get("pages", []),
        page_texts=raw.get("pageTexts", []),
    )
