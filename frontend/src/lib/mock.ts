/**
 * Static, fully-deterministic mock data matching the interfaces in `./api`.
 *
 * Used as a fallback whenever a live API call fails (see each page's
 * `try { ... } catch { use mock }` blocks), so the dashboard is fully
 * demoable without a running backend. Values are hand-picked (no
 * `Math.random()` / `Date.now()`) so server- and client-rendered output
 * always match — no hydration mismatches.
 */
import type {
  ActionPlan,
  AiReview,
  ApiKey,
  ContentScore,
  CrawlConfig,
  CrawlResult,
  CrawlSummary,
  CurrentOrg,
  DeliveryLog,
  Device,
  Effort,
  Indexability,
  Issue,
  IssueCategory,
  Keyword,
  KeywordCluster,
  KeywordResearchResult,
  LeadRecord,
  LeadValidationResult,
  LinkInfo,
  Member,
  OnPageCheck,
  OnPageResult,
  Org,
  PageAuditResult,
  Plan,
  RankPoint,
  RankTrackingSummary,
  RedirectHop,
  Report,
  ReportSection,
  SearchIntent,
  SerpAnalysis,
  SerpFeature,
  SerpResultItem,
  Severity,
  Subscription,
  Task,
  TaskStatus,
  TermTarget,
  TrackedKeyword,
  Usage,
  WhiteLabelBranding,
} from "./api";

// ---------------------------------------------------------------------------
// Demo constants — reused as prefilled form values across pages
// ---------------------------------------------------------------------------

export const DEMO_URL = "https://www.example-shop.com";
export const DEMO_DOMAIN = "example-shop.com";
export const DEMO_COUNTRY = "us";
export const DEMO_SEED_KEYWORD = "running shoes";
export const DEMO_TARGET_KEYWORD = "best running shoes for beginners";

// ---------------------------------------------------------------------------
// Shared issue catalog
// ---------------------------------------------------------------------------

const ISSUE_MISSING_META: Issue = {
  code: "missing_meta_description",
  title: "Missing meta description",
  description: "This page has no meta description, so search engines will auto-generate a snippet.",
  category: "on_page",
  severity: "medium",
  recommendation: "Write a unique 120-155 character meta description that includes the target keyword.",
  url: null,
  details: {},
};

const ISSUE_THIN_CONTENT: Issue = {
  code: "thin_content",
  title: "Thin content",
  description: "Word count is well below what top-ranking competitors publish for this topic.",
  category: "content",
  severity: "medium",
  recommendation: "Expand the article toward the 1,400-1,900 word range competitors average.",
  url: null,
  details: { word_count: 280 },
};

const ISSUE_BROKEN_LINK: Issue = {
  code: "broken_internal_link",
  title: "Broken internal link",
  description: "An internal link on this page points to a URL that returns a 404.",
  category: "links",
  severity: "high",
  recommendation: "Update or remove the link, or restore/redirect the destination page.",
  url: null,
  details: { target_status: 404 },
};

const ISSUE_MISSING_TITLE: Issue = {
  code: "missing_title",
  title: "Missing <title> tag",
  description: "No <title> element was found on this page.",
  category: "on_page",
  severity: "critical",
  recommendation: "Add a unique, keyword-rich title tag between 50-60 characters.",
  url: null,
  details: {},
};

const ISSUE_MISSING_ALT: Issue = {
  code: "images_missing_alt",
  title: "Images missing alt text",
  description: "Several images on this page have no alt attribute, hurting accessibility and image SEO.",
  category: "images",
  severity: "low",
  recommendation: "Add descriptive alt text to every content image.",
  url: null,
  details: { missing_count: 6 },
};

const ISSUE_NOINDEX_IMPORTANT: Issue = {
  code: "noindex_on_key_page",
  title: "Noindex on a page that should rank",
  description: "This page is excluded from indexing via meta robots, but appears to be a real content page.",
  category: "indexability",
  severity: "critical",
  recommendation: "Confirm this is intentional; remove the noindex directive if not.",
  url: null,
  details: {},
};

const ISSUE_404: Issue = {
  code: "page_not_found",
  title: "Page returns 404",
  description: "This URL was discovered during the crawl but no longer resolves.",
  category: "technical",
  severity: "high",
  recommendation: "301 redirect to the closest live equivalent or remove all internal links to it.",
  url: null,
  details: { status_code: 404 },
};

const ISSUE_REDIRECT_CHAIN: Issue = {
  code: "redirect_chain",
  title: "Unnecessary redirect",
  description: "Internal links point to a URL that redirects instead of the final destination.",
  category: "technical",
  severity: "low",
  recommendation: "Update internal links to point directly at the final URL.",
  url: null,
  details: {},
};

const ISSUE_KEYWORD_DENSITY: Issue = {
  code: "keyword_density_low",
  title: "Focus keyword underused",
  description: "The focus keyword and its variants appear less often than top-ranking pages.",
  category: "content",
  severity: "low",
  recommendation: "Naturally work the keyword and close variants into 2-3 more sections.",
  url: null,
  details: {},
};

// ---------------------------------------------------------------------------
// Audit / crawl
// ---------------------------------------------------------------------------

const BROKEN_LINK_1: LinkInfo = {
  source_url: `${DEMO_URL}/blog/running-tips`,
  target_url: `${DEMO_URL}/old-catalog`,
  anchor_text: "our spring promo",
  rel: "",
  is_internal: true,
  status_code: 404,
};

