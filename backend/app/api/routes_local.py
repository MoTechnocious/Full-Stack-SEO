"""Local SEO routes — tenant-scoped GBP manager and citation/NAP distribution."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.local.citations import CitationSyncEngine, get_citation_engine
from app.core.local.gbp import GbpManager, GbpProvider, get_gbp_provider
from app.middleware.errors import NotFoundError
from app.models.common import AppModel
from app.models.local import (
    CitationStatusReport,
    CitationSyncReport,
    Directory,
    GbpMetrics,
    GbpPost,
    GbpPostCreate,
    GbpReview,
    NapRecord,
    SuggestedReply,
)
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_permission

router = APIRouter(prefix="/local", tags=["local"])


# ---- Injectable providers (overridable in tests via dependency_overrides) ----


def get_gbp_provider_dep() -> GbpProvider:
    return get_gbp_provider()


def get_citation_engine_dep() -> CitationSyncEngine:
    return get_citation_engine()


# ---- GBP manager ----


@router.post("/gbp/posts", response_model=GbpPost)
async def publish_gbp_post_route(
    body: GbpPostCreate,
    ctx: TenantContext = Depends(require_permission("seo:write")),
    provider: GbpProvider = Depends(get_gbp_provider_dep),
) -> GbpPost:
    return GbpManager(provider).publish_post(ctx.org_id, body)


@router.get("/gbp/metrics", response_model=GbpMetrics)
async def gbp_metrics_route(
    period_days: int = Query(30, ge=1, le=365),
    ctx: TenantContext = Depends(require_permission("seo:read")),
    provider: GbpProvider = Depends(get_gbp_provider_dep),
) -> GbpMetrics:
    return GbpManager(provider).metrics(ctx.org_id, period_days)


class ReviewListResponse(AppModel):
    reviews: list[GbpReview] = []
    suggested_replies: list[SuggestedReply] = []


@router.get("/gbp/reviews", response_model=ReviewListResponse)
async def gbp_reviews_route(
    ctx: TenantContext = Depends(require_permission("seo:read")),
    provider: GbpProvider = Depends(get_gbp_provider_dep),
) -> ReviewListResponse:
    manager = GbpManager(provider)
    return ReviewListResponse(
        reviews=manager.reviews(ctx.org_id),
        suggested_replies=manager.suggested_replies(ctx.org_id, ctx.org_name),
    )


class ReviewReplyBody(AppModel):
    text: str | None = None  # empty -> use the generated suggested reply


@router.post("/gbp/reviews/{review_id}/reply", response_model=GbpReview)
async def gbp_review_reply_route(
    review_id: str,
    body: ReviewReplyBody,
    ctx: TenantContext = Depends(require_permission("seo:write")),
    provider: GbpProvider = Depends(get_gbp_provider_dep),
) -> GbpReview:
    review = GbpManager(provider).reply(ctx.org_id, review_id, body.text)
    if review is None:
        raise NotFoundError(f"No review '{review_id}' for this organization.")
    return review


# ---- Citation distributor ----


@router.get("/citations/nap", response_model=NapRecord)
async def get_nap_route(
    ctx: TenantContext = Depends(require_permission("seo:read")),
    engine: CitationSyncEngine = Depends(get_citation_engine_dep),
) -> NapRecord:
    nap = engine.get_nap(ctx.org_id)
    if nap is None:
        raise NotFoundError("No NAP record configured for this organization.")
    return nap


@router.put("/citations/nap", response_model=NapRecord)
async def put_nap_route(
    body: NapRecord,
    ctx: TenantContext = Depends(require_permission("seo:write")),
    engine: CitationSyncEngine = Depends(get_citation_engine_dep),
) -> NapRecord:
    return engine.set_nap(ctx.org_id, body)


@router.post("/citations/sync", response_model=CitationSyncReport)
async def sync_citations_route(
    directory: Directory | None = Query(None),
    ctx: TenantContext = Depends(require_permission("seo:write")),
    engine: CitationSyncEngine = Depends(get_citation_engine_dep),
) -> CitationSyncReport:
    try:
        return engine.sync(ctx.org_id, only=directory)
    except KeyError as exc:
        raise NotFoundError("No NAP record configured for this organization.") from exc


@router.get("/citations/status", response_model=CitationStatusReport)
async def citations_status_route(
    ctx: TenantContext = Depends(require_permission("seo:read")),
    engine: CitationSyncEngine = Depends(get_citation_engine_dep),
) -> CitationStatusReport:
    try:
        return engine.status(ctx.org_id)
    except KeyError as exc:
        raise NotFoundError("No NAP record configured for this organization.") from exc
