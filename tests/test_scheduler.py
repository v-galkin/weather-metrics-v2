import types

from prometheus_client import REGISTRY

from app.core.exceptions import WeatherAPIError
from app.weather.scheduler import update_all_metrics


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