function page(args: {
  path: string;
  status_code: number;
  score: number;
  title: string | null;
  meta_description?: string | null;
  word_count: number;
  issues: Issue[];
  h1?: string[];
  images_missing_alt?: number;
  broken_links?: LinkInfo[];
  indexability?: Indexability;
  indexability_reason?: string | null;
  response_time_ms?: number;
  depth?: number;
  redirect_chain?: RedirectHop[];
}): PageAuditResult {
  const url = `${DEMO_URL}${args.path}`;
  const metaDescription = args.meta_description ?? null;
  const depth = args.depth ?? 1;
  return {
    url,
    final_url: url,
    status_code: args.status_code,
    content_type: "text/html; charset=utf-8",
    response_time_ms: args.response_time_ms ?? 240,
    depth,
    discovered_from: depth === 0 ? null : DEMO_URL,
    title: args.title,
    title_length: args.title?.length ?? 0,
    meta_description: metaDescription,
    meta_description_length: metaDescription?.length ?? 0,
    meta_robots: "index,follow",
    x_robots_tag: null,
    canonical: url,
    indexability: args.indexability ?? "indexable",
    indexability_reason: args.indexability_reason ?? null,
    h1: args.h1 ?? (args.title ? [args.title] : []),
    h2: [],
    word_count: args.word_count,
    lang: "en",
    hreflang: [],
    structured_data_types: [],
    internal_links_count: 14,
    external_links_count: 4,
    outlinks: [],
    broken_links: args.broken_links ?? [],
    images_count: 8,
    images_missing_alt: args.images_missing_alt ?? 0,
    redirect_chain: args.redirect_chain ?? [],
    issues: args.issues,
    score: args.score,
  };
}

const CRAWL_PAGES: PageAuditResult[] = [
  page({
    path: "/",
    status_code: 200,
    score: 92,
    title: "Example Shop — Running Shoes, Apparel & Gear",
    meta_description: "Shop running shoes, apparel and gear with free shipping over $50.",
    word_count: 640,
    issues: [],
    depth: 0,
    response_time_ms: 180,
  }),
  page({
    path: "/collections/running-shoes",
    status_code: 200,
    score: 78,
    title: "Running Shoes",
    meta_description: null,
    word_count: 410,
    issues: [ISSUE_MISSING_META],
    images_missing_alt: 3,
    response_time_ms: 260,
  }),
  page({
    path: "/blog/running-tips",
    status_code: 200,
    score: 64,
    title: "5 Tips For New Runners",
    meta_description: "Tips for new runners.",
    word_count: 280,
    issues: [ISSUE_THIN_CONTENT, ISSUE_BROKEN_LINK],
    broken_links: [BROKEN_LINK_1],
    response_time_ms: 410,
  }),
  page({
    path: "/products/aero-trail-runner",
    status_code: 200,
    score: 55,
    title: null,
    meta_description: null,
    word_count: 190,
    issues: [ISSUE_MISSING_TITLE, ISSUE_MISSING_META, ISSUE_MISSING_ALT],
    images_missing_alt: 6,
    response_time_ms: 520,
  }),
  page({
    path: "/checkout/step-2",
    status_code: 200,
    score: 40,
    title: "Checkout",
    meta_description: null,
    word_count: 60,
    issues: [ISSUE_NOINDEX_IMPORTANT],
    indexability: "non_indexable",
    indexability_reason: "meta robots noindex",
    response_time_ms: 300,
  }),
  page({
    path: "/old-catalog",
    status_code: 404,
    score: 0,
    title: null,
    word_count: 0,
    issues: [ISSUE_404],
    response_time_ms: 150,
  }),
  page({
    path: "/collections/trail-running",
    status_code: 301,
    score: 70,
    title: "Trail Running (moved)",
    word_count: 0,
    issues: [ISSUE_REDIRECT_CHAIN],
    response_time_ms: 90,
    redirect_chain: [
      {
        url: `${DEMO_URL}/collections/trail-running`,
        status_code: 301,
        location: `${DEMO_URL}/collections/running-shoes?type=trail`,
      },
    ],
  }),
];

const CRAWL_CONFIG: CrawlConfig = {
  start_url: DEMO_URL,
  max_pages: 100,
  max_depth: 5,
  respect_robots: true,
  follow_external: false,
  render_js: false,
  user_agent: "MySEOappBot/0.1 (+https://scalingfirm.com/bot)",
  include_patterns: [],
  exclude_patterns: [],
};

const CRAWL_SUMMARY: CrawlSummary = {
  total_pages: 7,
  by_status_class: { "2xx": 5, "3xx": 1, "4xx": 1, "5xx": 0 },
  by_severity: { critical: 2, high: 2, medium: 3, low: 2, info: 0 },
  indexable_pages: 6,
  non_indexable_pages: 1,
  pages_with_issues: 5,
  avg_score: 57,
  broken_links_total: 1,
  missing_titles: 2,
  duplicate_titles: 0,
  missing_meta_descriptions: 3,
};

export const mockCrawlResult: CrawlResult = {
  crawl_id: "crawl_demo_0001",
  start_url: DEMO_URL,
  config: CRAWL_CONFIG,
  started_at: "2026-07-10T09:12:00Z",
  finished_at: "2026-07-10T09:14:35Z",
  pages: CRAWL_PAGES,
  summary: CRAWL_SUMMARY,
  top_issues: [ISSUE_MISSING_TITLE, ISSUE_NOINDEX_IMPORTANT, ISSUE_404, ISSUE_BROKEN_LINK, ISSUE_MISSING_META],
};

