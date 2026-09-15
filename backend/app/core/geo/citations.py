"""Citation & source mapping: which URLs/domains each engine cites, aggregated
domain frequency, and trust-weighted per-topic priority ranking."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.core.geo.providers import AnswerEngineProvider, brand_slug, get_answer_engine_provider
from app.core.geo.store import GeoStore, get_geo_store
from app.models.geo import (
    AnswerEngine,
    Citation,
    CitationReport,
    DomainCategory,
    DomainStats,
    DomainTrustReport,
    EngineCitations,
)
from app.utils.url import registrable_domain

# ---------------------------------------------------------------------------
# Domain classification & trust weights
# ---------------------------------------------------------------------------

_CATEGORY_BY_DOMAIN: dict[str, DomainCategory] = {
    "reddit.com": DomainCategory.COMMUNITY,
    "wikipedia.org": DomainCategory.ENCYCLOPEDIA,
    "g2.com": DomainCategory.REVIEW_PLATFORM,
    "capterra.com": DomainCategory.REVIEW_PLATFORM,
    "trustpilot.com": DomainCategory.REVIEW_PLATFORM,
    "quora.com": DomainCategory.QA_FORUM,
    "stackexchange.com": DomainCategory.QA_FORUM,
    "stackoverflow.com": DomainCategory.QA_FORUM,
}

_NEWS_DOMAINS: frozenset[str] = frozenset(
    {"techcrunch.com", "forbes.com", "reuters.com", "bloomberg.com", "bbc.co.uk", "cnn.com",
     "theverge.com", "wired.com", "nytimes.com"}
)

_BLOG_DOMAINS: frozenset[str] = frozenset({"medium.com", "substack.com", "wordpress.com"})

# How much an engine citing this class of domain matters for GEO outreach.
TRUST_WEIGHTS: dict[DomainCategory, float] = {
    DomainCategory.ENCYCLOPEDIA: 0.95,
    DomainCategory.REVIEW_PLATFORM: 0.90,
    DomainCategory.NEWS: 0.85,
    DomainCategory.COMMUNITY: 0.80,
    DomainCategory.QA_FORUM: 0.75,
    DomainCategory.OWN_DOMAIN: 0.60,
    DomainCategory.BLOG: 0.50,
    DomainCategory.OTHER: 0.40,
}


def classify_domain(domain: str, own_domain: str | None = None) -> DomainCategory:
    """Classify a cited domain into a :class:`DomainCategory` bucket."""
    root = registrable_domain(domain)
    if own_domain and root == registrable_domain(own_domain):
        return DomainCategory.OWN_DOMAIN
    if root in _CATEGORY_BY_DOMAIN:
        return _CATEGORY_BY_DOMAIN[root]
    if root in _NEWS_DOMAINS or "news" in root:
        return DomainCategory.NEWS
    if root in _BLOG_DOMAINS or "blog" in root:
        return DomainCategory.BLOG
    return DomainCategory.OTHER


def aggregate_domains(
    citations_by_engine: dict[AnswerEngine, list[Citation]],
    own_domain: str | None = None,
) -> list[DomainStats]:
    """Fold per-engine citations into trust-weighted, priority-ranked domain stats.

    ``priority_score`` (0-100) = trust weight x citation frequency, so a domain
    an engine leans on heavily *and* that carries authority ranks first.
    """
    counts: dict[str, int] = defaultdict(int)
    engines_for: dict[str, set[AnswerEngine]] = defaultdict(set)
    for engine, citations in citations_by_engine.items():
        for citation in citations:
            root = registrable_domain(citation.domain or citation.url)
            counts[root] += 1
            engines_for[root].add(engine)

    total = sum(counts.values())
    stats: list[DomainStats] = []
    for root, count in counts.items():
        category = classify_domain(root, own_domain=own_domain)
        trust = TRUST_WEIGHTS[category]
        frequency = round(count / total, 4) if total else 0.0
        stats.append(
            DomainStats(
                domain=root,
                category=category,
                trust_weight=trust,
                citations=count,
                frequency=frequency,
                engines=sorted(engines_for[root], key=lambda e: e.value),
                priority_score=round(trust * frequency * 100, 2),
            )
        )
    stats.sort(key=lambda s: (-s.priority_score, -s.citations, s.domain))
    return stats


# ---------------------------------------------------------------------------
# Scan + org-wide aggregation
# ---------------------------------------------------------------------------


def scan_citations(
    org_id: str,
    brand: str,
    prompts: list[str],
    engines: list[AnswerEngine] | None = None,
    own_domain: str | None = None,
    provider: AnswerEngineProvider | None = None,
    store: GeoStore | None = None,
    day: date | None = None,
) -> CitationReport:
    """Extract which URLs/domains each engine cites for the brand's prompt set.

    The report is appended to the org's citation history so
    :func:`build_domain_trust_report` can aggregate across scans.
    """
    engines = engines or list(AnswerEngine)
    provider = provider or get_answer_engine_provider()
    store = store or get_geo_store()
    own = own_domain or f"{brand_slug(brand)}.com"

    citations_by_engine: dict[AnswerEngine, list[Citation]] = {}
    for engine in engines:
        collected: list[Citation] = []
        for prompt in prompts:
            collected.extend(provider.ask(engine, prompt, brand, []).citations)
        citations_by_engine[engine] = collected

    report = CitationReport(
        brand=brand,
        scanned_on=day or date.today(),
        total_citations=sum(len(c) for c in citations_by_engine.values()),
        engines=[
            EngineCitations(engine=engine, citations=citations)
            for engine, citations in citations_by_engine.items()
        ],
        domains=aggregate_domains(citations_by_engine, own_domain=own),
    )
    store.append_citations(org_id, report)
    return report


def build_domain_trust_report(
    org_id: str,
    own_domain: str | None = None,
    store: GeoStore | None = None,
) -> DomainTrustReport:
    """Aggregate every stored citation scan for the org into one trust ranking."""
    store = store or get_geo_store()
    merged: dict[AnswerEngine, list[Citation]] = defaultdict(list)
    for report in store.citation_reports(org_id):
        for engine_citations in report.engines:
            merged[engine_citations.engine].extend(engine_citations.citations)

    domains = aggregate_domains(merged, own_domain=own_domain)
    return DomainTrustReport(
        total_citations=sum(len(c) for c in merged.values()),
        domains=domains,
    )
