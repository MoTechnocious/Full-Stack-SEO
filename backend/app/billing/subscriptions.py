"""Subscription lifecycle helpers (create/get/update)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.config import get_settings
from app.db.models_billing import Subscription
from app.db.models_tenancy import Organization


def get_subscription(session: Session, org_id: str) -> Subscription | None:
    return session.exec(select(Subscription).where(Subscription.org_id == org_id)).first()


def ensure_subscription(
    session: Session, org_id: str, plan_code: str | None = None
) -> Subscription:
    existing = get_subscription(session, org_id)
    if existing:
        return existing
    settings = get_settings()
    now = datetime.now(timezone.utc)
    sub = Subscription(
        org_id=org_id,
        plan_code=plan_code or settings.default_plan_code,
        status="trialing",
        provider=settings.billing_provider,
        current_period_start=now,
        current_period_end=now + timedelta(days=settings.billing_trial_days),
    )
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub


def set_plan(
    session: Session,
    org_id: str,
    plan_code: str,
    *,
    status: str = "active",
    provider: str | None = None,
    provider_customer_id: str | None = None,
    provider_subscription_id: str | None = None,
    current_period_end: datetime | None = None,
    seats: int | None = None,
) -> Subscription:
    sub = ensure_subscription(session, org_id, plan_code)
    sub.plan_code = plan_code
    sub.status = status
    if provider:
        sub.provider = provider
    if provider_customer_id:
        sub.provider_customer_id = provider_customer_id
    if provider_subscription_id:
        sub.provider_subscription_id = provider_subscription_id
    if current_period_end:
        sub.current_period_end = current_period_end
    if seats is not None:
        sub.seats = seats
    sub.updated_at = datetime.now(timezone.utc)
    session.add(sub)

    # Keep the denormalized plan_code on the org in sync (used by TenantContext).
    org = session.get(Organization, org_id)
    if org:
        org.plan_code = plan_code
        session.add(org)
    session.commit()
    session.refresh(sub)
    return sub
