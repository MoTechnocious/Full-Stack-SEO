# Screaming Frog SEO Spider — Feature Inventory (2026)

*Research date: 10 July 2026. Compiled from screamingfrog.co.uk (product, pricing, blog/changelog, tutorials, issue library) and independent SEO publications. Version references below reflect the SEO Spider desktop application, currently on the v24 line.*

## 1. Product Snapshot

- **Vendor**: Screaming Frog Ltd, Henley-on-Thames, UK.
- **Current version**: 24.3 (shipped 29 June 2026). The 24.x line began with the "bolus" release (v24.0) on 19 May 2026, followed by maintenance updates 24.1 (8 June), 24.2 (22 June), and 24.3.
- **Product type**: a locally-installed desktop crawler, not a SaaS product. It talks to remote APIs (Google, Ahrefs, AI providers, etc.) but the crawling engine itself runs on the user's own machine.
- **Platforms**: Windows, macOS (separate Apple Silicon and Intel builds), and Linux (Ubuntu `.deb` for amd64 and arm64, Fedora `.rpm` for x86_64 and aarch64 — Arm64 Linux builds were only added in v24.0).
- **Runtime**: Java-based application; the 24.x line runs on Java 25.
- **Sibling product**: the **Log File Analyser** is sold and licensed separately, though the two are designed to interoperate (crawl data can be dragged into the Log File Analyser to blend with server-log data, and both now support verifying/analysing AI-bot traffic).
- **Positioning**: marketed as identifying 300+ discrete SEO issues, warnings, and opportunities per crawl, each labelled with an issue type and an estimated priority so findings can be triaged.

## 2. Core Crawling

### What it crawls
The spider discovers pages the way a search engine crawler does: it requests a seed URL, parses the returned HTML (or rendered DOM, if JavaScript rendering is enabled) for hyperlinks, and follows them outward in a breadth-first pattern. It captures the raw HTTP response, headers, and page content for every URL it touches, plus referenced resources (CSS, JS, images, PDFs, etc.).

