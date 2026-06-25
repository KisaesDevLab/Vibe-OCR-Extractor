"""Static configuration and default settings for the Vibe OCR Extractor.

Values here come from environment variables and act as the *defaults*. The
user-editable runtime settings (GLM-OCR address, model, DPI, timeout, etc.) are
managed by ``settings.py`` and can be changed live from the web UI.
"""

import os


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


# --- Runtime-editable defaults (overridable from the UI / settings file) -----
DEFAULT_SETTINGS = {
    # Base URL of your local GLM-OCR OpenAI-compatible API (include /v1).
    "base_url": _env("GLM_OCR_BASE_URL", "http://localhost:8080/v1"),
    # API key. Most local servers ignore this, but the schema requires one.
    "api_key": _env("GLM_OCR_API_KEY", "EMPTY"),
    # Model name as registered on your server.
    "model": _env("GLM_OCR_MODEL", "glm-ocr"),
    # Instruction sent alongside each image.
    "prompt": _env(
        "GLM_OCR_PROMPT",
        "You are an OCR engine. Extract all text from this image exactly as it "
        "appears, preserving the reading order, line breaks, and layout as "
        "closely as possible. Return only the extracted text with no commentary.",
    ),
    # Per-image request timeout (seconds).
    "timeout": int(_env("GLM_OCR_TIMEOUT", "180")),
    # DPI used when rasterizing PDF pages to images before OCR.
    "pdf_dpi": int(_env("PDF_RENDER_DPI", "200")),
    # How to extract text from PDFs:
    #   "auto"  - detect a text layer (pdf.js) and follow the converter's
    #             routing: text layer -> text, scan -> OCR, mixed -> hybrid
    #   "text"  - always use the pdf.js text layer (what the converter ingests)
    #   "ocr"   - always rasterize and OCR (ignore any text layer)
    "extraction_mode": _env("EXTRACTION_MODE", "auto"),
}

# Allowed values for the extraction_mode setting.
EXTRACTION_MODES = ("auto", "text", "ocr")

# Keys the UI is allowed to edit.
EDITABLE_KEYS = tuple(DEFAULT_SETTINGS.keys())

# Where runtime settings are persisted. Mount a volume here in Docker to keep
# changes across restarts (e.g. SETTINGS_FILE=/data/settings.json).
SETTINGS_FILE = _env("SETTINGS_FILE", "settings.json")


# --- Static configuration (env-only, applied at startup) ---------------------

# Max upload size in bytes (default 50 MB).
MAX_CONTENT_LENGTH = int(_env("MAX_CONTENT_LENGTH", str(50 * 1024 * 1024)))

# Allowed upload extensions.
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff", "gif"}
