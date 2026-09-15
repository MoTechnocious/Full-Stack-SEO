/**
 * Static, fully-deterministic mock data for the AI-search + local modules
 * (GEO, PEO, AEO, Kit assistant, Local SEO), matching the interfaces in
 * `./api`. Same contract as `./mock`: used as a graceful fallback whenever a
 * live API call fails, hand-picked values only (no randomness / clock reads)
 * so server- and client-rendered output always match.
 */
import type {
  ActionItemPlan,
  BioResult,
  CitationStatusReport,
  ClusterMapResult,
  ContentCalendar,
  CorroborationReport,
  DomainTrustReport,
  EntitySchemaResult,
  EntitySearchResult,
  GbpMetrics,
  GbpPost,
  KeywordMapResult,
  LinkSuggestResult,
  NapRecord,
  PromptResearchResult,
  PromptTrackerReport,
  QuestionExtractionResult,
  QueuedAction,
  ReadinessReport,
  ReviewListResponse,
  SchemaGraphResult,
  SensorReport,
  SentimentReport,
  TrackedPrompt,
  VisibilityReport,
  VoiceAuditResult,
} from "./api";

// ---------------------------------------------------------------------------
// Demo constants
// ---------------------------------------------------------------------------

export const DEMO_BRAND = "Example Shop";
export const DEMO_COMPETITORS = ["RunnerHub", "StridePro"];
export const DEMO_ENTITY_QUERY = "Jane Doe";
export const DEMO_PROMPT_TOPIC = "running shoes";

// ---------------------------------------------------------------------------
// GEO — visibility
// ---------------------------------------------------------------------------

export const mockVisibilityReport: VisibilityReport = {
  brand: DEMO_BRAND,
  competitors: DEMO_COMPETITORS,
  scanned_on: "2026-07-08",
  engines: [
    {
      engine: "chatgpt",
      prompts_scanned: 12,
      mentions: 9,
      mention_frequency: 0.75,
      share_of_voice: 0.42,
      avg_position: 1.8,
      mention_frequency_delta: 0.08,
      share_of_voice_delta: 0.05,
      avg_position_delta: 0.4,
    },
    {
      engine: "claude",
      prompts_scanned: 12,
      mentions: 8,
      mention_frequency: 0.67,
      share_of_voice: 0.38,
      avg_position: 2.1,
      mention_frequency_delta: 0.02,
      share_of_voice_delta: -0.01,
      avg_position_delta: 0,
    },
    {
      engine: "perplexity",
      prompts_scanned: 12,
      mentions: 10,
      mention_frequency: 0.83,
      share_of_voice: 0.46,
      avg_position: 1.5,
      mention_frequency_delta: 0.12,
      share_of_voice_delta: 0.07,
      avg_position_delta: 0.6,
    },
    {
      engine: "copilot",
      prompts_scanned: 12,
      mentions: 6,
      mention_frequency: 0.5,
      share_of_voice: 0.29,
      avg_position: 2.9,
      mention_frequency_delta: -0.04,
      share_of_voice_delta: -0.03,
      avg_position_delta: -0.3,
    },
    {
      engine: "gemini",
      prompts_scanned: 12,
      mentions: 7,
      mention_frequency: 0.58,
      share_of_voice: 0.33,
      avg_position: 2.4,
      mention_frequency_delta: 0.05,
      share_of_voice_delta: 0.02,
      avg_position_delta: 0.2,
    },
    {
      engine: "google_ai_overviews",
      prompts_scanned: 12,
      mentions: 5,
      mention_frequency: 0.42,
      share_of_voice: 0.24,
      avg_position: 3.2,
      mention_frequency_delta: 0.03,
      share_of_voice_delta: 0.01,
      avg_position_delta: 0.1,
    },
  ],
  overall: {
    prompts_scanned: 72,
    mentions: 45,
    mention_frequency: 0.63,
    share_of_voice: 0.35,
    avg_position: 2.3,
    mention_frequency_delta: 0.04,
    share_of_voice_delta: 0.02,
    avg_position_delta: 0.2,
  },
  competitor_share_of_voice: { RunnerHub: 0.38, StridePro: 0.27 },
  answers: [],
};

// ---------------------------------------------------------------------------
// GEO — prompt library / research / tracker
// ---------------------------------------------------------------------------

export const mockTrackedPrompts: TrackedPrompt[] = [
  {
    id: "prm_0001",
    text: "what are the best running shoes for beginners",
    funnel_stage: "tofu",
    intent_tags: ["discovery", "best-of"],
    volume_estimate: 3400,
    created_on: "2026-06-12",
  },
  {
    id: "prm_0002",
    text: "example shop vs runnerhub which is better",
    funnel_stage: "mofu",
    intent_tags: ["comparison"],
    volume_estimate: 880,
    created_on: "2026-06-18",
  },
  {
    id: "prm_0003",
    text: "is example shop legit and worth buying from",
    funnel_stage: "bofu",
    intent_tags: ["trust", "purchase-intent"],
    volume_estimate: 590,
    created_on: "2026-06-25",
  },
  {
    id: "prm_0004",
    text: "where to buy trail running shoes online",
    funnel_stage: "bofu",
    intent_tags: ["purchase-intent"],
    volume_estimate: 1200,
    created_on: "2026-07-01",
  },
];

