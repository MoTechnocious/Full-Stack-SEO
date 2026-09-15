"""Fixed-window in-memory rate limiter middleware.

Keyed by API key (``X-API-Key``) or client IP. Swap for Redis in production by
replacing ``_WINDOWS`` with a shared store.
"""
from __future__ import annotations

import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.models.api import ErrorResponse

_LOCK = threading.Lock()
_WINDOWS: dict[str, tuple[int, int]] = {}  # key -> (window_start_epoch, count)


def _client_key(request: Request) -> str:
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key}"
    client = request.client.host if request.client else "anonymous"
    return f"ip:{client}"


def _hit(key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
    now = int(time.time())
    window_start = now - (now % window_seconds)
    with _LOCK:
        start, count = _WINDOWS.get(key, (window_start, 0))
        if start != window_start:
            start, count = window_start, 0
        count += 1
        _WINDOWS[key] = (start, count)
    remaining = max(0, limit - count)
    reset = start + window_seconds
    return count <= limit, remaining, reset


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, limit: int = 120, window_seconds: int = 60, enabled: bool = True):
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled or request.url.path in {"/health", "/", "/version"}:
            return await call_next(request)
        allowed, remaining, reset = _hit(
            _client_key(request), self.limit, self.window_seconds
        )
        if not allowed:
            body = ErrorResponse(
                error="rate_limited",
                detail="Too many requests. Slow down.",
                request_id=getattr(request.state, "request_id", None),
            )
            resp = JSONResponse(status_code=429, content=body.model_dump())
            resp.headers["Retry-After"] = str(max(1, reset - int(time.time())))
            resp.headers["X-RateLimit-Limit"] = str(self.limit)
            resp.headers["X-RateLimit-Remaining"] = "0"
            return resp
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)
        return response


def reset_rate_limit_state() -> None:
    """Test helper to clear the in-memory window store."""
    with _LOCK:
        _WINDOWS.clear()
