"""Keyword & SERP data providers.

Two families live here:

* ``Mock*`` — fully deterministic, offline generators used by default (and by
  every test). Every derived number/category is computed from
  :func:`hashlib.md5` digests of the keyword text, never from :mod:`random`,
  so results are stable across runs, processes, and machines.
* ``DataForSEO*`` — documented skeletons for a future live integration. They
  read credentials from :class:`~app.config.Settings` but perform no network
  I/O; every call raises ``NotImplementedError`` until a real HTTP client is
  wired in.
"""
from __future__ import annotations

import hashlib
import re
import typing

from app.config import Settings, get_settings
from app.models.common import Device, SearchIntent
from app.models.keywords import (
    Keyword,
    KeywordResearchRequest,
    SerpAnalysis,
    SerpFeature,
    SerpResultItem,
)
from app.utils.text import STOPWORDS, tokenize
from app.utils.url import registrable_domain

# --------------------------------------------------------------------------
# Protocols
# --------------------------------------------------------------------------


@typing.runtime_checkable
class KeywordProvider(typing.Protocol):
    def research(self, req: KeywordResearchRequest) -> list[Keyword]: ...


@typing.runtime_checkable
class SerpProvider(typing.Protocol):
    def fetch_serp(
        self, keyword: str, country: str = "us", device: Device = Device.DESKTOP
    ) -> SerpAnalysis: ...


# --------------------------------------------------------------------------
# Deterministic hashing helpers (hashlib-seeded, never `random`)
# --------------------------------------------------------------------------


def _hash_int(value: str, salt: str = "") -> int:
    """Stable non-negative integer derived from ``value`` (+ ``salt``) via MD5."""
    digest = hashlib.md5(f"{salt}::{value}".strip().lower().encode("utf-8")).hexdigest()
    return int(digest, 16)


def _score_phrase(phrase: str) -> tuple[int, int, float, float]:
    """Derive stable ``(search_volume, difficulty, cpc, competition)`` from a keyword string."""
    volume = 10 + (_hash_int(phrase, "volume") % 49990)  # 10 .. 49_999
    difficulty = _hash_int(phrase, "difficulty") % 101  # 0 .. 100
    cpc = round(0.10 + (_hash_int(phrase, "cpc") % 1191) / 100, 2)  # 0.10 .. 12.00
    competition = round((_hash_int(phrase, "competition") % 101) / 100, 2)  # 0.0 .. 1.0
    return volume, difficulty, cpc, competition


_TRANSACTIONAL_MARKERS: tuple[str, ...] = (
    "buy", "price", "cost", "near me", "cheap", "discount", "coupon", "deal",
    "for sale", "order",
)
_COMMERCIAL_MARKERS: tuple[str, ...] = (
    "best", "top", "review", "vs", "comparison", "alternative", "brands", "premium",
)
_INFORMATIONAL_LEADERS: tuple[str, ...] = (
    "what", "how", "why", "when", "where", "which", "who", "is", "does", "can",
)


def _infer_intent(phrase: str) -> SearchIntent:
    """Heuristic intent classifier: transactional > informational (leading word) > commercial."""
    p = phrase.lower().strip()
    if any(marker in p for marker in _TRANSACTIONAL_MARKERS):
        return SearchIntent.TRANSACTIONAL
    if p.startswith(_INFORMATIONAL_LEADERS):
        return SearchIntent.INFORMATIONAL
    if any(marker in p for marker in _COMMERCIAL_MARKERS):
        return SearchIntent.COMMERCIAL
    return SearchIntent.INFORMATIONAL


def _serp_features_for(phrase: str, intent: SearchIntent) -> list[SerpFeature]:
    """Deterministic, plausible SERP feature set for a keyword/intent pair."""
    p = phrase.lower()
    features: list[SerpFeature] = []

    if p.startswith(_INFORMATIONAL_LEADERS):
        features.append(SerpFeature.PEOPLE_ALSO_ASK)
        if _hash_int(phrase, "snippet") % 2 == 0:
            features.append(SerpFeature.FEATURED_SNIPPET)
    if "near me" in p:
        features.append(SerpFeature.LOCAL_PACK)
    if intent in (SearchIntent.COMMERCIAL, SearchIntent.TRANSACTIONAL):
        if _hash_int(phrase, "shopping") % 3 == 0:
            features.append(SerpFeature.SHOPPING)
        if _hash_int(phrase, "sitelinks") % 4 == 0:
            features.append(SerpFeature.SITELINKS)
    if _hash_int(phrase, "image") % 5 == 0:
        features.append(SerpFeature.IMAGE_PACK)
    if _hash_int(phrase, "ai_overview") % 6 == 0:
        features.append(SerpFeature.AI_OVERVIEW)
    if _hash_int(phrase, "video") % 8 == 0:
        features.append(SerpFeature.VIDEO)

    seen: set[SerpFeature] = set()
    ordered: list[SerpFeature] = []
    for f in features:
        if f not in seen:
            seen.add(f)
            ordered.append(f)
    return ordered