export const mockPromptResearchResult: PromptResearchResult = {
  topic: DEMO_PROMPT_TOPIC,
  suggestions: [
    {
      text: "what running shoes do experts recommend for flat feet",
      funnel_stage: "tofu",
      intent_tags: ["discovery"],
      volume_estimate: 2100,
    },
    {
      text: "best budget running shoes compared",
      funnel_stage: "mofu",
      intent_tags: ["comparison", "budget"],
      volume_estimate: 1500,
    },
    {
      text: "which running shoe store has the best return policy",
      funnel_stage: "bofu",
      intent_tags: ["trust", "purchase-intent"],
      volume_estimate: 640,
    },
  ],
  total: 3,
};

export const mockPromptTrackerReport: PromptTrackerReport = {
  brand: DEMO_BRAND,
  total_prompts: 3,
  engines: ["chatgpt", "claude", "perplexity"],
  entries: [
    {
      prompt: mockTrackedPrompts[0],
      engines: [
        {
          engine: "chatgpt",
          current_rank: 2,
          previous_rank: 3,
          best_rank: 2,
          history: [
            { day: "2026-06-24", rank: 4 },
            { day: "2026-07-01", rank: 3 },
            { day: "2026-07-08", rank: 2 },
          ],
        },
        {
          engine: "claude",
          current_rank: 3,
          previous_rank: 3,
          best_rank: 2,
          history: [
            { day: "2026-06-24", rank: 2 },
            { day: "2026-07-01", rank: 3 },
            { day: "2026-07-08", rank: 3 },
          ],
        },
        {
          engine: "perplexity",
          current_rank: 1,
          previous_rank: 2,
          best_rank: 1,
          history: [
            { day: "2026-06-24", rank: 3 },
            { day: "2026-07-01", rank: 2 },
            { day: "2026-07-08", rank: 1 },
          ],
        },
      ],
    },
    {
      prompt: mockTrackedPrompts[1],
      engines: [
        {
          engine: "chatgpt",
          current_rank: 1,
          previous_rank: 1,
          best_rank: 1,
          history: [
            { day: "2026-06-24", rank: 1 },
            { day: "2026-07-01", rank: 1 },
            { day: "2026-07-08", rank: 1 },
          ],
        },
        {
          engine: "claude",
          current_rank: 2,
          previous_rank: 1,
          best_rank: 1,
          history: [
            { day: "2026-06-24", rank: 1 },
            { day: "2026-07-01", rank: 1 },
            { day: "2026-07-08", rank: 2 },
          ],
        },
        {
          engine: "perplexity",
          current_rank: null,
          previous_rank: 3,
          best_rank: 3,
          history: [
            { day: "2026-06-24", rank: null },
            { day: "2026-07-01", rank: 3 },
            { day: "2026-07-08", rank: null },
          ],
        },
      ],
    },
    {
      prompt: mockTrackedPrompts[3],
      engines: [
        {
          engine: "chatgpt",
          current_rank: 4,
          previous_rank: 5,
          best_rank: 4,
          history: [
            { day: "2026-06-24", rank: 6 },
            { day: "2026-07-01", rank: 5 },
            { day: "2026-07-08", rank: 4 },
          ],
        },
        {
          engine: "claude",
          current_rank: null,
          previous_rank: null,
          best_rank: null,
          history: [
            { day: "2026-06-24", rank: null },
            { day: "2026-07-01", rank: null },
            { day: "2026-07-08", rank: null },
          ],
        },
        {
          engine: "perplexity",
          current_rank: 3,
          previous_rank: 3,
          best_rank: 2,
          history: [
            { day: "2026-06-24", rank: 2 },
            { day: "2026-07-01", rank: 3 },
            { day: "2026-07-08", rank: 3 },
          ],
        },
      ],
    },
  ],
};

// ---------------------------------------------------------------------------
// GEO — citations / sentiment / readiness
// ---------------------------------------------------------------------------

export const mockDomainTrustReport: DomainTrustReport = {
  total_citations: 86,
  domains: [
    {
      domain: "reddit.com",
      category: "community",
      trust_weight: 0.9,
      citations: 21,
      frequency: 0.24,
      engines: ["chatgpt", "perplexity", "google_ai_overviews"],
      priority_score: 21.6,
    },
    {
      domain: "wikipedia.org",
      category: "encyclopedia",
      trust_weight: 0.95,
      citations: 14,
      frequency: 0.16,
      engines: ["claude", "gemini", "copilot"],
      priority_score: 15.2,
    },
    {
      domain: "g2.com",
      category: "review_platform",
      trust_weight: 0.85,
      citations: 12,
      frequency: 0.14,
      engines: ["chatgpt", "claude"],
      priority_score: 11.9,
    },
    {
      domain: "quora.com",
      category: "qa_forum",
      trust_weight: 0.7,
      citations: 9,
      frequency: 0.1,
      engines: ["perplexity"],
      priority_score: 7.0,
    },
    {
      domain: "runnersworld.com",
      category: "news",
      trust_weight: 0.75,
      citations: 8,
      frequency: 0.09,
      engines: ["gemini", "google_ai_overviews"],
      priority_score: 6.8,
    },
    {
      domain: "example-shop.com",
      category: "own_domain",
      trust_weight: 0.5,
      citations: 6,
      frequency: 0.07,
      engines: ["perplexity", "copilot"],
      priority_score: 3.5,
    },
  ],
};

