"""HTML parsing helpers shared by the crawler and on-page analyzer.

Centralized here so both engines extract head/meta/links/images identically.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from app.utils.text import word_count
from app.utils.url import normalize_url


@dataclass
class ParsedLink:
    href: str
    anchor: str = ""
    rel: str = ""


@dataclass
class ParsedImage:
    src: str
    alt: str | None = None


@dataclass
class ParsedPage:
    title: str | None = None
    meta_description: str | None = None
    meta_robots: str | None = None
    canonical: str | None = None
    lang: str | None = None
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    h3: list[str] = field(default_factory=list)
    hreflang: list[tuple[str, str]] = field(default_factory=list)
    links: list[ParsedLink] = field(default_factory=list)
    images: list[ParsedImage] = field(default_factory=list)
    json_ld_types: list[str] = field(default_factory=list)
    text: str = ""
    word_count: int = 0
    og_tags: dict[str, str] = field(default_factory=dict)
    twitter_tags: dict[str, str] = field(default_factory=dict)


def _collect_schema_types(data: object, out: list[str]) -> None:
    if isinstance(data, dict):
        t = data.get("@type")
        if isinstance(t, str):
            out.append(t)
        elif isinstance(t, list):
            out.extend(x for x in t if isinstance(x, str))
        for value in data.values():
            _collect_schema_types(value, out)
    elif isinstance(data, list):
        for item in data:
            _collect_schema_types(item, out)


def parse_html(html: str, base_url: str | None = None) -> ParsedPage:
    """Parse an HTML string into a structured :class:`ParsedPage`."""
    soup = BeautifulSoup(html or "", "lxml")
    page = ParsedPage()

    if soup.title and soup.title.string:
        page.title = soup.title.string.strip()

    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        page.lang = html_tag.get("lang")

    for meta in soup.find_all("meta"):
        name = (meta.get("name") or "").lower()
        prop = (meta.get("property") or "").lower()
        content = meta.get("content")
        if content is None:
            continue
        if name == "description":
            page.meta_description = content.strip()
        elif name == "robots":
            page.meta_robots = content.strip()
        elif prop.startswith("og:"):
            page.og_tags[prop] = content
        elif name.startswith("twitter:"):
            page.twitter_tags[name] = content

    for link in soup.find_all("link"):
        rels = [r.lower() for r in (link.get("rel") or [])]
        href = link.get("href")
        if not href:
            continue
        if "canonical" in rels:
            page.canonical = normalize_url(href, base_url) if base_url else href
        if "alternate" in rels and link.get("hreflang"):
            page.hreflang.append((link.get("hreflang"), href))

    page.h1 = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    page.h2 = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
    page.h3 = [h.get_text(" ", strip=True) for h in soup.find_all("h3")]

    for a in soup.find_all("a"):
        href = a.get("href")
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        resolved = normalize_url(href, base_url) if base_url else href
        rel = " ".join(a.get("rel") or [])
        page.links.append(ParsedLink(href=resolved, anchor=a.get_text(" ", strip=True), rel=rel))

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue
        resolved = normalize_url(src, base_url) if base_url else src
        page.images.append(ParsedImage(src=resolved, alt=img.get("alt")))

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            _collect_schema_types(json.loads(raw), page.json_ld_types)
        except (json.JSONDecodeError, ValueError):
            continue

    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    body = soup.body or soup
    page.text = body.get_text(" ", strip=True)
    page.word_count = word_count(page.text)
    return page
