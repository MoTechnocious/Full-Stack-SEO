"""Billing tables: Subscription + UsageRecord (quota metering).

Plan *definitions* live in code (``app.billing.plans``); these tables track each
org's live subscription and period usage counters.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: str = Field(default_factory=_uuid, primary_key=True)
    org_id: str = Field(index=True, unique=True)
    plan_code: str = "free"
    status: str = "trialing"     # trialing | active | past_due | canceled | incomplete
    provider: str = "mock"       # mock | stripe
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None
    seats: int = 1
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class UsageRecord(SQLModel, table=True):
    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint("org_id", "metric", "period", name="uq_usage_org_metric_period"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    org_id: str = Field(index=True)
    metric: str = Field(index=True)       # e.g. crawls, tracked_keywords, content_scores
    period: str = Field(index=True)       # "YYYY-MM" for monthly metrics, "total" for absolute
    count: int = 0
    updated_at: datetime = Field(default_factory=_now)
