"""CRM lead pipeline: push validated leads to a CRM adapter with retry + delivery logging."""
from __future__ import annotations

import typing
import uuid
from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.integrations.make_gateway import MakeGateway
from app.integrations.validation import validate_lead
from app.models.integrations import DeliveryLog, DeliveryStatus, LeadRecord, MakeDispatch
from app.services.store import InMemoryStore, get_store


class CRMAdapter(typing.Protocol):
    """Structural interface every CRM adapter (mock or real) must satisfy."""

    def push(self, lead: LeadRecord) -> str:
        """Push a lead to the CRM and return an external reference id.

        May raise on failure — `LeadPipeline` treats exceptions as retryable.
        """
        ...


class MockCRMAdapter(CRMAdapter):
    """Deterministic in-memory CRM adapter. Default adapter for tests/dev."""

    provider = "mock"

    def __init__(self) -> None:
        self.leads: dict[str, LeadRecord] = {}

    def push(self, lead: LeadRecord) -> str:
        key = lead.id or uuid.uuid4().hex
        self.leads[key] = lead
        return f"crm_{key}"


class FailingCRMAdapter(CRMAdapter):
    """Always raises. Used to exercise retry/failure handling in tests."""

    provider = "failing"

    def push(self, lead: LeadRecord) -> str:
        raise RuntimeError("simulated CRM push failure")


class HubSpotAdapter(CRMAdapter):
    """Skeleton for a real HubSpot integration. No network calls are made here."""

    provider = "hubspot"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def push(self, lead: LeadRecord) -> str:
        raise NotImplementedError(
            "HubSpotAdapter.push() is not implemented. Set SEO_CRM_API_KEY and "
            "SEO_CRM_BASE_URL in the environment and implement the HubSpot REST client "
            f"to enable this adapter (api_key_set={bool(self.settings.crm_api_key)}, "
            f"base_url_set={bool(self.settings.crm_base_url)})."
        )


class SalesforceAdapter(CRMAdapter):
    """Skeleton for a real Salesforce integration. No network calls are made here."""

    provider = "salesforce"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def push(self, lead: LeadRecord) -> str:
        raise NotImplementedError(
            "SalesforceAdapter.push() is not implemented. Set SEO_CRM_API_KEY and "
            "SEO_CRM_BASE_URL in the environment and implement the Salesforce REST/Bulk "
            f"API client to enable this adapter (api_key_set={bool(self.settings.crm_api_key)}, "
            f"base_url_set={bool(self.settings.crm_base_url)})."
        )


def get_crm_adapter(settings: Settings | None = None) -> CRMAdapter:
    """Return the configured CRM adapter. Defaults to the mock adapter."""
    settings = settings or get_settings()
    provider = (settings.crm_provider or "mock").strip().lower()
    if provider == "hubspot":
        return HubSpotAdapter(settings)
    if provider == "salesforce":
        return SalesforceAdapter(settings)
    return MockCRMAdapter()


class LeadPipeline:
    """Validates a lead, pushes it to a CRM (with retries), and logs delivery state.

    On successful CRM delivery, best-effort mirrors the event to Make.com via an
    optional `MakeGateway` — a Make.com failure never flips the lead's own
    delivery status away from DELIVERED.
    """

    def __init__(
        self,
        *,
        adapter: CRMAdapter | None = None,
        store: InMemoryStore | None = None,
        make_gateway: MakeGateway | None = None,
        max_retries: int = 3,
    ) -> None:
        self.adapter = adapter or get_crm_adapter()
        self.store = store or get_store()
        self.make_gateway = make_gateway
        self.max_retries = max_retries

    def _target(self) -> str:
        provider = getattr(self.adapter, "provider", None) or type(self.adapter).__name__.lower()
        return f"crm:{provider}"

    async def process(self, lead: LeadRecord) -> DeliveryLog:
        """Validate -> persist -> push (with retries) -> log. Never raises."""
        created_at = datetime.now(timezone.utc)
        result = validate_lead(lead)

        if not result.valid:
            log = DeliveryLog(
                id=uuid.uuid4().hex,
                target=self._target(),
                lead_id=(result.normalized.id if result.normalized else lead.id),
                status=DeliveryStatus.REJECTED,
                attempts=0,
                last_error="; ".join(result.errors) or "invalid_lead",
                created_at=created_at,
                updated_at=created_at,
            )
            self.store.save_delivery(log)
            return log

        # `validate_lead` always returns a normalized record when errors is empty.
        normalized_lead = typing.cast(LeadRecord, result.normalized)
        self.store.save_lead(normalized_lead)

        status = DeliveryStatus.VALIDATED
        attempts = 0
        last_error: str | None = None
        response_ref: str | None = None

        for attempt in range(1, self.max_retries + 1):
            attempts = attempt
            status = DeliveryStatus.SENT
            try:
                response_ref = self.adapter.push(normalized_lead)
                status = DeliveryStatus.DELIVERED
                last_error = None
                break
            except Exception as exc:  # noqa: BLE001 - adapter failures are retryable
                last_error = str(exc)
                status = DeliveryStatus.FAILED
                continue

        log = DeliveryLog(
            id=uuid.uuid4().hex,
            target=self._target(),
            lead_id=normalized_lead.id,
            status=status,
            attempts=attempts,
            last_error=last_error,
            created_at=created_at,
            updated_at=datetime.now(timezone.utc),
            response_ref=response_ref,
        )

        if status == DeliveryStatus.DELIVERED and self.make_gateway is not None:
            try:
                await self.make_gateway.dispatch(
                    MakeDispatch(
                        event="lead.delivered",
                        data=normalized_lead.model_dump(mode="json"),
                        idempotency_key=normalized_lead.id,
                    )
                )
            except Exception:  # noqa: BLE001 - best-effort; must not affect lead status
                pass

        self.store.save_delivery(log)
        return log
