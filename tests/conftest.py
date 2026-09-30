import pytest

from app.core.config import get_settings
from app.weather.status import fetch_status


@pytest.fixture(autouse=True)
def fake_settings(monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_fetch_status(monkeypatch):
    monkeypatch.setattr(fetch_status, "has_fetched", False)
