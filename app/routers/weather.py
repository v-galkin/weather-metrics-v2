from fastapi import APIRouter, HTTPException

from app.core.exceptions import LocationNotFoundError, WeatherAPIError
from app.weather.fetch import weather
from app.weather.metrics import update_metrics

router = APIRouter()


@router.get("/weather/{location}")
async def get_weather(location: str) -> dict:
    try:
        reading = await weather(location)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except WeatherAPIError:
        raise HTTPException(status_code=502, detail="Weather service unavailable")

    update_metrics(reading)
    return reading
