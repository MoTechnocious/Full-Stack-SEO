"""Job queue backends.

Two working backends ship in-process:

- :class:`InlineJobQueue` — executes the job synchronously at submission time.
  Used in tests and for dev parity (identical state machine, zero threads).
- :class:`ThreadJobQueue` — stdlib :class:`~concurrent.futures.ThreadPoolExecutor`
  with a configurable worker count and a thread-safe, org-scoped registry.

``create_job_queue`` is the factory driven by ``settings.job_queue_backend``
("inline" | "thread" | "celery" | "rq"). The celery/rq values are documented
adapter stubs that raise :class:`NotImplementedError` with activation guidance —
there is deliberately no hard dependency on celery or redis.

Every job transition emits one structured log line (``job_id``, ``org_id``,
``type``, ``status``, ``attempt`` as extra fields) via the shared JSON logger.
"""
from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone

from app.config import Settings, get_settings
from app.logging_config import get_logger
from app.models.jobs import Job, JobStatus, JobType

logger = get_logger("jobs")

# A handler receives a progress callback (0-100) and returns a result_ref.
ProgressFn = Callable[[int], None]
JobHandler = Callable[[ProgressFn], str | None]

_TERMINAL = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobQueue(ABC):
    """Interface + shared state machine for org-scoped job queues.

    The registry is thread-safe; every read (``get``/``list``/``cancel``) is
    scoped to a single ``org_id`` and refuses to expose another tenant's jobs.
    """

    def __init__(self, *, max_attempts: int = 2) -> None:
        self.max_attempts = max(1, int(max_attempts))
        self._lock = threading.RLock()
        self._jobs: dict[str, Job] = {}
        self._handlers: dict[str, JobHandler] = {}

    # ---- Submission ----
    def submit(self, org_id: str, job_type: JobType, handler: JobHandler) -> Job:
        """Register a job and hand it to the backend. Returns a snapshot."""
        job = Job(org_id=org_id, type=job_type)
        with self._lock:
            self._jobs[job.id] = job
            self._handlers[job.id] = handler
        self._log(job)
        self._dispatch(job.id)
        return self.get(org_id, job.id)  # type: ignore[return-value]  # just registered

    @abstractmethod
    def _dispatch(self, job_id: str) -> None:
        """Backend-specific: schedule ``self._execute(job_id)``."""

    # ---- Org-scoped registry reads ----
    def get(self, org_id: str, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.org_id != org_id:
                return None
            return job.model_copy(deep=True)

    def list(
        self,
        org_id: str,
        status: JobStatus | None = None,
        job_type: JobType | None = None,
    ) -> list[Job]:
        with self._lock:
            jobs = [
                j.model_copy(deep=True)
                for j in self._jobs.values()
                if j.org_id == org_id
                and (status is None or j.status == status)
                and (job_type is None or j.type == job_type)
            ]
        return sorted(jobs, key=lambda j: j.submitted_at, reverse=True)

    # ---- Cancellation (best-effort for queued jobs) ----
    def cancel(self, org_id: str, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.org_id != org_id:
                return None
            if job.status == JobStatus.QUEUED:
                job.status = JobStatus.CANCELLED
                job.finished_at = _utcnow()
                self._log(job)
            snapshot = job.model_copy(deep=True)
        return snapshot

    # ---- Lifecycle / test hooks ----
    def join(self, timeout: float | None = None) -> None:
        """Block until all dispatched jobs settle (no-op for inline)."""

    def shutdown(self) -> None:
        """Release backend resources (no-op for inline)."""

    # ---- Shared execution state machine ----
    def _execute(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            handler = self._handlers.get(job_id)
            if job is None or handler is None or job.status != JobStatus.QUEUED:
                return  # cancelled (or unknown) before it started
            job.status = JobStatus.RUNNING
            job.started_at = _utcnow()
        self._log(job)

        def set_progress(value: int) -> None:
            with self._lock:
                if job.status == JobStatus.RUNNING:
                    job.progress = max(0, min(100, int(value)))

        last_error: str | None = None
        for attempt in range(1, self.max_attempts + 1):
            with self._lock:
                job.attempts = attempt
            try:
                result_ref = handler(set_progress)
            except Exception as exc:  # noqa: BLE001 - job failures become state, never raise
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "job attempt failed",
                    extra={
                        "job_id": job.id, "org_id": job.org_id, "type": job.type.value,
                        "status": job.status.value, "attempt": attempt,
                        "max_attempts": self.max_attempts, "error": last_error,
                    },
                )
                continue
            with self._lock:
                job.status = JobStatus.SUCCEEDED
                job.progress = 100
                job.result_ref = result_ref
                job.finished_at = _utcnow()
            self._log(job)
            return

        with self._lock:
            job.status = JobStatus.FAILED
            job.error = last_error
            job.finished_at = _utcnow()
        self._log(job)

    def _log(self, job: Job) -> None:
        logger.info(
            f"job {job.status.value}",
            extra={
                "job_id": job.id, "org_id": job.org_id, "type": job.type.value,
                "status": job.status.value, "attempt": job.attempts,
                "progress": job.progress, "result_ref": job.result_ref,
                "error": job.error,
            },
        )


class InlineJobQueue(JobQueue):
    """Executes jobs synchronously at submission (tests / dev parity)."""

    def _dispatch(self, job_id: str) -> None:
        self._execute(job_id)


class ThreadJobQueue(JobQueue):
    """ThreadPoolExecutor-backed queue with a configurable worker count."""

    def __init__(self, *, workers: int = 4, max_attempts: int = 2) -> None:
        super().__init__(max_attempts=max_attempts)
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, int(workers)), thread_name_prefix="jobq"
        )
        self._futures: dict[str, Future] = {}

    def _dispatch(self, job_id: str) -> None:
        future = self._executor.submit(self._execute, job_id)
        with self._lock:
            self._futures[job_id] = future

    def cancel(self, org_id: str, job_id: str) -> Job | None:
        snapshot = super().cancel(org_id, job_id)
        if snapshot is not None and snapshot.status == JobStatus.CANCELLED:
            with self._lock:
                future = self._futures.get(job_id)
            if future is not None:
                future.cancel()  # best-effort; _execute also re-checks status
        return snapshot

    def join(self, timeout: float | None = None) -> None:
        with self._lock:
            futures = list(self._futures.values())
        for future in futures:
            try:
                future.result(timeout=timeout)
            except Exception:  # noqa: BLE001 - cancelled futures; job errors never propagate
                pass

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)


