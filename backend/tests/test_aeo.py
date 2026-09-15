"""Tests for the Answer Engine Optimization engine (PAA extraction, question
clustering, schema graphs, internal linking, voice audits) and its API routes.
Deterministic: no network, no randomness. The router is mounted on a small
purpose-built FastAPI app with the tenant dependency overridden.
"""
from __future__ import annotations

import pytest

from app.core.aeo.clustering import build_cluster_map, cluster_questions
from app.core.aeo.linking import suggest_links
from app.core.aeo.providers import MockSerpQuestionProvider
from app.core.aeo.schema_graph import build_schema_graph
from app.core.aeo.vectorize import content_tokens, cosine_similarity, tfidf_vectors
from app.core.aeo.voice import voice_audit
from app.models.aeo import (
    BreadcrumbItem,
    ClusterMapRequest,
    HowToInput,
    HowToStep,
    LinkSuggestRequest,
    PageDoc,
    PageRef,
    QAItem,
    SchemaGraphRequest,
    VoiceAuditRequest,
)

API = "/api/v1"


# ---------------------------------------------------------------------------
# Test app (mirrors conftest.app_client, but mounts only the AEO router)
# ---------------------------------------------------------------------------


def _make_client(authenticated: bool = True):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import routes_aeo
    from app.db.session import get_session
    from app.middleware.errors import register_exception_handlers
    from app.tenancy.context import TenantContext
    from app.tenancy.deps import get_tenant_context
    from app.tenancy.rbac import Role

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(routes_aeo.router, prefix=API)

    if authenticated:
        app.dependency_overrides[get_tenant_context] = lambda: TenantContext(
            user_id="u-test", org_id="org-a", org_name="Test Org", role=Role.OWNER
        )
    else:
        app.dependency_overrides[get_session] = lambda: None  # no DB needed pre-auth
    return TestClient(app)


@pytest.fixture
def aeo_client():
    return _make_client()


# ---------------------------------------------------------------------------
# providers.py — PAA + autocomplete
# ---------------------------------------------------------------------------


def test_mock_paa_roots_and_followup_chains():
    provider = MockSerpQuestionProvider()
    questions = provider.paa_questions("content marketing", depth=3, per_level=5)

    assert questions == provider.paa_questions("content marketing", depth=3, per_level=5)
    roots = [q for q in questions if q.depth == 0]
    assert len(roots) == 5
    assert all(q.parent is None for q in roots)
    assert all("content marketing" in q.question for q in roots)

    texts = {q.question for q in questions}
    assert len(texts) == len(questions)  # no duplicates
    children = [q for q in questions if q.depth >= 1]
    assert children
    for child in children:
        assert child.parent in texts  # every follow-up chains off a known question
        assert child.question.startswith(child.parent)
    assert any(q.depth == 2 for q in questions)  # chains reach the requested depth


def test_mock_paa_depth_one_yields_only_roots_and_blank_seed_is_empty():
    provider = MockSerpQuestionProvider()
    questions = provider.paa_questions("crm software", depth=1, per_level=4)
    assert len(questions) == 4
    assert all(q.depth == 0 and q.parent is None for q in questions)
    assert provider.paa_questions("   ") == []


def test_mock_autocomplete_pathways():
    provider = MockSerpQuestionProvider()
    suggestions = provider.autocomplete("content marketing", limit=6)

    assert suggestions == provider.autocomplete("content marketing", limit=6)
    assert len(suggestions) == 6
    assert all(s.startswith("content marketing ") for s in suggestions)
    assert len(set(suggestions)) == 6
    assert provider.autocomplete("") == []


# ---------------------------------------------------------------------------
# vectorize.py
# ---------------------------------------------------------------------------


def test_tfidf_cosine_bounds():
    docs = [
        content_tokens("running shoes for beginners"),
        content_tokens("running shoes for beginners"),
        content_tokens("email newsletter deliverability"),
    ]
    vectors = tfidf_vectors(docs)

    assert cosine_similarity(vectors[0], vectors[1]) == pytest.approx(1.0)
    assert cosine_similarity(vectors[0], vectors[2]) == 0.0
    assert cosine_similarity({}, vectors[0]) == 0.0
    for a in vectors:
        for b in vectors:
            assert 0.0 <= cosine_similarity(a, b) <= 1.0 + 1e-9


