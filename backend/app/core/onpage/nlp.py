"""Term-target derivation (Surfer-style content term recommendations).

Given a set of competitor texts, surface the uni-/bi-grams that matter most and
translate their competitor usage into a recommended occurrence band for the
piece of content being optimized.
"""
from __future__ import annotations

from collections import Counter

from app.models.onpage import TermStatus, TermTarget
from app.utils.text import extract_terms, phrase_count

# Large per-document cap so extract_terms effectively returns full counts for a
# single document before we merge across documents (avoids cross-document
# n-gram bleed that a single joined-text pass would introduce).
_PER_DOC_TOP_K = 500


def derive_term_targets(competitor_texts: list[str], content: str, top_k: int = 25) -> list[TermTarget]:
    """Derive recommended usage bands for the terms that matter most to competitors.

    For every uni-/bi-gram surfaced by :func:`extract_terms` across
    ``competitor_texts``, compute a recommended ``[min, max]`` occurrence band
    from the average per-document frequency (``min ~= round(avg * 0.6)``,
    ``max ~= round(avg * 1.4) + 1``), compare it against how often the term
    already appears in ``content`` (via :func:`phrase_count`), and classify the
    gap as :class:`TermStatus` UNDER / OPTIMAL / OVER. Results are ordered by
    importance (aggregate competitor frequency) descending; ties keep their
    first-seen order for determinism.
    """
    texts = [t for t in (competitor_texts or []) if t and t.strip()]
    if not texts:
        return []

    total_counts: Counter[str] = Counter()
    for doc in texts:
        for term, count in extract_terms(doc, top_k=_PER_DOC_TOP_K, max_n=2):
            total_counts[term] += count

    n_docs = len(texts)
    ranked = total_counts.most_common(top_k)

    targets: list[TermTarget] = []
    for term, total in ranked:
        avg = total / n_docs
        recommended_min = max(0, round(avg * 0.6))
        recommended_max = round(avg * 1.4) + 1
        if recommended_max <= recommended_min:
            recommended_max = recommended_min + 1

        current = phrase_count(content, term)
        if current < recommended_min:
            status = TermStatus.UNDER
        elif current > recommended_max:
            status = TermStatus.OVER
        else:
            status = TermStatus.OPTIMAL

        targets.append(
            TermTarget(
                term=term,
                current_count=current,
                recommended_min=recommended_min,
                recommended_max=recommended_max,
                status=status,
                in_headings=False,
                importance=float(total),
            )
        )

    targets.sort(key=lambda t: t.importance, reverse=True)
    return targets
