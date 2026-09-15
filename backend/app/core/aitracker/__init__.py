"""v2 AI Answer-Engine Visibility Tracker (PRODUCT_SPEC §8).

Scheduled, managed, tier-gated prompt-set tracking built on the GEO module's
:class:`~app.core.geo.providers.AnswerEngineProvider` (mock by default):

* ``configs``   — org-scoped CRUD of named prompt sets, with per-plan limits.
* ``policy``    — per-plan engine / cadence / quota entitlement checks.
* ``engine``    — ``run_tracker(org, config, now)``: executes the prompt matrix
  across engines, parses mentions / positions / citations / sentiment, and
  rolls results into Visibility Score, Share-of-Voice, and Mention-Gap.
* ``scheduler`` — ``due_runs(now)``: pure helper listing configs due for
  refresh. The cron/queue hookup is intentionally pluggable and out of scope:
  any scheduler (Celery beat, APScheduler, a k8s CronJob polling
  ``GET /ai-tracker/due`` and POSTing ``/configs/{id}/run``) can drive it.
* ``store``     — org-scoped in-memory repository with a reset helper.
"""
