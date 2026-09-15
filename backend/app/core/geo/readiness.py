"""AI readiness audit: is a site consumable by generative answer engines?

Checks llms.txt presence/validity, robots.txt rules for AI crawlers,
structured data, heading structure, and answer-friendly formatting over
artifacts supplied by an injectable :class:`ArtifactFetcher` (mock default).
Produces a weighted 0-100 score plus prioritized fix instructions."""
from __future__ import annotations

import json
import re

from app.core.geo.providers import AI_CRAWLERS, ArtifactFetcher, get_artifact_fetcher
from app.models.common import Issue, IssueCategory, Severity, grade_from_score
from app.models.geo import AiCrawlerAccess, ReadinessCheck, ReadinessReport, SiteArtifacts
from app.utils.text import word_count

_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
_H3_RE = re.compile(r"<h3[^>]*>(.*?)</h3>", re.IGNORECASE | re.DOTALL)
_P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_LIST_RE = re.compile(r"<(?:ul|ol|table)[^>]*>", re.IGNORECASE)
_JSON_LD_RE = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_MD_LINK_RE = re.compile(r"\[[^\]]+\]\([^)]+\)")

_QUESTION_LEADERS: tuple[str, ...] = ("how", "what", "why", "which", "when", "where", "who", "can", "is", "does")

# Failed-check code -> (severity, category, recommendation).
_FIX_GUIDE: dict[str, tuple[Severity, IssueCategory, str]] = {
    "llms_txt_present": (
        Severity.HIGH,
        IssueCategory.TECHNICAL,
        "Publish an llms.txt file at the site root summarizing your key pages "
        "in markdown so LLM crawlers can discover canonical content.",
    ),
    "llms_txt_valid": (
        Severity.MEDIUM,
        IssueCategory.TECHNICAL,
        "Start llms.txt with an H1 title line ('# Site Name') and include at "
        "least one markdown link to an important page.",
    ),
    "robots_txt_present": (
        Severity.MEDIUM,
        IssueCategory.INDEXABILITY,
        "Publish a robots.txt so crawlers (including AI bots) get explicit rules "
        "instead of guessing.",
    ),
    "ai_crawlers_allowed": (
        Severity.CRITICAL,
        IssueCategory.INDEXABILITY,
        "Remove blanket 'Disallow: /' rules for GPTBot, ClaudeBot, PerplexityBot, "
        "Google-Extended, and CCBot — blocked engines cannot cite you.",
    ),
    "structured_data_present": (
        Severity.HIGH,
        IssueCategory.STRUCTURED_DATA,
        "Add JSON-LD structured data (Organization, Product, FAQPage, ...) so "
        "engines can extract entities and facts reliably.",
    ),
    "structured_data_valid": (
        Severity.MEDIUM,
        IssueCategory.STRUCTURED_DATA,
        "Fix the JSON-LD block: it must parse as valid JSON.",
    ),
    "single_h1": (
        Severity.MEDIUM,
        IssueCategory.ON_PAGE,
        "Use exactly one H1 describing the page topic; multiple or missing H1s "
        "confuse passage extraction.",
    ),
    "has_h2_sections": (
        Severity.MEDIUM,
        IssueCategory.CONTENT,
        "Break content into H2 sections so answer engines can lift self-contained passages.",
    ),
    "question_headings": (
        Severity.LOW,
        IssueCategory.CONTENT,
        "Phrase some H2/H3 headings as questions ('How does X work?') — they map "
        "directly onto conversational prompts.",
    ),
    "answer_friendly_lists": (
        Severity.LOW,
        IssueCategory.CONTENT,
        "Add bulleted/numbered lists or tables; engines prefer citing scannable structures.",
    ),
    "concise_paragraphs": (
        Severity.LOW,
        IssueCategory.CONTENT,
        "Keep paragraphs under ~120 words and lead with the answer so passages "
        "quote cleanly.",
    ),
}

