"""Background job queue tests: queue backends (inline + thread), the /jobs API,
and quota enforcement at submission time. Fully offline and deterministic."""
from __future__ import annotations

import threading

import pytest

from app.config import Settings
from app.jobs.queue import (
    InlineJobQueue,
    ThreadJobQueue,
    create_job_queue,
    get_job_queue,
    reset_job_queue,
)
from app.models.jobs import JobStatus, JobType

API = "/api/v1"

_LONG = "word " * 350
FAKE_SITE: dict[str, dict] = {
    "https://site.test/": {
        "status": 200,
        "html": (
            "<html><head><title>Home Page Title For Jobs Test</title>"
            "<meta name='description' content='" + ("home page description text " * 5) + "'>"
            "</head><body><h1>Home</h1><p>" + _LONG + "</p>"
            "<a href='/about'>About</a></body></html>"
        ),
    },
    "https://site.test/about": {
        "status": 200,
        "html": (
            "<html><head><title>About Us Jobs Test Company</title>"
            "<meta name='description' content='" + ("about page description text " * 5) + "'>"
            "</head><body><h1>About</h1><p>" + _LONG + "</p></body></html>"
        ),
    },
}


# ---------------------------------------------------------------------------
# Queue unit tests — inline backend
# ---------------------------------------------------------------------------


def test_inline_submit_executes_and_succeeds():
    q = InlineJobQueue(max_attempts=2)
    seen: list[int] = []

    def handler(progress):
        progress(40)
        seen.append(40)
        return "ref-1"

    job = q.submit("org-a", JobType.CRAWL, handler)
    assert job.status == JobStatus.SUCCEEDED
    fetched = q.get("org-a", job.id)
    assert fetched is not None
    assert fetched.progress == 100
    assert fetched.result_ref == "ref-1"
    assert fetched.attempts == 1
    assert fetched.error is None
    assert fetched.started_at is not None and fetched.finished_at is not None
    assert seen == [40]


def test_inline_retries_then_succeeds():
    q = InlineJobQueue(max_attempts=3)
    calls = {"n": 0}

    def flaky(progress):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient boom")
        return "ok"

    job = q.submit("org-a", JobType.RANK_POLL, flaky)
    assert job.status == JobStatus.SUCCEEDED
    assert job.attempts == 3
    assert job.result_ref == "ok"
    assert calls["n"] == 3


def test_inline_failure_exhausts_max_attempts():
    q = InlineJobQueue(max_attempts=2)
    calls = {"n": 0}

    def bad(progress):
        calls["n"] += 1
        raise ValueError("cannot do the thing")

    job = q.submit("org-a", JobType.REPORT, bad)
    assert job.status == JobStatus.FAILED
    assert job.attempts == 2
    assert calls["n"] == 2
    assert job.error is not None and "cannot do the thing" in job.error
    assert job.result_ref is None
    assert job.finished_at is not None


def test_queue_org_isolation():
    q = InlineJobQueue(max_attempts=1)
    a = q.submit("org-a", JobType.CRAWL, lambda p: "a")
    b = q.submit("org-b", JobType.CRAWL, lambda p: "b")
    assert q.get("org-a", a.id) is not None
    assert q.get("org-b", a.id) is None
    assert q.cancel("org-b", a.id) is None
    assert {j.id for j in q.list("org-a")} == {a.id}
    assert {j.id for j in q.list("org-b")} == {b.id}


def test_queue_list_filters_by_status_and_type():
    q = InlineJobQueue(max_attempts=1)
    ok = q.submit("org-a", JobType.CRAWL, lambda p: "x")
    bad = q.submit("org-a", JobType.REPORT, lambda p: 1 / 0)
    assert [j.id for j in q.list("org-a", status=JobStatus.FAILED)] == [bad.id]
    assert [j.id for j in q.list("org-a", job_type=JobType.CRAWL)] == [ok.id]
    assert q.list("org-a", status=JobStatus.FAILED, job_type=JobType.CRAWL) == []
    assert len(q.list("org-a")) == 2


