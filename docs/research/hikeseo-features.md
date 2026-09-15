# Hike SEO — 2026 Feature Inventory

**Research date:** 2026-07-10
**Sources:** Live pages on hikeseo.co (fetched directly), Capterra, G2, Trustpilot/third-party reviews, and independent review sites. See Sources list at the end.

## 1. Company & product snapshot

Hike (hikeseo.co; app runs at `my.hike.marketing`) is a UK-founded SEO platform (founded ~2017–2018 by Andy Allen and Kieran Headley, both ex-agency SEOs) built for small businesses and the small/micro agencies that serve them. Historically it was a self-serve SaaS toolkit; as of 2025–2026 the product has been substantially repositioned around **Kit**, a named AI "SEO agent" that operates the underlying toolkit on the customer's behalf. The company describes itself as "done-for-you" SEO now rather than "software you learn to use yourself." Hike claims 12,000–20,000+ small-business customers since 2017 and a 4.9/5 average across 390+ aggregated reviews on its own site; third-party samples (Capterra: 3.5/5 on 4 reviews; assorted G2/Trustpilot mentions) are smaller and more mixed. Typical customer profile cited by Hike: businesses with roughly 2–10 employees, plus solo/small agencies.

The task brief also referenced **hike.co** as an alternate domain; a direct fetch of that domain timed out during this research, so its current behavior (redirect vs. separate property) is unconfirmed here — treat hikeseo.co as the authoritative domain.

Note on naming: the brief hypothesized a strategy tool called "Vision." No such branding was found anywhere in current or historical Hike material. The strategy-building module is simply called **Strategy** in the product navigation.

## 2. Onboarding & SEO strategy

- The in-product navigation has a **Strategy** section containing Keyword Research and a **Keyword Sitemap** (also called **Keyword Mapping**) builder — this is Hike's closest equivalent to a "strategy builder."
- Kit-driven onboarding: Kit builds a profile of the business from the website, Google Business Profile, reviews, locations, and named competitors, then generates a tailored month-by-month SEO plan from that profile.
- Kit runs on a recurring **monthly cycle** that Hike documents explicitly:
  - **Week 1** – Kit drafts the coming month's plan and submits it to the customer's **Approval Centre** for review/sign-off.
  - **Week 2** – Approved changes are implemented on-site; Kit also drafts the month's blog post and the week's Google Business Profile post.
  - **Week 3** – Focus shifts to Google Business Profile and local-directory/citation work.
  - **Week 4** – End-of-month reporting: what was completed, what's planned next, current performance, plus an optional account-manager call.
- Configurable controls layered on top of this loop (per recent product updates referenced on hikeseo.co): **page prioritization** (tell Kit which pages matter most), **editable tone of voice**, an **AI business profile** Kit uses to reason about the business, and **custom auto-approval timing** (let Kit auto-execute low-risk changes after a set delay instead of waiting for manual approval every time).
- The underlying manual workflow (still usable without leaning on Kit) is: seed-keyword research → build a Keyword Sitemap by adding pages → assign keywords to pages → run an AI review of the sitemap.

## 3. Optimize: on-page guidance & keyword targeting

