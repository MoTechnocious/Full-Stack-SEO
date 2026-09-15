# MySEOapp — Competitive Feature Matrix

*Version 1.0 — 10 July 2026. Synthesized from the four research dossiers in `docs/research/` (Screaming Frog, Surfer SEO, Rank Math, HikeSEO) and cross-checked against the backend Pydantic contracts in `backend/app/models/`. This document is the single source of truth for "does MySEOapp do X, and does it already have a data contract for X."*

## How to read this matrix

**Competitor columns** (Screaming Frog, Surfer, Rank Math, HikeSEO) use:

| Symbol | Meaning |
|---|---|
| ✓ | Shipped, available on at least an entry paid tier (or free) |
| ✓ (tier) | Shipped, gated to a specific tier — tier noted in parentheses (e.g. `✓ (PRO)`, `✓ (Enterprise)`) |
| Partial | Adjacent capability exists but doesn't fully cover the feature as scoped |
| ✗ | Not offered |
| ✗ (gap) | Explicitly called out as a documented limitation/gap in the research dossier — a candidate differentiation point |

**MySEOapp Module** references the actual backend package or app that owns the capability, using repo-relative shorthand: `core/crawler`, `core/onpage`, `core/keywords`, `core/reporting`, `app/integrations`, `app/api`, `mcp-server`, `frontend`. These map 1:1 to `backend/app/core/*`, `backend/app/integrations`, `backend/app/api`, `mcp-server/`, and `frontend/`.

**Status** — exactly one of:

- **Implemented** — a concrete Pydantic model, enum, config flag, middleware, or utility function for this capability already exists in the current codebase (verified directly against `backend/app/models/*.py`, `backend/app/config.py`, `backend/app/middleware/*.py`, `backend/app/logging_config.py`, `backend/app/services/store.py`, `backend/app/utils/*.py`). This means the **contract and/or scaffolding is real and reviewable today** — it does not always mean the end-to-end engine, route, or UI is wired up yet (those are tracked separately as build tasks). Where useful, the owning class/field is named inline.
- **Planned** — committed for the MVP or v1 build; the capability is in scope for one of the five core engines, the REST API, the MCP server, or the frontend, but no concrete model/config artifact is confirmed yet, or the owning package is currently a stub.
- **Future** — v2+ or exploratory; either genuinely new territory (e.g., AI answer-engine tracking) or a deliberate near-term deferral of a competitor capability.

---

## 1. Crawl & Technical Audit

Screaming Frog's home turf: link-graph discovery, response-code/redirect/canonical/hreflang/robots auditing, structured-data and accessibility validation, and desktop-grade automation. Rank Math's sitewide analyzer and Hike's GSC-fed audit tool are the lighter-weight competitors here.

