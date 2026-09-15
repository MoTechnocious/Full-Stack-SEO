"""Tests for the integrations layer: validation, webhooks, Make.com gateway, CRM pipeline.

No live network: MakeGateway is always constructed with a fake in-process `poster`,
and CRM pushes go through `MockCRMAdapter`/`FailingCRMAdapter` — never real HTTP.
"""
from __future__ import annotations

import json

import pytest

from app.config import Settings
from app.integrations.crm_pipeline import (
    FailingCRMAdapter,
    HubSpotAdapter,
    LeadPipeline,
    MockCRMAdapter,
    get_crm_adapter,
)
from app.integrations.make_gateway import MakeGateway
from app.integrations.validation import validate_lead
from app.integrations.webhooks import parse_event, sign_payload, verify_signature
from app.models.integrations import DeliveryStatus, LeadRecord, MakeDispatch
from app.services.store import InMemoryStore

# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------


def test_validate_lead_valid_lead_is_normalized_with_id_and_created_at():
    lead = LeadRecord(name="Ada Lovelace", email="ada@example.com", company="Analytical Engines")

    result = validate_lead(lead)

    assert result.valid is True
    assert result.errors == []
    assert result.normalized is not None
    assert result.normalized.id  # uuid4 hex assigned
    assert result.normalized.created_at is not None
    assert "company is missing" not in result.warnings


def test_validate_lead_bad_email_fails_with_error():
    lead = LeadRecord(name="Bob", email="not-an-email")

    result = validate_lead(lead)

    assert result.valid is False
    assert any("email" in err.lower() for err in result.errors)


def test_validate_lead_missing_name_fails_with_error():
    lead = LeadRecord(name="   ", email="a@b.com")

    result = validate_lead(lead)

    assert result.valid is False
    assert any("name" in err.lower() for err in result.errors)


def test_validate_lead_website_without_scheme_gets_https_prefix():
    lead = LeadRecord(name="Grace Hopper", email="grace@example.com", website="example.com")

    result = validate_lead(lead)

    assert result.normalized is not None
    assert result.normalized.website == "https://example.com"


def test_validate_lead_website_with_scheme_is_untouched():
    lead = LeadRecord(name="Grace Hopper", email="grace@example.com", website="http://example.com")

    result = validate_lead(lead)

    assert result.normalized.website == "http://example.com"


def test_validate_lead_phone_normalized_and_missing_company_warns():
    lead = LeadRecord(name="Jane", email="jane@example.com", phone="+1 (555) 123-4567")

    result = validate_lead(lead)

    assert result.normalized.phone == "+15551234567"
    assert any("company" in w.lower() for w in result.warnings)


def test_validate_lead_never_raises_on_garbage_input():
    lead = LeadRecord(name="", email="", phone="???", website="")

    result = validate_lead(lead)  # must not raise

    assert result.valid is False
    assert len(result.errors) >= 2  # name + email both missing


# ---------------------------------------------------------------------------
# webhooks
# ---------------------------------------------------------------------------


def test_sign_and_verify_signature_round_trip():
    secret = "topsecret"
    body = b'{"type":"lead.created","id":"abc"}'

    signature = sign_payload(secret, body)

    assert verify_signature(secret, body, signature) is True


def test_verify_signature_rejects_tampered_payload():
    secret = "topsecret"
    body = b'{"type":"lead.created","id":"abc"}'
    signature = sign_payload(secret, body)
    tampered = body.replace(b"abc", b"xyz")

    assert verify_signature(secret, tampered, signature) is False


def test_verify_signature_false_on_empty_or_missing_signature():
    secret = "topsecret"
    body = b"{}"

    assert verify_signature(secret, body, "") is False
    assert verify_signature(secret, body, None) is False  # type: ignore[arg-type]


def test_parse_event_with_correct_signature_is_verified_and_typed():
    secret = "topsecret"
    payload = {"type": "lead.created", "lead_id": "abc123"}
    body = json.dumps(payload).encode("utf-8")
    signature = sign_payload(secret, body)
    headers = {"X-Signature": signature}

    event = parse_event(secret, headers, body)

    assert event.verified is True
    assert event.type == "lead.created"
    assert event.payload.get("lead_id") == "abc123"
    assert event.id


def test_parse_event_bad_signature_is_unverified_and_does_not_raise():
    secret = "topsecret"
    body = json.dumps({"type": "ping"}).encode("utf-8")
    headers = {"X-Signature": "deadbeef"}

    event = parse_event(secret, headers, body)  # must not raise

    assert event.verified is False
    assert event.type == "ping"


def test_parse_event_malformed_json_does_not_raise():
    secret = "topsecret"
    body = b"not-json{{{"
    signature = sign_payload(secret, body)
    headers = {"X-Signature": signature}

    event = parse_event(secret, headers, body)  # must not raise

    assert event.verified is True  # signature over the raw bytes is still valid
    assert event.type == "unknown"
    assert event.payload == {}


# ---------------------------------------------------------------------------
# MakeGateway
# ---------------------------------------------------------------------------


async def test_make_gateway_dispatch_delivered_with_signature_header_when_secret_set():
    captured: dict[str, object] = {}

    async def fake_poster(url: str, json_payload: dict, headers: dict) -> tuple[int, str]:
        captured["url"] = url
        captured["headers"] = headers
        captured["json_payload"] = json_payload
        return 200, "ok"

    gateway = MakeGateway(url="https://hooks.example.com/abc", secret="shhh", poster=fake_poster)

    log = await gateway.dispatch(MakeDispatch(event="lead.created", data={"a": 1}))

    assert log.status == DeliveryStatus.DELIVERED
    assert log.attempts == 1
    headers = captured["headers"]
    assert isinstance(headers, dict) and "X-Signature" in headers


