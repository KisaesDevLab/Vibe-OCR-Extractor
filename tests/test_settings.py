"""Tests for the runtime settings manager."""

import pytest

import config
import settings


def test_defaults(temp_settings):
    current = settings.get()
    assert current["base_url"].startswith("http")
    assert current["model"]
    assert isinstance(current["pdf_dpi"], int)


def test_update_and_persist(temp_settings):
    settings.update({"model": "custom-glm", "pdf_dpi": 300})
    assert settings.get("model") == "custom-glm"
    assert settings.get("pdf_dpi") == 300
    # Reload from disk to confirm persistence.
    settings.load()
    assert settings.get("model") == "custom-glm"
    assert settings.get("pdf_dpi") == 300


def test_partial_update_keeps_other_values(temp_settings):
    original_url = settings.get("base_url")
    settings.update({"model": "only-model"})
    assert settings.get("model") == "only-model"
    assert settings.get("base_url") == original_url


def test_numeric_coercion_from_strings(temp_settings):
    settings.update({"pdf_dpi": "250", "timeout": "60"})
    assert settings.get("pdf_dpi") == 250
    assert settings.get("timeout") == 60


@pytest.mark.parametrize(
    "bad",
    [
        {"pdf_dpi": 9999},
        {"pdf_dpi": 10},
        {"base_url": "ftp://example.com"},
        {"timeout": 1},
        {"timeout": 99999},
        {"model": "   "},
    ],
)
def test_validation_rejects_bad_values(temp_settings, bad):
    with pytest.raises(settings.SettingsError):
        settings.update(bad)


def test_unknown_keys_are_ignored(temp_settings):
    settings.update({"not_a_setting": "x", "model": "kept"})
    assert settings.get("model") == "kept"
    assert "not_a_setting" not in settings.get()


def test_reset(temp_settings):
    settings.update({"model": "temp"})
    settings.reset()
    assert settings.get("model") == config.DEFAULT_SETTINGS["model"]
