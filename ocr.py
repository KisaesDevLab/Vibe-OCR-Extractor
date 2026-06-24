"""OCR processing: turn an uploaded PDF/image into extracted text.

PDFs are rasterized page-by-page with PyMuPDF; images are normalized with
Pillow. Each resulting page image is sent to a local GLM-OCR server through its
OpenAI-compatible vision chat endpoint.
"""

import base64
import io
from dataclasses import dataclass, field

import fitz  # PyMuPDF
import requests
from PIL import Image

import config


class OCRError(Exception):
    """Raised when the OCR backend cannot be reached or returns an error."""


@dataclass
class OCRResult:
    text: str
    pages: list[str] = field(default_factory=list)


def _image_to_data_url(image: Image.Image) -> str:
    """Encode a Pillow image as a base64 PNG data URL."""
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _pdf_to_images(data: bytes) -> list[Image.Image]:
    images: list[Image.Image] = []
    zoom = config.PDF_RENDER_DPI / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    with fitz.open(stream=data, filetype="pdf") as doc:
        if doc.page_count == 0:
            raise OCRError("The PDF has no pages.")
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            images.append(Image.open(io.BytesIO(pix.tobytes("png"))))
    return images


def _bytes_to_images(data: bytes, extension: str) -> list[Image.Image]:
    if extension == "pdf":
        return _pdf_to_images(data)
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception as exc:  # noqa: BLE001 - surface a friendly message
        raise OCRError(f"Could not read the image file: {exc}") from exc
    return [image]


def _ocr_image(image: Image.Image) -> str:
    """Send a single image to the local GLM-OCR server and return its text."""
    payload = {
        "model": config.GLM_OCR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": config.GLM_OCR_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": _image_to_data_url(image)},
                    },
                ],
            }
        ],
        "temperature": 0,
    }
    url = config.GLM_OCR_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.GLM_OCR_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            url, json=payload, headers=headers, timeout=config.GLM_OCR_TIMEOUT
        )
    except requests.exceptions.ConnectionError as exc:
        raise OCRError(
            f"Could not connect to the GLM-OCR server at {config.GLM_OCR_BASE_URL}. "
            "Is it running? You can change the address with the GLM_OCR_BASE_URL "
            "environment variable."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise OCRError("The GLM-OCR server took too long to respond.") from exc

    if response.status_code != 200:
        raise OCRError(
            f"GLM-OCR server returned HTTP {response.status_code}: {response.text[:500]}"
        )

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise OCRError(f"Unexpected response from GLM-OCR server: {exc}") from exc


def extract_text(data: bytes, extension: str) -> OCRResult:
    """Extract text from raw file bytes of the given extension."""
    extension = extension.lower().lstrip(".")
    images = _bytes_to_images(data, extension)

    pages: list[str] = []
    for image in images:
        pages.append(_ocr_image(image))

    if len(pages) > 1:
        combined = "\n\n".join(
            f"--- Page {i} ---\n{text}" for i, text in enumerate(pages, start=1)
        )
    else:
        combined = pages[0] if pages else ""

    return OCRResult(text=combined, pages=pages)