- **Onsite Optimiser**: a JavaScript snippet installed on the customer's site that lets Hike/Kit push on-page changes (copy, titles, meta descriptions, headings, internal links, image attributes) live without needing CMS back-end access. This is the mechanism that makes the platform "work with any site" rather than requiring CMS-specific plugins.
- Hike's own retention messaging: SEO changes made through the Onsite Optimiser stay in place after cancellation, as long as the snippet remains installed.
- On-page scope covered: title tags, meta descriptions, header tags, keyword density/usage, internal linking, image alt text and title tags, and general content readability.
- Built-in guardrails baked into the Keyword Sitemap tool:
  - Recommended max of 3–4 keywords per page (character-limit and keyword-stuffing rationale explicitly given: ~70 characters for title tags, ~155 for meta descriptions).
  - **Keyword Cannibalization** guidance — warns against mapping near-duplicate keywords to different pages.
  - **Keyword Confusion** indicator — a flag shown when a keyword is mapped to one page in the sitemap, but Google is actually already ranking a *different* page on the site for it; includes the actual ranking URL/position so the user can decide whether to reassign.
  - **Auto-Assign** — bulk-assigns keywords already ranking in the top 5 to their corresponding sitemap pages automatically.
  - **Keyword intent classification** — each keyword is tagged transactional, informational, or mixed, used to guide whether it belongs on a service page or a blog post.
  - **AI Review / AI Keyword Sitemap Review** — an automated pass over chosen keywords (and later, the full sitemap) that marks each with a green tick or a yellow "?" plus a written justification of why a keyword is/isn't a good fit.
- One reviewer-reported detail worth flagging as a real limitation: a Capterra reviewer noted the platform sometimes treats different-language versions of the same page as duplicate content, which is a false positive in the optimization/audit logic.

## 4. Keyword research & suggestions

- Workflow: enter a seed keyword (e.g., "SEO London") → get a generated list of related keyword ideas, sortable by Search Volume or Difficulty.
- **Search Volume**: Google's average monthly search volume for the term. Hike's own documentation is explicit that this is an annual total divided by 12, so seasonal spikes are not visible in the number.
- **Difficulty**: bucketed as Low / Medium / High / Very High rather than a raw numeric score, calculated from the Domain Authority of the sites currently ranking on page 1 for that term. Hike pairs each band with a rough time-to-rank expectation: Low ≈ 3–6 months, Medium ≈ 6–12 months, High/Very High ≈ 12+ months.
- Filters available inside keyword research:
  - **Your Ranked Keywords** – keywords the site already ranks for, surfaced automatically (useful for finding "accidental" rankings to formally target).
  - **Blog Ideas** – content topic suggestions generated from the seed keywords.
  - **Competitor Keywords** – add a competitor's domain to pull the terms it ranks for.
  - **Previous Keyword Ideas** – history of past research sessions.
- Selected keywords flow directly into the Keyword Sitemap/mapping step described above.

## 5. Rankings & position tracking

- G2 categorizes this capability as **SERP Rank Tracking** (under an "SEO Content & Rankings" feature group).
- Current published plans track **up to 300 keywords** (both Single Site and Multi-site tiers, as of this research). Older/legacy pricing appears to have used a lower cap: one user review explicitly mentions being charged extra for keywords beyond a 100-keyword allowance, suggesting the cap and its pricing have changed over time.
- Rank data surfaces inside the Keyword Sitemap (each assigned keyword shows its current Ranking URL and Ranking Position) and inside keyword research (via the "Your Ranked Keywords" filter).
- A documented product limitation (Capterra review): rankings are not displayed beyond position 100, making it harder to watch a brand-new keyword's early movement toward page 1.
- **Local rank tracking** is not a separately branded module — it's folded into the Local SEO/Google Business Profile workflow. Hike's own copy states Kit "continuously tracks local rankings and refines recommendations" as part of maintaining Map Pack visibility.
- **Competitor rank/keyword tracking** exists as a related but distinct capability — see Section 7.
- A separate reviewer flagged the inability to track rankings across multiple countries/markets as a gap versus larger platforms like Semrush or Ahrefs.
- Exact refresh cadence (daily vs. weekly polling) is asserted by some third-party aggregator summaries but was not directly confirmed on Hike's own current marketing pages during this research — treat as unconfirmed.

## 6. Site audit (technical + on-page)

