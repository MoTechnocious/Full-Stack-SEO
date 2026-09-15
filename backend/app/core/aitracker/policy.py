"""Per-plan entitlement policy for the AI tracker (PRODUCT_SPEC §7).

Free/Starter: not included. Entry tier (``pro``, the spec's Growth analogue):
ChatGPT only + weekly refresh. Agency/Enterprise: all five engines + daily
refresh. The feature flags and quota knobs live in :mod:`app.billing.plans`
(``ai_tracker``, ``ai_tracker_all_engines``, ``ai_tracker_configs``,
``ai_tracker_prompts_per_config``); this module turns them into concrete
engine sets, cadence sets, and quota checks.
"""
from __future__ import annotations

from app.billing.entitlements import get_limit, has_feature, is_unlimited
from app.billing.plans import (
    F_AI_TRACKER,
    F_AI_TRACKER_ALL_ENGINES,
    L_AI_TRACKER_CONFIGS,
    L_AI_TRACKER_PROMPTS,
)
from app.middleware.errors import FeatureNotAvailableError, QuotaExceededError
from app.models.aitracker import RefreshCadence, TrackerEngine

# What the entry tier (feature flag without the all-engines flag) may use.
ENTRY_TIER_ENGINES: tuple[TrackerEngine, ...] = (TrackerEngine.CHATGPT,)
ENTRY_TIER_CADENCES: tuple[RefreshCadence, ...] = (RefreshCadence.WEEKLY,)


def allowed_engines(plan_code: str | None) -> list[TrackerEngine]:
    """Engines the plan may track (empty when the feature is not included)."""
    if not has_feature(plan_code, F_AI_TRACKER):
        return []
    if has_feature(plan_code, F_AI_TRACKER_ALL_ENGINES):
        return list(TrackerEngine)
    return list(ENTRY_TIER_ENGINES)


def allowed_cadences(plan_code: str | None) -> list[RefreshCadence]:
    """Refresh cadences the plan may schedule."""
    if not has_feature(plan_code, F_AI_TRACKER):
        return []
    if has_feature(plan_code, F_AI_TRACKER_ALL_ENGINES):
        return [RefreshCadence.DAILY, RefreshCadence.WEEKLY]
    return list(ENTRY_TIER_CADENCES)


def validate_engines(
    plan_code: str | None, engines: list[TrackerEngine]
) -> list[TrackerEngine]:
    """Resolve + validate an engine set against the plan.

    Empty input resolves to the plan's full allowed set. Requesting an engine
    outside the plan raises :class:`FeatureNotAvailableError` (402).
    """
    allowed = allowed_engines(plan_code)
    if not engines:
        return allowed
    denied = [e.value for e in engines if e not in allowed]
    if denied:
        raise FeatureNotAvailableError(
            f"Engines {denied} are not included in the '{plan_code}' plan "
            f"(allowed: {[e.value for e in allowed]}). Upgrade to track more engines."
        )
    deduped: list[TrackerEngine] = []
    for engine in engines:
        if engine not in deduped:
            deduped.append(engine)
    return deduped


def validate_cadence(plan_code: str | None, cadence: RefreshCadence) -> RefreshCadence:
    """Validate a refresh cadence against the plan (402 when too frequent)."""
    if cadence not in allowed_cadences(plan_code):
        raise FeatureNotAvailableError(
            f"'{cadence.value}' refresh is not included in the '{plan_code}' plan. "
            "Upgrade for daily tracking."
        )
    return cadence


def enforce_config_quota(plan_code: str | None, existing_count: int) -> None:
    """Raise 402 when the org already has as many configs as the plan allows."""
    limit = get_limit(plan_code, L_AI_TRACKER_CONFIGS)
    if is_unlimited(limit):
        return
    if existing_count >= limit:
        raise QuotaExceededError(
            f"The '{plan_code}' plan allows at most {limit} tracker configs. "
            "Delete one or upgrade."
        )


def enforce_prompt_quota(plan_code: str | None, prompt_count: int) -> None:
    """Raise 402 when a prompt set is larger than the plan allows."""
    limit = get_limit(plan_code, L_AI_TRACKER_PROMPTS)
    if is_unlimited(limit):
        return
    if prompt_count > limit:
        raise QuotaExceededError(
            f"The '{plan_code}' plan allows at most {limit} prompts per tracker "
            f"config (got {prompt_count})."
        )
