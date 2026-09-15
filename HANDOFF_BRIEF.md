# Technical Handoff Brief — MySEOapp

**Prepared for:** scalingfirm.com engineering & operations
**System version:** 0.2.0 · **Date:** 2026-07-10 · **Status:** Full platform build — core SEO engines, multi-tenant SaaS layer, GEO/PEO/AEO engines, Kit agentic assistant, Local SEO suite, and embeddable lead-gen widget. 269 backend tests green (plus 89 MCP tests, frontend typecheck/lint/build).

---

## 1. What was built and why

MySEOapp is a decoupled, self-hostable SEO platform that consolidates the four
tools scalingfirm.com's team and clients otherwise juggle — Screaming Frog
(technical crawling), Surfer (content optimization), Rank Math (on-page + schema),
and Hike SEO (rank tracking, action plans, agency reporting) — into one API-first
engine with an MCP server and a dashboard.

The design goal was **automation of client SEO delivery**: run audits at scale,
turn findings into prioritized action plans, track rankings, generate branded
client reports, and feed leads into the CRM/marketing stack — all driveable
programmatically (REST), conversationally (MCP), or visually (dashboard).

This phase of work turned that single-tenant engine into a **multi-tenant SaaS
product**: any number of companies (agencies, in-house teams, freelancers) can
now sign up, get an isolated workspace, invite their own team and clients with
different permission levels, and pay for exactly the plan that matches their
usage — all on one shared deployment. Section 4 covers this layer end to end.

## 2. How it automates the core workflows

| Workflow | How MySEOapp automates it | Entry points |
|----------|---------------------------|--------------|
| **Client site audit** | `Crawler` does async BFS crawl → per-page technical audit (status codes, redirect chains, titles/meta, canonicals, robots directives, broken links, alt text, thin content, hreflang, structured data) → weighted score + aggregated `top_issues`. | `POST /api/v1/audit/crawl`, MCP `run_audit` |
| **Content optimization** | `analyze_onpage` runs the Rank Math-style rule engine (100-pt); `score_content` computes a Surfer-style score with competitor-derived term bands and word-count targets. | `POST /api/v1/onpage/analyze`, `/onpage/content-score`, MCP `analyze_onpage` |
| **Structured data** | `generate_schema` emits valid JSON-LD for 12 schema types with missing-field warnings. | `POST /api/v1/onpage/schema`, MCP `generate_schema` |
| **Keyword & SERP research** | Keyword research with clustering + intent; SERP analysis of the top 10 with avg word count / backlinks / difficulty. | `POST /api/v1/keywords/*`, MCP `keyword_research`, `analyze_serp` |
| **Rank tracking** | `RankTracker` polls SERPs per keyword, keeps position history, computes deltas, top-3/top-10 counts, and a volume-weighted visibility score. | `POST /api/v1/rankings/track`, MCP `track_rankings` |
| **Action plans** | `generate_action_plan` converts audit issues + failed on-page checks + page-2 ranking opportunities into prioritized `Task`s, each with an **AI-review** verdict + reasoning for explainability. | `POST /api/v1/reports/action-plan` |
| **White-label reporting** | `build_report` assembles branded sections (health, rankings, keywords, tasks); `render_report_html` produces a self-contained, agency-branded HTML report (logo, colors, agent name), gated to plans with the `white_label` feature. | `POST /api/v1/reports/build?format=html`, MCP `generate_report` |
| **Lead → CRM/Make pipeline** | Public mini-audit / forms post leads → `validate_lead` (integrity checks) → `LeadPipeline` pushes to CRM with retry + delivery-state logging → optional HMAC-signed dispatch to a Make.com scenario. | `POST /api/v1/integrations/leads` |
| **Inbound automation** | HMAC-verified inbound webhook endpoint for Make.com/other systems. | `POST /api/v1/integrations/webhooks/make` |

Every one of these now runs **inside a tenant boundary**: the caller is resolved to an organization and role first (§4), the action is checked against that organization's plan (permission, feature flag, and/or usage quota), and every record it writes or reads carries that organization's `org_id`. None of the engine logic above changed to make this true — only the API layer wrapping it did.

## 3. Architecture posture (per the CTO mandate)

