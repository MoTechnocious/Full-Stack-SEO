"""Models for the integration layer: leads/CRM pipeline, webhooks, Make.com gateway."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.models.common import AppModel


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    REJECTED = "rejected"


class LeadRecord(AppModel):
    """A lead captured (e.g. from a public mini-audit widget) for CRM push."""

    id: str | None = None
    name: str = ""
    email: str = ""
    phone: str | None = None
    company: str | None = None
    website: str | None = None
    source: str = "mini_audit"
    message: str | None = None
    custom_fields: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | None = None


class LeadValidationResult(AppModel):
    valid: bool
    normalized: LeadRecord | None = None
    errors: list[str] = []
    warnings: list[str] = []


class DeliveryLog(AppModel):
    id: str
    target: str                 # e.g. "crm:mock", "make:scenario"
    lead_id: str | None = None
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempts: int = 0
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime
    response_ref: str | None = None


class WebhookEvent(AppModel):
    id: str
    type: str
    payload: dict[str, object] = Field(default_factory=dict)
    signature: str | None = None
    verified: bool = False
    received_at: datetime


class MakeDispatch(AppModel):
    """Outbound payload sent to a Make.com webhook / scenario."""

    event: str
    data: dict[str, object] = Field(default_factory=dict)
    idempotency_key: str | None = None