_SEVERITY_FOR_CODE = {code: guide[0] for code, guide in _FIX_GUIDE.items()}


# ---------------------------------------------------------------------------
# robots.txt parsing for AI crawlers
# ---------------------------------------------------------------------------


def _parse_robots_groups(robots_txt: str) -> list[tuple[list[str], list[str]]]:
    """Split robots.txt into ``(user_agents, disallow_paths)`` groups."""
    groups: list[tuple[list[str], list[str]]] = []
    agents: list[str] = []
    disallows: list[str] = []
    agents_open = False  # collecting consecutive User-agent lines

    for raw_line in robots_txt.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()
        if field == "user-agent":
            if not agents_open and agents:
                groups.append((agents, disallows))
                agents, disallows = [], []
            agents.append(value.lower())
            agents_open = True
        elif field == "disallow":
            disallows.append(value)
            agents_open = False
        else:
            agents_open = False
    if agents:
        groups.append((agents, disallows))
    return groups


def ai_crawler_access(robots_txt: str | None) -> list[AiCrawlerAccess]:
    """Evaluate whether each known AI crawler may fetch the site root.

    A crawler is blocked when its most specific robots.txt group (its own name,
    falling back to ``*``) contains a blanket ``Disallow: /``. A missing
    robots.txt allows everyone (crawler default behaviour).
    """
    if not robots_txt:
        return [AiCrawlerAccess(crawler=c, allowed=True) for c in AI_CRAWLERS]

    groups = _parse_robots_groups(robots_txt)
    access: list[AiCrawlerAccess] = []
    for crawler in AI_CRAWLERS:
        specific = [d for agents, d in groups if crawler.lower() in agents]
        wildcard = [d for agents, d in groups if "*" in agents]
        disallows = specific[0] if specific else (wildcard[0] if wildcard else [])
        access.append(AiCrawlerAccess(crawler=crawler, allowed="/" not in disallows))
    return access


# ---------------------------------------------------------------------------
# Individual artifact checks
# ---------------------------------------------------------------------------


def _llms_txt_valid(llms_txt: str) -> bool:
    lines = [line.strip() for line in llms_txt.strip().splitlines() if line.strip()]
    has_title = bool(lines) and lines[0].startswith("# ")
    has_link = bool(_MD_LINK_RE.search(llms_txt))
    return has_title and has_link


def _strip_tags(fragment: str) -> str:
    return _TAG_RE.sub(" ", fragment)


