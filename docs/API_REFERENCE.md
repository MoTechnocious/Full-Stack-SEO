# API Reference — MySEOapp

Base URL: `http://localhost:8000` · API prefix: `/api/v1` · Interactive docs: `/docs` (Swagger), `/redoc`.

**Conventions**
- All bodies are JSON. Responses are the Pydantic models in `backend/app/models/`.
- Errors return `{ "error": <code>, "detail": <msg>, "request_id": <id>, "errors": [...] }`.
- Every response carries `X-Request-ID`, `X-Response-Time-ms`, and `X-RateLimit-*` headers.
- Auth: send `X-API-Key` (currently used for rate-limit bucketing; RBAC is a planned layer).

---

## Meta

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service info / links |
| GET | `/health` | Liveness → `{status, environment}` |
| GET | `/version` | `{name, version, api_version}` |

## Audit (technical crawl)

### `POST /api/v1/audit/page` — audit one page
Body: `{ "url": "https://ex.com/p" }` **or** `{ "html": "<html>…</html>", "url": "https://ex.com/p" }`
→ `PageAuditResult` (status, title/meta lengths, canonical, indexability, links, images_missing_alt, structured_data_types, `issues[]`, `score`).

### `POST /api/v1/audit/crawl` — run a crawl
Body: `CrawlConfig` → `{ "start_url": "...", "max_pages": 100, "max_depth": 5, "respect_robots": true, "follow_external": false, "include_patterns": [], "exclude_patterns": [] }`
→ `CrawlResult` (`crawl_id`, `pages[]`, `summary`, `top_issues[]`). Persisted for retrieval.

### `GET /api/v1/audit/crawl/{crawl_id}` — fetch a stored crawl → `CrawlResult` (404 if unknown).

### `POST /api/v1/audit/sitemap` — generate XML sitemap
Body: `{ "urls": ["https://a/","https://a/b"] }` → `application/xml` sitemap.

## On-page & content

### `POST /api/v1/onpage/analyze` — Rank Math-style rule engine
Body: `OnPageRequest` → `{ "target_keyword": "running shoes", "html": "...", "url": "..." }` (or `title`/`meta_description`/`content`)
→ `OnPageResult` (`score` 0-100, `grade`, `checks[]` across 4 categories, `category_scores`, `issues[]`).

### `POST /api/v1/onpage/content-score` — Surfer-style content score
Body: `{ "target_keyword": "...", "content": "...", "secondary_keywords": [], "competitor_word_counts": [], "competitor_texts": [] }`
→ `ContentScore` (`content_score`, `seo_score`, `ai_search_score`, word-count band, `term_targets[]` with under/optimal/over, `missing_terms`, `overused_terms`, `suggestions`).

### `POST /api/v1/onpage/schema` — JSON-LD generator
Body: `{ "schema_type": "Article|Product|FAQPage|HowTo|LocalBusiness|…", "fields": { … } }`
→ `SchemaResult` (`json_ld`, `script_tag`, `warnings[]`).

## Keywords & SERP

### `POST /api/v1/keywords/research`
Body: `{ "seed": "running shoes", "country": "us", "limit": 50, "include_questions": true }`
→ `KeywordResearchResult` (`keywords[]` with volume/difficulty/cpc/intent/serp_features, `clusters[]`).

### `POST /api/v1/keywords/serp`
Body: `{ "keyword": "running shoes", "country": "us", "device": "desktop" }`
→ `SerpAnalysis` (top-10 `results[]`, `features[]`, `avg_word_count`, `avg_backlinks`, `difficulty`).

## Rank tracking

### `POST /api/v1/rankings/track` — add keywords, poll, summarize
Body: `{ "domain": "site.com", "country": "us", "device": "desktop", "keywords": ["a","b"], "search_volumes": {"a": 1200} }`
→ `RankTrackingSummary` (`avg_position`, `improved/declined/unchanged`, `top3`, `top10`, `visibility_score`, `keywords[]` with history/delta).

### `GET /api/v1/rankings/{domain}?country=us` → stored `RankTrackingSummary` (404 if none).

## Reports & tasks

### `POST /api/v1/reports/action-plan`
Body: `{ "site": "site.com", "crawl_id": "…", "domain": "site.com", "country": "us" }` (crawl_id/domain optional)
→ `ActionPlan` (`tasks[]` with priority, impact, effort, `ai_review`, `by_priority`, `by_status`).

