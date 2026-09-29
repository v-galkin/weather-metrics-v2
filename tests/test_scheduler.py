import types
from datetime import datetime, timedelta

import pytest
from prometheus_client import REGISTRY
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import WeatherAPIError
from app.weather.scheduler import scheduler, start_scheduler, update_all_metrics


# Helpers
async def _fake_weather(location: str) -> dict:
    test_data = {"temp": 14.2, "humidity": 81, "wind_speed": 4.1}

    return {
        "location": location,
        "temperature_c": test_data["temp"],
        "humidity_percent": test_data["humidity"],
        "wind_speed_mps": test_data["wind_speed"],
    }


async def _weather_fails_for_one(location: str) -> dict:
    test_data = {"temp": 14.2, "humidity": 81, "wind_speed": 4.1}
    if location == "Sch_Test_Fail":
        raise WeatherAPIError("Simulated Error")

    return {
        "location": location,
        "temperature_c": test_data["temp"],
        "humidity_percent": test_data["humidity"],
        "wind_speed_mps": test_data["wind_speed"],
    }


# ------------------------------------------------------------------------------------


# Actual Tests
# Version 2 Test
async def test_start_scheduler_runs_first_update_immediately(mocker):
    mocker.patch("app.weather.scheduler.update_all_metrics")

    start_scheduler()
    try:
        job = scheduler.get_job("update_all_metrics")
        now = datetime.now(job.next_run_time.tzinfo)
        assert job.next_run_time <= now + timedelta(seconds=5)
    finally:
        scheduler.shutdown(wait=False)


async def test_update_all_metrics_skips_failing_location(mocker):
    fake_settings = types.SimpleNamespace(locations=["Sch_Test_Fail", "Sch_Test_Pass"])
    mocker.patch("app.weather.scheduler.get_settings", return_value=fake_settings)
    mocker.patch("app.weather.scheduler.weather", side_effect=_weather_fails_for_one)

    await update_all_metrics()

    assert (
        REGISTRY.get_sample_value(
            "weather_temperature_celsius", {"location": "Sch_Test_Fail"}
        )
        is None
    )

    assert (
        REGISTRY.get_sample_value(
            "weather_temperature_celsius", {"location": "Sch_Test_Pass"}
        )
        == 14.2
    )


# Version 2 Test
async def test_start_scheduler_uses_interval_from_settings(mocker, monkeypatch):
    monkeypatch.setenv("FETCH_INTERVAL_SECONDS", "30")
    get_settings.cache_clear()
    mocker.patch("app.weather.scheduler.update_all_metrics")

    start_scheduler()
    try:
        job = scheduler.get_job("update_all_metrics")
        assert job.trigger.interval == timedelta(seconds=30)
    finally:
        scheduler.shutdown(wait=False)


# Version 2 Test
def test_settings_rejects_non_positive_interval(monkeypatch):
    monkeypatch.setenv("FETCH_INTERVAL_SECONDS", "0")

    with pytest.raises(ValidationError):
        Settings()
