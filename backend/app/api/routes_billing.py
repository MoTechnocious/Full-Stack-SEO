"""Billing routes: plans, subscription, checkout, portal, webhook."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.billing.plans import PLANS, get_plan, list_plans
from app.billing.providers import get_billing_provider
from app.billing.subscriptions import ensure_subscription, set_plan
from app.config import Settings, get_settings
from app.db.session import get_session
from app.middleware.errors import BadRequestError
from app.models.common import AppModel
from app.tenancy.context import TenantContext
from app.tenancy.deps import get_tenant_context, require_permission

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutBody(AppModel):
    plan_code: str
    success_url: str = "http://localhost:3000/billing/success"
    cancel_url: str = "http://localhost:3000/billing"


def _plan(p):
    return {
        "code": p.code, "name": p.name, "price_monthly": p.price_monthly,
        "price_annual": p.price_annual, "description": p.description,
        "limits": p.limits, "features": sorted(p.features), "is_custom": p.is_custom,
    }


@router.get("/plans")
def plans():
    return [_plan(p) for p in list_plans()]


@router.get("/subscription")
def subscription(ctx: TenantContext = Depends(get_tenant_context), session: Session = Depends(get_session)):
    sub = ensure_subscription(session, ctx.org_id, ctx.plan_code)
    return {
        "plan_code": sub.plan_code, "status": sub.status, "provider": sub.provider,
        "current_period_end": sub.current_period_end, "seats": sub.seats,
        "plan": _plan(get_plan(sub.plan_code)),
    }


@router.post("/checkout")
def checkout(
    body: CheckoutBody,
    ctx: TenantContext = Depends(require_permission("billing:manage")),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    if body.plan_code not in PLANS:
        raise BadRequestError(f"Unknown plan '{body.plan_code}'.")
    provider = get_billing_provider(settings)
    cs = provider.create_checkout(ctx.org_id, body.plan_code, success_url=body.success_url, cancel_url=body.cancel_url)
    if provider.name == "mock":  # simulate an immediately-completed checkout in dev
        set_plan(session, ctx.org_id, body.plan_code, status="active", provider="mock")
    return {"checkout_url": cs.url, "provider": cs.provider, "session_id": cs.id}


@router.post("/portal")
def portal(
    ctx: TenantContext = Depends(require_permission("billing:manage")),
    settings: Settings = Depends(get_settings),
):
    provider = get_billing_provider(settings)
    return {"portal_url": provider.create_portal(ctx.org_id, return_url="http://localhost:3000/billing")}


@router.post("/webhook")
async def webhook(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    provider = get_billing_provider(settings)
    body = await request.body()
    sig = request.headers.get("Stripe-Signature") or request.headers.get("X-Signature")
    event = provider.verify_webhook(body, sig)
    etype = event.get("type", "")
    obj = (event.get("data", {}) or {}).get("object", {}) if isinstance(event, dict) else {}
    meta = obj.get("metadata", {}) if isinstance(obj, dict) else {}
    org_id = event.get("org_id") or meta.get("org_id")
    plan_code = event.get("plan_code") or meta.get("plan_code")
    if org_id and plan_code and etype in {"subscription.updated", "subscription.created", "checkout.session.completed"}:
        set_plan(session, org_id, plan_code, status=event.get("status", "active"), provider=provider.name)
    return {"received": True, "type": etype}