# ---------------------------------------------------------------------------
# clustering.py
# ---------------------------------------------------------------------------

_QUESTIONS = [
    "what is content marketing",
    "how does content marketing work",
    "content marketing benefits",
    "best crm software",
    "crm software pricing",
]


def test_cluster_questions_groups_related_topics():
    clusters = cluster_questions(_QUESTIONS, threshold=0.25)

    assert clusters == cluster_questions(_QUESTIONS, threshold=0.25)  # deterministic
    assert len(clusters) == 2
    by_primary = {c.primary_question: c for c in clusters}
    content = by_primary["what is content marketing"]
    crm = by_primary["best crm software"]
    assert set(content.questions) == set(_QUESTIONS[:3])
    assert set(crm.questions) == set(_QUESTIONS[3:])
    assert "content" in content.label and "marketing" in content.label
    assert "crm" in crm.label

    assert cluster_questions([]) == []
    solo = cluster_questions(["is it worth it"])
    assert len(solo) == 1 and solo[0].questions == ["is it worth it"]


def test_build_cluster_map_targets_pages_and_templates():
    pages = [
        PageRef(url="/blog/content-marketing-guide", title="Content Marketing Guide"),
        PageRef(url="/tools/crm", title="Best CRM Software Compared"),
    ]
    result = build_cluster_map(ClusterMapRequest(questions=_QUESTIONS, pages=pages))

    assert len(result.faq) == len(result.clusters) == 2
    targets = {entry.question: entry.target_page for entry in result.faq}
    assert targets["what is content marketing"] == "/blog/content-marketing-guide"
    assert targets["best crm software"] == "/tools/crm"
    for entry in result.faq:
        assert entry.question in entry.answer_template
        assert "40 words" in entry.answer_template

    # Without candidate pages, a new answer-page slug is suggested.
    unmapped = build_cluster_map(ClusterMapRequest(questions=_QUESTIONS[:3]))
    assert all(entry.target_page.startswith("/answers/") for entry in unmapped.faq)


# ---------------------------------------------------------------------------
# schema_graph.py
# ---------------------------------------------------------------------------


def test_schema_graph_full_page_builds_all_nodes():
    req = SchemaGraphRequest(
        url="https://example.com/guides/podcasting/",
        title="How to Start a Podcast",
        description="A complete beginner guide to podcasting.",
        breadcrumbs=[
            BreadcrumbItem(name="Home", url="https://example.com/"),
            BreadcrumbItem(name="Guides", url="https://example.com/guides/"),
        ],
        faqs=[
            QAItem(question="How much does podcasting cost?", answer="Usually under $100."),
            QAItem(question="What gear do I need?", answer="A USB microphone is enough."),
        ],
        qa=QAItem(question="Can I podcast from my phone?", answer="Yes, with a recording app."),
        how_to=HowToInput(
            name="Start a podcast",
            steps=[HowToStep(name="Pick a topic"), HowToStep(name="Record", text="Record a pilot.")],
        ),
    )
    result = build_schema_graph(req)

    assert result.node_types == ["WebPage", "BreadcrumbList", "FAQPage", "QAPage", "HowTo"]
    assert result.warnings == []
    json_ld = result.json_ld
    assert json_ld["@context"] == "https://schema.org"
    nodes = json_ld["@graph"]
    assert all("@context" not in node for node in nodes)  # single top-level context
    assert all("@id" in node for node in nodes)
    web_page = nodes[0]
    assert web_page["breadcrumb"] == {"@id": nodes[1]["@id"]}
    faq_node = nodes[2]
    assert len(faq_node["mainEntity"]) == 2
    assert faq_node["mainEntity"][0]["acceptedAnswer"]["text"] == "Usually under $100."
    qa_node = nodes[3]
    assert qa_node["mainEntity"]["acceptedAnswer"]["text"] == "Yes, with a recording app."
    howto_node = nodes[4]
    assert [s["name"] for s in howto_node["step"]] == ["Pick a topic", "Record"]
    assert result.script_tag.startswith("<script") and "ld+json" in result.script_tag


