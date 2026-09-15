"""Outbound gateway: dispatches events to a Make.com webhook/scenario.

The HTTP transport is injected as a `Poster` callable so tests never touch the
network (see `MakeGateway.__init__`); production code falls back to a small
httpx-based poster.
"""
from __future__ import annotations

import json
import typing
import uuid
from datetime import datetime, timezone

import httpx

from app.integrations.webhooks import sign_payload
from app.models.integrations import DeliveryLog, DeliveryStatus, MakeDispatch
from app.services.store import get_store

# (url, json_payload, headers) -> (status_code, response_text)
Poster = typing.Callable[[str, dict, dict], typing.Awaitable[tuple[int, str]]]


async def _default_poster(url: str, json_payload: dict, headers: dict) -> tuple[int, str]:
    """Real (network) `Poster`: POSTs JSON to `url` with httpx. Never used in tests."""
    body = json.dumps(json_payload, default=str).encode("utf-8")
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, content=body, headers=headers)
        return response.status_code, response.text


class MakeGateway:
    """Dispatches `MakeDispatch` events to a configured Make.com webhook URL."""

    def __init__(
        self,
        *,
        url: str | None = None,
        secret: str | None = None,
        poster: Poster | None = None,
    ) -> None:
        self.url = url
        self.secret = secret
        self.poster: Poster = poster if poster is not None else _default_poster

    async def dispatch(self, event: MakeDispatch) -> DeliveryLog:
        """Send `event` to the configured webhook. Never raises.

        - No URL configured -> DeliveryLog(status=REJECTED, reason='no_webhook_url_configured').
        - 2xx response -> DELIVERED; anything else (incl. transport errors) -> FAILED.
        """
        created_at = datetime.now(timezone.utc)
        log_id = uuid.uuid4().hex

        if not self.url:
            log = DeliveryLog(
                id=log_id,
                target="make:webhook",
                status=DeliveryStatus.REJECTED,
                attempts=0,
                last_error="no_webhook_url_configured",
                created_at=created_at,
                updated_at=created_at,
            )
            get_store().save_delivery(log)
            return log

        body_dict = {
            "event": event.event,
            "data": event.data,
            "idempotency_key": event.idempotency_key,
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}

        attempts = 1
        status: DeliveryStatus
        last_error: str | None = None
        response_ref: str | None = None

        try:
            body = json.dumps(body_dict, default=str).encode("utf-8")
            if self.secret:
                headers["X-Signature"] = sign_payload(self.secret, body)

            status_code, text = await self.poster(self.url, body_dict, headers)
            response_ref = (text or "")[:500] or None

            if 200 <= status_code < 300:
                status = DeliveryStatus.DELIVERED
            else:
                status = DeliveryStatus.FAILED
                last_error = f"http_{status_code}: {(text or '')[:300]}"
        except Exception as exc:  # noqa: BLE001 - dispatch() must never raise
            status = DeliveryStatus.FAILED
            last_error = str(exc)

        log = DeliveryLog(
            id=log_id,
            target="make:webhook",
            status=status,
            attempts=attempts,
            last_error=last_error,
            created_at=created_at,
            updated_at=datetime.now(timezone.utc),
            response_ref=response_ref,
        )
        get_store().save_delivery(log)
        return log
