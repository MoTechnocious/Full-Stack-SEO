"""Dynamic internal linking: TF-IDF cosine similarity between site pages.

Pure python (stdlib/math only). Recommends source -> target links with anchor
text for page pairs above a similarity threshold, skipping links that already
exist on the source page.
"""
from __future__ import annotations

from app.core.aeo.vectorize import content_tokens, cosine_similarity, tfidf_vectors
from app.models.aeo import LinkSuggestion, LinkSuggestRequest, LinkSuggestResult


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/").lower()


def _anchor_text(target_title: str, target_url: str) -> str:
    """Anchor text: the target's title, falling back to a URL-derived phrase."""
    if target_title.strip():
        return target_title.strip()
    slug = _normalize_url(target_url).rsplit("/", 1)[-1]
    return slug.replace("-", " ").replace("_", " ") or target_url


def suggest_links(req: LinkSuggestRequest) -> LinkSuggestResult:
    """Recommend internal links between ``req.pages``.

    Every ordered page pair (source, target) with TF-IDF cosine similarity of
    title+body at or above ``req.similarity_threshold`` yields a suggestion,
    unless the source already links to the target or the pair shares a URL.
    Per source page, suggestions are strongest-first and capped at
    ``req.max_per_page``.
    """
    pages = req.pages
    documents = [content_tokens(f"{page.title} {page.body}") for page in pages]
    vectors = tfidf_vectors(documents)

    suggestions: list[LinkSuggestion] = []
    for i, source in enumerate(pages):
        existing = {_normalize_url(link) for link in source.existing_links}
        candidates: list[LinkSuggestion] = []
        for j, target in enumerate(pages):
            if i == j or _normalize_url(target.url) == _normalize_url(source.url):
                continue
            if _normalize_url(target.url) in existing:
                continue
            similarity = cosine_similarity(vectors[i], vectors[j])
            if similarity >= req.similarity_threshold:
                candidates.append(
                    LinkSuggestion(
                        source_url=source.url,
                        target_url=target.url,
                        similarity=round(similarity, 3),
                        anchor_text=_anchor_text(target.title, target.url),
                    )
                )
        candidates.sort(key=lambda s: s.similarity, reverse=True)
        suggestions.extend(candidates[: req.max_per_page])

    return LinkSuggestResult(suggestions=suggestions, pages_analyzed=len(pages))
