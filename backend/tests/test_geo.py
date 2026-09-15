"""Tests for the GEO module (app/core/geo + /geo API routes). Fully offline."""
from __future__ import annotations

from datetime import date

import pytest

from app.core.geo.citations import (
    aggregate_domains,
    build_domain_trust_report,
    classify_domain,
    scan_citations,
)
from app.core.geo.prompts import (
    add_prompt,
    build_prompt_tracker,
    classify_funnel_stage,
    estimate_prompt_volume,
    list_prompts,
    research_prompts,
)
from app.core.geo.providers import (
    LiveAnswerEngineProvider,
    LiveArtifactFetcher,
    MockAnswerEngineProvider,
    MockArtifactFetcher,
    get_answer_engine_provider,
    get_artifact_fetcher,
)
from app.core.geo.readiness import ai_crawler_access, audit_readiness
from app.core.geo.sentiment import scan_sentiment, score_sentiment
from app.core.geo.store import GeoStore, reset_geo_store
from app.core.geo.visibility import rank_in_list, scan_visibility
from app.models.common import Severity
from app.models.geo import (
    AnswerEngine,
    Citation,
    DomainCategory,
    EngineAnswer,
    FunnelStage,
    PromptCreate,
    PromptResearchRequest,
    SentimentLabel,
    SiteArtifacts,
)
from app.version import API_VERSION

API = f"/api/{API_VERSION}"
ALL_ENGINES = list(AnswerEngine)


@pytest.fixture(autouse=True)
def _fresh_geo_store():
    """The module-level GeoStore is a process singleton — reset around every test."""
    reset_geo_store()
    yield
    reset_geo_store()


class _ScriptedAnswerProvider:
    """Deterministic test double with fully controlled mentions, ranks, citations.

    Every answer mentions the brand once, each competitor twice, ranks the
    brand at ``brand_rank`` (1-based) behind the first competitor, and cites a
    fixed reddit URL — so visibility math has exact expected values.
    """

    def __init__(self, brand_rank: int = 2) -> None:
        self.brand_rank = brand_rank

    def ask(
        self,
        engine: AnswerEngine,
        prompt: str,
        brand: str,
        competitors: list[str] | None = None,
    ) -> EngineAnswer:
        competitors = competitors or []
        text = f"{brand} is excellent. " + " ".join(
            f"{c} is fine. {c} shows up again." for c in competitors
        )
        ranked = [*competitors, "FillerOne", "FillerTwo"]
        ranked.insert(min(self.brand_rank - 1, len(ranked)), brand)
        return EngineAnswer(
            engine=engine,
            prompt=prompt,
            text=text,
            ranked_list=ranked,
            citations=[Citation(url="https://reddit.com/r/x", domain="reddit.com", title="thread")],
        )


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


def test_mock_answer_provider_is_deterministic():
    provider = MockAnswerEngineProvider()
    a1 = provider.ask(AnswerEngine.CHATGPT, "best crm software", "AcmeCRM", ["RivalCo"])
    a2 = provider.ask(AnswerEngine.CHATGPT, "best crm software", "AcmeCRM", ["RivalCo"])
    assert a1 == a2
    assert a1.engine == AnswerEngine.CHATGPT
    assert 3 <= len(a1.citations) <= 6
    assert a1.ranked_list  # never empty thanks to filler rivals


def test_mock_answer_provider_varies_by_engine():
    provider = MockAnswerEngineProvider()
    answers = [provider.ask(e, "best crm software", "AcmeCRM", ["RivalCo"]) for e in ALL_ENGINES]
    assert len({a.text for a in answers}) > 1  # engines do not all say the same thing


def test_default_providers_are_mock():
    assert isinstance(get_answer_engine_provider(), MockAnswerEngineProvider)
    assert isinstance(get_artifact_fetcher(), MockArtifactFetcher)


def test_live_stubs_raise_not_implemented():
    with pytest.raises(NotImplementedError):
        LiveAnswerEngineProvider().ask(AnswerEngine.CLAUDE, "x", "Brand")
    with pytest.raises(NotImplementedError):
        LiveArtifactFetcher().fetch_site("https://example.com")


# ---------------------------------------------------------------------------
# Cross-LLM visibility
# ---------------------------------------------------------------------------


def test_rank_in_list_is_case_insensitive():
    assert rank_in_list("acme", ["RivalCo", "Acme", "Other"]) == 2
    assert rank_in_list("missing", ["RivalCo"]) is None