- **Decoupled microservice-ready**: engine (Python) · MCP (TS) · frontend (Next.js) are independently deployable; they communicate only over the versioned `/api/v1` contract.
- **Deterministic execution loops**: every engine is a pure/typed function over Pydantic models; IO (HTTP fetch, SERP, CRM) is behind injectable interfaces, which is why the 89-test backend suite runs offline and green.
- **Zero-trust foundations, now including auth**: no secrets in code (`SEO_` env + `.env.template`), HMAC-signed outbound/inbound webhooks, rate limiting + structured JSON logging + request IDs on every call — and, as of this phase, every `/api/v1` route requires a verified `Authorization: Bearer` token or `X-API-Key`, checked against an app-owned RBAC layer and the caller's plan. Auth/RBAC was the prior handoff's #1 next step (see the old §5 debt list) and is now done — see §4.
- **Pluggable providers everywhere**: mock adapters ship by default; real ones (DataForSEO, GSC, HubSpot, Salesforce, Make.com, and now identity providers and Stripe) activate purely via env config.

## 4. Multi-tenant SaaS: how a company adopts MySEOapp

*(Full detail: `docs/MULTI_TENANCY.md` and `docs/AUTH_AND_BILLING.md`. This section is the narrative walkthrough.)*

### 4.1 Sign up and get an isolated workspace

A new company creates an account with `POST /api/v1/auth/signup` (email + password against the built-in `dev` identity provider, or their first login through a configured external IdP). One call provisions:

- a **User** for the person signing up,
- a brand-new **Organization** — their isolated workspace, identified by `org_id` and a unique slug,
- a **Membership** giving that user the `owner` role in it,
- a **Subscription** on the default plan (Free, 14-day `trialing` status).

They're immediately usable — no manual provisioning step, no waiting on a schema or database to be created. Isolation is enforced at the data layer: every row anyone in this org creates from now on (crawls, reports, leads, API keys, everything) carries their `org_id`, and the tenant-scoped repository layer refuses to return a row belonging to any other org, even if an ID is guessed or reused (`docs/MULTI_TENANCY.md` §4).

### 4.2 Invite team and clients, with different roles

The owner (or anyone with `agency_admin`) invites people via `POST /api/v1/orgs/invites {email, role}`. Four roles are available, each a strict superset of the one below it: `client` (read-only — the natural role for an agency's own client to view results), `editor` (runs audits, writes content scores, manages leads/reports), `agency_admin` (also manages members and API keys), `owner` (also manages billing).

This is where the **agency multi-client model** falls out of the same mechanism used for internal teammates: a single person can hold a `client`-role membership in several different agencies' organizations and an `owner`-role membership in their own — one login, many workspaces, switchable with `POST /auth/switch-org`. An agency managing ten clients isn't ten separate accounts; it's one organization with ten client-role members (or, if a client needs their own private workspace, a separate org they're invited into).

### 4.3 Pick a plan

`GET /api/v1/billing/plans` is public and lists the full catalog (Free/Starter/Pro/Agency/Enterprise — full price/limit/feature matrix in `docs/AUTH_AND_BILLING.md` §2.1). A company starts on Free automatically and upgrades via `POST /api/v1/billing/checkout {plan_code}` whenever they're ready — in the shipped `mock` billing provider this activates instantly (useful for demos/local dev); with `SEO_BILLING_PROVIDER=stripe` configured, it hands back a real Stripe Checkout URL and the plan activates when Stripe's webhook confirms payment.

### 4.4 How quotas replace their per-tool subscriptions

This is the commercial point of the whole layer. Instead of a company paying separately for Screaming Frog (crawls), Surfer (content scoring), a keyword/rank tool, and HikeSEO-style reporting, they pay for **one MySEOapp plan**, and each of those four workflows draws down the same plan's usage counters:

| Instead of paying for... | ...they now consume | Metered as |
|---|---|---|
| Screaming Frog seats | Crawls | `crawls_per_month`, capped `pages_per_crawl` |
| Surfer credits | Content scores | `content_scores_per_month` |
| A keyword/rank-tracking tool | Keyword research + tracked keywords | `keyword_lookups_per_month`, `tracked_keywords` |
| HikeSEO's reporting tier | Branded reports | `reports_per_month`; white-label branding itself is a plan **feature**, not a quota |

