"""Tests for keyword research, SERP analysis, and rank tracking (app/core/keywords)."""
from __future__ import annotations

from datetime import date

import pytest

from app.core.keywords.clustering import cluster_keywords
from app.core.keywords.providers import (
    DataForSEOKeywordProvider,
    DataForSEOSerpProvider,
    MockKeywordProvider,
    MockSerpProvider,
    get_keyword_provider,
    get_serp_provider,
)
from app.core.keywords.rank_tracker import RankTracker, ctr_for_position
from app.core.keywords.research import research_keywords
from app.core.keywords.serp import analyze_serp
from app.models.common import Device
from app.models.keywords import Keyword, KeywordResearchRequest, SerpAnalysis
from app.services.store import InMemoryStore


class _SiteRankingSerpProvider(MockSerpProvider):
    """Deterministic test double.

    Delegates to the real MockSerpProvider and then forces ``domain`` into
    ``position`` for exactly one keyword, so a poll() run has a guaranteed,
    predictable ranking to assert on.
    """

    def __init__(self, ranking_keyword: str, domain: str = "site.test", position: int = 2) -> None:
        self._ranking_keyword = ranking_keyword
        self._domain = domain
        self._position = position

    def fetch_serp(
        self, keyword: str, country: str = "us", device: Device = Device.DESKTOP
    ) -> SerpAnalysis:
        analysis = super().fetch_serp(keyword, country=country, device=device)
        if keyword != self._ranking_keyword:
            return analysis
        results = list(analysis.results)
        idx = self._position - 1
        results[idx] = results[idx].model_copy(
            update={"url": f"https://{self._domain}/page", "domain": self._domain}
        )
        return analysis.model_copy(update={"results": results})


# ---------------------------------------------------------------------------
# Keyword research
# ---------------------------------------------------------------------------


def test_research_keywords_returns_limit_and_clusters():
    req = KeywordResearchRequest(seed="running shoes", limit=20)
    result = research_keywords(req)
    assert len(result.keywords) == 20
    assert result.total_keywords == 20
    assert len(result.clusters) > 0
    assert all(isinstance(k, Keyword) for k in result.keywords)


def test_research_keywords_is_deterministic():
    req = KeywordResearchRequest(seed="running shoes", limit=20)
    result1 = research_keywords(req)
    result2 = research_keywords(req)
    assert [k.keyword for k in result1.keywords] == [k.keyword for k in result2.keywords]
    assert result1.keywords == result2.keywords
    assert [c.name for c in result1.clusters] == [c.name for c in result2.clusters]


def test_mock_keyword_provider_intent_and_scores():
    provider = MockKeywordProvider()
    req = KeywordResearchRequest(seed="running shoes", limit=40, include_questions=True)
    keywords = provider.research(req)
    by_text = {k.keyword: k for k in keywords}

    assert by_text["running shoes near me"].intent.value in ("transactional", "commercial")
    assert by_text["what is running shoes"].intent.value == "informational"
    assert all(0 <= k.difficulty <= 100 for k in keywords)
    assert all(0.0 <= k.competition <= 1.0 for k in keywords)
    assert all(k.parent_topic == "running shoes" for k in keywords)


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------


def test_cluster_keywords_groups_by_topic_and_orders_by_volume():
    keywords = [
        Keyword(keyword="best running shoes", search_volume=1000, difficulty=40),
        Keyword(keyword="running shoes near me", search_volume=500, difficulty=30),
        Keyword(keyword="cheap yoga mats", search_volume=2000, difficulty=20),
        Keyword(keyword="yoga mats reviews", search_volume=800, difficulty=25),
    ]
    clusters = cluster_keywords(keywords)
    assert len(clusters) == 2
    # Highest total_volume cluster (yoga mats: 2800) sorts first.
    assert clusters[0].total_volume == 2800
    assert clusters[1].total_volume == 1500
    assert {len(c.keywords) for c in clusters} == {2}


# ---------------------------------------------------------------------------
# SERP analysis
# ---------------------------------------------------------------------------


def test_analyze_serp_returns_ten_results_with_positive_avg_word_count():
    analysis = analyze_serp("running shoes")
    assert len(analysis.results) == 10
    assert analysis.avg_word_count > 0
    assert analysis.avg_backlinks > 0
    assert [r.position for r in analysis.results] == list(range(1, 11))


def test_analyze_serp_is_deterministic():
    a1 = analyze_serp("running shoes")
    a2 = analyze_serp("running shoes")
    assert a1 == a2


# ---------------------------------------------------------------------------
# Providers / factories
# ---------------------------------------------------------------------------


def test_default_providers_are_mock():
    assert isinstance(get_keyword_provider(), MockKeywordProvider)
    assert isinstance(get_serp_provider(), MockSerpProvider)


def test_dataforseo_stubs_raise_not_implemented():
    with pytest.raises(NotImplementedError):
        DataForSEOKeywordProvider().research(KeywordResearchRequest(seed="x", limit=5))
    with pytest.raises(NotImplementedError):
        DataForSEOSerpProvider().fetch_serp("x")


# ---------------------------------------------------------------------------
# Rank tracking
# ---------------------------------------------------------------------------


def test_rank_tracker_poll_and_build_summary():
    store = InMemoryStore()
    provider = _SiteRankingSerpProvider(ranking_keyword="running shoes", domain="site.test", position=2)
    tracker = RankTracker(store=store, serp_provider=provider)

    tracker.add_keywords(
        "site.test",
        "us",
        ["running shoes", "yoga mats", "hiking boots"],
        search_volumes={"running shoes": 1000, "yoga mats": 500, "hiking boots": 300},
    )
    tracker.poll("site.test", "us")
    summary = tracker.build_summary("site.test", "us")

    assert summary.total_keywords == 3
    assert 0.0 <= summary.visibility_score <= 100.0
    assert summary.top10 >= 1

    by_keyword = {k.keyword: k for k in summary.keywords}
    assert by_keyword["running shoes"].current_position == 2
    assert by_keyword["yoga mats"].current_position is None
    assert by_keyword["hiking boots"].current_position is None
    assert summary.avg_position == 2.0


def test_record_positions_twice_updates_previous_position_and_delta():
    store = InMemoryStore()
    tracker = RankTracker(store=store, serp_provider=MockSerpProvider())
    tracker.add_keywords("site.test", "us", ["running shoes"], search_volumes={"running shoes": 100})

    tracker.record_positions(
        "site.test", "us", {"running shoes": (8, "https://site.test/a")}, day=date(2026, 7, 1)
    )
    tracker.record_positions(
        "site.test", "us", {"running shoes": (3, "https://site.test/b")}, day=date(2026, 7, 2)
    )

    tracked = store.get_tracked("site.test", "us")
    kw = next(t for t in tracked if t.keyword == "running shoes")
    assert kw.previous_position == 8
    assert kw.current_position == 3
    assert kw.delta == 5
    assert kw.best_position == 3
    assert len(kw.history) == 2


# ---------------------------------------------------------------------------
# CTR curve
# ---------------------------------------------------------------------------


def test_ctr_for_position_curve():
    assert ctr_for_position(1) > ctr_for_position(10) > 0
    assert ctr_for_position(None) == 0
    assert ctr_for_position(1) == pytest.approx(0.28)