def test_scan_visibility_exact_metrics_with_scripted_provider():
    store = GeoStore()
    report = scan_visibility(
        "org1",
        "AcmeCRM",
        ["best crm", "top crm tools"],
        competitors=["RivalCo"],
        engines=[AnswerEngine.CHATGPT, AnswerEngine.GEMINI],
        provider=_ScriptedAnswerProvider(brand_rank=2),
        store=store,
        day=date(2026, 7, 1),
    )
    # Per answer: brand mentioned once, competitor twice -> SOV = 4 / (4 + 8).
    assert report.overall.prompts_scanned == 4
    assert report.overall.mentions == 4
    assert report.overall.mention_frequency == 1.0
    assert report.overall.share_of_voice == pytest.approx(1 / 3, abs=1e-4)
    assert report.overall.avg_position == 2.0
    assert report.competitor_share_of_voice["RivalCo"] == pytest.approx(2 / 3, abs=1e-4)
    assert {ev.engine for ev in report.engines} == {AnswerEngine.CHATGPT, AnswerEngine.GEMINI}
    for ev in report.engines:
        assert ev.avg_position == 2.0
        assert ev.mention_frequency == 1.0
    # First scan has no prior snapshot to diff against.
    assert report.overall.share_of_voice_delta is None


def test_scan_visibility_trend_deltas_against_previous_scan():
    store = GeoStore()
    kwargs = dict(
        competitors=["RivalCo"],
        engines=[AnswerEngine.PERPLEXITY],
        store=store,
    )
    scan_visibility("org1", "AcmeCRM", ["best crm"], provider=_ScriptedAnswerProvider(brand_rank=3), **kwargs)
    second = scan_visibility(
        "org1", "AcmeCRM", ["best crm"], provider=_ScriptedAnswerProvider(brand_rank=1), **kwargs
    )
    assert second.overall.mention_frequency_delta == 0.0
    assert second.overall.share_of_voice_delta == 0.0
    # Moved from rank 3 to rank 1 -> positive improvement delta of 2.
    assert second.overall.avg_position_delta == 2.0
    assert second.engines[0].avg_position_delta == 2.0
    # History is org-scoped: another org sees no prior scans.
    assert store.visibility_history("org2", "AcmeCRM") == []
    assert len(store.visibility_history("org1", "AcmeCRM")) == 2


def test_scan_visibility_defaults_to_all_six_engines_and_is_deterministic():
    r1 = scan_visibility("org1", "AcmeCRM", ["best crm"], store=GeoStore())
    r2 = scan_visibility("org1", "AcmeCRM", ["best crm"], store=GeoStore())
    assert [ev.engine for ev in r1.engines] == ALL_ENGINES
    assert r1.overall == r2.overall
    assert 0.0 <= r1.overall.mention_frequency <= 1.0
    assert 0.0 <= r1.overall.share_of_voice <= 1.0


# ---------------------------------------------------------------------------
# Prompt library, research, tracker
# ---------------------------------------------------------------------------


def test_classify_funnel_stage_heuristics():
    assert classify_funnel_stage("how does crm software work") == FunnelStage.TOFU
    assert classify_funnel_stage("best crm compared to alternatives") == FunnelStage.MOFU
    assert classify_funnel_stage("crm pricing per month") == FunnelStage.BOFU


def test_add_prompt_fills_defaults_and_is_idempotent():
    store = GeoStore()
    p1 = add_prompt("org1", PromptCreate(text="what is the best crm pricing plan"), store=store)
    p2 = add_prompt("org1", PromptCreate(text="  What is the best CRM pricing plan  "), store=store)
    assert p1.id == p2.id  # normalized-text idempotency
    assert p1.funnel_stage == FunnelStage.BOFU  # "pricing" marker wins
    assert p1.volume_estimate == estimate_prompt_volume("what is the best crm pricing plan")
    assert p1.intent_tags == ["purchase", "high-intent"]
    assert len(list_prompts("org1", store=store)) == 1
    assert list_prompts("org2", store=store) == []  # org isolation


