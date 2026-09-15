"""SERP analysis: fetch via a SerpProvider and normalize aggregate metrics."""
from __future__ import annotations

from app.core.keywords.providers import SerpProvider, compute_serp_metrics, get_serp_provider
from app.models.common import Device
from app.models.keywords import SerpAnalysis


def analyze_serp(
    keyword: str,
    provider: SerpProvider | None = None,
    country: str = "us",
    device: Device = Device.DESKTOP,
) -> SerpAnalysis:
    """Fetch a SERP via ``provider`` (default: the configured SerpProvider).

    ``avg_word_count`` / ``avg_backlinks`` / ``difficulty`` are always
    recomputed from ``results`` here (via
    :func:`~app.core.keywords.providers.compute_serp_metrics`) so the
    aggregates stay internally consistent regardless of what the underlying
    provider filled in.
    """
    provider = provider or get_serp_provider()
    analysis = provider.fetch_serp(keyword, country=country, device=device)
    avg_word_count, avg_backlinks, difficulty = compute_serp_metrics(analysis.results)
    return analysis.model_copy(
        update={
            "keyword": keyword,
            "country": country,
            "device": device,
            "avg_word_count": avg_word_count,
            "avg_backlinks": avg_backlinks,
            "difficulty": difficulty,
        }
    )
