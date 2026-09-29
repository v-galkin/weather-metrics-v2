import httpx

from app.core.config import get_settings
from app.core.exceptions import LocationNotFoundError, WeatherAPIError

# Helpers(Private functions)


# Fetch data
async def _request(location: str) -> httpx.Response:
    settings = get_settings()

    # Using request with city as location, not lon and lat
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:

        try:
            response = await client.get(
                settings.openweather_base_url,
                params={
                    # City
                    "q": location,
                    "appid": settings.openweather_api_key,
                    "units": "metric",
                },
            )
        except httpx.TimeoutException as exc:
            raise WeatherAPIError("Weather API request timed out") from exc
        except httpx.RequestError as exc:
            raise WeatherAPIError("Could not reach the weather API") from exc

    return response


# Check status response to raise exceptions if needed
def _check_status(response: httpx.Response, location: str) -> None:
    if response.status_code == 404:
        raise LocationNotFoundError(location)

    if response.status_code == 401:
        raise WeatherAPIError("Weather API rejected the API key")

    if response.status_code != 200:
        raise WeatherAPIError(f"Weather API returned status {response.status_code}")


# Parse data
def _parse_data(data: dict, location: str) -> dict:
    return {
        "location": location,
        "temperature_c": data["main"]["temp"],
        "humidity_percent": data["main"]["humidity"],
        "wind_speed_mps": data["wind"]["speed"],
    }


# -----------------------------------------------------------------------------------------------


# Public
async def weather(location: str) -> dict:
    response = await _request(location)
    _check_status(response, location)

    weather_data = _parse_data(response.json(), location)

    return weather_data
