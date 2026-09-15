"""Answer-engine and site-artifact providers for the GEO module.

Two families live here, mirroring ``app.core.keywords.providers``:

* ``Mock*`` — fully deterministic, offline generators used by default (and by
  every test). Every synthesized answer, ranked list, citation, and artifact is
  computed from :func:`hashlib.md5` digests of the inputs, never from
  :mod:`random`, so results are stable across runs, processes, and machines.
* ``Live*`` — documented skeletons for future real integrations (OpenAI,
  Anthropic, Perplexity, ... APIs and a real HTTP artifact fetcher). They read
  credentials from :class:`~app.config.Settings` but perform no network I/O;
  every call raises ``NotImplementedError`` until a real client is wired in.
"""
from __future__ import annotations

import hashlib
import typing

from app.config import Settings, get_settings
from app.models.geo import AnswerEngine, Citation, EngineAnswer, SiteArtifacts
from app.utils.text import STOPWORDS, tokenize

# --------------------------------------------------------------------------
# Protocols
# --------------------------------------------------------------------------


@typing.runtime_checkable
class AnswerEngineProvider(typing.Protocol):
    """Queries a generative answer engine about a brand for one prompt."""

    def ask(
        self,
        engine: AnswerEngine,
        prompt: str,
        brand: str,
        competitors: list[str] | None = None,
    ) -> EngineAnswer: ...


@typing.runtime_checkable
class ArtifactFetcher(typing.Protocol):
    """Fetches the site artifacts an AI-readiness audit inspects."""

    def fetch_site(self, base_url: str) -> SiteArtifacts: ...


# --------------------------------------------------------------------------
# Deterministic hashing helpers (hashlib-seeded, never `random`)
# --------------------------------------------------------------------------


def _hash_int(value: str, salt: str = "") -> int:
    """Stable non-negative integer derived from ``value`` (+ ``salt``) via MD5."""
    digest = hashlib.md5(f"{salt}::{value}".strip().lower().encode("utf-8")).hexdigest()
    return int(digest, 16)


def _topic_word(phrase: str) -> str:
    tokens = [t for t in tokenize(phrase) if t not in STOPWORDS and len(t) > 2]
    if tokens:
        return tokens[0]
    all_tokens = tokenize(phrase)
    return all_tokens[0] if all_tokens else "topic"


def brand_slug(brand: str) -> str:
    """Lowercase dashless slug for a brand name (used to derive its own domain)."""
    return "".join(tokenize(brand)) or "brand"


# --------------------------------------------------------------------------
# Mock answer-engine provider
# --------------------------------------------------------------------------

_CITATION_POOL: tuple[tuple[str, str], ...] = (
    ("reddit.com", "r/{topic} discussion thread"),
    ("wikipedia.org", "{topic} - Wikipedia"),
    ("g2.com", "Best {topic} software reviews | G2"),
    ("quora.com", "What is the best {topic}? - Quora"),
    ("techcrunch.com", "The state of {topic} in 2026"),
    ("forbes.com", "Top {topic} picks according to experts"),
    ("medium.com", "A deep dive into {topic}"),
    ("capterra.com", "{topic} tools compared | Capterra"),
    ("trustpilot.com", "{topic} customer reviews | Trustpilot"),
    ("{topic}blog.com", "The {topic} blog: buyer's guide"),
)

_POSITIVE_PHRASES: tuple[str, ...] = (
    "{brand} is an excellent choice with reliable results and great support.",
    "Reviewers praise {brand} for its outstanding quality and intuitive design.",
    "{brand} delivers impressive value and users love the seamless experience.",
)
_NEUTRAL_PHRASES: tuple[str, ...] = (
    "{brand} is one option among several in this category.",
    "{brand} offers a standard feature set comparable to alternatives.",
    "Some users pick {brand}, while others prefer different tools.",
)
_NEGATIVE_PHRASES: tuple[str, ...] = (
    "{brand} has drawn complaints about poor support and disappointing pricing.",
    "Some reviewers find {brand} unreliable and frustrating to configure.",
    "{brand} lags behind rivals, with users citing buggy, slow performance.",
)


