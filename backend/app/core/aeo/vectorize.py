"""Pure-python TF-IDF vectors + cosine similarity (stdlib/math only).

Shared by the question-clustering and internal-linking engines so the two
never drift apart on tokenization or weighting.
"""
from __future__ import annotations

import math

from app.utils.text import STOPWORDS, tokenize


def content_tokens(text: str) -> list[str]:
    """Lowercase word tokens with stopwords removed (falls back to all tokens).

    The fallback keeps very short, stopword-heavy inputs (e.g. "is it worth it")
    representable instead of collapsing them to an empty vector.
    """
    tokens = tokenize(text)
    filtered = [t for t in tokens if t not in STOPWORDS]
    return filtered or tokens


def tfidf_vectors(documents: list[list[str]]) -> list[dict[str, float]]:
    """TF-IDF weight maps for pre-tokenized ``documents``.

    Uses smoothed IDF (``log((1+N)/(1+df)) + 1``) so terms present in every
    document keep a small positive weight instead of vanishing.
    """
    n_docs = len(documents)
    df: dict[str, int] = {}
    for tokens in documents:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1

    vectors: list[dict[str, float]] = []
    for tokens in documents:
        vector: dict[str, float] = {}
        if tokens:
            counts: dict[str, int] = {}
            for term in tokens:
                counts[term] = counts.get(term, 0) + 1
            for term, count in counts.items():
                tf = count / len(tokens)
                idf = math.log((1 + n_docs) / (1 + df[term])) + 1
                vector[term] = tf * idf
        vectors.append(vector)
    return vectors


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity between two sparse weight maps (0.0 for empty vectors)."""
    if not a or not b:
        return 0.0
    smaller, larger = (a, b) if len(a) <= len(b) else (b, a)
    dot = sum(weight * larger.get(term, 0.0) for term, weight in smaller.items())
    if dot == 0.0:
        return 0.0
    norm_a = math.sqrt(sum(w * w for w in a.values()))
    norm_b = math.sqrt(sum(w * w for w in b.values()))
    return dot / (norm_a * norm_b)
