"""Content calendar creator: target keywords/clusters -> dated article plan.

Keywords are grouped via the existing deterministic clustering engine
(:func:`app.core.keywords.clustering.cluster_keywords`, read-only); each cluster
becomes one dated calendar entry with a structured outline (H1/H2s, target
keyword, intent, internal links to mapped pages). Fully deterministic.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.core.keywords.clustering import cluster_keywords
from app.models.assistant import (
    ArticleOutline,
    CalendarCadence,
    CalendarEntry,
    ContentCalendar,
    KeywordAssignment,
    OutlineHeading,
)
from app.models.common import SearchIntent
from app.models.keywords import Keyword, KeywordCluster

# Title template per search intent of the cluster's target keyword.
_TITLE_TEMPLATES: dict[SearchIntent, str] = {
    SearchIntent.INFORMATIONAL: "The Complete Guide To {kw}",
    SearchIntent.COMMERCIAL: "Best {kw}: Top Options Compared",
    SearchIntent.TRANSACTIONAL: "How To Choose The Right {kw}",
    SearchIntent.NAVIGATIONAL: "{kw}: Everything You Need To Know",
}

# How many supporting-keyword H2 sections each outline includes at most.
_MAX_SUPPORTING_SECTIONS = 4


def _target_keyword(cluster: KeywordCluster) -> Keyword:
    """Highest-volume member wins; ties break alphabetically for stable output."""
    return sorted(cluster.keywords, key=lambda k: (-k.search_volume, k.keyword))[0]


def _build_outline(
    cluster: KeywordCluster,
    target: Keyword,
    title: str,
    link_map: dict[str, str],
) -> ArticleOutline:
    kw_title = target.keyword.title()
    supporting = [k.keyword for k in cluster.keywords if k.keyword != target.keyword]
    headings = [
        OutlineHeading(level=2, text=f"What You Need To Know About {kw_title}"),
        OutlineHeading(level=2, text=f"Why {kw_title} Matters"),
    ]
    headings.extend(
        OutlineHeading(level=2, text=member.title())
        for member in supporting[:_MAX_SUPPORTING_SECTIONS]
    )
    headings.append(OutlineHeading(level=2, text="Next Steps"))

    internal_links: list[str] = []
    for member in [target.keyword, *supporting]:
        url = link_map.get(member)
        if url and url not in internal_links:
            internal_links.append(url)

    return ArticleOutline(
        h1=title,
        headings=headings,
        target_keyword=target.keyword,
        supporting_keywords=supporting,
        intent=target.intent,
        internal_links=internal_links,
    )


def build_content_calendar(
    keywords: list[Keyword],
    *,
    start: date,
    cadence: CalendarCadence = CalendarCadence.WEEKLY,
    max_entries: int = 12,
    assignments: list[KeywordAssignment] | None = None,
) -> ContentCalendar:
    """Build a dated content calendar from target keywords.

    Keywords are clustered (highest total volume first) and each cluster yields
    one article idea, published every ``cadence.interval_days`` days from
    ``start``. When ``assignments`` (from the keyword mapper) are provided, each
    outline links internally to the pages its cluster keywords are mapped to.
    """
    link_map: dict[str, str] = {
        a.keyword: a.page_url for a in (assignments or []) if a.page_url
    }

    entries: list[CalendarEntry] = []
    clusters = cluster_keywords(keywords)
    for i, cluster in enumerate(clusters[: max(0, max_entries)]):
        target = _target_keyword(cluster)
        template = _TITLE_TEMPLATES.get(target.intent, _TITLE_TEMPLATES[SearchIntent.INFORMATIONAL])
        title = template.format(kw=target.keyword.title())
        entries.append(
            CalendarEntry(
                publish_date=start + timedelta(days=i * cadence.interval_days),
                title=title,
                cluster=cluster.name,
                outline=_build_outline(cluster, target, title, link_map),
            )
        )

    return ContentCalendar(start_date=start, cadence=cadence, entries=entries, total=len(entries))
