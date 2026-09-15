"""Shared pytest fixtures: path setup, sample HTML, test DB engine, auth helpers."""
from __future__ import annotations

import pathlib
import sys

import pytest

_BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

_LONG = "word " * 350
FAKE_SITE: dict[str, dict] = {
    "https://site.test/": {
        "status": 200,
        "html": (
            "<html><head><title>Home Page Title For Site Test</title>"
            "<meta name='description' content='" + ("home page description text " * 5) + "'>"
            "</head><body><h1>Home</h1><p>" + _LONG + "</p>"
            "<a href='/about'>About</a><a href='/missing'>Missing</a></body></html>"
        ),
    },
    "https://site.test/about": {
        "status": 200,
        "html": (
            "<html><head><title>About Us Site Test Company</title>"
            "<meta name='description' content='" + ("about page description text " * 5) + "'>"
            "</head><body><h1>About</h1><p>" + _LONG + "</p></body></html>"
        ),
    },
    "https://site.test/missing": {"status": 404, "html": "Not Found"},
}


@pytest.fixture
def sample_html() -> str:
    return (
        "<!doctype html><html lang='en'><head>"
        "<title>Best Running Shoes for Beginners (2026 Guide)</title>"
        "<meta name='description' content='Compare the best running shoes for beginners in 2026.' />"
        "<meta name='robots' content='index,follow' />"
        "<link rel='canonical' href='https://example.com/running-shoes' />"
        "<link rel='alternate' hreflang='fr' href='https://example.com/fr/running-shoes' />"
        "<script type='application/ld+json'>{\"@context\":\"https://schema.org\",\"@type\":\"Article\",\"headline\":\"Best Running Shoes\"}</script>"
        "</head><body><h1>Best Running Shoes for Beginners</h1><h2>How we tested</h2>"
        "<p>Choosing the best running shoes for beginners means balancing comfort, support and price. "
        "Our team tested dozens of running shoes to find the most comfortable options for new runners.</p>"
        "<img src='/img/shoe.jpg' alt='A blue running shoe' /><img src='/img/nolt.jpg' />"
        "<a href='/guides/marathon'>Marathon guide</a>"
        "<a href='https://external.example.org/review' rel='nofollow'>External review</a>"
        "</body></html>"
    )


@pytest.fixture
def test_engine():
    from sqlalchemy.pool import StaticPool
    from sqlmodel import SQLModel, create_engine

    import app.db  # noqa: F401  (registers tables)

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    from sqlmodel import Session

    with Session(test_engine) as session:
        yield session


@pytest.fixture
def app_client(test_engine):
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from app.api.deps import get_fetcher
    from app.core.crawler.fetcher import StaticFetcher
    from app.db.session import get_session
    from app.main import create_app
    from app.middleware.rate_limit import reset_rate_limit_state

    def _get_session():
        with Session(test_engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _get_session
    app.dependency_overrides[get_fetcher] = lambda: StaticFetcher(FAKE_SITE)
    reset_rate_limit_state()
    return TestClient(app)


@pytest.fixture
def make_auth(test_engine):
    from sqlmodel import Session

    from app.security.tokens import create_access_token
    from app.tenancy.provisioning import create_local_user, create_organization

    def _make(email="owner@acme.test", org_name="Acme Co", plan_code="pro",
              password="pw123456", full_name="Owner") -> dict:
        with Session(test_engine) as s:
            user = create_local_user(s, email, password, full_name)
            org, membership = create_organization(s, org_name, user, plan_code=plan_code)
            token = create_access_token(user.id, email=user.email, org_id=org.id, role=membership.role)
        return {"headers": {"Authorization": f"Bearer {token}"}, "token": token,
                "user_id": user.id, "org_id": org.id, "email": user.email}

    return _make
