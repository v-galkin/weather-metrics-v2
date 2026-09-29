from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import health, metrics, weather
from app.weather.scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Weather Metrics", lifespan=lifespan)

app.include_router(health.router)
app.include_router(weather.router)
app.include_router(metrics.router)