export const mockSentimentReport: SentimentReport = {
  brand: DEMO_BRAND,
  scanned_on: "2026-07-08",
  cells: [
    { engine: "chatgpt", prompt: mockTrackedPrompts[0].text, label: "positive", score: 0.6 },
    { engine: "chatgpt", prompt: mockTrackedPrompts[1].text, label: "positive", score: 0.4 },
    { engine: "chatgpt", prompt: mockTrackedPrompts[2].text, label: "neutral", score: 0.1 },
    { engine: "claude", prompt: mockTrackedPrompts[0].text, label: "positive", score: 0.5 },
    { engine: "claude", prompt: mockTrackedPrompts[1].text, label: "neutral", score: 0.0 },
    { engine: "claude", prompt: mockTrackedPrompts[2].text, label: "positive", score: 0.3 },
    { engine: "perplexity", prompt: mockTrackedPrompts[0].text, label: "positive", score: 0.7 },
    { engine: "perplexity", prompt: mockTrackedPrompts[1].text, label: "negative", score: -0.4 },
    { engine: "perplexity", prompt: mockTrackedPrompts[2].text, label: "neutral", score: -0.1 },
    { engine: "gemini", prompt: mockTrackedPrompts[0].text, label: "neutral", score: 0.1 },
    { engine: "gemini", prompt: mockTrackedPrompts[1].text, label: "positive", score: 0.5 },
    { engine: "gemini", prompt: mockTrackedPrompts[2].text, label: "negative", score: -0.3 },
  ],
  per_engine: [
    { engine: "chatgpt", avg_score: 0.37, label: "positive" },
    { engine: "claude", avg_score: 0.27, label: "positive" },
    { engine: "perplexity", avg_score: 0.07, label: "neutral" },
    { engine: "gemini", avg_score: 0.1, label: "neutral" },
  ],
  overall_score: 0.2,
  overall_label: "neutral",
};

export const mockReadinessReport: ReadinessReport = {
  url: "https://www.example-shop.com",
  score: 68,
  grade: "D",
  passed_count: 7,
  total_count: 10,
  checks: [
    { code: "llms_txt", label: "llms.txt present", passed: false, weight: 3, message: "No llms.txt found at the site root." },
    { code: "robots_ai_access", label: "AI crawlers allowed in robots.txt", passed: true, weight: 3, message: "GPTBot, ClaudeBot and PerplexityBot are not blocked." },
    { code: "structured_data", label: "Structured data present", passed: true, weight: 2, message: "Organization and Product JSON-LD detected." },
    { code: "semantic_headings", label: "Semantic heading hierarchy", passed: true, weight: 1, message: "H1-H3 structure is clean and descriptive." },
    { code: "answerable_intro", label: "Direct-answer first paragraph", passed: false, weight: 2, message: "The intro takes 3 paragraphs before answering the page topic." },
    { code: "faq_blocks", label: "FAQ/Q&A blocks", passed: true, weight: 1, message: "2 FAQ sections found." },
    { code: "canonical", label: "Canonical URL declared", passed: true, weight: 1, message: "Canonical tag matches the final URL." },
    { code: "meta_description", label: "Meta description present", passed: true, weight: 1, message: "Meta description is 148 characters." },
    { code: "content_freshness", label: "Visible last-updated date", passed: false, weight: 1, message: "No dateModified or visible updated date found." },
    { code: "clean_html", label: "Extractable main content", passed: true, weight: 2, message: "Main content is server-rendered and readable without JS." },
  ],
  crawler_access: [
    { crawler: "GPTBot", allowed: true },
    { crawler: "ClaudeBot", allowed: true },
    { crawler: "PerplexityBot", allowed: true },
    { crawler: "Google-Extended", allowed: false },
    { crawler: "CCBot", allowed: false },
  ],
  fixes: [
    {
      code: "missing_llms_txt",
      title: "Publish an llms.txt file",
      description: "AI crawlers look for llms.txt to understand what your site offers and which pages matter.",
      category: "technical",
      severity: "high",
      recommendation: "Add /llms.txt with a short site summary and links to your most important pages.",
      url: null,
      details: {},
    },
    {
      code: "slow_answer",
      title: "Answer the page topic in the first paragraph",
      description: "Answer engines quote pages that resolve the query immediately.",
      category: "content",
      severity: "medium",
      recommendation: "Move a 40-55 word direct answer to the very top of the page.",
      url: null,
      details: {},
    },
    {
      code: "no_freshness_signal",
      title: "Expose a last-updated date",
      description: "Freshness signals increase the odds of being cited for time-sensitive queries.",
      category: "structured_data",
      severity: "low",
      recommendation: "Add dateModified to your Article/Product JSON-LD and show it on the page.",
      url: null,
      details: {},
    },
  ],
};

