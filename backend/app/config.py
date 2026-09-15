"""Application configuration.

All settings are strictly typed and sourced from environment variables using the
``SEO_`` prefix (e.g. ``SEO_LOG_LEVEL``). Never hardcode secrets — see ``.env.template``.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from the environment / ``.env`` file."""

    model_config = SettingsConfigDict(
        env_prefix="SEO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- App ----
    app_name: str = "MySEOapp API"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    log_json: bool = True
    cors_allow_origins: list[str] = ["*"]

    # ---- Crawler ----
    crawler_user_agent: str = "MySEOappBot/0.1 (+https://scalingfirm.com/bot)"
    crawler_max_pages: int = 500
    crawler_max_depth: int = 10
    crawler_max_concurrency: int = 10
    crawler_timeout_seconds: float = 15.0
    crawler_respect_robots: bool = True

    # ---- Rate limiting (per client key / IP) ----
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    # ---- Providers (pluggable: "mock" | real adapter name) ----
    keyword_provider: str = "mock"
    serp_provider: str = "mock"
    dataforseo_login: str | None = None
    dataforseo_password: str | None = None
    google_api_key: str | None = None
    gsc_credentials_json: str | None = None

    # ---- Integrations ----
    make_webhook_url: str | None = None
    make_signing_secret: str | None = None
    webhook_signing_secret: str = "change-me-in-env"
    crm_provider: str = "mock"
    crm_api_key: str | None = None
    crm_base_url: str | None = None
    integration_max_retries: int = 3

    # ---- Database ----
    database_url: str = "sqlite:///./myseoapp.db"
    db_echo: bool = False

    # ---- Auth / Identity (delegated IdP + app-owned RBAC) ----
    idp_provider: str = "dev"  # "dev" | "clerk" | "supabase" | "auth0"
    jwt_secret: str = "change-me-in-env-super-secret"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 60
    idp_jwks_url: str | None = None
    idp_issuer: str | None = None
    idp_audience: str | None = None
    api_key_prefix: str = "msk"

    # ---- GEO (Generative Engine Optimization) ----
    answer_engine_provider: str = "mock"  # "mock" | "live"
    geo_artifact_fetcher: str = "mock"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    perplexity_api_key: str | None = None

    # ---- PEO / AEO ----
    kg_provider: str = "mock"  # "mock" | "google"
    google_kg_api_key: str | None = None
    profile_fetcher_provider: str = "mock"
    serp_question_provider: str = "mock"

    # ---- Kit assistant / Local SEO / Widget ----
    content_generator_provider: str = "mock"
    cms_provider: str = "mock"
    gbp_provider: str = "mock"
    directory_provider: str = "mock"
    assistant_max_attempts: int = 3
    assistant_approval_required_default: bool = False
    widget_allowed_origins: list[str] = ["*"]
    widget_default_org_slug: str = "default"

    # ---- Billing ----
    billing_provider: str = "mock"  # "mock" | "stripe"
    stripe_api_key: str | None = None
    stripe_webhook_secret: str | None = None
    default_plan_code: str = "free"
    billing_trial_days: int = 14

    # ---- Background jobs ----
    job_queue_backend: str = "thread"  # "inline" | "thread" | "celery" | "rq"
    job_queue_workers: int = 4
    job_max_attempts: int = 2

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""
    return Settings()
