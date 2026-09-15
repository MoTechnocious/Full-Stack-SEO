"""Account, org, API-key, and billing flow tests (multi-tenant SaaS)."""
from __future__ import annotations

API = "/api/v1"


def _signup(client, email, org="Acme Co", pw="pw123456"):
    r = client.post(f"{API}/auth/signup", json={"email": email, "password": pw, "org_name": org, "full_name": "U"})
    assert r.status_code == 200, r.text
    body = r.json()
    return body, {"Authorization": f"Bearer {body['access_token']}"}


def test_signup_login_me(app_client):
    body, headers = _signup(app_client, "owner@acme.test")
    assert body["org"]["plan_code"] == "free" and body["org"]["role"] == "owner"
    assert app_client.post(f"{API}/auth/signup", json={"email": "owner@acme.test", "password": "x"}).status_code == 400
    assert app_client.post(f"{API}/auth/login", json={"email": "owner@acme.test", "password": "nope"}).status_code == 401
    assert app_client.post(f"{API}/auth/login", json={"email": "owner@acme.test", "password": "pw123456"}).status_code == 200
    me = app_client.get(f"{API}/auth/me", headers=headers).json()
    assert me["role"] == "owner" and me["plan_code"] == "free" and me["auth_method"] == "token"
    assert app_client.get(f"{API}/auth/me").status_code == 401


def test_plans_public_and_upgrade(app_client):
    plans = app_client.get(f"{API}/billing/plans").json()
    codes = {p["code"] for p in plans}
    assert {"free", "starter", "pro", "agency", "enterprise"} <= codes
    _, headers = _signup(app_client, "up@acme.test")
    assert app_client.get(f"{API}/billing/subscription", headers=headers).json()["plan_code"] == "free"
    up = app_client.post(f"{API}/billing/checkout", json={"plan_code": "pro"}, headers=headers)
    assert up.status_code == 200 and "checkout_url" in up.json()
    assert app_client.get(f"{API}/billing/subscription", headers=headers).json()["plan_code"] == "pro"
    usage = app_client.get(f"{API}/usage", headers=headers).json()
    assert usage["plan_code"] == "pro"
    assert usage["resources"]["tracked_keywords"]["limit"] == 1000


def test_api_key_lifecycle(app_client):
    _, headers = _signup(app_client, "keys@acme.test")
    created = app_client.post(f"{API}/api-keys", json={"name": "ci", "role": "editor"}, headers=headers)
    assert created.status_code == 200
    secret = created.json()["secret"]
    assert secret.startswith("msk_")
    listed = app_client.get(f"{API}/api-keys", headers=headers).json()
    assert listed[0]["last4"] and "secret" not in listed[0]
    by_key = app_client.get(f"{API}/auth/me", headers={"X-API-Key": secret})
    assert by_key.status_code == 200 and by_key.json()["auth_method"] == "api_key"
    app_client.delete(f"{API}/api-keys/{created.json()['id']}", headers=headers)
    assert app_client.get(f"{API}/auth/me", headers={"X-API-Key": secret}).status_code == 401


def test_orgs_and_invite_flow(app_client):
    owner_body, owner_h = _signup(app_client, "boss@agency.test", org="Agency HQ")
    app_client.post(f"{API}/orgs", json={"name": "Client Site A"}, headers=owner_h)
    assert len(app_client.get(f"{API}/orgs", headers=owner_h).json()) == 2
    inv = app_client.post(f"{API}/orgs/invites", json={"email": "mate@agency.test", "role": "editor"}, headers=owner_h)
    assert inv.status_code == 200
    token = inv.json()["token"]
    _, mate_h = _signup(app_client, "mate@agency.test", org="Mate Co")
    acc = app_client.post(f"{API}/orgs/invites/accept", json={"token": token}, headers=mate_h)
    assert acc.status_code == 200
    hq_org = owner_body["org"]["id"]
    assert acc.json()["org_id"] == hq_org
    sw = app_client.post(f"{API}/auth/switch-org", json={"org_id": hq_org}, headers=mate_h)
    assert sw.status_code == 200
    mate_hq_h = {"Authorization": f"Bearer {sw.json()['access_token']}"}
    assert app_client.get(f"{API}/auth/me", headers=mate_hq_h).json()["role"] == "editor"


def test_rbac_client_cannot_manage_keys(app_client):
    owner_body, owner_h = _signup(app_client, "own@rbac.test", org="RBAC Co")
    inv = app_client.post(f"{API}/orgs/invites", json={"email": "ro@rbac.test", "role": "client"}, headers=owner_h)
    _, ro_h = _signup(app_client, "ro@rbac.test", org="RO Co")
    app_client.post(f"{API}/orgs/invites/accept", json={"token": inv.json()["token"]}, headers=ro_h)
    sw = app_client.post(f"{API}/auth/switch-org", json={"org_id": owner_body["org"]["id"]}, headers=ro_h)
    ro_hq = {"Authorization": f"Bearer {sw.json()['access_token']}"}
    assert app_client.post(f"{API}/api-keys", json={"name": "x"}, headers=ro_hq).status_code == 403
