# Vibe-OCR-Extractor

A simple web GUI to upload a **PDF or image**, run it through your **local
GLM-OCR** model (served with **llama.cpp**), view the extracted text, and
download it as a `.txt` file.

![flow](https://img.shields.io/badge/upload-%E2%86%92%20OCR%20%E2%86%92%20view%20%E2%86%92%20download-6c8cff)

## Features

- 📤 Drag-and-drop (or browse) upload for PDFs and common image formats
- 🧠 OCR via your **local GLM-OCR** server (OpenAI-compatible vision API)
- ⚙️ **In-app Settings panel** — set the server IP/URL, model, API key, PDF
  DPI, timeout, and OCR prompt right from the browser (with a *Test connection*
  button). Changes are saved and persist across restarts.
- 📄 Multi-page PDFs are rasterized and OCR'd page by page
- 👀 View / edit the extracted text in the browser
- 💾 One-click download to a `.txt` file (any edits you make are included)
- 📋 Copy to clipboard
- 🐳 Runs as a Docker image, published to **GHCR**

## How it works

```
Browser  ──upload──▶  Flask (app.py)
                         │
                         ├─ PDF → images (PyMuPDF)   image → normalized (Pillow)
                         │
                         └──▶  llama.cpp server (/v1/chat/completions, vision)
                                        │
                         ◀──────────  extracted text  ──────────┘
```

This app is the front end — point it at any OpenAI-compatible endpoint with
vision support. It is built and tested against **llama.cpp** (`llama-server`),
which serves GLM-OCR on port `8080` by default.

## Settings (configurable from the UI)

Click the **⚙️ gear** in the top-right to open Settings. You can change:

| Setting           | Description                                              |
| ----------------- | -------------------------------------------------------- |
| **GLM-OCR Base URL** | Your llama.cpp endpoint, e.g. `http://localhost:8080/v1` |
| **Model name**    | Model id as registered on the server (`glm-ocr`)         |
| **API key**       | Usually ignored by llama.cpp; leave as `EMPTY`           |
| **PDF render DPI**| Rasterization quality for PDFs (50–600)                  |
| **Timeout**       | Per-page request timeout in seconds (5–1800)             |
| **OCR prompt**    | The instruction sent with each image                     |

Use **🔌 Test connection** to confirm the server is reachable, or **Reset to
defaults** to revert. Settings are stored in a JSON file (`SETTINGS_FILE`) so
they survive restarts.

## Quick start (local Python)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) set defaults — or just configure them later in the UI
export GLM_OCR_BASE_URL="http://localhost:8080/v1"   # llama.cpp default port
export GLM_OCR_MODEL="glm-ocr"

# 3. Run the web app
python app.py

# 4. Open the GUI
#    http://127.0.0.1:5000
```

## Run with Docker

### Use the published GHCR image

```bash
docker run --rm -p 5000:5000 \
  --add-host=host.docker.internal:host-gateway \
  -e GLM_OCR_BASE_URL="http://host.docker.internal:8080/v1" \
  -e GLM_OCR_MODEL="glm-ocr" \
  -v ocr-settings:/data \
  ghcr.io/kisaesdevlab/vibe-ocr-extractor:latest
```

Then open <http://localhost:5000>.

> **Reaching llama.cpp on the host:** from inside the container, `localhost`
> is the container itself. Use `host.docker.internal` (enabled by the
> `--add-host` flag above) to reach a `llama-server` running on your host
> machine — e.g. `http://host.docker.internal:8080/v1`.

### Or with Docker Compose

```bash
docker compose up -d
```

`docker-compose.yml` wires up the port, the `host.docker.internal` mapping, and
a named volume for persisted settings. Edit the environment block to match your
setup (or set everything from the Settings UI afterwards).

### Build the image yourself

```bash
docker build -t vibe-ocr-extractor .
docker run --rm -p 5000:5000 vibe-ocr-extractor
```

## Container image (GHCR)

Every push to `main` (and every `v*` tag) builds and publishes a multi-tagged
image to the GitHub Container Registry via
[`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml):

```
ghcr.io/kisaesdevlab/vibe-ocr-extractor:latest
ghcr.io/kisaesdevlab/vibe-ocr-extractor:main
ghcr.io/kisaesdevlab/vibe-ocr-extractor:<git-sha>
ghcr.io/kisaesdevlab/vibe-ocr-extractor:<version>   # on v* tags
```

The workflow authenticates with the built-in `GITHUB_TOKEN` (no extra secrets
needed). After the first successful publish, set the package visibility to
*public* in the repo's **Packages** settings if you want to pull it without
authentication.

## Environment variables

These set the **defaults** (the UI can override most of them at runtime):

| Variable             | Default                       | Description                                          |
| -------------------- | ----------------------------- | ---------------------------------------------------- |
| `GLM_OCR_BASE_URL`   | `http://localhost:8080/v1`    | Base URL of the llama.cpp OpenAI-compatible API      |
| `GLM_OCR_MODEL`      | `glm-ocr`                     | Model name as registered on your server              |
| `GLM_OCR_API_KEY`    | `EMPTY`                       | API key (llama.cpp ignores it)                       |
| `GLM_OCR_PROMPT`     | *(OCR instruction)*           | Instruction sent with each image                     |
| `GLM_OCR_TIMEOUT`    | `180`                         | Per-image request timeout in seconds                 |
| `PDF_RENDER_DPI`     | `200`                         | DPI used to rasterize PDF pages                      |
| `SETTINGS_FILE`      | `settings.json` (`/data/...` in Docker) | Where UI settings are persisted          |
| `MAX_CONTENT_LENGTH` | `52428800` (50 MB)            | Max upload size in bytes                             |
| `HOST` / `PORT`      | `127.0.0.1` / `5000`          | Where the dev server listens (Docker uses `0.0.0.0`) |
| `FLASK_DEBUG`        | `0`                           | Set to `1` for Flask debug mode                      |

## Example: serving GLM-OCR with llama.cpp

```bash
# Vision models need both the model and its multimodal projector (mmproj).
llama-server \
  -m GLM-OCR.gguf \
  --mmproj GLM-OCR-mmproj.gguf \
  --host 0.0.0.0 --port 8080 \
  --alias glm-ocr
```

Then run this app and (if needed) set the Base URL to `http://localhost:8080/v1`
in Settings.

## Supported file types

`pdf`, `png`, `jpg`, `jpeg`, `webp`, `bmp`, `tif`, `tiff`, `gif`

## Project layout

```
app.py            Flask routes (/, /api/extract, /api/download, /api/config, /api/test-connection)
ocr.py            PDF/image → GLM-OCR → text
settings.py       Runtime-editable settings, persisted to JSON
config.py         Defaults and static configuration
templates/        index.html (the GUI + settings dialog)
static/           style.css, app.js
Dockerfile        Container image (gunicorn)
docker-compose.yml
.github/workflows/docker-publish.yml   Build & publish to GHCR
requirements.txt  Python dependencies
```

## Notes

- The GLM-OCR server is **not** bundled — start `llama-server` separately and
  point the app at it.
- Uploaded files are processed in memory and never written to disk.