def compute_serp_metrics(results: list[SerpResultItem]) -> tuple[int, int, int]:
    """Aggregate ``(avg_word_count, avg_backlinks, difficulty)`` from SERP results.

    Shared by :class:`MockSerpProvider` (initial fill) and
    ``app.core.keywords.serp.analyze_serp`` (defensive recompute), so the two
    never drift apart.
    """
    word_counts = [r.word_count for r in results if r.word_count is not None]
    backlink_counts = [r.backlinks for r in results if r.backlinks is not None]
    avg_word_count = round(sum(word_counts) / len(word_counts)) if word_counts else 0
    avg_backlinks = round(sum(backlink_counts) / len(backlink_counts)) if backlink_counts else 0
    difficulty = int(max(0, min(100, round(avg_backlinks / 40))))
    return avg_word_count, avg_backlinks, difficulty


# --------------------------------------------------------------------------
# Mock keyword provider
# --------------------------------------------------------------------------

_MODIFIER_TEMPLATES: tuple[str, ...] = (
    "{s}",
    "best {s}",
    "top {s}",
    "{s} near me",
    "cheap {s}",
    "affordable {s}",
    "premium {s}",
    "{s} reviews",
    "{s} review",
    "{s} cost",
    "{s} price",
    "{s} price list",
    "buy {s}",
    "{s} for sale",
    "{s} online",
    "{s} guide",
    "{s} tips",
    "{s} ideas",
    "{s} for beginners",
    "{s} vs alternatives",
    "{s} comparison",
    "{s} brands",
    "{s} near me open now",
    "local {s}",
    "{s} deals",
    "{s} discount",
    "{s} coupon",
    "{s} 2026",
    "best {s} 2026",
    "{s} for men",
    "{s} for women",
    "{s} for kids",
    "{s} size guide",
    "{s} alternative",
    "{s} pros and cons",
    "{s} benefits",
)

_QUESTION_TEMPLATES: tuple[str, ...] = (
    "what is {s}",
    "what are {s}",
    "how to {s}",
    "how does {s} work",
    "why {s}",
    "why is {s} important",
    "when to {s}",
    "where to buy {s}",
    "where to find {s}",
    "which {s} is best",
    "who makes {s}",
    "can {s} help",
    "is {s} worth it",
    "does {s} work",
)


class MockKeywordProvider:
    """Deterministic keyword-variation generator. No network, no ``random``."""

    def research(self, req: KeywordResearchRequest) -> list[Keyword]:
        seed = req.seed.strip()
        if not seed:
            return []

        templates = list(_MODIFIER_TEMPLATES)
        if req.include_questions:
            templates += list(_QUESTION_TEMPLATES)

        seen: set[str] = set()
        phrases: list[str] = []
        for template in templates:
            if len(phrases) >= req.limit:
                break
            phrase = re.sub(r"\s+", " ", template.format(s=seed)).strip()
            key = phrase.lower()
            if key in seen:
                continue
            seen.add(key)
            phrases.append(phrase)

        # Deterministic fallback so `limit` can exceed the template pool (up to 1000).
        extra = 1
        while len(phrases) < req.limit:
            phrase = f"{seed} option {extra}"
            extra += 1
            key = phrase.lower()
            if key in seen:
                continue
            seen.add(key)
            phrases.append(phrase)

        return [self._build_keyword(phrase, seed) for phrase in phrases[: req.limit]]

    @staticmethod
    def _build_keyword(phrase: str, seed: str) -> Keyword:
        volume, difficulty, cpc, competition = _score_phrase(phrase)
        intent = _infer_intent(phrase)
        features = _serp_features_for(phrase, intent)
        return Keyword(
            keyword=phrase,
            search_volume=volume,
            difficulty=difficulty,
            cpc=cpc,
            competition=competition,
            intent=intent,
            parent_topic=seed,
            serp_features=features,
        )


# --------------------------------------------------------------------------
# Mock SERP provider
# --------------------------------------------------------------------------

_DOMAIN_ROOTS: tuple[str, ...] = (
    "guide", "hub", "expert", "today", "central", "pro", "insider", "world",
    "zone", "daily", "network", "report", "wiki", "base", "review",
)
_DOMAIN_TLDS: tuple[str, ...] = ("com", "org", "net", "io", "co")


