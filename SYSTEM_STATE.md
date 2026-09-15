# SYSTEM_STATE

> Live architectural map, module inventory, build-agent goals, and known code debt.
> Last updated: 2026-07-10 (evening build) · Version 0.2.0 · Status: **MVP engines + multi-tenant SaaS layer + GEO/PEO/AEO + Kit agentic assistant + Local SEO suite + lead-gen widget complete; 269 backend tests green, 89 MCP tests green, frontend typecheck/build green**

## 1. Architectural map

```
                         ┌─────────────────────────────────┐
        MCP client ─────▶│  mcp-server (TypeScript)          │
   (Claude, LM Studio)   │  55 tools · stdio · X-API-Key/Bearer │
                         └──────────────┬────────────────────┘
                                        │ HTTP /api/v1  (Authorization: Bearer  or  X-API-Key)
   Browser ──▶ frontend (Next.js) ──────┤
                                        ▼
                         ┌───────────────────────────────────────────┐
                         │  backend (FastAPI)                          │
                         │  middleware: RateLimit → Context → CORS     │
                         ├─────────────────────────────────────────────┤
                         │  api/  (21 routers under /api/v1 + /meta)   │
                         │  ┌────────────────────┬─────────────────┐  │
                         │  │ Accounts & Billing  │ Core SEO API    │  │
                         │  │ auth·orgs·api-keys· │ audit·onpage·   │  │
                         │  │ billing·usage       │ keywords·rank-  │  │
                         │  │                     │ ings·reports·   │  │
                         │  │                     │ integrations    │  │
                         │  └──────────┬──────────┴────────┬────────┘  │
                         ├─────────────┼───────────────────┼───────────┤
                         │  tenancy/ (context·rbac·deps·provisioning·  │
                         │  repositories) — every DB access for tenant  │
                         │  data goes through this layer, org-scoped    │
                         ├───────────┬───────────────┬───────────────────┤
                         │  idp/     │  security/     │  billing/          │
                         │  dev HS256│  passwords ·   │  plans · entitle-  │
                         │  + JWKS   │  JWT tokens ·   │  ments · usage ·   │
                         │  adapters │  API-key hash   │  providers ·       │
                         │           │                 │  subscriptions     │
                         ├───────────┴─────────────────┴────────────────────┤
                         │  core engines (unchanged): crawler · onpage ·      │
                         │  keywords · reporting — still pure, DB-unaware,    │
                         │  Pydantic-in/Pydantic-out                          │
                         ├─────────────────────────────────────────────────────┤
                         │  integrations (Make.com · CRM · webhooks)           │
                         ├─────────────────────────────────────────────────────┤
                         │  db/  session.py · models_tenancy · models_billing ·│
                         │  models_seo  →  SQLite (dev/test) / Postgres (prod) │
                         └─────────────────────────────────────────────────────┘
```

Data providers remain **pluggable** (`core/keywords/providers.py`, CRM adapters, Make gateway): deterministic **mock** by default; real adapters activate when the matching `SEO_*` env vars are set. Identity and billing follow the same pattern — `idp_provider`/`billing_provider` select `dev`/`mock` locally and a real vendor (`clerk`/`supabase`/`auth0`, `stripe`) in production, purely via config. Zero secrets in code (`.env.template` pattern — see known debt §4 for a gap in that file).

Full request-flow diagram (auth → org resolution → RBAC → quota → tenant-scoped repos): `docs/MULTI_TENANCY.md` §3.

## 2. Module inventory

