"""Surfer-style dual content scoring (SEO score + AI-search score)."""
from __future__ import annotations

import re

from app.core.onpage.nlp import derive_term_targets
from app.models.onpage import ContentEditorRequest, ContentScore, TermStatus
from app.utils.text import keyword_density, phrase_count, word_count

_DEFAULT_WORD_COUNT_MIN = 800
_DEFAULT_WORD_COUNT_MAX = 1500

_MD_HEADING_RE = re.compile(r"(?m)^\s{0,3}#{1,6}\s+\S.*$")
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_LIST_LINE_RE = re.compile(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+\S")
_DIGIT_RE = re.compile(r"\d")


def _clamp_int(value: float) -> int:
    return int(round(max(0.0, min(100.0, value))))


def _word_count_band(req: ContentEditorRequest, competitor_texts: list[str] | None) -> tuple[int, int]:
    counts: list[int] = []
    if req.competitor_word_counts:
        counts = [c for c in req.competitor_word_counts if c > 0]
    elif competitor_texts:
        counts = [word_count(t) for t in competitor_texts if t and t.strip()]

    if not counts:
        return _DEFAULT_WORD_COUNT_MIN, _DEFAULT_WORD_COUNT_MAX

    wc_min, wc_max = min(counts), max(counts)
    if wc_max <= wc_min:
        wc_min = max(0, round(wc_min * 0.85))
        wc_max = round(max(wc_max, 1) * 1.15) + 1
    if wc_max <= wc_min:
        wc_max = wc_min + 100
    return wc_min, wc_max


def _count_headings(text: str) -> int:
    """Heuristic heading count for plain-text content (markdown headers, else
    short punctuation-free lines that read like a subheading)."""
    md_headings = _MD_HEADING_RE.findall(text or "")
    if md_headings:
        return len(md_headings)
    count = 0
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        word_len = len(stripped.split())
        if word_len <= 10 and not stripped.endswith((".", "!", "?", ",")):
            count += 1
    return count


def _count_images(text: str) -> int:
    """Heuristic media count for plain-text content (markdown image syntax)."""
    return len(_MD_IMAGE_RE.findall(text or ""))


def _structure_score(headings_count: int, headings_target: int, images_count: int, images_target: int) -> int:
    heading_ratio = min(1.0, headings_count / headings_target) if headings_target else 1.0
    image_ratio = min(1.0, images_count / images_target) if images_target else 1.0
    return _clamp_int(((heading_ratio + image_ratio) / 2.0) * 100.0)


def _ai_search_score(content: str, target_keyword: str) -> int:
    """Heuristic AI-search alignment: facts coverage (digits/lists) + intent
    alignment (target keyword present within the first 100 words)."""
    has_digits = bool(_DIGIT_RE.search(content or ""))
    has_list = bool(_LIST_LINE_RE.search(content or ""))
    facts_score = (30 if has_digits else 0) + (30 if has_list else 0)

    first_100 = " ".join((content or "").split()[:100])
    intent_score = 40 if target_keyword and phrase_count(first_100, target_keyword) > 0 else 0
    return _clamp_int(facts_score + intent_score)


def _build_suggestions(
    *,
    wc: int,
    wc_min: int,
    wc_max: int,
    missing_terms: list[str],
    overused_terms: list[str],
    headings_count: int,
    headings_target: int,
    images_count: int,
    images_target: int,
    content: str,
    target_keyword: str,
) -> list[str]:
    suggestions: list[str] = []
    if wc < wc_min:
        suggestions.append(
            f"Add roughly {wc_min - wc} more words to reach the target range of {wc_min}-{wc_max} words."
        )
    elif wc > wc_max:
        suggestions.append(
            f"Content ({wc} words) is longer than the competitor range ({wc_min}-{wc_max}); "
            "make sure the extra length adds value."
        )

    if missing_terms:
        preview = ", ".join(missing_terms[:5])
        suggestions.append(f"Use these underused terms more often: {preview}.")
    if overused_terms:
        preview = ", ".join(overused_terms[:5])
        suggestions.append(f"Reduce usage of these overused terms to avoid keyword stuffing: {preview}.")

    if headings_count < headings_target:
        suggestions.append(
            f"Add more subheadings (found {headings_count}, target {headings_target}) to improve structure."
        )
    if images_count < images_target:
        suggestions.append(f"Add more images or media (found {images_count}, target {images_target}).")

    first_100 = " ".join((content or "").split()[:100])
    if target_keyword and phrase_count(first_100, target_keyword) == 0:
        suggestions.append("Mention the target keyword within the first 100 words to align with search intent.")

    if not suggestions:
        suggestions.append(
            "Content is well-optimized; consider adding more original data or examples to strengthen authority."
        )
    return suggestions


def score_content(req: ContentEditorRequest, competitor_texts: list[str] | None = None) -> ContentScore:
    """Score ``req.content`` Surfer-style: a blended SEO score plus an
    AI-search alignment heuristic, with actionable term/structure targets.
    """
    content = req.content or ""
    wc = word_count(content)
    wc_min, wc_max = _word_count_band(req, competitor_texts)

    if competitor_texts:
        term_targets = derive_term_targets(competitor_texts, content)
    else:
        synthetic_texts = [t for t in [req.target_keyword, *req.secondary_keywords] if t and t.strip()]
        if not synthetic_texts:
            synthetic_texts = [req.target_keyword] if req.target_keyword else []
        term_targets = derive_term_targets(synthetic_texts, content, top_k=max(10, len(synthetic_texts) * 3))

    missing_terms = [t.term for t in term_targets if t.status == TermStatus.UNDER]
    overused_terms = [t.term for t in term_targets if t.status == TermStatus.OVER]

    headings_count = _count_headings(content)
    headings_target = max(2, round(wc / 300)) if wc else 2
    images_count = _count_images(content)
    images_target = max(1, round(wc / 500)) if wc else 1

    kw_present = bool(req.target_keyword) and phrase_count(content, req.target_keyword) > 0
    density = keyword_density(content, req.target_keyword) if req.target_keyword else 0.0

    presence_pts = 15.0 if kw_present else 0.0
    if density == 0:
        density_pts = 0.0
    elif 0.5 <= density <= 2.5:
        density_pts = 20.0
    else:
        density_pts = 8.0
    keyword_component = presence_pts + density_pts  # up to 35

    if term_targets:
        optimal_fraction = sum(1 for t in term_targets if t.status == TermStatus.OPTIMAL) / len(term_targets)
    else:
        optimal_fraction = 0.5
    optimal_component = optimal_fraction * 30.0  # up to 30

    if wc_min > 0:
        wc_component = 20.0 if wc >= wc_min else 20.0 * (wc / wc_min)
    else:
        wc_component = 20.0
    wc_component = max(0.0, min(20.0, wc_component))  # up to 20

    structure_score = _structure_score(headings_count, headings_target, images_count, images_target)
    structure_component = structure_score / 100.0 * 15.0  # up to 15

    seo_score = _clamp_int(keyword_component + optimal_component + wc_component + structure_component)
    ai_search_score = _ai_search_score(content, req.target_keyword)
    content_score = _clamp_int(0.7 * seo_score + 0.3 * structure_score)

    suggestions = _build_suggestions(
        wc=wc,
        wc_min=wc_min,
        wc_max=wc_max,
        missing_terms=missing_terms,
        overused_terms=overused_terms,
        headings_count=headings_count,
        headings_target=headings_target,
        images_count=images_count,
        images_target=images_target,
        content=content,
        target_keyword=req.target_keyword,
    )

    return ContentScore(
        target_keyword=req.target_keyword,
        content_score=content_score,
        seo_score=seo_score,
        ai_search_score=ai_search_score,
        word_count=wc,
        word_count_target_min=wc_min,
        word_count_target_max=wc_max,
        headings_count=headings_count,
        headings_target=headings_target,
        images_count=images_count,
        images_target=images_target,
        term_targets=term_targets,
        missing_terms=missing_terms,
        overused_terms=overused_terms,
        suggestions=suggestions,
    )
