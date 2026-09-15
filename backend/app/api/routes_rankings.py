"""Rank tracking routes — tenant-scoped, resource-limited by plan."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_serp_prov
from app.billing.usage import UsageService
from app.core.keywords.providers import SerpProvider
from app.core.keywords.rank_tracker import RankTracker
from app.db.session import get_session
from app.middleware.errors import NotFoundError
from app.models.common import AppModel, Device
from app.models.keywords import RankTrackingSummary
from app.services.store import InMemoryStore
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_permission
from app.tenancy.repositories import get_repos

router = APIRouter(prefix="/rankings", tags=["rankings"])


class TrackBody(AppModel):
    domain: str
    country: str = "us"
    device: Device = Device.DESKTOP
    keywords: list[str]
    search_volumes: dict[str, int] = {}


@router.post("/track", response_model=RankTrackingSummary)
async def track_route(
    body: TrackBody,
    ctx: TenantContext = Depends(require_permission("seo:write")),
    session: Session = Depends(get_session),
    serp_provider: SerpProvider = Depends(get_serp_prov),
) -> RankTrackingSummary:
    repos = get_repos(session, ctx.org_id)
    UsageService.check_resource(
        ctx.plan_code, "tracked_keywords", repos.count_tracked_keywords(), len(body.keywords)
    )
    tracker = RankTracker(store=InMemoryStore(), serp_provider=serp_provider)  # transient, per-request
    tracker.add_keywords(
        body.domain, body.country, body.keywords,
        device=body.device, search_volumes=body.search_volumes or None,
    )
    tracker.poll(body.domain, body.country, device=body.device)
    summary = tracker.build_summary(body.domain, body.country)
    repos.save_summary(summary)
    return summary


@router.get("/{domain}", response_model=RankTrackingSummary)
async def get_rankings_route(
    domain: str,
    country: str = "us",
    ctx: TenantContext = Depends(require_permission("seo:read")),
    session: Session = Depends(get_session),
) -> RankTrackingSummary:
    summary = get_repos(session, ctx.org_id).get_summary(domain, country)
    if summary is None:
        raise NotFoundError(f"No rankings tracked for '{domain}' ({country}).")
    return summary
