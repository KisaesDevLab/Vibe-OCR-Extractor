"""Tests for the Flask routes."""

import io

import fitz  # PyMuPDF
import requests
from PIL import Image

import ocr


def _png_bytes(size=(20, 20), color="white"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def test_index(client):
    assert client.get("/").status_code == 200


def test_config_get(client):
    body = client.get("/api/config").get_json()
    assert "settings" in body
    assert "defaults" in body
    assert "allowed_extensions" in body
    assert "pdf" in body["allowed_extensions"]


def test_config_post_valid(client):
    resp = client.post("/api/config", json={"model": "abc", "pdf_dpi": 150})
    assert resp.status_code == 200
    assert resp.get_json()["settings"]["model"] == "abc"


def test_config_post_invalid(client):
    resp = client.post("/api/config", json={"pdf_dpi": 5000})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_config_reset(client):
    client.post("/api/config", json={"model": "temp"})
    resp = client.post("/api/config", json={"reset": True})
    assert resp.status_code == 200
    assert resp.get_json()["settings"]["model"] != "temp"


def test_extract_no_file(client):
    assert client.post("/api/extract").status_code == 400


def test_extract_bad_extension(client):
    resp = client.post(
        "/api/extract",
        data={"file": (io.BytesIO(b"x"), "a.exe")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_extract_empty_file(client):
    resp = client.post(
        "/api/extract",
        data={"file": (io.BytesIO(b""), "a.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_extract_image(client, mock_ocr):
    resp = client.post(
        "/api/extract",
        data={"file": (_png_bytes(), "scan.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["text"] == "MOCK TEXT"
    assert body["page_count"] == 1
    assert body["filename"] == "scan.txt"
    assert body["method"] == "image"


def test_extract_pdf_multipage_ocr(client, mock_ocr):
    # Force OCR so the test does not depend on the Node text-layer extractor.
    import settings

    settings.update({"extraction_mode": "ocr"})

    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    resp = client.post(
        "/api/extract",
        data={"file": (io.BytesIO(pdf_bytes), "doc.pdf")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["page_count"] == 2
    assert body["method"] == "ocr"
    assert body["text"].count("MOCK TEXT") == 2
    assert [p["method"] for p in body["pages"]] == ["ocr", "ocr"]


def test_config_exposes_text_layer_availability(client):
    body = client.get("/api/config").get_json()
    assert "text_layer_available" in body
    assert "extraction_modes" in body
    assert set(body["extraction_modes"]) == {"auto", "text", "ocr"}


def test_extract_backend_error(client, monkeypatch):
    def boom(image):
        raise ocr.OCRError("server down")

    monkeypatch.setattr(ocr, "_ocr_image", boom)
    resp = client.post(
        "/api/extract",
        data={"file": (_png_bytes(), "scan.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 502
    assert "server down" in resp.get_json()["error"]


def test_download(client):
    resp = client.post("/api/download", json={"text": "hello world", "filename": "out"})
    assert resp.status_code == 200
    assert resp.data == b"hello world"
    assert "out.txt" in resp.headers["Content-Disposition"]


def test_test_connection_error(client, monkeypatch):
    def boom(*args, **kwargs):
        raise requests.exceptions.ConnectionError()

    monkeypatch.setattr(ocr.requests, "get", boom)
    resp = client.post("/api/test-connection", json={})
    assert resp.status_code == 502
    assert resp.get_json()["ok"] is False