export const mockPageAuditResult: PageAuditResult = page({
  path: "/collections/running-shoes",
  status_code: 200,
  score: 78,
  title: "Running Shoes",
  meta_description: null,
  word_count: 410,
  issues: [ISSUE_MISSING_META],
  images_missing_alt: 3,
  response_time_ms: 260,
  depth: 0,
});

// ---------------------------------------------------------------------------
// On-page / content editor
// ---------------------------------------------------------------------------

const ONPAGE_CHECKS: OnPageCheck[] = [
  { code: "title_contains_keyword", label: "Focus keyword in SEO title", category: "basic_seo", passed: true, weight: 3, message: `"${DEMO_TARGET_KEYWORD}" appears in the title.` },
  { code: "meta_contains_keyword", label: "Focus keyword in meta description", category: "basic_seo", passed: false, weight: 2, message: "Meta description is missing the focus keyword." },
  { code: "keyword_in_url", label: "Focus keyword in URL slug", category: "basic_seo", passed: true, weight: 2, message: "Slug includes the keyword." },
  { code: "keyword_in_intro", label: "Keyword used in the first 10% of content", category: "basic_seo", passed: true, weight: 2, message: "Keyword appears in the opening paragraph." },
  { code: "keyword_density", label: "Keyword density within target range", category: "basic_seo", passed: false, weight: 2, message: "Density is 0.4% — aim for 0.8%-1.5%." },
  { code: "content_length", label: "Content length meets target word count", category: "additional_seo", passed: false, weight: 2, message: "870 words vs. a 1,400-1,900 word target." },
  { code: "image_alt_keyword", label: "At least one image alt attribute contains the keyword", category: "additional_seo", passed: false, weight: 1, message: "No image alt text references the keyword." },
  { code: "external_links", label: "Links out to an authoritative external source", category: "additional_seo", passed: true, weight: 1, message: "1 external link to a reputable source found." },
  { code: "internal_links", label: "Links to other pages on the site", category: "additional_seo", passed: true, weight: 1, message: "3 internal links found." },
  { code: "title_length", label: "SEO title length is 50-60 characters", category: "title_readability", passed: true, weight: 1, message: "Title is 54 characters." },
  { code: "title_power_word", label: "Title contains a power word", category: "title_readability", passed: false, weight: 1, message: 'Consider adding a power word like "Ultimate" or "Proven".' },
  { code: "short_paragraphs", label: "Paragraphs are easy to scan (under 150 words)", category: "content_readability", passed: true, weight: 1, message: "All paragraphs are under 120 words." },
  { code: "transition_words", label: "Uses transition words", category: "content_readability", passed: false, weight: 1, message: "Only 8% of sentences use a transition word — aim for 30%+." },
];

export const mockOnPageResult: OnPageResult = {
  target_keyword: DEMO_TARGET_KEYWORD,
  score: 72,
  grade: "C",
  passed_count: 7,
  total_count: 13,
  checks: ONPAGE_CHECKS,
  issues: [ISSUE_KEYWORD_DENSITY, ISSUE_THIN_CONTENT],
  category_scores: {
    basic_seo: 62,
    additional_seo: 55,
    title_readability: 75,
    content_readability: 68,
  },
};

const TERM_TARGETS: TermTarget[] = [
  { term: "running shoes", current_count: 9, recommended_min: 8, recommended_max: 14, status: "optimal", in_headings: true, importance: 1 },
  { term: "beginners", current_count: 2, recommended_min: 4, recommended_max: 8, status: "under", in_headings: true, importance: 0.9 },
  { term: "cushioning", current_count: 0, recommended_min: 3, recommended_max: 6, status: "under", in_headings: false, importance: 0.8 },
  { term: "heel-to-toe drop", current_count: 0, recommended_min: 2, recommended_max: 4, status: "under", in_headings: false, importance: 0.6 },
  { term: "shoes", current_count: 21, recommended_min: 6, recommended_max: 16, status: "over", in_headings: true, importance: 0.7 },
  { term: "arch support", current_count: 3, recommended_min: 2, recommended_max: 5, status: "optimal", in_headings: false, importance: 0.5 },
];

export const mockContentScore: ContentScore = {
  target_keyword: DEMO_TARGET_KEYWORD,
  content_score: 74,
  seo_score: 70,
  ai_search_score: 66,
  word_count: 870,
  word_count_target_min: 1400,
  word_count_target_max: 1900,
  headings_count: 4,
  headings_target: 7,
  images_count: 2,
  images_target: 4,
  term_targets: TERM_TARGETS,
  missing_terms: ["cushioning", "heel-to-toe drop", "trail vs. road"],
  overused_terms: ["shoes"],
  suggestions: [
    "Add a comparison table for the top 3 beginner shoe picks.",
    'Cover "heel-to-toe drop" — 6 of 8 top-ranking pages mention it.',
    "Expand to at least 1,400 words to match the top-10 average.",
    "Add 2 more subheadings to break up the middle section.",
  ],
};

// ---------------------------------------------------------------------------
// Keyword research / SERP
// ---------------------------------------------------------------------------