// ---------------------------------------------------------------------------
// PEO
// ---------------------------------------------------------------------------

export const mockEntitySearchResult: EntitySearchResult = {
  query: DEMO_ENTITY_QUERY,
  entities: [
    {
      kg_mid: "/g/11abc1d2e3",
      name: "Jane Doe",
      types: ["Person"],
      description: "Founder and CEO of Example Shop",
      result_score: 412.7,
      url: "https://www.example-shop.com/about/jane-doe",
    },
    {
      kg_mid: "/g/11xyz9w8v7",
      name: "Jane Doe (author)",
      types: ["Person"],
      description: "Author of Run Further",
      result_score: 128.4,
      url: null,
    },
    {
      kg_mid: "/m/0examplshp",
      name: "Example Shop",
      types: ["Organization", "Corporation"],
      description: "Online running-gear retailer",
      result_score: 96.1,
      url: "https://www.example-shop.com",
    },
  ],
};

export const mockSensorReport: SensorReport = {
  kg_mid: "/g/11abc1d2e3",
  name: "Jane Doe",
  observations: [
    { observed_at: "2026-04-20", score: 318.2 },
    { observed_at: "2026-05-04", score: 330.5 },
    { observed_at: "2026-05-18", score: 341.9 },
    { observed_at: "2026-06-01", score: 336.4 },
    { observed_at: "2026-06-15", score: 372.8 },
    { observed_at: "2026-06-29", score: 398.3 },
    { observed_at: "2026-07-08", score: 412.7 },
  ],
  latest_score: 412.7,
  mean_score: 358.7,
  net_change: 94.5,
  volatility: 14.2,
  trend: "rising",
};

export const mockBioResult: BioResult = {
  name: "Jane Doe",
  variants: [
    {
      length: "short",
      text: "Jane Doe is the founder and CEO of Example Shop, an online running-gear retailer. She is the author of Run Further and holds an MBA from Stanford University.",
      word_count: 28,
      triple_count: 4,
      triple_density: 2.0,
    },
    {
      length: "medium",
      text: "Jane Doe is the founder and CEO of Example Shop, an online running-gear retailer based in Austin, Texas. Doe founded Example Shop in 2018. She is the author of Run Further, a bestselling training guide. Doe holds an MBA from Stanford University and received the Retail Innovator Award in 2024.",
      word_count: 51,
      triple_count: 7,
      triple_density: 1.75,
    },
    {
      length: "long",
      text: "Jane Doe is the founder and CEO of Example Shop, an online running-gear retailer based in Austin, Texas. Doe founded Example Shop in 2018 after a decade in retail operations. She is the author of Run Further, a bestselling training guide published in 2022. Doe is also an angel investor in consumer fitness startups. She holds an MBA from Stanford University and received the Retail Innovator Award in 2024. Her official website is example-shop.com.",
      word_count: 76,
      triple_count: 10,
      triple_density: 1.67,
    },
  ],
  warnings: ["No image URL provided — consider adding a canonical headshot for entity panels."],
};

export const mockCorroborationReport: CorroborationReport = {
  entity_name: "Jane Doe",
  consistency_score: 67,
  sources_checked: 4,
  comparisons: [
    { source: "wikipedia", fact: "job_title", canonical_value: "Founder & CEO", found_value: "Founder & CEO", status: "match" },
    { source: "wikipedia", fact: "organization", canonical_value: "Example Shop", found_value: "Example Shop", status: "match" },
    { source: "wikidata", fact: "job_title", canonical_value: "Founder & CEO", found_value: "Chief Executive Officer", status: "mismatch" },
    { source: "wikidata", fact: "location", canonical_value: "Austin, Texas", found_value: "Austin, Texas", status: "match" },
    { source: "crunchbase", fact: "organization", canonical_value: "Example Shop", found_value: "ExampleShop Inc.", status: "mismatch" },
    { source: "crunchbase", fact: "founded_year", canonical_value: "2018", found_value: "2018", status: "match" },
    { source: "linkedin", fact: "job_title", canonical_value: "Founder & CEO", found_value: "Founder & CEO", status: "match" },
    { source: "linkedin", fact: "location", canonical_value: "Austin, Texas", found_value: null, status: "missing" },
  ],
  match_count: 5,
  mismatch_count: 2,
  missing_count: 1,
  fixes: [
    "Update the Wikidata occupation claim to match the canonical title Founder & CEO.",
    "Request a Crunchbase edit: organization name should read Example Shop, not ExampleShop Inc.",
    "Add the Austin, Texas location to the LinkedIn profile.",
  ],
};