def test_schema_graph_minimal_and_empty_howto_warn():
    minimal = build_schema_graph(SchemaGraphRequest(url="https://example.com/", title="Home"))
    assert minimal.node_types == ["WebPage"]
    assert any("FAQPage/QAPage/HowTo" in w for w in minimal.warnings)

    empty_howto = build_schema_graph(
        SchemaGraphRequest(
            url="https://example.com/x", title="X", how_to=HowToInput(name="Empty", steps=[])
        )
    )
    assert "HowTo" in empty_howto.node_types
    assert any("step" in w for w in empty_howto.warnings)


# ---------------------------------------------------------------------------
# linking.py
# ---------------------------------------------------------------------------

_RUNNING_BODY = (
    "Running shoes cushion every stride. Beginners should choose running shoes with soft "
    "foam, breathable mesh, and a comfortable fit for longer training runs."
)
_PAGES = [
    PageDoc(url="https://site.test/guide", title="Running Shoes Guide", body=_RUNNING_BODY),
    PageDoc(
        url="https://site.test/beginners",
        title="Best Running Shoes for Beginners",
        body=_RUNNING_BODY + " New runners also need a training plan for their first weeks.",
    ),
    PageDoc(
        url="https://site.test/newsletter",
        title="Email Newsletter Tips",
        body="Grow an email newsletter with strong subject lines, welcome sequences, and clean lists.",
    ),
]


def test_suggest_links_recommends_similar_pages_only():
    result = suggest_links(LinkSuggestRequest(pages=_PAGES, similarity_threshold=0.2))

    assert result.pages_analyzed == 3
    pairs = {(s.source_url, s.target_url) for s in result.suggestions}
    assert ("https://site.test/guide", "https://site.test/beginners") in pairs
    assert ("https://site.test/beginners", "https://site.test/guide") in pairs
    # The unrelated newsletter page is neither source nor target.
    assert not any("newsletter" in a or "newsletter" in b for a, b in pairs)
    for suggestion in result.suggestions:
        assert suggestion.source_url != suggestion.target_url
        assert 0.2 <= suggestion.similarity <= 1.0
    by_pair = {(s.source_url, s.target_url): s for s in result.suggestions}
    anchor = by_pair[("https://site.test/guide", "https://site.test/beginners")].anchor_text
    assert anchor == "Best Running Shoes for Beginners"


def test_suggest_links_excludes_existing_links_and_respects_threshold():
    pages = [_PAGES[0].model_copy(update={"existing_links": ["https://site.test/beginners/"]})] + _PAGES[1:]
    result = suggest_links(LinkSuggestRequest(pages=pages, similarity_threshold=0.2))
    pairs = {(s.source_url, s.target_url) for s in result.suggestions}
    assert ("https://site.test/guide", "https://site.test/beginners") not in pairs  # already linked
    assert ("https://site.test/beginners", "https://site.test/guide") in pairs      # reverse still suggested

    strict = suggest_links(LinkSuggestRequest(pages=_PAGES, similarity_threshold=0.99))
    assert strict.suggestions == []


# ---------------------------------------------------------------------------
# voice.py
# ---------------------------------------------------------------------------

_GOOD_ANSWER = (
    "You can start a podcast in one afternoon. Pick a topic you enjoy and record a short "
    "test episode with your phone. Then publish it to one platform and share it."
)
_BAD_ANSWER = (
    "Enterprises orchestrating multidimensional optimization initiatives systematically "
    "operationalize heterogeneous infrastructural methodologies, harmonizing organizational "
    "interdependencies, prioritizing technological modernization, facilitating anticipatory "
    "computational paradigms, institutionalizing comprehensive governance frameworks across "
    "geographically distributed administrative hierarchies, calibrating proprietary analytical "
    "instrumentation, synchronizing interdepartmental accountability structures, and "
    "perpetually renegotiating multilateral infrastructural commitments notwithstanding "
    "considerable organizational complexity throughout every conceivable operational dimension "
    "of the contemporary transnational corporation."
)