function kw(args: {
  keyword: string;
  volume: number;
  difficulty: number;
  cpc: number;
  competition: number;
  intent: SearchIntent;
  parent_topic?: string | null;
  serp_features?: SerpFeature[];
}): Keyword {
  return {
    keyword: args.keyword,
    search_volume: args.volume,
    difficulty: args.difficulty,
    cpc: args.cpc,
    competition: args.competition,
    intent: args.intent,
    parent_topic: args.parent_topic ?? null,
    serp_features: args.serp_features ?? [],
  };
}

const KW_BEST_FOR_BEGINNERS = kw({ keyword: DEMO_TARGET_KEYWORD, volume: 8100, difficulty: 38, cpc: 1.85, competition: 0.62, intent: "commercial", parent_topic: "running shoes for beginners", serp_features: ["featured_snippet", "people_also_ask"] });
const KW_FOR_BEGINNERS = kw({ keyword: "running shoes for beginners", volume: 5400, difficulty: 34, cpc: 1.6, competition: 0.55, intent: "commercial", parent_topic: "running shoes for beginners", serp_features: ["people_also_ask"] });
const KW_HOW_TO_CHOOSE = kw({ keyword: "how to choose running shoes", volume: 2900, difficulty: 29, cpc: 0.9, competition: 0.4, intent: "informational", parent_topic: "running shoes for beginners", serp_features: ["featured_snippet"] });
const KW_BEGINNER_GUIDE = kw({ keyword: "beginner running shoe guide", volume: 480, difficulty: 22, cpc: 0.7, competition: 0.3, intent: "informational", parent_topic: "running shoes for beginners" });

const KW_TRAIL = kw({ keyword: "trail running shoes", volume: 33100, difficulty: 45, cpc: 1.2, competition: 0.58, intent: "commercial", parent_topic: "shoe types & fit", serp_features: ["shopping", "image_pack"] });
const KW_ROAD = kw({ keyword: "road running shoes", volume: 6600, difficulty: 41, cpc: 1.1, competition: 0.5, intent: "commercial", parent_topic: "shoe types & fit", serp_features: ["shopping"] });
const KW_FLAT_FEET = kw({ keyword: "running shoes for flat feet", volume: 9900, difficulty: 36, cpc: 1.75, competition: 0.6, intent: "commercial", parent_topic: "shoe types & fit", serp_features: ["people_also_ask"] });
const KW_OVERPRONATION = kw({ keyword: "running shoes for overpronation", volume: 4400, difficulty: 33, cpc: 1.9, competition: 0.63, intent: "commercial", parent_topic: "shoe types & fit" });
const KW_MINIMALIST = kw({ keyword: "minimalist running shoes", volume: 3600, difficulty: 39, cpc: 1.05, competition: 0.48, intent: "commercial", parent_topic: "shoe types & fit" });

const KW_NIKE_VS_BROOKS = kw({ keyword: "nike vs brooks running shoes", volume: 1900, difficulty: 25, cpc: 0.6, competition: 0.35, intent: "commercial", parent_topic: "comparisons & reviews", serp_features: ["people_also_ask"] });
const KW_BEST_2026 = kw({ keyword: "best running shoes 2026", volume: 14800, difficulty: 52, cpc: 1.4, competition: 0.7, intent: "commercial", parent_topic: "comparisons & reviews", serp_features: ["featured_snippet", "ai_overview"] });
const KW_REVIEW = kw({ keyword: "running shoes review", volume: 5900, difficulty: 44, cpc: 1.15, competition: 0.55, intent: "informational", parent_topic: "comparisons & reviews" });

const KW_NEAR_ME = kw({ keyword: "running shoes near me", volume: 12100, difficulty: 30, cpc: 2.4, competition: 0.75, intent: "navigational", serp_features: ["local_pack", "sitelinks"] });
const KW_SIZE_CHART = kw({ keyword: "running shoe size chart", volume: 3300, difficulty: 18, cpc: 0.4, competition: 0.2, intent: "informational", serp_features: ["featured_snippet"] });

const KEYWORD_CLUSTERS: KeywordCluster[] = [
  {
    name: "Beginner Buying Guides",
    keywords: [KW_BEST_FOR_BEGINNERS, KW_FOR_BEGINNERS, KW_HOW_TO_CHOOSE, KW_BEGINNER_GUIDE],
    total_volume: 16880,
    avg_difficulty: 30.75,
  },
  {
    name: "Shoe Types & Fit",
    keywords: [KW_TRAIL, KW_ROAD, KW_FLAT_FEET, KW_OVERPRONATION, KW_MINIMALIST],
    total_volume: 57600,
    avg_difficulty: 38.8,
  },
  {
    name: "Comparisons & Reviews",
    keywords: [KW_NIKE_VS_BROOKS, KW_BEST_2026, KW_REVIEW],
    total_volume: 22600,
    avg_difficulty: 40.3,
  },
];

export const mockKeywordResearchResult: KeywordResearchResult = {
  seed: DEMO_SEED_KEYWORD,
  country: DEMO_COUNTRY,
  keywords: [
    KW_BEST_FOR_BEGINNERS,
    KW_FOR_BEGINNERS,
    KW_HOW_TO_CHOOSE,
    KW_BEGINNER_GUIDE,
    KW_TRAIL,
    KW_ROAD,
    KW_FLAT_FEET,
    KW_OVERPRONATION,
    KW_MINIMALIST,
    KW_NIKE_VS_BROOKS,
    KW_BEST_2026,
    KW_REVIEW,
    KW_NEAR_ME,
    KW_SIZE_CHART,
  ],
  clusters: KEYWORD_CLUSTERS,
  total_keywords: 14,
};