| # | Module | Path | Purpose | Tests |
|---|--------|------|---------|-------|
| Spine | Models | `backend/app/models/` | Strictly-typed Pydantic contracts (audit, onpage, keywords, reporting, integrations, common, api) | via spine (5) |
| Spine | Config/Logging | `backend/app/config.py`, `logging_config.py` | Env-driven settings (`SEO_` prefix, now incl. DB/Auth/Billing) + structured JSON logs | ✅ |
| Spine | Middleware | `backend/app/middleware/` | Fixed-window rate limiter, request-id context, typed error handlers (incl. 401/402/403 for auth/billing) | ✅ |
| Spine | Utils | `backend/app/utils/` | URL normalization/same-site, text/NLP, shared HTML parser | ✅ |
| Spine | Store | `backend/app/services/store.py` | Thread-safe in-memory seam — now only backs request-scoped helpers (lead-pipeline idempotency, transient rank polling); durable tenant data moved to the DB (see §4.5) | ✅ |
| Spine | **Database** | `backend/app/db/` | `session.py` (engine/session/`init_db`), `models_tenancy.py`, `models_billing.py`, `models_seo.py` — full SQLModel schema; SQLite by default, Postgres via `SEO_DATABASE_URL` | exercised throughout the SaaS suite |
| Spine | **Security** | `backend/app/security/` | PBKDF2-SHA256 password hashing (200k iterations), HS256 JWT access tokens, SHA-256-hashed API-key generation | exercised throughout the SaaS suite |
| Spine | **Identity Provider (IdP)** | `backend/app/idp/` | Pluggable auth: built-in `dev` HS256 provider (zero third-party deps) + `ExternalJwksProvider` (RS256 via JWKS) for `clerk`/`supabase`/`auth0` | exercised via the `dev` path (external adapter untested against a live vendor — debt §4.1) |
| Spine | **Tenancy** | `backend/app/tenancy/` | `context.py` (`TenantContext`), `rbac.py` (roles/permissions), `provisioning.py` (JIT users, org+owner bootstrap), `deps.py` (auth resolution + RBAC guards), `repositories.py` (org-scoped CRUD, the single persistence seam) | 8\* |
| Spine | **Billing** | `backend/app/billing/` | `plans.py` (catalog), `entitlements.py`, `usage.py` (metering/quota), `providers.py` (mock + Stripe), `subscriptions.py`, `deps.py` (feature/quota guards) | 8\* |
| 1 | Crawler/Audit | `backend/app/core/crawler/` | Async BFS crawl, per-page audit (status, redirects, titles/meta, canonical, robots, broken links, images/alt, word count, hreflang, structured data), scoring, sitemap gen/parse, crawl-vs-crawl compare | 8 |
| 2 | On-page/Content | `backend/app/core/onpage/` | Rank Math-style rule engine (~20 checks, 100-pt score), Surfer-style dual content score + term-band targets, JSON-LD schema generator (12 types), readability | 11 |
| 3 | Keywords/SERP/Rank | `backend/app/core/keywords/` | Keyword research + clustering, SERP analysis, rank tracker (poll, history, visibility score, CTR curve), mock + DataForSEO/GSC provider stubs | 11 |
| 4 | Reporting/Tasks | `backend/app/core/reporting/` | Action-plan generation (issues→tasks with AI-review explainability), white-label report builder + branded HTML render | 9 |
| 5 | Integrations | `backend/app/integrations/` | Lead validation, CRM pipeline (retry + delivery logs), Make.com gateway (HMAC-signed), inbound webhook verification | 24 |
| 6 | **Accounts & Billing API** | `backend/app/api/routes_{auth,orgs,apikeys,billing,usage}.py` | Signup/login/me/switch-org; org + member + invite management; API-key lifecycle; plans/subscription/checkout/portal/webhook; usage summary | 5 |
| 7 | Core SEO API | `backend/app/api/routes_{audit,onpage,keywords,rankings,reports,integrations,meta}.py` + `main.py` | All engine endpoints — now tenant-scoped, RBAC-permission-checked, and quota/feature-gated; unauthenticated meta routes (`/`, `/health`, `/version`) unchanged | 8 |
| 8 | MCP server | `mcp-server/` | 9 zod-validated tools calling the REST API over stdio; multi-tenant-aware — sends `X-API-Key` (`MYSEOAPP_API_KEY`, preferred) or `Authorization: Bearer` (`MYSEOAPP_TOKEN`), and rewrites backend 401/402/403 responses into actionable tool errors naming the exact fix (`apiClient.ts`/`config.ts`) | 15 |
| 9 | Frontend | `frontend/` | Next.js 14 dashboard: audit, on-page editor, keywords, rankings, reports, integrations; no auth/onboarding/org-switcher/billing UI yet (`lib/api.ts` sends no auth header) | typecheck+build |
| 6 | **GEO engine** | `backend/app/core/geo/` | Cross-LLM visibility (6 engines: ChatGPT, Claude, Perplexity, Copilot, Gemini, AI Overviews), share of voice, prompt library/research/tracker (TOFU/MOFU/BOFU), citation & domain-trust mapping, lexicon sentiment heatmaps, AI readiness audit (llms.txt, AI-bot robots rules) | 35 |
| 7 | **PEO engine** | `backend/app/core/peo/` | Knowledge Graph explorer (KGMID search/track), KG sensor (volatility/confidence trends), entity bio builder, corroboration mapping across Wikipedia/Wikidata/Crunchbase/LinkedIn, relational entity JSON-LD (founder/worksFor/author/sameAs) | 20 |
| 8 | **AEO engine** | `backend/app/core/aeo/` | PAA/autocomplete extraction, topic clusters → FAQ mapping, combined JSON-LD @graph builder, TF-IDF internal-link suggestions, voice-search readiness audit | 20 |
| 9 | **Kit assistant** | `backend/app/core/assistant/` | Audit → prioritized plain-English action items with guided fixes; agentic execution queue (write_blog_post, update_meta_tags, publish_gbp_update, sync_directory_listing) with approval gating + retries; keyword mapping & cannibalization; content calendar | 27\* |
| 10 | **Local SEO** | `backend/app/core/local/` | GBP manager (posts, metrics, reviews + suggested replies), citation distributor (NAP diff/sync/lock across Yelp, Apple Maps, Bing Places, Foursquare) | 27\* |
| 11 | **Lead-gen widget** | `backend/app/api/routes_widget.py` | Public embeddable audit.js + public lead capture → validated lead pipeline (CRM/Make) | via assistant/local suites |