class MockAnswerEngineProvider:
    """Deterministic answer-engine simulator. No network, no ``random``.

    Every derived fact — whether the brand is mentioned, its position in the
    ranked list, the sentiment of the wording, which URLs are cited — is a pure
    function of ``(engine, prompt, brand, competitors)``.
    """

    def ask(
        self,
        engine: AnswerEngine,
        prompt: str,
        brand: str,
        competitors: list[str] | None = None,
    ) -> EngineAnswer:
        competitors = competitors or []
        key = f"{engine.value}|{prompt}|{brand}"
        topic = _topic_word(prompt)

        # ~80% of (engine, prompt) pairs mention the brand at all.
        brand_mentioned = _hash_int(key, "mentioned") % 5 != 0

        candidates = [brand, *competitors]
        # Deterministic filler rivals so ranked lists are never trivially short.
        candidates += [f"{topic.title()}Hub", f"{topic.title()}Pro"]
        ranked = sorted(candidates, key=lambda name: _hash_int(f"{key}|{name}", "rank"))
        if not brand_mentioned:
            ranked = [name for name in ranked if name != brand]

        text = self._answer_text(key, prompt, brand, ranked, brand_mentioned)
        citations = self._citations(key, topic, brand)
        return EngineAnswer(
            engine=engine, prompt=prompt, text=text, ranked_list=ranked, citations=citations
        )

    @staticmethod
    def _answer_text(
        key: str, prompt: str, brand: str, ranked: list[str], brand_mentioned: bool
    ) -> str:
        listing = ", ".join(f"{i}. {name}" for i, name in enumerate(ranked, start=1))
        sentences = [f'For "{prompt}", commonly recommended options are: {listing}.']
        if brand_mentioned:
            # Deterministic sentiment bucket: ~60% positive, ~25% neutral, ~15% negative.
            bucket = _hash_int(key, "sentiment") % 20
            if bucket < 12:
                phrases = _POSITIVE_PHRASES
            elif bucket < 17:
                phrases = _NEUTRAL_PHRASES
            else:
                phrases = _NEGATIVE_PHRASES
            phrase = phrases[_hash_int(key, "phrase") % len(phrases)]
            sentences.append(phrase.format(brand=brand))
        else:
            sentences.append("Evaluate each option against your budget and requirements.")
        return " ".join(sentences)

    @staticmethod
    def _citations(key: str, topic: str, brand: str) -> list[Citation]:
        count = 3 + (_hash_int(key, "citation-count") % 3)  # 3..5
        start = _hash_int(key, "citation-start") % len(_CITATION_POOL)
        citations: list[Citation] = []
        for offset in range(count):
            domain_tpl, title_tpl = _CITATION_POOL[(start + offset) % len(_CITATION_POOL)]
            domain = domain_tpl.format(topic=topic)
            citations.append(
                Citation(
                    url=f"https://{domain}/{topic}-{offset + 1}",
                    domain=domain,
                    title=title_tpl.format(topic=topic),
                )
            )
        # Roughly a third of answers also cite the brand's own site.
        if _hash_int(key, "own-domain") % 3 == 0:
            own = f"{brand_slug(brand)}.com"
            citations.append(
                Citation(url=f"https://{own}/{topic}", domain=own, title=f"{brand} — {topic}")
            )
        return citations


# --------------------------------------------------------------------------
# Mock artifact fetcher (AI readiness)
# --------------------------------------------------------------------------

AI_CRAWLERS: tuple[str, ...] = (
    "GPTBot",
    "ClaudeBot",
    "PerplexityBot",
    "Google-Extended",
    "CCBot",
)


