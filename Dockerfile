# Vibe OCR Extractor — container image
#
# Stage 1: install the pdf.js text-layer extractor's node_modules.
FROM node:20-bookworm-slim AS pdfdeps
WORKDIR /pdf
COPY pdf_text/package.json pdf_text/package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund

# Stage 2: the Python app, plus a Node runtime for the text-layer extractor.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5000 \
    SETTINGS_FILE=/data/settings.json

# Node.js runtime (Debian bookworm ships Node 18+, which runs pdfjs-dist 4.x).
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies first to leverage layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bring in the prebuilt pdf.js dependencies.
COPY --from=pdfdeps /pdf/node_modules ./pdf_text/node_modules

# Copy the application.
COPY . .

# Persisted settings live here; mount a volume to keep them across restarts.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 5000

# Single worker keeps in-memory settings consistent; threads handle concurrency.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", \
     "--timeout", "1800", "app:app"]