- **Technical SEO Audits**: automatic scans of the connected site, with **Google Search Console** as a direct data source feeding the audit.
- Issue types referenced across Hike's own copy and third-party reviews: missing/duplicate title tags, duplicate meta descriptions, broken links/404s, slow-loading pages, duplicate content (including the language-variant false-positive noted above), redirect problems, and general crawlability/indexing issues.
- Fixes are presented as a prioritized, step-by-step list; where the issue is in scope for the Onsite Optimiser, Kit can apply the fix directly rather than just reporting it.
- A 2022 product update ("Google Search Console Actions") specifically extended this from passive reporting to letting the platform act directly on GSC-sourced issues.
- **No distinctly-branded numeric "Health Score"** was found in Hike's current marketing or help content during this research. Some third-party summarizers use generic "health score" language, but Hike's own materials present audit output as a prioritized issue/task list rather than a single score — unlike, for example, Ahrefs' or Semrush's named "Site Health %" metrics. Treat a Hike-specific health score as unconfirmed/likely not a distinct feature.
- A documented limitation from an agency reviewer: the audit tool (used for prospecting/lead-gen) was wished to surface more technical/performance and local-SEO detail than it currently does.

## 7. Competitor analysis

- Inside Keyword Research, users can add one or more competitor domains to pull the keywords those sites rank for, with the option to import selected terms into their own research/sitemap.
- A distinct **Competitor Tracking** capability (named explicitly by a third-party reviewer) monitors, on an ongoing basis, how competitors rank and which keywords they're targeting — separate from the one-off "add a competitor" lookup inside keyword research.
- G2 lists **Competitor Analysis** under the product's Reporting feature group, implying competitor comparisons also surface inside client-facing reports, not just the research tool.
- Guidance content stresses picking competitors of a similar size and locale so suggestions stay relevant, and offers a "need help" prompt for users unsure who their competitors are.

## 8. Reporting (including white-label agency reports & client management)

