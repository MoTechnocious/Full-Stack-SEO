"""Agentic execution engine: an org-scoped queue of executable SEO actions.

Providers (``ContentGenerator``, ``CmsAdapter``) are structural interfaces with
deterministic in-memory mocks, mirroring :mod:`app.integrations.crm_pipeline`.
``ActionQueueService`` owns the org-scoped queues and the execution loop
(pending -> running -> completed/failed, with awaiting_approval gating and
retry-on-failure up to ``max_attempts``); ``ActionExecutor`` dispatches each
action type to its provider. Fully deterministic — no network calls.
"""
from __future__ import annotations

import hashlib
import threading
import typing
from datetime import datetime, timezone

from app.core.local.citations import CitationSyncEngine, get_citation_engine
from app.core.local.gbp import GbpProvider, get_gbp_provider
from app.models.assistant import (
    ActionType,
    BlogDraft,
    ExecutionLogEntry,
    ExecutionStatus,
    QueuedAction,
    QueueRunReport,
)
from app.models.local import Directory, GbpPostCreate
from app.utils.text import word_count


class ContentGenerator(typing.Protocol):
    """Structural interface for blog-content generation providers."""

    def generate(self, keyword: str, topic: str | None = None) -> BlogDraft:
        """Produce an outline + draft for a keyword/topic.

        May raise on failure — the queue treats exceptions as retryable.
        """
        ...


class MockContentGenerator(ContentGenerator):
    """Deterministic outline+draft generator. Default for tests/dev."""

    provider = "mock"

    def generate(self, keyword: str, topic: str | None = None) -> BlogDraft:
        kw = (keyword or "").strip()
        if not kw:
            raise ValueError("write_blog_post requires a non-empty 'keyword' param")
        subject = (topic or "").strip() or kw
        title = f"{kw.title()}: The Complete Guide"
        outline = [
            f"What Is {kw.title()}?",
            f"Why {kw.title()} Matters",
            f"How To Get Started With {kw.title()}",
            "Common Mistakes To Avoid",
            "Key Takeaways",
        ]
        sections = [
            f"## {heading}\n\n"
            f"This section covers {heading.rstrip('?').lower()} in the context of {subject}. "
            f"It explains, in plain language, what readers searching for '{kw}' need to know, "
            f"with practical examples and clear next steps."
            for heading in outline
        ]
        draft = f"# {title}\n\n" + "\n\n".join(sections)
        return BlogDraft(
            keyword=kw,
            topic=subject,
            title=title,
            outline=outline,
            draft=draft,
            word_count=word_count(draft),
        )


class CmsAdapter(typing.Protocol):
    """Structural interface for CMS meta-tag update providers."""

    def update_meta_tags(
        self, page_url: str, title: str | None = None, description: str | None = None
    ) -> str:
        """Apply new meta tags to a page and return an external change reference.

        May raise on failure — the queue treats exceptions as retryable.
        """
        ...


class MockCmsAdapter(CmsAdapter):
    """Deterministic in-memory CMS adapter recording every meta-tag update."""

    provider = "mock"

    def __init__(self) -> None:
        self.updates: dict[str, dict[str, str | None]] = {}

    def update_meta_tags(
        self, page_url: str, title: str | None = None, description: str | None = None
    ) -> str:
        url = (page_url or "").strip()
        if not url:
            raise ValueError("update_meta_tags requires a non-empty 'page_url' param")
        self.updates[url] = {"title": title, "description": description}
        return f"cms_{hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]}"


class ActionExecutor:
    """Dispatches a :class:`QueuedAction` to the provider for its type."""

    def __init__(
        self,
        *,
        content_generator: ContentGenerator | None = None,
        cms_adapter: CmsAdapter | None = None,
        gbp_provider: GbpProvider | None = None,
        citation_engine: CitationSyncEngine | None = None,
    ) -> None:
        self.content_generator = content_generator or get_content_generator()
        self.cms_adapter = cms_adapter or get_cms_adapter()
        self.gbp_provider = gbp_provider or get_gbp_provider()
        self.citation_engine = citation_engine or get_citation_engine()

    def execute(self, action: QueuedAction) -> dict[str, object]:
        """Run one action and return its structured result payload.

        Raises on failure — the queue's execution loop handles retries.
        """
        params = action.params
        if action.type == ActionType.WRITE_BLOG_POST:
            draft = self.content_generator.generate(
                str(params.get("keyword", "")), topic=typing.cast("str | None", params.get("topic"))
            )
            return {"draft": draft.model_dump(mode="json")}
        if action.type == ActionType.UPDATE_META_TAGS:
            ref = self.cms_adapter.update_meta_tags(
                str(params.get("page_url", "")),
                title=typing.cast("str | None", params.get("title")),
                description=typing.cast("str | None", params.get("description")),
            )
            return {"cms_ref": ref, "page_url": params.get("page_url")}
        if action.type == ActionType.PUBLISH_GBP_UPDATE:
            summary = str(params.get("summary", "")).strip()
            if not summary:
                raise ValueError("publish_gbp_update requires a non-empty 'summary' param")
            post = self.gbp_provider.publish_post(
                action.org_id,
                GbpPostCreate(
                    summary=summary,
                    topic=str(params.get("topic", "update")),
                    cta_url=typing.cast("str | None", params.get("cta_url")),
                ),
            )
            return {"post": post.model_dump(mode="json")}
        if action.type == ActionType.SYNC_DIRECTORY_LISTING:
            only_raw = params.get("directory")
            only = Directory(str(only_raw)) if only_raw else None
            report = self.citation_engine.sync(action.org_id, only=only)
            return {"sync": report.model_dump(mode="json")}
        raise ValueError(f"Unsupported action type: {action.type}")


