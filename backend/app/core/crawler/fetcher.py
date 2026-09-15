"""HTTP fetching abstractions for the crawler.

Two implementations are provided:

- :class:`HttpxFetcher` — a real async fetcher backed by httpx, used in production.
- :class:`StaticFetcher` — a deterministic in-memory fetcher used in tests. It never
  touches the network, which keeps the test suite fast and 100% reproducible.

Both implement the :class:`Fetcher` protocol so the rest of the crawler (analyzers,
engine) can depend on the abstraction rather than a concrete transport.
"""
from __future__ import annotations

import time
import typing
from dataclasses import dataclass, field

import httpx

from app.models.audit import RedirectHop


@dataclass
class FetchResponse:
    """The raw result of fetching a single URL, before any HTML analysis."""

    url: str
    final_url: str
    status_code: int
    headers: dict[str, str]
    text: str
    elapsed_ms: int
    content_type: str = ""
    redirect_chain: list[RedirectHop] = field(default_factory=list)
    error: str | None = None


@typing.runtime_checkable
class Fetcher(typing.Protocol):
    """Minimal async fetch contract implemented by all fetcher backends."""

    async def fetch(self, url: str) -> FetchResponse: ...


def _content_type_from_headers(headers: httpx.Headers) -> str:
    raw = headers.get("content-type", "")
    return raw.split(";")[0].strip()


class HttpxFetcher:
    """Real async HTTP fetcher backed by httpx.

    Follows redirects transparently and records each hop into ``redirect_chain``.
    Never raises: any transport-level failure (DNS, timeout, connection refused,
    too many redirects, ...) is captured and returned as a ``FetchResponse`` with
    ``status_code=0`` and ``error`` set, so callers never need to wrap ``fetch`` in
    a try/except.
    """

    def __init__(self, *, user_agent: str, timeout: float = 15.0, max_redirects: int = 10) -> None:
        self._user_agent = user_agent
        self._timeout = timeout
        self._max_redirects = max_redirects

    async def fetch(self, url: str) -> FetchResponse:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                max_redirects=self._max_redirects,
                timeout=self._timeout,
                headers={"User-Agent": self._user_agent},
            ) as client:
                response = await client.get(url)
        except Exception as exc:  # noqa: BLE001 - any fetch failure becomes a FetchResponse
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return FetchResponse(
                url=url,
                final_url=url,
                status_code=0,
                headers={},
                text="",
                elapsed_ms=elapsed_ms,
                content_type="",
                redirect_chain=[],
                error=str(exc),
            )

        elapsed_ms = int((time.monotonic() - start) * 1000)
        redirect_chain = [
            RedirectHop(
                url=str(hop.url),
                status_code=hop.status_code,
                location=hop.headers.get("location"),
            )
            for hop in response.history
        ]
        return FetchResponse(
            url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            headers=dict(response.headers),
            text=response.text,
            elapsed_ms=elapsed_ms,
            content_type=_content_type_from_headers(response.headers),
            redirect_chain=redirect_chain,
            error=None,
        )


class StaticFetcher:
    """Deterministic in-memory fetcher used by tests. No network I/O.

    ``pages`` maps a URL (exact string match, callers should pass normalized URLs)
    to a dict describing the fake response:

    - ``status`` (int, default 200)
    - ``html`` (str, default "")
    - ``headers`` (dict[str, str], default {})
    - ``redirect_to`` (str): simulates a single redirect hop to another key in ``pages``
    - ``content_type`` (str, default "text/html")

    A URL missing from ``pages`` resolves to a 404 response (mirrors a real site
    returning "not found" for an unknown path) so tests can exercise broken-link
    handling without listing every 404 explicitly.
    """

    def __init__(self, pages: dict[str, dict]) -> None:
        self._pages = pages

    async def fetch(self, url: str) -> FetchResponse:
        redirect_chain: list[RedirectHop] = []
        current_url = url
        entry = self._pages.get(current_url)

        if entry is not None and entry.get("redirect_to"):
            target = str(entry["redirect_to"])
            redirect_chain.append(
                RedirectHop(
                    url=current_url,
                    status_code=int(entry.get("status", 301)),
                    location=target,
                )
            )
            current_url = target
            entry = self._pages.get(current_url)

        if entry is None:
            return FetchResponse(
                url=url,
                final_url=current_url,
                status_code=404,
                headers={},
                text="",
                elapsed_ms=0,
                content_type="text/html",
                redirect_chain=redirect_chain,
                error=None,
            )

        headers = dict(entry.get("headers", {}))
        content_type = str(entry.get("content_type") or headers.get("content-type", "text/html"))
        return FetchResponse(
            url=url,
            final_url=current_url,
            status_code=int(entry.get("status", 200)),
            headers=headers,
            text=str(entry.get("html", "")),
            elapsed_ms=0,
            content_type=content_type,
            redirect_chain=redirect_chain,
            error=None,
        )
