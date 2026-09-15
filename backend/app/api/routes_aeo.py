"""Answer Engine Optimization routes — tenant-scoped, provider-injected."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_settings_dep
from app.config import Settings
from app.core.aeo.clustering import build_cluster_map
from app.core.aeo.linking import suggest_links
from app.core.aeo.providers import SerpQuestionProvider, get_question_provider
from app.core.aeo.schema_graph import build_schema_graph
from app.core.aeo.voice import voice_audit
from app.models.aeo import (
    ClusterMapRequest,
    ClusterMapResult,
    LinkSuggestRequest,
    LinkSuggestResult,
    QuestionExtractionResult,
    QuestionExtractRequest,
    SchemaGraphRequest,
    SchemaGraphResult,
    VoiceAuditRequest,
    VoiceAuditResult,
)
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_permission

router = APIRouter(prefix="/aeo", tags=["aeo"])


def get_question_provider_dep(
    settings: Settings = Depends(get_settings_dep),
) -> SerpQuestionProvider:
    return get_question_provider(settings)


@router.post("/questions/extract", response_model=QuestionExtractionResult)
async def questions_extract_route(
    req: QuestionExtractRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    provider: SerpQuestionProvider = Depends(get_question_provider_dep),
) -> QuestionExtractionResult:
    """Extract PAA questions, follow-up chains, and autocomplete pathways."""
    questions = provider.paa_questions(req.seed, depth=req.depth, per_level=req.per_level)
    autocomplete = (
        provider.autocomplete(req.seed, limit=req.autocomplete_limit)
        if req.include_autocomplete
        else []
    )
    return QuestionExtractionResult(seed=req.seed, questions=questions, autocomplete=autocomplete)


@router.post("/clusters/map", response_model=ClusterMapResult)
async def clusters_map_route(
    req: ClusterMapRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
) -> ClusterMapResult:
    """Cluster related questions and emit a structured FAQ layout."""
    return build_cluster_map(req)


@router.post("/schema/graph", response_model=SchemaGraphResult)
async def schema_graph_route(
    req: SchemaGraphRequest,
    ctx: TenantContext = Depends(require_permission("seo:write")),
) -> SchemaGraphResult:
    """Build a combined JSON-LD @graph (WebPage/BreadcrumbList/FAQPage/QAPage/HowTo)."""
    return build_schema_graph(req)


@router.post("/linking/suggest", response_model=LinkSuggestResult)
async def linking_suggest_route(
    req: LinkSuggestRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
) -> LinkSuggestResult:
    """Recommend internal links (TF-IDF cosine similarity, anchor text included)."""
    return suggest_links(req)


@router.post("/voice/audit", response_model=VoiceAuditResult)
async def voice_audit_route(
    req: VoiceAuditRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
) -> VoiceAuditResult:
    """Score content for voice/assistant answer readiness."""
    return voice_audit(req)