def create_job_queue(settings: Settings | None = None) -> JobQueue:
    """Build a queue from ``settings.job_queue_backend``.

    Distributed adapters are documented stubs:

    - ``celery``: add ``celery[redis]`` to requirements, implement a
      ``CeleryJobQueue(JobQueue)`` whose ``_dispatch`` calls a shared Celery
      task (``run_job.delay(job_id)``) and whose registry is backed by Redis or
      the DB instead of process memory, then set ``SEO_JOB_QUEUE_BACKEND=celery``
      plus broker/result env vars.
    - ``rq``: add ``rq`` to requirements, implement an ``RqJobQueue(JobQueue)``
      whose ``_dispatch`` enqueues onto an ``rq.Queue`` (Redis connection from
      settings) and run ``rq worker`` processes, then set
      ``SEO_JOB_QUEUE_BACKEND=rq``.
    """
    settings = settings or get_settings()
    backend = settings.job_queue_backend.strip().lower()
    if backend == "inline":
        return InlineJobQueue(max_attempts=settings.job_max_attempts)
    if backend == "thread":
        return ThreadJobQueue(
            workers=settings.job_queue_workers, max_attempts=settings.job_max_attempts
        )
    if backend == "celery":
        raise NotImplementedError(
            "Celery backend is a documented adapter stub: install 'celery[redis]', "
            "implement CeleryJobQueue (see create_job_queue docstring), and set "
            "SEO_JOB_QUEUE_BACKEND=celery. Use 'thread' or 'inline' meanwhile."
        )
    if backend == "rq":
        raise NotImplementedError(
            "RQ backend is a documented adapter stub: install 'rq', implement "
            "RqJobQueue (see create_job_queue docstring), and set "
            "SEO_JOB_QUEUE_BACKEND=rq. Use 'thread' or 'inline' meanwhile."
        )
    raise ValueError(
        f"Unknown job queue backend '{settings.job_queue_backend}'. "
        "Expected one of: inline, thread, celery, rq."
    )


_QUEUE: JobQueue | None = None
_QUEUE_LOCK = threading.Lock()


def get_job_queue() -> JobQueue:
    """Return the process-wide queue singleton (built from settings)."""
    global _QUEUE
    if _QUEUE is None:
        with _QUEUE_LOCK:
            if _QUEUE is None:
                _QUEUE = create_job_queue()
    return _QUEUE


def reset_job_queue() -> None:
    """Drop the singleton (tests)."""
    global _QUEUE
    with _QUEUE_LOCK:
        if _QUEUE is not None:
            _QUEUE.shutdown()
            _QUEUE = None
