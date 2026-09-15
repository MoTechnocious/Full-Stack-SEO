"""Kit assistant routes — tenant-scoped; injectable providers for the agentic queue."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlmodel import Session

from app.core.assistant.advisor import build_action_items
from app.core.assistant.calendar import build_content_calendar
from app.core.assistant.execution import (
    ActionExecutor,
    ActionQueueService,
    CmsAdapter,
    ContentGenerator,
    get_cms_adapter,
    get_content_generator,
    get_queue_service,
)
from app.core.assistant.mapping import map_keywords
from app.core.local.citations import CitationSyncEngine, get_citation_engine
from app.core.local.gbp import GbpProvider, get_gbp_provider
from app.db.session import get_session
from app.middleware.errors import BadRequestError, NotFoundError
from app.models.assistant import (
    ActionItemPlan,
    ActionType,
    CalendarCadence,
    ContentCalendar,
    KeywordMapResult,
    QueuedAction,
    QueueRunReport,
    SitePage,
)
from app.models.common import AppModel, Issue
from app.models.keywords import Keyword
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_permission
from app.tenancy.repositories import get_repos

router = APIRouter(prefix="/assistant", tags=["assistant"])


# ---- Injectable providers (overridable in tests via dependency_overrides) ----


def get_queue_service_dep() -> ActionQueueService:
    return get_queue_service()


def get_content_generator_dep() -> ContentGenerator:
    return get_content_generator()


def get_cms_adapter_dep() -> CmsAdapter:
    return get_cms_adapter()


def get_gbp_provider_dep() -> GbpProvider:
    return get_gbp_provider()


def get_citation_engine_dep() -> CitationSyncEngine:
    return get_citation_engine()


# ---- Continuous audit -> action items ----


class ActionPlanBody(AppModel):
    site: str
    crawl_id: str | None = None
    domain: str | None = None
    country: str = "us"
    issues: list[Issue] = []


@router.post("/actions/plan", response_model=ActionItemPlan)
async def action_items_route(
    body: ActionPlanBody,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    session: Session = Depends(get_session),
) -> ActionItemPlan:
    repos = get_repos(session, ctx.org_id)
    audit = repos.get_crawl(body.crawl_id) if body.crawl_id else None
    rank_summary = repos.get_summary(body.domain, body.country) if body.domain else None
    return build_action_items(
        body.site, audit=audit, issues=body.issues, rank_summary=rank_summary
    )


# ---- Agentic execution queue ----


class EnqueueBody(AppModel):
    type: ActionType
    params: dict[str, object] = {}
    approval_required: bool = False
    max_attempts: int = Field(default=3, ge=1, le=10)


@router.get("/queue", response_model=list[QueuedAction])
async def list_queue_route(
    ctx: TenantContext = Depends(require_permission("seo:read")),
    queue: ActionQueueService = Depends(get_queue_service_dep),
) -> list[QueuedAction]:
    return queue.list(ctx.org_id)


@router.post("/queue", response_model=QueuedAction)
async def enqueue_route(
    body: EnqueueBody,
    ctx: TenantContext = Depends(require_permission("seo:write")),
    queue: ActionQueueService = Depends(get_queue_service_dep),
) -> QueuedAction:
    return queue.enqueue(
        ctx.org_id,
        body.type,
        body.params,
        approval_required=body.approval_required,
        max_attempts=body.max_attempts,
    )


@router.post("/queue/{action_id}/approve", response_model=QueuedAction)
async def approve_route(
    action_id: str,
    ctx: TenantContext = Depends(require_permission("seo:write")),
    queue: ActionQueueService = Depends(get_queue_service_dep),
) -> QueuedAction:
    try:
        action = queue.approve(ctx.org_id, action_id)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    if action is None:
        raise NotFoundError(f"No queued action '{action_id}' for this organization.")
    return action


@router.post("/queue/run", response_model=QueueRunReport)
async def run_queue_route(
    ctx: TenantContext = Depends(require_permission("seo:write")),
    queue: ActionQueueService = Depends(get_queue_service_dep),
    generator: ContentGenerator = Depends(get_content_generator_dep),
    cms: CmsAdapter = Depends(get_cms_adapter_dep),
    gbp: GbpProvider = Depends(get_gbp_provider_dep),
    citations: CitationSyncEngine = Depends(get_citation_engine_dep),
) -> QueueRunReport:
    executor = ActionExecutor(
        content_generator=generator, cms_adapter=cms, gbp_provider=gbp, citation_engine=citations
    )
    return queue.run(ctx.org_id, executor)


# ---- Keyword mapping & cannibalization ----


class KeywordMapBody(AppModel):
    keywords: list[str]
    pages: list[SitePage]
    cannibalization_ratio: float = Field(default=0.8, gt=0.0, le=1.0)


@router.post("/keywords/map", response_model=KeywordMapResult)
async def keyword_map_route(
    body: KeywordMapBody,
    ctx: TenantContext = Depends(require_permission("seo:read")),
) -> KeywordMapResult:
    return map_keywords(
        body.keywords, body.pages, cannibalization_ratio=body.cannibalization_ratio
    )


# ---- Content calendar ----


class CalendarBody(AppModel):
    keywords: list[Keyword]
    start_date: date
    cadence: CalendarCadence = CalendarCadence.WEEKLY
    max_entries: int = Field(default=12, ge=1, le=100)
    pages: list[SitePage] = []


@router.post("/calendar/build", response_model=ContentCalendar)
async def calendar_build_route(
    body: CalendarBody,
    ctx: TenantContext = Depends(require_permission("seo:read")),
) -> ContentCalendar:
    assignments = None
    if body.pages:
        mapped = map_keywords([k.keyword for k in body.keywords], body.pages)
        assignments = mapped.assignments
    return build_content_calendar(
        body.keywords,
        start=body.start_date,
        cadence=body.cadence,
        max_entries=body.max_entries,
        assignments=assignments,
    )
