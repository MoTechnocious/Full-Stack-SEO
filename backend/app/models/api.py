"""Generic API envelope + meta response models."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

from app.models.common import AppModel

T = TypeVar("T")


class ErrorDetail(AppModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(AppModel):
    error: str
    detail: str = ""
    request_id: str | None = None
    errors: list[ErrorDetail] = []


class HealthResponse(AppModel):
    status: str = "ok"
    environment: str = "development"


class VersionResponse(AppModel):
    name: str
    version: str
    api_version: str


class Page(BaseModel, Generic[T]):
    """Simple pagination envelope."""

    items: list[T]
    total: int
    page: int = 1
    page_size: int = 50
