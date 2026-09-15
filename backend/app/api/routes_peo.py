"""Personal Entity Optimization routes — tenant-scoped, provider-injected."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_settings_dep
from app.config import Settings
from app.core.peo.bio_builder import build_bio
from app.core.peo.corroboration import audit_corroboration
from app.core.peo.entity_schema import generate_entity_schema
from app.core.peo.providers import (
    KnowledgeGraphProvider,
    ProfileFetcher,
    get_kg_provider,
    get_profile_fetcher,
)
from app.core.peo.repository import PeoRepository, get_peo_repository
from app.core.peo.sensor import analyze_series
from app.middleware.errors import NotFoundError
from app.models.peo import (
    BioRequest,
    BioResult,
    CorroborationReport,
    CorroborationRequest,
    EntitySchemaRequest,
    EntitySchemaResult,
    EntitySearchRequest,
    EntitySearchResult,
    EntityTrackRequest,
    SensorReport,
    TrackedEntity,
)
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_permission

router = APIRouter(prefix="/peo", tags=["peo"])


def get_kg_provider_dep(settings: Settings = Depends(get_settings_dep)) -> KnowledgeGraphProvider:
    return get_kg_provider(settings)


def get_profile_fetcher_dep(settings: Settings = Depends(get_settings_dep)) -> ProfileFetcher:
    return get_profile_fetcher(settings)


def get_peo_repo_dep() -> PeoRepository:
    return get_peo_repository()


@router.post("/entities/search", response_model=EntitySearchResult)
async def entity_search_route(
    req: EntitySearchRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    kg_provider: KnowledgeGraphProvider = Depends(get_kg_provider_dep),
) -> EntitySearchResult:
    """Search the Knowledge Graph for entity candidates (KGMID, types, score)."""
    entities = kg_provider.search_entities(req.query, limit=req.limit, types=req.types or None)
    return EntitySearchResult(query=req.query, entities=entities)


@router.post("/entities/track", response_model=TrackedEntity)
async def entity_track_route(
    req: EntityTrackRequest,
    ctx: TenantContext = Depends(require_permission("seo:write")),
    kg_provider: KnowledgeGraphProvider = Depends(get_kg_provider_dep),
    repo: PeoRepository = Depends(get_peo_repo_dep),
) -> TrackedEntity:
    """Register a KGMID for org-scoped confidence tracking."""
    series = kg_provider.confidence_series(req.kg_mid, points=1)
    entity = TrackedEntity(
        kg_mid=req.kg_mid,
        name=req.name,
        types=req.types,
        description=req.description,
        latest_score=series[-1].score if series else 0.0,
    )
    return repo.track_entity(ctx.org_id, entity)


@router.get("/entities/sensor", response_model=SensorReport)
async def entity_sensor_route(
    kg_mid: str = Query(..., description="Tracked entity KGMID"),
    points: int = Query(default=12, ge=2, le=52),
    ctx: TenantContext = Depends(require_permission("seo:read")),
    kg_provider: KnowledgeGraphProvider = Depends(get_kg_provider_dep),
    repo: PeoRepository = Depends(get_peo_repo_dep),
) -> SensorReport:
    """Confidence-score time series + volatility/trend for a tracked entity."""
    tracked = repo.get_tracked(ctx.org_id, kg_mid)
    if tracked is None:
        raise NotFoundError(f"Entity '{kg_mid}' is not tracked for this organization.")
    observations = kg_provider.confidence_series(kg_mid, points=points)
    return analyze_series(kg_mid, observations, name=tracked.name)


@router.post("/bio/build", response_model=BioResult)
async def bio_build_route(
    req: BioRequest,
    ctx: TenantContext = Depends(require_permission("seo:write")),
) -> BioResult:
    """Generate authoritative short/medium/long entity bios from structured facts."""
    return build_bio(req)


@router.post("/corroboration/audit", response_model=CorroborationReport)
async def corroboration_audit_route(
    req: CorroborationRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    fetcher: ProfileFetcher = Depends(get_profile_fetcher_dep),
) -> CorroborationReport:
    """Diff canonical facts across source profiles (inline and/or fetched)."""
    profiles = list(req.profiles)
    profiles.extend(
        fetcher.fetch_profile(source, req.entity_name) for source in req.fetch_sources
    )
    return audit_corroboration(req.entity_name, req.canonical_facts, profiles)


@router.post("/schema/entity", response_model=EntitySchemaResult)
async def entity_schema_route(
    req: EntitySchemaRequest,
    ctx: TenantContext = Depends(require_permission("seo:write")),
) -> EntitySchemaResult:
    """Generate relationally-linked Person/Organization JSON-LD."""
    return generate_entity_schema(req)
