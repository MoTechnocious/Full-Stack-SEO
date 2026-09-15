"""Keyword-to-page mapping and cannibalization detection.

Pure token/TF-IDF relevance: each keyword is assigned to the page whose weighted
text (title counted 3x + body) scores highest for the keyword's significant
tokens, with an exact-phrase boost. Cannibalization is flagged when two or more
pages score within ``cannibalization_ratio`` of the winner. Deterministic —
scores are rounded and ties break alphabetically by URL.
"""
from __future__ import annotations

import math
from collections import Counter

from app.models.assistant import (
    CannibalizationFlag,
    KeywordAssignment,
    KeywordMapResult,
    PageScore,
    SitePage,
)
from app.utils.text import STOPWORDS, phrase_count, tokenize

# Title tokens are repeated this many times when building a page's term counts.
_TITLE_WEIGHT = 3

# Exact-phrase boosts (multiplicative) for a keyword appearing verbatim.
_TITLE_PHRASE_BOOST = 1.5
_BODY_PHRASE_BOOST = 1.2

# How many runner-up pages to expose per assignment.
_MAX_ALTERNATIVES = 3


def _keyword_tokens(keyword: str) -> list[str]:
    tokens = [t for t in tokenize(keyword) if t not in STOPWORDS]
    return tokens or tokenize(keyword)


def _page_counts(page: SitePage) -> tuple[Counter[str], int]:
    tokens = tokenize(page.title) * _TITLE_WEIGHT + tokenize(page.content)
    return Counter(tokens), max(1, len(tokens))


def _score(
    kw_tokens: list[str],
    keyword: str,
    page: SitePage,
    counts: Counter[str],
    length: int,
    idf: dict[str, float],
) -> float:
    score = 0.0
    for token in dict.fromkeys(kw_tokens):  # unique, order-preserving
        tf = counts.get(token, 0) / length
        score += tf * idf.get(token, 1.0)
    if score > 0.0:
        if phrase_count(page.title, keyword) > 0:
            score *= _TITLE_PHRASE_BOOST
        elif phrase_count(page.content, keyword) > 0:
            score *= _BODY_PHRASE_BOOST
    return round(score * 100, 4)


def _consolidation_actions(keyword: str, primary: str) -> list[str]:
    return [
        f"Keep '{primary}' as the primary page for '{keyword}' and point internal links "
        "that use this keyword as anchor text at it.",
        "Consolidate overlapping sections from the competing pages into the primary page, "
        "then 301-redirect any page left with no unique purpose.",
        "If the competing pages must stay, re-target each one at a distinct long-tail "
        "variation so they stop competing for the same query.",
        "Update titles and H1s on the competing pages so only the primary page targets "
        "this keyword directly.",
    ]


def map_keywords(
    keywords: list[str],
    pages: list[SitePage],
    *,
    cannibalization_ratio: float = 0.8,
) -> KeywordMapResult:
    """Assign each keyword to its most relevant page and flag cannibalization.

    ``cannibalization_ratio`` — a competing page is flagged when its score is at
    least this fraction of the winning page's score (0 < ratio <= 1).
    """
    ratio = min(max(cannibalization_ratio, 0.0), 1.0)
    page_data = [(page, *_page_counts(page)) for page in pages]
    total_pages = max(1, len(pages))

    # Document frequency over every keyword token -> smoothed IDF.
    df: Counter[str] = Counter()
    all_kw_tokens = {t for kw in keywords for t in _keyword_tokens(kw)}
    for _, counts, _ in page_data:
        for token in all_kw_tokens:
            if counts.get(token, 0) > 0:
                df[token] += 1
    idf = {t: math.log((total_pages + 1) / (df[t] + 1)) + 1.0 for t in all_kw_tokens}

    assignments: list[KeywordAssignment] = []
    flags: list[CannibalizationFlag] = []
    unmapped: list[str] = []

    for keyword in keywords:
        kw_tokens = _keyword_tokens(keyword)
        scored = [
            PageScore(url=page.url, score=_score(kw_tokens, keyword, page, counts, length, idf))
            for page, counts, length in page_data
        ]
        scored = [s for s in scored if s.score > 0.0]
        scored.sort(key=lambda s: (-s.score, s.url))

        if not scored:
            unmapped.append(keyword)
            assignments.append(KeywordAssignment(keyword=keyword, page_url=None, score=0.0))
            continue

        best = scored[0]
        assignments.append(
            KeywordAssignment(
                keyword=keyword,
                page_url=best.url,
                score=best.score,
                alternatives=scored[1 : 1 + _MAX_ALTERNATIVES],
            )
        )

        competitors = [s for s in scored if s.score >= ratio * best.score]
        if len(competitors) >= 2:
            flags.append(
                CannibalizationFlag(
                    keyword=keyword,
                    primary_page=best.url,
                    competing_pages=competitors,
                    suggested_actions=_consolidation_actions(keyword, best.url),
                )
            )

    return KeywordMapResult(
        assignments=assignments, cannibalization=flags, unmapped_keywords=unmapped
    )