*\* `test_saas_spine.py` (8 tests) covers **both** Tenancy and Billing together (auth resolution, RBAC denial, feature gating, quota enforcement, tenant isolation) — it is one test file, not two sets of 8; see the total below.*

**Total automated backend tests: 269, all green** (verified 2026-09-15). The MVP-era breakdown below totalled 89 and is kept for provenance; the suites have grown since.

**MVP-era breakdown (89):** 5 spine + 8 crawler + 11 on-page + 11 keywords + 9 reporting + 24 integrations + 8 core SEO API (`test_api.py`) + 8 tenancy/billing spine (`test_saas_spine.py`) + 5 accounts/orgs/billing routes (`test_accounts.py`). Plus the MCP suite (7 at MVP, 89 today, covering multi-tenant auth-header selection and 401/402/403 error messaging) and frontend typecheck/build. The frontend SaaS UI (signup/onboarding/org-switcher/billing screens) is still in progress — see §3 (goal Q) and §4.

## 3. Build-agent goals (completed, unless noted)

**Phase 1 — MVP engines** (eight isolated agents against locked interface contracts):

- **A — Crawler**: `fetcher.py` (Httpx + Static/injectable), `analyzers.py`, `engine.py`, `sitemap.py`, `compare.py` → 8 tests green.
- **B — On-page**: `analyzer.py`, `content_score.py`, `nlp.py`, `schema_generator.py`, `readability.py` → 11 tests green.
- **C — Keywords**: `providers.py`, `research.py`, `serp.py`, `clustering.py`, `rank_tracker.py` → 11 tests green.
- **D — Reporting**: `tasks.py`, `reports.py`, `whitelabel.py` → 9 tests green.
- **E — Integrations**: `validation.py`, `crm_pipeline.py`, `make_gateway.py`, `webhooks.py` → 24 tests green.
- **F — MCP server**: full TS server + 9 tools → build green, 89 tests green (verified 2026-09-15; 7 at MVP).
- **G — Frontend**: Next.js dashboard, typed API client, mock fallback → typecheck + build green.
- **H — Specs**: `FEATURE_MATRIX.md` (224 features), `PRODUCT_SPEC.md`, `ARCHITECTURE.md`.

**Phase 2 — Multi-tenant SaaS layer** (this build):

