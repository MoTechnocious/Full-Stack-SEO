"""Tests for the Personal Entity Optimization engine (Knowledge Graph explorer/
sensor, bio builder, corroboration auditing, entity schema) and its API routes.
Deterministic: no network, no randomness. The router is mounted on a small
purpose-built FastAPI app with the tenant dependency overridden.
"""
from __future__ import annotations

import re

import pytest

from app.core.peo.bio_builder import build_bio
from app.core.peo.corroboration import audit_corroboration
from app.core.peo.entity_schema import generate_entity_schema
from app.core.peo.providers import MockKnowledgeGraphProvider, MockProfileFetcher
from app.core.peo.repository import PeoRepository, reset_peo_repository
from app.core.peo.sensor import analyze_series, classify_trend
from app.models.peo import (
    BioLength,
    BioRequest,
    EntitySchemaRequest,
    EntityType,
    FactStatus,
    SensorObservation,
    SourceProfile,
    SourceType,
    TrackedEntity,
    TrendClass,
)

API = "/api/v1"


# ---------------------------------------------------------------------------
# Test app (mirrors conftest.app_client, but mounts only the PEO router)
# ---------------------------------------------------------------------------


def _make_client(authenticated: bool = True):
    """A minimal app hosting the PEO router with the same dependency-override
    pattern as the full application; returns ``(client, org_holder)`` where
    mutating ``org_holder["org_id"]`` switches the acting organization."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import routes_peo
    from app.db.session import get_session
    from app.middleware.errors import register_exception_handlers
    from app.tenancy.context import TenantContext
    from app.tenancy.deps import get_tenant_context
    from app.tenancy.rbac import Role

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(routes_peo.router, prefix=API)

    holder = {"org_id": "org-a"}
    if authenticated:
        def _ctx() -> TenantContext:
            return TenantContext(
                user_id="u-test", org_id=holder["org_id"], org_name="Test Org", role=Role.OWNER
            )

        app.dependency_overrides[get_tenant_context] = _ctx
    else:
        app.dependency_overrides[get_session] = lambda: None  # no DB needed pre-auth
    return TestClient(app), holder


@pytest.fixture
def peo_api():
    reset_peo_repository()
    client, holder = _make_client()
    yield client, holder
    reset_peo_repository()


# ---------------------------------------------------------------------------
# providers.py — Knowledge Graph explorer
# ---------------------------------------------------------------------------


def test_mock_kg_search_is_deterministic_and_well_shaped():
    provider = MockKnowledgeGraphProvider()
    first = provider.search_entities("ada lovelace", limit=8)
    second = provider.search_entities("ada lovelace", limit=8)

    assert first == second  # stable across calls
    assert 0 < len(first) <= 8
    mids = [e.kg_mid for e in first]
    assert len(mids) == len(set(mids))  # unique KGMIDs
    for entity in first:
        assert entity.kg_mid.startswith("/g/")
        assert entity.name
        assert entity.types
        assert entity.description
        assert entity.result_score > 0
    # Scores are non-increasing (strongest match first).
    scores = [e.result_score for e in first]
    assert scores == sorted(scores, reverse=True)


def test_mock_kg_search_respects_limit_and_type_filter():
    provider = MockKnowledgeGraphProvider()
    assert len(provider.search_entities("acme corp", limit=3)) == 3
    assert provider.search_entities("   ") == []

    unfiltered = provider.search_entities("acme corp", limit=10)
    filtered = provider.search_entities("acme corp", limit=10, types=["Organization"])
    assert all("Organization" in e.types for e in filtered)
    assert {e.kg_mid for e in filtered} <= {e.kg_mid for e in unfiltered}


def test_mock_kg_confidence_series_deterministic_and_chronological():
    provider = MockKnowledgeGraphProvider()
    series = provider.confidence_series("/g/abc123", points=10)

    assert series == provider.confidence_series("/g/abc123", points=10)
    assert len(series) == 10
    dates = [obs.observed_at for obs in series]
    assert dates == sorted(dates)
    assert len(set(dates)) == len(dates)
    assert all(obs.score > 0 for obs in series)
    # Different entities get different series.
    other = provider.confidence_series("/g/zzz999", points=10)
    assert [o.score for o in other] != [o.score for o in series]


# ---------------------------------------------------------------------------
# sensor.py
# ---------------------------------------------------------------------------


def test_classify_trend_all_four_classes():
    assert classify_trend([100.0, 106.0, 112.0, 118.0, 124.0]) == TrendClass.RISING
    assert classify_trend([124.0, 118.0, 112.0, 106.0, 100.0]) == TrendClass.DECLINING
    assert classify_trend([100.0, 101.0, 100.0, 100.5, 100.0]) == TrendClass.STABLE
    assert classify_trend([100.0, 140.0, 80.0, 150.0, 90.0]) == TrendClass.VOLATILE
    assert classify_trend([]) == TrendClass.STABLE
    assert classify_trend([42.0]) == TrendClass.STABLE


def test_analyze_series_metrics():
    observations = [
        SensorObservation(observed_at=f"2026-01-{5 + i:02d}", score=score)
        for i, score in enumerate([100.0, 110.0, 120.0, 130.0])
    ]
    report = analyze_series("/g/abc", observations, name="Acme")

    assert report.kg_mid == "/g/abc"
    assert report.name == "Acme"
    assert report.latest_score == 130.0
    assert report.mean_score == 115.0
    assert report.net_change == 30.0
    assert report.volatility == 0.0  # constant deltas -> zero stddev
    assert report.trend == TrendClass.RISING

    empty = analyze_series("/g/none", [])
    assert empty.latest_score == 0.0
    assert empty.volatility == 0.0
    assert empty.trend == TrendClass.STABLE


# ---------------------------------------------------------------------------
# bio_builder.py
# ---------------------------------------------------------------------------

_FULL_BIO = BioRequest(
    name="Jane Doe",
    roles=["CEO", "angel investor"],
    organizations=["Acme Robotics", "Doe Ventures"],
    works=["The Automation Playbook"],
    credentials=["PhD in Robotics from MIT"],
    location="Austin, Texas",
    websites=["https://janedoe.com"],
)


def test_build_bio_variants_ordered_and_subject_first():
    result = build_bio(_FULL_BIO)

    assert [v.length for v in result.variants] == [BioLength.SHORT, BioLength.MEDIUM, BioLength.LONG]
    short, medium, long = result.variants
    assert short.word_count <= medium.word_count <= long.word_count
    assert short.triple_count <= medium.triple_count <= long.triple_count
    assert long.triple_count >= 7  # 2 roles + 2 orgs + 1 work + 1 credential + location + site
    # Every sentence in every variant is subject-first (starts with the name).
    for variant in result.variants:
        sentences = [s for s in re.split(r"(?<=\.)\s+", variant.text) if s]
        assert sentences
        assert all(s.startswith("Jane Doe") for s in sentences)
        assert variant.triple_density > 0
    assert result.warnings == []  # rich input -> nothing to warn about
    # Deterministic across calls.
    assert build_bio(_FULL_BIO) == result


def test_build_bio_sparse_input_warns():
    result = build_bio(BioRequest(name="John Roe", organizations=["Roe LLC"]))

    assert len(result.variants) == 3
    assert result.variants[0].text.startswith("John Roe is a professional")
    joined = " ".join(result.warnings)
    assert "roles" in joined
    assert "3 structured facts" in joined
    assert "websites" in joined


# ---------------------------------------------------------------------------
# corroboration.py
# ---------------------------------------------------------------------------

_CANONICAL = {
    "name": "Jane Doe",
    "job_title": "CEO",
    "website": "https://janedoe.com",
}


def test_corroboration_detects_match_mismatch_and_missing():
    profiles = [
        SourceProfile(
            source=SourceType.WIKIPEDIA,
            facts={"name": "JANE DOE", "job_title": "ceo", "website": "https://janedoe.com/"},
        ),
        SourceProfile(
            source=SourceType.LINKEDIN,
            facts={"name": "Jane Doe", "job_title": "CTO"},  # mismatch + missing website
        ),
    ]
    report = audit_corroboration("Jane Doe", _CANONICAL, profiles)

    assert report.sources_checked == 2
    assert len(report.comparisons) == 6
    assert report.match_count == 4      # cosmetic diffs (case, trailing slash) still match
    assert report.mismatch_count == 1
    assert report.missing_count == 1
    assert report.consistency_score == round(100 * 4 / 6)
    statuses = {(c.source, c.fact): c.status for c in report.comparisons}
    assert statuses[(SourceType.LINKEDIN, "job_title")] == FactStatus.MISMATCH
    assert statuses[(SourceType.LINKEDIN, "website")] == FactStatus.MISSING
    assert len(report.fixes) == 2
    assert any("Update 'job_title' on linkedin" in fix for fix in report.fixes)
    assert any("Add 'website'" in fix for fix in report.fixes)


def test_corroboration_perfect_and_empty_inputs():
    perfect = audit_corroboration(
        "Jane Doe", _CANONICAL, [SourceProfile(source=SourceType.OWN_SITE, facts=dict(_CANONICAL))]
    )
    assert perfect.consistency_score == 100
    assert perfect.fixes == []

    empty = audit_corroboration("Jane Doe", _CANONICAL, [])
    assert empty.consistency_score == 100  # nothing contradicts the canonical narrative
    assert empty.sources_checked == 0
    assert empty.comparisons == []


def test_mock_profile_fetcher_deterministic():
    fetcher = MockProfileFetcher()
    profile = fetcher.fetch_profile(SourceType.CRUNCHBASE, "Jane Doe")

    assert profile == fetcher.fetch_profile(SourceType.CRUNCHBASE, "Jane Doe")
    assert profile.source == SourceType.CRUNCHBASE
    assert profile.facts["name"] == "Jane Doe"
    assert profile.url and "crunchbase.com" in profile.url
    assert {"job_title", "employer", "website"} <= set(profile.facts)


# ---------------------------------------------------------------------------
# entity_schema.py
# ---------------------------------------------------------------------------


def test_entity_schema_person_complete_relational_links():
    req = EntitySchemaRequest(
        entity_type=EntityType.PERSON,
        name="Jane Doe",
        url="https://janedoe.com",
        description="Robotics executive.",
        same_as=["https://en.wikipedia.org/wiki/Jane_Doe", "https://www.linkedin.com/in/janedoe"],
        job_title="CEO",
        works_for="Acme Robotics",
        founder_of=["Doe Ventures"],
        author_of=["The Automation Playbook"],
        alumni_of=["MIT"],
    )
    result = generate_entity_schema(req)

    assert result.warnings == []
    json_ld = result.json_ld
    assert json_ld["@context"] == "https://schema.org"
    assert json_ld["@type"] == "Person"
    assert json_ld["worksFor"] == {"@type": "Organization", "name": "Acme Robotics"}
    assert json_ld["alumniOf"] == [{"@type": "EducationalOrganization", "name": "MIT"}]
    assert json_ld["sameAs"] == req.same_as
    reverse = json_ld["@reverse"]
    assert reverse["founder"] == [{"@type": "Organization", "name": "Doe Ventures"}]
    assert reverse["author"] == [{"@type": "CreativeWork", "name": "The Automation Playbook"}]
    assert result.script_tag.startswith("<script") and "ld+json" in result.script_tag


def test_entity_schema_organization_warnings_and_founders():
    complete = generate_entity_schema(
        EntitySchemaRequest(
            entity_type=EntityType.ORGANIZATION,
            name="Acme Robotics",
            url="https://acme.example",
            logo="https://acme.example/logo.png",
            same_as=["https://www.wikidata.org/wiki/Q1"],
            founding_date="2019-04-01",
            founders=["Jane Doe"],
        )
    )
    assert complete.warnings == []
    assert complete.json_ld["@type"] == "Organization"
    assert complete.json_ld["founder"] == [{"@type": "Person", "name": "Jane Doe"}]
    assert complete.json_ld["foundingDate"] == "2019-04-01"

    sparse = generate_entity_schema(
        EntitySchemaRequest(entity_type=EntityType.ORGANIZATION, name="Acme Robotics")
    )
    joined = " ".join(sparse.warnings)
    assert "url" in joined
    assert "sameAs" in joined
    assert "logo" in joined


# ---------------------------------------------------------------------------
# repository.py
# ---------------------------------------------------------------------------


def test_repository_is_org_scoped():
    repo = PeoRepository()
    entity = TrackedEntity(kg_mid="/g/abc", name="Jane Doe")
    repo.track_entity("org-a", entity)

    assert repo.get_tracked("org-a", "/g/abc") == entity
    assert repo.get_tracked("org-b", "/g/abc") is None
    assert repo.list_tracked("org-a") == [entity]
    assert repo.list_tracked("org-b") == []
    repo.clear()
    assert repo.get_tracked("org-a", "/g/abc") is None


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


def test_peo_endpoints_require_auth():
    client, _ = _make_client(authenticated=False)
    assert client.post(f"{API}/peo/entities/search", json={"query": "x"}).status_code == 401
    assert client.post(f"{API}/peo/bio/build", json={"name": "x"}).status_code == 401
    assert client.get(f"{API}/peo/entities/sensor", params={"kg_mid": "/g/x"}).status_code == 401


def test_api_entity_search(peo_api):
    client, _ = peo_api
    r = client.post(f"{API}/peo/entities/search", json={"query": "jane doe", "limit": 5})

    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "jane doe"
    assert 0 < len(body["entities"]) <= 5
    assert all(e["kg_mid"].startswith("/g/") for e in body["entities"])


def test_api_track_then_sensor_and_tenant_isolation(peo_api):
    client, holder = peo_api
    entity = client.post(f"{API}/peo/entities/search", json={"query": "jane doe"}).json()["entities"][0]

    tracked = client.post(
        f"{API}/peo/entities/track",
        json={"kg_mid": entity["kg_mid"], "name": entity["name"], "types": entity["types"]},
    )
    assert tracked.status_code == 200
    assert tracked.json()["kg_mid"] == entity["kg_mid"]
    assert tracked.json()["latest_score"] > 0

    sensor = client.get(
        f"{API}/peo/entities/sensor", params={"kg_mid": entity["kg_mid"], "points": 8}
    )
    assert sensor.status_code == 200
    report = sensor.json()
    assert len(report["observations"]) == 8
    assert report["name"] == entity["name"]
    assert report["trend"] in {"rising", "stable", "volatile", "declining"}
    assert report["volatility"] >= 0

    # Untracked KGMID -> 404.
    missing = client.get(f"{API}/peo/entities/sensor", params={"kg_mid": "/g/untracked"})
    assert missing.status_code == 404 and missing.json()["error"] == "not_found"
    # Another org cannot read this org's tracked entity.
    holder["org_id"] = "org-b"
    other = client.get(f"{API}/peo/entities/sensor", params={"kg_mid": entity["kg_mid"]})
    assert other.status_code == 404


def test_api_bio_build(peo_api):
    client, _ = peo_api
    r = client.post(f"{API}/peo/bio/build", json=_FULL_BIO.model_dump())

    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Jane Doe"
    assert [v["length"] for v in body["variants"]] == ["short", "medium", "long"]
    assert all(v["text"].startswith("Jane Doe") for v in body["variants"])


def test_api_corroboration_with_inline_and_fetched_profiles(peo_api):
    client, _ = peo_api
    r = client.post(
        f"{API}/peo/corroboration/audit",
        json={
            "entity_name": "Jane Doe",
            "canonical_facts": _CANONICAL,
            "profiles": [{"source": "own_site", "facts": _CANONICAL}],
            "fetch_sources": ["wikipedia", "linkedin"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["sources_checked"] == 3  # 1 inline + 2 fetched
    assert 0 <= body["consistency_score"] <= 100
    assert len(body["comparisons"]) == 9  # 3 facts x 3 sources


def test_api_entity_schema(peo_api):
    client, _ = peo_api
    r = client.post(
        f"{API}/peo/schema/entity",
        json={"entity_type": "Person", "name": "Jane Doe", "job_title": "CEO"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["json_ld"]["@type"] == "Person"
    assert "ld+json" in body["script_tag"]
    assert any("sameAs" in w for w in body["warnings"])


def test_api_validation_error(peo_api):
    client, _ = peo_api
    r = client.post(f"{API}/peo/entities/search", json={})  # missing 'query'
    assert r.status_code == 422 and r.json()["error"] == "validation_failed"
