"""Billing FastAPI guards: feature gating + quota enforcement (per plan)."""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends
from sqlmodel import Session

from app.billing.entitlements import has_feature
from app.billing.usage import UsageService
from app.db.session import get_session
from app.middleware.errors import FeatureNotAvailableError
from app.tenancy.context import TenantContext
from app.tenancy.deps import get_tenant_context


def require_feature(feature: str) -> Callable[..., TenantContext]:
    def dependency(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if not has_feature(ctx.plan_code, feature):
            raise FeatureNotAvailableError(
                f"'{feature}' is not included in the '{ctx.plan_code}' plan. Upgrade to enable it."
            )
        return ctx

    return dependency


def require_quota(metric: str, amount: int = 1) -> Callable[..., TenantContext]:
    """Guard a route by a monthly quota. Does NOT consume — call UsageService.record
    after the action succeeds."""

    def dependency(
        ctx: TenantContext = Depends(get_tenant_context),
        session: Session = Depends(get_session),
    ) -> TenantContext:
        UsageService(session).enforce(ctx.org_id, ctx.plan_code, metric, amount)
        return ctx

    return dependency