def test_voice_audit_good_answer_scores_high():
    result = voice_audit(
        VoiceAuditRequest(content=_GOOD_ANSWER, question="how do you start a podcast")
    )

    assert result.score >= 80
    assert result.grade in {"A", "B"}
    assert result.flesch >= 60
    assert 0 < result.avg_sentence_length <= 20
    assert result.first_paragraph_words <= 50
    by_code = {c.code: c for c in result.checks}
    assert by_code["concise_answer"].passed is True
    assert by_code["direct_answer"].passed is True
    assert by_code["conversational_tone"].passed is True
    assert result.fixes == []


def test_voice_audit_bad_answer_scores_low_with_fixes():
    result = voice_audit(VoiceAuditRequest(content=_BAD_ANSWER))

    assert result.score < 50
    assert result.grade in {"E", "F"}
    by_code = {c.code: c for c in result.checks}
    assert "direct_answer" not in by_code  # no target question supplied
    assert by_code["flesch_easy"].passed is False
    assert by_code["short_sentences"].passed is False
    assert by_code["concise_answer"].passed is False
    assert by_code["conversational_tone"].passed is False
    assert len(result.fixes) >= 4
    assert result.syllable_density > 1.7


def test_voice_audit_empty_content():
    result = voice_audit(VoiceAuditRequest(content=""))
    assert result.score == 0
    assert result.grade == "F"
    assert all(c.passed is False for c in result.checks)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


def test_aeo_endpoints_require_auth():
    client = _make_client(authenticated=False)
    assert client.post(f"{API}/aeo/questions/extract", json={"seed": "x"}).status_code == 401
    assert client.post(f"{API}/aeo/voice/audit", json={"content": "x"}).status_code == 401


def test_api_questions_extract(aeo_client):
    r = aeo_client.post(
        f"{API}/aeo/questions/extract",
        json={"seed": "content marketing", "depth": 2, "per_level": 4, "autocomplete_limit": 5},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["seed"] == "content marketing"
    assert len([q for q in body["questions"] if q["depth"] == 0]) == 4
    assert len(body["autocomplete"]) == 5

    without = aeo_client.post(
        f"{API}/aeo/questions/extract",
        json={"seed": "content marketing", "include_autocomplete": False},
    )
    assert without.status_code == 200 and without.json()["autocomplete"] == []


def test_api_clusters_map(aeo_client):
    r = aeo_client.post(
        f"{API}/aeo/clusters/map",
        json={
            "questions": _QUESTIONS,
            "pages": [{"url": "/blog/content-marketing-guide", "title": "Content Marketing Guide"}],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["clusters"]) == 2
    assert len(body["faq"]) == 2
    assert all(entry["target_page"] for entry in body["faq"])


def test_api_schema_graph(aeo_client):
    r = aeo_client.post(
        f"{API}/aeo/schema/graph",
        json={
            "url": "https://example.com/faq",
            "title": "FAQ",
            "faqs": [{"question": "Q?", "answer": "A."}],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["node_types"] == ["WebPage", "FAQPage"]
    assert "ld+json" in body["script_tag"]


def test_api_linking_suggest(aeo_client):
    r = aeo_client.post(
        f"{API}/aeo/linking/suggest",
        json={"pages": [p.model_dump() for p in _PAGES], "similarity_threshold": 0.2},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["pages_analyzed"] == 3
    assert len(body["suggestions"]) >= 2
    assert all(s["anchor_text"] for s in body["suggestions"])


def test_api_voice_audit(aeo_client):
    r = aeo_client.post(
        f"{API}/aeo/voice/audit",
        json={"content": _GOOD_ANSWER, "question": "how do you start a podcast"},
    )
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["score"] <= 100
    assert body["grade"] in {"A", "B", "C", "D", "E", "F"}
    assert body["checks"] and body["score"] >= 80


def test_api_validation_error(aeo_client):
    r = aeo_client.post(f"{API}/aeo/questions/extract", json={})  # missing 'seed'
    assert r.status_code == 422 and r.json()["error"] == "validation_failed"
