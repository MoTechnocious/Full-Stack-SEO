"""Background job routes — submit long-running work, poll status, cancel.

Submission endpoints mirror the auth/RBAC/quota guards of the sync endpoint each
job type wraps (quota is enforced AT SUBMISSION TIME; usage is recorded by the
handler once the job succeeds):

- POST /jobs/crawl     mirrors POST /audit/crawl    (seo:run + crawls_per_month)
- POST /jobs/rank-poll mirrors POST /rankings/track (seo:write + tracked_keywords)
- POST /jobs/report    mirrors POST /reports/build  (seo:write + reports_per_month)

Handlers are plain ``def`` (threadpool) so the inline backend can drive the
async crawler engine with ``asyncio.run`` without touching the request loop.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_fetcher, get_serp_prov
from app.billing.deps import require_quota
from app.billing.entitlements import get_limit, has_feature
from app.billing.usage import UsageService
from app.core.crawler.fetcher import Fetcher
from app.core.keywords.providers import SerpProvider
from app.db.session import get_session
from app.jobs.queue import JobQueue, get_job_queue
from app.jobs.tasks import (
    make_crawl_handler,
    make_rank_poll_handler,
    make_report_handler,
    session_factory_from,
)
from app.middleware.errors import NotFoundError
from app.models.audit import CrawlConfig
from app.models.common import AppModel, Device
from app.models.jobs import Job, JobListResponse, JobStatus, JobSubmitResponse, JobType
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_permission
from app.tenancy.repositories import get_repos

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_queue_dep() -> JobQueue:
    """Process-wide queue; overridable in tests (e.g. with an InlineJobQueue)."""
    return get_job_queue()


class RankPollJobBody(AppModel):
    """Mirrors the /rankings/track request body."""

    domain: str
    country: str = "us"
    device: Device = Device.DESKTOP
    keywords: list[str]
    search_volumes: dict[str, int] = {}


class ReportJobBody(AppModel):
    """Mirrors the /reports/build request body."""

    site: str
    period_start: str
    period_end: str
    branding: dict | None = None
    crawl_id: str | None = None
    domain: str | None = None
    country: str = "us"


@router.post("/crawl", response_model=JobSubmitResponse, dependencies=[Depends(require_permission("seo:run"))])
def submit_crawl_job_route(
    config: CrawlConfig,
    ctx: TenantContext = Depends(require_quota("crawls_per_month")),
    fetcher: Fetcher = Depends(get_fetcher),
    session: Session = Depends(get_session),
    queue: JobQueue = Depends(get_queue_dep),
) -> JobSubmitResponse:
    page_cap = get_limit(ctx.plan_code, "pages_per_crawl")
    if page_cap and page_cap > 0:
        config.max_pages = min(config.max_pages, page_cap)
    handler = make_crawl_handler(ctx.org_id, config, fetcher, session_factory_from(session))
    job = queue.submit(ctx.org_id, JobType.CRAWL, handler)
    return JobSubmitResponse(job_id=job.id, status=job.status)


@router.post("/rank-poll", response_model=JobSubmitResponse)
def submit_rank_poll_job_route(
    body: RankPollJobBody,
    ctx: TenantContext = Depends(require_permission("seo:write")),
    session: Session = Depends(get_session),
    serp_provider: SerpProvider = Depends(get_serp_prov),
    queue: JobQueue = Depends(get_queue_dep),
) -> JobSubmitResponse:
    UsageService.check_resource(
        ctx.plan_code, "tracked_keywords",
        get_repos(session, ctx.org_id).count_tracked_keywords(), len(body.keywords),
    )
    handler = make_rank_poll_handler(
        ctx.org_id, body.domain, body.country, body.keywords, body.device,
        body.search_volumes, serp_provider, session_factory_from(session),
    )
    job = queue.submit(ctx.org_id, JobType.RANK_POLL, handler)
    return JobSubmitResponse(job_id=job.id, status=job.status)


@router.post("/report", response_model=JobSubmitResponse, dependencies=[Depends(require_permission("seo:write"))])
def submit_report_job_route(
    body: ReportJobBody,
    ctx: TenantContext = Depends(require_quota("reports_per_month")),
    session: Session = Depends(get_session),
    queue: JobQueue = Depends(get_queue_dep),
) -> JobSubmitResponse:
    # White-label branding requires the plan feature; gate at submission time.
    branding_input = body.branding if (body.branding and has_feature(ctx.plan_code, "white_label")) else None
    handler = make_report_handler(
        ctx.org_id, body.site, body.period_start, body.period_end, branding_input,
        body.crawl_id, body.domain, body.country, session_factory_from(session),
    )
    job = queue.submit(ctx.org_id, JobType.REPORT, handler)
    return JobSubmitResponse(job_id=job.id, status=job.status)


@router.get("", response_model=JobListResponse)
def list_jobs_route(
    status: JobStatus | None = None,
    type: JobType | None = None,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    queue: JobQueue = Depends(get_queue_dep),
) -> JobListResponse:
    items = queue.list(ctx.org_id, status=status, job_type=type)
    return JobListResponse(items=items, total=len(items))


@router.get("/{job_id}", response_model=Job)
def get_job_route(
    job_id: str,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    queue: JobQueue = Depends(get_queue_dep),
) -> Job:
    job = queue.get(ctx.org_id, job_id)
    if job is None:
        raise NotFoundError(f"Job '{job_id}' not found.")
    return job


@router.post("/{job_id}/cancel", response_model=Job)
def cancel_job_route(
    job_id: str,
    ctx: TenantContext = Depends(require_permission("seo:write")),
    queue: JobQueue = Depends(get_queue_dep),
) -> Job:
    job = queue.cancel(ctx.org_id, job_id)
    if job is None:
        raise NotFoundError(f"Job '{job_id}' not found.")
    return job