export const mockEntitySchemaResult: EntitySchemaResult = {
  entity_type: "Person",
  json_ld: {
    "@context": "https://schema.org",
    "@type": "Person",
    "@id": "https://www.example-shop.com/about/jane-doe#person",
    name: "Jane Doe",
    url: "https://www.example-shop.com/about/jane-doe",
    description: "Founder and CEO of Example Shop",
    jobTitle: "Founder & CEO",
    worksFor: { "@type": "Organization", name: "Example Shop" },
    alumniOf: [{ "@type": "EducationalOrganization", name: "Stanford University" }],
    sameAs: [
      "https://www.wikidata.org/wiki/Q00000000",
      "https://www.linkedin.com/in/janedoe",
      "https://www.crunchbase.com/person/jane-doe",
    ],
  },
  script_tag:
    '<script type="application/ld+json">{"@context": "https://schema.org", "@type": "Person", "name": "Jane Doe"}</script>',
  warnings: ["No image provided — entity panels perform better with a canonical headshot."],
};

// ---------------------------------------------------------------------------
// AEO
// ---------------------------------------------------------------------------

export const mockQuestionExtractionResult: QuestionExtractionResult = {
  seed: "running shoes",
  questions: [
    { question: "What are the best running shoes for beginners?", parent: null, depth: 0 },
    { question: "How much should I spend on running shoes?", parent: null, depth: 0 },
    { question: "How often should running shoes be replaced?", parent: null, depth: 0 },
    { question: "Do beginners need stability running shoes?", parent: "What are the best running shoes for beginners?", depth: 1 },
    { question: "Are expensive running shoes worth it?", parent: "How much should I spend on running shoes?", depth: 1 },
    { question: "How many miles do running shoes last?", parent: "How often should running shoes be replaced?", depth: 1 },
    { question: "What happens if you run in worn-out shoes?", parent: "How many miles do running shoes last?", depth: 2 },
  ],
  autocomplete: [
    "running shoes for flat feet",
    "running shoes for wide feet",
    "running shoes vs trail shoes",
    "running shoes sale",
    "running shoes near me",
  ],
};

export const mockClusterMapResult: ClusterMapResult = {
  clusters: [
    {
      label: "beginner shoes",
      primary_question: "What are the best running shoes for beginners?",
      questions: [
        "What are the best running shoes for beginners?",
        "Do beginners need stability running shoes?",
      ],
    },
    {
      label: "price value",
      primary_question: "How much should I spend on running shoes?",
      questions: [
        "How much should I spend on running shoes?",
        "Are expensive running shoes worth it?",
      ],
    },
    {
      label: "shoe lifespan",
      primary_question: "How often should running shoes be replaced?",
      questions: [
        "How often should running shoes be replaced?",
        "How many miles do running shoes last?",
        "What happens if you run in worn-out shoes?",
      ],
    },
  ],
  faq: [
    {
      question: "What are the best running shoes for beginners?",
      answer_template: "For most beginners, a neutral cushioned trainer is the safest choice. Answer in 40-55 words, then link to your buying guide.",
      target_page: "https://www.example-shop.com/guides/beginner-running-shoes",
    },
    {
      question: "How often should running shoes be replaced?",
      answer_template: "Most running shoes last 300-500 miles. State the range up front, then explain the wear signals to check.",
      target_page: "https://www.example-shop.com/guides/when-to-replace-shoes",
    },
    {
      question: "How much should I spend on running shoes?",
      answer_template: "Give a concrete price band first, then break down what each tier adds.",
      target_page: null,
    },
  ],
};

export const mockSchemaGraphResult: SchemaGraphResult = {
  json_ld: {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebPage",
        "@id": "https://www.example-shop.com/guides/beginner-running-shoes#webpage",
        url: "https://www.example-shop.com/guides/beginner-running-shoes",
        name: "Best Running Shoes for Beginners (2026 Guide)",
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Guides", item: "https://www.example-shop.com/guides" },
          { "@type": "ListItem", position: 2, name: "Beginner Running Shoes", item: "https://www.example-shop.com/guides/beginner-running-shoes" },
        ],
      },
      {
        "@type": "FAQPage",
        mainEntity: [
          {
            "@type": "Question",
            name: "What are the best running shoes for beginners?",
            acceptedAnswer: { "@type": "Answer", text: "For most beginners, a neutral cushioned trainer is the safest choice." },
          },
        ],
      },
    ],
  },
  script_tag:
    '<script type="application/ld+json">{"@context": "https://schema.org", "@graph": []}</script>',
  node_types: ["WebPage", "BreadcrumbList", "FAQPage"],
  warnings: [],
};