def test_research_prompts_deterministic_with_stage_mix():
    req = PromptResearchRequest(topic="crm software", limit=20)
    r1 = research_prompts(req)
    r2 = research_prompts(req)
    assert r1 == r2
    assert r1.total == 20
    assert all(s.text and s.volume_estimate >= 50 for s in r1.suggestions)
    stages = {s.funnel_stage for s in r1.suggestions}
    assert {FunnelStage.TOFU, FunnelStage.MOFU, FunnelStage.BOFU} <= stages


def test_research_prompts_limit_beyond_template_pool():
    result = research_prompts(PromptResearchRequest(topic="crm", limit=40))
    assert result.total == 40
    assert len({s.text for s in result.suggestions}) == 40


def test_prompt_tracker_rolls_history_forward():
    store = GeoStore()
    add_prompt("org1", PromptCreate(text="best crm for startups"), store=store)
    engines = [AnswerEngine.CHATGPT]

    build_prompt_tracker(
        "org1", "AcmeCRM", competitors=["RivalCo"], engines=engines,
        provider=_ScriptedAnswerProvider(brand_rank=3), store=store, day=date(2026, 7, 1),
    )
    report = build_prompt_tracker(
        "org1", "AcmeCRM", competitors=["RivalCo"], engines=engines,
        provider=_ScriptedAnswerProvider(brand_rank=1), store=store, day=date(2026, 7, 2),
    )

    assert report.total_prompts == 1
    record = report.entries[0].engines[0]
    assert record.previous_rank == 3
    assert record.current_rank == 1
    assert record.best_rank == 1
    assert record.delta == 2  # rank 3 -> rank 1
    assert [p.day for p in record.history] == [date(2026, 7, 1), date(2026, 7, 2)]


def test_prompt_tracker_same_day_replaces_point():
    store = GeoStore()
    add_prompt("org1", PromptCreate(text="best crm for startups"), store=store)
    engines = [AnswerEngine.CLAUDE]
    day = date(2026, 7, 3)

    build_prompt_tracker("org1", "AcmeCRM", engines=engines,
                         provider=_ScriptedAnswerProvider(brand_rank=1), store=store, day=day)
    report = build_prompt_tracker("org1", "AcmeCRM", engines=engines,
                                  provider=_ScriptedAnswerProvider(brand_rank=2), store=store, day=day)

    record = report.entries[0].engines[0]
    assert len(record.history) == 1  # same-day point replaced, not appended
    assert record.current_rank in (1, 2)
    assert record.previous_rank is None


# ---------------------------------------------------------------------------
# Citations & domain trust
# ---------------------------------------------------------------------------


def test_classify_domain_buckets():
    assert classify_domain("reddit.com") == DomainCategory.COMMUNITY
    assert classify_domain("en.wikipedia.org") == DomainCategory.ENCYCLOPEDIA
    assert classify_domain("g2.com") == DomainCategory.REVIEW_PLATFORM
    assert classify_domain("quora.com") == DomainCategory.QA_FORUM
    assert classify_domain("techcrunch.com") == DomainCategory.NEWS
    assert classify_domain("medium.com") == DomainCategory.BLOG
    assert classify_domain("crmblog.com") == DomainCategory.BLOG
    assert classify_domain("acmecrm.com", own_domain="acmecrm.com") == DomainCategory.OWN_DOMAIN
    assert classify_domain("randomsite.io") == DomainCategory.OTHER


def test_aggregate_domains_frequency_and_priority_order():
    citations = {
        AnswerEngine.CHATGPT: [
            Citation(url="https://reddit.com/r/a", domain="reddit.com"),
            Citation(url="https://reddit.com/r/b", domain="reddit.com"),
            Citation(url="https://wikipedia.org/wiki/x", domain="wikipedia.org"),
        ],
        AnswerEngine.GEMINI: [
            Citation(url="https://randomsite.io/post", domain="randomsite.io"),
        ],
    }
    stats = aggregate_domains(citations)
    by_domain = {s.domain: s for s in stats}
    assert by_domain["reddit.com"].citations == 2
    assert by_domain["reddit.com"].frequency == pytest.approx(0.5)
    assert sum(s.frequency for s in stats) == pytest.approx(1.0)
    assert by_domain["reddit.com"].engines == [AnswerEngine.CHATGPT]
    # reddit: 0.8 * 0.5 = 40 beats wikipedia: 0.95 * 0.25 = 23.75 beats other: 0.4 * 0.25 = 10.
    assert [s.domain for s in stats] == ["reddit.com", "wikipedia.org", "randomsite.io"]
    assert stats[0].priority_score == pytest.approx(40.0)


