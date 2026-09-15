"""Keyword research + SERP routes — tenant-scoped, quota on research."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_kw_provider, get_serp_prov
from app.billing.deps import require_quota
from app.billing.usage import UsageService
from app.core.keywords.providers import KeywordProvider, SerpProvider
from app.core.keywords.research import research_keywords
from app.core.keywords.serp import analyze_serp
from app.db.session import get_session
from app.models.common import AppModel, Device
from app.models.keywords import KeywordResearchRequest, KeywordResearchResult, SerpAnalysis
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_permission

router = APIRouter(prefix="/keywords", tags=["keywords"])


@router.post("/research", response_model=KeywordResearchResult, dependencies=[Depends(require_permission("seo:read"))])
async def research_route(
    req: KeywordResearchRequest,
    ctx: TenantContext = Depends(require_quota("keyword_lookups_per_month")),
    provider: KeywordProvider = Depends(get_kw_provider),
    session: Session = Depends(get_session),
) -> KeywordResearchResult:
    result = research_keywords(req, provider=provider)
    UsageService(session).record(ctx.org_id, "keyword_lookups_per_month", 1)
    return result


class SerpBody(AppModel):
    keyword: str
    country: str = "us"
    device: Device = Device.DESKTOP


@router.post("/serp", response_model=SerpAnalysis)
async def serp_route(
    body: SerpBody,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    provider: SerpProvider = Depends(get_serp_prov),
) -> SerpAnalysis:
    return analyze_serp(body.keyword, provider=provider, country=body.country, device=body.device)