const SERP_RESULTS: SerpResultItem[] = [
  { position: 1, url: "https://www.runnersworld.com/gear/best-running-shoes-beginners", domain: "runnersworld.com", title: "The 14 Best Running Shoes for Beginners in 2026", snippet: "We tested dozens of pairs to find the best running shoes for beginners across budgets and foot types.", word_count: 3200, backlinks: 1450 },
  { position: 2, url: "https://www.nytimes.com/wirecutter/reviews/best-running-shoes/", domain: "nytimes.com", title: "Best Running Shoes | Reviews by Wirecutter", snippet: "After 250+ hours of testing, these are the running shoes we recommend for new and experienced runners.", word_count: 4100, backlinks: 2870 },
  { position: 3, url: "https://www.verywellfit.com/best-running-shoes-for-beginners", domain: "verywellfit.com", title: "9 Best Running Shoes for Beginners, Tested by Editors", snippet: "Our top picks balance cushioning, support and price for runners just getting started.", word_count: 2600, backlinks: 640 },
  { position: 4, url: "https://www.self.com/story/best-running-shoes-new-runners", domain: "self.com", title: "The Best Running Shoes for New Runners", snippet: "Podiatrists and coaches weigh in on what beginners should look for in a first pair.", word_count: 2100, backlinks: 510 },
  { position: 5, url: "https://runrepeat.com/guides/best-beginner-running-shoes", domain: "runrepeat.com", title: "Best Beginner Running Shoes, Ranked by Lab Data", snippet: "We rank beginner running shoes using lab-tested cushioning, flexibility and durability data.", word_count: 3800, backlinks: 980 },
  { position: 6, url: "https://www.healthline.com/health/fitness/best-running-shoes-for-beginners", domain: "healthline.com", title: "10 Best Running Shoes for Beginners", snippet: "A physical-therapist-reviewed roundup of running shoes for new runners.", word_count: 1900, backlinks: 720 },
  { position: 7, url: `${DEMO_URL}/collections/running-shoes`, domain: "example-shop.com", title: "Running Shoes", snippet: "Shop running shoes for every level.", word_count: 410, backlinks: 38 },
  { position: 8, url: "https://www.brooksrunning.com/en_us/beginner-running-shoes", domain: "brooksrunning.com", title: "Beginner Running Shoes | Brooks Running", snippet: "Shop Brooks running shoes built for comfort from your very first mile.", word_count: 1500, backlinks: 3200 },
  { position: 9, url: "https://www.reddit.com/r/running/comments/best_beginner_shoe/", domain: "reddit.com", title: "Best beginner running shoe recommendations? : r/running", snippet: "Runners share which shoes worked for them when they were just starting out.", word_count: 800, backlinks: 120 },
  { position: 10, url: "https://www.shape.com/best-running-shoes-for-beginners", domain: "shape.com", title: "Best Running Shoes for Beginners, According to Experts", snippet: "Trainers and podiatrists share their top picks for new runners.", word_count: 2300, backlinks: 460 },
];

export const mockSerpAnalysis: SerpAnalysis = {
  keyword: DEMO_TARGET_KEYWORD,
  country: DEMO_COUNTRY,
  device: "desktop",
  results: SERP_RESULTS,
  features: ["featured_snippet", "people_also_ask", "ai_overview"],
  avg_word_count: 2271,
  avg_backlinks: 1099,
  difficulty: 42,
};

// ---------------------------------------------------------------------------
// Rank tracking
// ---------------------------------------------------------------------------

const HISTORY_DAYS = ["2026-07-04", "2026-07-05", "2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10"];

function makeHistory(positions: Array<number | null>, url: string): RankPoint[] {
  return positions.map((position, i) => ({
    day: HISTORY_DAYS[i],
    position,
    url: position === null ? null : url,
  }));
}

function trackedKeyword(args: {
  keyword: string;
  current: number | null;
  previous: number | null;
  best: number | null;
  volume: number;
  positions: Array<number | null>;
  device?: Device;
  path?: string;
}): TrackedKeyword {
  return {
    keyword: args.keyword,
    domain: DEMO_DOMAIN,
    country: DEMO_COUNTRY,
    device: args.device ?? "desktop",
    search_volume: args.volume,
    current_position: args.current,
    previous_position: args.previous,
    best_position: args.best,
    history: makeHistory(args.positions, `${DEMO_URL}${args.path ?? "/"}`),
  };
}

