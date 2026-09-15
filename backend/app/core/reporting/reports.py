"""White-label report assembly and self-contained HTML rendering (HikeSEO style)."""
from __future__ import annotations

import html
import uuid
from datetime import datetime, timezone

from app.core.reporting.whitelabel import apply_branding
from app.models.audit import CrawlResult
from app.models.common import Issue, grade_from_score
from app.models.keywords import KeywordResearchResult, RankTrackingSummary
from app.models.reporting import (
    ActionPlan,
    Report,
    ReportSection,
    TaskStatus,
    WhiteLabelBranding,
)

_TOP_ISSUES_LIMIT = 5

_HEADLINE_LABELS: dict[str, str] = {
    "health_score": "Health Score",
    "avg_position": "Avg. Position",
    "top10": "Keywords in Top 10",
    "open_tasks": "Open Tasks",
    "tracked_keywords": "Tracked Keywords",
}


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _derive_top_issues(audit: CrawlResult, limit: int = _TOP_ISSUES_LIMIT) -> list[Issue]:
    """Fallback top-issues list (highest severity, deduped by code) used when the
    crawl didn't already populate ``CrawlResult.top_issues``."""
    worst: dict[str, Issue] = {}
    for page in audit.pages:
        for issue in page.issues:
            current = worst.get(issue.code)
            if current is None or issue.severity.weight > current.severity.weight:
                worst[issue.code] = issue
    return sorted(worst.values(), key=lambda i: -i.severity.weight)[:limit]


def _build_summary_section(
    site: str, period_start: str, period_end: str, headline: dict[str, object]
) -> ReportSection:
    parts = [f"SEO performance summary for {site} ({period_start} to {period_end})."]
    if headline.get("health_score") is not None:
        parts.append(f"Site health score: {headline['health_score']}/100.")
    if headline.get("avg_position") is not None:
        parts.append(f"Average keyword position: {headline['avg_position']}.")
    if headline.get("tracked_keywords") is not None:
        parts.append(f"{headline['tracked_keywords']} keywords tracked.")
    if headline.get("open_tasks") is not None:
        parts.append(f"{headline['open_tasks']} open action item(s).")
    return ReportSection(
        title="Executive Summary", type="summary", summary=" ".join(parts), data=dict(headline)
    )


def _build_audit_section(audit: CrawlResult) -> ReportSection:
    summary = audit.summary
    top_issues = list(audit.top_issues[:_TOP_ISSUES_LIMIT]) if audit.top_issues else _derive_top_issues(audit)
    data: dict[str, object] = {
        "health_score": round(summary.avg_score, 1),
        "grade": grade_from_score(summary.avg_score),
        "total_pages": summary.total_pages,
        "indexable_pages": summary.indexable_pages,
        "non_indexable_pages": summary.non_indexable_pages,
        "pages_with_issues": summary.pages_with_issues,
        "broken_links_total": summary.broken_links_total,
        "by_severity": dict(summary.by_severity),
        "top_issues": [
            {
                "code": issue.code,
                "title": issue.title,
                "severity": issue.severity.value,
                "category": issue.category.value,
                "url": issue.url,
            }
            for issue in top_issues
        ],
    }
    return ReportSection(
        title="Site Audit",
        type="audit",
        summary=f"Health score {round(summary.avg_score, 1)}/100 across {summary.total_pages} page(s).",
        data=data,
    )


def _build_rankings_section(rank_summary: RankTrackingSummary) -> ReportSection:
    data: dict[str, object] = {
        "domain": rank_summary.domain,
        "avg_position": round(rank_summary.avg_position, 1),
        "top3": rank_summary.top3,
        "top10": rank_summary.top10,
        "visibility_score": round(rank_summary.visibility_score, 1),
        "improved": rank_summary.improved,
        "declined": rank_summary.declined,
        "unchanged": rank_summary.unchanged,
        "total_keywords": rank_summary.total_keywords,
    }
    return ReportSection(
        title="Keyword Rankings",
        type="rankings",
        summary=(
            f"Average position {round(rank_summary.avg_position, 1)} across "
            f"{rank_summary.total_keywords} tracked keyword(s); {rank_summary.top10} in the top 10."
        ),
        data=data,
    )