### Crawl modes
- **Spider mode** — the default mode. Point it at a domain or subfolder and it discovers the site organically by following links, uncovering pages that weren't explicitly listed anywhere.
- **List mode** — upload or paste a fixed set of URLs (e.g., a GSC export, a CMS database dump, a client's URL list). Crawl depth is automatically pinned to 0 so only the supplied URLs are checked — no further discovery — which makes it well suited to migration audits, redirect-mapping validation, or spot-checking a known page set.
- **SERP mode** — not really a "crawl" at all: you paste in page titles and meta descriptions and the tool renders them as search-result snippets, calculating pixel width and character length per device so you can validate copy before it goes live.
- A third input option, **crawling from an XML Sitemap**, lets the sitemap itself act as the URL source, either as a standalone check or merged into a normal crawl.

### Crawl configuration & limits
- **Include/Exclude**: regex-based include and exclude rules to scope a crawl to (or away from) specific paths/patterns.
- **Speed control**: adjustable thread count and max URLs/second to throttle crawl speed and avoid overloading a server.
- **User-agent switching**: crawl as Googlebot, Bingbot, a named AI crawler (e.g., GPTBot- or ClaudeBot-style strings), or a fully custom UA string, via preset dropdown or manual entry.
- **Custom HTTP headers**: attach arbitrary request headers (Accept-Language, cookies, auth tokens, etc.) to every request.
- **Authentication**: standards-based (basic/digest) authentication plus forms-based authentication for logging into staging environments or gated content through an embedded browser window.
- **Custom robots.txt**: download, edit, and test a site's robots.txt inside the tool without needing to publish changes first.
- **Segmentation**: user-defined URL segments (e.g., blog, product, category) so crawl data and reports can be filtered/broken out by section of the site.
- **Storage engine**: a configurable hybrid crawler — data can be held in memory (fast, RAM-bound) or written to a database on disk, which is what allows very large crawls to run without exhausting memory.
- **Crawl limit**: the free tier caps a crawl at 500 URLs. The licensed version removes that hard cap; the practical ceiling is then whatever the host machine's allocated RAM and disk allow (Screaming Frog markets this as "unlimited," but it is effectively hardware-bound, and their own FAQ frames it that way).

### JavaScript rendering
The Spider embeds a headless Chromium-based rendering engine (their "Web Rendering Service") so it can execute JavaScript and crawl the post-render DOM — necessary for auditing sites built on frameworks like React, Angular, and Vue where content/links aren't present in the raw HTML response. Rendering settings include things like AJAX timeout, viewport/device emulation, and capturing rendered screenshots per page. The tool can also diff raw HTML vs rendered HTML to flag content or links that only exist after JavaScript execution — a common JS-SEO risk indicator.

## 3. Technical Audit Checks & Data Outputs

### Response codes, redirects & redirect chains
Every crawled URL is bucketed by response type: no-response/connection failures, 2xx success, 3xx redirects, 4xx client errors, and 5xx server errors, with the referring (source) page recorded for each. Redirect handling goes beyond simple HTTP 301/302s to also detect JavaScript-based redirects and meta/HTTP refreshes, and it maps out full **redirect chains and loops** so a migration or legacy-redirect mess can be untangled in one view rather than link-by-link.

### Canonicalization
Canonical link elements (`<link rel="canonical">`) and canonical HTTP headers are both parsed and compared, surfacing conflicts (e.g., a page canonicalizing to itself vs. elsewhere, multiple canonical tags, or a mismatch between the HTML and header canonical).

### Pagination
`rel="next"`/`rel="prev"` attributes are audited across paginated sequences, including common misconfigurations (e.g., pagination pointing at non-indexable pages, or missing sequence links).

### Hreflang
A dedicated Hreflang tab audits international/multilingual annotations: missing return (reciprocal) tags, inconsistent or invalid language-region codes, hreflang values pointing to non-200 URLs, and other common international-SEO misconfigurations.

### Robots directives
Meta robots tags and the `X-Robots-Tag` HTTP header are both parsed for directives such as `noindex`, `nofollow`, `none`, and `nosnippet`, alongside robots.txt disallow rules — giving a single combined view of everything that could be blocking a page from being indexed or having links followed.

### Page titles, meta descriptions & headings
Title tags and meta descriptions are flagged when missing, duplicated across pages, too long/short (with pixel-width truncation awareness, tying back into SERP mode), or when multiple instances exist on one page. H1/H2 headings (and further levels) are checked for the same missing/duplicate/multiple issues, plus non-sequential heading order.

### Content, word count & readability
Each page gets a word count, a readability score, and a "low relevance" flag that uses on-page NLP to detect content that deviates significantly from the site's average topical focus — useful for spotting thin or off-topic pages at scale.

### Indexability
A dedicated Indexability column/status explains, in plain terms, *why* a URL is or isn't indexable (canonicalized elsewhere, noindex, blocked by robots.txt, non-200 status, etc.), rather than requiring the user to cross-reference multiple columns manually.

### Duplicate & near-duplicate content
Exact duplicates are detected via an MD5 hash comparison of page content. Near-duplicate detection uses an adjustable similarity threshold to catch pages that are mostly-but-not-completely identical (templated boilerplate, thin variants, etc.). As of recent versions, this has been extended with **vector-embedding-based semantic similarity**, so pages that are worded differently but topically near-identical can also be surfaced — not just byte-level duplicates.

### Security & URL hygiene
The crawler flags mixed content (HTTP resources on HTTPS pages), insecure forms, missing security headers, and general HTTP-vs-HTTPS inconsistencies, plus URL hygiene issues like non-ASCII characters, underscores, uppercase letters, excessive parameters, overly long URLs, and repetitive path segments.

## 4. Links

- **Internal vs. external inventory**: every link on the site is classified as internal or external, with status code and source page recorded for each — external link status is useful for finding link rot in outbound references.
- **Broken links (4xx/5xx)**: instant bulk identification of dead links with export of both the broken URL and every page that links to it, so a fix list can go straight to a developer.
- **Inlinks / Outlinks**: per-URL tabs showing exactly which pages link to a given URL (inlinks) and which pages it links out to (outlinks) — the granular building block behind most link analysis in the tool.
- **Anchor text**: anchor text is captured both in aggregate (site-wide anchor text usage) and per-link, with flags for generic/non-descriptive anchor text ("click here," "read more") that carries little SEO or usability value.
- **Orphan pages**: pages that exist (found via XML sitemap, Google Analytics, Search Console, or other crawl sources) but have no internal links pointing to them are identified by cross-referencing those sources against the regular crawl's link graph.
- **Internal Link Score**: a proprietary 0–100 scoring model approximating internal PageRank/link equity distribution across the site, so pages that are under-linked relative to their importance can be spotted.
- **Uncrawlable internal outlinks (new in v24.0)**: a dedicated filter and "Link Crawlability" column identify links that technically exist in the HTML but don't follow crawlable-link best practice (e.g., links on `<span>`/`<div>` elements, `onclick` JavaScript handlers, or `javascript:` pseudo-protocol hrefs) — these are exportable in bulk so they can be converted to proper `<a href>` links.

## 5. Images, Resources, AMP, Structured Data & Quality Checks

### Images & page resources
All images referenced across the crawl are inventoried, with checks for oversized files, missing `alt` text, background-images (which don't carry alt text at all), and missing width/height attributes (a layout-shift/Core Web Vitals concern). Other page resources — CSS, JS, fonts — are similarly tracked, and in rendering mode the tool reports which resources were blocked (e.g., by robots.txt) and therefore couldn't be used to render the page.

### AMP crawling & validation
AMP URLs can be crawled and validated using Google's own official AMP validation library, embedded directly in the tool, so AMP markup errors are caught without needing a separate validator pass.

### Structured data validation (Schema.org & Google Rich Results)
Screaming Frog parses JSON-LD, Microdata, and RDFa structured data and validates it against two distinct rule sets: general **Schema.org** specification compliance, and **Google's Rich Result eligibility rules** (which are stricter and Google-specific). Google's rule set distinguishes between missing/invalid *required* properties (validation errors — these disqualify a page from the rich result) and missing *recommended* properties (validation warnings — these don't disqualify eligibility but reduce the richness of the result). Results appear in a dedicated Structured Data tab per URL, and a summary report aggregates recurring error/warning *patterns* across the whole site (rather than one row per instance), showing how many URLs each pattern affects. As Google's supported rich-result feature set changes, the tool's validation rules are updated accordingly (for example, a retired "FAQ rich result" feature type was removed from validation in v24.2 after Google discontinued it).

### Accessibility auditing
Accessibility checks run on the open-source **axe-core** engine (the same engine behind many browser accessibility devtools), tested against WCAG guidelines, and are performed automatically at crawl scale rather than one page at a time. The bundled axe-core version is kept current (updated to 4.11.4 in v24.2).

### Spelling & grammar
A built-in spelling and grammar checker runs across the crawl in 25+ languages, flagging issues per page with the ability to maintain a custom ignore/dictionary list.

## 6. Site Structure & Visualizations

Crawl depth (distance from the start URL) is tracked and filterable for every page, and site architecture can be analysed by directory as well as by the custom segments described earlier. Beyond tabular data, the tool renders interactive **site visualizations**:
- **Force-directed crawl diagrams** — a physics-style graph of the whole crawl, clustering pages by how they interlink.
- **Directory tree diagrams** — a hierarchical view following URL folder structure.
- **Tree-graph visualizations** — another structural view of link depth/hierarchy.

These are interactive (zoom/pan/click-through) and exportable as images. A v24.0 addition lets users click content-cluster legend entries to toggle specific clusters on/off within the diagram, making dense graphs easier to read.

## 7. XML Sitemaps

### Sitemap generation
XML sitemaps — and separate Image XML sitemaps — can be generated directly from crawl data, with configuration over which URLs are eligible for inclusion (e.g., only indexable, only 200-status pages), `lastmod` values, priority, and change-frequency fields.

### Sitemap auditing
Existing sitemaps can be crawled either as a standalone check or merged into a full site crawl, which enables cross-referencing: URLs present in the sitemap but non-indexable (blocked, noindexed, redirecting, erroring) get flagged as sitemap hygiene issues, and the same data source feeds orphan-page detection (URLs in the sitemap that aren't linked internally anywhere, and — just as importantly — pages found by crawling that are missing from the sitemap).

## 8. Integrations & APIs

### Google Analytics (GA4)
Connects to the Google Analytics API using the user's own account credentials and pulls per-URL analytics data (sessions, engagement, conversions, bounce/engagement rate, and more) directly into the crawl, so technical data and real user behaviour can be viewed side by side. GA4 support was added several versions back, replacing the now-retired Universal Analytics connector.

### Google Search Console
Two GSC APIs are used: the **Search Analytics API** (clicks, impressions, CTR, and average position per URL/query) and the **URL Inspection API** (bulk index status, Google-selected canonical, mobile usability, and rich-result status per URL). Because Google rate-limits the URL Inspection API, this is typically run against a subset of priority URLs rather than an entire large site. Read timeouts for GSC calls were extended (from 20 seconds to 2 minutes) in v24.1 to reduce failures on slower responses.

### PageSpeed Insights / Core Web Vitals
Connects to the PageSpeed Insights API to pull Lighthouse-based lab metrics (performance score, opportunities, diagnostics) as well as **Core Web Vitals** field data from the Chrome User Experience Report (CrUX) — at crawl scale, across every URL, rather than one-at-a-time via the public PSI web tool.

### Backlink/authority data: Ahrefs, Majestic, Moz
The Spider connects to the Ahrefs, Majestic, and Moz APIs (using the user's own paid subscription/API credentials for each) and imports link-authority metrics — e.g., backlink counts, referring domains, and each provider's proprietary authority scores — directly into the crawl's Link Metrics tab, useful for combining technical audits with link-equity/content-audit work. Ahrefs' integration gained a country-level metrics filter (choose country, and monthly vs. average search volume) in v24.0.

### AI / LLM features
This is the area with the most 2026 activity:
- **Native AI prompt integration**: the tool can send page data to an LLM mid-crawl and capture the response as a crawl column — supported providers are **OpenAI, Google Gemini, Anthropic, and Ollama** (for free, local/self-hosted models). Typical uses include auto-generating or evaluating meta descriptions, classifying page types/intent, or pulling structured information out of unstructured content. v24.0 added live validation of the selected model against each provider's current model list (so prompts don't silently fail against a deprecated model), a system-wide prompt field to set consistent role/tone/constraints across all AI calls, and visible token-usage tracking per provider.
- **SEO Spider MCP Server (flagship new feature, v24.0, May 2026)**: the Spider can now be driven through the **Model Context Protocol**, letting AI assistants — Claude, Claude Cowork, LM Studio, and other MCP-compatible clients — connect to a running instance (via Node.js) and trigger crawls, query and manipulate crawl data, generate exports, and build visualizations using natural-language requests instead of manual UI steps. It ships as an installable MCP extension/connector alongside the main app. As of the June 2026 point releases: an auto-start-MCP-on-launch option was added, the tool list can be exported as markdown documentation, and progress reporting was extended to cover API calls and crawl analysis — but coverage is still partial (e.g., **List mode crawling was not yet supported through MCP** as of the most recent update, though the vendor has indicated it's imminent). Screaming Frog has been explicit that this is meant to speed up workflows, not replace an experienced SEO practitioner.
- **AI-crawler / LLM-bot testing**: the existing user-agent switcher can impersonate AI crawlers (e.g., GPTBot- or ClaudeBot-style strings) to test how a site responds to them, and the companion Log File Analyser can verify (not just claim-match) genuine AI bot traffic in server logs, guarding against spoofed user-agents.
- **No conventional public API**: notably, Screaming Frog has confirmed directly (in response to user questions) that there is **no general-purpose REST API** for the SEO Spider — automation is done via the desktop UI, the CLI, the Scheduler, or (now) the MCP server for AI-agent use specifically. This is a meaningful gap relative to typical modern SaaS tools.

### Google Sheets & Looker Studio (Data Studio)
Scheduled crawls can automatically export results to a connected **Google Sheet**. There's also a supported connector/template setup for **Google Looker Studio** (internally the product still refers to it by its older name, "Data Studio," after Google's naming reversed course again) that enables automated, continuously-refreshed crawl dashboards without manual export/import steps.

## 9. Custom Extraction, Custom Search & Custom JavaScript

- **Custom Search**: search the raw page source for arbitrary strings, keywords, or regex patterns (e.g., presence/absence of an analytics tracking snippet, a specific code comment, a keyword) and get a filtered list of matching/non-matching pages.
- **Custom Extraction**: up to 100 independently configured "extractors" per crawl, each using **XPath, CSS Path selectors, or regex** to scrape specific data points out of the HTML or rendered DOM — prices, SKUs, review counts, social meta tags, custom data attributes, and so on. Extractors can pull text content, inner/outer HTML, or a specific attribute value. Selectors can be authored by hand or copied straight out of Chrome DevTools' "inspect element" panel.
- **Custom JavaScript**: arbitrary JavaScript snippets can be run against each page during the crawl (via the embedded Chromium engine) to extract data, simulate interactions like scrolling or mouseover events, or otherwise manipulate the page before extraction — comparable to what's possible from a browser's DevTools console, with a library of example snippets to start from.

## 10. Automation

### Scheduling
A built-in task scheduler runs crawls unattended at defined intervals, with full control over which exports/reports get generated each run. Recent additions (v24.0) include:
- **Auto Compare Crawls** for scheduled (and CLI) runs — automatically diffs the two most recent crawls in a project without manual setup.
- **Crawl-change summaries in completion emails** — the existing crawl-complete notification email now includes a table of issues found, and (if auto-compare is on) highlights what changed since the previous run.
- **Emailed export attachments** — scheduled tasks can zip and email specific export files straight to a stakeholder or developer inbox (e.g., a weekly broken-links list) automatically on completion.
- **Skip Empty Reports** — exports/reports with no matching data are no longer generated or attached, reducing clutter.

### Command-line interface / headless mode
The Spider can run **headless** (no GUI) from the command line, which requires a paid licence. Typical invocation supplies a start URL, a `--headless` flag, output-folder and timestamping options, and optionally a saved configuration profile so automated runs match manual ones exactly. This is the mechanism used to wire Screaming Frog into cron jobs, Windows Task Scheduler, CI pipelines, or external orchestration tools (people commonly pair it with tools like n8n, PowerShell scripts, or custom Python/SQL pipelines that pick up the exported files afterward). CLI error handling has been improved recently — e.g., a failed CLI run due to an invalid report name now lists the valid report names (v24.2).

### Crawl comparison
Two saved crawls can be compared (or a staging crawl can be compared against production using URL mapping/rewrite rules) to see what changed structurally and in key on-page elements — new/removed pages, status code changes, metadata changes, and shifts in issue counts. This used to be a manual, on-demand action and is now also available as an automatic step on every scheduled or CLI-triggered crawl.

### Exports, reports & formats
Any tab or filtered view can be bulk-exported (CSV/Excel-style tabular formats), and the tool ships a fixed catalogue of purpose-built reports (e.g., redirect chains, duplicate content, orphan pages, structured data validation summary, uncrawlable internal outlinks, etc.) alongside the raw tab exports. Full crawls themselves save and reopen using a proprietary `.seospider` project file so work can be resumed without re-crawling.

### Notifications
Email notifications on crawl completion (with the issue-summary table and optional comparison data described above) round out the automation story — the combination of scheduling + comparison + notification + emailed exports is effectively a lightweight monitoring/alerting layer bolted onto a desktop crawler.

## 11. Licensing, Pricing & Platform Support

### Free vs. paid
The SEO Spider is free to download with **no sign-up or email capture required**, but the free tier is capped at **500 URLs per crawl**, and — per the vendor's own description — crawl configuration options, the ability to save/reopen crawls, and advanced features such as JavaScript rendering, custom extraction, and API integrations are also restricted in that tier. (Note: the site's own feature-comparison checklist lists most advanced features under both the "Free" and "Paid" columns identically, which appears to be a template artefact — the descriptive text elsewhere on the same page is the more reliable source for what's actually gated.)

### Pricing tiers
A licence is priced **per user**, lasts **one year**, and must be renewed annually. One user may use their key across multiple of their own machines, but keys cannot be shared between different people. As of this research, base and volume pricing (confirmed directly on screamingfrog.co.uk) is:

| Licences | GBP / licence / yr | USD / licence / yr |
|---|---|---|
| 1–4 | £199 | $279 |
| 5–9 | £189 | $265 |
| 10–19 | £179 | $249 |
| 20+ | £169 | $235 |

EUR pricing is also offered (base rate €245/year for 1–4 licences), following the same volume-discount structure.

### Platforms
Windows, macOS (Apple Silicon and Intel builds are distributed separately), and Linux (Ubuntu `.deb`, Fedora `.rpm`, each with amd64/x86_64 and arm64/aarch64 builds). There is no browser-based or hosted version — it is strictly a local desktop install, which also means crawl performance and maximum crawl size are bound by the specifications of whatever machine it's running on.

## 12. What's New in 2026 (Version 24.x Changelog Highlights)

- **v24.0 ("bolus," 19 May 2026)** — headline release: SEO Spider **MCP Server** for AI-assistant integration (Claude, LM Studio, etc.); **Auto Compare Crawls** for scheduled/CLI runs; crawl-change summaries added to completion-notification emails; ability to **email zipped export attachments** on crawl completion; new detection for **uncrawlable internal outlinks** (non-standard link markup); a local **Usage Stats** dashboard; new **Arm64 Linux** builds (Ubuntu and Fedora); a `Crawl Invalid Links` option to capture syntactically malformed URLs; `Skip Empty Reports` for exports; Ahrefs country-level metric filters; clickable/filterable content-cluster legends in visualizations; live AI model validation, system-wide AI prompts, and AI token-usage display; Ollama image-generation support; the Looker Studio connector reverted to being labelled "Data Studio"; and an upgrade to Java 25.
- **v24.1 (8 June 2026)** — mostly MCP refinements and bug fixes: recently-crawled URLs surfaced in the scheduled-crawl seed box; a non-cumulative view added to the Usage Stats graph; an "auto-start MCP server on launch" setting; bulk export support for multi-file exports through MCP; MCP tool documentation exportable as markdown; GSC read timeout extended from 20 seconds to 2 minutes; and several MCP-related bug fixes (large page-content errors, stdout logging conflicts in CLI mode, non-English-language tool failures).
- **v24.2 (22 June 2026)** — CLI now lists valid report names when a run fails due to an invalid one; MCP crawl-progress data now includes a database id; removed validation for Google's now-retired FAQ rich-result feature; axe-core accessibility engine updated to 4.11.4; assorted crash fixes (Windows/RDP, Custom JavaScript preview window, Chromium rendering for website archives).
- **v24.3 (29 June 2026)** — dependency/security patch (jackson-databind updated to close known CVEs) plus further Java crash fixes on Windows.

The throughline across the whole 24.x line is clearly **AI-agent integration** (MCP server) and **automation/monitoring polish** (auto-compare, richer notifications, emailed exports) rather than net-new audit checks — the core technical-SEO check set has been comparatively stable, with most 2026 energy going into how crawls get triggered, monitored, and consumed by both humans and AI assistants.

## 13. Capabilities Most Relevant to Replicate in a Web App

For a competing/complementary web application, these are the specific capabilities worth targeting, with a note on how each maps to a modern web-app architecture:

- **Google Analytics (GA4) integration** → OAuth2 + GA4 Data API (`runReport`) calls keyed by landing page path, joined against crawl data server-side.
- **Google Search Console integration** → Search Console API, specifically `searchanalytics.query` (clicks/impressions/CTR/position) and the URL Inspection API (`urlInspection.index.inspect`) for index-status data; needs rate-limit-aware batching since Google throttles the inspection endpoint hard.
- **PageSpeed Insights / Core Web Vitals** → PageSpeed Insights API v5 (Lighthouse lab data) plus the CrUX API/BigQuery dataset (field data) for at-scale Core Web Vitals reporting — both are directly callable from a backend service.
- **Backlink data (Ahrefs / Majestic / Moz)** → optional "bring your own API key" connectors, mirroring Screaming Frog's model, since these are commercial third-party data sources rather than something to build in-house.
- **Structured data validation** → build a JSON-LD/Microdata/RDFa parser plus a rules engine that separately encodes Schema.org spec compliance vs. Google's stricter, feature-specific required/recommended property rules (and keep it updateable, since Google adds/retires rich-result types over time).
- **Custom extraction engine** → a user-facing rule builder supporting XPath, CSS selectors, and regex against either raw HTML or a rendered DOM, essentially a lightweight scraping-rules table tied to the crawl pipeline.
- **JavaScript rendering** → a headless-browser worker pool (Playwright/Puppeteer against Chromium) mirroring Screaming Frog's embedded rendering service, needed for parity on JS-framework sites.
- **Accessibility auditing** → the **axe-core** engine Screaming Frog itself uses is open-source and npm-installable, so it can be embedded directly into a rendering worker rather than reimplemented.
- **Scheduling + monitoring** → a cron-style job scheduler combined with a diff/compare engine (store crawl snapshots, diff on completion) and a notification layer (email/Slack/webhook) that can attach generated export files — this cluster of features (schedule → crawl → compare → notify → export) is the most "product-market-fit-tested" automation pattern to copy.
- **Exports** → CSV/XLSX generation for arbitrary filtered views, plus first-class **Google Sheets API** push and a **Looker Studio** connector/community-connector definition for live dashboards — both are standard Google APIs, not proprietary.
- **CLI/headless equivalent** → in a web app this becomes a REST/queue-triggered crawl-worker service (submit job → poll/webhook on completion → fetch results), which is the natural analogue to Screaming Frog's `--headless` CLI mode.
- **MCP server** → Screaming Frog only shipped this in May 2026, and it's explicitly still partial (e.g., list-mode crawls weren't supported through it as of the latest point release). Shipping a well-documented **MCP server (or general agent-tool interface)** from early on — exposing crawl-trigger, query, and export actions as callable tools — is a legitimate differentiation opportunity rather than a catch-up feature.
- **The missing public REST API** → this is arguably the biggest gap in Screaming Frog's current offering: the vendor has confirmed there is no general-purpose API, only a desktop CLI and the new AI-agent-oriented MCP server. A web app that ships a real, documented REST/GraphQL API for triggering crawls and pulling structured results programmatically would cover a use case Screaming Frog explicitly does not.

## Sources

- [Screaming Frog SEO Spider — product overview](https://www.screamingfrog.co.uk/seo-spider/)
- [Screaming Frog SEO Spider — pricing](https://www.screamingfrog.co.uk/seo-spider/pricing/)
- [Screaming Frog SEO Spider — release history](https://www.screamingfrog.co.uk/seo-spider/release-history/)
- [Screaming Frog SEO Spider Update — Version 24.0 (blog/changelog, incl. 24.1–24.3 notes)](https://www.screamingfrog.co.uk/blog/seo-spider-24/)
- [How To Use List Mode — Screaming Frog tutorial](https://www.screamingfrog.co.uk/seo-spider/tutorials/how-to-use-list-mode/)
- [Structured Data Testing & Validation Tool — Screaming Frog tutorial](https://www.screamingfrog.co.uk/seo-spider/tutorials/structured-data-testing-validation/)
- [Issues — Structured Data: Rich Result Validation Warnings — Screaming Frog issue library](https://www.screamingfrog.co.uk/seo-spider/issues/structured-data/rich-result-validation-warnings/)
- [Web Scraping & Custom Extraction — Screaming Frog tutorial](https://www.screamingfrog.co.uk/seo-spider/tutorials/web-scraping/)
- [How To Audit Core Web Vitals — Screaming Frog tutorial](https://www.screamingfrog.co.uk/seo-spider/tutorials/how-to-audit-core-web-vitals/)
- [How To Crawl With AI Prompts — Screaming Frog tutorial](https://www.screamingfrog.co.uk/seo-spider/tutorials/how-to-crawl-with-ai-prompts/)
- [How to Monitor AI Bots in the Log File Analyser — Screaming Frog tutorial](https://www.screamingfrog.co.uk/log-file-analyser/tutorials/monitor-ai-bots-in-the-log-file-analyser/)
- [Screaming Frog Log File Analyser — product overview](https://www.screamingfrog.co.uk/log-file-analyser/)
- [Screaming Frog Guide to Doing Almost Anything (60+ Uses) — Seer Interactive](https://www.seerinteractive.com/insights/screaming-frog-guide)
- [How to Use APIs in Screaming Frog — Seer Interactive](https://www.seerinteractive.com/insights/how-to-use-apis-in-screaming-frog)
- [The Complete Guide to Screaming Frog Custom Extraction with XPath & Regex — Uproer](https://uproer.com/articles/screaming-frog-custom-extraction-xpath-regex/)
- [The Comprehensive Guide To Automating Screaming Frog — Understanding Data](https://understandingdata.com/posts/the-comprehensive-guide-to-automating-screaming-frog/)
- [The Screaming Frog API [A Tutorial] — Lupage Digital](https://www.lupagedigital.com/blog/screaming-frog-api/)
- [AI crawler tools & software for allowing, blocking & limiting AI bots — Search Engine Land](https://searchengineland.com/guide/ai-crawler-tools-software)