export const mockLinkSuggestResult: LinkSuggestResult = {
  suggestions: [
    {
      source_url: "https://www.example-shop.com/guides/beginner-running-shoes",
      target_url: "https://www.example-shop.com/guides/when-to-replace-shoes",
      similarity: 0.61,
      anchor_text: "when to replace running shoes",
    },
    {
      source_url: "https://www.example-shop.com/guides/beginner-running-shoes",
      target_url: "https://www.example-shop.com/collections/neutral-trainers",
      similarity: 0.54,
      anchor_text: "neutral cushioned trainers",
    },
    {
      source_url: "https://www.example-shop.com/guides/when-to-replace-shoes",
      target_url: "https://www.example-shop.com/guides/beginner-running-shoes",
      similarity: 0.58,
      anchor_text: "best shoes for new runners",
    },
    {
      source_url: "https://www.example-shop.com/blog/marathon-training-plan",
      target_url: "https://www.example-shop.com/guides/when-to-replace-shoes",
      similarity: 0.41,
      anchor_text: "replace your shoes mid-plan",
    },
  ],
  pages_analyzed: 4,
};

export const mockVoiceAuditResult: VoiceAuditResult = {
  score: 74,
  grade: "C",
  flesch: 68.4,
  avg_sentence_length: 14.8,
  syllable_density: 1.52,
  first_paragraph_words: 62,
  checks: [
    { code: "direct_answer", label: "Direct answer up front", passed: true, weight: 3, message: "The opening sentence answers the question directly." },
    { code: "answer_length", label: "Answer within 50 words", passed: false, weight: 2, message: "First paragraph is 62 words — trim to 50 or fewer." },
    { code: "readability", label: "Conversational readability", passed: true, weight: 2, message: "Flesch 68.4 is within the conversational band (60-80)." },
    { code: "sentence_length", label: "Short sentences", passed: true, weight: 1, message: "Average sentence length 14.8 words." },
    { code: "question_heading", label: "Question phrased as heading", passed: false, weight: 1, message: "No H2 restates the spoken query." },
  ],
  fixes: [
    "Trim the first paragraph to 50 words or fewer so assistants can read it aloud verbatim.",
    "Add an H2 that restates the spoken question word-for-word.",
  ],
};

// ---------------------------------------------------------------------------
// Kit assistant
// ---------------------------------------------------------------------------

export const mockActionItemPlan: ActionItemPlan = {
  site: "https://www.example-shop.com",
  generated_at: "2026-07-08T09:30:00Z",
  items: [
    {
      id: "act_0001",
      title: "Fix the broken link on your Trail Shoes page",
      what_it_means: "A link on /collections/trail points to a page that no longer exists, so visitors hit a dead end.",
      why_it_matters: "Dead ends frustrate shoppers and waste the authority that page passes on.",
      category: "links",
      severity: "high",
      priority_score: 88,
      page_url: "https://www.example-shop.com/collections/trail",
      keyword: null,
      source_code: "broken_internal_link",
      steps: [
        { number: 1, instruction: "Open the Trail Shoes collection page in your site editor." },
        { number: 2, instruction: "Find the link labelled 'sizing guide' near the bottom of the page." },
        { number: 3, instruction: "Point it at the new sizing guide page, or remove it if the guide is gone." },
        { number: 4, instruction: "Save and publish, then click the link once to confirm it works." },
      ],
      estimated_minutes: 10,
    },
    {
      id: "act_0002",
      title: "Write a meta description for your homepage",
      what_it_means: "Your homepage has no meta description, so Google writes its own snippet.",
      why_it_matters: "A hand-written snippet earns more clicks from the same ranking.",
      category: "on_page",
      severity: "medium",
      priority_score: 71,
      page_url: "https://www.example-shop.com/",
      keyword: "running shoes online",
      source_code: "missing_meta_description",
      steps: [
        { number: 1, instruction: "Open your homepage settings in the site editor." },
        { number: 2, instruction: "Write 120-155 characters describing what you sell and why to buy from you." },
        { number: 3, instruction: "Include the phrase 'running shoes' once, naturally." },
        { number: 4, instruction: "Save and publish." },
      ],
      estimated_minutes: 15,
    },
    {
      id: "act_0003",
      title: "Expand the beginner running shoes guide",
      what_it_means: "Your guide is 280 words while competing pages average about 1,600.",
      why_it_matters: "Thin pages rarely rank for competitive keywords or get cited by AI assistants.",
      category: "content",
      severity: "medium",
      priority_score: 64,
      page_url: "https://www.example-shop.com/guides/beginner-running-shoes",
      keyword: "best running shoes for beginners",
      source_code: "thin_content",
      steps: [
        { number: 1, instruction: "Add a 45-word direct answer at the very top of the guide." },
        { number: 2, instruction: "Add sections for cushioning, fit, budget, and common mistakes." },
        { number: 3, instruction: "Answer the 3 People-Also-Ask questions from the AEO tab as FAQ entries." },
      ],
      estimated_minutes: 90,
    },
    {
      id: "act_0004",
      title: "Add alt text to 12 product images",
      what_it_means: "12 images on product pages have no alt text.",
      why_it_matters: "Alt text helps you appear in image search and keeps the store accessible.",
      category: "images",
      severity: "low",
      priority_score: 42,
      page_url: null,
      keyword: null,
      source_code: "images_missing_alt",
      steps: [
        { number: 1, instruction: "Open the media library and filter for images without alt text." },
        { number: 2, instruction: "Describe each image in one short sentence, e.g. 'Blue neutral running shoe, side view'." },
      ],
      estimated_minutes: 25,
    },
  ],
  total: 4,
  by_severity: { high: 1, medium: 2, low: 1 },
};

