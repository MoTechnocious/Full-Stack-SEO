# Rank Math SEO — Feature Inventory (2026)

Compiled July 2026 from rankmath.com (product pages, pricing page, and knowledge-base articles fetched directly) plus corroborating secondary sources. Rank Math is a WordPress SEO plugin (free on WordPress.org as "Rank Math SEO," `seo-by-rank-math`) with a paid PRO add-on and a separately metered Content AI subscription. This document exists to catalog what the product actually does, in enough functional detail to inform an independent web-app implementation — not to reproduce Rank Math's marketing copy.

## 1. Overview and Product Architecture

- Distributed as a lean "core" plugin plus roughly 30 independently toggleable **modules** (`Rank Math SEO → Dashboard → Modules`) — Sitemap, Schema, Local SEO, WooCommerce SEO, Easy Digital Downloads SEO, Redirections, 404 Monitor, Role Manager, Link Counter, Image SEO, News Sitemap, Video Sitemap, AMP, bbPress, BuddyPress, Instant Indexing, Web Stories, Analytics (Search Console/GA4/Rank Tracker), Content AI, AI Visibility, and others. A site only runs code for modules it enables.
- Licensing tiers: **Free** (WordPress.org plugin) → **PRO** → **Business** → **Agency**, sold separately from a **Content AI** subscription (Starter/Creator/Expert). Two newer 2026 add-ons — **AI Visibility** and **AI Link Genius** — are billed under the same account.
- Works inside both the classic metabox and the Gutenberg sidebar/toolbar, plus dedicated integrations for Elementor and Divi.
- One-click migration importers exist for Yoast SEO (free & premium) and All in One SEO, mapping their data into Rank Math's own model.

## 2. On-Page SEO Analysis and the 100-Point Score

### 2.1 How the score is computed
- Every post/page/CPT gets a live **0–100 SEO Score** while editing, color-banded as Red (<50), Yellow (51–80), Green (81–100); vendor guidance treats 81+ as publish-ready.
- Tests are grouped into four categories, each contributing to the total: **Basic SEO**, **Additional SEO**, **Title Readability**, **Content Readability**.
- Individual tests render as pass / warning / fail; a few (content length, keyword density, media count) are **graduated/partial-credit** rather than binary.
- Marketing copy describes the underlying engine as checking "40 SEO factors"; the publicly documented per-post checklist totals roughly two dozen distinct tests (a separate, larger sitewide audit also exists — see 2.8). Some tests are skipped entirely for WooCommerce/Easy Digital Downloads product pages.
- The score can legitimately differ between the native block editor and a page builder like Elementor/Divi because shortcodes render differently; Rank Math tells users to trust whichever score is shown inside the tool they're actually editing in.

### 2.2 Focus keyword model
- Content has one **Primary Focus Keyword** plus optional **Secondary Focus Keywords**. Free is limited to a single focus keyword per post; PRO allows multiple/unlimited focus keywords per post.
- Keyword suggestions are pulled live from Google once the install is connected to a Rank Math account.
- PRO layers on **Google Trends** lookups (7-day–12-month window, country-targeted) and a **Search Intent** label (e.g., commercial, informational) shown beside the primary keyword.
- Each test is scoped to a specific keyword set: some run against every focus keyword, some only the primary, some only secondary keywords, and some ignore keywords altogether and just judge content mechanics.

