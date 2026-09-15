"""Continuous-audit advisor: turns audit findings into plain-English action items.

Each finding is matched to a guided instruction template (per issue code, falling
back to the issue category, then to a generic template) that assumes no dev
experience. Ids are stable sha256 hashes of ``site|code|page`` — mirroring
:mod:`app.core.reporting.tasks` — so re-running yields identical items. Pure and
deterministic: no randomness, no network/IO.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.reporting.tasks import generate_action_plan
from app.models.assistant import ActionItem, ActionItemPlan, FixStep
from app.models.audit import CrawlResult
from app.models.common import Issue, IssueCategory, Severity
from app.models.keywords import RankTrackingSummary
from app.models.reporting import Task


@dataclass(frozen=True)
class _FixTemplate:
    """Plain-English explanation + guided steps for one kind of finding."""

    what_it_means: str
    why_it_matters: str
    steps: tuple[str, ...]
    estimated_minutes: int = 15


_CODE_TEMPLATES: dict[str, _FixTemplate] = {
    "missing_title": _FixTemplate(
        what_it_means="This page has no title tag — the headline shown in Google results.",
        why_it_matters="Without a title, Google guesses what your page is about and fewer people click your result.",
        steps=(
            "Log in to your website editor (WordPress, Wix, Squarespace, etc.).",
            "Open the page {page} for editing.",
            "Find the 'SEO' or 'Page settings' panel and locate the 'Title' field.",
            "Write a 50-60 character title that describes the page and includes your main keyword.",
            "Save and publish the page, then reload it to confirm the new title appears in the browser tab.",
        ),
        estimated_minutes=10,
    ),
    "missing_meta_description": _FixTemplate(
        what_it_means="This page has no meta description — the short blurb shown under your title in Google.",
        why_it_matters="A clear description convinces more searchers to click your result instead of a competitor's.",
        steps=(
            "Log in to your website editor.",
            "Open the page {page} for editing.",
            "Find the 'SEO' or 'Search appearance' panel and locate the 'Meta description' field.",
            "Write a 150-160 character summary of the page that reads like a small ad and mentions your keyword.",
            "Save and publish the page.",
        ),
        estimated_minutes=10,
    ),
    "duplicate_title": _FixTemplate(
        what_it_means="Two or more of your pages share the exact same title.",
        why_it_matters="Google struggles to decide which page to show, so both pages can rank worse.",
        steps=(
            "Open the page {page} for editing in your website editor.",
            "Rewrite its title so it describes what makes this page different from the others.",
            "Repeat for every page that shares this title, giving each one a unique title.",
            "Save and publish the changes.",
        ),
        estimated_minutes=20,
    ),
    "missing_h1": _FixTemplate(
        what_it_means="This page has no main headline (an 'H1' heading).",
        why_it_matters="The main headline tells visitors and Google what the page is about at a glance.",
        steps=(
            "Open the page {page} for editing.",
            "Add one clear headline at the very top of the page content.",
            "In the text style dropdown, set that headline to 'Heading 1' (H1).",
            "Make sure it mentions the topic or keyword the page targets, then save.",
        ),
        estimated_minutes=10,
    ),
    "thin_content": _FixTemplate(
        what_it_means="This page has very little text on it.",
        why_it_matters="Pages with thin content rarely rank because Google prefers pages that fully answer a question.",
        steps=(
            "Open the page {page} and read it as if you were a first-time visitor.",
            "List the questions a visitor would still have after reading it.",
            "Write new sections that answer those questions — aim for at least 600 words in total.",
            "Add subheadings every few paragraphs so the page is easy to scan.",
            "Save and publish the expanded page.",
        ),
        estimated_minutes=60,
    ),
    "broken_link": _FixTemplate(
        what_it_means="A link on this page points to a page that no longer exists (a '404' error).",
        why_it_matters="Broken links frustrate visitors and waste the trust Google places in your site.",
        steps=(
            "Open the page {page} for editing.",
            "Click each link on the page (or use the audit detail) to find the one that shows an error.",
            "Either update the link to the correct address or remove it entirely.",
            "Save and publish, then click the link again to confirm it now works.",
        ),
        estimated_minutes=10,
    ),
    "missing_alt_text": _FixTemplate(
        what_it_means="One or more images on this page have no 'alt text' (a written description).",
        why_it_matters="Alt text helps Google understand your images and makes your site usable for visitors with screen readers.",
        steps=(
            "Open the page {page} for editing.",
            "Click each image and look for an 'Alt text' or 'Description' field.",
            "Describe what the image shows in one short sentence.",
            "Save and publish the page.",
        ),
        estimated_minutes=10,
    ),
    "slow_page": _FixTemplate(
        what_it_means="This page takes a long time to load.",
        why_it_matters="Slow pages lose visitors before they even see your content, and Google ranks slow sites lower.",
        steps=(
            "Open the page {page} and note which images or sections load slowly.",
            "Compress large images before uploading them (free tools like tinypng.com work well).",
            "Remove any plugins, embeds, or scripts the page does not really need.",
            "If the whole site is slow, ask your hosting provider about a faster plan or enabling caching.",
        ),
        estimated_minutes=45,
    ),
}

_CATEGORY_TEMPLATES: dict[IssueCategory, _FixTemplate] = {
    IssueCategory.ON_PAGE: _FixTemplate(
        what_it_means="Something in this page's basic setup (titles, descriptions, headings) needs attention.",
        why_it_matters="These basics are the easiest wins in SEO — small edits here often move rankings.",
        steps=(
            "Open the page {page} in your website editor.",
            "Follow the recommendation shown for this finding.",
            "Save and publish, then re-run the audit to confirm the issue is resolved.",
        ),
        estimated_minutes=15,
    ),
    IssueCategory.CONTENT: _FixTemplate(
        what_it_means="The written content on this page can be improved.",
        why_it_matters="Better content keeps visitors on the page longer, which helps rankings and sales.",
        steps=(
            "Open the page {page} and read the audit recommendation for this finding.",
            "Update the text following that recommendation — write for people first, keywords second.",
            "Save and publish the page.",
        ),
        estimated_minutes=30,
    ),
    IssueCategory.LINKS: _FixTemplate(
        what_it_means="There is a problem with links on this page.",
        why_it_matters="Working links help visitors and Google move through your site smoothly.",
        steps=(
            "Open the page {page} for editing.",
            "Review the links mentioned in this finding and fix or remove the problematic ones.",
            "Save and publish, then click through the links to double-check them.",
        ),
        estimated_minutes=15,
    ),
    IssueCategory.IMAGES: _FixTemplate(
        what_it_means="Images on this page need attention (descriptions, size, or format).",
        why_it_matters="Well-prepared images load faster and give Google extra ranking signals.",
        steps=(
            "Open the page {page} for editing and click each image.",
            "Add missing descriptions (alt text) and replace overly large files with compressed versions.",
            "Save and publish the page.",
        ),
        estimated_minutes=15,
    ),
    IssueCategory.TECHNICAL: _FixTemplate(
        what_it_means="A technical setting on your site needs attention.",
        why_it_matters="Technical problems can quietly stop Google from finding or trusting your pages.",
        steps=(
            "Copy the recommendation for this finding.",
            "If you use a website builder, search its help center for the setting mentioned.",
            "If your site was custom-built, forward the recommendation to whoever maintains it.",
            "Re-run the audit afterwards to confirm the fix.",
        ),
        estimated_minutes=30,
    ),
    IssueCategory.INDEXABILITY: _FixTemplate(
        what_it_means="Google may be blocked from showing this page in search results.",
        why_it_matters="If Google cannot index a page, it can never rank — no matter how good it is.",
        steps=(
            "Open the page {page} settings in your website editor.",
            "Look for a toggle like 'Hide from search engines' or 'noindex' and turn it OFF if the page should rank.",
            "Save and publish, then re-run the audit to confirm the page is indexable.",
        ),
        estimated_minutes=10,
    ),
    IssueCategory.PERFORMANCE: _FixTemplate(
        what_it_means="This page or site loads slower than it should.",
        why_it_matters="Every extra second of load time costs visitors, sales, and ranking positions.",
        steps=(
            "Compress large images before uploading them.",
            "Remove unused plugins, embeds, or scripts.",
            "Ask your hosting provider about caching or a faster plan if the whole site is slow.",
        ),
        estimated_minutes=45,
    ),
    IssueCategory.STRUCTURED_DATA: _FixTemplate(
        what_it_means="This page is missing structured data — extra labels that describe your content to Google.",
        why_it_matters="Structured data can win richer search listings (stars, prices, FAQs) that get more clicks.",
        steps=(
            "If you use WordPress, install an SEO plugin (like Yoast or Rank Math) — it adds structured data automatically.",
            "Otherwise, use Google's free 'Structured Data Markup Helper' to generate the code for {page}.",
            "Paste the generated code into the page's custom-code / header area and publish.",
        ),
        estimated_minutes=30,
    ),
    IssueCategory.INTERNATIONAL: _FixTemplate(
        what_it_means="Settings that tell Google which language/country a page targets need attention.",
        why_it_matters="Correct language targeting shows the right page to the right audience.",
        steps=(
            "Note the pages and languages mentioned in this finding.",
            "In your website platform, review the language / region settings for those pages.",
            "If your site was custom-built, forward the recommendation to whoever maintains it.",
        ),
        estimated_minutes=30,
    ),
    IssueCategory.SECURITY: _FixTemplate(
        what_it_means="A security-related setting (like HTTPS) needs attention.",
        why_it_matters="Browsers warn visitors away from insecure sites, and Google ranks them lower.",
        steps=(
            "Log in to your hosting or domain provider's dashboard.",
            "Enable the free SSL/HTTPS option (most providers offer one-click setup).",
            "Confirm your site loads with a padlock icon at https:// afterwards.",
        ),
        estimated_minutes=30,
    ),
    IssueCategory.MOBILE: _FixTemplate(
        what_it_means="This page does not work well on phones.",
        why_it_matters="Most searches happen on mobile, and Google ranks the mobile version of your site.",
        steps=(
            "Open {page} on your own phone and note anything that is hard to read or tap.",
            "In your website editor, use the mobile preview to fix those spots.",
            "Save and publish, then check on your phone again.",
        ),
        estimated_minutes=30,
    ),
    IssueCategory.LOCAL: _FixTemplate(
        what_it_means="A local-search detail (business name, address, phone, or hours) needs attention.",
        why_it_matters="Consistent business details across the web are a major local ranking factor.",
        steps=(
            "Write down your exact business name, address, and phone number as they should appear everywhere.",
            "Update your Google Business Profile and website footer to match exactly.",
            "Use the citation sync tool to push the same details to Yelp, Apple Maps, Bing Places, and Foursquare.",
        ),
        estimated_minutes=30,
    ),
}

_GENERIC_TEMPLATE = _FixTemplate(
    what_it_means="The audit found something on your site that can be improved.",
    why_it_matters="Fixing audit findings — even small ones — steadily improves how your site ranks.",
    steps=(
        "Read the recommendation attached to this finding.",
        "Apply the change in your website editor, or forward it to whoever maintains your site.",
        "Re-run the audit to confirm the finding is resolved.",
    ),
    estimated_minutes=20,
)

_QUICK_WIN_TEMPLATE = _FixTemplate(
    what_it_means="This keyword already ranks on page 2 of Google — it is 'almost there'.",
    why_it_matters="Page-2 keywords are usually the fastest wins: a small push often lands them on page 1.",
    steps=(
        "Open the page that ranks for this keyword and re-read it for freshness and completeness.",
        "Add a new section or updated statistics so the page clearly beats what currently ranks above it.",
        "Add 2-3 links to this page from other related pages on your site.",
        "Make sure the keyword appears in the page title and main headline.",
    ),
    estimated_minutes=45,
)


def _make_item_id(site: str, code: str, page: str) -> str:
    """Stable, deterministic id derived from ``site + code + page``."""
    raw = f"{site}|{code}|{page or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _template_for(code: str, category: IssueCategory) -> _FixTemplate:
    return _CODE_TEMPLATES.get(code) or _CATEGORY_TEMPLATES.get(category) or _GENERIC_TEMPLATE


def _render_steps(template: _FixTemplate, page: str | None, site: str) -> list[FixStep]:
    page_label = page or "the affected page"
    return [
        FixStep(number=i, instruction=raw.format(page=page_label, site=site))
        for i, raw in enumerate(template.steps, start=1)
    ]


def _item_from_issue(site: str, issue: Issue) -> ActionItem:
    """Convert one audit :class:`Issue` into a guided :class:`ActionItem`."""
    template = _template_for(issue.code, issue.category)
    what = issue.description.strip() or template.what_it_means
    return ActionItem(
        id=_make_item_id(site, issue.code, issue.url or ""),
        title=issue.title,
        what_it_means=what,
        why_it_matters=template.why_it_matters,
        category=issue.category,
        severity=issue.severity,
        priority_score=issue.severity.weight * 20,
        page_url=issue.url,
        keyword=None,
        source_code=issue.code,
        steps=_render_steps(template, issue.url, site),
        estimated_minutes=template.estimated_minutes,
    )


def _item_from_quick_win(site: str, task: Task) -> ActionItem:
    """Convert a rank quick-win :class:`Task` (from reporting/tasks) into an item."""
    return ActionItem(
        id=_make_item_id(site, "rank:quick_win", task.keyword or ""),
        title=task.title,
        what_it_means=task.description,
        why_it_matters=_QUICK_WIN_TEMPLATE.why_it_matters,
        category=task.category,
        severity=task.priority,
        priority_score=task.priority.weight * 20,
        page_url=task.page_url,
        keyword=task.keyword,
        source_code="rank:quick_win",
        steps=_render_steps(_QUICK_WIN_TEMPLATE, task.page_url, site),
        estimated_minutes=_QUICK_WIN_TEMPLATE.estimated_minutes,
    )


def build_action_items(
    site: str,
    audit: CrawlResult | None = None,
    issues: list[Issue] | None = None,
    rank_summary: RankTrackingSummary | None = None,
) -> ActionItemPlan:
    """Build a deduplicated, prioritized :class:`ActionItemPlan` for ``site``.

    Sources (all optional, independently combinable):
      * ``audit`` — every :class:`Issue` on every crawled page becomes an item.
      * ``issues`` — extra findings supplied directly (e.g. from an API body).
      * ``rank_summary`` — page-2 keywords become quick-win items, reusing the
        rank logic from :func:`app.core.reporting.tasks.generate_action_plan`.
    """
    items: list[ActionItem] = []

    if audit is not None:
        for page in audit.pages:
            for issue in page.issues:
                located = issue if issue.url else issue.model_copy(update={"url": page.url})
                items.append(_item_from_issue(site, located))

    for issue in issues or []:
        items.append(_item_from_issue(site, issue))

    if rank_summary is not None:
        rank_plan = generate_action_plan(site, rank_summary=rank_summary)
        for task in rank_plan.tasks:
            items.append(_item_from_quick_win(site, task))

    deduped: dict[str, ActionItem] = {}
    for item in items:
        deduped.setdefault(item.id, item)
    unique = list(deduped.values())
    unique.sort(key=lambda i: (-i.priority_score, i.title, i.id))

    by_severity: dict[str, int] = {}
    for item in unique:
        by_severity[item.severity.value] = by_severity.get(item.severity.value, 0) + 1

    return ActionItemPlan(
        site=site,
        generated_at=datetime.now(timezone.utc),
        items=unique,
        total=len(unique),
        by_severity=by_severity,
    )
