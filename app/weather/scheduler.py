import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.core.exceptions import LocationNotFoundError, WeatherAPIError
from app.weather.fetch import weather
from app.weather.metrics import record_fetch_error, update_metrics
from app.weather.status import fetch_status

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    scheduler.add_job(
        update_all_metrics,
        "interval",
        seconds=get_settings().fetch_interval_seconds,
        id="update_all_metrics",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )

    scheduler.start()


async def update_all_metrics() -> None:
    settings = get_settings()

    for location in settings.locations:
        try:
            reading = await weather(location)
        except (WeatherAPIError, LocationNotFoundError) as exc:
            logger.warning("Skipping %s: %s", location, exc)
            record_fetch_error(location)
            continue

        update_metrics(reading)
        fetch_status.mark_success()
