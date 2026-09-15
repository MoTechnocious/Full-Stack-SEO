"""URL normalization and same-site logic (no network / no external deps)."""
from __future__ import annotations

from urllib.parse import urljoin, urlsplit, urlunsplit

# Common multi-label public suffixes so "bbc.co.uk" is treated as one registrable domain.
_MULTI_PART_TLDS = {
    "co.uk", "org.uk", "gov.uk", "ac.uk", "me.uk", "co.nz", "co.za", "com.au",
    "net.au", "org.au", "co.jp", "co.in", "com.br", "com.mx", "com.sg", "co.kr",
}


def is_http_url(url: str) -> bool:
    return urlsplit(url).scheme in {"http", "https"}


def normalize_url(url: str, base: str | None = None) -> str:
    """Resolve against ``base``, drop fragments, lowercase host, strip default ports."""
    if base:
        url = urljoin(base, url)
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    host = parts.hostname or ""
    host = host.lower()
    port = parts.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    else:
        netloc = host
    if parts.username:
        creds = parts.username + (f":{parts.password}" if parts.password else "")
        netloc = f"{creds}@{netloc}"
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def get_host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def registrable_domain(url_or_host: str) -> str:
    """Return the registrable domain (eTLD+1) using a small multi-part TLD list."""
    host = url_or_host
    if "://" in url_or_host or url_or_host.startswith("//"):
        host = get_host(url_or_host)
    host = host.strip(".").lower()
    if host.startswith("www."):
        host = host[4:]
    labels = host.split(".")
    if len(labels) <= 2:
        return ".".join(labels)
    last2 = ".".join(labels[-2:])
    if last2 in _MULTI_PART_TLDS:
        return ".".join(labels[-3:])
    return last2


def is_internal(url: str, root: str) -> bool:
    """True when ``url`` shares a registrable domain with ``root``."""
    try:
        return registrable_domain(url) == registrable_domain(root)
    except Exception:
        return False


def strip_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