async def test_make_gateway_dispatch_no_signature_header_when_secret_missing():
    captured: dict[str, object] = {}

    async def fake_poster(url: str, json_payload: dict, headers: dict) -> tuple[int, str]:
        captured["headers"] = headers
        return 200, "ok"

    gateway = MakeGateway(url="https://hooks.example.com/abc", poster=fake_poster)

    log = await gateway.dispatch(MakeDispatch(event="lead.created", data={}))

    assert log.status == DeliveryStatus.DELIVERED
    assert "X-Signature" not in captured["headers"]


async def test_make_gateway_dispatch_rejected_when_no_url_configured():
    calls = 0

    async def fake_poster(url: str, json_payload: dict, headers: dict) -> tuple[int, str]:
        nonlocal calls
        calls += 1
        return 200, "ok"

    gateway = MakeGateway(url=None, poster=fake_poster)

    log = await gateway.dispatch(MakeDispatch(event="lead.created", data={}))

    assert log.status == DeliveryStatus.REJECTED
    assert log.last_error == "no_webhook_url_configured"
    assert calls == 0  # poster must never be called without a URL


async def test_make_gateway_dispatch_failed_on_non_2xx_response():
    async def fake_poster(url: str, json_payload: dict, headers: dict) -> tuple[int, str]:
        return 500, "server error"

    gateway = MakeGateway(url="https://hooks.example.com/abc", poster=fake_poster)

    log = await gateway.dispatch(MakeDispatch(event="lead.created", data={}))

    assert log.status == DeliveryStatus.FAILED
    assert log.last_error is not None


async def test_make_gateway_dispatch_failed_when_poster_raises():
    async def broken_poster(url: str, json_payload: dict, headers: dict) -> tuple[int, str]:
        raise ConnectionError("network unreachable")

    gateway = MakeGateway(url="https://hooks.example.com/abc", poster=broken_poster)

    log = await gateway.dispatch(MakeDispatch(event="lead.created", data={}))  # must not raise

    assert log.status == DeliveryStatus.FAILED
    assert "network unreachable" in (log.last_error or "")


# ---------------------------------------------------------------------------
# CRM pipeline
# ---------------------------------------------------------------------------


async def test_lead_pipeline_delivers_and_persists_lead_and_delivery_with_mock_adapter():
    store = InMemoryStore()
    pipeline = LeadPipeline(adapter=MockCRMAdapter(), store=store)
    lead = LeadRecord(name="Ada", email="ada@example.com", company="Engines Inc")

    log = await pipeline.process(lead)

    assert log.status == DeliveryStatus.DELIVERED
    assert log.attempts == 1
    assert log.response_ref == f"crm_{log.lead_id}"
    assert store.get_lead(log.lead_id) is not None
    assert any(d.id == log.id for d in store.list_deliveries())


async def test_lead_pipeline_fails_after_max_retries_with_failing_adapter():
    store = InMemoryStore()
    pipeline = LeadPipeline(adapter=FailingCRMAdapter(), store=store, max_retries=3)
    lead = LeadRecord(name="Bob", email="bob@example.com")

    log = await pipeline.process(lead)

    assert log.status == DeliveryStatus.FAILED
    assert log.attempts == 3
    assert log.last_error and "simulated CRM push failure" in log.last_error
    assert store.get_lead(log.lead_id) is not None  # lead itself was still persisted


async def test_lead_pipeline_rejects_invalid_lead_without_calling_adapter():
    store = InMemoryStore()

    class ExplodingAdapter:
        provider = "exploding"

        def push(self, lead: LeadRecord) -> str:
            raise AssertionError("adapter.push must not be called for an invalid lead")

    pipeline = LeadPipeline(adapter=ExplodingAdapter(), store=store)
    lead = LeadRecord(name="", email="bad-email")

    log = await pipeline.process(lead)

    assert log.status == DeliveryStatus.REJECTED
    assert log.attempts == 0
    assert log.last_error


async def test_lead_pipeline_dispatches_to_make_gateway_on_delivery_best_effort():
    store = InMemoryStore()
    calls: list[dict] = []

    async def failing_poster(url: str, json_payload: dict, headers: dict) -> tuple[int, str]:
        calls.append(json_payload)
        raise RuntimeError("make.com unreachable")

    gateway = MakeGateway(url="https://hooks.example.com/x", poster=failing_poster)
    pipeline = LeadPipeline(adapter=MockCRMAdapter(), store=store, make_gateway=gateway)
    lead = LeadRecord(name="Ada", email="ada@example.com")

    log = await pipeline.process(lead)

    # Make.com dispatch failure must never flip the lead's own delivery status.
    assert log.status == DeliveryStatus.DELIVERED
    assert len(calls) == 1
    assert calls[0]["event"] == "lead.delivered"


def test_get_crm_adapter_defaults_to_mock_and_selects_by_provider():
    assert isinstance(get_crm_adapter(Settings(crm_provider="mock")), MockCRMAdapter)
    assert isinstance(get_crm_adapter(Settings(crm_provider="hubspot")), HubSpotAdapter)
    assert isinstance(get_crm_adapter(Settings(crm_provider="unknown-provider")), MockCRMAdapter)


def test_hubspot_adapter_push_raises_not_implemented_with_env_hint():
    adapter = HubSpotAdapter(Settings(crm_provider="hubspot"))

    with pytest.raises(NotImplementedError, match="SEO_CRM_API_KEY"):
        adapter.push(LeadRecord(name="X", email="x@example.com"))