- **Reporting & Analytics** pulls rankings, traffic, and performance data together into one view; a plan-level feature called **AI Reporting** indicates reports/summaries are now at least partly AI-generated.
- Monthly reporting is standard across plans; it's explicitly the Week 4 deliverable in Kit's monthly cycle (completed work, next month's plan, current performance), with an optional account-manager call attached.
- **Report Builder**: agencies can brand client-facing reports with their own logo, fonts, and colors (a dedicated "new Report Builder" was a named product update in Hike's release history, so this has existed for several years, not just since the Kit rebrand).
- G2 explicitly lists **White Label**, **Custom Reports**, and **Data Visualization** as supported capabilities under the product's SEO Reporting feature category.
- **Lead-gen SEO Audit Tool**: originally a standalone, credit-metered add-on (historically ~25 audits/month for ~£20/$25, or unlimited for ~£40/$50), this is a public-facing, agency-branded free-audit widget — a prospect enters their URL, gets a branded audit showing current keyword rankings (used explicitly as a sales trigger), can log in to explore the data themselves, and is prompted to upgrade into the agency's paid packages. It is now listed as a bundled line item ("lead-gen audit widget") on the current Multi-site/agency plan rather than a separate paid add-on.
- **Client management**: clients can be given a restricted, "client-friendly" view into their own site's data without exposure to the agency's other clients or full toolset — but see Section 12 for the caveat that this is not a full multi-seat/role-based permission system.

## 9. Tasks, action plans & SEO education

- The product's core interaction model is an **itemized, prioritized task/action list** rather than raw data dashboards. A Capterra reviewer specifically called out "the itemized list of tasks" as the platform's strongest idea in concept — while also flagging a real bug: completed items sometimes continued to display as outstanding (or the reverse), which is a documented reliability caveat rather than a design strength.
- **Approval Centre**: the current name for the screen where Kit's proposed monthly actions (page edits, the month's blog draft, GBP posts, review replies) are queued for the customer or agency to review and approve before anything goes live, with configurable auto-approval timing as noted in Section 2.
- **Learn SEO hub**: a large, structured education library organized into pillars that closely mirror the product's own module structure — SEO Content (on-page), Technical SEO, Off-Page SEO, Local SEO, SEO Strategy, SEO Reporting, and International SEO — plus a newer **AI SEO** pillar covering GEO (Generative Engine Optimization), AEO (Answer Engine Optimization), and LLMO (LLM Optimization) concepts.
- **Industry Strategy Guides**: a separate library of 10+ vertical-specific guides (dentists, plumbers, electricians, accountants, real estate agents, roofers, construction firms, recruiters, chiropractors, photographers, web design agencies) that repackage the same strategic advice for specific trades/professions.
- Human support wraps the self-serve content: unlimited live chat and email, a named account manager, onboarding and monthly review calls, and — called out repeatedly in reviews — custom short videos recorded in response to individual customer questions.

## 10. Local SEO, citations & backlinks

- **Google Business Profile toolset**: primary/secondary category selection, business description writing and updates, and website URL/tracking-parameter management.
- **Review management**: AI-drafted replies to positive reviews; negative reviews are routed to a manual-response queue rather than auto-answered.
- **Weekly, auto-generated Google Business Profile posts** (seasonal promotions, industry news, business updates) to keep listings active.
- **Citation/directory building**: businesses are submitted to 50+ directories (Google, Bing, Apple Maps, Facebook, Yelp, Foursquare, and others named on the features page), with roughly 40–50 individual listings built out over the course of a year, and ongoing NAP (name/address/phone) consistency maintenance as business details change.
- Local rank tracking and Google Map Pack visibility monitoring are folded into this same local workflow rather than existing as a separate module (see Section 5).
- The Local SEO education hub additionally covers "near me" keyword targeting, city/service-area page creation, and local schema markup — it's unclear from public material how much of this is actively automated by Kit versus purely educational content for self-serve users.
- **Backlinks**: Hike's own features page describes uncovering "backlink opportunities," flagging toxic links, and monitoring referring domains/anchor text/link equity (topics also covered in the Off-Page SEO learning hub). However, a fairly recent third-party review is explicit that **active link-building/acquisition is not included** — Hike monitors and surfaces backlink data but does not build links on the customer's behalf. Treat backlink "building" claims as monitoring/opportunity-surfacing rather than a managed link-building service.

## 11. Content tools & AI content writer

- **Content Wizard**: Hike's AI writing assistant. It identifies strong title/topic options for a target keyword and generates a unique blog post (recent product copy cites roughly 400–500 words; earlier third-party coverage cited ~500 words) with an editable tone of voice, ready to publish.
- One AI-written blog post per month is the standard cadence on current plans ("monthly blog content creation").
- Per G2's summary of Kit's workflow, content/on-page work also includes building **6-month content calendars**, metadata optimization, and internal-linking suggestions generated alongside the copy.
- Content ties back into the Keyword Sitemap: the "Blog Ideas" filter suggests topics from seed keywords, and finished posts are generally mapped to informational-intent keywords rather than transactional ones.

## 12. Agency features (multi-client, white label, team)

- **Hike for Agencies** is a distinct product track aimed explicitly at small agencies and solo operators — Hike's own copy states plainly that agencies with an in-house SEO department are not the target customer.
- **Multi-site plan**: manage multiple client websites from a single dashboard/account. The published baseline covers "up to 3" sites; higher counts are custom-quoted via `sales@hikeseo.co` rather than self-serve.
- **White-labeling** (mature, dating back to a dedicated 2019 launch, not just a recent Kit-era addition): custom domain or `*.hike.marketing` subdomain, custom company name shown in page titles, a toggle to remove all "powered by Hike" mentions, custom logos (top nav, login screen), custom login background image, custom favicon, and the ability to plug in the agency's own live-chat widget ID. Two other historical white-label features are notable for a replication effort: an **"Action Delivery Link"** and **"Citation Delivery Link"** — configurable links the agency can attach so that, when a task in a client's action list is something the agency wants to upsell (extra SEO work, citation building), the client sees the agency's own sales page rather than Hike's.
- **Kit rebranding**: as of recent updates, the Kit AI agent itself can be renamed and re-iconed per agency, so end clients never see "Hike" or "Kit" branding at all — the automation is a re-skinned layer over the same underlying engine.
- White-label was historically sold as a standalone flat-fee add-on (~£19.99/$24.99 per month, covering unlimited sites in the account). The current live Multi-site plan bundles white-labeling into the plan price rather than charging separately — packaging has clearly changed over time.
- **Compass**: a bi-weekly newsletter (with occasional in-person events) for agencies/freelancers covering search, social, paid, and AI-marketing trends. This is a content/community perk bundled into the agency plan rather than a product feature.
- A **dedicated agency support tier** ("dedicated agency support") is called out as distinct from the standard account-management support given to single-site customers.
- **Team seats / role-based permissions**: no public evidence was found of a conventional multi-seat, role-based permission system for internal agency team members (i.e., inviting colleagues with different access levels), the way some competitors (e.g., SE Ranking's "Agency Pack") advertise. Hike's agency model appears structured around **one agency login managing many client site-records**, each with its own strategy/sitemap/tasks/reports — not multiple internal users with differentiated permissions. This is worth flagging as either a real product gap or simply an undocumented area.
- Free reseller signup path exists at `my.hike.marketing/register/reseller`.

## 13. Integrations & API

- **Confirmed first-party integrations**: Google Search Console, Google Analytics (GA4 — Capterra's integration catalog also lists "Google Analytics 360," which may be a categorization artifact rather than a literal GA4-360/enterprise integration), and Google Business Profile/Google Maps. These three are the only integrations independently verified via Capterra's catalog and Hike's own copy.
- **CMS/platform compatibility**: Hike states it works with WordPress, Webflow, Wix, Shopify, Squarespace, Framer, and Magento. GoDaddy's own Website Builder is explicitly **not** supported (sites hosted on GoDaddy but built with another platform are fine). This compatibility is achieved through the universal Onsite Optimiser JS snippet rather than CMS-native plugins — a different architecture from, say, Yoast or Rank Math, which are WordPress-plugin-native.
- **API**: search results indexed a developer documentation site at `docs.hikeseo.co` (and an `api-dev.hikeseo.co` host), with indexed descriptions suggesting a narrow scope — basic site-management endpoints (view, add, delete websites on an account). Direct fetch attempts against these documentation URLs during this research returned no readable content (likely JS-rendered or access-gated), so the current public availability, authentication model, and full endpoint coverage could **not be verified**. No evidence was found of a broad, self-serve, publicly marketed API for keyword, ranking, audit, or task data comparable to Ahrefs' or Semrush's public APIs — treat any such API as narrow/uncertain rather than a confirmed platform capability.
- **Deployment**: Capterra's listing metadata marks Hike as available on Web, Android, and iPhone/iPad. No App Store or Google Play listing was located during this research, so "native mobile apps" should be treated as unconfirmed — this more likely reflects a responsive web app than dedicated mobile apps.

## 14. Pricing tiers & limits (live-fetched 2026-07-10)

No free trial is offered; instead Hike uses a 14-day money-back guarantee, an interactive product demo, and frequent promotional discounts (e.g., "half price first month," 50%-off referral links).

**Single Site**
- $149/month, or $89/month billed annually (~$1,068 billed upfront) — USD.
- £99/month, or £59/month billed annually (~£708 billed upfront) — GBP.
- Included: SEO strategy build & ongoing updates, **up to 300 tracked keywords**, monthly website optimizations, technical SEO fixes, one monthly blog post, "AI Search Optimization," directory listings across major platforms, Google Business Profile management, review tracking, AI-assisted reporting, monthly reporting, a named "dedicated digital expert" (account manager), and access to the full Hike tool suite.

**Multi-site**
- $299/month, or $179/month billed annually — USD (£199/£119 GBP) — for **up to 3 websites**.
- Higher site counts: custom-quoted via `sales@hikeseo.co` rather than self-serve checkout.
- Adds on top of Single Site: full white-label feature set, white-labeled Kit AI agent, more granular control over Kit's automation/approval behavior, the lead-gen audit widget, a multi-site management dashboard, Compass newsletter access, and dedicated agency support.

**No long-term contracts** beyond the billing interval chosen at purchase; plans auto-renew unless cancelled.

**Pricing has changed materially and repeatedly** in the recent past — worth flagging explicitly since this is a fast-moving area:
- A November 2025 third-party review cites a single unified plan at **£99/month (£60/month annual)**, i.e., no Single-site/Multi-site split existed yet at that point.
- An older, apparently superseded tier structure referenced in general search indexes described three tiers: a self-serve "Basic" plan (~$59.99/month or ~$35.99/month annual), an "Expert Support" tier (~$189.99/month), and a "Managed" tier (~$1,079 upfront, described as a 40%-discounted annual price) with a 300-keyword cap and dedicated account manager — this looks like an earlier packaging model predating the current Kit-branded structure.
- Capterra's own listing (verified by Capterra as of March 2026) shows a starting price of **£75/month flat rate**, a third data point distinct from both of the above.
- At least one review references being charged extra for keywords beyond a **100-keyword cap** on an older/lower plan, versus the 300-keyword allowance on current plans.

Given this volatility, treat the Single Site / Multi-site figures above (fetched live today) as the most current and authoritative snapshot, and expect further repricing.

## 15. AI search positioning (GEO / AEO / LLMO)

A distinctly 2025–2026 addition worth calling out on its own: Hike now markets Kit as optimizing for AI-driven search surfaces (ChatGPT, Perplexity, Claude, and other LLMs), not just Google — reflected in a dedicated "AI SEO" pillar in the Learn hub (explaining Generative Engine Optimization, Answer Engine Optimization, and LLM Optimization), an "AI Search Optimization" line item on both pricing plans, and a dedicated "Hike vs. ChatGPT" comparison page arguing that ChatGPT alone can brainstorm but can't crawl a site, track rankings, or execute changes the way Kit does.

## 16. Capabilities relevant to replicating in a web app

This section maps Hike's approach to concrete build patterns, for direct use in planning a comparable product.

1. **Action-plan/task generation engine.** Hike's core loop isn't a one-time checklist — it's a recurring monthly cycle (plan → human approval → execute → report) gated by an "Approval Centre" with configurable auto-approval thresholds. A reasonable data model to replicate: a `Task`/`Action` entity linked to a `Page` + `Keyword` + category (technical / on-page / content / local), a status machine (`proposed → approved → in_progress → done → verified`), and a short "why" justification string attached to each recommendation. The "AI Review" pattern (pass/flag + written reasoning) is a cheap, high-value explainability layer worth copying onto any auto-generated recommendation.
2. **On-page optimize guidance.** Two components are directly reusable: (a) a **Keyword Sitemap** data model — pages × assigned keywords × intent × current ranking URL/position — with cannibalization and "keyword confusion" (mapped-page vs. actually-ranking-page mismatch) as validation rules run on save; (b) a **site-agnostic change-delivery mechanism**. Hike's JS-snippet "Onsite Optimiser" avoids building N CMS-specific integrations; a similar injected-tag approach (or a small set of official connectors for the top 2–3 CMSs) is a lower-effort path to "works with any site" than deep per-CMS plugin development.
3. **Rank tracking.** Straightforward to replicate: per-keyword SERP position polling (via a third-party SERP API) tied back to the sitemap's keyword-to-page mapping, capped per plan tier (Hike's 300-keyword ceiling on its top self-serve plan is a reasonable reference point for a comparable cap), plus a "ranked but unassigned" discovery job (their "Your Ranked Keywords" filter) that surfaces keywords a site already ranks for without deliberate targeting. Hike's acknowledged gaps — no visibility past position 100 in at least one plan, no multi-country tracking on lower tiers — are explicit differentiation opportunities for a competing build.
4. **White-label agency reporting.** Model this as: (a) tenant-level branding config (logo, color tokens, custom domain/subdomain, favicon, "powered by" toggle) applied at the UI-shell level; (b) a rebrand-able AI-agent persona (name/icon) layered on the same underlying automation engine — Hike treats this as a skin over Kit, not a fork of the product; (c) a monthly report generator that assembles ranking deltas + traffic + completed tasks + next month's plan into a branded, shareable report; (d) an on-demand public "lead-gen audit" variant (enter a domain, get a gated branded mini-audit with a rankings teaser) as a growth/upsell mechanic specifically for agency customers, plus a configurable "upsell link" so a flagged issue in a client's task list can deep-link to the agency's own sales page.
5. **Agency multi-client model.** Hike's structure is "one agency login, N client-site records," each with its own strategy/sitemap/tasks/reports — not a classic multi-seat, role-based-permission team model. A replicating product should decide deliberately whether to copy that simpler pattern or invest in proper multi-user/role-based access, since Hike does not appear to have built the latter — a plausible, concrete differentiation gap.
6. **Integrations.** Prioritize Google Search Console + Google Analytics (GA4) + Google Business Profile as the "must-have three" — these are Hike's only clearly confirmed direct integrations, despite being a mature, funded product. A genuinely open, documented public API covering keywords/rankings/audits/tasks would be a real, exploitable gap, since Hike's own API access and scope could not even be confirmed during this research.

## 17. What's uncertain / not publicly documented

For transparency, the following could not be confirmed from public sources during this research and should not be treated as verified fact:

- No feature called "Vision" exists anywhere in current or historical Hike material — the strategy module is simply named "Strategy."
- No distinctly-branded, numeric "Health Score" for site audits was found; Hike appears to present audit results as a prioritized issue/task list rather than a single score.
- The scope, authentication model, and current public availability of Hike's developer API (`docs.hikeseo.co`) could not be verified — the documentation pages returned no readable content during this research.
- Native iOS/Android apps are implied by Capterra's deployment metadata, but no App Store or Google Play listing was found; likely a responsive web app rather than true native apps.
- Team-seat / role-based-permission pricing for internal agency users is not clearly documented in either direction (i.e., it's unclear whether it doesn't exist or simply isn't marketed).
- Exact keyword rank-check frequency (daily vs. weekly) is asserted by some secondary/aggregator sources but not directly confirmed on Hike's own current pages.
- The relationship between the hike.co domain (referenced in the task brief) and hikeseo.co could not be independently verified — a direct fetch attempt timed out.
- Pricing and plan packaging have changed multiple times within roughly the last 12–18 months; any figures in this document are a snapshot as of 2026-07-10 and should be expected to change again.

## Sources

- https://www.hikeseo.co/features
- https://www.hikeseo.co/pricing
- https://www.hikeseo.co/
- https://www.hikeseo.co/agency
- https://www.hikeseo.co/kit
- https://www.hikeseo.co/strategy-guides/seo-strategy
- https://www.hikeseo.co/post/how-to-do-keyword-research-in-hike-seo
- https://www.hikeseo.co/post/new-feature-the-new-hike-seo-audit-tool-for-agencies
- https://www.hikeseo.co/post/how-kit-does-your-local-seo
- https://www.hikeseo.co/post/hike-launches-white-label
- https://www.hikeseo.co/learn
- https://www.hikeseo.co/learn/reporting
- https://www.hikeseo.co/compare/alternative-to-semrush
- https://hikeseo.co/features/content-wizard/
- https://www.capterra.com/p/10004632/Hike-SEO/
- https://www.g2.com/products/hike-seo-kit/reviews
- https://relywp.com/blog/hike-seo-tool-review/
