"""Tests for the v2 AI Answer-Engine Visibility Tracker
(app/core/aitracker + /ai-tracker API routes). Fully offline."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.aitracker.configs import (
    create_config,
    delete_config,
    get_config,
    update_config,
)
from app.core.aitracker.engine import rollup_metrics, run_tracker
from app.core.aitracker.policy import (
    allowed_cadences,
    allowed_engines,
    enforce_config_quota,
    enforce_prompt_quota,
    validate_cadence,
    validate_engines,
)
from app.core.aitracker.scheduler import due_runs, is_due
from app.core.aitracker.store import TrackerStore, reset_tracker_store
from app.core.geo.providers import MockAnswerEngineProvider
from app.middleware.errors import (
    BadRequestError,
    FeatureNotAvailableError,
    NotFoundError,
    QuotaExceededError,
)
from app.models.aitracker import (
    RefreshCadence,
    TrackerConfig,
    TrackerConfigCreate,
    TrackerConfigUpdate,
    TrackerEngine,
)
from app.models.geo import Citation, EngineAnswer, SentimentLabel
from app.version import API_VERSION

API = f"/api/{API_VERSION}"
UTC = timezone.utc
T0 = datetime(2026, 7, 1, tzinfo=UTC)
ALL_TRACKER_ENGINES = list(TrackerEngine)


@pytest.fixture(autouse=True)
def _fresh_tracker_store():
    """The module-level TrackerStore is a process singleton — reset every test."""
    reset_tracker_store()
    yield
    reset_tracker_store()


class _ScriptedProvider:
    """Deterministic test double with fully controlled mentions/ranks/citations.

    Normal prompts: the brand is mentioned once in text (positive wording),
    each competitor twice, the brand ranks at ``brand_rank`` (1-based), and
    every answer cites reddit plus (when ``cite_own``) the brand's own domain.
    Prompts containing any ``miss_markers`` substring omit the brand entirely
    (competitors only) — the raw material for mention-gap tests. Prompts
    containing "solo" only surface the first competitor.
    """

    def __init__(self, brand_rank: int = 2, cite_own: bool = True, miss_markers: tuple = ()):
        self.brand_rank = brand_rank
        self.cite_own = cite_own
        self.miss_markers = miss_markers

    def ask(self, engine, prompt, brand, competitors=None):
        competitors = list(competitors or [])
        if "solo" in prompt:
            competitors = competitors[:1]
        if any(marker in prompt for marker in self.miss_markers):
            text = " ".join(f"{c} is fine." for c in competitors) or "Nothing to see."
            ranked = [*competitors, "FillerOne"]
            citations = [Citation(url="https://reddit.com/r/x", domain="reddit.com")]
            return EngineAnswer(
                engine=engine, prompt=prompt, text=text, ranked_list=ranked, citations=citations
            )
        text = f"{brand} is excellent. " + " ".join(
            f"{c} is fine. {c} shows up again." for c in competitors
        )
        ranked = [*competitors, "FillerOne", "FillerTwo"]
        ranked.insert(min(self.brand_rank - 1, len(ranked)), brand)
        citations = [Citation(url="https://reddit.com/r/x", domain="reddit.com")]
        if self.cite_own:
            own = "".join(brand.lower().split()) + ".com"
            citations.append(Citation(url=f"https://{own}/product", domain=own))
        return EngineAnswer(
            engine=engine, prompt=prompt, text=text, ranked_list=ranked, citations=citations
        )


def _make_config(**overrides) -> TrackerConfig:
    base = dict(
        id="trk-test",
        name="Main prompt set",
        brand="AcmeCRM",
        prompts=["best crm", "top crm tools"],
        competitors=["RivalCo"],
        engines=[TrackerEngine.CHATGPT, TrackerEngine.GEMINI],
        own_domain="acmecrm.com",
        refresh_cadence=RefreshCadence.WEEKLY,
        created_at=T0,
    )
    base.update(overrides)
    return TrackerConfig(**base)


# ---------------------------------------------------------------------------
# Run engine: determinism + exact metric math
# ---------------------------------------------------------------------------


def test_run_tracker_deterministic_with_mock_provider():
    provider = MockAnswerEngineProvider()
    r1 = run_tracker(
        "org1", _make_config(engines=ALL_TRACKER_ENGINES), now=T0,
        provider=provider, store=TrackerStore(),
    )
    r2 = run_tracker(
        "org1", _make_config(engines=ALL_TRACKER_ENGINES), now=T0,
        provider=provider, store=TrackerStore(),
    )
    assert r1 == r2
    assert len(r1.answers) == len(ALL_TRACKER_ENGINES) * 2
    assert 0.0 <= r1.rollup.overall.visibility_score <= 100.0
    assert 0.0 <= r1.rollup.overall.share_of_voice <= 1.0


def test_google_ai_mode_answers_differ_from_ai_overviews():
    report = run_tracker(
        "org1",
        _make_config(
            engines=[TrackerEngine.GOOGLE_AI_OVERVIEWS, TrackerEngine.GOOGLE_AI_MODE],
            prompts=["best crm software"],
            competitors=["RivalCo", "OtherCo"],
        ),
        now=T0,
        provider=MockAnswerEngineProvider(),
        store=TrackerStore(),
    )
    by_engine = {a.engine: a for a in report.answers}
    aio = by_engine[TrackerEngine.GOOGLE_AI_MODE]
    aiov = by_engine[TrackerEngine.GOOGLE_AI_OVERVIEWS]
    assert aio.text != aiov.text  # deterministic but distinct
    assert aio.prompt == aiov.prompt == "best crm software"  # original prompt preserved


def test_run_tracker_exact_visibility_math():
    """Scripted: brand rank 2, mentioned once per answer, competitor twice,
    2 citations per answer (1 own). Hand-computed expectations:
    mention_rate=1.0, position_score=0.5, citation_share=0.5
    -> VS = 100*(0.5*1 + 0.3*0.5 + 0.2*0.5) = 75.0; SOV = 4/(4+8) = 1/3."""
    report = run_tracker(
        "org1", _make_config(), now=T0,
        provider=_ScriptedProvider(brand_rank=2, cite_own=True), store=TrackerStore(),
    )
    overall = report.rollup.overall
    assert overall.prompts_total == 4  # 2 engines x 2 prompts
    assert overall.prompts_mentioned == 4
    assert overall.mention_rate == 1.0
    assert overall.avg_position == 2.0
    assert overall.position_score == 0.5
    assert overall.citation_share == 0.5
    assert overall.visibility_score == 75.0
    assert overall.share_of_voice == pytest.approx(1 / 3, abs=1e-4)
    assert overall.competitor_share_of_voice["RivalCo"] == pytest.approx(2 / 3, abs=1e-4)
    assert overall.avg_sentiment == 1.0  # "excellent" in every answer
    assert overall.sentiment_label == SentimentLabel.POSITIVE
    # Per-engine rollups see the same scripted answers.
    assert {er.engine for er in report.rollup.engines} == {
        TrackerEngine.CHATGPT, TrackerEngine.GEMINI,
    }
    for er in report.rollup.engines:
        assert er.visibility_score == 75.0
        assert er.avg_position == 2.0
    # First run -> no deltas.
    assert overall.visibility_score_delta is None
    assert overall.share_of_voice_delta is None


def test_run_tracker_citation_share_zero_without_own_citations():
    report = run_tracker(
        "org1", _make_config(), now=T0,
        provider=_ScriptedProvider(brand_rank=1, cite_own=False), store=TrackerStore(),
    )
    overall = report.rollup.overall
    assert overall.citation_share == 0.0
    assert overall.position_score == 1.0
    assert overall.visibility_score == 80.0  # 100*(0.5 + 0.3 + 0)


def test_run_tracker_trend_deltas_run_over_run():
    store = TrackerStore()
    config = _make_config()
    run_tracker("org1", config, now=T0, provider=_ScriptedProvider(brand_rank=2), store=store)
    second = run_tracker(
        "org1", config, now=datetime(2026, 7, 8, tzinfo=UTC),
        provider=_ScriptedProvider(brand_rank=1), store=store,
    )
    overall = second.rollup.overall
    assert overall.visibility_score == 90.0  # 100*(0.5 + 0.3*1.0 + 0.2*0.5)
    assert overall.visibility_score_delta == 15.0  # 90 - 75
    assert overall.avg_position_delta == 1.0  # rank 2 -> rank 1 (improvement)
    assert overall.mention_rate_delta == 0.0
    assert overall.share_of_voice_delta == 0.0
    for er in second.rollup.engines:
        assert er.visibility_score_delta == 15.0
    # History is org-scoped.
    assert len(store.runs("org1", config.id)) == 2
    assert store.runs("org2", config.id) == []
    assert config.last_run_at == datetime(2026, 7, 8, tzinfo=UTC)


def test_rollup_metrics_empty_answers_are_all_zero():
    metrics = rollup_metrics([], ["RivalCo"], "acmecrm.com")
    assert metrics.prompts_total == 0
    assert metrics.visibility_score == 0.0
    assert metrics.avg_position is None


# ---------------------------------------------------------------------------
# Mention-Gap report
# ---------------------------------------------------------------------------


def test_mention_gap_entries_ranked_by_opportunity():
    config = _make_config(
        prompts=["best crm", "crm gaps alpha", "solo gap beta"],
        competitors=["RivalCo", "OtherCo"],
    )
    report = run_tracker(
        "org1", config, now=T0,
        provider=_ScriptedProvider(miss_markers=("gap",)), store=TrackerStore(),
    )
    gap = report.mention_gap
    assert gap.total_prompts == 3
    assert [e.prompt for e in gap.entries] == ["crm gaps alpha", "solo gap beta"]

    alpha = gap.entries[0]
    assert alpha.gap_engines == [TrackerEngine.CHATGPT, TrackerEngine.GEMINI]
    assert alpha.competitors_mentioned == ["OtherCo", "RivalCo"]
    assert alpha.opportunity_score == 4.0  # 2 engines x 2 competitors

    beta = gap.entries[1]
    assert beta.competitors_mentioned == ["RivalCo"]  # "solo" -> first competitor only
    assert beta.opportunity_score == 2.0  # 2 engines x 1 competitor

    # The fully-mentioned prompt does not appear, and mention_rate reflects gaps.
    assert report.rollup.overall.mention_rate == pytest.approx(2 / 6, abs=1e-4)


# ---------------------------------------------------------------------------
# Scheduler: cadence / due logic
# ---------------------------------------------------------------------------


def test_is_due_when_never_run():
    assert is_due(_make_config(last_run_at=None), T0) is True


def test_is_due_daily_and_weekly_boundaries():
    daily = _make_config(refresh_cadence=RefreshCadence.DAILY, last_run_at=T0)
    assert is_due(daily, datetime(2026, 7, 1, 23, 59, tzinfo=UTC)) is False
    assert is_due(daily, datetime(2026, 7, 2, 0, 0, tzinfo=UTC)) is True

    weekly = _make_config(refresh_cadence=RefreshCadence.WEEKLY, last_run_at=T0)
    assert is_due(weekly, datetime(2026, 7, 7, tzinfo=UTC)) is False
    assert is_due(weekly, datetime(2026, 7, 8, tzinfo=UTC)) is True
    # Naive datetimes are treated as UTC instead of raising.
    assert is_due(weekly, datetime(2026, 7, 8)) is True


def test_due_runs_scans_all_orgs_and_filters_by_org():
    store = TrackerStore()
    store.save_config("org1", _make_config(id="trk-a", name="A", last_run_at=None))
    store.save_config(
        "org1",
        _make_config(id="trk-b", name="B", refresh_cadence=RefreshCadence.DAILY, last_run_at=T0),
    )
    store.save_config("org2", _make_config(id="trk-c", name="C", last_run_at=None))

    now = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)  # trk-b ran 12h ago -> not due
    due = due_runs(now, store=store)
    assert {(org, c.id) for org, c in due} == {("org1", "trk-a"), ("org2", "trk-c")}
    assert [c.id for _org, c in due_runs(now, org_id="org1", store=store)] == ["trk-a"]

    later = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
    assert {c.id for _o, c in due_runs(later, org_id="org1", store=store)} == {"trk-a", "trk-b"}


# ---------------------------------------------------------------------------
# Plan policy (entitlements)
# ---------------------------------------------------------------------------


def test_allowed_engines_by_plan():
    assert allowed_engines("free") == []
    assert allowed_engines("starter") == []
    assert allowed_engines("pro") == [TrackerEngine.CHATGPT]  # entry tier
    assert allowed_engines("agency") == ALL_TRACKER_ENGINES
    assert allowed_engines("enterprise") == ALL_TRACKER_ENGINES


def test_allowed_cadences_by_plan():
    assert allowed_cadences("free") == []
    assert allowed_cadences("pro") == [RefreshCadence.WEEKLY]
    assert allowed_cadences("agency") == [RefreshCadence.DAILY, RefreshCadence.WEEKLY]


def test_validate_engines_entry_tier_restriction_and_default():
    assert validate_engines("pro", []) == [TrackerEngine.CHATGPT]
    assert validate_engines("agency", []) == ALL_TRACKER_ENGINES
    assert validate_engines(
        "agency", [TrackerEngine.GEMINI, TrackerEngine.GEMINI]
    ) == [TrackerEngine.GEMINI]  # deduped
    with pytest.raises(FeatureNotAvailableError):
        validate_engines("pro", [TrackerEngine.GEMINI])
    with pytest.raises(FeatureNotAvailableError):
        validate_engines("pro", [TrackerEngine.CHATGPT, TrackerEngine.GOOGLE_AI_MODE])


def test_validate_cadence_gating():
    assert validate_cadence("pro", RefreshCadence.WEEKLY) == RefreshCadence.WEEKLY
    assert validate_cadence("agency", RefreshCadence.DAILY) == RefreshCadence.DAILY
    with pytest.raises(FeatureNotAvailableError):
        validate_cadence("pro", RefreshCadence.DAILY)
    with pytest.raises(FeatureNotAvailableError):
        validate_cadence("free", RefreshCadence.WEEKLY)


def test_quota_helpers():
    enforce_config_quota("pro", 4)  # under the pro limit of 5
    with pytest.raises(QuotaExceededError):
        enforce_config_quota("pro", 5)
    enforce_prompt_quota("pro", 25)
    with pytest.raises(QuotaExceededError):
        enforce_prompt_quota("pro", 26)
    enforce_config_quota("enterprise", 10_000)  # unlimited (-1)
    enforce_prompt_quota("enterprise", 10_000)


# ---------------------------------------------------------------------------
# Config CRUD (core)
# ---------------------------------------------------------------------------


def test_create_config_defaults_cleaning_and_derived_domain():
    store = TrackerStore()
    config = create_config(
        "org1",
        "pro",
        TrackerConfigCreate(
            name="  German market  ",
            brand=" AcmeCRM ",
            prompts=["  best crm ", "best crm", "BEST CRM", "top crm tools", "  "],
            competitors=["RivalCo", "rivalco ".strip(), "RivalCo"],
            market="de",
            language="de",
        ),
        store=store,
    )
    assert config.name == "German market"
    assert config.brand == "AcmeCRM"
    assert config.prompts == ["best crm", "top crm tools"]  # stripped + deduped
    assert config.competitors == ["RivalCo"]
    assert config.engines == [TrackerEngine.CHATGPT]  # pro entry-tier default
    assert config.refresh_cadence == RefreshCadence.WEEKLY
    assert config.own_domain == "acmecrm.com"  # derived from the brand
    assert config.market == "de" and config.language == "de"
    assert config.last_run_at is None

    with pytest.raises(BadRequestError):  # duplicate name
        create_config(
            "org1", "pro",
            TrackerConfigCreate(name="german market", brand="AcmeCRM", prompts=["x"]),
            store=store,
        )
    with pytest.raises(BadRequestError):  # empty prompts
        create_config(
            "org1", "pro",
            TrackerConfigCreate(name="Other", brand="AcmeCRM", prompts=["  "]),
            store=store,
        )
    with pytest.raises(BadRequestError):  # empty brand
        create_config(
            "org1", "pro", TrackerConfigCreate(name="Other", brand=" ", prompts=["x"]),
            store=store,
        )


def test_update_and_delete_config():
    store = TrackerStore()
    config = create_config(
        "org1", "agency",
        TrackerConfigCreate(
            name="Main", brand="AcmeCRM", prompts=["best crm"],
            engines=[TrackerEngine.CHATGPT], refresh_cadence=RefreshCadence.DAILY,
        ),
        store=store,
    )
    updated = update_config(
        "org1", "agency", config.id,
        TrackerConfigUpdate(name="Renamed", prompts=["top crm"], engines=[]),
        store=store,
    )
    assert updated.id == config.id
    assert updated.name == "Renamed"
    assert updated.prompts == ["top crm"]
    assert updated.engines == ALL_TRACKER_ENGINES  # [] resets to the plan default
    assert updated.refresh_cadence == RefreshCadence.DAILY  # untouched

    create_config(
        "org1", "agency", TrackerConfigCreate(name="Second", brand="B", prompts=["x"]),
        store=store,
    )
    with pytest.raises(BadRequestError):  # rename onto an existing name
        update_config("org1", "agency", config.id, TrackerConfigUpdate(name="second"), store=store)

    delete_config("org1", config.id, store=store)
    with pytest.raises(NotFoundError):
        get_config("org1", config.id, store=store)
    with pytest.raises(NotFoundError):
        delete_config("org1", config.id, store=store)


# ---------------------------------------------------------------------------
# API routes (router mounted on a minimal app; no changes to main.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def tracker_client(test_engine):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from app.api import routes_aitracker
    from app.db.session import get_session
    from app.middleware.errors import register_exception_handlers

    def _get_session():
        with Session(test_engine) as session:
            yield session

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(routes_aitracker.router, prefix=API)
    app.dependency_overrides[get_session] = _get_session
    return TestClient(app)


@pytest.fixture
def pro_auth(make_auth):
    return make_auth(email="pro@acme.test", org_name="Pro Co", plan_code="pro")


@pytest.fixture
def agency_auth(make_auth):
    return make_auth(email="agency@acme.test", org_name="Agency Co", plan_code="agency")


def _member_headers(test_engine, org_id: str, role: str) -> dict:
    from sqlmodel import Session

    from app.db.models_tenancy import Membership
    from app.security.tokens import create_access_token
    from app.tenancy.provisioning import create_local_user

    with Session(test_engine) as s:
        user = create_local_user(s, f"{role}@member.test", "pw123456", role.title())
        s.add(Membership(org_id=org_id, user_id=user.id, role=role, status="active"))
        s.commit()
        token = create_access_token(user.id, email=user.email, org_id=org_id, role=role)
    return {"Authorization": f"Bearer {token}"}


def test_api_requires_auth(tracker_client):
    assert tracker_client.get(f"{API}/ai-tracker/configs").status_code == 401
    assert tracker_client.post(
        f"{API}/ai-tracker/configs", json={"name": "x", "brand": "B", "prompts": ["p"]}
    ).status_code == 401


def test_api_feature_gated_for_free_and_starter(tracker_client, make_auth):
    payload = {"name": "Main", "brand": "AcmeCRM", "prompts": ["best crm"]}
    for plan in ("free", "starter"):
        headers = make_auth(
            email=f"{plan}@x.test", org_name=f"{plan.title()} Co", plan_code=plan
        )["headers"]
        get = tracker_client.get(f"{API}/ai-tracker/configs", headers=headers)
        assert get.status_code == 402
        assert get.json()["error"] == "feature_not_available"
        assert tracker_client.post(
            f"{API}/ai-tracker/configs", json=payload, headers=headers
        ).status_code == 402
        assert tracker_client.get(f"{API}/ai-tracker/due", headers=headers).status_code == 402


def test_api_entry_tier_engine_and_cadence_restrictions(tracker_client, pro_auth):
    headers = pro_auth["headers"]
    # Engines beyond ChatGPT -> 402 for the entry tier.
    denied = tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Main", "brand": "AcmeCRM", "prompts": ["best crm"],
              "engines": ["gemini"]},
        headers=headers,
    )
    assert denied.status_code == 402
    # Daily refresh -> 402 for the entry tier.
    assert tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Main", "brand": "AcmeCRM", "prompts": ["best crm"],
              "refresh_cadence": "daily"},
        headers=headers,
    ).status_code == 402
    # Defaults resolve to ChatGPT-only + weekly.
    created = tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Main", "brand": "AcmeCRM", "prompts": ["best crm"]},
        headers=headers,
    )
    assert created.status_code == 200
    body = created.json()
    assert body["engines"] == ["chatgpt"]
    assert body["refresh_cadence"] == "weekly"
    # And the restriction also applies via PUT.
    assert tracker_client.put(
        f"{API}/ai-tracker/configs/{body['id']}",
        json={"engines": ["chatgpt", "perplexity"]},
        headers=headers,
    ).status_code == 402


def test_api_agency_gets_all_engines_and_daily(tracker_client, agency_auth):
    created = tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Main", "brand": "AcmeCRM", "prompts": ["best crm"],
              "refresh_cadence": "daily"},
        headers=agency_auth["headers"],
    )
    assert created.status_code == 200
    body = created.json()
    assert body["engines"] == [e.value for e in ALL_TRACKER_ENGINES]
    assert "google_ai_mode" in body["engines"]
    assert body["refresh_cadence"] == "daily"


def test_api_config_crud_roundtrip(tracker_client, pro_auth):
    headers = pro_auth["headers"]
    created = tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Main", "brand": "AcmeCRM", "prompts": ["best crm", "crm pricing"],
              "competitors": ["RivalCo"], "market": "us", "language": "en"},
        headers=headers,
    ).json()
    config_id = created["id"]

    listed = tracker_client.get(f"{API}/ai-tracker/configs", headers=headers).json()
    assert [c["id"] for c in listed] == [config_id]

    fetched = tracker_client.get(
        f"{API}/ai-tracker/configs/{config_id}", headers=headers
    ).json()
    assert fetched == created

    updated = tracker_client.put(
        f"{API}/ai-tracker/configs/{config_id}",
        json={"name": "Renamed", "prompts": ["top crm tools"]},
        headers=headers,
    ).json()
    assert updated["name"] == "Renamed"
    assert updated["prompts"] == ["top crm tools"]
    assert updated["brand"] == "AcmeCRM"  # untouched fields kept

    deleted = tracker_client.delete(
        f"{API}/ai-tracker/configs/{config_id}", headers=headers
    )
    assert deleted.status_code == 200 and deleted.json()["deleted"] is True
    assert tracker_client.get(
        f"{API}/ai-tracker/configs/{config_id}", headers=headers
    ).status_code == 404
    assert tracker_client.get(f"{API}/ai-tracker/configs", headers=headers).json() == []


def test_api_run_history_visibility_and_mention_gap(tracker_client, agency_auth):
    headers = agency_auth["headers"]
    config = tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Main", "brand": "AcmeCRM", "prompts": ["best crm", "crm reviews"],
              "competitors": ["RivalCo"]},
        headers=headers,
    ).json()
    cid = config["id"]

    # No runs yet -> 404 on rollup endpoints, empty history.
    assert tracker_client.get(
        f"{API}/ai-tracker/configs/{cid}/visibility", headers=headers
    ).status_code == 404
    assert tracker_client.get(
        f"{API}/ai-tracker/configs/{cid}/mention-gap", headers=headers
    ).status_code == 404
    assert tracker_client.get(
        f"{API}/ai-tracker/configs/{cid}/history", headers=headers
    ).json() == []

    first = tracker_client.post(
        f"{API}/ai-tracker/configs/{cid}/run",
        params={"now": "2026-07-01T00:00:00Z"},
        headers=headers,
    )
    assert first.status_code == 200
    body = first.json()
    assert len(body["answers"]) == 5 * 2  # all five engines x 2 prompts
    assert body["rollup"]["overall"]["visibility_score_delta"] is None
    assert 0.0 <= body["rollup"]["overall"]["visibility_score"] <= 100.0
    assert len(body["rollup"]["engines"]) == 5
    assert body["mention_gap"]["total_prompts"] == 2

    second = tracker_client.post(
        f"{API}/ai-tracker/configs/{cid}/run",
        params={"now": "2026-07-08T00:00:00Z"},
        headers=headers,
    ).json()
    # Identical deterministic scan -> zero (not None) deltas.
    assert second["rollup"]["overall"]["visibility_score_delta"] == 0.0
    assert second["rollup"]["overall"]["share_of_voice_delta"] == 0.0

    history = tracker_client.get(
        f"{API}/ai-tracker/configs/{cid}/history", headers=headers
    ).json()
    assert len(history) == 2
    assert history[0]["overall"]["visibility_score_delta"] is None
    assert history[1] == second["rollup"]

    latest = tracker_client.get(
        f"{API}/ai-tracker/configs/{cid}/visibility", headers=headers
    ).json()
    assert latest == second["rollup"]

    gap = tracker_client.get(
        f"{API}/ai-tracker/configs/{cid}/mention-gap", headers=headers
    ).json()
    assert gap["config_id"] == cid
    assert gap["total_prompts"] == 2
    for entry in gap["entries"]:
        assert entry["opportunity_score"] > 0
        assert entry["competitors_mentioned"]


def test_api_org_isolation(tracker_client, pro_auth, make_auth):
    headers = pro_auth["headers"]
    config = tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Main", "brand": "AcmeCRM", "prompts": ["best crm"]},
        headers=headers,
    ).json()

    other = make_auth(email="other@rival.test", org_name="Rival Co", plan_code="pro")["headers"]
    assert tracker_client.get(f"{API}/ai-tracker/configs", headers=other).json() == []
    assert tracker_client.get(
        f"{API}/ai-tracker/configs/{config['id']}", headers=other
    ).status_code == 404
    assert tracker_client.post(
        f"{API}/ai-tracker/configs/{config['id']}/run", headers=other
    ).status_code == 404
    assert tracker_client.delete(
        f"{API}/ai-tracker/configs/{config['id']}", headers=other
    ).status_code == 404
    # The owner still sees it.
    assert tracker_client.get(
        f"{API}/ai-tracker/configs/{config['id']}", headers=headers
    ).status_code == 200


def test_api_rbac_client_role_and_ops_endpoint(tracker_client, pro_auth, test_engine):
    owner = pro_auth["headers"]
    tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Main", "brand": "AcmeCRM", "prompts": ["best crm"]},
        headers=owner,
    )
    client_headers = _member_headers(test_engine, pro_auth["org_id"], "client")
    # Read allowed, writes forbidden, ops endpoint admin/owner-only.
    assert tracker_client.get(f"{API}/ai-tracker/configs", headers=client_headers).status_code == 200
    assert tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "X", "brand": "B", "prompts": ["p"]},
        headers=client_headers,
    ).status_code == 403
    assert tracker_client.get(f"{API}/ai-tracker/due", headers=client_headers).status_code == 403
    # Owner can list due configs; the never-run config is due.
    due = tracker_client.get(f"{API}/ai-tracker/due", headers=owner)
    assert due.status_code == 200
    assert [d["last_run_at"] for d in due.json()] == [None]


def test_api_due_endpoint_respects_cadence(tracker_client, pro_auth):
    headers = pro_auth["headers"]
    config = tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Main", "brand": "AcmeCRM", "prompts": ["best crm"]},
        headers=headers,
    ).json()
    tracker_client.post(
        f"{API}/ai-tracker/configs/{config['id']}/run",
        params={"now": "2026-07-01T00:00:00Z"},
        headers=headers,
    )
    # 1 day after a weekly run -> nothing due; 7+ days after -> due again.
    assert tracker_client.get(
        f"{API}/ai-tracker/due", params={"now": "2026-07-02T00:00:00Z"}, headers=headers
    ).json() == []
    due = tracker_client.get(
        f"{API}/ai-tracker/due", params={"now": "2026-07-08T00:00:00Z"}, headers=headers
    ).json()
    assert [d["config_id"] for d in due] == [config["id"]]
    assert due[0]["refresh_cadence"] == "weekly"


def test_api_quota_limits(tracker_client, pro_auth):
    headers = pro_auth["headers"]
    # Prompt quota: pro allows 25 prompts per config.
    too_many = tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Big", "brand": "AcmeCRM",
              "prompts": [f"prompt {i}" for i in range(26)]},
        headers=headers,
    )
    assert too_many.status_code == 402
    assert too_many.json()["error"] == "quota_exceeded"
    # Config quota: pro allows 5 configs.
    for i in range(5):
        assert tracker_client.post(
            f"{API}/ai-tracker/configs",
            json={"name": f"Set {i}", "brand": "AcmeCRM", "prompts": ["best crm"]},
            headers=headers,
        ).status_code == 200
    sixth = tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Set 5", "brand": "AcmeCRM", "prompts": ["best crm"]},
        headers=headers,
    )
    assert sixth.status_code == 402
    assert sixth.json()["error"] == "quota_exceeded"


def test_api_bad_requests(tracker_client, pro_auth):
    headers = pro_auth["headers"]
    assert tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Main", "brand": "AcmeCRM", "prompts": ["   "]},
        headers=headers,
    ).status_code == 400
    tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "Main", "brand": "AcmeCRM", "prompts": ["best crm"]},
        headers=headers,
    )
    dup = tracker_client.post(
        f"{API}/ai-tracker/configs",
        json={"name": "  main ", "brand": "AcmeCRM", "prompts": ["best crm"]},
        headers=headers,
    )
    assert dup.status_code == 400
