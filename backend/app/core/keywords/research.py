"""Keyword research orchestration: provider -> clustering -> KeywordResearchResult."""
from __future__ import annotations

from app.core.keywords.clustering import cluster_keywords
from app.core.keywords.providers import KeywordProvider, get_keyword_provider
from app.models.keywords import KeywordResearchRequest, KeywordResearchResult


def research_keywords(
    req: KeywordResearchRequest, provider: KeywordProvider | None = None
) -> KeywordResearchResult:
    """Generate keyword variations for ``req.seed`` via ``provider`` and cluster them.

    Deterministic end-to-end: the default provider (:class:`MockKeywordProvider`)
    and :func:`~app.core.keywords.clustering.cluster_keywords` are both pure
    functions of their inputs, so calling this twice with an equal ``req``
    yields identical results.
    """
    provider = provider or get_keyword_provider()
    keywords = provider.research(req)
    clusters = cluster_keywords(keywords)
    return KeywordResearchResult(
        seed=req.seed,
        country=req.country,
        keywords=keywords,
        clusters=clusters,
        total_keywords=len(keywords),
    )