def _topic_word(phrase: str) -> str:
    tokens = [t for t in tokenize(phrase) if t not in STOPWORDS and len(t) > 2]
    if tokens:
        return tokens[0]
    all_tokens = tokenize(phrase)
    return all_tokens[0] if all_tokens else "site"


def _slug(phrase: str) -> str:
    tokens = tokenize(phrase)
    return "-".join(tokens) if tokens else "page"


def _domain_for(keyword: str, position: int) -> str:
    h = _hash_int(keyword, f"domain-{position}")
    root = _DOMAIN_ROOTS[h % len(_DOMAIN_ROOTS)]
    tld = _DOMAIN_TLDS[(h // len(_DOMAIN_ROOTS)) % len(_DOMAIN_TLDS)]
    return f"{_topic_word(keyword)}{root}.{tld}"


class MockSerpProvider:
    """Deterministic top-10 SERP generator. No network, no ``random``."""

    def fetch_serp(
        self, keyword: str, country: str = "us", device: Device = Device.DESKTOP
    ) -> SerpAnalysis:
        intent = _infer_intent(keyword)
        slug = _slug(keyword)
        max_backlinks = 100 + (_hash_int(keyword, "competitiveness") % 60) * 100  # 100..6000

        results: list[SerpResultItem] = []
        for position in range(1, 11):
            domain = _domain_for(keyword, position)
            decay = max(0.25, 1.0 - (position - 1) * 0.075)
            noise = 0.9 + (_hash_int(keyword, f"links-{position}") % 21) / 100  # 0.90..1.10
            backlinks = max(1, round(max_backlinks * decay * noise))
            word_count = 500 + (_hash_int(keyword, f"words-{position}") % 2600)  # 500..3099
            results.append(
                SerpResultItem(
                    position=position,
                    url=f"https://{domain}/{slug}",
                    domain=registrable_domain(domain),
                    title=f"{keyword.title()} | {domain.split('.')[0].title()}",
                    snippet=(
                        f"Everything about {keyword} for {country.upper()} searchers "
                        f"on {device.value}."
                    ),
                    word_count=word_count,
                    backlinks=backlinks,
                )
            )

        features = _serp_features_for(keyword, intent)
        avg_word_count, avg_backlinks, difficulty = compute_serp_metrics(results)

        return SerpAnalysis(
            keyword=keyword,
            country=country,
            device=device,
            results=results,
            features=features,
            avg_word_count=avg_word_count,
            avg_backlinks=avg_backlinks,
            difficulty=difficulty,
        )


# --------------------------------------------------------------------------
# DataForSEO skeletons (no network; documented stubs)
# --------------------------------------------------------------------------


class DataForSEOKeywordProvider:
    """Stub adapter for the DataForSEO Keyword Data API.

    Reads ``dataforseo_login`` / ``dataforseo_password`` from
    :class:`~app.config.Settings` but performs no HTTP calls. Replace
    :meth:`research` with a real client to go live; until then it always
    raises ``NotImplementedError``.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self.login = settings.dataforseo_login
        self.password = settings.dataforseo_password

    def research(self, req: KeywordResearchRequest) -> list[Keyword]:
        raise NotImplementedError("Configure SEO_DATAFORSEO_* to enable")


class DataForSEOSerpProvider:
    """Stub adapter for the DataForSEO SERP API.

    Reads ``dataforseo_login`` / ``dataforseo_password`` from
    :class:`~app.config.Settings` but performs no HTTP calls. Replace
    :meth:`fetch_serp` with a real client to go live; until then it always
    raises ``NotImplementedError``.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self.login = settings.dataforseo_login
        self.password = settings.dataforseo_password

    def fetch_serp(
        self, keyword: str, country: str = "us", device: Device = Device.DESKTOP
    ) -> SerpAnalysis:
        raise NotImplementedError("Configure SEO_DATAFORSEO_* to enable")


# --------------------------------------------------------------------------
# Factories
# --------------------------------------------------------------------------


def get_keyword_provider(settings: Settings | None = None) -> KeywordProvider:
    settings = settings or get_settings()
    if settings.keyword_provider == "mock":
        return MockKeywordProvider()
    return DataForSEOKeywordProvider(settings=settings)


def get_serp_provider(settings: Settings | None = None) -> SerpProvider:
    settings = settings or get_settings()
    if settings.serp_provider == "mock":
        return MockSerpProvider()
    return DataForSEOSerpProvider(settings=settings)
