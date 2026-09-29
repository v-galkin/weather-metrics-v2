from fastapi.testclient import TestClient

from app.core.exceptions import LocationNotFoundError, WeatherAPIError
from app.main import app

client = TestClient(app)


# Helpers
async def _fake_weather(location: str) -> dict:
    test_data = {"temp": 14.2, "humidity": 81, "wind_speed": 4.1}

    return {
        "location": location,
        "temperature_c": test_data["temp"],
        "humidity_percent": test_data["humidity"],
        "wind_speed_mps": test_data["wind_speed"],
    }


async def _weather_not_found(location: str) -> dict:
    raise LocationNotFoundError(location)


async def _weather_upstream_error(location: str) -> dict:
    raise WeatherAPIError("Weather API rejected provided API key")


# ------------------------------------------------------------------------------------


# Actual Tests
def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_weather_success(mocker):
    test_data = {
        "location": "Routes_Loc_A",
        "temp": 14.2,
        "humidity": 81,
        "wind_speed": 4.1,
    }

    mocker.patch("app.routers.weather.weather", side_effect=_fake_weather)

    response = client.get("/weather/Routes_Loc_A")

    assert response.status_code == 200

    assert response.json() == {
        "location": test_data["location"],
        "temperature_c": test_data["temp"],
        "humidity_percent": test_data["humidity"],
        "wind_speed_mps": test_data["wind_speed"],
    }


def test_get_weather_not_found(mocker):
    fake_location = "ASdfqew"

    mocker.patch("app.routers.weather.weather", side_effect=_weather_not_found)

    response = client.get(f"/weather/{fake_location}")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Location '{fake_location}' does not exist"}


def test_get_weather_upstream_error(mocker):
    location = "Routes_Loc_A"

    mocker.patch("app.routers.weather.weather", side_effect=_weather_upstream_error)

    response = client.get(f"/weather/{location}")

    assert response.status_code == 502
    assert response.json() == {"detail": "Weather service unavailable"}
    assert "API key" not in response.text
