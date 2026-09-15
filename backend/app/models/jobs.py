"""Background job domain models (org-scoped, backend-agnostic)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import Field

from app.models.common import AppModel


class JobType(str, Enum):
    """Kinds of long-running work executed on the job queue."""

    CRAWL = "crawl"
    RANK_POLL = "rank_poll"
    REPORT = "report"


class JobStatus(str, Enum):
    """Lifecycle of a job. Terminal states: succeeded / failed / cancelled."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(AppModel):
    """A single background job and its progress/result metadata.

    ``result_ref`` points at the artifact produced by the job in the existing
    persistence layer (crawl_id for crawls, ``domain|country`` for rank polls,
    report_id for reports) so results are fetched through the existing GET
    endpoints (e.g. ``GET /audit/crawl/{id}``).
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    org_id: str
    type: JobType
    status: JobStatus = JobStatus.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    submitted_at: datetime = Field(default_factory=_utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result_ref: str | None = None
    error: str | None = None
    attempts: int = 0


class JobSubmitResponse(AppModel):
    """Returned by POST /jobs/* submission endpoints."""

    job_id: str
    status: JobStatus


class JobListResponse(AppModel):
    """Org-scoped job listing envelope."""

    items: list[Job]
    total: int