### `POST /api/v1/reports/build?format=json|html`
Body: `{ "site": "site.com", "period_start": "2026-06-01", "period_end": "2026-06-30", "branding": {"agency_name": "Acme SEO", "primary_color": "#111"}, "crawl_id": "…", "domain": "site.com" }`
→ `Report` (JSON) or a self-contained branded HTML document (`format=html`).

## Integrations

### `POST /api/v1/integrations/leads` — validate + push a lead
Body: `LeadRecord` → `{ "name": "Jane", "email": "jane@ex.com", "website": "ex.com", "source": "mini_audit" }`
→ `DeliveryLog` (`status`: validated→sent→delivered / rejected / failed, `attempts`, `response_ref`).

### `GET /api/v1/integrations/deliveries` → `DeliveryLog[]`.

### `POST /api/v1/integrations/webhooks/make` — inbound webhook
Send raw JSON body + `X-Signature: <hex HMAC-SHA256>` (secret = `SEO_WEBHOOK_SIGNING_SECRET`).
→ `{ received, verified, type, id }`.

---

## MCP tool ↔ endpoint map

| MCP tool | REST endpoint (all under `/api/v1`) |
|----------|---------------|
| `run_audit` | `POST /audit/crawl` |
| `audit_page` | `POST /audit/page` |
| `analyze_onpage` | `POST /onpage/analyze` |
| `content_score` | `POST /onpage/content-score` |
| `generate_schema` | `POST /onpage/schema` |
| `keyword_research` | `POST /keywords/research` |
| `analyze_serp` | `POST /keywords/serp` |
| `track_rankings` | `POST /rankings/track` |
| `generate_report` | `POST /reports/build` |

---

## GEO — Generative Engine Optimization (`/api/v1/geo`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/geo/visibility/scan` | Scan answer engines (ChatGPT, Claude, Perplexity, Copilot, Gemini, AI Overviews) for brand visibility → per-engine + overall mention frequency, share of voice, avg list position, trend deltas. Body: `{brand, competitors?, prompts?, engines?}` |
| GET | `/geo/prompts` | List the org's tracked prompt library |
| POST | `/geo/prompts` | Track a prompt `{text, funnel_stage?, intent?}` (TOFU/MOFU/BOFU) |
| POST | `/geo/prompts/research` | Expand `{topic}` into high-intent conversational queries |
| GET | `/geo/prompts/tracker?brand=&competitors=&engines=` | Master tracker — brand rank per prompt per engine with history |
| POST | `/geo/citations/scan` | Which URLs/domains engines cite for your prompts |
| GET | `/geo/citations/domains?own_domain=` | Aggregated domain-trust report (Reddit/Wikipedia/G2/Quora/news/own) |
| POST | `/geo/sentiment/scan` | Engine × prompt sentiment heatmap (lexicon NLP, −1..1) |
| POST | `/geo/readiness/audit` | AI readiness: llms.txt, AI-bot robots rules (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot), structure → graded score + fixes |

## PEO — Personal Entity Optimization (`/api/v1/peo`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/peo/entities/search` | Query the Knowledge Graph for an entity → KGMID, types, result score |
| POST | `/peo/entities/track` | Track an entity's KGMID org-scoped |
| GET | `/peo/entities/sensor?kg_mid=&points=` | Confidence time-series + volatility + trend (rising/stable/volatile/declining) |
| POST | `/peo/bio/build` | NLP-optimized authoritative bio (short/medium/long variants, triple-density score) |
| POST | `/peo/corroboration/audit` | Diff entity facts across Wikipedia/Wikidata/Crunchbase/LinkedIn/own site → consistency score + mismatch fixes |
| POST | `/peo/schema/entity` | Relational Person/Organization JSON-LD (founder, worksFor, author, alumniOf, sameAs) |

## AEO — Answer Engine Optimization (`/api/v1/aeo`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/aeo/questions/extract` | People-Also-Ask questions, follow-up chains, autocomplete pathways for a seed query |
| POST | `/aeo/clusters/map` | Group questions into topic clusters → structured FAQ layout with page mapping |
| POST | `/aeo/schema/graph` | Combined JSON-LD `@graph` (FAQPage, QAPage, HowTo, WebPage, BreadcrumbList) |
| POST | `/aeo/linking/suggest` | TF-IDF cosine internal-link suggestions with anchor text |
| POST | `/aeo/voice/audit` | Voice-search readiness: reading ease, sentence length, syllable density, answer conciseness |