def _build_checks(artifacts: SiteArtifacts, access: list[AiCrawlerAccess]) -> list[ReadinessCheck]:
    """Run every readiness check against the fetched artifacts."""
    html = artifacts.html or ""
    checks: list[ReadinessCheck] = []

    def add(code: str, label: str, passed: bool, weight: int, message: str) -> None:
        checks.append(
            ReadinessCheck(code=code, label=label, passed=passed, weight=weight, message=message)
        )

    # ---- llms.txt ----
    has_llms = bool(artifacts.llms_txt and artifacts.llms_txt.strip())
    add("llms_txt_present", "llms.txt is published", has_llms, 3,
        "Found llms.txt at the site root." if has_llms else "No llms.txt found.")
    llms_valid = has_llms and _llms_txt_valid(artifacts.llms_txt or "")
    add("llms_txt_valid", "llms.txt is well-formed", llms_valid, 2,
        "llms.txt has a title and markdown links." if llms_valid
        else "llms.txt is missing an H1 title line and/or markdown links.")

    # ---- robots.txt / AI crawlers ----
    has_robots = bool(artifacts.robots_txt and artifacts.robots_txt.strip())
    add("robots_txt_present", "robots.txt is published", has_robots, 1,
        "Found robots.txt." if has_robots else "No robots.txt found.")
    blocked = [a.crawler for a in access if not a.allowed]
    add("ai_crawlers_allowed", "AI crawlers are not blocked", not blocked, 3,
        "All tracked AI crawlers may fetch the site." if not blocked
        else f"Blocked AI crawlers: {', '.join(blocked)}.")

    # ---- structured data ----
    json_ld_blocks = _JSON_LD_RE.findall(html)
    add("structured_data_present", "JSON-LD structured data present", bool(json_ld_blocks), 2,
        f"Found {len(json_ld_blocks)} JSON-LD block(s)." if json_ld_blocks
        else "No application/ld+json blocks found.")
    if json_ld_blocks:
        valid = True
        for block in json_ld_blocks:
            try:
                json.loads(block)
            except ValueError:
                valid = False
                break
        add("structured_data_valid", "JSON-LD parses as valid JSON", valid, 1,
            "All JSON-LD blocks parse." if valid else "At least one JSON-LD block is invalid JSON.")

    # ---- heading structure ----
    h1s = _H1_RE.findall(html)
    h2s = _H2_RE.findall(html)
    h3s = _H3_RE.findall(html)
    add("single_h1", "Exactly one H1", len(h1s) == 1, 2, f"Found {len(h1s)} H1 tag(s).")
    add("has_h2_sections", "Content sectioned with H2s", bool(h2s), 1,
        f"Found {len(h2s)} H2 tag(s).")

    # ---- answer-friendly formatting ----
    headings_text = [_strip_tags(h).strip().lower() for h in h2s + h3s]
    question_headings = [
        h for h in headings_text if "?" in h or h.startswith(_QUESTION_LEADERS)
    ]
    add("question_headings", "Question-style headings present", bool(question_headings), 1,
        f"{len(question_headings)} heading(s) phrased as questions.")

    add("answer_friendly_lists", "Lists or tables present", bool(_LIST_RE.search(html)), 1,
        "Found list/table markup." if _LIST_RE.search(html) else "No <ul>/<ol>/<table> found.")

    paragraphs = [_strip_tags(p) for p in _P_RE.findall(html)]
    paragraph_lengths = [word_count(p) for p in paragraphs if p.strip()]
    concise = bool(paragraph_lengths) and (
        sum(paragraph_lengths) / len(paragraph_lengths) <= 120
    )
    add("concise_paragraphs", "Paragraphs are concise", concise, 1,
        "Average paragraph length is answer-friendly." if concise
        else "Paragraphs are missing or too long for clean passage extraction.")

    return checks


def _fixes_for(checks: list[ReadinessCheck], url: str) -> list[Issue]:
    """Turn failed checks into prioritized fix instructions (most severe first)."""
    fixes: list[Issue] = []
    for check in checks:
        if check.passed:
            continue
        severity, category, recommendation = _FIX_GUIDE[check.code]
        fixes.append(
            Issue(
                code=f"geo_{check.code}",
                title=f"Fix: {check.label}",
                description=check.message,
                category=category,
                severity=severity,
                recommendation=recommendation,
                url=url,
            )
        )
    fixes.sort(key=lambda issue: -issue.severity.weight)
    return fixes


def audit_readiness(url: str, fetcher: ArtifactFetcher | None = None) -> ReadinessReport:
    """Run the full AI readiness audit for ``url`` via ``fetcher``.

    Deterministic for a fixed fetcher: score is the weighted share of passed
    checks (0-100), graded A-F, with prioritized fixes for every failure.
    """
    fetcher = fetcher or get_artifact_fetcher()
    artifacts = fetcher.fetch_site(url)
    access = ai_crawler_access(artifacts.robots_txt)
    checks = _build_checks(artifacts, access)

    total_weight = sum(c.weight for c in checks)
    passed_weight = sum(c.weight for c in checks if c.passed)
    score = round(passed_weight / total_weight * 100) if total_weight else 0

    return ReadinessReport(
        url=url,
        score=score,
        grade=grade_from_score(score),
        passed_count=sum(1 for c in checks if c.passed),
        total_count=len(checks),
        checks=checks,
        crawler_access=access,
        fixes=_fixes_for(checks, url),
    )