def test_scan_citations_and_org_wide_trust_report():
    store = GeoStore()
    report = scan_citations(
        "org1", "AcmeCRM", ["best crm software", "crm reviews"], store=store
    )
    assert report.total_citations > 0
    assert {ec.engine for ec in report.engines} == set(ALL_ENGINES)
    assert report.domains == sorted(
        report.domains, key=lambda s: (-s.priority_score, -s.citations, s.domain)
    )

    scan_citations("org1", "AcmeCRM", ["crm pricing"], store=store)
    trust = build_domain_trust_report("org1", store=store)
    assert trust.total_citations > report.total_citations
    assert sum(s.frequency for s in trust.domains) == pytest.approx(1.0)
    # Org scoping: a different org has no citation history.
    assert build_domain_trust_report("org2", store=store).total_citations == 0


def test_mock_provider_own_domain_shows_up_in_trust_report():
    store = GeoStore()
    prompts = research_prompts(PromptResearchRequest(topic="crm software", limit=20))
    scan_citations("org1", "AcmeCRM", [s.text for s in prompts.suggestions], store=store)
    trust = build_domain_trust_report("org1", own_domain="acmecrm.com", store=store)
    categories = {s.category for s in trust.domains}
    assert DomainCategory.OWN_DOMAIN in categories
    assert DomainCategory.COMMUNITY in categories


# ---------------------------------------------------------------------------
# Sentiment
# ---------------------------------------------------------------------------


def test_score_sentiment_lexicon_and_negation():
    label, score = score_sentiment("This tool is excellent, reliable and fast.")
    assert label == SentimentLabel.POSITIVE and score == 1.0
    label, score = score_sentiment("Buggy, slow, and disappointing experience.")
    assert label == SentimentLabel.NEGATIVE and score == -1.0
    label, score = score_sentiment("It is not reliable at all.")
    assert label == SentimentLabel.NEGATIVE and score < 0
    label, score = score_sentiment("The product ships on Tuesdays.")
    assert label == SentimentLabel.NEUTRAL and score == 0.0
    label, score = score_sentiment("")
    assert label == SentimentLabel.NEUTRAL and score == 0.0


def test_scan_sentiment_heatmap_shape_and_bounds():
    prompts = ["best crm software", "crm for small business", "is crm worth it"]
    report = scan_sentiment("AcmeCRM", prompts, engines=ALL_ENGINES)
    assert len(report.cells) == len(ALL_ENGINES) * len(prompts)
    assert {(c.engine, c.prompt) for c in report.cells} == {
        (e, p) for e in ALL_ENGINES for p in prompts
    }
    assert all(-1.0 <= c.score <= 1.0 for c in report.cells)
    assert len(report.per_engine) == len(ALL_ENGINES)
    assert -1.0 <= report.overall_score <= 1.0
    assert report == scan_sentiment("AcmeCRM", prompts, engines=ALL_ENGINES)  # deterministic


def test_scan_sentiment_mock_answers_include_polarity_variety():
    prompts = [s.text for s in research_prompts(PromptResearchRequest(topic="crm", limit=20)).suggestions]
    report = scan_sentiment("AcmeCRM", prompts)
    labels = {c.label for c in report.cells}
    assert SentimentLabel.POSITIVE in labels
    assert SentimentLabel.NEGATIVE in labels


# ---------------------------------------------------------------------------
# AI readiness audit
# ---------------------------------------------------------------------------

_BAD_ROBOTS = (
    "User-agent: GPTBot\nDisallow: /\n\n"
    "User-agent: ClaudeBot\nDisallow: /\n\n"
    "User-agent: *\nDisallow: /admin/\n"
)
_BAD_HTML = (
    "<html><head><title>Bad</title></head><body>"
    "<h1>One</h1><h1>Two</h1><p>" + ("word " * 200) + "</p></body></html>"
)
_BAD_SITE = SiteArtifacts(
    base_url="https://bad.test", llms_txt=None, robots_txt=_BAD_ROBOTS, html=_BAD_HTML
)


def test_ai_crawler_access_specific_groups_override_wildcard():
    access = {a.crawler: a.allowed for a in ai_crawler_access(_BAD_ROBOTS)}
    assert access["GPTBot"] is False
    assert access["ClaudeBot"] is False
    assert access["PerplexityBot"] is True
    assert access["Google-Extended"] is True
    assert access["CCBot"] is True