## Kit assistant (`/api/v1/assistant`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/assistant/actions/plan` | Audit findings → prioritized plain-English action items with guided step-by-step fixes |
| GET / POST | `/assistant/queue` | List / enqueue agentic actions (`write_blog_post`, `update_meta_tags`, `publish_gbp_update`, `sync_directory_listing`) |
| POST | `/assistant/queue/{action_id}/approve` | Approve an action awaiting approval |
| POST | `/assistant/queue/run` | Run the queue (retries to max attempts, structured logs) → run report |
| POST | `/assistant/keywords/map` | Map keywords to most-relevant pages + cannibalization flags + consolidation actions |
| POST | `/assistant/calendar/build` | Keyword-mapped content calendar with dated article outlines |

## Local SEO (`/api/v1/local`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/local/gbp/posts` | Publish a Google Business Profile update |
| GET | `/local/gbp/metrics?period_days=` | GBP search metrics (views, searches, actions) |
| GET | `/local/gbp/reviews` | Reviews + AI-suggested replies |
| POST | `/local/gbp/reviews/{review_id}/reply` | Reply to a review (empty body → use suggested reply) |
| GET / PUT | `/local/citations/nap` | Get / update the canonical NAP record (with `locked` drift protection) |
| POST | `/local/citations/sync?directory=` | Push NAP to all (or one) of Yelp, Apple Maps, Bing Places, Foursquare |
| GET | `/local/citations/status` | Per-directory listing + drift status vs canonical NAP |

## Lead-gen widget (`/api/v1/widget`) — public, no auth

| Method | Path | Description |
|--------|------|-------------|
| GET | `/widget/audit.js?org=<slug>` | Self-contained embeddable JS: renders a free-audit lead form branded for the org |
| POST | `/widget/leads` | `{url, email, name?}` → validated, mini-audit teaser returned, lead pushed through the CRM/Make pipeline |

## Background jobs (`/api/v1/jobs`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/jobs/crawl` | Submit an async crawl (same guards/quota as `POST /audit/crawl`, checked at submission) → `{job_id, status}` |
| POST | `/jobs/rank-poll` | Submit an async rank poll (same guards as `/rankings/track`) |
| POST | `/jobs/report` | Submit an async report build (same guards as `/reports/build`; white-label feature-gated) |
| GET | `/jobs?status=&type=` | Org-scoped job list |
| GET | `/jobs/{job_id}` | Status, progress (0–100), attempts, `result_ref` (crawl_id / domain / report_id — fetch via the existing GET endpoints) |
| POST | `/jobs/{job_id}/cancel` | Best-effort cancel for queued jobs |

Backend selected by `SEO_JOB_QUEUE_BACKEND`: `thread` (default, in-process pool), `inline` (sync, tests/dev), `celery`/`rq` (adapter stubs — see `app/jobs/queue.py` for activation guidance).

## AI Answer-Engine Visibility Tracker v2 (`/api/v1/ai-tracker`) — plan-gated (`ai_tracker` feature)

| Method | Path | Description |
|--------|------|-------------|
| POST / GET | `/ai-tracker/configs` | Create / list managed prompt-set configs (name, prompts, brand, competitors, engines, cadence) — per-plan config/prompt limits |
| GET / PUT / DELETE | `/ai-tracker/configs/{id}` | Manage a config (engine set re-validated against plan tier) |
| POST | `/ai-tracker/configs/{id}/run?now=` | Run the prompt matrix across engines → `TrackerRunReport` (mentions, citations, position-in-answer, sentiment per answer + rollups) |
| GET | `/ai-tracker/configs/{id}/history` | Run history with run-over-run deltas |
| GET | `/ai-tracker/configs/{id}/visibility` | Latest rollup: **Visibility Score** (0–100 = 0.5·mention rate + 0.3·position score + 0.2·citation share), **Share-of-Voice** per engine + overall |
| GET | `/ai-tracker/configs/{id}/mention-gap` | Prompts where competitors are mentioned but the brand isn't, ranked by opportunity |
| GET | `/ai-tracker/due?now=` | Ops: configs due for refresh per cadence (admin/owner only; hook to cron/queue) |

Tiering (per `PRODUCT_SPEC.md` §7): free/starter — not included · pro — ChatGPT only, weekly · agency/enterprise — all 5 engines (ChatGPT, Perplexity, Gemini, AI Overviews, AI Mode), daily.
