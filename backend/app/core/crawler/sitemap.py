"""XML sitemap generation and parsing (sitemaps.org 0.9 protocol)."""
from __future__ import annotations

from xml.etree import ElementTree as ET

from app.models.audit import SitemapUrl

_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def generate_sitemap(urls: list[str] | list[SitemapUrl]) -> str:
    """Render URLs (plain strings or :class:`SitemapUrl` entries) as a <urlset> XML document."""
    entries: list[SitemapUrl] = [u if isinstance(u, SitemapUrl) else SitemapUrl(loc=u) for u in urls]

    urlset = ET.Element("urlset", {"xmlns": _SITEMAP_NS})
    for entry in entries:
        url_el = ET.SubElement(urlset, "url")
        loc_el = ET.SubElement(url_el, "loc")
        loc_el.text = entry.loc
        if entry.lastmod:
            lastmod_el = ET.SubElement(url_el, "lastmod")
            lastmod_el.text = entry.lastmod
        if entry.changefreq:
            changefreq_el = ET.SubElement(url_el, "changefreq")
            changefreq_el.text = entry.changefreq
        if entry.priority is not None:
            priority_el = ET.SubElement(url_el, "priority")
            priority_el.text = f"{entry.priority:.1f}"

    body = ET.tostring(urlset, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{body}'


def parse_sitemap(xml: str) -> list[SitemapUrl]:
    """Parse a <urlset> sitemap XML document into a list of :class:`SitemapUrl`.

    Accepts documents with or without an XML declaration / namespace. Parsing is
    done from encoded bytes so a leading ``<?xml ... encoding="..."?>`` declaration
    (as produced by :func:`generate_sitemap`) never trips up the parser.
    """
    if not xml or not xml.strip():
        return []

    root = ET.fromstring(xml.encode("utf-8"))
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag[1 : root.tag.index("}")]

    def qualify(name: str) -> str:
        return f"{{{ns}}}{name}" if ns else name

    results: list[SitemapUrl] = []
    for url_el in root.findall(qualify("url")):
        loc_el = url_el.find(qualify("loc"))
        if loc_el is None or not (loc_el.text or "").strip():
            continue

        lastmod_el = url_el.find(qualify("lastmod"))
        changefreq_el = url_el.find(qualify("changefreq"))
        priority_el = url_el.find(qualify("priority"))

        priority: float | None = None
        if priority_el is not None and (priority_el.text or "").strip():
            try:
                priority = float(priority_el.text.strip())
            except ValueError:
                priority = None

        results.append(
            SitemapUrl(
                loc=loc_el.text.strip(),
                lastmod=lastmod_el.text.strip() if lastmod_el is not None and lastmod_el.text else None,
                changefreq=changefreq_el.text.strip()
                if changefreq_el is not None and changefreq_el.text
                else None,
                priority=priority,
            )
        )
    return results
