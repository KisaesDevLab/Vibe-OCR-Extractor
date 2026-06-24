# Vibe OCR Extractor — container image
FROM python:3.11-slim

# Avoid .pyc files and buffer issues; sensible defaults for running in Docker.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5000 \
    SETTINGS_FILE=/data/settings.json

WORKDIR /app

# Install Python dependencies first to leverage layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application.
COPY . .

# Persisted settings live here; mount a volume to keep them across restarts.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 5000

# Single worker keeps in-memory settings consistent; threads handle concurrency.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", \
     "--timeout", "1800", "app:app"]
