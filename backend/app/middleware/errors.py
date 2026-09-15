"""Domain exceptions + FastAPI exception handlers returning typed error envelopes."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.logging_config import get_logger
from app.models.api import ErrorDetail, ErrorResponse

logger = get_logger("errors")


class AppError(Exception):
    """Base application error with an HTTP status and machine-readable code."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"


class ValidationFailedError(AppError):
    status_code = 422
    code = "validation_failed"


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"


class ProviderError(AppError):
    status_code = 502
    code = "provider_error"


class NotAuthenticatedError(AppError):
    status_code = 401
    code = "not_authenticated"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class QuotaExceededError(AppError):
    status_code = 402
    code = "quota_exceeded"


class FeatureNotAvailableError(AppError):
    status_code = 402
    code = "feature_not_available"


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        body = ErrorResponse(error=exc.code, detail=exc.message, request_id=_request_id(request))
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            ErrorDetail(
                code="invalid",
                message=err.get("msg", "invalid"),
                field=".".join(str(p) for p in err.get("loc", [])),
            )
            for err in exc.errors()
        ]
        body = ErrorResponse(
            error="validation_failed",
            detail="Request validation failed.",
            request_id=_request_id(request),
            errors=details,
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", extra={"path": str(request.url), "error": str(exc)})
        body = ErrorResponse(
            error="internal_error",
            detail="An unexpected error occurred.",
            request_id=_request_id(request),
        )
        return JSONResponse(status_code=500, content=body.model_dump())