def test_cancel_is_noop_for_finished_job():
    q = InlineJobQueue(max_attempts=1)
    job = q.submit("org-a", JobType.CRAWL, lambda p: "done")
    cancelled = q.cancel("org-a", job.id)
    assert cancelled is not None
    assert cancelled.status == JobStatus.SUCCEEDED  # best-effort: terminal jobs unchanged


# ---------------------------------------------------------------------------
# Queue unit tests — thread backend (deterministic via events + join)
# ---------------------------------------------------------------------------


def test_thread_queue_runs_jobs_to_completion():
    q = ThreadJobQueue(workers=4, max_attempts=2)
    try:
        jobs = [
            q.submit("org-a", JobType.REPORT, (lambda ref: lambda p: (p(50), ref)[1])(f"ref-{i}"))
            for i in range(6)
        ]
        q.join(timeout=5.0)
        for i, submitted in enumerate(jobs):
            done = q.get("org-a", submitted.id)
            assert done is not None
            assert done.status == JobStatus.SUCCEEDED
            assert done.progress == 100
            assert done.result_ref == f"ref-{i}"
    finally:
        q.shutdown()


def test_thread_queue_retries_failed_job():
    q = ThreadJobQueue(workers=1, max_attempts=2)
    try:
        lock = threading.Lock()
        calls = {"n": 0}

        def flaky(progress):
            with lock:
                calls["n"] += 1
                if calls["n"] == 1:
                    raise RuntimeError("first attempt fails")
            return "recovered"

        job = q.submit("org-a", JobType.CRAWL, flaky)
        q.join(timeout=5.0)
        done = q.get("org-a", job.id)
        assert done is not None
        assert done.status == JobStatus.SUCCEEDED
        assert done.attempts == 2
        assert done.result_ref == "recovered"
    finally:
        q.shutdown()


def test_thread_queue_cancels_queued_job():
    q = ThreadJobQueue(workers=1, max_attempts=2)
    try:
        started = threading.Event()
        release = threading.Event()
        second_ran = threading.Event()

        def blocker(progress):
            started.set()
            assert release.wait(timeout=5.0)
            return "first"

        def second(progress):
            second_ran.set()
            return "second"

        a = q.submit("org-a", JobType.CRAWL, blocker)
        assert started.wait(timeout=5.0)  # worker is now busy with job A
        b = q.submit("org-a", JobType.CRAWL, second)
        cancelled = q.cancel("org-a", b.id)
        assert cancelled is not None and cancelled.status == JobStatus.CANCELLED
        release.set()
        q.join(timeout=5.0)
        a_done = q.get("org-a", a.id)
        b_done = q.get("org-a", b.id)
        assert a_done is not None and a_done.status == JobStatus.SUCCEEDED
        assert b_done is not None and b_done.status == JobStatus.CANCELLED
        assert not second_ran.is_set()  # cancelled job never executed
    finally:
        q.shutdown()


def test_thread_queue_org_isolation():
    q = ThreadJobQueue(workers=2, max_attempts=1)
    try:
        a = q.submit("org-a", JobType.RANK_POLL, lambda p: "a")
        q.join(timeout=5.0)
        assert q.get("org-b", a.id) is None
        assert q.list("org-b") == []
        assert q.get("org-a", a.id) is not None
    finally:
        q.shutdown()


# ---------------------------------------------------------------------------
# Factory / settings
# ---------------------------------------------------------------------------


def test_factory_builds_inline_and_thread_backends():
    inline = create_job_queue(Settings(job_queue_backend="inline", job_max_attempts=5))
    assert isinstance(inline, InlineJobQueue)
    assert inline.max_attempts == 5
    thread = create_job_queue(
        Settings(job_queue_backend="thread", job_queue_workers=2, job_max_attempts=3)
    )
    try:
        assert isinstance(thread, ThreadJobQueue)
        assert thread.max_attempts == 3
    finally:
        thread.shutdown()