const TRACKED_KEYWORDS: TrackedKeyword[] = [
  trackedKeyword({ keyword: "running shoes near me", current: 3, previous: 4, best: 3, volume: 12100, positions: [6, 5, 5, 4, 4, 4, 3], path: "/" }),
  trackedKeyword({ keyword: DEMO_TARGET_KEYWORD, current: 7, previous: 9, best: 7, volume: 8100, positions: [12, 11, 10, 9, 9, 8, 7], path: "/collections/running-shoes" }),
  trackedKeyword({ keyword: "running shoes for beginners", current: 11, previous: 10, best: 8, volume: 5400, positions: [8, 8, 9, 9, 10, 10, 11], path: "/collections/running-shoes" }),
  trackedKeyword({ keyword: "trail running shoes", current: 15, previous: 15, best: 13, volume: 33100, positions: [14, 13, 14, 15, 15, 15, 15], path: "/collections/trail-running" }),
  trackedKeyword({ keyword: "running shoes for flat feet", current: 6, previous: 8, best: 6, volume: 9900, positions: [10, 9, 9, 8, 8, 7, 6], path: "/collections/running-shoes" }),
  trackedKeyword({ keyword: "best running shoes 2026", current: null, previous: null, best: null, volume: 14800, positions: [null, null, null, null, null, null, null] }),
  trackedKeyword({ keyword: "minimalist running shoes", current: 22, previous: 19, best: 17, volume: 3600, positions: [17, 18, 18, 19, 19, 20, 22] }),
  trackedKeyword({ keyword: "running shoe size chart", current: 4, previous: 4, best: 2, volume: 3300, positions: [3, 3, 4, 4, 4, 4, 4] }),
];

export const mockRankTrackingSummary: RankTrackingSummary = {
  domain: DEMO_DOMAIN,
  country: DEMO_COUNTRY,
  total_keywords: 8,
  avg_position: 9.7,
  improved: 3,
  declined: 2,
  unchanged: 2,
  top3: 1,
  top10: 4,
  visibility_score: 61.4,
  keywords: TRACKED_KEYWORDS,
};

// ---------------------------------------------------------------------------
// Action plan
// ---------------------------------------------------------------------------

function task(args: {
  id: string;
  title: string;
  description: string;
  category: IssueCategory;
  priority: Severity;
  status: TaskStatus;
  page_url?: string | null;
  keyword?: string | null;
  impact: number;
  effort: Effort;
  ai_review?: AiReview | null;
}): Task {
  return {
    id: args.id,
    title: args.title,
    description: args.description,
    category: args.category,
    priority: args.priority,
    status: args.status,
    page_url: args.page_url ?? null,
    keyword: args.keyword ?? null,
    impact: args.impact,
    effort: args.effort,
    ai_review: args.ai_review ?? null,
  };
}

const ACTION_TASKS: Task[] = [
  task({
    id: "task_001",
    title: "Add a meta description to /collections/running-shoes",
    description: "Highest-traffic category page currently has no meta description.",
    category: "on_page",
    priority: "high",
    status: "todo",
    page_url: `${DEMO_URL}/collections/running-shoes`,
    impact: 4,
    effort: "low",
    ai_review: { verdict: "pass", reasoning: "High-traffic category page has zero meta description; quick win.", confidence: 0.92 },
  }),
  task({
    id: "task_002",
    title: "Fix the 404 on /old-catalog",
    description: "Redirect the dead URL to the nearest live equivalent.",
    category: "technical",
    priority: "critical",
    status: "todo",
    page_url: `${DEMO_URL}/old-catalog`,
    impact: 5,
    effort: "low",
    ai_review: { verdict: "pass", reasoning: "Broken internal destination found in the latest crawl; likely losing link equity.", confidence: 0.95 },
  }),
  task({
    id: "task_003",
    title: "Write a unique title tag for the Aero Trail Runner PDP",
    description: "Product page currently renders with no <title> element.",
    category: "on_page",
    priority: "high",
    status: "in_progress",
    page_url: `${DEMO_URL}/products/aero-trail-runner`,
    impact: 4,
    effort: "low",
  }),
  task({
    id: "task_004",
    title: "Expand the beginner buying guide to 1,400+ words",
    description: "Current draft is 280 words; top-10 competitors average 2,271.",
    category: "content",
    priority: "medium",
    status: "todo",
    page_url: `${DEMO_URL}/blog/running-tips`,
    keyword: DEMO_TARGET_KEYWORD,
    impact: 3,
    effort: "medium",
    ai_review: { verdict: "pass", reasoning: "Top-10 competitors average 2,271 words; current page is 280.", confidence: 0.81 },
  }),
  task({
    id: "task_005",
    title: "Add alt text across the product gallery",
    description: "6 images missing descriptive alt attributes on the PDP.",
    category: "images",
    priority: "medium",
    status: "todo",
    page_url: `${DEMO_URL}/products/aero-trail-runner`,
    impact: 2,
    effort: "low",
  }),
  task({
    id: "task_006",
    title: "Resolve the redirect chain on /collections/trail-running",
    description: "Internal links point at a URL that 301s instead of the final destination.",
    category: "technical",
    priority: "low",
    status: "flagged",
    page_url: `${DEMO_URL}/collections/trail-running`,
    impact: 2,
    effort: "medium",
    ai_review: { verdict: "flag", reasoning: "Redirect target could not be confirmed automatically — needs manual check.", confidence: 0.4 },
  }),
  task({
    id: "task_007",
    title: "Link from the homepage to the beginner guide",
    description: "Adds a relevant internal link and topical signal for the target keyword.",
    category: "links",
    priority: "medium",
    status: "done",
    page_url: DEMO_URL,
    keyword: DEMO_TARGET_KEYWORD,
    impact: 3,
    effort: "low",
  }),
  task({
    id: "task_008",
    title: "Publish a comparison table for the top 3 beginner picks",
    description: "Matches a common SERP pattern among top-ranking competitor pages.",
    category: "content",
    priority: "medium",
    status: "todo",
    keyword: DEMO_TARGET_KEYWORD,
    impact: 3,
    effort: "high",
  }),
];

