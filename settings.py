"""Runtime-editable settings, persisted to a JSON file.

Settings start from the env-derived defaults in ``config.DEFAULT_SETTINGS`` and
are overlaid with whatever is saved in ``config.SETTINGS_FILE``. The web UI can
read and update them live via the ``/api/config`` endpoint.
"""

import json
import os
import threading

import config

_LOCK = threading.RLock()
_settings: dict = dict(config.DEFAULT_SETTINGS)


class SettingsError(ValueError):
    """Raised when a settings update is invalid."""


def _coerce(data: dict) -> dict:
    """Keep only editable keys and coerce numeric fields to ints."""
    out = {}
    for key in config.EDITABLE_KEYS:
        if key in data and data[key] is not None:
            out[key] = data[key]
    for num_key in ("timeout", "pdf_dpi"):
        if num_key in out:
            try:
                out[num_key] = int(out[num_key])
            except (TypeError, ValueError) as exc:
                raise SettingsError(f"'{num_key}' must be a whole number.") from exc
    if "base_url" in out and isinstance(out["base_url"], str):
        out["base_url"] = out["base_url"].strip()
    return out


def _validate(clean: dict) -> None:
    if "base_url" in clean:
        url = clean["base_url"]
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise SettingsError("Base URL must start with http:// or https://")
    if "pdf_dpi" in clean and not (50 <= clean["pdf_dpi"] <= 600):
        raise SettingsError("PDF DPI must be between 50 and 600.")
    if "timeout" in clean and not (5 <= clean["timeout"] <= 1800):
        raise SettingsError("Timeout must be between 5 and 1800 seconds.")
    if "model" in clean and not str(clean["model"]).strip():
        raise SettingsError("Model name cannot be empty.")


def load() -> dict:
    """(Re)load settings from disk, layered over the defaults."""
    merged = dict(config.DEFAULT_SETTINGS)
    if os.path.exists(config.SETTINGS_FILE):
        try:
            with open(config.SETTINGS_FILE, encoding="utf-8") as handle:
                merged.update(_coerce(json.load(handle)))
        except (json.JSONDecodeError, OSError, SettingsError):
            # Corrupt/unreadable settings file -> fall back to defaults.
            pass
    with _LOCK:
        _settings.clear()
        _settings.update(merged)
        return dict(_settings)


def get(key: str | None = None):
    with _LOCK:
        if key is None:
            return dict(_settings)
        return _settings[key]


def _persist(snapshot: dict) -> None:
    payload = {key: snapshot[key] for key in config.EDITABLE_KEYS}
    try:
        directory = os.path.dirname(os.path.abspath(config.SETTINGS_FILE))
        os.makedirs(directory, exist_ok=True)
        with open(config.SETTINGS_FILE, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
    except OSError:
        # Persisting is best-effort; the in-memory update still applies.
        pass


def update(data: dict) -> dict:
    """Validate, apply, and persist a partial settings update."""
    clean = _coerce(data)
    if not clean:
        return get()
    _validate(clean)
    with _LOCK:
        _settings.update(clean)
        snapshot = dict(_settings)
    _persist(snapshot)
    return snapshot


def reset() -> dict:
    """Reset all settings back to the env-derived defaults."""
    with _LOCK:
        _settings.clear()
        _settings.update(config.DEFAULT_SETTINGS)
        snapshot = dict(_settings)
    _persist(snapshot)
    return snapshot


# Load persisted settings at import time.
load()