def test_factory_celery_and_rq_are_documented_stubs():
    with pytest.raises(NotImplementedError, match="celery"):
        create_job_queue(Settings(job_queue_backend="celery"))
    with pytest.raises(NotImplementedError, match="rq"):
        create_job_queue(Settings(job_queue_backend="rq"))
    with pytest.raises(ValueError, match="bogus"):
        create_job_queue(Settings(job_queue_backend="bogus"))


def test_job_settings_defaults():
    fields = Settings.model_fields
    assert fields["job_queue_backend"].default == "thread"
    assert fields["job_queue_workers"].default == 4
    assert fields["job_max_attempts"].default == 2


def test_job_queue_singleton_reset(monkeypatch):
    monkeypatch.setenv("SEO_JOB_QUEUE_BACKEND", "inline")
    from app.config import get_settings

    get_settings.cache_clear()
    reset_job_queue()
    try:
        q1 = get_job_queue()
        assert isinstance(q1, InlineJobQueue)
        assert get_job_queue() is q1
    finally:
        reset_job_queue()
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# API tests (inline backend override; results fetched via existing endpoints)
# ---------------------------------------------------------------------------


@pytest.fixture
def jobs_client(test_engine):
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from app.api import routes_jobs
    from app.api.deps import get_fetcher
    from app.core.crawler.fetcher import StaticFetcher
    from app.db.session import get_session
    from app.main import create_app
    from app.middleware.rate_limit import reset_rate_limit_state

    def _get_session():
        with Session(test_engine) as session:
            yield session

    app = create_app()
    # main.py wires the router in the app proper; include it here defensively so
    # these tests do not depend on that wiring (idempotent if already present).
    if not any(getattr(r, "path", "") == f"{API}/jobs" for r in app.routes):
        app.include_router(routes_jobs.router, prefix=API)
    queue = InlineJobQueue(max_attempts=2)  # one shared instance across requests
    app.dependency_overrides[get_session] = _get_session
    app.dependency_overrides[get_fetcher] = lambda: StaticFetcher(FAKE_SITE)
    app.dependency_overrides[routes_jobs.get_queue_dep] = lambda: queue
    reset_rate_limit_state()
    return TestClient(app)


def _submit_crawl(client, headers):
    return client.post(
        f"{API}/jobs/crawl",
        json={"start_url": "https://site.test/", "max_pages": 10},
        headers=headers,
    )


def test_jobs_endpoints_require_auth(jobs_client):
    assert jobs_client.post(f"{API}/jobs/crawl", json={"start_url": "https://site.test/"}).status_code == 401
    assert jobs_client.get(f"{API}/jobs").status_code == 401
    assert jobs_client.get(f"{API}/jobs/nope").status_code == 401
    assert jobs_client.post(f"{API}/jobs/nope/cancel").status_code == 401


def test_crawl_job_end_to_end(jobs_client, make_auth):
    a = make_auth(email="jobs-a@x.test", org_name="Jobs Org A", plan_code="agency")
    r = _submit_crawl(jobs_client, a["headers"])
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    assert job_id

    # Poll status via GET /jobs/{id} (inline backend => already terminal).
    st = jobs_client.get(f"{API}/jobs/{job_id}", headers=a["headers"])
    assert st.status_code == 200
    body = st.json()
    assert body["status"] == "succeeded"
    assert body["progress"] == 100
    assert body["attempts"] == 1
    crawl_id = body["result_ref"]
    assert crawl_id

    # Fetch the result through the EXISTING sync endpoint.
    crawl = jobs_client.get(f"{API}/audit/crawl/{crawl_id}", headers=a["headers"])
    assert crawl.status_code == 200
    assert crawl.json()["crawl_id"] == crawl_id
    assert crawl.json()["summary"]["total_pages"] >= 1

    # Tenant isolation: org B sees neither the job nor the crawl.
    b = make_auth(email="jobs-b@x.test", org_name="Jobs Org B", plan_code="agency")
    assert jobs_client.get(f"{API}/jobs/{job_id}", headers=b["headers"]).status_code == 404
    assert jobs_client.get(f"{API}/audit/crawl/{crawl_id}", headers=b["headers"]).status_code == 404
    assert jobs_client.get(f"{API}/jobs", headers=b["headers"]).json()["total"] == 0


