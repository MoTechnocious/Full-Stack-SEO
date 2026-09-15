"""Org-scoped CRUD for managed tracker configs (named prompt sets).

Every mutation is validated against the caller's plan via
:mod:`app.core.aitracker.policy` (engine set, cadence, prompt count, config
count), so entitlements are enforced in one place regardless of entry point.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.core.aitracker.policy import (
    enforce_config_quota,
    enforce_prompt_quota,
    validate_cadence,
    validate_engines,
)
from app.core.aitracker.store import TrackerStore, get_tracker_store
from app.core.geo.providers import brand_slug
from app.middleware.errors import BadRequestError, NotFoundError
from app.models.aitracker import TrackerConfig, TrackerConfigCreate, TrackerConfigUpdate


def _clean_prompts(prompts: list[str]) -> list[str]:
    """Strip, drop empties, dedupe case-insensitively (order preserved)."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for prompt in prompts:
        text = prompt.strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            cleaned.append(text)
    if not cleaned:
        raise BadRequestError("A tracker config needs at least one non-empty prompt.")
    return cleaned


def _clean_competitors(competitors: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for name in competitors:
        text = name.strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            cleaned.append(text)
    return cleaned


def _config_id(org_id: str, name: str, seq: int) -> str:
    digest = hashlib.md5(f"{org_id}|{name.strip().lower()}|{seq}".encode("utf-8")).hexdigest()
    return f"trk-{digest[:12]}"


def create_config(
    org_id: str,
    plan_code: str | None,
    body: TrackerConfigCreate,
    store: TrackerStore | None = None,
    now: datetime | None = None,
) -> TrackerConfig:
    store = store or get_tracker_store()
    name = body.name.strip()
    brand = body.brand.strip()
    if not name:
        raise BadRequestError("A tracker config needs a non-empty name.")
    if not brand:
        raise BadRequestError("A tracker config needs a non-empty brand.")
    if store.find_config_by_name(org_id, name) is not None:
        raise BadRequestError(f"A tracker config named '{name}' already exists.")

    enforce_config_quota(plan_code, len(store.list_configs(org_id)))
    prompts = _clean_prompts(body.prompts)
    enforce_prompt_quota(plan_code, len(prompts))
    engines = validate_engines(plan_code, body.engines)
    cadence = validate_cadence(plan_code, body.refresh_cadence)

    config = TrackerConfig(
        id=_config_id(org_id, name, store.next_seq(org_id)),
        name=name,
        brand=brand,
        prompts=prompts,
        competitors=_clean_competitors(body.competitors),
        engines=engines,
        market=(body.market or "global").strip() or "global",
        language=(body.language or "en").strip() or "en",
        own_domain=(body.own_domain or f"{brand_slug(brand)}.com").strip().lower(),
        refresh_cadence=cadence,
        created_at=now or datetime.now(timezone.utc),
        last_run_at=None,
    )
    store.save_config(org_id, config)
    return config


def list_configs(org_id: str, store: TrackerStore | None = None) -> list[TrackerConfig]:
    store = store or get_tracker_store()
    return store.list_configs(org_id)


def get_config(
    org_id: str, config_id: str, store: TrackerStore | None = None
) -> TrackerConfig:
    store = store or get_tracker_store()
    config = store.get_config(org_id, config_id)
    if config is None:
        raise NotFoundError(f"Tracker config '{config_id}' not found.")
    return config


def update_config(
    org_id: str,
    plan_code: str | None,
    config_id: str,
    body: TrackerConfigUpdate,
    store: TrackerStore | None = None,
) -> TrackerConfig:
    store = store or get_tracker_store()
    config = get_config(org_id, config_id, store=store)
    data = config.model_dump()

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise BadRequestError("A tracker config needs a non-empty name.")
        clash = store.find_config_by_name(org_id, name)
        if clash is not None and clash.id != config_id:
            raise BadRequestError(f"A tracker config named '{name}' already exists.")
        data["name"] = name
    if body.brand is not None:
        brand = body.brand.strip()
        if not brand:
            raise BadRequestError("A tracker config needs a non-empty brand.")
        data["brand"] = brand
    if body.prompts is not None:
        prompts = _clean_prompts(body.prompts)
        enforce_prompt_quota(plan_code, len(prompts))
        data["prompts"] = prompts
    if body.competitors is not None:
        data["competitors"] = _clean_competitors(body.competitors)
    if body.engines is not None:
        # [] resets to the plan's full allowed engine set.
        data["engines"] = validate_engines(plan_code, body.engines)
    if body.market is not None:
        data["market"] = body.market.strip() or "global"
    if body.language is not None:
        data["language"] = body.language.strip() or "en"
    if body.own_domain is not None:
        data["own_domain"] = body.own_domain.strip().lower() or f"{brand_slug(data['brand'])}.com"
    if body.refresh_cadence is not None:
        data["refresh_cadence"] = validate_cadence(plan_code, body.refresh_cadence)

    updated = TrackerConfig(**data)
    store.save_config(org_id, updated)
    return updated


def delete_config(org_id: str, config_id: str, store: TrackerStore | None = None) -> None:
    store = store or get_tracker_store()
    if not store.delete_config(org_id, config_id):
        raise NotFoundError(f"Tracker config '{config_id}' not found.")