def _default_artifacts(base_url: str) -> SiteArtifacts:
    """A deterministic, reasonably AI-ready site for any URL not explicitly staged."""
    host = base_url.split("://")[-1].strip("/")
    name = host.split(".")[0].title() or "Site"
    llms_txt = (
        f"# {name}\n\n> {name} product documentation and guides.\n\n"
        f"## Docs\n- [Getting started]({base_url}/docs): quick start guide\n"
        f"- [Pricing]({base_url}/pricing): plans overview\n"
    )
    robots_txt = "User-agent: *\nDisallow: /admin/\n\nSitemap: " + base_url + "/sitemap.xml\n"
    html = (
        f"<html><head><title>{name}</title>"
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Organization","name":"' + name + '"}'
        "</script></head><body>"
        f"<h1>{name}</h1><h2>What is {name}?</h2>"
        f"<p>{name} helps teams work faster.</p>"
        "<h2>How does it work?</h2><p>Short answer first, details after.</p>"
        "<ul><li>Fast setup</li><li>Clear pricing</li></ul>"
        "</body></html>"
    )
    return SiteArtifacts(base_url=base_url, llms_txt=llms_txt, robots_txt=robots_txt, html=html)


class MockArtifactFetcher:
    """Deterministic in-memory artifact fetcher used by default and in tests.

    ``sites`` maps a base URL (exact string match) to pre-staged
    :class:`SiteArtifacts`; any URL missing from ``sites`` resolves to a
    deterministic, reasonably AI-ready default so audits always have material
    to score. No network I/O.
    """

    def __init__(self, sites: dict[str, SiteArtifacts] | None = None) -> None:
        self._sites = sites or {}

    def fetch_site(self, base_url: str) -> SiteArtifacts:
        staged = self._sites.get(base_url)
        if staged is not None:
            return staged
        return _default_artifacts(base_url)


# --------------------------------------------------------------------------
# Live skeletons (no network; documented stubs)
# --------------------------------------------------------------------------


class LiveAnswerEngineProvider:
    """Stub adapter for real answer-engine APIs (OpenAI, Anthropic, Perplexity, ...).

    Reads ``google_api_key`` (and any future per-engine keys) from
    :class:`~app.config.Settings` but performs no HTTP calls. Replace
    :meth:`ask` with real clients to go live; until then it always raises
    ``NotImplementedError``.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self.google_api_key = settings.google_api_key

    def ask(
        self,
        engine: AnswerEngine,
        prompt: str,
        brand: str,
        competitors: list[str] | None = None,
    ) -> EngineAnswer:
        raise NotImplementedError("Configure SEO_ANSWER_ENGINE_* credentials to enable")


class LiveArtifactFetcher:
    """Stub adapter for a real HTTP artifact fetcher (llms.txt / robots.txt / HTML).

    Performs no network I/O; :meth:`fetch_site` raises ``NotImplementedError``
    until a real httpx-backed client is wired in.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self.user_agent = settings.crawler_user_agent
        self.timeout = settings.crawler_timeout_seconds

    def fetch_site(self, base_url: str) -> SiteArtifacts:
        raise NotImplementedError("Wire an HTTP client into LiveArtifactFetcher to enable")


# --------------------------------------------------------------------------
# Factories
# --------------------------------------------------------------------------


def get_answer_engine_provider(settings: Settings | None = None) -> AnswerEngineProvider:
    """Return the configured answer-engine provider (mock by default).

    Reads the optional ``answer_engine_provider`` setting via ``getattr`` so the
    module works before the key is added to :class:`~app.config.Settings`.
    """
    settings = settings or get_settings()
    if getattr(settings, "answer_engine_provider", "mock") == "mock":
        return MockAnswerEngineProvider()
    return LiveAnswerEngineProvider(settings=settings)


def get_artifact_fetcher(settings: Settings | None = None) -> ArtifactFetcher:
    """Return the configured site-artifact fetcher (mock by default)."""
    settings = settings or get_settings()
    if getattr(settings, "geo_artifact_fetcher", "mock") == "mock":
        return MockArtifactFetcher()
    return LiveArtifactFetcher(settings=settings)