class ActionQueueService:
    """Thread-safe, org-scoped action queue with an approval-gated run loop."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._queues: dict[str, dict[str, QueuedAction]] = {}
        self._counter = 0

    def enqueue(
        self,
        org_id: str,
        type: ActionType,
        params: dict[str, object] | None = None,
        *,
        approval_required: bool = False,
        max_attempts: int = 3,
    ) -> QueuedAction:
        """Add an action; approval mode parks it as ``awaiting_approval``."""
        now = datetime.now(timezone.utc)
        with self._lock:
            self._counter += 1
            action = QueuedAction(
                id=f"act_{self._counter:06d}",
                org_id=org_id,
                type=type,
                params=dict(params or {}),
                status=(
                    ExecutionStatus.AWAITING_APPROVAL
                    if approval_required
                    else ExecutionStatus.PENDING
                ),
                approval_required=approval_required,
                max_attempts=max_attempts,
                created_at=now,
                updated_at=now,
            )
            self._queues.setdefault(org_id, {})[action.id] = action
            return action

    def list(self, org_id: str) -> list[QueuedAction]:
        with self._lock:
            return list(self._queues.get(org_id, {}).values())

    def get(self, org_id: str, action_id: str) -> QueuedAction | None:
        with self._lock:
            return self._queues.get(org_id, {}).get(action_id)

    def approve(self, org_id: str, action_id: str) -> QueuedAction | None:
        """Move an ``awaiting_approval`` action to ``pending``.

        Returns None when the action does not exist for this org; raises
        :class:`ValueError` when it exists but is not awaiting approval.
        """
        with self._lock:
            action = self._queues.get(org_id, {}).get(action_id)
            if action is None:
                return None
            if action.status != ExecutionStatus.AWAITING_APPROVAL:
                raise ValueError(
                    f"Action '{action_id}' is '{action.status.value}', not awaiting approval."
                )
            action.status = ExecutionStatus.PENDING
            action.updated_at = datetime.now(timezone.utc)
            return action

    def run(self, org_id: str, executor: ActionExecutor | None = None) -> QueueRunReport:
        """Execute every pending action for the org (retrying up to max_attempts).

        Actions awaiting approval are skipped and counted; completed/failed
        actions are left untouched. Never raises for provider failures — they
        are captured in the action's structured logs and ``last_error``.
        """
        executor = executor or ActionExecutor()
        with self._lock:
            actions = list(self._queues.get(org_id, {}).values())

        executed = completed = failed = skipped = 0
        for action in actions:
            if action.status == ExecutionStatus.AWAITING_APPROVAL:
                skipped += 1
                continue
            if action.status != ExecutionStatus.PENDING:
                continue
            executed += 1
            action.status = ExecutionStatus.RUNNING
            action.logs.append(
                ExecutionLogEntry(attempt=0, level="info", message=f"started {action.type.value}")
            )
            for attempt in range(1, action.max_attempts + 1):
                action.attempts = attempt
                try:
                    result = executor.execute(action)
                    action.result = result
                    action.last_error = None
                    action.status = ExecutionStatus.COMPLETED
                    action.logs.append(
                        ExecutionLogEntry(
                            attempt=attempt, level="info", message=f"attempt {attempt}: completed"
                        )
                    )
                    break
                except Exception as exc:  # noqa: BLE001 - provider failures are retryable
                    action.last_error = str(exc)
                    action.status = ExecutionStatus.FAILED
                    action.logs.append(
                        ExecutionLogEntry(
                            attempt=attempt, level="error", message=f"attempt {attempt}: {exc}"
                        )
                    )
            action.updated_at = datetime.now(timezone.utc)
            if action.status == ExecutionStatus.COMPLETED:
                completed += 1
            else:
                failed += 1

        return QueueRunReport(
            org_id=org_id,
            executed=executed,
            completed=completed,
            failed=failed,
            skipped_awaiting_approval=skipped,
            actions=actions,
        )


_QUEUE: ActionQueueService | None = None
_GENERATOR: MockContentGenerator | None = None
_CMS: MockCmsAdapter | None = None
_SINGLETON_LOCK = threading.Lock()


def get_queue_service() -> ActionQueueService:
    """Return the process-wide action-queue singleton."""
    global _QUEUE
    if _QUEUE is None:
        with _SINGLETON_LOCK:
            if _QUEUE is None:
                _QUEUE = ActionQueueService()
    return _QUEUE


def get_content_generator() -> ContentGenerator:
    """Return the process-wide mock content generator singleton."""
    global _GENERATOR
    if _GENERATOR is None:
        with _SINGLETON_LOCK:
            if _GENERATOR is None:
                _GENERATOR = MockContentGenerator()
    return _GENERATOR


def get_cms_adapter() -> CmsAdapter:
    """Return the process-wide mock CMS adapter singleton."""
    global _CMS
    if _CMS is None:
        with _SINGLETON_LOCK:
            if _CMS is None:
                _CMS = MockCmsAdapter()
    return _CMS


def reset_execution_state() -> None:
    """Drop all execution singletons (test isolation)."""
    global _QUEUE, _GENERATOR, _CMS
    with _SINGLETON_LOCK:
        _QUEUE = None
        _GENERATOR = None
        _CMS = None