export const mockActionPlan: ActionPlan = {
  site: DEMO_URL,
  generated_at: "2026-07-10T09:20:00Z",
  tasks: ACTION_TASKS,
  total: 8,
  by_priority: { critical: 1, high: 2, medium: 4, low: 1, info: 0 },
  by_status: { todo: 5, in_progress: 1, done: 1, flagged: 1 },
};

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export const mockBranding: WhiteLabelBranding = {
  agency_name: "Scaling Firm",
  logo_url: null,
  primary_color: "#4f46e5",
  accent_color: "#22d3ee",
  footer_text: "Prepared by Scaling Firm — MySEOapp confidential.",
  agent_name: "Hikebot",
  agent_icon_url: null,
  contact_email: "hello@scalingfirm.com",
};

const REPORT_SECTIONS: ReportSection[] = [
  {
    title: "Executive Summary",
    type: "summary",
    summary: "Site health improved 6 points this period; 3 keywords broke into the top 10.",
    data: { site_health: 78, health_delta: 6, keywords_top10: 4 },
  },
  {
    title: "Technical & On-Page Audit",
    type: "audit",
    summary: "7 pages crawled, 5 with open issues. Average score 57/100.",
    data: { pages_crawled: 7, avg_score: 57, critical_issues: 1 },
  },
  {
    title: "Keyword Rankings",
    type: "rankings",
    summary: "Average position 9.7 across 8 tracked keywords; visibility score 61.4.",
    data: { avg_position: 9.7, visibility_score: 61.4, improved: 3, declined: 2 },
  },
  {
    title: "Action Plan Progress",
    type: "tasks",
    summary: "1 of 8 tasks completed this period; 1 critical fix still open.",
    data: { total: 8, done: 1, todo: 5 },
  },
];

export const mockReport: Report = {
  report_id: "report_demo_0001",
  site: DEMO_URL,
  period_start: "2026-06-10",
  period_end: "2026-07-10",
  generated_at: "2026-07-10T09:25:00Z",
  branding: mockBranding,
  sections: REPORT_SECTIONS,
  headline_metrics: { site_health: 78, avg_position: 9.7, tracked_keywords: 8, open_tasks: 6 },
};

// ---------------------------------------------------------------------------
// Integrations
// ---------------------------------------------------------------------------

function delivery(args: {
  id: string;
  target: string;
  lead_id?: string | null;
  status: DeliveryLog["status"];
  attempts: number;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
  response_ref?: string | null;
}): DeliveryLog {
  return {
    id: args.id,
    target: args.target,
    lead_id: args.lead_id ?? null,
    status: args.status,
    attempts: args.attempts,
    last_error: args.last_error ?? null,
    created_at: args.created_at,
    updated_at: args.updated_at,
    response_ref: args.response_ref ?? null,
  };
}

export const mockDeliveries: DeliveryLog[] = [
  delivery({ id: "dlv_1001", target: "crm:mock", lead_id: "lead_2001", status: "delivered", attempts: 1, created_at: "2026-07-09T14:02:11Z", updated_at: "2026-07-09T14:02:13Z", response_ref: "crm_ref_88213" }),
  delivery({ id: "dlv_1002", target: "make:scenario", lead_id: "lead_2001", status: "sent", attempts: 1, created_at: "2026-07-09T14:02:11Z", updated_at: "2026-07-09T14:02:12Z", response_ref: "scenario_run_5541" }),
  delivery({ id: "dlv_1003", target: "crm:mock", lead_id: "lead_2002", status: "failed", attempts: 3, last_error: "Upstream CRM returned 503", created_at: "2026-07-08T09:44:00Z", updated_at: "2026-07-08T09:47:22Z" }),
  delivery({ id: "dlv_1004", target: "webhook:zapier", lead_id: "lead_2003", status: "pending", attempts: 0, created_at: "2026-07-10T08:10:05Z", updated_at: "2026-07-10T08:10:05Z" }),
  delivery({ id: "dlv_1005", target: "crm:mock", lead_id: "lead_2003", status: "validated", attempts: 1, created_at: "2026-07-10T08:10:05Z", updated_at: "2026-07-10T08:10:06Z" }),
  delivery({ id: "dlv_1006", target: "make:scenario", lead_id: "lead_2004", status: "rejected", attempts: 1, last_error: "Missing required field: email", created_at: "2026-07-07T11:15:40Z", updated_at: "2026-07-07T11:15:41Z" }),
];

export const mockLeadValidationResult: LeadValidationResult = {
  valid: true,
  normalized: {
    id: "lead_demo_offline",
    name: "",
    email: "",
    phone: null,
    company: null,
    website: null,
    source: "mini_audit",
    message: null,
    custom_fields: {},
    created_at: "2026-07-10T09:30:00Z",
  } satisfies LeadRecord,
  errors: [],
  warnings: ["Running in offline demo mode — this lead was not actually delivered."],
};

// ---------------------------------------------------------------------------
// SaaS: orgs, members, API keys, billing plans/subscription, usage
// ---------------------------------------------------------------------------

export const MOCK_ORG_ID = "org_demo_0001";

