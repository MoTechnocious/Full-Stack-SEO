"""Meta routes: root, health, version (mounted at the app root, no /api prefix)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_settings_dep
from app.config import Settings
from app.models.api import HealthResponse, VersionResponse
from app.version import API_VERSION, __version__

router = APIRouter(tags=["meta"])


@router.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "name": "MySEOapp API",
        "docs": "/docs",
        "health": "/health",
        "version": "/version",
        "api_base": "/api/v1",
    }


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings_dep)) -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.environment)


@router.get("/version", response_model=VersionResponse)
async def version(settings: Settings = Depends(get_settings_dep)) -> VersionResponse:
    return VersionResponse(name=settings.app_name, version=__version__, api_version=API_VERSION)