export const mockQueuedActions: QueuedAction[] = [
  {
    id: "qact_0001",
    org_id: "org_demo_0001",
    type: "write_blog_post",
    params: { keyword: "best running shoes for beginners", topic: "beginner buying guide" },
    status: "awaiting_approval",
    approval_required: true,
    attempts: 0,
    max_attempts: 3,
    result: null,
    last_error: null,
    logs: [],
    created_at: "2026-07-08T08:00:00Z",
    updated_at: "2026-07-08T08:00:00Z",
  },
  {
    id: "qact_0002",
    org_id: "org_demo_0001",
    type: "update_meta_tags",
    params: { url: "https://www.example-shop.com/", title: "Running Shoes Online | Example Shop" },
    status: "pending",
    approval_required: false,
    attempts: 0,
    max_attempts: 3,
    result: null,
    last_error: null,
    logs: [],
    created_at: "2026-07-08T08:05:00Z",
    updated_at: "2026-07-08T08:05:00Z",
  },
  {
    id: "qact_0003",
    org_id: "org_demo_0001",
    type: "publish_gbp_update",
    params: { summary: "Summer trail-shoe sale — 20% off this week." },
    status: "completed",
    approval_required: false,
    attempts: 1,
    max_attempts: 3,
    result: { post_id: "gbp_post_101" },
    last_error: null,
    logs: [{ attempt: 1, level: "info", message: "Published GBP update gbp_post_101." }],
    created_at: "2026-07-07T15:00:00Z",
    updated_at: "2026-07-07T15:01:00Z",
  },
  {
    id: "qact_0004",
    org_id: "org_demo_0001",
    type: "sync_directory_listing",
    params: { directory: "yelp" },
    status: "failed",
    approval_required: false,
    attempts: 3,
    max_attempts: 3,
    result: null,
    last_error: "Yelp API rejected the phone format.",
    logs: [
      { attempt: 1, level: "error", message: "Yelp API rejected the phone format." },
      { attempt: 2, level: "error", message: "Yelp API rejected the phone format." },
      { attempt: 3, level: "error", message: "Yelp API rejected the phone format." },
    ],
    created_at: "2026-07-06T10:00:00Z",
    updated_at: "2026-07-06T10:12:00Z",
  },
];

export const mockKeywordMapResult: KeywordMapResult = {
  assignments: [
    {
      keyword: "best running shoes for beginners",
      page_url: "https://www.example-shop.com/guides/beginner-running-shoes",
      score: 0.72,
      alternatives: [{ url: "https://www.example-shop.com/collections/neutral-trainers", score: 0.44 }],
    },
    {
      keyword: "trail running shoes",
      page_url: "https://www.example-shop.com/collections/trail",
      score: 0.68,
      alternatives: [],
    },
    {
      keyword: "when to replace running shoes",
      page_url: "https://www.example-shop.com/guides/when-to-replace-shoes",
      score: 0.81,
      alternatives: [{ url: "https://www.example-shop.com/guides/beginner-running-shoes", score: 0.69 }],
    },
  ],
  cannibalization: [
    {
      keyword: "when to replace running shoes",
      primary_page: "https://www.example-shop.com/guides/when-to-replace-shoes",
      competing_pages: [{ url: "https://www.example-shop.com/guides/beginner-running-shoes", score: 0.69 }],
      suggested_actions: [
        "Consolidate the replacement advice into the dedicated guide and link to it from the beginner guide.",
        "De-optimize the beginner guide for this keyword (remove it from the H2s).",
      ],
    },
  ],
  unmapped_keywords: ["running shoe subscription"],
};