def test_ai_crawler_access_wildcard_blanket_block_and_missing_robots():
    blocked = ai_crawler_access("User-agent: *\nDisallow: /\n")
    assert all(not a.allowed for a in blocked)
    open_site = ai_crawler_access(None)
    assert all(a.allowed for a in open_site)


def test_audit_readiness_default_mock_site_scores_high():
    report = audit_readiness("https://acme.test")
    assert report.score >= 90
    assert report.grade == "A"
    assert report.fixes == []
    assert report.passed_count == report.total_count
    assert all(a.allowed for a in report.crawler_access)
    assert report == audit_readiness("https://acme.test")  # deterministic


def test_audit_readiness_flags_and_prioritizes_fixes():
    fetcher = MockArtifactFetcher({"https://bad.test": _BAD_SITE})
    report = audit_readiness("https://bad.test", fetcher=fetcher)

    failed = {c.code for c in report.checks if not c.passed}
    assert {
        "llms_txt_present", "llms_txt_valid", "ai_crawlers_allowed",
        "structured_data_present", "single_h1", "has_h2_sections",
        "question_headings", "answer_friendly_lists", "concise_paragraphs",
    } <= failed
    assert report.score < 50
    assert report.grade in ("E", "F")
    # Fixes prioritized: blocked AI crawlers (critical) come first.
    assert report.fixes[0].code == "geo_ai_crawlers_allowed"
    assert report.fixes[0].severity == Severity.CRITICAL
    weights = [f.severity.weight for f in report.fixes]
    assert weights == sorted(weights, reverse=True)
    assert all(f.recommendation for f in report.fixes)


# ---------------------------------------------------------------------------
# API routes (router mounted on a minimal app; no changes to main.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def geo_client(test_engine):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from app.api import routes_geo
    from app.db.session import get_session
    from app.middleware.errors import register_exception_handlers

    def _get_session():
        with Session(test_engine) as session:
            yield session

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(routes_geo.router, prefix=API)
    app.dependency_overrides[get_session] = _get_session
    return TestClient(app)


@pytest.fixture
def auth_headers(make_auth):
    return make_auth(email="geo@acme.test", org_name="Geo Co")["headers"]


def test_api_requires_auth(geo_client):
    assert geo_client.get(f"{API}/geo/prompts").status_code == 401
    assert geo_client.post(
        f"{API}/geo/visibility/scan", json={"brand": "Acme", "prompts": ["x"]}
    ).status_code == 401


def test_api_prompt_library_crud_and_org_scoping(geo_client, auth_headers, make_auth):
    created = geo_client.post(
        f"{API}/geo/prompts",
        json={"text": "best crm pricing", "intent_tags": ["pricing"]},
        headers=auth_headers,
    )
    assert created.status_code == 200
    body = created.json()
    assert body["funnel_stage"] == "bofu"
    assert body["intent_tags"] == ["pricing"]
    assert body["volume_estimate"] >= 50

    listed = geo_client.get(f"{API}/geo/prompts", headers=auth_headers).json()
    assert [p["text"] for p in listed] == ["best crm pricing"]

    # A different org must not see this prompt.
    other = make_auth(email="other@rival.test", org_name="Rival Co")["headers"]
    assert geo_client.get(f"{API}/geo/prompts", headers=other).json() == []

    # Empty prompt text is rejected.
    assert geo_client.post(
        f"{API}/geo/prompts", json={"text": "   "}, headers=auth_headers
    ).status_code == 400


