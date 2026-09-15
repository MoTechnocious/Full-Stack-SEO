"""GEO routes — cross-LLM visibility, prompt library/analytics, citation & source
mapping, sentiment profiling, and AI readiness audits. Tenant-scoped."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_settings_dep
from app.config import Settings
from app.core.geo.citations import build_domain_trust_report, scan_citations
from app.core.geo.prompts import add_prompt, build_prompt_tracker, list_prompts, research_prompts
from app.core.geo.providers import (
    AnswerEngineProvider,
    ArtifactFetcher,
    get_answer_engine_provider,
    get_artifact_fetcher,
)
from app.core.geo.readiness import audit_readiness
from app.core.geo.sentiment import scan_sentiment
from app.core.geo.store import GeoStore, get_geo_store
from app.core.geo.visibility import scan_visibility
from app.middleware.errors import BadRequestError
from app.models.geo import (
    AnswerEngine,
    CitationReport,
    CitationScanRequest,
    DomainTrustReport,
    PromptCreate,
    PromptResearchRequest,
    PromptResearchResult,
    PromptTrackerReport,
    ReadinessReport,
    ReadinessRequest,
    SentimentReport,
    SentimentScanRequest,
    TrackedPrompt,
    VisibilityReport,
    VisibilityScanRequest,
)
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_permission

router = APIRouter(prefix="/geo", tags=["geo"])


def get_answer_provider_dep(
    settings: Settings = Depends(get_settings_dep),
) -> AnswerEngineProvider:
    return get_answer_engine_provider(settings)


def get_artifact_fetcher_dep(settings: Settings = Depends(get_settings_dep)) -> ArtifactFetcher:
    return get_artifact_fetcher(settings)


def get_geo_store_dep() -> GeoStore:
    return get_geo_store()


def _resolve_prompts(org_id: str, requested: list[str], store: GeoStore) -> list[str]:
    """Use explicit prompts when given, else fall back to the org's library."""
    prompts = [p.strip() for p in requested if p.strip()]
    if not prompts:
        prompts = [p.text for p in store.list_prompts(org_id)]
    if not prompts:
        raise BadRequestError(
            "No prompts supplied and the prompt library is empty. "
            "Add prompts via POST /geo/prompts or pass them in the request."
        )
    return prompts


# ---------------------------------------------------------------------------
# Cross-LLM visibility
# ---------------------------------------------------------------------------


@router.post("/visibility/scan", response_model=VisibilityReport)
async def visibility_scan_route(
    req: VisibilityScanRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    provider: AnswerEngineProvider = Depends(get_answer_provider_dep),
    store: GeoStore = Depends(get_geo_store_dep),
) -> VisibilityReport:
    prompts = _resolve_prompts(ctx.org_id, req.prompts, store)
    return scan_visibility(
        ctx.org_id,
        req.brand,
        prompts,
        competitors=req.competitors,
        engines=req.engines or None,
        provider=provider,
        store=store,
    )


# ---------------------------------------------------------------------------
# Prompt library & analytics
# ---------------------------------------------------------------------------


@router.get("/prompts", response_model=list[TrackedPrompt])
async def list_prompts_route(
    ctx: TenantContext = Depends(require_permission("seo:read")),
    store: GeoStore = Depends(get_geo_store_dep),
) -> list[TrackedPrompt]:
    return list_prompts(ctx.org_id, store=store)


@router.post("/prompts", response_model=TrackedPrompt)
async def add_prompt_route(
    body: PromptCreate,
    ctx: TenantContext = Depends(require_permission("seo:write")),
    store: GeoStore = Depends(get_geo_store_dep),
) -> TrackedPrompt:
    if not body.text.strip():
        raise BadRequestError("Prompt text must not be empty.")
    return add_prompt(ctx.org_id, body, store=store)


@router.post("/prompts/research", response_model=PromptResearchResult)
async def prompt_research_route(
    req: PromptResearchRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
) -> PromptResearchResult:
    return research_prompts(req)


@router.get("/prompts/tracker", response_model=PromptTrackerReport)
async def prompt_tracker_route(
    brand: str = Query(..., min_length=1),
    competitors: list[str] = Query(default=[]),
    engines: list[AnswerEngine] = Query(default=[]),
    ctx: TenantContext = Depends(require_permission("seo:read")),
    provider: AnswerEngineProvider = Depends(get_answer_provider_dep),
    store: GeoStore = Depends(get_geo_store_dep),
) -> PromptTrackerReport:
    return build_prompt_tracker(
        ctx.org_id,
        brand,
        competitors=competitors,
        engines=engines or None,
        provider=provider,
        store=store,
    )


# ---------------------------------------------------------------------------
# Citation & source mapping
# ---------------------------------------------------------------------------


@router.post("/citations/scan", response_model=CitationReport)
async def citations_scan_route(
    req: CitationScanRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    provider: AnswerEngineProvider = Depends(get_answer_provider_dep),
    store: GeoStore = Depends(get_geo_store_dep),
) -> CitationReport:
    prompts = _resolve_prompts(ctx.org_id, req.prompts, store)
    return scan_citations(
        ctx.org_id,
        req.brand,
        prompts,
        engines=req.engines or None,
        own_domain=req.own_domain,
        provider=provider,
        store=store,
    )


@router.get("/citations/domains", response_model=DomainTrustReport)
async def citation_domains_route(
    own_domain: str | None = Query(default=None),
    ctx: TenantContext = Depends(require_permission("seo:read")),
    store: GeoStore = Depends(get_geo_store_dep),
) -> DomainTrustReport:
    return build_domain_trust_report(ctx.org_id, own_domain=own_domain, store=store)


# ---------------------------------------------------------------------------
# Sentiment profiling
# ---------------------------------------------------------------------------


@router.post("/sentiment/scan", response_model=SentimentReport)
async def sentiment_scan_route(
    req: SentimentScanRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    provider: AnswerEngineProvider = Depends(get_answer_provider_dep),
    store: GeoStore = Depends(get_geo_store_dep),
) -> SentimentReport:
    prompts = _resolve_prompts(ctx.org_id, req.prompts, store)
    return scan_sentiment(
        req.brand,
        prompts,
        engines=req.engines or None,
        provider=provider,
    )


# ---------------------------------------------------------------------------
# AI readiness audit
# ---------------------------------------------------------------------------


@router.post("/readiness/audit", response_model=ReadinessReport)
async def readiness_audit_route(
    req: ReadinessRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    fetcher: ArtifactFetcher = Depends(get_artifact_fetcher_dep),
) -> ReadinessReport:
    if not req.url.strip():
        raise BadRequestError("A non-empty url is required.")
    return audit_readiness(req.url.strip(), fetcher=fetcher)