export const mockOrgs: Org[] = [
  { id: "org_demo_0001", name: "Scaling Firm", slug: "scaling-firm", plan_code: "agency", role: "owner" },
  { id: "org_demo_0002", name: "Example Shop Co", slug: "example-shop-co", plan_code: "pro", role: "editor" },
];

export const mockCurrentOrg: CurrentOrg = {
  id: "org_demo_0001",
  name: "Scaling Firm",
  plan_code: "agency",
  role: "owner",
  subscription: { plan_code: "agency", status: "active" },
};

export const mockMembers: Member[] = [
  { user_id: "user_demo_0001", email: "owner@example.com", role: "owner", status: "active" },
  { user_id: "user_demo_0002", email: "priya@scalingfirm.com", role: "agency_admin", status: "active" },
  { user_id: "user_demo_0003", email: "sam@scalingfirm.com", role: "editor", status: "active" },
  { user_id: "user_demo_0004", email: "client@example-shop.com", role: "client", status: "invited" },
];

export const mockApiKeys: ApiKey[] = [
  {
    id: "key_demo_0001",
    name: "CI pipeline",
    prefix: "msk_live",
    last4: "7f2a",
    role: "editor",
    revoked: false,
    created_at: "2026-06-02T10:00:00Z",
    last_used_at: "2026-07-09T18:22:00Z",
  },
  {
    id: "key_demo_0002",
    name: "Zapier",
    prefix: "msk_live",
    last4: "c93d",
    role: "client",
    revoked: false,
    created_at: "2026-05-14T09:30:00Z",
    last_used_at: null,
  },
];

const PLAN_FREE: Plan = {
  code: "free",
  name: "Free",
  price_monthly: 0,
  price_annual: 0,
  description: "Try the platform on a single site.",
  limits: {
    sites: 1,
    tracked_keywords: 25,
    crawls_per_month: 5,
    pages_per_crawl: 100,
    content_scores_per_month: 10,
    keyword_lookups_per_month: 50,
    reports_per_month: 2,
    seats: 1,
  },
  features: [],
  is_custom: false,
};

const PLAN_STARTER: Plan = {
  code: "starter",
  name: "Starter",
  price_monthly: 29,
  price_annual: 290,
  description: "For freelancers and small businesses.",
  limits: {
    sites: 3,
    tracked_keywords: 200,
    crawls_per_month: 30,
    pages_per_crawl: 1_000,
    content_scores_per_month: 100,
    keyword_lookups_per_month: 500,
    reports_per_month: 20,
    seats: 3,
  },
  features: ["api_access", "content_ai"],
  is_custom: false,
};

const PLAN_PRO: Plan = {
  code: "pro",
  name: "Pro",
  price_monthly: 79,
  price_annual: 790,
  description: "For in-house SEO teams.",
  limits: {
    sites: 10,
    tracked_keywords: 1_000,
    crawls_per_month: 150,
    pages_per_crawl: 10_000,
    content_scores_per_month: 500,
    keyword_lookups_per_month: 2_500,
    reports_per_month: 100,
    seats: 10,
  },
  features: ["api_access", "competitor_analysis", "content_ai", "mcp_access", "scheduled_crawls"],
  is_custom: false,
};

const PLAN_AGENCY: Plan = {
  code: "agency",
  name: "Agency",
  price_monthly: 199,
  price_annual: 1_990,
  description: "For agencies managing many client sites, with white-label reporting.",
  limits: {
    sites: 50,
    tracked_keywords: 5_000,
    crawls_per_month: 1_000,
    pages_per_crawl: 50_000,
    content_scores_per_month: 2_500,
    keyword_lookups_per_month: 10_000,
    reports_per_month: 1_000,
    seats: 25,
  },
  features: [
    "api_access",
    "competitor_analysis",
    "content_ai",
    "mcp_access",
    "priority_support",
    "scheduled_crawls",
    "white_label",
  ],
  is_custom: false,
};

const PLAN_ENTERPRISE: Plan = {
  code: "enterprise",
  name: "Enterprise",
  price_monthly: 0,
  price_annual: 0,
  description: "Custom limits, SSO, and priority support.",
  limits: {
    sites: -1,
    tracked_keywords: -1,
    crawls_per_month: -1,
    pages_per_crawl: -1,
    content_scores_per_month: -1,
    keyword_lookups_per_month: -1,
    reports_per_month: -1,
    seats: -1,
  },
  features: [
    "api_access",
    "competitor_analysis",
    "content_ai",
    "mcp_access",
    "priority_support",
    "scheduled_crawls",
    "white_label",
  ],
  is_custom: true,
};

export const mockPlans: Plan[] = [PLAN_FREE, PLAN_STARTER, PLAN_PRO, PLAN_AGENCY, PLAN_ENTERPRISE];

export const mockSubscription: Subscription = {
  plan_code: "agency",
  status: "active",
  provider: "mock",
  current_period_end: "2026-08-10T00:00:00Z",
  seats: 25,
  plan: PLAN_AGENCY,
};

export const mockUsage: Usage = {
  plan_code: "agency",
  monthly: {
    crawls_per_month: { used: 42, limit: 1_000 },
    content_scores_per_month: { used: 210, limit: 2_500 },
    keyword_lookups_per_month: { used: 1_380, limit: 10_000 },
    reports_per_month: { used: 6, limit: 1_000 },
  },
  resources: {
    sites: { used: 7, limit: 50 },
    tracked_keywords: { used: 8, limit: 5_000 },
  },
};
