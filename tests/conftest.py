"""Shared pytest fixtures.

Settings are isolated per-test by pointing ``config.SETTINGS_FILE`` at a temp
file and resetting to defaults, so tests never touch a real ``settings.json``.
"""

import pytest

import app as flaskapp
import config
import ocr
import settings


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    settings.reset()
    flaskapp.app.config["TESTING"] = True
    yield flaskapp.app.test_client()
    settings.load()


@pytest.fixture
def temp_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    settings.reset()
    yield
    settings.load()


@pytest.fixture
def mock_ocr(monkeypatch):
    """Replace the network OCR call with a deterministic stub."""
    monkeypatch.setattr(ocr, "_ocr_image", lambda image: "MOCK TEXT")
