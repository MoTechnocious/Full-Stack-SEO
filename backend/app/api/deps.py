"""FastAPI dependencies (settings, store, fetcher, providers).

Dependencies are overridable in tests via ``app.dependency_overrides`` — e.g. a
``StaticFetcher`` is injected in place of the live ``HttpxFetcher`` for
deterministic crawl tests.
"""
from __future__ import annotations

from fastapi import Depends

from app.config import Settings, get_settings
from app.core.crawler.fetcher import Fetcher, HttpxFetcher
from app.core.keywords.providers import (
    KeywordProvider,
    SerpProvider,
    get_keyword_provider,
    get_serp_provider,
)
from app.services.store import InMemoryStore, get_store


def get_settings_dep() -> Settings:
    return get_settings()


def get_store_dep() -> InMemoryStore:
    return get_store()


def get_fetcher(settings: Settings = Depends(get_settings_dep)) -> Fetcher:
    return HttpxFetcher(
        user_agent=settings.crawler_user_agent,
        timeout=settings.crawler_timeout_seconds,
    )


def get_kw_provider(settings: Settings = Depends(get_settings_dep)) -> KeywordProvider:
    return get_keyword_provider(settings)


def get_serp_prov(settings: Settings = Depends(get_settings_dep)) -> SerpProvider:
    return get_serp_provider(settings)
