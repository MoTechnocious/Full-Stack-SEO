# MySEOapp — Product Requirements Document

*Version 1.0 — 10 July 2026. Companion documents: `FEATURE_MATRIX.md` (exhaustive competitive feature inventory, 224 features) and `../ARCHITECTURE.md` (system design). This document defines what MySEOapp is, who it is for, what each module must do, and how the roadmap is sequenced.*

---

## 1. Vision & Positioning

**MySEOapp is the unified SEO system of record** — one product, one REST API, and one MCP server standing behind a crawl engine, a content-scoring engine, a keyword/rank engine, and a white-label reporting layer. It replaces the four-tool stack that technical SEOs, in-house marketers, and agencies currently assemble by hand:

| Instead of... | For... | MySEOapp gives you |
|---|---|---|
| **Screaming Frog** | desktop technical crawling & audits | the same audit depth, run from a cloud API, with no per-seat desktop license |
| **Surfer SEO** | NLP-driven content scoring | a dual SEO/AI-search content score, generated from the same data as the crawl |
| **Rank Math** | on-page rules & schema markup | the identical deterministic checklist and JSON-LD generator, without requiring WordPress |
| **HikeSEO** | managed task lists & white-label agency reporting | the same plan → task → report loop, exposed over an open API instead of a closed SaaS |

**Positioning statement:** *MySEOapp is the SEO platform built for the agentic era — every capability a human can click through in the dashboard, an AI agent can call through MCP, and every integration a competitor bolts on as an afterthought (CRM, Make.com, webhooks) is a first-class, audited pipeline from day one.*

### Why now

1. **The fragmentation tax is real and well-documented.** Across the four research dossiers, the same pattern repeats: Screaming Frog does technical audits but has no cloud story or API; Surfer does content scoring but has no crawler and no GA4; Rank Math does on-page/schema but is WordPress-only; Hike does task/reporting but has a narrow, unverified API and no multi-seat permissions. Nobody spans all four. See `FEATURE_MATRIX.md` §§1–6 for the full row-by-row evidence.
2. **The agentic/MCP moment is happening now, and it's half-built.** Screaming Frog shipped an MCP server in May 2026, but it's explicitly partial (list-mode crawling still unsupported as of the latest point release) and only ever controls the user's own desktop instance. Rank Math shipped MCP tools, but scoped to a single WordPress site. Nobody has shipped a cloud-native REST API *and* a complete MCP server as peer, first-class surfaces (`FEATURE_MATRIX.md` §5, rows 1–6).
3. **The AI-search shift (AEO/GEO) is real but immature.** Surfer is the only competitor with a shipped answer-engine visibility tracker; the other three are flat-footed or purely marketing the concept. This is a market-forming category — the right move is to build the foundation now and commit full engineering investment once methodology and demand are proven (see §8, v2 roadmap).

---

## 2. Market & Competitive Context

| Competitor | Pricing anchor (Jul 2026) | Core strength | #1 documented gap |
|---|---|---|---|
| **Screaming Frog** | £199–235 ($279–235) per seat/year, desktop license | Deepest technical-audit checklist in the category (300+ issue types); JS rendering, structured-data validation, custom extraction | Vendor-confirmed: **no general-purpose REST API**. Automation is desktop CLI or a partial MCP server only. |
| **Surfer SEO** | $49–999+/mo, 5-tier cloud SaaS | Best-in-class NLP content scoring; only shipped AI answer-engine tracker (AI Tracker) in the category | No native crawler (scope-limited to GSC-anchored content audit); no GA4 integration; thin backlink data (own admission) |
| **Rank Math** | Free plugin → PRO/Business/Agency + separately metered Content AI | Unmatched schema/redirect/on-page rule depth (37 schema types, ~24-test on-page checklist); shipped MCP tools | Entirely WordPress-bound; no standalone product for non-WP sites |
| **HikeSEO** | $89–299/mo ($59–199 GBP), Single/Multi-site | Best "done-for-you" task/report loop and white-label agency packaging; monthly plan→approve→execute→report cycle | Rank visibility capped at position 100 on at least one plan; no multi-country tracking on lower tiers; narrow/unverified API; no confirmed multi-seat RBAC |

MySEOapp's product bet is that **the union of these four feature sets, delivered through one API-and-MCP-first product**, is a materially stronger offer than any single competitor — and that the specific gaps each one has left open (no API, no crawler, WordPress lock-in, capped visibility, no RBAC) are exactly where a new entrant should differentiate rather than merely match.

---

## 3. Target Users & Personas

MySEOapp serves three primary buyer segments plus one MySEOapp-specific segment no competitor product targets well.

### Persona 1 — Priya, SMB Owner/Marketer
- **Profile:** Runs or markets for a small business (2–10 employees) — the exact profile HikeSEO's own research names as its core customer. Wears the marketing hat herself alongside other duties.
- **Goals:** Rank higher locally/organically without hiring a specialist or learning SEO jargon.
- **Pains today:** Screaming Frog and Surfer both assume SEO literacy she doesn't have; Hike is closest to her needs but caps rank visibility and locks her into one vendor's narrow API if she ever wants to build something custom.
- **How MySEOapp serves her:** Task-first dashboard (not a data dump), auto-generated action plans with plain-language "why" reasoning attached to every recommendation, monthly branded reports she can forward to a business partner.
- **Primary modules:** Reporting & Tasks, On-Page auto-fixes, Rankings summary.

### Persona 2 — Daniel, In-House SEO / Content Marketer
- **Profile:** Owns the organic channel inside a mid-size company; technically literate but not a crawler-configuration power user.
- **Goals:** Fewer tool switches (currently stacks Screaming Frog + Surfer + a separate rank tracker); defensible, explainable recommendations he can bring to stakeholders.
- **Pains today:** Technical audit data (Screaming Frog) and content optimization data (Surfer) live in two disconnected tools with no shared vocabulary; neither exposes a real API to build internal reporting against.
- **How MySEOapp serves him:** One crawl + one content score sharing the same issue taxonomy (`IssueCategory`, `Severity`) and grading language (`grade_from_score`) end to end.
- **Primary modules:** Crawl & Technical Audit, On-Page & Content Optimization.

### Persona 3 — Farah, Technical SEO Consultant
- **Profile:** Freelance/independent consultant auditing many client sites; power user of crawl configuration (regex include/exclude, segmentation, custom extraction).
- **Goals:** Bulk exports, scriptable access, the ability to build her own tooling on top of raw audit data.
- **Pains today:** Screaming Frog has the depth she needs but is desktop-bound and per-seat licensed across client machines; nothing in the category gives her a documented API to automate against.
- **How MySEOapp serves her:** Full `/api/v1` surface with the same data a UI user sees, versioned and documented for programmatic use.
- **Primary modules:** Crawl & Technical Audit, REST API.

