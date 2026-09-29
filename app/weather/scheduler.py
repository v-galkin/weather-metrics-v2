import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.core.exceptions import WeatherAPIError
from app.weather.fetch import weather
from app.weather.metrics import update_metrics

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

# Probably need to move to DB later. Currently ok to have it here
scheduler_config = {
    "query_interval": 60,
}


async def update_all_metrics() -> None:
    settings = get_settings()

    for location in settings.locations:
        try:
            reading = await weather(location)
        except WeatherAPIError as exc:
            logger.warning("Skipping %s: %s", location, exc)
            continue

        update_metrics(reading)


scheduler.add_job(
    update_all_metrics, "interval", seconds=scheduler_config["query_interval"]
)
