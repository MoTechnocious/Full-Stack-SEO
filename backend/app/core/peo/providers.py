"""PEO data providers: Knowledge Graph search + source-profile fetching.

Two families live here, mirroring ``app.core.keywords.providers``:

* ``Mock*`` — fully deterministic, offline generators used by default (and by
  every test). Every derived number/category is computed from
  :func:`hashlib.md5` digests of the input text, never from :mod:`random`,
  so results are stable across runs, processes, and machines.
* ``Google*`` / live skeletons — documented stubs for future integrations.
  They read (optional) credentials from :class:`~app.config.Settings` via
  ``getattr`` but perform no network I/O; every call raises
  ``NotImplementedError`` until a real HTTP client is wired in.
"""
from __future__ import annotations

import hashlib
import typing
from datetime import date, timedelta

from app.config import Settings, get_settings
from app.models.peo import KGEntity, SensorObservation, SourceProfile, SourceType
from app.utils.text import tokenize

# --------------------------------------------------------------------------
# Protocols
# --------------------------------------------------------------------------


@typing.runtime_checkable
class KnowledgeGraphProvider(typing.Protocol):
    def search_entities(
        self, query: str, limit: int = 10, types: list[str] | None = None
    ) -> list[KGEntity]: ...

    def confidence_series(self, kg_mid: str, points: int = 12) -> list[SensorObservation]: ...


@typing.runtime_checkable
class ProfileFetcher(typing.Protocol):
    def fetch_profile(self, source: SourceType, entity_name: str) -> SourceProfile: ...


# --------------------------------------------------------------------------
# Deterministic hashing helpers (hashlib-seeded, never `random`)
# --------------------------------------------------------------------------


def _hash_int(value: str, salt: str = "") -> int:
    """Stable non-negative integer derived from ``value`` (+ ``salt``) via MD5."""
    digest = hashlib.md5(f"{salt}::{value}".strip().lower().encode("utf-8")).hexdigest()
    return int(digest, 16)


def _slug(text: str) -> str:
    tokens = tokenize(text)
    return "-".join(tokens) if tokens else "entity"


# --------------------------------------------------------------------------
# Mock Knowledge Graph provider (Google KG Search API shape)
# --------------------------------------------------------------------------

_TYPE_POOL: tuple[tuple[str, ...], ...] = (
    ("Person",),
    ("Person", "Thing"),
    ("Organization",),
    ("Organization", "Corporation"),
    ("Thing",),
)

_NAME_TEMPLATES: tuple[str, ...] = (
    "{n}",
    "{n} Inc.",
    "{n} Foundation",
    "{n} Group",
    "Dr. {n}",
    "{n} (musician)",
    "{n} Media",
    "{n} Labs",
    "{n} Institute",
    "{n} Jr.",
)

# Sensor series shape: weekly observations starting from a fixed anchor date.
_SERIES_ANCHOR = date(2026, 1, 5)


class MockKnowledgeGraphProvider:
    """Deterministic Google KG Search API stand-in. No network, no ``random``."""

    def search_entities(
        self, query: str, limit: int = 10, types: list[str] | None = None
    ) -> list[KGEntity]:
        query = query.strip()
        if not query:
            return []
        base_name = query.title()
        base_score = 400 + _hash_int(query, "kg-score") % 1100  # 400 .. 1499

        entities: list[KGEntity] = []
        for rank, template in enumerate(_NAME_TEMPLATES):
            if len(entities) >= limit:
                break
            name = template.format(n=base_name)
            entity_types = list(_TYPE_POOL[(_hash_int(name, "kg-types") + rank) % len(_TYPE_POOL)])
            if types and not set(entity_types) & set(types):
                continue
            kg_mid = f"/g/{hashlib.md5(name.lower().encode('utf-8')).hexdigest()[:10]}"
            kind = "organization" if "Organization" in entity_types else (
                "person" if "Person" in entity_types else "topic"
            )
            url = (
                f"https://en.wikipedia.org/wiki/{name.replace(' ', '_')}"
                if _hash_int(name, "kg-url") % 2 == 0
                else None
            )
            entities.append(
                KGEntity(
                    kg_mid=kg_mid,
                    name=name,
                    types=entity_types,
                    description=f"{name} is a {kind} associated with {query}.",
                    result_score=round(base_score * max(0.15, 1.0 - rank * 0.09), 2),
                    url=url,
                )
            )
        return entities

    def confidence_series(self, kg_mid: str, points: int = 12) -> list[SensorObservation]:
        """Weekly confidence readings for ``kg_mid``: base level + drift + jitter."""
        base = 100 + _hash_int(kg_mid, "kg-base") % 900          # 100 .. 999
        drift = ((_hash_int(kg_mid, "kg-drift") % 3) - 1) * 0.015  # -1.5% / 0 / +1.5% per step
        observations: list[SensorObservation] = []
        for i in range(max(0, points)):
            jitter = ((_hash_int(kg_mid, f"kg-obs-{i}") % 61) - 30) / 1000  # -3.0% .. +3.0%
            score = round(base * (1 + drift * i + jitter), 2)
            observed_at = (_SERIES_ANCHOR + timedelta(weeks=i)).isoformat()
            observations.append(SensorObservation(observed_at=observed_at, score=score))
        return observations


