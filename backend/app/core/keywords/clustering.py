"""Deterministic keyword clustering by shared topical tokens."""
from __future__ import annotations

from app.models.keywords import Keyword, KeywordCluster
from app.utils.text import STOPWORDS, tokenize

# Common SEO "modifier" words that shouldn't drive topic grouping on their own
# — they describe intent/qualifiers, not the topic itself. Keeping this
# separate from STOPWORDS (a general-purpose NLP list) lets keyword variations
# like "best running shoes" and "running shoes near me" land in the same
# "running shoes" cluster instead of splitting on the modifier.
_MODIFIER_WORDS: frozenset[str] = frozenset(
    """best top cheap affordable premium near reviews review cost price buy sale
    online guide guides tips idea ideas beginners beginner alternative alternatives
    comparison brand brands local deals deal discount coupon coupons men women kids
    size worth works makes open now list lists help finds find important option
    options 2024 2025 2026 2027""".split()
)


def _significant_tokens(keyword: str) -> list[str]:
    tokens = tokenize(keyword)
    return [t for t in tokens if t not in STOPWORDS and t not in _MODIFIER_WORDS and len(t) > 2]


def _cluster_key(keyword: str) -> str:
    """Primary grouping key: bigram of the two leading significant tokens.

    Falls back to a single significant token, then to the raw first token,
    when the keyword has fewer significant (non-stopword/non-modifier) tokens.
    """
    significant = _significant_tokens(keyword)
    if len(significant) >= 2:
        return f"{significant[0]} {significant[1]}"
    if significant:
        return significant[0]
    tokens = tokenize(keyword)
    return tokens[0] if tokens else keyword.strip().lower()


def cluster_keywords(keywords: list[Keyword]) -> list[KeywordCluster]:
    """Group keywords by shared topic; order clusters by total volume (desc).

    Grouping is pure string/token logic (first non-stopword/non-modifier
    token, or a shared bigram of the first two) with no hashing or
    randomness, so the same input always yields the same clusters in the
    same order. Ties in ``total_volume`` are broken alphabetically by cluster
    name for fully stable output.
    """
    buckets: dict[str, list[Keyword]] = {}
    for kw in keywords:
        key = _cluster_key(kw.keyword)
        buckets.setdefault(key, []).append(kw)

    clusters: list[KeywordCluster] = []
    for key, members in buckets.items():
        total_volume = sum(k.search_volume for k in members)
        avg_difficulty = round(sum(k.difficulty for k in members) / len(members), 1)
        clusters.append(
            KeywordCluster(
                name=key.title(),
                keywords=members,
                total_volume=total_volume,
                avg_difficulty=avg_difficulty,
            )
        )

    clusters.sort(key=lambda c: (-c.total_volume, c.name))
    return clusters
