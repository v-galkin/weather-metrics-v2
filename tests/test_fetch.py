import httpx
import pytest
import respx

from app.core.config import get_settings
from app.core.exceptions import LocationNotFoundError, WeatherAPIError
from app.weather.fetch import _parse_data, weather

# Helpers

# ------------------------------------------------------------------------------------


# Actual Tests
def test_parse_data():
    location = "Fetch_Loc_A"
    data = {"main": {"temp": 14.2, "humidity": 81}, "wind": {"speed": 4.1}}

    test_result = _parse_data(data, location)

    assert test_result == {
        "location": location,
        "temperature_c": data["main"]["temp"],
        "humidity_percent": data["main"]["humidity"],
        "wind_speed_mps": data["wind"]["speed"],
    }


@respx.mock
async def test_weather_sucess():
    location = "Fetch_Loc_A"
    data = {"main": {"temp": 14.2, "humidity": 81}, "wind": {"speed": 4.1}}

    settings = get_settings()
    respx.get(settings.openweather_base_url).mock(
        return_value=httpx.Response(200, json=data)
    )

    test_result = await weather(location)

    assert test_result == {
        "location": location,
        "temperature_c": data["main"]["temp"],
        "humidity_percent": data["main"]["humidity"],
        "wind_speed_mps": data["wind"]["speed"],
    }


@respx.mock
async def test_weather_not_found():
    settings = get_settings()
    respx.get(settings.openweather_base_url).mock(
        return_value=httpx.Response(
            404, json={"cod": "404", "message": "Location not found"}
        )
    )

    with pytest.raises(LocationNotFoundError):
        await weather("Asdqf")


@respx.mock
async def test_weather_bad_key():
    settings = get_settings()
    respx.get(settings.openweather_base_url).mock(
        return_value=httpx.Response(
            401, json={"cod": "401", "message": "Invalid API key"}
        )
    )

    with pytest.raises(WeatherAPIError):
        await weather("Auckland")


@respx.mock
async def test_weather_timeout():
    settings = get_settings()
    respx.get(settings.openweather_base_url).mock(
        side_effect=httpx.TimeoutException("Timed out")
    )

    with pytest.raises(WeatherAPIError):
        await weather("Auckland")


@respx.mock
async def test_weather_server_error():
    settings = get_settings()
    respx.get(settings.openweather_base_url).mock(
        return_value=httpx.Response(
            500, json={"cod": "500", "message": "Internal error"}
        )
    )

    with pytest.raises(WeatherAPIError):
        await weather("Auckland")


@respx.mock
async def test_weather_connection_error():
    settings = get_settings()
    respx.get(settings.openweather_base_url).mock(
        side_effect=httpx.ConnectError("Connection error")
    )

    with pytest.raises(WeatherAPIError):
        await weather("Auckland")