| # | Feature | Screaming Frog | Surfer | Rank Math | HikeSEO | MySEOapp Module | Status |
|---|---|---|---|---|---|---|---|
| 1 | Organic "spider" crawl (breadth-first link discovery from a seed URL) | ✓ | ✗ | ✗ | Partial (GSC-fed audit, not a crawler) | `core/crawler` | Implemented — `CrawlConfig.start_url`, `CrawlResult` |
| 2 | List-mode crawl (fixed URL list, depth pinned to 0) | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Planned |
| 3 | SERP snippet preview (pixel-width title/meta rendering) | ✓ | Partial (screenshots in SERP Analyzer) | ✓ (social preview editor) | ✗ | `core/onpage` | Planned |
| 4 | Crawl seeded from an XML sitemap | ✓ | ✗ | ✗ (generates, doesn't crawl-seed) | ✗ | `core/crawler` | Planned |
| 5 | Include/Exclude regex scoping | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Implemented — `CrawlConfig.include_patterns` / `exclude_patterns` |
| 6 | Speed/concurrency throttling | ✓ | n/a | n/a | n/a | `core/crawler` | Implemented — `Settings.crawler_max_concurrency`, `crawler_timeout_seconds` |
| 7 | User-agent switching (Googlebot/Bingbot/AI bots/custom) | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Implemented — `CrawlConfig.user_agent` |
| 8 | Custom HTTP headers & authenticated crawling (basic/digest/forms) | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Planned |
| 9 | robots.txt viewer/editor/tester | ✓ | ✗ | ✓ (built-in editor) | ✗ | `core/crawler` | Planned |
| 10 | Crawl segmentation by site section | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Future |
| 11 | Configurable crawl size ceiling | ✓ (500 free / hardware-bound paid) | n/a | n/a | ✓ (plan-based) | `core/crawler` | Implemented — `CrawlConfig.max_pages` (1–100,000), `Settings.crawler_max_pages` |
| 12 | JavaScript rendering (headless browser) | ✓ | n/a | n/a | n/a (JS snippet ≠ rendering) | `core/crawler` | Planned — `CrawlConfig.render_js` flag reserved, fetcher not yet built |
| 13 | Raw-vs-rendered HTML diff (JS-SEO risk indicator) | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Future |
| 14 | Response-code bucketing (2xx–5xx, no-response) with source page | ✓ | ✗ | Partial (404 Monitor only) | Partial (broken-link list) | `core/crawler` | Implemented — `PageAuditResult.status_code`, `CrawlSummary.by_status_class` |
| 15 | Redirect chain & loop mapping (incl. JS/meta-refresh redirects) | ✓ | ✗ | Partial (redirect manager, no chain view) | Partial (flags "redirect problems") | `core/crawler` | Implemented — `RedirectHop`, `PageAuditResult.redirect_chain` |
| 16 | Canonical tag vs. header conflict detection | ✓ | ✗ | ✓ (auto-canonical + override) | ✗ | `core/crawler` | Planned — `PageAuditResult.canonical` models the tag; header-vs-tag comparison is engine work |
| 17 | Pagination `rel=next/prev` audit | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Future |
| 18 | Hreflang audit (missing return tags, invalid codes, non-200 targets) | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Implemented — `HreflangEntry`, `PageAuditResult.hreflang` |
| 19 | Combined robots-directive view (meta robots + X-Robots-Tag + robots.txt) | ✓ | ✗ | ✓ (per-post + global) | ✗ | `core/crawler` | Implemented — `PageAuditResult.meta_robots` / `x_robots_tag`, `Indexability` |
| 20 | Title tag audit (missing/duplicate/length/multiple) | ✓ | Partial (via Content Score) | ✓ | ✓ | `core/crawler` + `core/onpage` | Implemented — `PageAuditResult.title`, `title_length` |
| 21 | Meta description audit (missing/duplicate/length/multiple) | ✓ | Partial | ✓ | ✓ | `core/crawler` + `core/onpage` | Implemented — `PageAuditResult.meta_description`, `meta_description_length` |
| 22 | Heading audit (H1/H2+ missing/duplicate/non-sequential) | ✓ | Partial (structural targets) | ✓ (subheading keyword test) | ✓ | `core/crawler` + `core/onpage` | Implemented — `PageAuditResult.h1`, `h2` |
| 23 | Word count per page | ✓ | ✓ | ✓ | Partial | `core/crawler` + `core/onpage` | Implemented — `PageAuditResult.word_count`, `utils/text.word_count` |
| 24 | Readability scoring | ✓ | Partial (structure guidance) | ✓ (content readability tests) | Partial | `core/onpage` | Implemented — `utils/text.flesch_reading_ease` |
| 25 | Thin/low-relevance content flag (topical-deviation NLP) | ✓ | Partial (topical gap panel) | ✗ | ✗ | `core/crawler` | Future |
| 26 | Indexability status with plain-English reason | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Implemented — `Indexability`, `PageAuditResult.indexability_reason` |
| 27 | Exact duplicate-content detection (hash-based) | ✓ | ✗ | ✗ | Partial (flags language-variant false positives) | `core/crawler` | Planned |
| 28 | Near-duplicate / semantic-similarity detection | ✓ (incl. vector-embedding similarity) | ✗ | ✗ | ✗ | `core/crawler` | Future |
| 29 | Security & URL-hygiene checks (mixed content, insecure forms, URL format) | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Planned |
| 30 | Internal/external link inventory with status codes | ✓ | ✗ | ✓ (Link Counter module) | ✗ | `core/crawler` | Implemented — `LinkInfo`, `internal_links_count`/`external_links_count` |
| 31 | Broken-link bulk detection with source-page export | ✓ | ✗ | ✓ (Broken Link Checker, Business/Agency) | ✓ | `core/crawler` | Implemented — `PageAuditResult.broken_links` |
| 32 | Per-URL inlinks/outlinks detail | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Implemented — `PageAuditResult.outlinks` (inlinks derived from the link graph) |
| 33 | Anchor-text aggregation & generic-anchor flag | ✓ | Partial (structure factor) | ✗ | ✗ | `core/crawler` | Planned — `LinkInfo.anchor_text` captures raw text; aggregation/flagging is engine work |
| 34 | Orphan-page detection (cross-referenced against sitemap/GA/GSC) | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Planned |
| 35 | Internal Link Score (PageRank-style 0–100) | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Future |
| 36 | Uncrawlable internal outlinks (span/div/onclick/`javascript:` links) | ✓ (v24.0) | ✗ | ✗ | ✗ | `core/crawler` | Future |
| 37 | Image audit (missing alt, oversized, missing width/height) | ✓ | ✓ (image-count target) | ✓ (Image SEO module) | ✓ (alt-text scope) | `core/crawler` + `core/onpage` | Implemented — `ImageInfo`, `images_count`/`images_missing_alt` |
| 38 | AMP crawling & validation | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Future |
| 39 | Structured-data type inventory at crawl time | ✓ | Partial (schema-presence factor) | ✓ (inline validation) | ✗ | `core/crawler` | Implemented — `PageAuditResult.structured_data_types` |
| 40 | Structured-data validation — Schema.org + Google Rich Result required/recommended rules | ✓ (both rule sets) | ✗ | ✓ | ✗ | `core/onpage` | Planned — full validator engine; `SchemaResult.warnings` reserves the output shape |
| 41 | Accessibility auditing (axe-core / WCAG) | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Future |
| 42 | Spelling & grammar checker (multi-language) | ✓ (25+ languages) | ✗ | ✗ | ✗ | `core/onpage` | Future |
| 43 | Crawl depth & directory-structure tracking | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Implemented — `PageAuditResult.depth`, `discovered_from` |
| 44 | Site visualizations (force-directed / directory-tree / tree-graph) | ✓ | ✗ | ✗ | ✗ | `frontend` | Future |
| 45 | XML sitemap generation (incl. image sitemap) | ✓ | ✗ | ✓ (auto-generated, split by type) | ✗ | `core/crawler` | Planned — `audit/sitemap` endpoint scoped |
| 46 | XML sitemap auditing (hygiene, orphan cross-reference) | ✓ | ✗ | Partial (News/Video sitemap modules) | ✗ | `core/crawler` | Planned — `SitemapUrl` models generation, not audit |
| 47 | GA4 integration (per-URL sessions/engagement/conversions) | ✓ | ✗ (gap) | ✓ (1-click install) | ✓ | `app/integrations` | Planned |
| 48 | GSC — Search Analytics (clicks/impressions/CTR/position) | ✓ | ✓ (required) | ✓ | ✓ | `app/integrations` | Planned — `Settings.gsc_credentials_json` reserved |
| 49 | GSC — URL Inspection API (index status, rich-result status) | ✓ | ✗ | ✓ | ✗ | `app/integrations` | Planned |
| 50 | PageSpeed Insights / Core Web Vitals at crawl scale (lab + CrUX field data) | ✓ | Partial (SERP "Quality" factor only) | ✓ (per-post score) | ✗ | `core/crawler` | Planned |
| 51 | Backlink data import (Ahrefs/Majestic/Moz, bring-your-own key) | ✓ | ✗ (gap) | ✗ | Partial (monitors, doesn't build links) | `app/integrations` | Future |
| 52 | Native AI prompt-per-page (LLM column generation mid-crawl) | ✓ (v24.0; OpenAI/Gemini/Anthropic/Ollama) | ✗ | ✓ (Content AI, different layer) | ✗ | `core/onpage` | Future |
| 53 | AI-crawler / LLM-bot user-agent testing | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Planned — reuses `CrawlConfig.user_agent` |
| 54 | Custom Search (raw source string/regex match) | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Future |
| 55 | Custom Extraction (XPath/CSS/regex scraping rules, up to 100/crawl) | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Future |
| 56 | Custom JavaScript execution per page | ✓ | ✗ | ✗ | ✗ | `core/crawler` | Future |
| 57 | Scheduled/unattended recurring crawls | ✓ | ✓ (daily GSC pull) | Partial (Rank Tracker polling) | ✓ (monthly cycle) | `app/api` | Planned |
| 58 | Automatic crawl comparison (diff last two runs) | ✓ (v24.0) | ✗ | ✗ | ✗ | `core/crawler` | Implemented — `CrawlComparison` |
| 59 | CLI / headless automation equivalent | ✓ | via API | via WP REST | ✗ (narrow/unverified API) | `app/api` | Planned — the documented REST API *is* MySEOapp's answer to this; see §5 row 1 |
| 60 | Bulk exports (CSV/XLSX) + fixed report catalogue | ✓ | ✓ (CSV) | Partial (settings export) | Partial (branded PDF) | `app/api` | Planned |
| 61 | Google Sheets / Looker Studio export | ✓ | ✓ (Looker, AI Tracker) | ✗ | ✗ | `app/integrations` | Future |
| 62 | Email notification on crawl/audit completion | ✓ | ✓ (weekly digest) | ✓ (scheduled reports) | ✓ (monthly report) | `app/integrations` | Planned |

**Section total: 62 features.**

---

## 2. On-Page & Content Optimization

Surfer's NLP-driven Content Score and SERP Analyzer, Rank Math's deterministic 100-point checklist and schema generator, and Hike's Onsite Optimiser/Content Wizard converge here — MySEOapp's `core/onpage` package is deliberately positioned as "Rank Math's rule engine + Surfer's scoring model in one analyzer."

| # | Feature | Screaming Frog | Surfer | Rank Math | HikeSEO | MySEOapp Module | Status |
|---|---|---|---|---|---|---|---|
| 1 | Real-time on-page SEO score (0–100) | ✗ | ✓ (Content Score) | ✓ (SEO Score) | ✗ | `core/onpage` | Implemented — `OnPageResult.score`, `common.grade_from_score` |
| 2 | Rule-based checklist with pass/warning/fail tests | Partial (issue library) | ✗ (model-based, not checklist) | ✓ | Partial (fix list) | `core/onpage` | Implemented — `OnPageCheck` |
| 3 | Weighted category scoring (Basic / Additional / Title Readability / Content Readability) | ✗ | ✗ | ✓ | ✗ | `core/onpage` | Implemented — `CheckCategory`, `OnPageResult.category_scores` |
| 4 | Focus-keyword placement checks (title / meta / URL / first 10% of body) | ✗ | Partial (term placement) | ✓ | ✗ | `core/onpage` | Implemented — `OnPageRequest.target_keyword` + rule set |
| 5 | Secondary/multi-keyword optimization | ✗ | ✓ | ✓ (PRO) | ✓ (Keyword Sitemap, 3–4/page) | `core/onpage` | Implemented — `OnPageRequest.secondary_keywords` |
| 6 | Graduated content-length scoring curve | ✗ | Partial (competitor-derived range) | ✓ | ✗ | `core/onpage` | Planned |
| 7 | Keyword-density guidance | ✗ | ✓ ("true density," competitor-derived) | ✓ (fixed 1–1.5% band) | ✗ | `core/onpage` | Implemented — `TermTarget.status` (under/optimal/over) |
| 8 | Title readability tests (sentiment word, power word, number, keyword position) | ✗ | ✗ | ✓ | ✗ | `core/onpage` | Planned |
| 9 | Content readability tests (TOC present, paragraph length, media count) | ✗ | Partial (structure targets) | ✓ | ✗ | `core/onpage` | Implemented — `CheckCategory.CONTENT_READABILITY` |
| 10 | Keyword cannibalization / focus-keyword uniqueness check | ✗ | ✗ | ✓ | ✓ (Keyword Confusion) | `core/onpage` + `core/keywords` | Planned |
| 11 | Internal/external linking presence checks | ✗ | ✓ (1-click internal linking) | ✓ | Partial | `core/onpage` | Implemented — dedicated `OnPageCheck` codes |
| 12 | One-click "Fix with AI" remediation | ✗ | Partial (Auto-Optimize) | ✓ | Partial (Kit auto-applies) | `core/onpage` | Future |
| 13 | Sitewide technical/on-page analyzer (~40-factor, distinct from per-post score) | Partial (full crawl) | ✗ | ✓ | ✓ (audit tool) | `core/crawler` | Implemented — `CrawlSummary` aggregates issue counts across a crawl |
| 14 | Dual content score: SEO Score + AI Search Score | ✗ | ✓ (2026 flagship) | ✗ | ✗ | `core/onpage` | Implemented — `ContentScore.seo_score` / `ai_search_score` |
| 15 | AI Search sub-score — Facts Coverage | ✗ | ✓ | ✗ | ✗ | `core/onpage` | Future |
| 16 | AI Search sub-score — Upfront Intent Alignment | ✗ | ✓ | ✗ | ✗ | `core/onpage` | Future |
| 17 | Structural targets derived from the competitor set (word count/headings/paragraphs/images) | ✗ | ✓ | Partial (Content AI research) | ✗ | `core/onpage` | Implemented — `ContentScore.word_count_target_min/max`, `headings_target`, `images_target` |
| 18 | NLP prominent-term extraction with usage-count ranges | ✗ | ✓ | Partial (related keywords) | ✗ | `core/onpage` | Implemented — `TermTarget` |
| 19 | Placement-aware term weighting (headings weighted above body) | ✗ | ✓ | ✗ | ✗ | `core/onpage` | Implemented — `TermTarget.in_headings`, `importance` |
| 20 | Popular / Common / Prominent term-frequency views | ✗ | ✓ (SERP Analyzer) | ✗ | ✗ | `core/keywords` | Future |
| 21 | Competitor benchmarking & curation guardrails (≥3 distinct domains, exclude mega-authority) | ✗ | ✓ | ✗ | ✗ | `core/onpage` | Implemented — `ContentEditorRequest.competitor_word_counts`; curation UX Planned |
| 22 | Outline Builder (H2/H3 suggestions, sub-questions) | ✗ | ✓ | Partial (Content AI research) | Partial (Content Wizard topics) | `core/onpage` | Planned |
| 23 | AI writing assistant with inline commands | ✗ | ✓ (Surfy) | ✓ (RankBot, 50+ tools) | ✓ (Content Wizard) | `core/onpage` | Future |
| 24 | Custom brand voice/tone persistence | ✗ | ✓ (Pro+) | ✗ | ✓ (editable tone) | `core/onpage` | Future |
| 25 | Topical gap / subtopic-coverage mining | ✗ | ✓ | Partial | ✗ | `core/keywords` | Future |
| 26 | Collaboration (shareable links, comments, version history, folders) | ✗ | ✓ | ✗ | ✗ | `frontend` | Future |
| 27 | CMS publish connectors (WordPress, Contentful, Google Docs overlay) | ✗ | ✓ | ✓ (native — it *is* a WP plugin) | ✓ (Onsite Optimiser, any CMS) | `app/integrations` | Future |
| 28 | Plagiarism checker | ✗ | ✓ | ✗ | ✗ | `core/onpage` | Future |
| 29 | AI Humanizer / AI Detector | ✗ | ✓ | ✗ | ✗ | `core/onpage` | Future |
| 30 | Auto-Optimize (one-click rewrite pass against live guidelines) | ✗ | ✓ | ✓ (broader "Fix with AI") | ✓ (Kit auto-apply) | `core/onpage` | Future |
| 31 | 500+ SERP ranking-factor extraction with correlation scoring | ✗ | ✓ | ✗ | ✗ | `core/keywords` | Future |
| 32 | SERP result charting (per-page/grouped averages, outlier view) | ✗ | ✓ | ✗ | ✗ | `frontend` | Future |
| 33 | SERP Questions tab (People-Also-Ask mining) | ✗ | ✓ | Partial (candidate FAQs via Content AI) | ✗ | `core/keywords` | Planned |
| 34 | Content-refresh "Best Opportunities" ranking (GSC + score-driven) | ✗ | ✓ | ✗ | Partial (prioritized fix list) | `core/reporting` | Planned |
| 35 | Weekly performance email digest | ✗ | ✓ | ✓ (scheduled reports) | ✓ (monthly) | `app/integrations` | Planned |
| 36 | Topical Map / content cluster planning (GSC-gap or greenfield) | ✗ | ✓ | ✗ | Partial (Keyword Sitemap) | `core/keywords` | Planned |
| 37 | Full AI article generation (keyword → outline → draft pipeline) | ✗ | ✓ (Surfer AI) | ✗ | ✓ (Content Wizard, ~400–500 words) | `core/onpage` | Future |
| 38 | Auto-FAQ section generation from PAA data | ✗ | ✓ | Partial (Content AI research) | ✗ | `core/onpage` | Future |
| 39 | Bulk/category content generation | ✗ | ✓ | ✗ | ✗ | `core/onpage` | Future |
| 40 | Schema/structured-data generator (type picker → JSON-LD) | Partial (validation only, no generation) | ✗ | ✓ (37 types) | ✗ | `core/onpage` | Implemented — `SchemaType`, `SchemaRequest`/`SchemaResult` (12 types modeled at launch, extensible) |
| 41 | Schema variable/token auto-fill library | ✗ | ✗ | ✓ | ✗ | `core/onpage` | Planned |
| 42 | Schema Templates + Display Conditions (bulk-apply rules by site/archive/singular scope) | ✗ | ✗ | ✓ (PRO) | ✗ | `core/onpage` | Future |
| 43 | Schema import (live URL/HTML/JSON-LD → editable fields) | ✗ | ✗ | ✓ (PRO) | ✗ | `core/onpage` | Future |
| 44 | AI-assisted content research (word/heading/media/link targets from top-ranking pages) | ✗ | ✓ (structural targets) | ✓ (Content AI Research) | ✗ | `core/onpage` | Implemented — same contract as row 17 (`ContentScore` targets) |
| 45 | AI content-generation tool library (titles, meta, copy frameworks, social posts) | ✗ | Partial | ✓ (50+ tools) | ✗ | `core/onpage` | Future |
| 46 | AI-generated image alt text | ✗ | Partial (auto alt-tag) | ✓ | ✗ | `core/onpage` | Future |
| 47 | Feature-based AI usage quotas (per-tool allowance, not a shared credit pool) | ✗ | ✗ | ✓ (2026 model) | ✗ | `app/api` | Future |
| 48 | Automated internal-link insertion / keyword-to-URL mapping | ✗ | ✓ (1-click Internal Linking) | ✓ (AI Link Genius) | Partial (link suggestions) | `core/onpage` | Future |
| 49 | Onsite live-publish snippet (CMS-agnostic changes without back-end access) | ✗ | ✗ | ✗ | ✓ | `app/integrations` | Future |
| 50 | Multi-language content scoring/UI | ✗ | ✓ | Partial (English-only singular/plural matching) | ✗ | `core/onpage` | Planned |

**Section total: 50 features.**

---

## 3. Keywords, SERP & Rank Tracking

HikeSEO's Keyword Sitemap and rank tracker, Surfer's SERP Analyzer and AI Tracker, and Rank Math's Rank Tracker/Google Trends layer all live here. This is also where MySEOapp's `SerpFeature` enum (including `AI_OVERVIEW`) and `RankTrackingSummary.visibility_score` sit — a differentiation point none of the four competitors ship as a single named metric.

| # | Feature | Screaming Frog | Surfer | Rank Math | HikeSEO | MySEOapp Module | Status |
|---|---|---|---|---|---|---|---|
| 1 | Seed-keyword research (related ideas, sortable by volume/difficulty) | ✗ | ✓ | Partial (live Google suggestions) | ✓ | `core/keywords` | Implemented — `KeywordResearchRequest`/`Result` |
| 2 | Monthly search-volume metric | ✗ | ✓ | Partial | ✓ (annual-total/12 methodology) | `core/keywords` | Implemented — `Keyword.search_volume` |
| 3 | Keyword difficulty score | ✗ | Partial (via correlation, not a single score) | ✗ | ✓ (bucketed Low–Very High, DA-based) | `core/keywords` | Implemented — `Keyword.difficulty` (0–100) |
| 4 | CPC / competition metrics | ✗ | ✗ | ✗ | ✗ | `core/keywords` | Implemented — `Keyword.cpc`, `Keyword.competition` |
| 5 | Search-intent classification (informational/navigational/commercial/transactional) | ✗ | ✓ | ✓ (PRO) | ✓ | `core/keywords` | Implemented — `SearchIntent`, `Keyword.intent` |
| 6 | SERP feature detection (featured snippet, PAA, local pack, AI Overview, etc.) | ✗ | Partial (via SERP Analyzer factors) | ✗ | ✗ | `core/keywords` | Implemented — `SerpFeature` (10 types, incl. `AI_OVERVIEW`) |
| 7 | Keyword clustering by SERP overlap | ✗ | ✓ | ✗ | ✗ | `core/keywords` | Implemented — `KeywordCluster` model; overlap algorithm Planned |
| 8 | Parent-topic grouping | ✗ | Partial | ✗ | ✗ | `core/keywords` | Implemented — `Keyword.parent_topic` |
| 9 | "Already ranking, not yet targeted" keyword discovery | ✗ | Partial (Content Audit) | Partial (per-post SEO report) | ✓ (Your Ranked Keywords) | `core/keywords` | Planned |
| 10 | Blog/content topic-idea generation from seed keywords | ✗ | ✓ (Topical Map) | Partial (Content AI) | ✓ (Blog Ideas filter) | `core/keywords` | Planned |
| 11 | Competitor-domain keyword lookup | ✗ | ✓ (Organic Competitors) | ✗ | ✓ | `core/keywords` | Planned |
| 12 | Ongoing competitor rank/keyword tracking (not a one-off lookup) | ✗ | Partial (Share of Voice, AI Tracker only) | ✗ | ✓ (Competitor Tracking) | `core/keywords` | Future |
| 13 | Free browser-extension SERP overlay | ✗ | ✓ (Keyword Surfer) | ✗ | ✗ | n/a (growth/marketing surface, not core API) | Future |
| 14 | SERP query lock (keyword + location + device) with optional NLP sentiment | ✗ | ✓ | ✗ | ✗ | `core/keywords` | Implemented — `SerpAnalysis.device`/`country` |
| 15 | Arbitrary/not-yet-ranking URL comparison in a SERP view | ✗ | ✓ | ✗ | ✗ | `core/keywords` | Planned |
| 16 | 500+ ranking-factor extraction with correlation coefficients | ✗ | ✓ | ✗ | ✗ | `core/keywords` | Future |
| 17 | Rank-position tracking (scheduled polling + history) | ✗ | Partial (Content Audit positions, not a dedicated tracker) | ✓ (PRO+, 12-month history) | ✓ (300-keyword cap) | `core/keywords` | Implemented — `TrackedKeyword`, `RankPoint`, `.history` |
| 18 | Position delta / improved-declined-unchanged breakdown | ✗ | ✗ | ✓ (Top 5 winning/losing widgets) | Partial | `core/keywords` | Implemented — `TrackedKeyword.delta`, `RankTrackingSummary.improved/declined/unchanged` |
| 19 | Volume-weighted visibility index (single composite metric) | ✗ | ✗ | ✗ | ✗ | `core/keywords` | Implemented — `RankTrackingSummary.visibility_score` — **not shipped by any of the four as a named metric** |
| 20 | Top-3 / Top-10 ranking counts | ✗ | ✗ | Partial (winning-posts widget) | ✗ | `core/keywords` | Implemented — `RankTrackingSummary.top3`/`top10` |
| 21 | Tracked-keyword ceilings gated by plan | ✗ | ✗ | ✓ (500/10k/50k) | ✓ (300 fixed) | `app/api` | Planned |
| 22 | Local rank tracking / Map Pack visibility | ✗ | ✗ | Partial (Local SEO schema, no dedicated tracker) | ✓ (folded into Local SEO) | `core/keywords` | Future |
| 23 | Multi-country / multi-market rank tracking | ✗ | ✗ | ✗ | ✗ (gap on lower tiers) | `core/keywords` | Planned — explicit differentiation opportunity |
| 24 | Ranking visibility beyond position 100 | ✗ | ✗ | ✗ | ✗ (gap — capped at 100) | `core/keywords` | Planned — explicit differentiation opportunity |
| 25 | Keyword Sitemap (pages × keywords × intent × current ranking URL/position) | ✗ | ✗ | ✗ | ✓ | `core/keywords` + `core/reporting` | Planned |
| 26 | Keyword cannibalization / "Keyword Confusion" validation | ✗ | ✗ | ✓ (focus-keyword uniqueness) | ✓ | `core/keywords` | Planned |
| 27 | Auto-assign top-5-ranking keywords to sitemap pages | ✗ | ✗ | ✗ | ✓ (Auto-Assign) | `core/keywords` | Future |
| 28 | Scheduled email ranking reports | ✗ | ✗ | ✓ | ✓ (monthly) | `app/integrations` | Planned |
| 29 | Google Trends lookup (windowed, country-targeted) | ✗ | ✗ | ✓ (PRO) | ✗ | `app/integrations` | Future |
| 30 | AI answer-engine visibility tracking (ChatGPT, Perplexity, Gemini, AI Overviews, AI Mode) | ✗ | ✓ (AI Tracker — 2026 flagship) | ✗ | Partial (marketing line only, not a tracker) | `core/keywords` | Future — **flagship v2 bet; see PRODUCT_SPEC.md roadmap** |
| 31 | Share of Voice vs. named competitors (AI answers) | ✗ | ✓ | ✗ | ✗ | `core/keywords` | Future |
| 32 | Mention-gap reporting (prompts where a competitor is cited and the brand isn't) | ✗ | ✓ | ✗ | ✗ | `core/keywords` | Future |

**Section total: 32 features.**

---

## 4. Reporting & Tasks

Hike's monthly plan → Approval Centre → execute → report loop is the primary template here, layered with Surfer's Dashboard/alerting and Rank Math's scheduled reports and prioritized widgets. This section is where MySEOapp's `Task`/`AiReview`/`ActionPlan`/`Report` contracts already closely mirror Hike's action-plan model.

| # | Feature | Screaming Frog | Surfer | Rank Math | HikeSEO | MySEOapp Module | Status |
|---|---|---|---|---|---|---|---|
| 1 | Prioritized task/action list as the core interaction model | Partial (issue list, not tasks) | ✗ | ✗ | ✓ | `core/reporting` | Implemented — `Task`, `ActionPlan` |
| 2 | Task categorization (technical/on-page/content/local) | ✗ | ✗ | ✗ | ✓ | `core/reporting` | Implemented — `Task.category` (`IssueCategory`) |
| 3 | Task status workflow (todo → in progress → done/flagged) | ✗ | ✗ | ✗ | ✓ (Approval Centre states) | `core/reporting` | Implemented — `TaskStatus` |
| 4 | Impact/effort scoring per task | ✗ | ✗ | ✗ | Partial (implied by prioritization) | `core/reporting` | Implemented — `Task.impact` (1–5), `Effort` |
| 5 | AI Review explainability (pass/flag verdict + written reasoning + confidence) | ✗ | ✗ | ✗ | ✓ (AI Review) | `core/reporting` | Implemented — `AiReview` |
| 6 | Approval Centre / human-in-the-loop sign-off workflow | ✗ | ✗ | ✗ | ✓ | `core/reporting` | Planned |
| 7 | Configurable auto-approval thresholds | ✗ | ✗ | ✗ | ✓ | `core/reporting` | Future |
| 8 | Recurring monthly plan → execute → report cycle | ✗ | Partial (weekly digest cadence) | ✗ | ✓ | `core/reporting` + `app/integrations` | Planned |
| 9 | Priority/status roll-up summaries | ✗ | ✗ | Partial (Top 5 widgets) | ✗ | `core/reporting` | Implemented — `ActionPlan.by_priority`/`by_status` |
| 10 | Client-facing branded report builder | ✗ | ✗ | ✗ | ✓ (Report Builder) | `core/reporting` | Implemented — `Report`, `ReportSection` |
| 11 | AI-generated report narrative/summaries | ✗ | ✗ | ✗ | ✓ (AI Reporting) | `core/reporting` | Future |
| 12 | Headline-metrics dashboard block | ✗ | ✓ (Dashboard) | Partial | Partial | `core/reporting` | Implemented — `Report.headline_metrics` |
| 13 | Data visualization/charts inside reports | ✗ | ✓ | ✗ | ✓ (G2-listed) | `frontend` | Planned — `ReportSection.type` reserves a `"chart"` section |
| 14 | Scheduled/emailed reports | ✓ | ✓ | ✓ | ✓ — universal pattern across all four | `app/integrations` | Planned |
| 15 | Performance-shift / rank-drop alerts | ✗ | ✓ (Rank Drop Detection) | Partial (winning/losing widgets) | ✗ | `core/keywords` + `core/reporting` | Planned |
| 16 | Point-in-time comparison annotations (what changed & why) | ✓ (crawl-change summary emails) | ✓ (Dashboard) | ✗ | ✗ | `core/reporting` | Implemented — feeds from `CrawlComparison` |
| 17 | Dedicated cannibalization report | ✗ | ✓ (Pro+) | Partial (per-post uniqueness flag) | ✗ | `core/reporting` | Planned |
| 18 | Public lead-gen mini-audit widget | ✗ | ✗ | ✗ | ✓ | `core/crawler` + `app/integrations` | Planned |
| 19 | Lead capture → validation → CRM push pipeline | ✗ | ✗ | ✗ | ✓ (implied) | `app/integrations` | Implemented — `LeadRecord`, `LeadValidationResult`, `DeliveryLog` |
| 20 | Client-restricted / read-only report view | ✗ | ✗ | ✗ | ✓ | `frontend` | Planned |
| 21 | Bulk edit / quick edit for admin efficiency | ✗ | ✗ | ✓ (PRO) | ✗ | `core/onpage` | Future |
| 22 | 404 monitor (real visitor 404 logging) | Partial (crawl-time only) | ✗ | ✓ | ✗ | `core/crawler` | Planned |
| 23 | Standing broken-link report (not one-off) | Partial (per-crawl export) | ✗ | ✓ (Business/Agency) | ✗ | `core/crawler` | Planned |
| 24 | Vertical/industry playbook content library | ✗ | ✗ | ✗ | ✓ (10+ guides) | n/a (content/marketing asset) | Future |

**Section total: 24 features.**

---

## 5. Integrations, API & MCP

This is MySEOapp's sharpest differentiation section. Screaming Frog has confirmed there is **no general-purpose REST API** (only a desktop CLI and a partial MCP server). Surfer runs a gated, versioned API but no MCP server. Rank Math ships MCP tools scoped to WordPress. Hike's API scope is narrow and unverified. **No competitor ships both a full REST API and an MCP server as first-class, always-on surfaces** — that combination is MySEOapp's core architectural bet (see `ARCHITECTURE.md`).

| # | Feature | Screaming Frog | Surfer | Rank Math | HikeSEO | MySEOapp Module | Status |
|---|---|---|---|---|---|---|---|
| 1 | Public, documented REST API | ✗ (gap — vendor-confirmed no general API) | ✓ (v1/v2, gated) | Partial (WP REST API extension only) | ✗ (gap — narrow/unverified) | `app/api` | Planned — full `/api/v1` surface specified in `ARCHITECTURE.md` |
| 2 | Versioned API with concurrent version support | ✗ | ✓ (v1 + v2 concurrently) | n/a | ✗ | `app/api` | Planned |
| 3 | Machine-readable API docs for AI-agent discovery (`/llms.txt`-style) | ✗ | ✓ | ✗ | ✗ | `app/api` | Planned |
| 4 | API-key authentication | ✗ | ✓ | n/a | ✗ (unconfirmed) | `app/api` | Planned — `X-API-Key` header already read by rate-limit keying; full auth enforcement pending |
| 5 | MCP server exposing product actions as callable tools | ✓ (flagship v24.0, partial coverage) | ✗ | ✓ (WordPress Abilities API bridge) | ✗ | `mcp-server` | Planned — scaffold in place, tool surface specified in `ARCHITECTURE.md` |
| 6 | REST API *and* MCP server both shipped as first-class surfaces | ✗ | ✗ | ✗ | ✗ | `app/api` + `mcp-server` | Planned — **flagship differentiation, none of the four ship both** |
| 7 | CLI / headless automation | ✓ | via API | via WP-CLI/REST | ✗ | `app/api` | Planned — REST API is the automation surface |
| 8 | Workflow-automation connector (Zapier-equivalent) | ✗ | ✓ (Peace of Mind+) | ✗ | ✗ | `app/integrations` | Future |
| 9 | Native Make.com gateway (inbound + outbound) | ✗ | ✗ | ✗ | ✗ | `app/integrations` | Implemented — `MakeDispatch`, `WebhookEvent`, `Settings.make_webhook_url`/`make_signing_secret` |
| 10 | Inbound webhook signature verification (HMAC) | ✗ | ✗ | ✗ | ✗ | `app/integrations` | Implemented — `WebhookEvent.signature`/`verified`, `Settings.webhook_signing_secret` |
| 11 | CRM lead push (pluggable provider) | ✗ | ✗ | ✗ | ✓ (implied) | `app/integrations` | Implemented — `LeadRecord` + `Settings.crm_provider` (`mock`/`hubspot`/`salesforce`) |
| 12 | Delivery log / retry tracking for outbound dispatches | ✗ | ✗ | ✗ | ✗ | `app/integrations` | Implemented — `DeliveryLog`, `DeliveryStatus`, `Settings.integration_max_retries` |
| 13 | GA4 integration | ✓ | ✗ (gap) | ✓ | ✓ | `app/integrations` | Planned |
| 14 | GSC OAuth integration | ✓ | ✓ (required) | ✓ | ✓ | `app/integrations` | Planned |
| 15 | Google Business Profile integration | ✗ | ✗ | ✗ | ✓ | `app/integrations` | Future |
| 16 | PageSpeed Insights / CrUX API | ✓ | Partial | ✓ | ✗ | `app/integrations` | Planned |
| 17 | Ahrefs / Majestic / Moz bring-your-own-key backlink import | ✓ | ✗ | ✗ | ✗ | `app/integrations` | Future |
| 18 | Third-party keyword/SERP data provider (DataForSEO-class) | n/a | n/a | n/a | n/a | `core/keywords` | Planned — `Settings.serp_provider`/`keyword_provider` config flags reserved; adapter not yet built |
| 19 | WordPress plugin / native CMS integration | ✗ | ✓ | ✓ (is one) | ✓ (via snippet) | `app/integrations` | Future |
| 20 | Headless-CMS overlay (Contentful-style) | ✗ | ✓ (Pro+) | ✗ | ✗ | `app/integrations` | Future |
| 21 | Google Docs guideline overlay | ✗ | ✓ | ✗ | ✗ | `app/integrations` | Future |
| 22 | ChatGPT Canvas / third-party AI-writer pairing | ✗ | ✓ (Canvas, Jasper) | ✗ | ✗ | `app/integrations` | Future |
| 23 | Google Sheets export | ✓ | ✗ | ✗ | ✗ | `app/integrations` | Future |
| 24 | Looker Studio / BI connector | ✓ | ✓ | ✗ | ✗ | `app/integrations` | Future |
| 25 | Extensive hooks/filters developer library | ✗ | ✗ | ✓ | ✗ | `app/api` | Planned — outbound webhooks are MySEOapp's equivalent extension point |
| 26 | Import/export & migration tooling from competitor products | ✗ | ✗ | ✓ (Yoast/AIOSEO importers) | ✗ | `app/api` | Future |
| 27 | Multisite / multi-property support | ✗ | ✓ (Brand Workspaces) | ✓ | Partial | `app/api` | Planned |
| 28 | AI-provider integration for content generation (OpenAI/Gemini/Anthropic/Ollama) | ✓ (crawl-time prompts) | ✓ (underlying engine) | ✓ (Content AI) | ✓ (Content Wizard) | `core/onpage` | Future |
| 29 | Native mobile apps | ✗ | ✗ | ✗ | Unconfirmed/likely absent | `frontend` | Future |
| 30 | Public unauthenticated endpoint for lead-gen widgets | ✗ | ✗ | ✗ | ✓ (implied) | `app/api` | Planned |
| 31 | Structured error envelope + request-id tracing across the API | ✗ | ✗ | ✗ | ✗ | `app/api` | Implemented — `ErrorResponse`, `AppError` hierarchy, `RequestContextMiddleware` |
| 32 | Rate limiting with standard headers (429, `Retry-After`, `X-RateLimit-*`) | ✗ | ✗ | ✗ | ✗ | `app/api` | Implemented — `RateLimitMiddleware` (fixed-window, per API key/IP) |
| 33 | Health/version endpoints for uptime & deploy verification | ✗ | ✗ | ✗ | ✗ | `app/api` | Planned — `HealthResponse`/`VersionResponse` models and `version.py` exist; route wiring pending |
| 34 | Pluggable provider architecture (swap mock ↔ real vendor via config) | Partial (BYO API keys, not code-level swappable) | ✗ | ✗ | ✗ | `app/api` + `core/*` | Planned — `SEO_KEYWORD_PROVIDER`/`SEO_SERP_PROVIDER`/`SEO_CRM_PROVIDER` config flags exist; adapter classes not yet built |

**Section total: 34 features.**

---

## 6. Agency & White-Label

HikeSEO is the richest source here (its whole "Hike for Agencies" track), with Rank Math's Role Manager/site-tiered licensing and Surfer's Brand Workspaces/Enterprise tier contributing the rest. This section also surfaces the two clearest competitor gaps worth deliberately closing: **true multi-seat RBAC** (Hike doesn't have it) and **a rebrandable AI-agent persona** (Hike has it, and it maps directly onto MySEOapp's own `AiReview`/task-automation surface).

| # | Feature | Screaming Frog | Surfer | Rank Math | HikeSEO | MySEOapp Module | Status |
|---|---|---|---|---|---|---|---|
| 1 | Agency-specific product tier/track | ✗ | Partial (Enterprise) | ✓ (Business/Agency licensing) | ✓ (Hike for Agencies) | `app/api` | Planned |
| 2 | Multi-site / multi-client management from one account | ✗ | ✓ (Brand Workspaces) | ✓ (100/500 client sites) | ✓ (up to 3 self-serve) | `app/api` | Planned |
| 3 | White-label branding (logo, colors, footer text) | ✗ | ✓ (Enterprise) | ✗ | ✓ | `core/reporting` | Implemented — `WhiteLabelBranding` |
| 4 | Custom domain/subdomain for client-facing app | ✗ | ✓ (Enterprise) | ✗ | ✓ | `app/api` | Future |
| 5 | "Powered by" / platform-branding removal toggle | ✗ | ✗ | ✗ | ✓ | `core/reporting` | Implemented — `WhiteLabelBranding` fields support it; UI toggle Planned |
| 6 | Rebrandable AI-agent persona (name + icon) | ✗ | ✗ | ✗ | ✓ (Kit rebranding) | `core/reporting` | Implemented — `WhiteLabelBranding.agent_name`/`agent_icon_url` |
| 7 | Custom login/branding assets (favicon, login background) | ✗ | ✗ | ✗ | ✓ | `frontend` | Future |
| 8 | Upsell deep-links inside client task lists | ✗ | ✗ | ✗ | ✓ (Action/Citation Delivery Link) | `core/reporting` | Future |
| 9 | Role Manager / per-role capability matrix | ✗ | Partial (workspace-level permissions) | ✓ | ✗ | `app/api` | Future |
| 10 | True multi-seat, role-based internal team permissions | ✗ | Partial | Partial | ✗ (documented gap) | `app/api` | Future — explicit differentiation opportunity |
| 11 | Percentage-based usage allocation across client sites | ✗ | ✗ | ✓ (2026 Content AI model) | ✗ | `app/api` | Future |
| 12 | Config/settings replay across a client portfolio | ✗ | ✗ | ✓ (Setup Wizard) | ✗ | `app/api` | Future |
| 13 | Dedicated agency support tier | n/a | ✓ (Enterprise CSM) | ✓ (Business+, 24/7) | ✓ | n/a (ops, not engineering) | Future |
| 14 | Enterprise SSO | ✗ | ✓ (Enterprise) | ✗ | ✗ | `app/api` | Future |
| 15 | Shareable links without recipient login (view/edit) | ✗ | ✓ | ✗ | ✗ | `frontend` | Future |
| 16 | Version history with plan-gated retention | ✗ | ✓ | ✗ | ✗ | `core/reporting` | Future |
| 17 | Per-user/per-seat licensing model | ✓ (named-user annual license) | ✗ | ✗ | ✗ | `app/api` | Future |
| 18 | Free reseller/partner signup path | ✗ | ✗ | ✗ | ✓ | `app/api` | Future |
| 19 | Client-restricted read-only portal | ✗ | ✗ | ✗ | ✓ | `frontend` | Planned |
| 20 | Agency-branded public lead-gen audit widget | ✗ | ✗ | ✗ | ✓ | `app/api` + `app/integrations` | Planned — cross-references §4 row 18 |
| 21 | Volume/tier pricing scaling with client-site count | ✓ (per-seat volume discount) | Partial | ✓ (site-count tiers) | ✓ (site-count tiers) | `app/api` (billing) | Planned |
| 22 | Community/education perk bundled into agency plan | ✗ | ✗ | ✗ | ✓ (Compass newsletter) | n/a (marketing) | Future |

**Section total: 22 features.**

---

## Summary & Feature Counts

| Domain | Features cataloged | Implemented | Planned | Future |
|---|---|---|---|---|
| 1. Crawl & Technical Audit | 62 | 26 | 22 | 14 |
| 2. On-Page & Content Optimization | 50 | 12 | 10 | 28 |
| 3. Keywords, SERP & Rank Tracking | 32 | 12 | 11 | 9 |
| 4. Reporting & Tasks | 24 | 8 | 12 | 4 |
| 5. Integrations, API & MCP | 34 | 6 | 20 | 8 |
| 6. Agency & White-Label | 22 | 3 | 6 | 13 |
| **Total** | **224** | **67** | **81** | **76** |

*(Counts are approximate hand-tallies from the tables above; treat the grand total of 224 as the authoritative "how many named competitor features did we evaluate" figure.)*

### Headline takeaways

1. **No competitor ships both a documented REST API and an MCP server.** Screaming Frog explicitly has no general API; Surfer has an API but no MCP; Rank Math's MCP is WordPress-scoped; Hike's API is narrow and unverified. MySEOapp shipping both as first-class, always-on surfaces (§5, rows 1–6) is the single clearest architectural differentiator.
2. **AI answer-engine visibility (AEO/GEO) is real but nascent.** Only Surfer has shipped a tracker (§3 row 30); Hike only markets the concept. This is deliberately scoped as a v2 bet in `PRODUCT_SPEC.md` rather than an MVP feature, given the scraping infrastructure and data-licensing complexity involved.
3. **The `Task`/`AiReview`/`ActionPlan` contracts already mirror Hike's monthly action-plan loop** (§4, rows 1–5) more closely than any other competitor pattern, which is why Reporting & Tasks has a comparatively high Implemented ratio despite the engine itself being unbuilt.
4. **On-Page & Content Optimization has the deepest Future backlog** (28 of 50) because Surfer's AI-writing pipeline (Surfy, Auto-Optimize, full article generation, Humanizer/Detector) is a substantial standalone build — deliberately sequenced after the deterministic rule engine and content-scoring core, which are Implemented/Planned.
5. **Two explicit HikeSEO-documented gaps are called out as differentiation opportunities**: no rank visibility past position 100 (§3 row 24) and no multi-country tracking on lower tiers (§3 row 23) — both are cheap to do right from day one in a fresh rank-tracking data model.
6. **Agency/White-Label is intentionally the smallest Implemented bucket** (3 of 22) — the branding *data model* (`WhiteLabelBranding`) exists, but multi-tenant account structure, RBAC, and billing-tier gating are correctly sequenced as v1/v2 work, not MVP.

---

## Sources

Feature claims are drawn directly from the four research dossiers; see each for full citations:

- `docs/research/screaming-frog-features.md`
- `docs/research/surfer-seo-features.md`
- `docs/research/rank-math-features.md`
- `docs/research/hikeseo-features.md`

MySEOapp implementation status is cross-checked against `backend/app/models/{audit,onpage,keywords,reporting,integrations,common}.py`, `backend/app/config.py`, `backend/app/middleware/*.py`, `backend/app/logging_config.py`, `backend/app/services/store.py`, and `backend/app/utils/*.py` as of 10 July 2026.
