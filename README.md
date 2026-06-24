# Vibe-OCR-Extractor

A simple web GUI to upload a **PDF or image**, run it through your **local
GLM-OCR** model, view the extracted text, and download it as a `.txt` file.

![flow](https://img.shields.io/badge/upload-%E2%86%92%20OCR%20%E2%86%92%20view%20%E2%86%92%20download-6c8cff)

## Features

- 📤 Drag-and-drop (or browse) upload for PDFs and common image formats
- 🧠 OCR via your **local GLM-OCR** server (OpenAI-compatible vision API)
- 📄 Multi-page PDFs are rasterized and OCR'd page by page
- 👀 View / edit the extracted text in the browser
- 💾 One-click download to a `.txt` file (any edits you make are included)
- 📋 Copy to clipboard

## How it works

```
Browser  ──upload──▶  Flask (app.py)
                         │
                         ├─ PDF → images (PyMuPDF)   image → normalized (Pillow)
                         │
                         └──▶  Local GLM-OCR server (/v1/chat/completions, vision)
                                        │
                         ◀──────────  extracted text  ──────────┘
```

The app talks to any OpenAI-compatible endpoint that supports image input, so it
works with GLM-OCR served via **vLLM**, **SGLang**, **Ollama**, or similar.

## Requirements

- Python 3.10+
- A running local GLM-OCR server exposing an OpenAI-compatible
  `/v1/chat/completions` endpoint with vision support.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Point the app at your local GLM-OCR server (defaults shown)
export GLM_OCR_BASE_URL="http://localhost:8000/v1"
export GLM_OCR_MODEL="glm-ocr"
export GLM_OCR_API_KEY="EMPTY"        # most local servers ignore this

# 3. Run the web app
python app.py

# 4. Open the GUI
#    http://127.0.0.1:5000
```

## Configuration

All settings are environment variables (see `config.py`):

| Variable             | Default                       | Description                                          |
| -------------------- | ----------------------------- | ---------------------------------------------------- |
| `GLM_OCR_BASE_URL`   | `http://localhost:8000/v1`    | Base URL of your GLM-OCR OpenAI-compatible API       |
| `GLM_OCR_MODEL`      | `glm-ocr`                     | Model name as registered on your server              |
| `GLM_OCR_API_KEY`    | `EMPTY`                       | API key (most local servers ignore it)               |
| `GLM_OCR_PROMPT`     | *(OCR instruction)*           | Instruction sent with each image                     |
| `GLM_OCR_TIMEOUT`    | `180`                         | Per-image request timeout in seconds                 |
| `PDF_RENDER_DPI`     | `200`                         | DPI used to rasterize PDF pages                      |
| `MAX_CONTENT_LENGTH` | `52428800` (50 MB)            | Max upload size in bytes                             |
| `HOST` / `PORT`      | `127.0.0.1` / `5000`          | Where the web server listens                         |
| `FLASK_DEBUG`        | `0`                           | Set to `1` for Flask debug mode                      |

## Example: serving GLM-OCR with vLLM

```bash
vllm serve zai-org/GLM-OCR \
  --served-model-name glm-ocr \
  --port 8000
```

Then run this app with the defaults above.

## Supported file types

`pdf`, `png`, `jpg`, `jpeg`, `webp`, `bmp`, `tif`, `tiff`, `gif`

## Project layout

```
app.py            Flask routes (/, /api/extract, /api/download, /api/config)
ocr.py            PDF/image → GLM-OCR → text
config.py         Environment-driven configuration
templates/        index.html (the GUI)
static/           style.css, app.js
requirements.txt  Python dependencies
```

## Notes

- The GLM-OCR server is **not** bundled — this app is the front end. Start your
  model server separately and point `GLM_OCR_BASE_URL` at it.
- Uploaded files are processed in memory and never written to disk.