### Persona 4 — Marcus, Agency Owner (+ team)
- **Profile:** Manages 10–100 client sites through a small agency; needs to prove ROI to clients monthly without every client seeing "powered by [vendor]."
- **Goals:** White-label reporting, multi-site management from one login, a way to delegate/track task execution across a client portfolio, a lead-gen mechanism to grow the client base.
- **Pains today:** Hike gets closest but has no confirmed team-seat/role-based permission system (it's "one agency login, many client-site records," not true multi-user RBAC) and pricing jumps sharply past 3 sites.
- **How MySEOapp serves him:** `WhiteLabelBranding` (logo, colors, footer, rebrandable AI-agent persona) applied consistently across the dashboard and generated reports; a public lead-gen audit widget wired straight into the CRM/lead pipeline; multi-seat RBAC sequenced explicitly for v1 rather than left undefined.
- **Primary modules:** Reporting & Agency/White-label, Integration Layer.

### Persona 5 — The Automation Engineer (MySEOapp-unique)
- **Profile:** Building an internal agentic workflow (e.g., a Claude-based SEO operations assistant) that needs to call SEO tooling programmatically, not click through a UI.
- **Goals:** A clean, documented tool surface an AI agent can reason about and call reliably.
- **Pains today:** No competitor serves this persona well — Screaming Frog's MCP is desktop-bound and partial; Rank Math's MCP is WordPress-scoped; Surfer and Hike have no MCP server at all.
- **How MySEOapp serves them:** A complete MCP server, callable both locally (stdio, for Claude Desktop/Code) and remotely (hosted HTTP/SSE, v1), where every tool is a thin wrapper over the same REST API — nothing is MCP-exclusive functionality.
- **Primary modules:** MCP Server, REST API.

---

## 4. Module-by-Module Functional Spec

Eight modules make up the product. Each subsection below covers purpose, key features, inputs/outputs (naming the actual Pydantic models), competitor parity notes (cross-referenced to `FEATURE_MATRIX.md`), and acceptance criteria.

### 4.1 Crawl & Technical Audit Engine (`backend/app/core/crawler`)

**Purpose.** Discover and evaluate every reachable URL on a site the way a search-engine crawler would — status codes, redirects, canonicalization, indexability, metadata, links, and images — at crawl scale, as a cloud/API-native service rather than a desktop application.

**Key features.**
- Seeded spider crawl with configurable page/depth limits and concurrency.
- Regex include/exclude scoping and custom user-agent per crawl.
- Per-page technical audit: response status, full redirect chain, canonical tag, combined robots-directive view, indexability verdict with a plain-English reason, headings, word count, internal/external links, broken-link detection, image inventory, structured-data type inventory.
- Crawl-level roll-up: status-class distribution, severity distribution, average score, top issues.
- Crawl comparison: diff two runs of the same site for added/removed URLs and status/score changes.
- Single-page audit without running a full crawl (`audit/page`).

**Inputs / Outputs.**
- Input: `CrawlConfig` (`start_url`, `max_pages` 1–100,000, `max_depth`, `respect_robots`, `follow_external`, `render_js`, `user_agent`, `include_patterns`, `exclude_patterns`).
- Output: `CrawlResult` (`crawl_id`, config echo, `started_at`/`finished_at`, `pages: list[PageAuditResult]`, `summary: CrawlSummary`, `top_issues: list[Issue]`).
- `PageAuditResult` carries title/meta/canonical/indexability fields, `h1`/`h2`, `hreflang: list[HreflangEntry]`, `structured_data_types`, `outlinks`/`broken_links: list[LinkInfo]`, `images_count`/`images_missing_alt`, `redirect_chain: list[RedirectHop]`, `issues: list[Issue]`, and a per-page `score`.
- Comparison: `CrawlComparison` (`added_urls`, `removed_urls`, `status_changes`, `score_changes`, `new_issues`, `resolved_issues`).

**Competitor parity notes.** Matches Screaming Frog's response-code/redirect/canonical/hreflang/robots/heading/image/link auditing (`FEATURE_MATRIX.md` §1, rows 14–37) delivered as a cloud service instead of a local install. JS rendering, custom extraction/XPath scraping, and site visualizations are deliberately deferred (§1 rows 12, 44, 54–56) so the API-first MVP ships fast — the one thing Screaming Frog's architecture structurally cannot offer.

**Acceptance criteria.**
- Given a valid `start_url` and default `CrawlConfig`, a crawl returns a `CrawlResult` with a `PageAuditResult` for every reachable, robots-allowed URL up to `max_pages`.
- Every `PageAuditResult` has a non-null indexability verdict, with `indexability_reason` populated whenever `indexability` is `NON_INDEXABLE`.
- Redirect chains longer than one hop are captured in full in `redirect_chain`, not collapsed to the final destination.
- `CrawlSummary.avg_score` is the mean of all page scores.
- A second crawl of the same `start_url` can be diffed against the first via `CrawlComparison`, correctly classifying added/removed URLs and status/score deltas.
- With `respect_robots=True` (the default), no `PageAuditResult` is ever recorded for a robots.txt-disallowed URL.
- Requests exceeding `crawler_max_pages`/`max_depth` are rejected with a 422 validation error, never silently truncated.

### 4.2 On-Page & Content Optimization Engine (`backend/app/core/onpage`)

**Purpose.** Score and guide a single piece of content against both a deterministic rule checklist (Rank Math parity) and a competitor-derived NLP model (Surfer parity), and generate valid JSON-LD structured data (Rank Math schema-generator parity) — all from a plain `(title, meta, body, keyword)` input tuple with no CMS dependency.

**Key features.**
- Rule-based on-page analysis: 0–100 score, letter grade, four weighted test categories, pass/fail checks with human-readable messages.
- Dual Content Score: an SEO Score and an AI Search Score, with competitor-derived structural targets (word count range, heading count, image count) and per-term usage targets (recommended range, heading-placement flag, under/optimal/over status).
- Schema/structured-data generation across 12 initial Schema.org types, producing both raw JSON-LD and a ready-to-embed `<script>` tag.

**Inputs / Outputs.**
- `OnPageRequest` (`url`, `html`/`content`, `title`, `meta_description`, `target_keyword`, `secondary_keywords`) → `OnPageResult` (`score`, `grade`, `checks: list[OnPageCheck]`, `category_scores`, `issues`).
- `ContentEditorRequest` (`target_keyword`, `content`, `country`, `secondary_keywords`, `competitor_word_counts`) → `ContentScore` (`content_score`, `seo_score`, `ai_search_score`, word/heading/image targets, `term_targets: list[TermTarget]`, `missing_terms`, `overused_terms`, `suggestions`).
- `SchemaRequest` (`schema_type: SchemaType`, `fields`) → `SchemaResult` (`json_ld`, `script_tag`, `warnings`).

**Competitor parity notes.** The rule engine mirrors Rank Math's four test categories (`FEATURE_MATRIX.md` §2 rows 1–11); the dual score mirrors Surfer's 2026 SEO Score/AI Search Score split (§2 rows 14–19) — this is the single most distinctive piece of the product, since no competitor combines a deterministic checklist and a competitor-derived NLP score in one call. Full AI-assisted rewriting (Auto-Optimize, Surfy-style inline commands, bulk generation) is deliberately deferred to v2 (§2 rows 12, 23, 30, 37–39, 45–48) so the explainable, deterministic core ships first.

**Acceptance criteria.**
- An `OnPageRequest` whose title omits `target_keyword` fails the keyword-in-title check, with the specific missing-keyword message present in `OnPageCheck.message`.
- `OnPageResult.score` is a weighted aggregate consistent with `category_scores` — no single category silently dominates the total.
- A `ContentEditorRequest` with fewer than three distinct competitor data points returns a flagged/capped `content_score` rather than a misleadingly precise number (mirrors Surfer's own ≥3-domain guardrail).
- Every `TermTarget` satisfies `recommended_min <= recommended_max`, with `status` consistent against `current_count`.
- `SchemaResult.json_ld` is syntactically valid JSON-LD for every supported `SchemaType`.
- An unsupported `schema_type` returns a clear validation error, never a best-effort guess.

### 4.3 Keyword Research, SERP & Rank Tracking Engine (`backend/app/core/keywords`)

**Purpose.** Turn a seed keyword or a tracked domain into actionable keyword intelligence — research, SERP composition, and time-series rank position — behind a pluggable data-provider seam so the engine runs on a free `mock` provider in dev/test and a paid data vendor in production without touching calling code.

**Key features.**
- Keyword research with volume, difficulty, CPC, competition, intent, and SERP-feature detection, clustered by SERP overlap.
- SERP analysis for a keyword + country + device combination: result list, detected SERP features, aggregate word count/backlinks/difficulty.
- Rank tracking with per-keyword history, position delta, best position, and a domain-level summary (average position, improved/declined/unchanged counts, top-3/top-10 counts, and a volume-weighted visibility score).

**Inputs / Outputs.**
- `KeywordResearchRequest` (`seed`, `country`, `language`, `limit`, `include_questions`) → `KeywordResearchResult` (`keywords: list[Keyword]`, `clusters: list[KeywordCluster]`).
- `SerpAnalysis` (`keyword`, `country`, `device`) → `results: list[SerpResultItem]`, `features: list[SerpFeature]`, aggregate stats.
- Rank tracking accumulates `TrackedKeyword` (with `RankPoint` history, `.delta` property) into `RankTrackingSummary`, keyed by domain + country.

**Competitor parity notes.** Covers Hike's keyword-research workflow and rank tracker (`FEATURE_MATRIX.md` §3 rows 1–4, 17–21) and Rank Math's Rank Tracker (row 17) at launch, and deliberately builds past two of Hike's own documented gaps from the same underlying data model rather than retrofitting them later: no visibility cap at position 100, and multi-country tracking from day one (rows 23–24). Surfer's 500-factor SERP correlation engine, Topical Map, and AI answer-engine tracker (rows 16, 30–32, 36) are v1/v2, not MVP.

**Acceptance criteria.**
- `KeywordResearchResult.keywords` never contains duplicate keyword strings within one request.
- `Keyword.difficulty` stays within 0–100 and `Keyword.competition` within 0.0–1.0 (enforced at the model layer via Pydantic `Field` constraints).
- Switching `SEO_KEYWORD_PROVIDER`/`SEO_SERP_PROVIDER` from `mock` to a real adapter requires no route or engine code changes — only a new adapter class and a config value.
- `TrackedKeyword.delta` returns `None` (never an exception or a misleading `0`) when either position is unknown.
- `RankTrackingSummary.visibility_score` weights both position and search volume — a #1 ranking on a 10-search/month keyword must never outrank a #3 ranking on a 50,000-search/month keyword.
- Recomputing a rank-tracking summary for the same domain+country correctly diffs improved/declined/unchanged against the prior stored snapshot.

### 4.4 Action Plans & Reporting, incl. White-Label (`backend/app/core/reporting`)

**Purpose.** Convert every finding produced by the other three engines into a single prioritized, explainable task list per site, and roll that list plus headline metrics into a branded, shareable report — replicating Hike's monthly plan → approve → execute → report loop and its white-label agency packaging.

**Key features.**
- Auto-generated `Task` entities (category, priority, page/keyword linkage, impact/effort, status) with an `AiReview` explainability layer — pass/flag verdict, written reasoning, confidence — attached to every auto-generated recommendation.
- `ActionPlan` roll-ups by priority and by status.
- Branded `Report` generation: headline metrics plus modular sections (`summary`/`rankings`/`audit`/`tasks`/`keywords`/`chart`) rendered under per-agency `WhiteLabelBranding` (agency name, logo, colors, footer text, and a rebrandable AI-agent persona name/icon — directly mirroring Hike's Kit-rebranding pattern).

**Inputs / Outputs.**
- Tasks are assembled from the other engines' issue/opportunity output into `ActionPlan` (`site`, `tasks: list[Task]`, `total`, `by_priority`, `by_status`).
- `Report` (`report_id`, `site`, `period_start`/`period_end`, `branding: WhiteLabelBranding`, `sections: list[ReportSection]`, `headline_metrics`).

**Competitor parity notes.** `Task`/`AiReview`/`TaskStatus`/`Effort` map almost field-for-field onto Hike's Approval-Centre task model (`FEATURE_MATRIX.md` §4 rows 1–5) — the closest 1:1 parity anywhere in the product. `WhiteLabelBranding` maps onto Hike's white-label and Kit-rebranding feature set (§6 rows 3, 5, 6). The Approval Centre human-sign-off workflow itself, and configurable auto-approval delay, are v1 — the data model needs to exist before the approval UX is built on top of it.

**Acceptance criteria.**
- Every auto-generated `Task` carries a non-empty `AiReview.reasoning` string — no recommendation ships unexplained.
- `ActionPlan.total` always equals `len(tasks)`; `by_priority`/`by_status` counts always sum to `total`.
- A `Report` generated without custom `WhiteLabelBranding` falls back to sane MySEOapp defaults, never blank branding fields.
- Two reports for the same site with overlapping periods never silently collide on `report_id`.
- `Report.sections` accepts at minimum the six documented section types and rejects an undocumented type at the API boundary.

### 4.5 Integration Layer (`backend/app/integrations`)

**Purpose.** Own every outbound and inbound integration boundary — lead capture and CRM delivery, Make.com dispatch, inbound webhook verification — as a single audited, retryable pipeline, so no other part of the system talks to a third party directly.

**Key features.**
- Lead intake and validation: normalizes a raw submission (e.g., from a public lead-gen audit widget) into a clean `LeadRecord`, or rejects it with explicit errors/warnings.
- Pluggable CRM push, selected by config (`mock`/`hubspot`/`salesforce`), not code.
- Outbound Make.com dispatch with idempotency keys.
- Inbound webhook receipt with HMAC-SHA256 signature verification.
- `DeliveryLog` audit trail with attempt counts and last-error capture for every outbound send.

**Inputs / Outputs.**
- `LeadRecord` → `LeadValidationResult` (`valid`, `normalized`, `errors`, `warnings`) → `DeliveryLog` (`target`, `lead_id`, `status: DeliveryStatus`, `attempts`, `last_error`).
- `MakeDispatch` (`event`, `data`, `idempotency_key`) for outbound; `WebhookEvent` (`type`, `payload`, `signature`, `verified`) for inbound.

**Competitor parity notes.** Directly answers Hike's lead-gen audit widget → CRM pipeline (`FEATURE_MATRIX.md` §4 rows 18–19) and is the concrete implementation of the pluggable-provider pattern used everywhere external data enters or leaves the system. No competitor in the research ships a Make.com-native gateway specifically (§5 row 9) — a deliberate MySEOapp choice given Make.com's popularity in the SMB/agency automation space this product targets.

**Acceptance criteria.**
- A `LeadRecord` missing a valid email fails `LeadValidationResult.valid` with a specific error, not a generic rejection.
- Every outbound dispatch produces exactly one `DeliveryLog` entry per attempt, with `attempts` incrementing on retry rather than creating duplicate rows.
- Failed deliveries retry up to `Settings.integration_max_retries` (default 3) before being marked `DeliveryStatus.FAILED`.
- An inbound webhook whose HMAC signature doesn't match `Settings.webhook_signing_secret` is rejected (`verified=False`) and never dispatched downstream.
- Switching `Settings.crm_provider` from `mock` to a real value requires no changes to the lead-intake route.

### 4.6 REST API (`backend/app/api`)

**Purpose.** Expose every engine as a stable, versioned, authenticated HTTP surface under `/api/v1` — the thing Screaming Frog explicitly lacks and Hike's is unverified/narrow — so the frontend, the MCP server, and any third-party integrator are peer consumers of one contract. Full endpoint-by-endpoint detail lives in `../ARCHITECTURE.md` §7.

**Key features.** Full `/api/v1` surface (audit, on-page, keywords, rankings, reports, integrations); a consistent request-id-tagged JSON error envelope on every failure path; fixed-window rate limiting with standard headers; structured JSON access logging on every request.

**Inputs / Outputs.** Every request/response pair is a named Pydantic model from `backend/app/models/`; every error is an `ErrorResponse`.

**Competitor parity notes.** Directly closes the single biggest documented gap in the competitive set (`FEATURE_MATRIX.md` §5 row 1) — Screaming Frog has vendor-confirmed there is no general API. This is the connective tissue the rest of the product is built around, not a bolt-on afterthought.

**Acceptance criteria.**
- Every documented `/api/v1` route returns a response matching its documented model; every error path returns an `ErrorResponse` with a stable `error` code.
- Every response carries `X-Request-ID` (echoing the caller's header when supplied) and `X-Response-Time-ms`.
- Rate-limited responses always include `Retry-After` and `X-RateLimit-Remaining: 0`.
- `/health` and `/version` require no authentication and are exempt from rate limiting.
- The OpenAPI schema is generated from the route/model definitions directly (FastAPI default), so docs cannot drift from the models.

### 4.7 MCP Server (`mcp-server/`)

**Purpose.** Let an AI agent (Claude Desktop, Claude Code, Cowork, or any MCP-compatible client) drive the entire product — trigger a crawl, score a page, research keywords, pull rankings, build a report — through natural-language tool calls, without duplicating a single line of business logic: every MCP tool is a thin, authenticated wrapper around the same REST API the frontend uses.

**Key features.** One MCP tool per core REST capability; API-key auth to the backend (`MYSEOAPP_API_KEY`, never a shared database credential); stdio transport for local desktop clients, with a hosted HTTP/SSE mode reserved for v1 remote-agent use.

**Inputs / Outputs.** MCP tool schemas mirror REST request/response models field-for-field — no parallel data model to maintain.

**Competitor parity notes.** Screaming Frog's MCP server (`FEATURE_MATRIX.md` §5 row 5) is the closest precedent but is explicitly partial (list-mode crawling unsupported as of its latest release) and, being desktop-bound, can only ever control the user's own machine — never a remote/hosted agent. Rank Math's MCP is scoped to a single WordPress site. MySEOapp is the only product in this set built against a cloud-native, multi-tenant REST API from the outset, which is what makes remote/hosted MCP access viable at all (not just "point an agent at my own laptop").

**Acceptance criteria.**
- Every MCP tool call maps to exactly one REST API call (or a small fixed sequence, e.g., submit-crawl then poll) — no tool re-implements engine logic locally.
- A missing or invalid `MYSEOAPP_API_KEY` produces a clear, actionable MCP tool error, never a silent failure.
- The MCP server's tool list and each tool's input schema are introspectable, so an agent or a human can discover the surface without reading source code.
- Long-running actions (a full crawl) are exposed as a submit-then-poll tool pair, never a single tool call that blocks for the crawl's duration.

### 4.8 Frontend (`frontend/`, Next.js)

**Purpose.** Give a human user the same capability set as the REST API and MCP server, through a task-first, dashboard-second UI that visualizes crawl results, content scores, rankings, and branded reports.

**Key features.** Site/project switcher; crawl-run view (filterable issue list, per-page drill-down); content editor/scorer view (live score, term targets, suggestions); keyword & rankings dashboard (position history, visibility score); action-plan/task board with inline AI Review reasoning; report builder/viewer with live white-label branding preview; agency/client switcher for multi-site accounts (v1).

**Inputs / Outputs.** Consumes the same `/api/v1` contract as the MCP server; no direct provider or database access (zero-trust — see `../ARCHITECTURE.md` §5).

**Competitor parity notes.** Deliberately borrows Hike's "task list, not a data dump" interaction model (`FEATURE_MATRIX.md` §4 row 1) as the default landing view, rather than Screaming Frog's spreadsheet-grid-first UI, since the primary personas skew toward "tell me what to do" over "let me explore raw data" — a full crawl-data grid remains available for the technical-consultant persona.

**Acceptance criteria.**
- Every screen's data comes exclusively from `/api/v1` calls — no frontend code path calls a third-party provider or a database directly.
- The content-scoring view updates score and term targets live as the user edits, with a bounded perceived-latency debounce (~1s).
- Agency users previewing a white-labeled report see their own branding applied consistently across every section, not just the header.
- The task board never displays a `Task` without its linked `AiReview` reasoning visible on hover/expand.

---

## 5. Non-Functional Requirements

### 5.1 Performance
- Default crawl concurrency is 10 workers (`Settings.crawler_max_concurrency`) with a 15-second per-request timeout (`crawler_timeout_seconds`) and a default 500-page cap (`crawler_max_pages`), independently overridable per request up to 100,000 pages (`CrawlConfig.max_pages`).
- Synchronous read endpoints (e.g., `rankings/{domain}`, `integrations/deliveries`) target sub-200ms p95 latency.
- Long-running work (crawls, content generation once AI writing ships) is always submit-then-poll — never a blocking multi-minute HTTP call.

### 5.2 Security / Zero-Trust
- No implicit trust between components: the frontend and MCP server are both external, authenticated clients of the REST API — neither has direct database or provider-credential access (full rationale in `../ARCHITECTURE.md` §5).
- All secrets (provider API keys, CRM credentials, webhook signing secrets, GSC service-account JSON) are environment-variable-sourced only (`SEO_` prefix via `Settings`/pydantic-settings), never hardcoded, never committed.
- Inbound webhooks are HMAC-SHA256-signed and verified before processing; unverified events never reach downstream handlers.
- Every request carries a `request_id` (`X-Request-ID`) for cross-log, cross-error-response correlation.
- API-key auth (`X-API-Key`) scopes and rate-limits every caller; production deployments additionally scope keys to a tenant/workspace (v1).
- Least-privilege provider credentials: each integration (GSC, GA4, DataForSEO, CRM, Make.com) uses its own narrowly scoped credential, so a compromised CRM key cannot be used to pull GSC data.

### 5.3 Rate Limiting
- Fixed-window limiter, default 120 requests/60-second window, keyed by API key when present, else client IP (`RateLimitMiddleware`).
- `/health`, `/`, and `/version` are explicitly exempt so uptime monitors are never throttled.
- 429 responses always carry `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining: 0`; successful responses carry `X-RateLimit-Remaining`/`X-RateLimit-Reset` so well-behaved clients can self-throttle.
- The in-memory limiter is explicitly documented as swappable for a Redis-backed shared store ahead of horizontal scale-out.

### 5.4 Logging & Observability
- Every log line is single-line JSON (`JsonFormatter`) — timestamp, level, logger name, message, plus arbitrary structured `extra` fields — parseable by any aggregator without a custom parser.
- Every HTTP request logs method, path, status, and `duration_ms` keyed to its `request_id` (`RequestContextMiddleware`).
- Unhandled exceptions are logged with full context before being converted to a generic 500 `ErrorResponse` — internals are never leaked to the caller, only to the log stream.
- Log level and JSON-vs-human-readable output are environment-configurable (`SEO_LOG_LEVEL`, `SEO_LOG_JSON`).

### 5.5 Reliability
- Persistence is abstracted behind one seam, `get_store()` / `InMemoryStore`, explicitly designed so Postgres/Redis can replace it without touching engine or route code.
- Outbound integration dispatches retry up to `integration_max_retries` (default 3) with attempt tracking in `DeliveryLog` before being marked failed.
- All domain errors raise a typed `AppError` subclass (`NotFoundError`, `BadRequestError`, `ValidationFailedError`, `RateLimitError`, `ProviderError`) mapped to a stable HTTP status and machine-readable `code` — callers branch on `code`, never on parsing a message string.

### 5.6 Data Privacy
- `LeadRecord` captures PII (name, email, phone, company) from public-facing lead-gen widgets. v1 requires documented retention limits, a deletion/export path, and CRM-push consent language appropriate for GDPR/CCPA-adjacent obligations, since agency customers will operate this against both EU and US site visitors.
- Crawled site content is treated as the customer's own data; MySEOapp does not resell or share crawl/content data across tenants.

### 5.7 Accessibility
- The frontend itself targets WCAG 2.1 AA — a product whose own audit engine will eventually flag accessibility issues (`FEATURE_MATRIX.md` §1 row 41, v2) should not ship an inaccessible UI.

### 5.8 Internationalization
- Content scoring and on-page checks must not hard-assume English. Rank Math's own singular/plural keyword matching is explicitly English-only per the research (`FEATURE_MATRIX.md` §2 row 50) — MySEOapp should not inherit that as a permanent constraint. UI copy is structured for future localization even though only English ships at MVP.

---

## 6. Data Model Overview

All domain models inherit from a shared base and reuse a shared vocabulary, so a "B grade" or a "needs_improvement" status means the same thing whether it describes a crawled page, an on-page check, or (in v1) a keyword portfolio.

| File | Key classes | Domain |
|---|---|---|
| `backend/app/models/common.py` | `AppModel` (base — populate-by-name, ignores unknown input), `Severity` (weighted enum: critical→info), `IssueCategory`, `Device`, `SearchIntent`, `Indexability`, `Issue`, `grade_from_score()`, `status_label()` | Shared vocabulary used by every other model file |
| `backend/app/models/audit.py` | `CrawlConfig`, `RedirectHop`, `LinkInfo`, `ImageInfo`, `HreflangEntry`, `PageAuditResult`, `CrawlSummary`, `CrawlResult`, `SitemapUrl`, `CrawlComparison` | Crawl & Technical Audit (Screaming Frog parity) |
| `backend/app/models/onpage.py` | `CheckCategory`, `OnPageRequest`, `OnPageCheck`, `OnPageResult`, `TermStatus`, `TermTarget`, `ContentEditorRequest`, `ContentScore`, `SchemaType`, `SchemaRequest`, `SchemaResult` | On-Page & Content Optimization (Rank Math + Surfer parity) |
| `backend/app/models/keywords.py` | `SerpFeature`, `Keyword`, `KeywordCluster`, `KeywordResearchRequest`/`Result`, `SerpResultItem`, `SerpAnalysis`, `RankPoint`, `TrackedKeyword`, `RankTrackingSummary` | Keyword Research, SERP & Rank Tracking (HikeSEO parity) |
| `backend/app/models/reporting.py` | `TaskStatus`, `Effort`, `AiReview`, `Task`, `ActionPlan`, `WhiteLabelBranding`, `ReportSection`, `Report` | Action Plans & Reporting, incl. White-Label (HikeSEO parity) |
| `backend/app/models/integrations.py` | `DeliveryStatus`, `LeadRecord`, `LeadValidationResult`, `DeliveryLog`, `WebhookEvent`, `MakeDispatch` | Integration Layer (CRM, Make.com, webhooks) |
| `backend/app/models/api.py` | `ErrorDetail`, `ErrorResponse`, `HealthResponse`, `VersionResponse`, `Page[T]` | Cross-cutting API envelope |

**Shared conventions worth calling out explicitly:**
- Every model extends `AppModel`, configured with `populate_by_name=True` and `extra="ignore"` — API clients can send extra fields without breaking requests, and both snake_case field names and any future aliases resolve consistently.
- `Severity.weight` gives every issue/task a numeric ordering (critical=5 → info=1) so priority sorting is identical whether the source is a crawl issue, an on-page check, or a task.
- `grade_from_score()` (0–100 → A–F) and `status_label()` (0–100 → good/needs_improvement/poor) are the single implementations reused everywhere a score needs a human-readable label — `OnPageResult.grade`, crawl summaries, and future keyword-portfolio grading all derive from the same two functions, so the product never accidentally ships two different definitions of "what counts as a B."

---

## 7. Pricing & Packaging Concept

Tiers are anchored against the market data in the research dossiers — Screaming Frog's flat per-seat license, Surfer's five-tier doc/prompt-gated SaaS, Rank Math's site-count-gated plugin tiers, and Hike's Single/Multi-site split — while keeping MySEOapp's entry price below Hike's ($89–149/mo) to win the SMB self-serve segment on price as well as scope.

| Tier | Target persona | Price anchor | Sites | Crawl pages/mo | Tracked keywords | API / MCP access | White-label | Notes |
|---|---|---|---|---|---|---|---|---|
| **Free** | Evaluators, Priya (trial) | $0 | 1 | 100 | 10 | Read-only, low rate limit | MySEOapp-branded | No signup-gated crawl cap, mirroring Screaming Frog's free-tier philosophy but as a cloud trial, not a desktop download |
| **Starter** | Priya (SMB owner) | ~$39–49/mo | 1 | 2,500 | 100 | Full REST API (no MCP) | MySEOapp-branded | Full on-page + content-score tools; monthly branded report (MySEOapp branding) |
| **Growth** | Daniel (in-house SEO) | ~$99–149/mo | 3–5 | 10,000 | 500 | Full REST API + MCP server | Optional add-on | GA4 + GSC integrations, scheduled crawls/reports, Make.com/CRM integration |
| **Agency** | Marcus (agency owner) | ~$299–499/mo + per-site | Unlimited (fair-use) | 50,000 | 5,000 | Full REST API + MCP, higher rate limits | Full (incl. rebrandable AI persona) | Multi-seat RBAC (v1), client-restricted portals, lead-gen audit widget, priority support |
| **Enterprise** | Large agencies, in-house teams at scale | Custom, from ~$999/mo | Custom | Custom | Custom | Custom quota, dedicated support | Full + custom domain | SSO, dedicated CSM, custom data-retention/SLA, first access to AI Answer-Engine Tracking (v2) once shipped |

**AI Answer-Engine Tracking (v2)** is positioned as a Growth+/Agency+ capability once built — mirroring how Surfer gates AI Tracker prompt volume and model coverage by tier (entry tier: ChatGPT only, weekly refresh; higher tiers: all five models, daily refresh) — rather than a Free/Starter feature, given its materially higher per-query infrastructure cost.

**Packaging principles carried over from the research:**
- Match Rank Math's 2026 shift from a shared credit pool to **per-feature usage counters** once AI writing tools ship (v2) — a heavy research run should never silently exhaust a user's budget for unrelated tools.
- Match Surfer's practice of keeping core value (content score, on-page checklist, basic rank tracking) available on every paid tier, gating primarily on *volume* and *which integrations/advanced modules* unlock — not on hiding the core product behind the top tier.
- Avoid Hike's documented cap-and-surprise pattern (being "charged extra for keywords beyond an allowance" on a legacy plan) — publish hard tracked-keyword ceilings per tier up front.

---

## 8. Phased Roadmap: MVP → v1 → v2

### MVP (current build phase)
Ship criteria: all five engines, the REST API, the MCP server, and the frontend are functional end-to-end against the `mock` data providers, with the full test suite green.

- **Crawl & Audit:** static HTTP fetch + parse (no JS rendering yet); core technical checks — status/redirects/canonical/robots/headings/meta/word-count/indexability/links/images; crawl summary and crawl comparison.
- **On-Page:** full rule-based checklist scorer; dual Content Score with competitor-derived targets (against mock competitor data); schema generator (12 types).
- **Keywords:** research/SERP/rank-tracking against the `mock` provider; visibility score; SERP-feature tagging.
- **Reporting:** `Task`/`ActionPlan` generation from the other engines' issues; white-label `Report` builder.
- **Integrations:** lead capture + validation, mock CRM push, Make.com dispatch, inbound webhook verification.
- **REST API:** the full documented `/api/v1` surface wired to every engine above.
- **MCP server:** one tool per primary REST capability, stdio transport.
- **Frontend:** dashboard shell, crawl view, content editor, rankings view, task board, report viewer — all backed by the live REST API.
- **NFRs already carried through:** rate limiting, structured JSON logging, typed error envelope, request-id tracing.

### v1 (near-term, post-MVP — "real data + agencies")
- Live data providers: a DataForSEO-class keyword/SERP adapter, Google Search Console OAuth, GA4, PageSpeed Insights/CrUX.
- JS rendering (headless browser pool) for the crawler.
- Structured-data Rich-Results validation depth (required vs. recommended property rules); schema templates/display conditions.
- Content-refresh "Best Opportunities" ranking; topical/cluster planning; keyword cannibalization and Keyword-Confusion-style validation.
- Redirects manager and 404 monitor as standing features, not just crawl-time detection.
- CMS publish connectors: WordPress plugin/REST bridge, Google Docs overlay.
- Postgres/Redis swap for the in-memory store; Redis-backed rate limiter ahead of horizontal scale-out.
- Multi-tenant agency accounts: multi-site management, client-restricted portals, the lead-gen audit widget wired end-to-end, first-cut role-based permissions.
- API hardening: full API-key auth enforcement, `/api/v2` groundwork, machine-readable docs index for AI-agent discovery.
- Ahrefs/Majestic/Moz bring-your-own-key backlink import.

> **Status update (10 July 2026):** the multi-tenant agency accounts and API-key auth-enforcement items above have shipped, ahead of the rest of this v1 list — see §11 below and `../MULTI_TENANCY.md` / `../AUTH_AND_BILLING.md` for the delivered design. The Postgres swap shipped as the default *schema*, not yet the default *deployment target* (SQLite remains the dev/test default; Postgres is opt-in via `SEO_DATABASE_URL`, see `../SYSTEM_STATE.md` known debt).

### v2 (future / exploratory bets)

**AI Answer-Engine (AEO/GEO) tracking — the headline v2 bet.** This is the gap Surfer is actively pushing (its AI Tracker is the only shipped answer-engine visibility product across all four competitors) and that Hike only markets, without a working tracker. The v2 scope: run a scheduled, managed set of prompts against multiple LLM front ends (ChatGPT, Perplexity, Gemini, Google AI Overviews, Google AI Mode), parse each answer for brand/competitor mentions, citation links, position-within-answer, and sentiment, and roll the results into a Visibility Score, a Share-of-Voice metric, and a Mention-Gap report (`FEATURE_MATRIX.md` §3 rows 30–32).

*Why v2 and not MVP/v1:* (1) it requires scraping infrastructure against multiple consumer-facing AI front ends rather than clean, stable APIs — Surfer itself states it scrapes real front-end answers because APIs return "sanitized" responses; (2) the infrastructure and cost profile is materially different from the rest of the product (browser automation at prompt-and-model-matrix scale, not page-fetch scale); (3) the category's methodology is still forming — no vendor has a standardized definition of "mention rate" or "visibility score" yet. The right MVP/v1-stage move is to reserve the data-model shape (a prompt-management and mention-tracking schema, extending the `keywords` domain) without committing full engineering investment until the core product is proven and the category matures.

**Other v2 items:**
- Full AI-writing pipeline (Surfy-style inline assistant, Auto-Optimize, full article generation, Humanizer/Detector, bulk/category generation).
- Accessibility auditing (axe-core), spelling/grammar checking, AMP validation, site visualizations, custom extraction (XPath/CSS/regex scraping rules).
- Onsite-Optimiser-style JS-snippet live publishing (CMS-agnostic on-page changes without back-end access) — Hike's most structurally distinct feature and the highest-effort integration pattern in the whole matrix.
- True multi-seat RBAC maturity, Enterprise SSO, native mobile apps.
- Broader provider marketplace: Zapier-equivalent automation, Looker Studio/Google Sheets export, Contentful, ChatGPT Canvas.
- Full multi-language content-scoring parity and non-English keyword/rank support at depth.

---

## 9. Success Metrics / KPIs

| Metric | What it tells us |
|---|---|
| **Activation** — % of signups completing a first crawl or on-page analysis within 24h | Whether the core value loop is reachable fast enough |
| **Engagement** — weekly active audits/content-scores per account; tasks marked done per week | Whether the product is used as a working tool, not a one-time report |
| **Retention** — % of tracked domains still actively polled at day 30/90 | Whether rank tracking (the highest-frequency touch point) sticks |
| **Expansion** — agency accounts adding a 2nd+ site; seat/site growth within an account | Whether the agency tier's packaging is landing |
| **API/MCP adoption** — external API calls and MCP tool invocations per active account | Leading indicator that the "AI-agent native" positioning is real usage, not just a slide |
| **Report delivery** — white-label reports generated/shared per agency account per month | Whether the Hike-style reporting loop is actually replacing the competitor tool it targets |

---

## 10. Risks & Open Questions

- **Third-party data-licensing cost.** Keyword/SERP data (DataForSEO-class) and Google API usage at scale must be modeled against real per-call provider cost before tier pricing is finalized — competitor sticker prices are a starting anchor, not a cost model.
- **AEO tracking carries ToS/reliability risk.** Front-end scraping of consumer AI products (rather than calling vendor APIs) is Surfer's own stated methodology and the more accurate approach, but it needs a legal/ToS review before v2 commitment.
- **Headless rendering is materially more expensive per page than a static fetch.** JS-rendering needs cost modeling before it becomes a v1 default rather than an opt-in.
- **WordPress-native parity is a real market expectation** (Rank Math's entire distribution model rides on it). Decide deliberately in v1 planning whether a WordPress plugin/connector is a must-have or whether MySEOapp stays API/dashboard-only and lets WordPress users integrate via the REST API.
- **Google API rate limits** (especially the URL Inspection API, which Screaming Frog itself works around by sampling priority URLs rather than full-site inspection) constrain how deep GSC-derived features can go without careful batching and caching.

---

## 11. Multi-Tenancy, Accounts & Billing

*Added 10 July 2026, once this layer was built and validated (89 passing backend tests). Full implementation detail lives in `../MULTI_TENANCY.md` (tenancy model, data model, auth+org request flow) and `../AUTH_AND_BILLING.md` (identity providers, RBAC, API keys, plan catalog, quota enforcement, Stripe setup) — this section covers the product decisions those documents implement.*

### 11.1 Overview & positioning shift

Everything in §§1–10 above describes MySEOapp as a single-tenant engine: one deployment, one set of engines, consumed by whichever frontend/MCP/API client is pointed at it. This section specs the layer that sits in front of that engine so the *same* deployment can serve many independent customers at once — the step that turns MySEOapp from "a tool scalingfirm.com runs for itself" into "a product other agencies and teams can sign up for." Nothing in §§1–10 changed to make this true: every engine (crawler, on-page, keywords, reporting) is exactly as pure and DB-unaware as it was at MVP. What was added sits strictly above it — accounts, organizations, roles, plans, and quotas.

### 11.2 Accounts, organizations & the agency multi-client model

**Purpose.** Let a person hold membership in more than one workspace at different permission levels, so the same account model serves an in-house team (Daniel, §3) and an agency managing many clients (Marcus, §3) without treating them as different products.

**Key features.**
- A **User** is a person; an **Organization** is a tenant workspace; a **Membership** joins the two with a **role** — `owner`, `agency_admin`, `editor`, or `client` (read-only). One user can hold memberships in many organizations simultaneously, and switch between them without logging out.
- Signup is self-serve and instant: a new company gets a working, isolated organization the moment they create an account, on the Free plan, with no manual provisioning step.
- Team and client onboarding is invite-based, assigning a role at invite time.
- The `client` role is the direct product answer to Hike's documented gap (§2): "one agency login, many client-site records" is not the same as a client having their *own*, real, read-only login into their *own* results — MySEOapp gives the client an actual account and an actual role, not a shared password or a static export.

**Why this is the agency multi-client model, concretely.** An agency (Marcus) doesn't get ten disconnected accounts for ten clients — it gets one organization it owns, with client stakeholders invited into it at the `client` role (read-only: they can see audits, rankings, and reports, but never trigger a crawl, spend a content-score quota, or see billing). If a client wants their *own* workspace with its *own* quota — e.g., a client who wants to run their own crawls independently of the agency's plan — they get their own organization, and the agency's team is invited into *that* org instead, typically at `editor`. Both shapes ("client as a read-only member of the agency's org" and "agency as an editor inside the client's own org") are the same underlying primitive (`Membership`), so the product doesn't have to pick one topology in advance — the buyer does.

**Acceptance criteria.**
- A user with memberships in two organizations sees both when listing their orgs, and switching between them never leaks data from the non-active organization into a response.
- Inviting a `client`-role member never grants them the ability to trigger a crawl, spend any metered quota, or reach a billing endpoint — enforced by the RBAC permission matrix in `../AUTH_AND_BILLING.md` §1.4.
- Removing/revoking a membership does not delete the underlying user account — the same person can still hold other memberships elsewhere.

### 11.3 Pricing & packaging — the subscription-replacement strategy

The tier concept in §7 above was written before this layer was built, as a market-anchored *concept*. What actually shipped in code (validated by the billing test suite) is the pricing/packaging system below — it supersedes §7's numbers as the authoritative, enforced catalog; §7 is left in place above as the original market-positioning rationale, which still holds directionally (undercut Hike on entry price, gate primarily on volume not core value, avoid a cap-and-surprise pattern).

| Plan | Price | Sites | Tracked keywords | Crawls/mo | Reports/mo | Notable features |
|---|---|---|---|---|---|---|
| **Free** | $0 | 1 | 25 | 5 | 2 | — (evaluation tier) |
| **Starter** | $29/mo ($290/yr) | 3 | 200 | 30 | 20 | API access, Content AI |
| **Pro** | $79/mo ($790/yr) | 10 | 1,000 | 150 | 100 | + MCP access, competitor analysis, scheduled crawls |
| **Agency** | $199/mo ($1,990/yr) | 50 | 5,000 | 1,000 | 1,000 | + White-label reporting, priority support |
| **Enterprise** | Custom | Unlimited | Unlimited | Unlimited | Unlimited | Everything, custom SLA |

*(The complete limit set — pages/crawl, content scores/mo, keyword lookups/mo, seats — and the full feature-flag matrix are in `../AUTH_AND_BILLING.md` §2.1; the table above is the product-level summary.)*

**The subscription-replacement strategy.** The product bet stated in §1 — that the union of four competitors' feature sets beats any one of them — only becomes a *pricing* advantage if a customer's bill actually shrinks by consolidating. The mechanism is direct: each of the four workflows MySEOapp replaces (Screaming Frog crawling, Surfer content scoring, a keyword/rank tool, Hike-style reporting) maps onto one of this plan's usage counters (crawls/month, content scores/month, keyword lookups/month + tracked keywords, reports/month), all drawn from the *same* plan instead of four separate vendor invoices. A Starter customer at $29/mo is being asked to compare that single number against what they were paying Screaming Frog plus a content tool plus a rank tracker separately — not against any single competitor's sticker price. This is why limits are published per-metric and per-tier up front (§7's "avoid Hike's cap-and-surprise pattern" principle) rather than bundled into an opaque "credits" pool: a prospective customer can map their current per-tool usage directly onto the table above before switching.

**Feature gating follows the same buyer logic used in §3's personas**, not an arbitrary tier ladder:
- API access and Content AI unlock at Starter — Priya (SMB owner, §3) needs the content tooling and the option to automate immediately, even on the cheapest paid tier.
- MCP access, competitor analysis, and scheduled crawls unlock at Pro — Daniel (in-house SEO, §3) is the persona who wants an agentic workflow and recurring automated audits, not just ad-hoc runs.
- White-label reporting and priority support are Agency-and-up exclusives — this is Marcus's (§3) tier by design; white-label branding has no value to a single-site in-house team, and every SEO reporting competitor in the research (§2) gates it at the top of their ladder for the same reason.

### 11.4 Quota enforcement & feature gating (product-level contract)

**Purpose.** Guarantee that "which plan are we on" is enforced the same way everywhere in the product — no engine, route, or UI screen gets to invent its own definition of "over quota."

**Key features.**
- Every metered action is checked against the org's plan **before** it runs and recorded **only after** it succeeds, so a failed or rejected request never silently consumes quota.
- Two failure modes are distinguished at the HTTP layer: `402 quota_exceeded` (allowed in principle, this period's/plan's allowance is used up) and `402 feature_not_available` (not included in this plan at all, regardless of usage) — both return machine-readable codes plus a human-readable message naming the exact metric/feature and the plan that would unblock it, so a UI can turn either straight into an in-product upsell rather than a dead end.
- A single usage-summary endpoint gives an authoritative used/limit view across every metric — the same numbers a customer would use to decide whether to upgrade.

**Acceptance criteria.**
- No two entry points to the same metered action (REST, MCP, future UI) can disagree about whether a request is within quota, because both consult the same entitlements/usage code path, never a duplicated check.
- A rejected (402) request never increments any usage counter.
- Every plan's limits and feature flags are discoverable without authentication, so pricing-page copy can never drift from what is actually enforced.

### 11.5 Data model additions

| File | Key classes | Domain |
|---|---|---|
| `backend/app/db/models_tenancy.py` | `User`, `Organization`, `Membership`, `Invite`, `ApiKey` | Accounts, workspaces, roles, invitations, self-hosted API credentials |
| `backend/app/db/models_billing.py` | `Subscription`, `UsageRecord` | Live plan state per org; per-metric usage counters |
| `backend/app/db/models_seo.py` | `Project`, `CrawlRecord`, `RankingRecord`, `ReportRecord`, `ActionPlanRecord`, `LeadRow`, `DeliveryLogRow` | Org-scoped persistence for every engine output described in §4 above |

These tables follow the same shared-vocabulary discipline described in §6: they don't re-model engine concepts (an `Issue`, a `Task`, a `RankTrackingSummary`) as new SQL columns — they wrap the existing Pydantic models from §6 in an `org_id`-carrying envelope. Full column-level detail and the tenant-isolation mechanics live in `../MULTI_TENANCY.md` §2 and §4.

### 11.6 Competitor parity notes

None of the four competitors researched for this product (§2) were evaluated on multi-tenant account architecture specifically, but the research repeatedly surfaces the same gap this section closes: Hike is the only one of the four with anything resembling agency/multi-site packaging, and its own documented limitation is "one agency login, many client-site records" rather than real multi-seat, role-based membership (§2, §3 persona 4). A `client` role with its own real login and a hard read-only permission boundary — rather than a shared password or a static PDF export — is a materially stronger agency offering than the closest precedent in the category.

---

## Cross-References

- Full competitive feature inventory: `FEATURE_MATRIX.md` (224 features across 6 domains)
- System design, API surface, MCP tool list, deployment topology: `../ARCHITECTURE.md`
- Multi-tenancy model, data model, and the auth+tenant request-flow diagram: `../MULTI_TENANCY.md`
- Authentication (IdP delegation, RBAC, API keys) and billing (plans, quotas, Stripe): `../AUTH_AND_BILLING.md`
- Live module inventory, test counts, and known debt: `../SYSTEM_STATE.md`
- Source research: `docs/research/{screaming-frog,surfer-seo,rank-math,hikeseo}-features.md`
- Backend contracts referenced throughout: `backend/app/models/{audit,onpage,keywords,reporting,integrations,common,api}.py`, `backend/app/config.py`
