"""Configuration for the Vibe OCR Extractor.

All settings can be overridden with environment variables so the app can talk
to whatever local GLM-OCR server you are running (vLLM, SGLang, Ollama, etc.),
as long as it exposes an OpenAI-compatible /chat/completions endpoint with
vision support.
"""

import os


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


# Base URL of your local GLM-OCR server's OpenAI-compatible API.
# Should include the version path, e.g. "http://localhost:8000/v1".
GLM_OCR_BASE_URL = _env("GLM_OCR_BASE_URL", "http://localhost:8000/v1")

# API key. Most local servers ignore this, but the OpenAI schema requires one.
GLM_OCR_API_KEY = _env("GLM_OCR_API_KEY", "EMPTY")

# Model name as registered on your local server.
GLM_OCR_MODEL = _env("GLM_OCR_MODEL", "glm-ocr")

# Instruction sent alongside each image.
GLM_OCR_PROMPT = _env(
    "GLM_OCR_PROMPT",
    "You are an OCR engine. Extract all text from this image exactly as it "
    "appears, preserving the reading order, line breaks, and layout as closely "
    "as possible. Return only the extracted text with no commentary.",
)

# Request timeout (seconds) for a single image.
GLM_OCR_TIMEOUT = int(_env("GLM_OCR_TIMEOUT", "180"))

# DPI used when rasterizing PDF pages to images before OCR.
PDF_RENDER_DPI = int(_env("PDF_RENDER_DPI", "200"))

# Max upload size in bytes (default 50 MB).
MAX_CONTENT_LENGTH = int(_env("MAX_CONTENT_LENGTH", str(50 * 1024 * 1024)))

# Allowed upload extensions.
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff", "gif"}