def test_api_prompt_research(geo_client, auth_headers):
    resp = geo_client.post(
        f"{API}/geo/prompts/research",
        json={"topic": "crm software", "limit": 10},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 10
    assert len(body["suggestions"]) == 10
    assert all(s["funnel_stage"] in ("tofu", "mofu", "bofu") for s in body["suggestions"])


def test_api_visibility_scan_with_deltas_on_second_call(geo_client, auth_headers):
    payload = {
        "brand": "AcmeCRM",
        "competitors": ["RivalCo"],
        "prompts": ["best crm software", "crm reviews"],
    }
    first = geo_client.post(f"{API}/geo/visibility/scan", json=payload, headers=auth_headers)
    assert first.status_code == 200
    body = first.json()
    assert len(body["engines"]) == 6
    assert body["overall"]["prompts_scanned"] == 12
    assert body["overall"]["share_of_voice_delta"] is None
    assert "RivalCo" in body["competitor_share_of_voice"]

    second = geo_client.post(f"{API}/geo/visibility/scan", json=payload, headers=auth_headers).json()
    assert second["overall"]["share_of_voice_delta"] == 0.0  # identical deterministic scan


def test_api_visibility_scan_uses_prompt_library_fallback(geo_client, auth_headers):
    # Empty library + no prompts -> 400.
    resp = geo_client.post(
        f"{API}/geo/visibility/scan", json={"brand": "AcmeCRM"}, headers=auth_headers
    )
    assert resp.status_code == 400

    geo_client.post(f"{API}/geo/prompts", json={"text": "best crm software"}, headers=auth_headers)
    resp = geo_client.post(
        f"{API}/geo/visibility/scan",
        json={"brand": "AcmeCRM", "engines": ["chatgpt", "claude"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [e["engine"] for e in body["engines"]] == ["chatgpt", "claude"]
    assert body["overall"]["prompts_scanned"] == 2


def test_api_prompt_tracker(geo_client, auth_headers):
    geo_client.post(f"{API}/geo/prompts", json={"text": "best crm software"}, headers=auth_headers)
    geo_client.post(f"{API}/geo/prompts", json={"text": "crm pricing"}, headers=auth_headers)

    resp = geo_client.get(
        f"{API}/geo/prompts/tracker",
        params={"brand": "AcmeCRM", "competitors": ["RivalCo"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_prompts"] == 2
    assert len(body["engines"]) == 6
    entry = body["entries"][0]
    assert len(entry["engines"]) == 6
    assert all(len(e["history"]) == 1 for e in entry["engines"])

    # Second poll on the same day keeps a single history point per engine.
    again = geo_client.get(
        f"{API}/geo/prompts/tracker", params={"brand": "AcmeCRM"}, headers=auth_headers
    ).json()
    assert all(len(e["history"]) == 1 for e in again["entries"][0]["engines"])


def test_api_citations_scan_and_domains(geo_client, auth_headers):
    resp = geo_client.post(
        f"{API}/geo/citations/scan",
        json={"brand": "AcmeCRM", "prompts": ["best crm software"], "own_domain": "acmecrm.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_citations"] > 0
    assert len(body["engines"]) == 6
    assert all(d["priority_score"] >= 0 for d in body["domains"])

    domains = geo_client.get(
        f"{API}/geo/citations/domains", params={"own_domain": "acmecrm.com"}, headers=auth_headers
    ).json()
    assert domains["total_citations"] == body["total_citations"]
    assert domains["domains"]


def test_api_sentiment_scan(geo_client, auth_headers):
    resp = geo_client.post(
        f"{API}/geo/sentiment/scan",
        json={"brand": "AcmeCRM", "prompts": ["best crm software", "crm reviews"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["cells"]) == 12  # 6 engines x 2 prompts
    assert body["overall_label"] in ("positive", "neutral", "negative")
    assert all(-1.0 <= c["score"] <= 1.0 for c in body["cells"])


def test_api_readiness_audit(geo_client, auth_headers):
    resp = geo_client.post(
        f"{API}/geo/readiness/audit", json={"url": "https://acme.test"}, headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["url"] == "https://acme.test"
    assert body["score"] >= 90
    assert body["grade"] == "A"
    assert len(body["crawler_access"]) == 5
    assert body["checks"]

    blank = geo_client.post(f"{API}/geo/readiness/audit", json={"url": "  "}, headers=auth_headers)
    assert blank.status_code == 400


def test_api_readiness_audit_with_fetcher_override(geo_client, auth_headers):
    from app.api.routes_geo import get_artifact_fetcher_dep

    geo_client.app.dependency_overrides[get_artifact_fetcher_dep] = lambda: MockArtifactFetcher(
        {"https://bad.test": _BAD_SITE}
    )
    body = geo_client.post(
        f"{API}/geo/readiness/audit", json={"url": "https://bad.test"}, headers=auth_headers
    ).json()
    assert body["score"] < 50
    assert body["fixes"][0]["severity"] == "critical"
    blocked = {a["crawler"]: a["allowed"] for a in body["crawler_access"]}
    assert blocked["GPTBot"] is False
    assert blocked["PerplexityBot"] is True
