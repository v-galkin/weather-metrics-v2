from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.weather.status import fetch_status

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    if not fetch_status.is_ready():
        return JSONResponse(status_code=503, content={"status": "not ready"})

    return JSONResponse(content={"status": "ready"})
