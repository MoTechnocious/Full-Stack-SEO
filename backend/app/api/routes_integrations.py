"""Integration routes — tenant-scoped lead pipeline; public inbound webhook."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.api.deps import get_settings_dep
from app.config import Settings
from app.db.session import get_session
from app.integrations.crm_pipeline import LeadPipeline, get_crm_adapter
from app.integrations.make_gateway import MakeGateway
from app.integrations.webhooks import parse_event
from app.models.integrations import DeliveryLog, LeadRecord
from app.services.store import InMemoryStore
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_permission
from app.tenancy.repositories import get_repos

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/leads", response_model=DeliveryLog)
async def submit_lead_route(
    lead: LeadRecord,
    ctx: TenantContext = Depends(require_permission("leads:write")),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_dep),
) -> DeliveryLog:
    gateway = MakeGateway(url=settings.make_webhook_url, secret=settings.make_signing_secret)
    pipeline = LeadPipeline(
        adapter=get_crm_adapter(settings), store=InMemoryStore(),
        make_gateway=gateway, max_retries=settings.integration_max_retries,
    )
    log = await pipeline.process(lead)
    repos = get_repos(session, ctx.org_id)
    repos.save_lead(lead)
    repos.save_delivery(log)
    return log


@router.get("/deliveries", response_model=list[DeliveryLog])
async def deliveries_route(
    ctx: TenantContext = Depends(require_permission("leads:read")),
    session: Session = Depends(get_session),
) -> list[DeliveryLog]:
    return get_repos(session, ctx.org_id).list_deliveries()


@router.post("/webhooks/make")
async def make_webhook_route(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
) -> dict[str, object]:
    body = await request.body()
    headers = dict(request.headers)
    if "x-signature" in headers and "X-Signature" not in headers:
        headers["X-Signature"] = headers["x-signature"]
    event = parse_event(settings.webhook_signing_secret, headers, body)
    return {"received": True, "verified": event.verified, "type": event.type, "id": event.id}
