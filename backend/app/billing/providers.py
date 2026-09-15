"""Billing providers (checkout / portal / webhook).

``mock`` is fully functional for local dev and tests. ``stripe`` is a real adapter
that lazily imports the SDK and requires ``SEO_STRIPE_*`` env vars — it never
imports at module load, so the app runs without the dependency installed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

from app.config import Settings, get_settings
from app.middleware.errors import ProviderError


@dataclass
class CheckoutSession:
    id: str
    url: str
    provider: str


class BillingProvider(Protocol):
    name: str

    def create_checkout(
        self, org_id: str, plan_code: str, *, success_url: str, cancel_url: str
    ) -> CheckoutSession: ...

    def create_portal(self, org_id: str, *, return_url: str) -> str: ...

    def verify_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]: ...


class MockBillingProvider:
    """Deterministic, dependency-free provider for dev/testing."""

    name = "mock"

    def create_checkout(
        self, org_id: str, plan_code: str, *, success_url: str, cancel_url: str
    ) -> CheckoutSession:
        sid = f"cs_mock_{uuid4().hex[:16]}"
        return CheckoutSession(
            id=sid,
            url=f"{success_url}?session_id={sid}&org={org_id}&plan={plan_code}&provider=mock",
            provider="mock",
        )

    def create_portal(self, org_id: str, *, return_url: str) -> str:
        return f"{return_url}?portal=mock&org={org_id}"

    def verify_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        # No signature to verify in mock mode; just parse the body.
        try:
            return json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ProviderError(f"Invalid mock webhook payload: {exc}") from exc


class StripeBillingProvider:
    """Real Stripe adapter (SDK imported lazily; requires configuration)."""

    name = "stripe"

    def __init__(self, settings: Settings):
        self.api_key = settings.stripe_api_key
        self.webhook_secret = settings.stripe_webhook_secret

    def _client(self):  # pragma: no cover - requires stripe + network
        if not self.api_key:
            raise ProviderError("Stripe is not configured (set SEO_STRIPE_API_KEY).")
        try:
            import stripe  # type: ignore
        except ImportError as exc:
            raise ProviderError("The 'stripe' package is not installed.") from exc
        stripe.api_key = self.api_key
        return stripe

    def create_checkout(  # pragma: no cover
        self, org_id: str, plan_code: str, *, success_url: str, cancel_url: str
    ) -> CheckoutSession:
        stripe = self._client()
        session = stripe.checkout.Session.create(
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=org_id,
            metadata={"org_id": org_id, "plan_code": plan_code},
            line_items=[{"price": f"price_{plan_code}", "quantity": 1}],
        )
        return CheckoutSession(id=session["id"], url=session["url"], provider="stripe")

    def create_portal(self, org_id: str, *, return_url: str) -> str:  # pragma: no cover
        stripe = self._client()
        session = stripe.billing_portal.Session.create(customer=org_id, return_url=return_url)
        return session["url"]

    def verify_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]:  # pragma: no cover
        stripe = self._client()
        if not self.webhook_secret:
            raise ProviderError("Stripe webhook secret not configured.")
        return stripe.Webhook.construct_event(payload, signature, self.webhook_secret)


def get_billing_provider(settings: Settings | None = None) -> BillingProvider:
    settings = settings or get_settings()
    if settings.billing_provider.lower() == "stripe":
        return StripeBillingProvider(settings)
    return MockBillingProvider()