def test_rank_poll_job_end_to_end(jobs_client, make_auth):
    h = make_auth(email="jobs-rank@x.test", org_name="Jobs Rank Org", plan_code="agency")["headers"]
    r = jobs_client.post(
        f"{API}/jobs/rank-poll",
        json={"domain": "site.test", "keywords": ["alpha", "beta", "gamma"]},
        headers=h,
    )
    assert r.status_code == 200
    job = jobs_client.get(f"{API}/jobs/{r.json()['job_id']}", headers=h).json()
    assert job["status"] == "succeeded"
    assert job["result_ref"] == "site.test|us"
    summary = jobs_client.get(f"{API}/rankings/site.test", headers=h)
    assert summary.status_code == 200
    assert summary.json()["total_keywords"] == 3


def test_report_job_end_to_end(jobs_client, make_auth):
    h = make_auth(email="jobs-rep@x.test", org_name="Jobs Report Org", plan_code="agency")["headers"]
    crawl_job = _submit_crawl(jobs_client, h)
    crawl_id = jobs_client.get(
        f"{API}/jobs/{crawl_job.json()['job_id']}", headers=h
    ).json()["result_ref"]
    r = jobs_client.post(
        f"{API}/jobs/report",
        json={"site": "site.test", "period_start": "2026-06-01", "period_end": "2026-06-30",
              "crawl_id": crawl_id},
        headers=h,
    )
    assert r.status_code == 200
    job = jobs_client.get(f"{API}/jobs/{r.json()['job_id']}", headers=h).json()
    assert job["status"] == "succeeded"
    assert job["result_ref"]  # report_id persisted via TenantRepos.save_report


def test_list_jobs_with_filters(jobs_client, make_auth):
    h = make_auth(email="jobs-list@x.test", org_name="Jobs List Org", plan_code="agency")["headers"]
    assert _submit_crawl(jobs_client, h).status_code == 200
    assert jobs_client.post(
        f"{API}/jobs/rank-poll", json={"domain": "site.test", "keywords": ["kw"]}, headers=h
    ).status_code == 200

    all_jobs = jobs_client.get(f"{API}/jobs", headers=h).json()
    assert all_jobs["total"] == 2
    crawls = jobs_client.get(f"{API}/jobs?type=crawl", headers=h).json()
    assert crawls["total"] == 1 and crawls["items"][0]["type"] == "crawl"
    succeeded = jobs_client.get(f"{API}/jobs?status=succeeded", headers=h).json()
    assert succeeded["total"] == 2
    failed = jobs_client.get(f"{API}/jobs?status=failed", headers=h).json()
    assert failed["total"] == 0


def test_crawl_job_quota_enforced_at_submission(jobs_client, make_auth):
    h = make_auth(email="jobs-q@x.test", org_name="Jobs Quota Co", plan_code="free")["headers"]
    for _ in range(5):  # free plan allows 5 crawls/month
        assert _submit_crawl(jobs_client, h).status_code == 200
    assert _submit_crawl(jobs_client, h).status_code == 402  # 6th rejected at submission


def test_cancel_job_via_api(jobs_client, make_auth):
    h = make_auth(email="jobs-c@x.test", org_name="Jobs Cancel Org", plan_code="agency")["headers"]
    job_id = _submit_crawl(jobs_client, h).json()["job_id"]
    # Inline backend already finished it: cancel is a best-effort no-op.
    r = jobs_client.post(f"{API}/jobs/{job_id}/cancel", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "succeeded"
    assert jobs_client.post(f"{API}/jobs/unknown-id/cancel", headers=h).status_code == 404
