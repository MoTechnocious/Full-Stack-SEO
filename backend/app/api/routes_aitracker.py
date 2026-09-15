"""AI Answer-Engine Visibility Tracker routes (v2, PRODUCT_SPEC §8).

Tenant-scoped and tier-gated: every route requires the ``ai_tracker`` plan
feature (the same :func:`require_feature` guard that gates white-label), plus
the usual RBAC permission. Engine sets and refresh cadences are additionally
validated against the plan by :mod:`app.core.aitracker.policy`.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_settings_dep
from app.billing.deps import require_feature
from app.billing.plans import F_AI_TRACKER
from app.config import Settings
from app.core.aitracker.configs import (
    create_config,
    delete_config,
    get_config,
    list_configs,
    update_config,
)
from app.core.aitracker.engine import run_tracker
from app.core.aitracker.policy import validate_engines
from app.core.aitracker.scheduler import due_runs
from app.core.aitracker.store import TrackerStore, get_tracker_store
from app.core.geo.providers import AnswerEngineProvider, get_answer_engine_provider
from app.middleware.errors import NotFoundError
from app.models.aitracker import (
    DueConfig,
    MentionGapReport,
    TrackerConfig,
    TrackerConfigCreate,
    TrackerConfigUpdate,
    TrackerRunReport,
    VisibilityRollup,
)
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_min_role, require_permission
from app.tenancy.rbac import Role

router = APIRouter(prefix="/ai-tracker", tags=["ai-tracker"])


def get_tracker_provider_dep(
    settings: Settings = Depends(get_settings_dep),
) -> AnswerEngineProvider:
    return get_answer_engine_provider(settings)


def get_tracker_store_dep() -> TrackerStore:
    return get_tracker_store()


def _gated(permission: str) -> Callable[..., TenantContext]:
    """Combine the ai_tracker feature gate (402) with an RBAC permission (403)."""
    perm_dep = require_permission(permission)
    feature_dep = require_feature(F_AI_TRACKER)

    def dependency(
        _feat: TenantContext = Depends(feature_dep),
        ctx: TenantContext = Depends(perm_dep),
    ) -> TenantContext:
        return ctx

    return dependency


def _ops_gated() -> Callable[..., TenantContext]:
    """Feature gate + admin/owner-only role gate for the /due ops endpoint."""
    role_dep = require_min_role(Role.AGENCY_ADMIN)
    feature_dep = require_feature(F_AI_TRACKER)

    def dependency(
        _feat: TenantContext = Depends(feature_dep),
        ctx: TenantContext = Depends(role_dep),
    ) -> TenantContext:
        return ctx

    return dependency


# ---------------------------------------------------------------------------
# Managed prompt sets (configs)
# ---------------------------------------------------------------------------


@router.post("/configs", response_model=TrackerConfig)
async def create_config_route(
    body: TrackerConfigCreate,
    ctx: TenantContext = Depends(_gated("seo:write")),
    store: TrackerStore = Depends(get_tracker_store_dep),
) -> TrackerConfig:
    return create_config(ctx.org_id, ctx.plan_code, body, store=store)


@router.get("/configs", response_model=list[TrackerConfig])
async def list_configs_route(
    ctx: TenantContext = Depends(_gated("seo:read")),
    store: TrackerStore = Depends(get_tracker_store_dep),
) -> list[TrackerConfig]:
    return list_configs(ctx.org_id, store=store)


# NOTE: /due is declared before /configs/{config_id} routes purely for
# readability; the paths do not collide.


@router.get("/due", response_model=list[DueConfig])
async def due_configs_route(
    now: datetime | None = Query(default=None),
    ctx: TenantContext = Depends(_ops_gated()),
    store: TrackerStore = Depends(get_tracker_store_dep),
) -> list[DueConfig]:
    """Ops endpoint: configs of this org due for a scheduled refresh.

    The cron/queue hookup is pluggable — poll this endpoint (or call
    ``app.core.aitracker.scheduler.due_runs``) and POST /configs/{id}/run.
    """
    return [
        DueConfig(
            config_id=config.id,
            name=config.name,
            brand=config.brand,
            refresh_cadence=config.refresh_cadence,
            last_run_at=config.last_run_at,
        )
        for _org, config in due_runs(now, org_id=ctx.org_id, store=store)
    ]


@router.get("/configs/{config_id}", response_model=TrackerConfig)
async def get_config_route(
    config_id: str,
    ctx: TenantContext = Depends(_gated("seo:read")),
    store: TrackerStore = Depends(get_tracker_store_dep),
) -> TrackerConfig:
    return get_config(ctx.org_id, config_id, store=store)


@router.put("/configs/{config_id}", response_model=TrackerConfig)
async def update_config_route(
    config_id: str,
    body: TrackerConfigUpdate,
    ctx: TenantContext = Depends(_gated("seo:write")),
    store: TrackerStore = Depends(get_tracker_store_dep),
) -> TrackerConfig:
    return update_config(ctx.org_id, ctx.plan_code, config_id, body, store=store)


@router.delete("/configs/{config_id}")
async def delete_config_route(
    config_id: str,
    ctx: TenantContext = Depends(_gated("seo:write")),
    store: TrackerStore = Depends(get_tracker_store_dep),
) -> dict[str, object]:
    delete_config(ctx.org_id, config_id, store=store)
    return {"deleted": True, "id": config_id}


# ---------------------------------------------------------------------------
# Runs & rollups
# ---------------------------------------------------------------------------


@router.post("/configs/{config_id}/run", response_model=TrackerRunReport)
async def run_config_route(
    config_id: str,
    now: datetime | None = Query(default=None),
    ctx: TenantContext = Depends(_gated("seo:run")),
    provider: AnswerEngineProvider = Depends(get_tracker_provider_dep),
    store: TrackerStore = Depends(get_tracker_store_dep),
) -> TrackerRunReport:
    config = get_config(ctx.org_id, config_id, store=store)
    # Re-validate at run time so a downgraded plan cannot keep running
    # engines it no longer pays for.
    validate_engines(ctx.plan_code, config.engines)
    return run_tracker(ctx.org_id, config, now=now, provider=provider, store=store)


@router.get("/configs/{config_id}/history", response_model=list[VisibilityRollup])
async def config_history_route(
    config_id: str,
    ctx: TenantContext = Depends(_gated("seo:read")),
    store: TrackerStore = Depends(get_tracker_store_dep),
) -> list[VisibilityRollup]:
    get_config(ctx.org_id, config_id, store=store)  # 404 for unknown/foreign configs
    return [run.rollup for run in store.runs(ctx.org_id, config_id)]


@router.get("/configs/{config_id}/visibility", response_model=VisibilityRollup)
async def config_visibility_route(
    config_id: str,
    ctx: TenantContext = Depends(_gated("seo:read")),
    store: TrackerStore = Depends(get_tracker_store_dep),
) -> VisibilityRollup:
    get_config(ctx.org_id, config_id, store=store)
    runs = store.runs(ctx.org_id, config_id)
    if not runs:
        raise NotFoundError(
            f"Tracker config '{config_id}' has no runs yet. POST /configs/{config_id}/run first."
        )
    return runs[-1].rollup


@router.get("/configs/{config_id}/mention-gap", response_model=MentionGapReport)
async def config_mention_gap_route(
    config_id: str,
    ctx: TenantContext = Depends(_gated("seo:read")),
    store: TrackerStore = Depends(get_tracker_store_dep),
) -> MentionGapReport:
    get_config(ctx.org_id, config_id, store=store)
    runs = store.runs(ctx.org_id, config_id)
    if not runs:
        raise NotFoundError(
            f"Tracker config '{config_id}' has no runs yet. POST /configs/{config_id}/run first."
        )
    return runs[-1].mention_gap
