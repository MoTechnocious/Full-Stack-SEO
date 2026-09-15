"""Rule-based on-page analyzer (Rank Math style checks -> weighted 0-100 score)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.common import Issue, IssueCategory, Severity, grade_from_score
from app.models.onpage import CheckCategory, OnPageCheck, OnPageRequest, OnPageResult
from app.utils.html import ParsedImage, ParsedLink, parse_html
from app.utils.text import (
    flesch_reading_ease,
    keyword_density,
    phrase_count,
    sentence_count,
    tokenize,
    word_count,
)
from app.utils.url import is_internal

_POWER_WORDS: frozenset[str] = frozenset(
    {
        "best", "ultimate", "guide", "top", "proven", "essential", "free", "new",
        "easy", "quick", "simple", "secret", "secrets", "tips", "complete", "expert",
        "amazing", "definitive", "powerful", "effective",
    }
)


@dataclass
class _PageData:
    """Normalized view of the page under analysis, sourced from HTML or raw fields."""

    title: str
    meta_description: str
    content: str
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    h3: list[str] = field(default_factory=list)
    images: list[ParsedImage] = field(default_factory=list)
    links: list[ParsedLink] = field(default_factory=list)
    has_html: bool = False


def _extract(req: OnPageRequest) -> _PageData:
    if req.html:
        page = parse_html(req.html, base_url=req.url)
        return _PageData(
            title=page.title or "",
            meta_description=page.meta_description or "",
            content=page.text or "",
            h1=list(page.h1),
            h2=list(page.h2),
            h3=list(page.h3),
            images=list(page.images),
            links=list(page.links),
            has_html=True,
        )
    return _PageData(
        title=req.title or "",
        meta_description=req.meta_description or "",
        content=req.content or "",
        has_html=False,
    )


def _first_fraction(text: str, fraction: float, min_words: int = 15) -> str:
    words = (text or "").split()
    if not words:
        return ""
    k = max(min_words, round(len(words) * fraction))
    k = min(k, len(words))
    return " ".join(words[:k])


def _near_start(haystack: str, needle: str, fraction: float = 0.5) -> bool:
    needle = (needle or "").strip()
    if not needle or not haystack:
        return False
    idx = haystack.lower().find(needle.lower())
    if idx == -1:
        return False
    limit = max(1, round(len(haystack) * fraction))
    return idx <= limit


def _slug_text(url: str) -> str:
    return re.sub(r"[\-_/]+", " ", url or "")


def _is_internal_href(href: str, base_url: str | None) -> bool:
    if base_url:
        try:
            return is_internal(href, base_url)
        except Exception:
            pass
    return not href.lower().startswith(("http://", "https://", "//"))


# ---------------------------------------------------------------------------
# Individual checks. Each returns a fully-populated OnPageCheck.
# ---------------------------------------------------------------------------


def _check_kw_in_title(kw: str, data: _PageData) -> OnPageCheck:
    passed = bool(kw) and phrase_count(data.title, kw) > 0
    msg = "Focus keyword found in the SEO title." if passed else "Focus keyword is missing from the SEO title."
    return OnPageCheck(
        code="kw_in_title", label="Keyword in title", category=CheckCategory.BASIC,
        passed=passed, weight=5, message=msg,
    )


def _check_kw_in_meta(kw: str, data: _PageData) -> OnPageCheck:
    passed = bool(kw) and phrase_count(data.meta_description, kw) > 0
    msg = (
        "Focus keyword found in the meta description."
        if passed else "Focus keyword is missing from the meta description."
    )
    return OnPageCheck(
        code="kw_in_meta_description", label="Keyword in meta description", category=CheckCategory.BASIC,
        passed=passed, weight=4, message=msg,
    )


def _check_kw_in_url(kw: str, url: str) -> OnPageCheck:
    passed = bool(kw) and phrase_count(_slug_text(url), kw) > 0
    msg = "Focus keyword found in the URL." if passed else "Focus keyword is missing from the URL."
    return OnPageCheck(
        code="kw_in_url", label="Keyword in URL", category=CheckCategory.BASIC,
        passed=passed, weight=3, message=msg,
    )


def _check_kw_in_content_start(kw: str, data: _PageData) -> OnPageCheck:
    start = _first_fraction(data.content, 0.10, min_words=20)
    passed = bool(kw) and phrase_count(start, kw) > 0
    msg = (
        "Focus keyword found near the beginning of the content."
        if passed else "Focus keyword should appear in the first 10% of the content."
    )
    return OnPageCheck(
        code="kw_in_content_start", label="Keyword in opening content", category=CheckCategory.BASIC,
        passed=passed, weight=4, message=msg,
    )


def _check_kw_in_subheading(kw: str, data: _PageData) -> OnPageCheck:
    subheadings = [*data.h2, *data.h3]
    passed = bool(kw) and any(phrase_count(h, kw) > 0 for h in subheadings)
    msg = (
        "Focus keyword found in a subheading."
        if passed else "Focus keyword not found in any subheading (H2/H3)."
    )
    return OnPageCheck(
        code="kw_in_subheading", label="Keyword in subheading", category=CheckCategory.BASIC,
        passed=passed, weight=3, message=msg,
    )


def _check_kw_in_image_alt(kw: str, data: _PageData) -> OnPageCheck:
    passed = bool(kw) and any(img.alt and phrase_count(img.alt, kw) > 0 for img in data.images)
    msg = (
        "Focus keyword found in an image alt attribute."
        if passed else "Focus keyword not found in any image alt attribute."
    )
    return OnPageCheck(
        code="kw_in_image_alt", label="Keyword in image alt text", category=CheckCategory.BASIC,
        passed=passed, weight=2, message=msg,
    )


def _check_content_length(data: _PageData) -> OnPageCheck:
    wc = word_count(data.content)
    passed = wc >= 600
    if wc < 300:
        msg = f"Content is very thin ({wc} words); aim for 600+ words."
    elif wc < 600:
        msg = f"Content is below the recommended minimum ({wc} words); aim for 600+ words."
    elif wc < 1200:
        msg = f"Content length is adequate ({wc} words)."
    elif wc < 2500:
        msg = f"Content length is strong and comprehensive ({wc} words)."
    else:
        msg = f"Content length is excellent and highly comprehensive ({wc}+ words)."
    return OnPageCheck(
        code="content_length", label="Content length", category=CheckCategory.BASIC,
        passed=passed, weight=5, message=msg,
    )


def _check_kw_density(kw: str, data: _PageData) -> OnPageCheck:
    dens = keyword_density(data.content, kw) if kw else 0.0
    passed = 0.5 <= dens <= 2.5
    msg = f"Keyword density is {dens}% (ideal range 0.5%-2.5%)."
    return OnPageCheck(
        code="kw_density", label="Keyword density", category=CheckCategory.BASIC,
        passed=passed, weight=4, message=msg,
    )


def _check_kw_in_h1(kw: str, data: _PageData) -> OnPageCheck:
    passed = bool(kw) and any(phrase_count(h, kw) > 0 for h in data.h1)
    msg = "Focus keyword found in the H1 heading." if passed else "Focus keyword not found in the H1 heading."
    return OnPageCheck(
        code="kw_in_h1", label="Keyword in H1", category=CheckCategory.BASIC,
        passed=passed, weight=3, message=msg,
    )


def _check_url_length(url: str) -> OnPageCheck:
    length = len(url)
    passed = length <= 75
    msg = f"URL length is {length} characters (recommended <= 75)."
    return OnPageCheck(
        code="url_length", label="URL length", category=CheckCategory.ADDITIONAL,
        passed=passed, weight=2, message=msg,
    )


def _check_internal_links(data: _PageData, base_url: str | None) -> OnPageCheck:
    passed = any(_is_internal_href(link.href, base_url) for link in data.links)
    msg = "Page contains at least one internal link." if passed else "Page has no internal links to other site content."
    return OnPageCheck(
        code="internal_links", label="Internal links", category=CheckCategory.ADDITIONAL,
        passed=passed, weight=3, message=msg,
    )


def _check_external_links(data: _PageData, base_url: str | None) -> OnPageCheck:
    passed = any(not _is_internal_href(link.href, base_url) for link in data.links)
    msg = "Page links out to an external resource." if passed else "Page has no outbound links to external resources."
    return OnPageCheck(
        code="external_links", label="External links", category=CheckCategory.ADDITIONAL,
        passed=passed, weight=2, message=msg,
    )


def _check_has_media(data: _PageData) -> OnPageCheck:
    passed = len(data.images) >= 1
    msg = "Page contains at least one image or media element." if passed else "Page has no images or media; add at least one."
    return OnPageCheck(
        code="has_media", label="Image or media present", category=CheckCategory.ADDITIONAL,
        passed=passed, weight=3, message=msg,
    )


def _check_secondary_keywords(secondary: list[str], data: _PageData) -> OnPageCheck:
    cleaned = [kw for kw in secondary if kw and kw.strip()]
    if not cleaned:
        return OnPageCheck(
            code="secondary_keyword_usage", label="Secondary keyword usage", category=CheckCategory.ADDITIONAL,
            passed=True, weight=2, message="No secondary keywords specified.",
        )
    passed = any(phrase_count(data.content, kw) > 0 for kw in cleaned)
    msg = (
        "At least one secondary keyword is used in the content."
        if passed else "None of the secondary keywords appear in the content."
    )
    return OnPageCheck(
        code="secondary_keyword_usage", label="Secondary keyword usage", category=CheckCategory.ADDITIONAL,
        passed=passed, weight=2, message=msg,
    )


def _check_images_alt_coverage(data: _PageData) -> OnPageCheck:
    passed = all(bool(img.alt and img.alt.strip()) for img in data.images) if data.images else True
    msg = "All images have descriptive alt text." if passed else "Some images are missing alt text."
    return OnPageCheck(
        code="all_images_have_alt", label="Image alt coverage", category=CheckCategory.ADDITIONAL,
        passed=passed, weight=1, message=msg,
    )


def _check_title_length(data: _PageData) -> OnPageCheck:
    length = len(data.title)
    passed = 15 <= length <= 60
    msg = f"Title length is {length} characters (recommended 15-60)."
    return OnPageCheck(
        code="title_length", label="Title length", category=CheckCategory.TITLE_READABILITY,
        passed=passed, weight=3, message=msg,
    )


def _check_kw_near_start_title(kw: str, data: _PageData) -> OnPageCheck:
    passed = bool(kw) and _near_start(data.title, kw, fraction=0.5)
    msg = (
        "Focus keyword appears near the beginning of the title."
        if passed else "Focus keyword should appear closer to the beginning of the title."
    )
    return OnPageCheck(
        code="kw_near_start_title", label="Keyword near start of title", category=CheckCategory.TITLE_READABILITY,
        passed=passed, weight=4, message=msg,
    )


def _check_title_has_number(data: _PageData) -> OnPageCheck:
    passed = bool(re.search(r"\d", data.title))
    msg = "Title contains a number." if passed else "Consider adding a number to the title (e.g. a year or list count)."
    return OnPageCheck(
        code="title_has_number", label="Title contains a number", category=CheckCategory.TITLE_READABILITY,
        passed=passed, weight=1, message=msg,
    )


def _check_title_power_word(data: _PageData) -> OnPageCheck:
    passed = any(w in _POWER_WORDS for w in tokenize(data.title))
    msg = (
        "Title contains a power word."
        if passed else "Consider adding a power word (e.g. 'best', 'ultimate', 'guide') to the title."
    )
    return OnPageCheck(
        code="title_has_power_word", label="Title contains a power word", category=CheckCategory.TITLE_READABILITY,
        passed=passed, weight=1, message=msg,
    )


def _check_meta_length(data: _PageData) -> OnPageCheck:
    length = len(data.meta_description)
    passed = 70 <= length <= 160
    msg = f"Meta description length is {length} characters (recommended 70-160)."
    return OnPageCheck(
        code="meta_length", label="Meta description length", category=CheckCategory.CONTENT_READABILITY,
        passed=passed, weight=2, message=msg,
    )


def _check_flesch(data: _PageData) -> OnPageCheck:
    score = flesch_reading_ease(data.content)
    passed = score >= 50
    msg = f"Flesch reading ease score is {score} (aim for 50+)."
    return OnPageCheck(
        code="flesch_readability", label="Content readability (Flesch)", category=CheckCategory.CONTENT_READABILITY,
        passed=passed, weight=3, message=msg,
    )


def _check_has_h2(data: _PageData) -> OnPageCheck:
    passed = len(data.h2) >= 1
    msg = "Content contains at least one H2 subheading." if passed else "Add at least one H2 subheading to break up the content."
    return OnPageCheck(
        code="has_h2", label="Has H2 subheading", category=CheckCategory.CONTENT_READABILITY,
        passed=passed, weight=2, message=msg,
    )


def _check_avg_sentence_length(data: _PageData) -> OnPageCheck:
    wc = word_count(data.content)
    sc = sentence_count(data.content)
    avg = round(wc / sc, 1) if sc else 0.0
    passed = avg <= 25
    msg = f"Average sentence length is {avg} words (aim for <= 25)."
    return OnPageCheck(
        code="avg_sentence_length", label="Average sentence length", category=CheckCategory.CONTENT_READABILITY,
        passed=passed, weight=1, message=msg,
    )


def get_checks(req: OnPageRequest) -> list[OnPageCheck]:
    """Run the full deterministic Rank-Math-style rule set for ``req``.

    URL-dependent checks (``kw_in_url``, ``url_length``) are only included when
    ``req.url`` is set; HTML-dependent link checks (``internal_links``,
    ``external_links``) are only included when ``req.html`` is set. All other
    checks are always evaluated (they degrade gracefully -- e.g. failing --
    when the underlying data, such as headings or images, isn't available).
    """
    data = _extract(req)
    kw = req.target_keyword or ""
    checks: list[OnPageCheck] = []

    # ---- Basic SEO ----
    checks.append(_check_kw_in_title(kw, data))
    checks.append(_check_kw_in_meta(kw, data))
    if req.url:
        checks.append(_check_kw_in_url(kw, req.url))
    checks.append(_check_kw_in_content_start(kw, data))
    checks.append(_check_kw_in_subheading(kw, data))
    checks.append(_check_kw_in_image_alt(kw, data))
    checks.append(_check_content_length(data))
    checks.append(_check_kw_density(kw, data))
    checks.append(_check_kw_in_h1(kw, data))

    # ---- Additional SEO ----
    if req.url:
        checks.append(_check_url_length(req.url))
    if req.html:
        checks.append(_check_internal_links(data, req.url))
        checks.append(_check_external_links(data, req.url))
    checks.append(_check_has_media(data))
    checks.append(_check_secondary_keywords(req.secondary_keywords, data))
    checks.append(_check_images_alt_coverage(data))

    # ---- Title readability ----
    checks.append(_check_title_length(data))
    checks.append(_check_kw_near_start_title(kw, data))
    checks.append(_check_title_has_number(data))
    checks.append(_check_title_power_word(data))

    # ---- Content readability ----
    checks.append(_check_meta_length(data))
    checks.append(_check_flesch(data))
    checks.append(_check_has_h2(data))
    checks.append(_check_avg_sentence_length(data))

    return checks


def _category_scores(checks: list[OnPageCheck]) -> dict[str, int]:
    scores: dict[str, int] = {}
    for category in CheckCategory:
        cat_checks = [c for c in checks if c.category == category]
        if not cat_checks:
            scores[category.value] = 100
            continue
        total_weight = sum(c.weight for c in cat_checks) or 1
        passed_weight = sum(c.weight for c in cat_checks if c.passed)
        scores[category.value] = round(passed_weight / total_weight * 100)
    return scores


def _issues_from_checks(checks: list[OnPageCheck]) -> list[Issue]:
    issues: list[Issue] = []
    for check in checks:
        if check.passed or check.weight < 3:
            continue
        category = (
            IssueCategory.CONTENT
            if check.category in (CheckCategory.TITLE_READABILITY, CheckCategory.CONTENT_READABILITY)
            else IssueCategory.ON_PAGE
        )
        severity = Severity.HIGH if check.weight >= 4 else Severity.MEDIUM
        issues.append(
            Issue(
                code=check.code,
                title=check.label,
                description=check.message,
                category=category,
                severity=severity,
                recommendation=check.message,
                details={"weight": check.weight, "category": check.category.value},
            )
        )
    return issues


def analyze_onpage(req: OnPageRequest) -> OnPageResult:
    """Run the on-page rule set for ``req`` and produce a weighted 0-100 score."""
    checks = get_checks(req)

    total_weight = sum(c.weight for c in checks) or 1
    passed_weight = sum(c.weight for c in checks if c.passed)
    score = round(passed_weight / total_weight * 100)

    return OnPageResult(
        target_keyword=req.target_keyword,
        score=score,
        grade=grade_from_score(score),
        passed_count=sum(1 for c in checks if c.passed),
        total_count=len(checks),
        checks=checks,
        issues=_issues_from_checks(checks),
        category_scores=_category_scores(checks),
    )