def _build_keywords_section(keywords: KeywordResearchResult) -> ReportSection:
    data: dict[str, object] = {
        "seed": keywords.seed,
        "total_keywords": keywords.total_keywords,
        "total_volume": sum(k.search_volume for k in keywords.keywords),
        "clusters": [
            {
                "name": cluster.name,
                "keyword_count": len(cluster.keywords),
                "total_volume": cluster.total_volume,
                "avg_difficulty": round(cluster.avg_difficulty, 1),
            }
            for cluster in keywords.clusters
        ],
    }
    return ReportSection(
        title="Keyword Research",
        type="keywords",
        summary=f"{keywords.total_keywords} keyword(s) across {len(keywords.clusters)} cluster(s).",
        data=data,
    )


def _build_tasks_section(action_plan: ActionPlan) -> ReportSection:
    open_by_priority: dict[str, int] = {}
    for task in action_plan.tasks:
        if task.status == TaskStatus.DONE:
            continue
        open_by_priority[task.priority.value] = open_by_priority.get(task.priority.value, 0) + 1
    open_total = sum(open_by_priority.values())
    data: dict[str, object] = {
        "total_tasks": action_plan.total,
        "open_total": open_total,
        "open_by_priority": open_by_priority,
        "by_status": dict(action_plan.by_status),
    }
    return ReportSection(
        title="Action Plan",
        type="tasks",
        summary=f"{open_total} open task(s) out of {action_plan.total}.",
        data=data,
    )


def build_report(
    site: str,
    period_start: str,
    period_end: str,
    *,
    branding: WhiteLabelBranding | None = None,
    audit: CrawlResult | None = None,
    rank_summary: RankTrackingSummary | None = None,
    keywords: KeywordResearchResult | None = None,
    action_plan: ActionPlan | None = None,
) -> Report:
    """Assemble a branded, section-based :class:`Report` from whichever data sources
    are supplied.

    Each section ('audit', 'rankings', 'keywords', 'tasks') is included only when its
    source data was provided; 'summary' is included whenever at least one other
    section is. ``headline_metrics`` always carries all five keys (``health_score``,
    ``avg_position``, ``top10``, ``open_tasks``, ``tracked_keywords``) — ``None``
    where the relevant source wasn't supplied.
    """
    resolved_branding = apply_branding(branding)

    tracked_keywords: int | None = None
    if keywords is not None:
        tracked_keywords = keywords.total_keywords
    elif rank_summary is not None:
        tracked_keywords = rank_summary.total_keywords

    open_tasks: int | None = None
    if action_plan is not None:
        open_tasks = sum(
            count for status, count in action_plan.by_status.items() if status != TaskStatus.DONE.value
        )

    headline_metrics: dict[str, object] = {
        "health_score": round(audit.summary.avg_score, 1) if audit is not None else None,
        "avg_position": round(rank_summary.avg_position, 1) if rank_summary is not None else None,
        "top10": rank_summary.top10 if rank_summary is not None else None,
        "open_tasks": open_tasks,
        "tracked_keywords": tracked_keywords,
    }

    sections: list[ReportSection] = []
    if audit is not None:
        sections.append(_build_audit_section(audit))
    if rank_summary is not None:
        sections.append(_build_rankings_section(rank_summary))
    if keywords is not None:
        sections.append(_build_keywords_section(keywords))
    if action_plan is not None:
        sections.append(_build_tasks_section(action_plan))
    if sections:
        sections.insert(0, _build_summary_section(site, period_start, period_end, headline_metrics))

    return Report(
        report_id=uuid.uuid4().hex,
        site=site,
        period_start=period_start,
        period_end=period_end,
        generated_at=datetime.now(timezone.utc),
        branding=resolved_branding,
        sections=sections,
        headline_metrics=headline_metrics,
    )


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

