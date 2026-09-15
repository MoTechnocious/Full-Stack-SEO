"""FastAPI application factory for MySEOapp (multi-tenant SaaS)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_aeo,
    routes_aitracker,
    routes_apikeys,
    routes_assistant,
    routes_audit,
    routes_auth,
    routes_billing,
    routes_geo,
    routes_integrations,
    routes_jobs,
    routes_keywords,
    routes_local,
    routes_meta,
    routes_onpage,
    routes_orgs,
    routes_peo,
    routes_rankings,
    routes_reports,
    routes_usage,
    routes_widget,
)
from app.config import get_settings
from app.db.session import init_db
from app.logging_config import configure_logging
from app.middleware.context import RequestContextMiddleware
from app.middleware.errors import register_exception_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.version import API_VERSION, __version__

API_PREFIX = f"/api/{API_VERSION}"

_DESCRIPTION = (
    "Unified multi-tenant SEO/GEO/PEO/AEO platform — technical crawl/audit, on-page + "
    "content optimization, keyword research/mapping, SERP analysis, rank tracking, "
    "the Kit agentic assistant (action plans, guided fixes, autonomous execution "
    "queue, content calendar), Local SEO (GBP manager, citation distributor), "
    "Generative Engine Optimization (cross-LLM visibility, prompt analytics, "
    "citation/source mapping, sentiment heatmaps, AI readiness audits), Personal "
    "Entity Optimization (Knowledge Graph explorer/sensor, bio builder, "
    "corroboration mapping, entity schema), Answer Engine Optimization (PAA "
    "extraction, topic clusters, JSON-LD graphs, dynamic internal linking, voice "
    "search audits), white-label reporting, embeddable lead-gen audit widget, and "
    "CRM/Make.com integrations. Organizations, RBAC, API keys, plans, and usage "
    "quotas included. Exposed over REST + MCP."
)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Added last = outermost. Execution order: CORS -> Context -> RateLimit -> route.
    app.add_middleware(
        RateLimitMiddleware,
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        enabled=settings.rate_limit_enabled,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    )

    register_exception_handlers(app)

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    app.include_router(routes_meta.router)
    for module in (
        routes_audit,
        routes_onpage,
        routes_keywords,
        routes_rankings,
        routes_reports,
        routes_integrations,
        routes_auth,
        routes_orgs,
        routes_apikeys,
        routes_billing,
        routes_usage,
        routes_geo,
        routes_peo,
        routes_aeo,
        routes_assistant,
        routes_local,
        routes_widget,
        routes_jobs,
        routes_aitracker,
    ):
        app.include_router(module.router, prefix=API_PREFIX)

    return app


app = create_app()