class GoogleKnowledgeGraphProvider:
    """Stub adapter for the live Google Knowledge Graph Search API.

    Reads an optional ``google_kg_api_key`` from :class:`~app.config.Settings`
    (via ``getattr``, so no config changes are required) but performs no HTTP
    calls. Replace the two methods with a real client to go live; until then
    every call raises ``NotImplementedError``.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self.api_key = getattr(settings, "google_kg_api_key", None)

    def search_entities(
        self, query: str, limit: int = 10, types: list[str] | None = None
    ) -> list[KGEntity]:
        raise NotImplementedError("Configure SEO_GOOGLE_KG_API_KEY to enable")

    def confidence_series(self, kg_mid: str, points: int = 12) -> list[SensorObservation]:
        raise NotImplementedError("Configure SEO_GOOGLE_KG_API_KEY to enable")


# --------------------------------------------------------------------------
# Mock source-profile fetcher (corroboration inputs)
# --------------------------------------------------------------------------

_JOB_TITLES: tuple[str, ...] = (
    "Chief Executive Officer", "Founder", "Software Engineer", "Author", "Consultant",
)
_EMPLOYER_SUFFIXES: tuple[str, ...] = ("Ventures", "Labs", "Media", "Consulting", "Group")

_SOURCE_URL_TEMPLATES: dict[SourceType, str] = {
    SourceType.WIKIPEDIA: "https://en.wikipedia.org/wiki/{slug}",
    SourceType.WIKIDATA: "https://www.wikidata.org/wiki/Q{qid}",
    SourceType.CRUNCHBASE: "https://www.crunchbase.com/person/{slug}",
    SourceType.LINKEDIN: "https://www.linkedin.com/in/{slug}",
    SourceType.OWN_SITE: "https://{slug}.com/about",
}


class MockProfileFetcher:
    """Deterministic source-profile generator. No network, no ``random``.

    Facts are hashed per ``(source, entity_name)`` pair, so different sources
    naturally disagree on some facts — which is exactly what the corroboration
    auditor is designed to surface.
    """

    def fetch_profile(self, source: SourceType, entity_name: str) -> SourceProfile:
        entity_name = entity_name.strip()
        seed = f"{source.value}|{entity_name}"
        slug = _slug(entity_name)
        first = entity_name.split()[0].title() if entity_name else "Entity"

        facts: dict[str, str] = {
            "name": entity_name,
            "job_title": _JOB_TITLES[_hash_int(seed, "job") % len(_JOB_TITLES)],
            "employer": f"{first} {_EMPLOYER_SUFFIXES[_hash_int(seed, 'employer') % len(_EMPLOYER_SUFFIXES)]}",
            "website": f"https://{slug}.com",
        }
        url = _SOURCE_URL_TEMPLATES[source].format(
            slug=slug, qid=_hash_int(entity_name, "qid") % 10_000_000
        )
        return SourceProfile(source=source, url=url, facts=facts)


class LiveProfileFetcher:
    """Stub adapter for live profile scraping/API lookups (Wikipedia, LinkedIn, ...).

    Documented skeleton only — every call raises ``NotImplementedError`` until
    a real HTTP client is wired in.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def fetch_profile(self, source: SourceType, entity_name: str) -> SourceProfile:
        raise NotImplementedError("Live profile fetching is not configured")


# --------------------------------------------------------------------------
# Factories
# --------------------------------------------------------------------------


def get_kg_provider(settings: Settings | None = None) -> KnowledgeGraphProvider:
    settings = settings or get_settings()
    if getattr(settings, "kg_provider", "mock") == "mock":
        return MockKnowledgeGraphProvider()
    return GoogleKnowledgeGraphProvider(settings=settings)


def get_profile_fetcher(settings: Settings | None = None) -> ProfileFetcher:
    settings = settings or get_settings()
    if getattr(settings, "profile_fetcher_provider", "mock") == "mock":
        return MockProfileFetcher()
    return LiveProfileFetcher(settings=settings)