### 2.3 Basic SEO tests
1. **Focus keyword in the SEO title** — primary keyword only; must land inside roughly the first 50 characters of the title (Google's ~60-char desktop display budget).
2. **Focus keyword in the meta description** — primary keyword only, expected within a 120–160 character description. If no custom description is set, Rank Math auto-builds one from, in priority order: custom meta description → configured description template → post excerpt → first paragraph containing the keyword → first paragraph of the post.
3. **Focus keyword in the URL/slug** — primary keyword only; the test is skipped entirely on sites still using plain/numeric permalinks.
4. **Focus keyword at the start of the content** — must appear within the first 10% of the post, or anywhere in the first 300 words for posts shorter than 300 words.
5. **Focus keyword present in the body** — runs across *all* focus keywords, with singular/plural matching (English only).
6. **Overall content length** — graduated: 2500+ words = 100%, 2000–2500 = 70%, 1500–2000 = 60%, 1000–1500 = 40%, 600–1000 = 20%, <600 = 0%. Product pages are exempt from this curve (PRO instead recommends roughly 200 words for WooCommerce/EDD products). When Content AI is active, the target word count is replaced by Content AI's own recommendation for that keyword.
7. **Product Schema present** — PRO only, WooCommerce/EDD products only.

### 2.4 Additional SEO tests
1. **Focus keyword in subheadings** (H2/H3, etc.) — runs for both primary and secondary keywords.
2. **Focus keyword in image ALT text** — primary keyword only, singular/plural match.
3. **Keyword density** — target 1–1.5%, warning above ~2.5%; computed across primary + secondary keywords and their combinations.
4. **URL length** — target ≤75 characters, measuring the entire URL (protocol, domain, and slug).
5. **Linking to external sources** — at least one outbound link.
6. **At least one followed (non-nofollow) external link** — depends on passing test 5 first; site-wide auto-nofollow behavior can be scoped with per-domain whitelist/blacklist lists.
7. **Linking to internal resources** — links to other posts, other subdomains, or the root domain all qualify.
8. **Focus keyword uniqueness** — flags when the same primary keyword already anchors another post (a cannibalization check), linking directly to the conflicting posts so they can be merged, deleted-and-redirected, or re-targeted.
9. **Content AI used to optimize the post** — rewards using Content AI's own recommendations instead of the generic thresholds above.
10. **Product reviews enabled** — PRO only, WooCommerce/EDD only.

### 2.5 Title readability tests
1. Focus keyword within the first 50% of the SEO title.
2. A positive or negative **sentiment word** present (internal word list).
3. A **"power word"** present (internal curated list).
4. A **number** present in the title.

### 2.6 Content readability tests
1. **Table of contents present** — recognizes Rank Math's own TOC block plus roughly ten third-party TOC plugins; developers can register additional plugins via a filter hook.
2. **No paragraph over 120 words** — offending paragraphs are highlighted, with a "Shorten with AI" one-click fix.
3. **At least one image or video** — partial credit for one, full credit requires 4+ media items.

### 2.7 AI-assisted fixing
Failing tests can show a **"Fix with AI"** (or "Shorten with AI") button that calls Content AI to rewrite the specific offending element — title, paragraph, ALT text, keyword placement — without the user leaving the editor.

### 2.8 Sitewide SEO Analyzer (distinct from the per-post score)
A separate **SEO Analysis** tool (`Status & Tools`, and also published as a free public web tool at rankmath.com/tools/seo-analyzer/) crawls an entire site and scores it against roughly 40 technical/on-page factors (titles, meta, sitemap health, indexability, ALT-text coverage, etc.), producing a prioritized issue list rather than a single content score.

## 3. Schema / Structured Data

### 3.1 Schema Generator
- A point-and-click generator lives in the block-editor sidebar and the Classic Editor metabox's "Schema" tab — no external plugin required.
- A **default schema type** can be set globally per post type (`Titles & Meta → [post type] → Schema Type`) and then overridden per individual post; "None" is a valid default so specific templates can ship schema-free.

### 3.2 Supported schema types (counted directly from the live product docs)
**Free (28 types)** — grouped for readability:
- Content/media: Article, BlogPosting, Book, Course, Event, FAQPage, HowTo, JobPosting, Music, Person, Recipe, Restaurant, Service, SoftwareApplication, Video
- Commerce: Product, WooCommerce product schema, Easy Digital Downloads product schema
- Site structure (mostly auto-applied): WebPage, WebSite, Person-or-Organization, ProfilePage, BreadcrumbList, CollectionPage, SiteNavigationElement, SitelinksSearchBox, NewsArticle, and Local Business (via the Local SEO module)

**PRO-only (9 additional types):** Dataset, FactCheck (ClaimReview), Movie, PodcastEpisode, About & Mentions, ItemList, Carousel, Q&A Page (auto-applied to resolved bbPress topics), Speakable.

Note: marketing pages elsewhere round this total differently ("20+", "23+"); the count above is a direct enumeration from Rank Math's own schema documentation as fetched for this report. Also note several individual rich-result types (FAQ, HowTo, Course Info, Claim Review, Sitelinks Search Box) have had Google rich-result eligibility reduced or deprecated over time even though Rank Math still emits the underlying markup — schema is increasingly framed as useful for AI/LLM content understanding, not only classic SERP rich snippets.

### 3.3 Variables
A large token library — grouped as Basic, Advanced, Post, Term, Author, WooCommerce, and BuddyPress — such as `%title%`, `%excerpt%`, `%focuskw%`, `%wc_price%`, `%date%`, `%currentyear%`, `%customfield(name)%` — lets a single schema or meta template auto-populate per post instead of manual per-page entry.

### 3.4 Schema Templates & Display Conditions (PRO)
- Any schema configuration can be saved as a reusable, named **Template** in its own admin screen (bulk edit, search, trash — modeled like the post list).
- Templates attach to content via **Display Conditions**: Include / Exclude / Insert (extend an already-existing schema graph with extra properties), each targeting Entire Site, Archives (by category, tag, author, CPT archive, etc.), or Singular content (post/page/CPT), with further sub-filters down to individual categories or posts. Rules stack, and Exclude + Singular/Archive rules take priority over Include/Entire-site rules.
- Multiple schema graphs can be attached to one URL (e.g., Article + FAQ + Breadcrumb together); Carousel schema is auto-added when Rank Math detects repeated same-type schema stacked on one page.

### 3.5 Import & Custom Schema (PRO)
- **Import** schema from a live URL, pasted HTML, or pasted JSON-LD — auto-parsed into editable fields, then usable as a one-off addition or saved as a template.
- **Custom Schema Builder**: a freeform property/property-group editor for any schema.org type not natively modeled among the ~37 built-in types.
- **Advanced Schema Editor**: a lower-level editing layer over both generated and custom schema.
- **Code validation** against Google's Rich Results test, run inline inside wp-admin.

## 4. Sitemaps, Meta Robots, Breadcrumbs, Canonical

### 4.1 XML sitemaps
Auto-generated and auto-updating XML sitemap index, split by post type/taxonomy, with images included by default and per-post-type include/exclude toggles. **News Sitemap** and **Video Sitemap** are separate opt-in modules (both free) aimed at Google News and video search inclusion rather than general web indexing.

### 4.2 Robots meta / indexing controls
- Global default robots meta (index/noindex, follow/nofollow, plus advanced directives like `max-snippet`, `max-image-preview`, `max-video-preview`) configurable per post type, taxonomy, and archive (author, date, search results).
- Per-post override inside the editor; PRO adds **bulk edit** (mark many posts index/noindex/nofollow, remove canonical, add/remove redirects, change schema type, all at once) and inline **Quick Edit** fields directly in the post list table.
- Built-in **robots.txt editor** and **.htaccess editor** inside wp-admin, with automatic .htaccess backup before any save.

### 4.3 Canonical URLs
Auto-canonical applied to every URL by default, manually overridable per post/page, and bulk-removable through PRO's bulk editor.

### 4.4 Breadcrumbs
Theme-agnostic breadcrumb trail (shortcode + PHP function + automatic injection into many themes) paired with matching `BreadcrumbList` schema; separator characters, labels, and primary-category logic are all configurable.

## 5. Redirections Manager and 404 Monitor

### 5.1 Redirection manager
- Spreadsheet-style UI supporting standard HTTP redirects (301/302/307) plus "Gone" (410) and "Unavailable for Legal Reasons" (451) status responses for content that should stay removed rather than redirect.
- Match types: **Exact, Contains, Starts With, Ends With, and Regex** — regex enables one rule to redirect many source URLs matching a pattern (e.g., an entire retired category structure).
- Built-in helpers: redirect media attachment pages to their parent post, and strip the `/category/` base from URLs.
- Import/export redirects as an `.htaccess` file or an Nginx config snippet, alongside general import/export of the rest of Rank Math's settings.
- A redirect can be created from three different entry points that all write to the same table: the Redirections screen, the 404 Monitor screen, and directly from the post editor.

### 5.2 404 Monitor
- Logs real visitor 404s in **Simple** mode (URL + timestamp) or **Advanced** mode (adds referring URL and user agent).
- **Exclude Paths** filtering (Exact/Contains/Starts With/Ends With/Regex) keeps known-noise requests (bot probes, intentionally-missing paths) out of the log.
- PRO's Business/Agency tiers add an automated **Broken Link Checker** (scans internal and external links across the site for dead targets) — a 2026 addition layered on top of the manual/reactive 404 monitor, alongside a companion **Automated Keyword Linking** tool for building keyword → URL maps.

## 6. Local SEO, Knowledge Graph, WooCommerce SEO, News/Video Sitemaps

### 6.1 Local SEO module
Stores business NAP data, hours, geo-coordinates, price range, and social profiles; emits `LocalBusiness` (or a more specific subtype) schema plus `WebSite`/Person-or-Organization schema. Ships a shortcode and a Gutenberg block for printing contact info anywhere on the site so it always matches the stored settings. PRO adds **multiple physical locations**, each with independent schema/markup, for multi-location businesses.

### 6.2 Google Knowledge Graph
A "Person or Organization" toggle plus logo/name/`sameAs` (social profile) fields feed the `WebSite`/`Organization` schema Google can use to build a Knowledge Panel for the site or its owner.

### 6.3 WooCommerce / Easy Digital Downloads SEO
- Auto-detects WooCommerce or EDD and generates Product schema straight from live store data (price, stock/availability, SKU, ratings) so schema never drifts out of sync with inventory.
- **Global Identifier** support (GTIN-8/12/13, MPN, ISBN), settable per product and per product variation.
- Custom or global **Brand** field feeds the `product:brand` tag / schema brand property.
- Auto-noindexes hidden products; can strip the `/product/` and `/product-category/` URL base.
- Advanced Open Graph tags on product pages; PRO adds a review-prompt SEO test and swaps the generic word-count curve for a ~200-word product-page bar (see 2.3).

### 6.4 News & Video sitemaps
Covered in 4.1 — both are dedicated opt-in modules distinct from the general XML sitemap, aimed at Google News and video search inclusion.

## 7. Rank Tracker, Search Console & Analytics Integration

- **Google Search Console** connects directly into wp-admin: indexing status, sitemap status, and per-keyword impressions/clicks surface without leaving WordPress.
- **Google Index Status** pulls Google's URL Inspection API per URL (last crawl time, coverage state).
- **Google Analytics (GA4)** connects via a one-click script install — no manual gtag/GTM editing.
- **Rank Tracker** (PRO/Business/Agency only) polls Google for ranking position against a defined keyword list, stores **position history** (dashboard shows up to a trailing 12 months), and surfaces "Top 5 winning/losing posts" and "Top 5 winning/losing keywords" widgets.
- A **per-post SEO report** shows which keywords a specific URL ranks for, its PageSpeed score, and historical performance, without leaving the post list view.
- Tracked-keyword ceilings are the main plan-gated quota (see Pricing, section 11) — the analysis itself isn't feature-gated, only its scale.
- Scheduled **email ranking reports** can be sent to the site owner.

## 8. Content AI

### 8.1 What it does
Content AI is a connected (SaaS-backed, requires a rankmath.com account) writing/optimization layer with three broad areas:
- **Research** — pulls signals from top-ranking pages for a target keyword to recommend word count, heading count, media count, link count, related keywords, and candidate FAQs.
- **Write** — a library of 50+ purpose-built generation tools (SEO title, meta description, blog intro/outro, product description, email, tweet, copywriting frameworks like AIDA/PAS/BAB/HERO/SPIN, etc.), a general-purpose "AI Command" prompt tool, and a "RankBot" chat assistant.
- **Images** — AI-generated ALT text for images missing it.
- **"Fix with AI"** wires Content AI directly into failing on-page tests (section 2.7) so a specific test can be resolved without manually rewriting anything.

### 8.2 Consumption model — changed in 2026
- **Old model** (pre Rank Math SEO v1.0.269 / PRO v3.0.112): a shared monthly credit pool, roughly 1 credit ≈ 1 generated word, with flat costs for some actions (a research run = 500 credits, a link suggestion = 100, an image ALT text = 50). Free users got 750 credits/month; paid tiers were Starter 5,000, Creator 12,000, and Expert 30,000 credits/month. Unused credits did not roll over.
- **Current model (2026): feature-based usage.** Every individual AI tool now has its own separate monthly allowance instead of drawing from one shared pool — e.g., the Creator plan includes 30 Research runs/month and 500 "Write" actions/month independently, so a heavy research session no longer starves the writing tools. Most generation tools are unlimited on the Expert plan; a representative sample of allowances:

  | AI Feature | Starter | Creator | Expert |
  |---|---|---|---|
  | Fix SEO Tests | 500 | 1,000 | Unlimited |
  | Research | 10 | 30 | 100 |
  | Image Alt Text | 50 | 100 | 500 |
  | Write (general) | 100 | 500 | Unlimited |
  | Bulk SEO Meta | 100 | 500 | Unlimited |
  | Long-Form Content | 15 | 60 | Unlimited |
  | Link/Related-post suggestions | 50 | 200 | 1,000 |
  | Most single-shot writing tools (SEO title/description, social posts, frameworks, etc.) | 100 | 500 | Unlimited |

  Free-plan users get a small trial allotment (about 1 use per feature). Allowances reset monthly, do not roll over, and failed/unsuccessful generations are not charged against the quota.
- **Business/Agency** license holders can split their Content AI allowance across managed client sites using a **percentage-based allocation** (replacing the older fixed-credits-per-site assignment).
- A related 2026 add-on, **AI Link Genius**, automates internal-link insertion (with a companion **Automated Keyword Linking** keyword-to-URL mapping tool), billed under the same feature-based model.

## 9. Modules, Role Manager, Link Counter, Image SEO, Social, Site Audit

### 9.1 Modules architecture
Recap of section 1: roughly 30 independently toggleable modules let a site run only the code it needs (`Dashboard → Modules`). This is the mechanism behind Rank Math positioning itself as a single plugin that replaces many single-purpose ones (schema plugin, redirect plugin, local-SEO plugin, sitemap plugin, etc.).

### 9.2 Role Manager
A per-WordPress-role capability matrix (Administrator, Editor, Author, Contributor, Subscriber, and any custom roles) controlling which Rank Math screens and settings groups (General Settings, Titles & Meta, Schema, Redirections, etc.) each role can see or edit. This is how an agency gives a client limited access without granting full admin rights.

### 9.3 Link Counter
A background module that counts internal and external links per post/page and surfaces the counts in the content list, supporting the internal-linking tests (2.4) and general link-audit workflows. Vendor documentation notes this module (and Analytics) accumulate database rows over time and may need periodic cleanup on large, long-running sites.

### 9.4 Image SEO
- **Free**: automatically adds missing ALT/title attributes to images at render time, without rewriting stored post content.
- **PRO ("Advanced Image SEO")**: bulk-overwrites ALT/title/captions using variable-based templates, with find/replace-style overwrite conditions.

### 9.5 Social / OpenGraph / Twitter Cards
Automatic Facebook Open Graph and Twitter Card tags on every post, with a live social-preview editor inside wp-admin, default/fallback share images, Facebook authorship tags, and one-click verification for Google/Bing/Yandex/Pinterest/etc. PRO adds watermarking of shared images and a play-button/GIF overlay on video thumbnails intended to lift social click-through rate.

### 9.6 SEO Analyzer (sitewide audit)
Covered in 2.8 — a distinct sitewide/technical scan, also published as a free standalone web tool, separate from the per-post score described in section 2.

## 10. Developer Surface

### 10.1 REST API
Rank Math's data (SEO meta, schema, redirects, focus keywords, scores) is reachable primarily through the standard **WordPress REST API** surface that Rank Math extends/hooks into, rather than via one large bespoke REST namespace of its own. A dedicated **Content Analysis API** exposes two filters so theme/plugin developers can feed custom title/content strings into Rank Math's own analyzer — useful for headless WordPress or non-standard editors.

### 10.2 Hooks & filters
An extensive, categorized action/filter library, documented by category as: Settings, Admin, Frontend, Breadcrumbs, Meta Data, OpenGraph, Rich Snippets, SEO Score, Redirections, Sitemap, Podcast, and Misc. These let third-party code override or extend nearly any output — for example, a filter lets another plugin register itself as a recognized "Table of Contents" plugin for test 2.6.1. Vendor guidance recommends isolating custom filters in a dedicated `rank-math.php` file rather than a theme's `functions.php`, so the customizations survive a theme change.

### 10.3 MCP Tools (new in 2026)
Rank Math ships a **Model Context Protocol (MCP)** bridge built on the WordPress Abilities API (using the `wordpress/mcp-adapter` library), exposing a live MCP endpoint on the site's own domain. Documented tools include: running a full SEO audit, auto-fixing failed SEO tests, and reading a post's complete SEO meta (title, description, focus keyword, robots settings, canonical URL, OpenGraph/Twitter data, SEO score). It's designed to be driven by Claude Desktop, Claude Code, Cursor, Claude.ai, or ChatGPT via an Application-Password-authenticated proxy — a concrete, shipping precedent for exposing SEO tooling to AI agents over MCP.

### 10.4 Import / export
- One-click export of settings and redirects (including `.htaccess`/Nginx redirect export), importable on another install.
- One-click migration importers from Yoast SEO (free & premium) and All in One SEO.
- A **Custom Setup Wizard** mode replays one site's Rank Math configuration onto another — useful for agencies standardizing settings across a portfolio of sites.

### 10.5 Multisite
Vendor describes Rank Math as "multisite ready," working on both single installs and full WordPress network installs. Business/Agency plans are licensed by number of **client sites** managed from one account, which is a separate axis from WordPress multisite networking.

## 11. Plans, Pricing, and Limits

Fetched directly from rankmath.com/pricing (July 2026). Prices on that page are geo/currency-localized (this fetch returned EUR, ex-VAT) and carry rotating promotional discounts off a stated renewal price — treat the figures below as illustrative of relative tier sizing rather than fixed USD list prices, since third-party review sites reported different USD numbers at different points in 2026.

| Tier | Site licensing | Tracked keywords (Rank Tracker) | Content AI trial included | Notable extras |
|---|---|---|---|---|
| **Free** (WordPress.org plugin) | Unlimited sites, no license needed | None (no built-in tracker) | Small trial allotment (~1 use/feature) | 1 focus keyword/post, 28 schema types, redirects + 404 monitor, GSC + GA4 connection, ~24 on-page tests, most modules |
| **PRO** | Unlimited *personal/owned* websites (client sites excluded) | 500 | Starter plan trial | Schema templates/import/custom builder, multi-keyword optimization, AI Link Genius, Broken Link Checker, Automated Keyword Linking |
| **Business** ("Most Popular") | 100 client websites | 10,000 | Creator plan trial | Everything in PRO + client-site management, 24/7 priority support |
| **Agency** | 500 client websites | 50,000 | Expert plan trial | Everything in Business at agency-scale ceilings |

Content AI is sold/consumed separately from the SEO-plugin tiers above (Starter / Creator / Expert), using the 2026 feature-based usage limits detailed in section 8.2. The "trial" bundled into each SEO-plugin tier is time-boxed (roughly 15–30 days), not a permanent inclusion — after the trial, Content AI is its own recurring purchase.

## 12. What's Directly Relevant to Replicate in a Web App

Rank Math is a WordPress plugin, so most of its *implementation* is WordPress-specific — but its *design decisions* generalize cleanly to a standalone web app:

- **On-page scoring engine (section 2).** The score is a deterministic, rule-based checklist, not an LLM judgment call — that's what makes it fast, explainable, and reproducible. Every rule is implementable against a plain `(title, meta_description, url, body_html, focus_keyword[s])` input tuple with no WordPress dependency. The graduated/partial-credit rules (content length curve, 1–1.5% keyword-density band, 4-image media threshold) are the trickiest part to get right and matter more to perceived score quality than the binary pass/fail rules — worth copying faithfully rather than approximating.
- **Schema generator (section 3).** The reusable pattern is *type picker → structured field form → variable-token autofill*, not hand-written JSON-LD. Display Conditions (Include/Exclude/Insert against Site/Archive/Singular scopes) is the automation layer worth adopting for any multi-page or bulk-content tool. Schema import (parse a live URL/HTML/JSON-LD back into editable fields) is a nice differentiator, not a core requirement.
- **Redirections + 404 monitor (section 5).** The clean part of this design is the shared data model: one match-type taxonomy (Exact/Contains/Starts/Ends/Regex) and one redirect table feeding both a manual redirect manager and an automatic 404 log, with three UI entry points writing to the same table.
- **Rank tracker (section 7).** The mechanic is simply *keyword list × scheduled SERP-position fetch × time-series storage*, gated by a per-plan keyword quota. Straightforward to replicate as a scheduled job plus a time-series table — the hard part is sourcing reliable SERP position data, not the storage/UI layer.
- **Content AI (section 8).** The 2026 shift from a shared word-credit pool to **per-feature usage counters** is a monetization/UX lesson worth adopting directly: it prevents one heavy action (e.g., a bulk research run) from silently exhausting a user's budget for unrelated tools, and it makes usage limits legible to the user at a glance.
- **REST API / hooks / MCP (section 10).** Rank Math's own move to expose an MCP server (audit, fix-failed-tests, get-post-SEO-meta tools) over the WordPress Abilities API is a concrete, shipping precedent for wrapping a product's core SEO actions as MCP tools — directly applicable to a project that plans its own MCP server surface.

## Sources

- https://rankmath.com/
- https://rankmath.com/wordpress/plugin/seo-suite/
- https://rankmath.com/pricing/
- https://rankmath.com/free-vs-pro/
- https://rankmath.com/kb/score-100-in-tests/
- https://rankmath.com/kb/rich-snippets/
- https://rankmath.com/kb/content-ai-credits-migration/
- https://rankmath.com/content-ai/
- https://rankmath.com/ai-visibility/
- https://rankmath.com/ai-link-genius/
- https://rankmath.com/kb/managing-modules/
- https://rankmath.com/kb/role-manager/
- https://rankmath.com/kb/analytics/
- https://rankmath.com/kb/how-to-use-regex-redirects/
- https://rankmath.com/kb/monitor-404-errors/
- https://rankmath.com/kb/setting-up-redirections/
- https://rankmath.com/kb/woocommerce-seo-feature-comparison/
- https://rankmath.com/kb/gtin-mpn-woocommerce/
- https://rankmath.com/kb/woocommerce-custom-brand-schema/
- https://rankmath.com/kb/filters-hooks-api-developer/
- https://rankmath.com/docs/filters-and-hooks/
- https://rankmath.com/kb/content-analysis-api/
- https://rankmath.com/kb/mcp-tools/
- https://gauravtiwari.org/rank-math-mcp-server/
- https://wordpress.org/plugins/seo-by-rank-math/