_PAGE_STYLE_TEMPLATE = """
  :root { --primary: __PRIMARY__; --accent: __ACCENT__; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif; margin: 0;
    background: #f5f6fa; color: #1f2430; }
  .header { background: var(--primary); color: #fff; padding: 24px 32px;
    display: flex; align-items: center; gap: 16px; }
  .header img.logo { height: 40px; width: auto; border-radius: 4px; background: #fff; }
  .header h1 { margin: 0; font-size: 20px; font-weight: 600; }
  .header p { margin: 4px 0 0; opacity: .85; font-size: 13px; }
  .container { max-width: 920px; margin: 0 auto; padding: 24px 32px 48px; }
  .metrics { display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 28px; }
  .metric-card { background: #fff; border-top: 3px solid var(--accent); border-radius: 6px;
    padding: 14px 20px; min-width: 140px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  .metric-card .value { font-size: 24px; font-weight: 700; color: var(--primary); }
  .metric-card .label { font-size: 11px; text-transform: uppercase; letter-spacing: .04em;
    color: #6b7280; margin-top: 4px; }
  .section { background: #fff; border-radius: 6px; padding: 20px 24px; margin-bottom: 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  .section h2 { margin: 0 0 8px; color: var(--primary); font-size: 16px;
    border-bottom: 2px solid var(--accent); padding-bottom: 8px; }
  .section .summary { color: #374151; font-size: 14px; margin: 0 0 12px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  table th, table td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #e5e7eb;
    vertical-align: top; }
  table th { width: 220px; color: #4b5563; font-weight: 600; }
  ul { margin: 0; padding-left: 18px; }
  .footer { text-align: center; padding: 24px; font-size: 12px; color: #9ca3af; }
""".strip()

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{title}</title>
<style>{style}</style>
</head>
<body>
  <div class="header">
    {logo_html}
    <div>
      <h1>{agency_name} &middot; {site} SEO Report</h1>
      <p>Period: {period} &nbsp;|&nbsp; Generated {generated}</p>
    </div>
  </div>
  <div class="container">
    <div class="metrics">{metrics_html}</div>
    {sections_html}
  </div>
  <div class="footer">{footer_text}</div>
</body>
</html>"""


def _page_style(primary_color: str, accent_color: str) -> str:
    """Fill the CSS custom properties with escaped, user-supplied brand colors."""
    return _PAGE_STYLE_TEMPLATE.replace("__PRIMARY__", html.escape(primary_color)).replace(
        "__ACCENT__", html.escape(accent_color)
    )


def _render_value(value: object) -> str:
    """Escape-safe rendering of an arbitrary JSON-ish value pulled from report data."""
    if value is None:
        return "&mdash;"
    if isinstance(value, dict):
        if not value:
            return "&mdash;"
        rows = "".join(
            f"<tr><th>{html.escape(str(k))}</th><td>{_render_value(v)}</td></tr>" for k, v in value.items()
        )
        return f"<table>{rows}</table>"
    if isinstance(value, (list, tuple)):
        if not value:
            return "&mdash;"
        items = "".join(f"<li>{_render_value(item)}</li>" for item in value)
        return f"<ul>{items}</ul>"
    return html.escape(str(value))


def _render_section(section: ReportSection) -> str:
    return (
        f'<div class="section"><h2>{html.escape(section.title)}</h2>'
        f'<p class="summary">{html.escape(section.summary)}</p>'
        f"{_render_value(section.data)}</div>"
    )


def _render_headline_metrics(metrics: dict[str, object]) -> str:
    cards = []
    for key, label in _HEADLINE_LABELS.items():
        value = metrics.get(key)
        if value is None:
            continue
        cards.append(
            f'<div class="metric-card"><div class="value">{html.escape(str(value))}</div>'
            f'<div class="label">{html.escape(label)}</div></div>'
        )
    return "".join(cards)


def render_report_html(report: Report) -> str:
    """Render ``report`` as a single self-contained, branded HTML document.

    All user- and crawl-derived text (site, agency name, footer, section content,
    task/issue titles, etc.) is passed through :func:`html.escape` before being
    interpolated, so a hostile page title / keyword / branding string cannot break
    out of the markup. Nothing from the process environment or app settings is ever
    read here — the function only touches fields already present on ``report``.
    """
    branding = report.branding
    agency_name = html.escape(branding.agency_name)
    site = html.escape(report.site)
    period = f"{html.escape(report.period_start)} &ndash; {html.escape(report.period_end)}"
    generated = html.escape(report.generated_at.strftime("%Y-%m-%d %H:%M UTC"))
    footer_text = (
        html.escape(branding.footer_text) if branding.footer_text else f"Report generated by {agency_name}."
    )

    logo_html = ""
    if branding.logo_url:
        logo_html = f'<img class="logo" src="{html.escape(branding.logo_url)}" alt="{agency_name} logo" />'

    style = _page_style(branding.primary_color, branding.accent_color)
    metrics_html = _render_headline_metrics(report.headline_metrics)
    sections_html = "".join(_render_section(section) for section in report.sections)

    return _HTML_TEMPLATE.format(
        title=f"{site} SEO Report — {agency_name}",
        style=style,
        logo_html=logo_html,
        agency_name=agency_name,
        site=site,
        period=period,
        generated=generated,
        metrics_html=metrics_html,
        sections_html=sections_html,
        footer_text=footer_text,
    )
