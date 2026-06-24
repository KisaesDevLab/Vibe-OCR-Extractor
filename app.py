"""Vibe OCR Extractor — a tiny Flask web GUI around a local GLM-OCR server.

Upload a PDF or image, the file is OCR'd with your local GLM-OCR model, and the
extracted text is returned for viewing and download.
"""

import io
import os

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
)
from werkzeug.utils import secure_filename

import config
import settings
from ocr import OCRError, extract_text, test_connection

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH


def _allowed(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS
    )


@app.route("/")
def index():
    return render_template("index.html")


def _config_payload():
    return {
        "settings": settings.get(),
        "defaults": dict(config.DEFAULT_SETTINGS),
        "editable_keys": list(config.EDITABLE_KEYS),
        "allowed_extensions": sorted(config.ALLOWED_EXTENSIONS),
        "max_content_length": config.MAX_CONTENT_LENGTH,
    }


@app.route("/api/config", methods=["GET"])
def api_config():
    """Return the current runtime settings plus defaults and static config."""
    return jsonify(_config_payload())


@app.route("/api/config", methods=["POST"])
def api_config_update():
    """Update runtime settings from the UI."""
    payload = request.get_json(silent=True) or {}
    try:
        if payload.get("reset") is True:
            settings.reset()
        else:
            settings.update(payload)
    except settings.SettingsError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_config_payload())


@app.route("/api/test-connection", methods=["POST"])
def api_test_connection():
    """Apply any provided settings, then ping the GLM-OCR server."""
    payload = request.get_json(silent=True) or {}
    try:
        if payload:
            settings.update(payload)
        result = test_connection()
    except settings.SettingsError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except OCRError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502
    return jsonify(result)


@app.route("/api/extract", methods=["POST"])
def api_extract():
    if "file" not in request.files:
        return jsonify({"error": "No file was uploaded."}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file was selected."}), 400

    filename = secure_filename(file.filename)
    if not _allowed(filename):
        return (
            jsonify(
                {
                    "error": "Unsupported file type. Allowed: "
                    + ", ".join(sorted(config.ALLOWED_EXTENSIONS))
                }
            ),
            400,
        )

    extension = filename.rsplit(".", 1)[1].lower()
    data = file.read()
    if not data:
        return jsonify({"error": "The uploaded file is empty."}), 400

    try:
        result = extract_text(data, extension)
    except OCRError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:  # noqa: BLE001 - never leak a stack trace to the UI
        return jsonify({"error": f"Unexpected error: {exc}"}), 500

    base_name = os.path.splitext(filename)[0] or "extracted"
    return jsonify(
        {
            "text": result.text,
            "pages": result.pages,
            "page_count": len(result.pages),
            "filename": f"{base_name}.txt",
            "source_filename": filename,
        }
    )


@app.route("/api/download", methods=["POST"])
def api_download():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    filename = secure_filename(payload.get("filename", "extracted.txt")) or "extracted.txt"
    if not filename.endswith(".txt"):
        filename += ".txt"

    buffer = io.BytesIO(text.encode("utf-8"))
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="text/plain; charset=utf-8",
        as_attachment=True,
        download_name=filename,
    )


@app.errorhandler(413)
def too_large(_error):
    limit_mb = config.MAX_CONTENT_LENGTH / (1024 * 1024)
    return jsonify({"error": f"File is too large. Maximum size is {limit_mb:.0f} MB."}), 413


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