export const mockContentCalendar: ContentCalendar = {
  start_date: "2026-07-13",
  cadence: "weekly",
  entries: [
    {
      publish_date: "2026-07-13",
      title: "Best Running Shoes for Beginners: The 2026 Buying Guide",
      cluster: "Beginner Guides",
      outline: {
        h1: "Best Running Shoes for Beginners: The 2026 Buying Guide",
        headings: [
          { level: 2, text: "What makes a great beginner running shoe" },
          { level: 2, text: "Our top 5 picks compared" },
          { level: 2, text: "How much should you spend?" },
          { level: 2, text: "FAQ" },
        ],
        target_keyword: "best running shoes for beginners",
        supporting_keywords: ["beginner running shoes", "neutral running shoes"],
        intent: "commercial",
        internal_links: ["https://www.example-shop.com/collections/neutral-trainers"],
      },
    },
    {
      publish_date: "2026-07-20",
      title: "How Many Miles Do Running Shoes Last?",
      cluster: "Shoe Care",
      outline: {
        h1: "How Many Miles Do Running Shoes Last?",
        headings: [
          { level: 2, text: "The 300-500 mile rule" },
          { level: 2, text: "5 signs your shoes are worn out" },
          { level: 2, text: "How to make shoes last longer" },
        ],
        target_keyword: "how many miles do running shoes last",
        supporting_keywords: ["when to replace running shoes"],
        intent: "informational",
        internal_links: ["https://www.example-shop.com/guides/when-to-replace-shoes"],
      },
    },
    {
      publish_date: "2026-07-27",
      title: "Trail vs Road Running Shoes: Which Do You Actually Need?",
      cluster: "Comparisons",
      outline: {
        h1: "Trail vs Road Running Shoes: Which Do You Actually Need?",
        headings: [
          { level: 2, text: "Key differences at a glance" },
          { level: 2, text: "When trail shoes are worth it" },
          { level: 2, text: "Can you use trail shoes on the road?" },
        ],
        target_keyword: "trail vs road running shoes",
        supporting_keywords: ["trail running shoes", "road running shoes"],
        intent: "commercial",
        internal_links: ["https://www.example-shop.com/collections/trail"],
      },
    },
  ],
  total: 3,
};

// ---------------------------------------------------------------------------
// Local SEO
// ---------------------------------------------------------------------------

export const mockGbpMetrics: GbpMetrics = {
  org_id: "org_demo_0001",
  period_days: 30,
  views_search: 4820,
  views_maps: 2310,
  searches_direct: 1140,
  searches_discovery: 3260,
  actions_website: 640,
  actions_calls: 187,
  actions_directions: 254,
};

export const mockGbpPosts: GbpPost[] = [
  {
    id: "gbp_post_101",
    org_id: "org_demo_0001",
    summary: "Summer trail-shoe sale — 20% off all trail models this week only.",
    topic: "offer",
    cta_url: "https://www.example-shop.com/collections/trail",
    state: "live",
    created_at: "2026-07-07T15:01:00Z",
  },
  {
    id: "gbp_post_100",
    org_id: "org_demo_0001",
    summary: "Free gait analysis every Saturday in our Austin store. Walk-ins welcome.",
    topic: "event",
    cta_url: "https://www.example-shop.com/stores/austin",
    state: "live",
    created_at: "2026-06-28T10:00:00Z",
  },
];

export const mockReviewList: ReviewListResponse = {
  reviews: [
    {
      id: "rev_0001",
      author: "Maria G.",
      rating: 5,
      text: "The gait analysis was spot on and my new trainers feel amazing. Great staff!",
      created_at: "2026-07-05T14:20:00Z",
      reply: null,
    },
    {
      id: "rev_0002",
      author: "Tom H.",
      rating: 2,
      text: "Ordered online, the delivery took almost two weeks and nobody answered my emails.",
      created_at: "2026-07-03T09:10:00Z",
      reply: null,
    },
    {
      id: "rev_0003",
      author: "Priya S.",
      rating: 4,
      text: "Good selection and fair prices. The store was a bit crowded on Saturday.",
      created_at: "2026-06-29T16:45:00Z",
      reply: "Thanks Priya! Saturdays are our busiest day — weekday mornings are much calmer.",
    },
  ],
  suggested_replies: [
    {
      review_id: "rev_0001",
      sentiment: "positive",
      text: "Thank you, Maria! We are thrilled the gait analysis helped — happy running, and see you at the next fitting.",
    },
    {
      review_id: "rev_0002",
      sentiment: "negative",
      text: "Tom, we are sorry about the slow delivery and the missed emails. Please contact support@example-shop.com with your order number and we will make this right.",
    },
    {
      review_id: "rev_0003",
      sentiment: "positive",
      text: "Thanks Priya! Saturdays get busy — weekday mornings are the quietest time for a relaxed fitting.",
    },
  ],
};

export const mockNapRecord: NapRecord = {
  name: "Example Shop",
  address: "500 Congress Ave, Austin, TX 78701",
  phone: "+1 512-555-0134",
  website: "https://www.example-shop.com",
  hours: { "mon-fri": "09:00-19:00", sat: "10:00-18:00", sun: "closed" },
  locked: true,
};

export const mockCitationStatusReport: CitationStatusReport = {
  org_id: "org_demo_0001",
  locked: true,
  drift_detected: true,
  directories: [
    { directory: "yelp", listed: true, drift: false, diffs: [], state: "in_sync" },
    {
      directory: "apple_maps",
      listed: true,
      drift: true,
      diffs: [{ field: "phone", expected: "+1 512-555-0134", found: "+1 512-555-0100" }],
      state: "drift_blocked",
    },
    { directory: "bing_places", listed: true, drift: false, diffs: [], state: "updated" },
    { directory: "foursquare", listed: false, drift: false, diffs: [], state: "not_listed" },
  ],
};