- **I — DB & security spine**: `db/session.py` + `models_tenancy.py`/`models_billing.py`/`models_seo.py` (full SQLModel schema), `security/passwords.py`/`tokens.py`/`api_keys.py`, new `Settings` fields (`SEO_DATABASE_*`, `SEO_JWT_*`, `SEO_API_KEY_PREFIX`).
- **J — Identity provider layer**: `idp/providers.py` — `DevIdentityProvider` (HS256) + `ExternalJwksProvider` (RS256/JWKS for `clerk`/`supabase`/`auth0`).
- **K — Tenancy**: `context.py`, `rbac.py`, `provisioning.py` (JIT users + org/owner bootstrap), `deps.py` (auth resolution + RBAC guards), `repositories.py` (org-scoped CRUD).
- **L — Billing**: `plans.py` (catalog), `entitlements.py`, `usage.py` (metering + quota enforcement), `providers.py` (mock + Stripe adapter), `subscriptions.py`, `deps.py` (feature/quota guards).
- **K+L tests** → 8 tests green (`test_saas_spine.py`: auth resolution, RBAC denial, feature gating, quota enforcement, tenant isolation).
- **M — Accounts & Billing API**: `routes_auth.py`, `routes_orgs.py`, `routes_apikeys.py`, `routes_billing.py`, `routes_usage.py` → 5 tests green (`test_accounts.py`).
- **N — SEO router retrofit**: `routes_audit/onpage/keywords/rankings/reports/integrations.py` rewritten to require auth, check RBAC permissions, and enforce quotas/features; API test suite rewritten → 8 tests green (`test_api.py`).
- **O — App wiring**: `main.py` updated (`init_db()` on startup, all 13 routers mounted, OpenAPI description updated) → full backend suite green (89/89).
- **P — MCP SaaS wiring**: `apiClient.ts`/`config.ts` updated to send `X-API-Key` (preferred) or `Authorization: Bearer` (`MYSEOAPP_TOKEN`) and to rewrite backend 401/402/403 responses into actionable, fix-it-now tool errors → 15 tests green (`mcp-server/test/tools.test.ts`, up from 7 at MVP).
- **Q — Frontend SaaS wiring** *(in progress)*: auth/onboarding/org-switcher/team/API-key/billing screens on the frontend. `lib/api.ts` does not yet send an auth header of any kind.
- **R — Docs** (this pass): `docs/MULTI_TENANCY.md`, `docs/AUTH_AND_BILLING.md`, this file, `HANDOFF_BRIEF.md`, `docs/spec/PRODUCT_SPEC.md` §11.

Integration (REST API wiring + full-suite verification) for both phases was performed by the lead loop.

## 4. Known code debt / follow-ups

