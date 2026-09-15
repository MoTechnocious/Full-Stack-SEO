"""Thin helpers over the plan catalog for feature/limit checks."""
from __future__ import annotations

from app.billing.plans import get_plan


def get_limit(plan_code: str | None, metric: str) -> int:
    return get_plan(plan_code).limit(metric)


def has_feature(plan_code: str | None, feature: str) -> bool:
    return get_plan(plan_code).has_feature(feature)


def is_unlimited(limit: int) -> bool:
    return limit < 0
