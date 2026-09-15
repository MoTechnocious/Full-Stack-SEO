"""Spine tests for the multi-tenant layer: auth, RBAC, feature gating, quotas."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.billing.deps import require_feature, require_quota
from app.billing.entitlements import get_limit, has_feature
from app.billing.usage import UsageService
from app.db.models_tenancy import ApiKey, Membership
from app.db.session import get_session
from app.middleware.errors import register_exception_handlers
from app.security.api_keys import generate_api_key
from app.security.tokens import create_access_token
from app.tenancy.context import TenantContext
from app.tenancy.deps import get_tenant_context, require_permission
from app.tenancy.provisioning import create_local_user


def _spine_app(test_engine) -> FastAPI:
    app = FastAPI()

    def _get_session():
        with Session(test_engine) as s:
            yield s

    app.dependency_overrides[get_session] = _get_session
    register_exception_handlers(app)

    @app.get("/whoami")
    def whoami(ctx: TenantContext = Depends(get_tenant_context)):
        return {"org_id": ctx.org_id, "role": ctx.role.value, "plan": ctx.plan_code, "auth": ctx.auth_method}

    @app.get("/admin")
    def admin(ctx: TenantContext = Depends(require_permission("members:manage"))):
        return {"ok": True}

    @app.get("/wl")
    def white_label(ctx: TenantContext = Depends(require_feature("white_label"))):
        return {"ok": True}

    @app.get("/quota")
    def quota(ctx: TenantContext = Depends(require_quota("crawls_per_month", 1))):
        return {"ok": True}

    return app


def test_plan_entitlements_unit():
    assert get_limit("free", "crawls_per_month") == 5
    assert get_limit("enterprise", "crawls_per_month") == -1  # unlimited
    assert has_feature("agency", "white_label") is True
    assert has_feature("free", "white_label") is False


def test_unauthenticated_rejected(test_engine):
    client = TestClient(_spine_app(test_engine))
    assert client.get("/whoami").status_code == 401


def test_token_auth_resolves_context(test_engine, make_auth):
    info = make_auth(plan_code="pro")
    client = TestClient(_spine_app(test_engine))
    r = client.get("/whoami", headers=info["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["org_id"] == info["org_id"]
    assert body["role"] == "owner"
    assert body["plan"] == "pro"
    assert body["auth"] == "token"


def test_api_key_auth(test_engine, make_auth):
    info = make_auth(plan_code="pro")
    gen = generate_api_key("msk")
    with Session(test_engine) as s:
        s.add(
            ApiKey(
                org_id=info["org_id"], user_id=info["user_id"], name="ci",
                prefix=gen.prefix, last4=gen.last4, hash=gen.hash, role="editor",
            )
        )
        s.commit()
    client = TestClient(_spine_app(test_engine))
    r = client.get("/whoami", headers={"X-API-Key": gen.secret})
    assert r.status_code == 200
    assert r.json()["auth"] == "api_key" and r.json()["role"] == "editor"
    # Wrong key rejected
    assert client.get("/whoami", headers={"X-API-Key": "msk_wrong"}).status_code == 401


def test_rbac_denies_client_role(test_engine, make_auth):
    info = make_auth(plan_code="pro")
    with Session(test_engine) as s:
        u2 = create_local_user(s, "client@acme.test", "pw123456", "Client User")
        s.add(Membership(org_id=info["org_id"], user_id=u2.id, role="client", status="active"))
        s.commit()
        token = create_access_token(u2.id, email=u2.email, org_id=info["org_id"], role="client")
    client = TestClient(_spine_app(test_engine))
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/whoami", headers=headers).json()["role"] == "client"
    assert client.get("/admin", headers=headers).status_code == 403  # cannot manage members
    # Owner can
    assert client.get("/admin", headers=info["headers"]).status_code == 200


def test_feature_gating(test_engine, make_auth):
    free = make_auth(email="free@x.test", org_name="Free Co", plan_code="free")
    agency = make_auth(email="ag@x.test", org_name="Agency Co", plan_code="agency")
    client = TestClient(_spine_app(test_engine))
    assert client.get("/wl", headers=free["headers"]).status_code == 402  # white_label not in free
    assert client.get("/wl", headers=agency["headers"]).status_code == 200


def test_quota_enforcement(test_engine, make_auth):
    free = make_auth(email="q@x.test", org_name="Quota Co", plan_code="free")
    client = TestClient(_spine_app(test_engine))
    assert client.get("/quota", headers=free["headers"]).status_code == 200  # under limit
    with Session(test_engine) as s:
        UsageService(s).record(free["org_id"], "crawls_per_month", 5)  # hit free limit (5)
    assert client.get("/quota", headers=free["headers"]).status_code == 402


def test_tenant_isolation_repos(test_engine, make_auth):
    """A crawl saved under org A must not be readable under org B."""
    from datetime import datetime, timezone

    from app.models.audit import CrawlConfig, CrawlResult
    from app.tenancy.repositories import get_repos

    a = make_auth(email="a@x.test", org_name="Org A")
    b = make_auth(email="b@x.test", org_name="Org B")
    crawl = CrawlResult(
        crawl_id="shared-id",
        start_url="https://a.test",
        config=CrawlConfig(start_url="https://a.test"),
        started_at=datetime.now(timezone.utc),
    )
    with Session(test_engine) as s:
        get_repos(s, a["org_id"]).save_crawl(crawl)
    with Session(test_engine) as s:
        assert get_repos(s, a["org_id"]).get_crawl("shared-id") is not None
        assert get_repos(s, b["org_id"]).get_crawl("shared-id") is None  # isolated