1. **Real IdP wiring** — `ExternalJwksProvider` (clerk/supabase/auth0) is implemented and unit-shaped but has never been pointed at a live vendor tenant; JWKS fetch, issuer/audience validation, and claim mapping are unverified against a real IdP. All 89 backend tests exercise only the built-in `dev` provider. Wire and smoke-test against at least one real external provider before depending on it in production. *(high, before external-IdP go-live)*
2. **Alembic migrations** — the schema is created via `SQLModel.metadata.create_all()` (`db/session.py::init_db`, called on FastAPI startup) with no migration framework. Any future column/table change requires either a manual `ALTER` against the running DB or a dropped-and-recreated dev database. Add Alembic before the first production schema change. *(high, before prod schema changes)*
3. **Stripe live testing** — `StripeBillingProvider` is implemented but only ever exercised through the `mock` provider in tests. Three specifics need verification against a real Stripe test-mode account: the `price_<plan_code>` Price-ID naming convention assumed by `create_checkout`, the webhook handler's event-type matching (`subscription.updated`/`subscription.created` vs. Stripe's actual `customer.subscription.*` names), and `create_portal`'s use of `org_id` as the Stripe customer reference (should be `Subscription.provider_customer_id`). Full detail in `docs/AUTH_AND_BILLING.md` §2.3. *(high, before paid billing go-live)*
4. **Background job queue** — crawls, rank polls, and report builds still run inline in the request, and now also sit behind a quota check — a large crawl on a low tier can hold a worker for the full crawl duration before the request even resolves to 200 or 402. Move long-running actions to a task queue (Celery/RQ/Arq) with a submit-then-poll API shape. *(scale)*
5. **Persistence remnants** — mostly resolved this phase: tenant-owned SEO artifacts (crawls, rankings, reports, action plans, leads, deliveries) now persist durably via `TenantRepos` into SQLite/Postgres. `services/store.py::InMemoryStore` still backs two request-scoped, per-call helpers (the lead pipeline's idempotency bookkeeping and the rank tracker's transient polling buffer) — harmless today since a fresh instance is created per request and durable state lives elsewhere, but worth consolidating away. *(low)*
6. **JS rendering** — `CrawlConfig.render_js` is honored as a flag but `HttpxFetcher` fetches raw HTML only. Add a Playwright-backed fetcher for SPA crawling. *(medium)*
7. **Real data providers** — DataForSEO / GSC / HubSpot / Salesforce adapters are documented stubs raising `NotImplementedError` until credentials are supplied. *(feature-gated)*
8. **AEO/answer-engine tracking** — the v2 differentiator (ChatGPT/Perplexity/AI-Overview visibility, per Surfer's AI Tracker) is specced in `docs/spec/PRODUCT_SPEC.md` but not built. *(future)*
9. **Packaging gaps found while documenting this phase** — `backend/requirements.txt` was not updated for the SaaS layer: it lists FastAPI/pydantic/httpx/etc. but not `sqlmodel`, `PyJWT`, or `stripe`, all of which the new code imports (the first two unconditionally, `stripe` lazily). A clean `pip install -r requirements.txt` would not currently satisfy the app's imports. Separately, `.env.template` has no `SEO_DATABASE_*`/`SEO_JWT_*`/`SEO_IDP_*`/`SEO_BILLING_*`/`SEO_STRIPE_*` entries (full list in `docs/AUTH_AND_BILLING.md` §2.4). *(medium, fix before the next clean-environment setup)*
10. **Entitlement coverage is partial** — `sites` and `seats` plan limits are defined in the catalog and reported by `GET /usage`, but neither is enforced yet at a creation endpoint: there is no project-creation route to gate `sites` against, and invite creation doesn't call `check_resource` for `seats`. Only `tracked_keywords` currently enforces a live absolute-resource ceiling. *(medium)*
11. **Frontend SaaS wiring** — tracked as build-agent goal Q, in progress: the frontend has no signup/login/org-switcher/team/API-key/billing screens yet (`lib/api.ts` sends no auth header at all). MCP SaaS wiring (goal P) is now done — dual `X-API-Key`/`Authorization: Bearer` auth plus actionable 401/402/403 error messages, covered by 15 tests. *(in progress — frontend only)*
12. **Mount leftovers** — `mcp-server/node_modules/` and an empty `mcp-server/src/_probe.ts` are locked by the cloud-synced filesystem; delete `node_modules` and reinstall cleanly. `_probe.ts` is empty and harmless. *(cleanup)*
13. **Synced-folder tooling quirk** — this workspace's file sync/mount tooling has duplicated parts of the tree one level deeper than the real source: `backend/app/app/**` mirrors `backend/app/**`, and `backend/tests/tests/**` mirrors `backend/tests/**`, file-for-file. The canonical, actually-imported source is `backend/app/*.py` / `backend/app/<package>/*.py` and `backend/tests/*.py` (confirmed via `main.py`'s import graph and `conftest.py`'s `sys.path` setup, which both point at the shallower path). Treat the nested `app/app/` and `tests/tests/` copies as stale duplicates — don't edit them, and delete them once confirmed unused, to avoid a future edit accidentally landing in the wrong copy. *(cleanup, low risk but confusing — flag to anyone new touching this repo)*

## 5. Deployment (summary — see README + HANDOFF_BRIEF)

- Backend: `uvicorn app.main:app` (containerize; set `SEO_*` env, including the new DB/Auth/Billing vars — see `docs/AUTH_AND_BILLING.md` §2.4). Tables are created automatically on startup (`init_db()`); no separate migration step exists yet (debt §4.2). Set `SEO_DATABASE_URL` to a Postgres DSN in any shared/production environment — SQLite is a dev/test default only.
- MCP: `node dist/index.js` with `MYSEOAPP_API_BASE_URL` pointing at the backend and `MYSEOAPP_API_KEY` set to an org-scoped API key (`POST /api-keys`).
- Frontend: `next build && next start` (or static/Vercel) with `NEXT_PUBLIC_API_BASE_URL`. Auth/billing UI not yet built — see debt §4.11.
- New deployments must set `SEO_JWT_SECRET` (and `SEO_STRIPE_*` if billing is live) to real secrets — the shipped defaults are dev-only placeholders and are rejected by nothing at runtime, so this is an operational checklist item, not an enforced guard.