Every metered action is checked against the org's plan **before** it runs and recorded **after** it succeeds; hitting a ceiling returns `402 quota_exceeded` (or `402 feature_not_available` for a plan-gated capability like white-label reporting or MCP access) with a message naming exactly what's exhausted and what plan would raise it. `GET /api/v1/usage` gives the dashboard a live used/limit view across every metric, so a company can see exactly how their actual usage maps to a plan decision — the same visibility that justifies paying for one platform instead of four.

## 5. Operating it

1. **Backend**: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000`. OpenAPI at `/docs`. Tests: `python -m pytest -q`. Tables are created automatically on startup (`init_db()`); there's no separate migration step yet (see next steps). **Note:** `requirements.txt` currently omits `sqlmodel` and `PyJWT`, which the app now imports unconditionally — install them alongside the listed packages until the requirements file is updated (`SYSTEM_STATE.md` debt #9).
2. **Database**: defaults to local SQLite (`SEO_DATABASE_URL=sqlite:///./myseoapp.db`) — fine for dev/demo. Point `SEO_DATABASE_URL` at Postgres for anything shared or production-facing.
3. **Auth**: defaults to the built-in `dev` identity provider — no external account needed to run the whole stack locally. Set a real `SEO_JWT_SECRET` outside local dev. To use a real IdP (Clerk/Supabase/Auth0), set `SEO_IDP_PROVIDER` + `SEO_IDP_JWKS_URL` (+ issuer/audience) — see `docs/AUTH_AND_BILLING.md` §1.2 and §2.4 for the full variable list (most of which still need to be added to `.env.template`, per `SYSTEM_STATE.md` debt #9).
4. **Billing**: defaults to the `mock` provider (no external account needed). Set `SEO_BILLING_PROVIDER=stripe` + `SEO_STRIPE_API_KEY`/`SEO_STRIPE_WEBHOOK_SECRET` for real billing — see `docs/AUTH_AND_BILLING.md` §2.3 for setup steps and the specific things to verify before trusting it in production.
5. **MCP**: `cd mcp-server && rm -rf node_modules && npm install && npm run build && node dist/index.js`, with `MYSEOAPP_API_BASE_URL` pointing at the backend and either `MYSEOAPP_API_KEY` (preferred; create one via `POST /api/v1/api-keys` once signed in) or `MYSEOAPP_TOKEN` (a signed-in user's bearer token) set. Missing/invalid credentials, exhausted quota, and insufficient-role responses all come back as clear, actionable MCP tool errors rather than generic failures.
6. **Frontend**: `cd frontend && npm install && npm run dev` (`NEXT_PUBLIC_API_BASE_URL`). The dashboard's SEO views work against the API today; signup/onboarding/org-switcher/billing screens are not built yet (§6).
7. **Config**: copy `.env.template` → `.env`. It documents the crawler/provider/integration surface but not yet the new DB/Auth/Billing variables — fill those in from `docs/AUTH_AND_BILLING.md` §2.4 in the meantime.

## 6. Recommended next steps (priority order)

1. **Finish the frontend SaaS wiring** (in progress) — signup/login/onboarding, org switcher, team/invite management, API-key management, and billing/usage screens on the frontend (`lib/api.ts` sends no auth header yet). MCP SaaS wiring is already done: the server sends `X-API-Key`/`Authorization: Bearer` and surfaces 401/402/403 as actionable errors, covered by 15 tests.
2. **Wire and test a real external IdP** (Clerk/Supabase/or similar) end-to-end at least once — the adapter code exists but has only run against the built-in `dev` provider so far.
3. **Add Alembic migrations** before the first real production schema change — today's `SQLModel.metadata.create_all()` has no upgrade/downgrade story.
4. **Verify Stripe against a real test-mode account** — Price-ID naming, webhook event-type matching, and the customer-portal mapping all need a live check before real money moves through checkout.
5. **Move long-running actions to a background job queue** (Celery/RQ/Arq) — crawls, rank polls, and report builds are still inline per-request, which now also sits behind a quota check on every call.
6. **Close the packaging gaps found while writing these docs** — update `requirements.txt` (missing `sqlmodel`, `PyJWT`, optional `stripe`) and `.env.template` (missing DB/Auth/Billing variables) so a fresh clone actually runs out of the box.
7. **Wire one real SEO data provider end-to-end** (DataForSEO or GSC) to replace mocks, and add the Playwright JS-rendering fetcher for SPA clients — both carried over from the original MVP debt list, still open.
8. **Scope the v2 AEO/answer-engine visibility tracker** — the market's current differentiator, specced in `docs/spec/PRODUCT_SPEC.md` but not built.

## 7. Where to look

- Multi-tenancy model, data model, and the full auth+tenant request-flow diagram → `docs/MULTI_TENANCY.md`
- Authentication, RBAC/permission matrix, API keys, and the full billing/plans/quota reference → `docs/AUTH_AND_BILLING.md`
- Feature parity vs. the 4 tools → `docs/spec/FEATURE_MATRIX.md`
- Full PRD / roadmap, incl. pricing & packaging as a subscription-replacement strategy → `docs/spec/PRODUCT_SPEC.md`
- System design + request flows (pre-SaaS engine architecture) → `docs/ARCHITECTURE.md`
- Endpoint reference → `docs/API_REFERENCE.md`
- Live status, module inventory, and debt → `SYSTEM_STATE.md`

---

## Appendix A — 2026-07-10 evening build: GEO · PEO · AEO · Kit · Local SEO · Widget

This build adds six modules on top of the SaaS spine. All follow the established architecture: pure Pydantic-typed engines, pluggable providers (deterministic mocks by default, live adapters via `SEO_*` env vars — see `.env.template`), org-scoped state, RBAC + plan enforcement at the API layer, and offline test suites.

| Workflow | How it's automated | Entry points |
|----------|--------------------|--------------|
| **AI search visibility (GEO)** | Scans 6 answer engines (ChatGPT, Claude, Perplexity, Copilot, Gemini, AI Overviews) for brand mentions, share of voice vs competitors, and average list position, with trend deltas per scan. | `POST /api/v1/geo/visibility/scan`, MCP `geo_visibility_scan` |
| **Prompt analytics** | Org-scoped prompt library with TOFU/MOFU/BOFU staging; research endpoint expands a topic into high-intent conversational queries; master tracker records rank history per prompt per engine. | `/geo/prompts*`, MCP `geo_prompt_research`, `geo_prompt_tracker` |
| **Citation & source mapping** | Extracts which URLs/domains each engine cites; classifies and trust-weights domains (Reddit, Wikipedia, G2, Quora, news, own domain) into a priority ranking. | `/geo/citations/*`, MCP `geo_citations_scan`, `geo_domain_trust` |
| **AI sentiment heatmaps** | Lexicon NLP scores every engine answer about the brand (−1..1) into an engine × prompt heatmap. | `POST /geo/sentiment/scan`, MCP `geo_sentiment_scan` |
| **AI readiness audit** | Checks llms.txt, robots rules for GPTBot/ClaudeBot/PerplexityBot/Google-Extended/CCBot, structured data, heading structure, answer-friendly formatting → graded score + prioritized fixes. | `POST /geo/readiness/audit`, MCP `geo_ai_readiness_audit` |
| **Entity optimization (PEO)** | Knowledge Graph KGMID search/track, confidence-volatility sensor, NLP-optimized bio builder, cross-source corroboration audit (Wikipedia/Wikidata/Crunchbase/LinkedIn), relational entity JSON-LD (founder / worksFor / author / sameAs). | `/peo/*`, MCP `peo_*` (6 tools) |
| **Answer engine optimization (AEO)** | PAA + autocomplete extraction, topic clusters → FAQ layouts, combined JSON-LD @graph, TF-IDF internal-link suggestions, voice-search readiness scoring. | `/aeo/*`, MCP `aeo_*` (5 tools) |
| **Kit agentic assistant** | Turns audit findings into prioritized plain-English action items with step-by-step guided fixes; agentic queue executes actions (blog drafts, meta-tag updates, GBP posts, directory syncs) with approval gating, retries, and structured logs; keyword→page mapping with cannibalization flags; keyword-mapped content calendar. | `/assistant/*`, MCP `kit_*` (5 tools) |
| **Local SEO** | GBP posts/metrics/reviews with AI-suggested replies; NAP citation distributor diffs, syncs, and locks name/address/phone across Yelp, Apple Maps, Bing Places, Foursquare with per-directory delivery state. | `/local/*`, MCP `local_*` (6 tools) |
| **Lead-gen audit widget** | Public `audit.js` embed renders a free-audit form on any agency site; submissions are validated, run through a mini-audit teaser, and pushed through the existing lead pipeline (CRM + Make.com) org-attributed. | `GET /api/v1/widget/audit.js?org=<slug>`, `POST /api/v1/widget/leads` (both public) |

**Frontend:** six new dashboard pages — `/kit`, `/geo`, `/peo`, `/aeo`, `/local`, `/widget` — grouped in the sidebar under "AI Search" and "Local & Agency", all with graceful demo-data fallback when the API is unreachable.

**MCP:** 29 new tools (38 total) covering every module, tested with a mocked API client (60 tests).

**Verification:** `cd backend && python -m pytest tests` → 218 green · `cd mcp-server && npm run typecheck && npm test` → clean, 60 green · `cd frontend && npx tsc --noEmit && npm run build` → clean.

**Going live:** every provider ships as a deterministic mock. To activate real integrations set the corresponding env vars (`SEO_ANSWER_ENGINE_PROVIDER=live` + engine API keys, `SEO_KG_PROVIDER=google` + `SEO_GOOGLE_KG_API_KEY`, `SEO_GBP_PROVIDER`, `SEO_DIRECTORY_PROVIDER`, `SEO_CONTENT_GENERATOR_PROVIDER`, `SEO_CMS_PROVIDER`) — no code changes required.

---

## Appendix B — 2026-07-10 night build: SaaS debt closure + AI Tracker v2

**Frontend SaaS wiring — audited, confirmed done.** The prior debt note ("lib/api.ts sends no auth header") was stale: a live end-to-end TestClient run (24 checks: signup → login → me → invites → accept → switch-org → API keys → billing checkout → usage → negative cases) confirmed the full flow works. One real issue found and fixed: an open-redirect in login/signup `?redirect=` handling (now sanitized to same-app paths). Two backend gaps flagged for the backlog: no pending-invite list/revoke endpoints, no member role-change/remove endpoints.

**Alembic migrations.** `backend/alembic/` + `alembic.ini`; initial revision `0001_initial_schema` captures all 14 tables; upgrade/downgrade verified programmatically against `SQLModel.metadata` (table/column/type/nullability parity); `tests/test_migrations.py` guards it. Workflow documented in `docs/DEPLOYMENT.md` ("Database migrations"). `init_db()` remains the dev/test path; production applies `alembic upgrade head`.

**Background job queue.** `app/jobs/` — `JobQueue` with `thread` (default) and `inline` backends plus documented `celery`/`rq` adapter stubs, org-scoped registry, retries, structured transition logs. Crawls, rank polls, and report builds submit via `POST /jobs/*` with the SAME RBAC/quota guards as their sync twins (checked at submission); results land in the existing stores so `GET /audit/crawl/{id}` etc. keep working. Sync endpoints untouched. New `/jobs` dashboard page with live polling.

**Packaging.** `requirements.txt` now matches real imports (added `alembic`; confirmed `pyjwt` is the JWT lib in use; commented optional extras: `stripe`, `celery`, `redis`). `.env.template` covers all 60+ Settings fields including DB/Auth/Billing/Jobs. Fresh-install smoke test: pip install → app boots → suite green.

**AI Answer-Engine Visibility Tracker v2** (`app/core/aitracker/`, `/api/v1/ai-tracker`, `/ai-tracker` page, 10 MCP tools). Managed org-scoped prompt sets run a scheduled matrix across ChatGPT, Perplexity, Gemini, AI Overviews, and AI Mode (mock provider by default, per the established pattern); each answer is parsed for brand/competitor mentions, citations, position-within-answer, and sentiment; rollups: Visibility Score (0.5·mention rate + 0.3·position + 0.2·citation share), Share-of-Voice, Mention-Gap report, run-over-run deltas. Plan-gated per spec §7: pro = ChatGPT-only/weekly; agency/enterprise = all engines/daily; free/starter = 402. `GET /ai-tracker/due` + `due_runs()` are the cron/queue hookup point.

**Verification:** backend 269 tests green · MCP 89 tests + typecheck green (55 tools) · frontend tsc/lint clean, production build green (27 routes).
