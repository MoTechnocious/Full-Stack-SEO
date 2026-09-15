/**
 * Static, fully-deterministic mock data for the v2 AI Answer-Engine
 * Visibility Tracker and the background job queue, matching the interfaces in
 * `./api`. Same contract as `./mock` / `./mock-ai`: used as a graceful
 * fallback whenever a live API call fails, hand-picked values only (no
 * randomness / clock reads) so server- and client-rendered output always match.
 */
import type {
  Job,
  MentionGapReport,
  TrackerConfig,
  TrackerRunReport,
  VisibilityRollup,
} from "./api";

// ---------------------------------------------------------------------------
// Tracker configs
// ---------------------------------------------------------------------------

export const mockTrackerConfigs: TrackerConfig[] = [
  {
    id: "trk_0001",
    name: "Core brand prompts",
    brand: "Example Shop",
    prompts: [
      "what is the best online running shoe store",
      "best running shoes for beginners",
      "example shop vs runnerhub which is better",
      "where should I buy trail running shoes online",
      "is example shop trustworthy",
      "best place to buy running shoes with free returns",
    ],
    competitors: ["RunnerHub", "StridePro"],
    engines: ["chatgpt", "perplexity", "gemini", "google_ai_overviews"],
    market: "us",
    language: "en",
    own_domain: "example-shop.com",
    refresh_cadence: "weekly",
    created_at: "2026-06-15T09:00:00Z",
    last_run_at: "2026-07-08T06:00:00Z",
  },
  {
    id: "trk_0002",
    name: "Trail niche (DACH)",
    brand: "Example Shop",
    prompts: [
      "beste trailrunning schuhe online kaufen",
      "welcher online shop für laufschuhe ist am besten",
    ],
    competitors: ["RunnerHub"],
    engines: ["chatgpt", "gemini"],
    market: "de",
    language: "de",
    own_domain: "example-shop.com",
    refresh_cadence: "daily",
    created_at: "2026-07-01T10:30:00Z",
    last_run_at: null,
  },
];

// ---------------------------------------------------------------------------
// Visibility rollup (latest run) + run history
// ---------------------------------------------------------------------------

export const mockVisibilityRollup: VisibilityRollup = {
  config_id: "trk_0001",
  brand: "Example Shop",
  run_at: "2026-07-08T06:00:00Z",
  engines: [
    {
      engine: "chatgpt",
      prompts_total: 6,
      prompts_mentioned: 5,
      mention_rate: 0.83,
      avg_position: 1.8,
      position_score: 0.62,
      citation_share: 0.18,
      visibility_score: 71.4,
      share_of_voice: 0.44,
      competitor_share_of_voice: { RunnerHub: 0.34, StridePro: 0.22 },
      avg_sentiment: 0.35,
      sentiment_label: "positive",
      visibility_score_delta: 4.2,
      share_of_voice_delta: 0.05,
      mention_rate_delta: 0.16,
      avg_position_delta: 0.4,
    },
    {
      engine: "perplexity",
      prompts_total: 6,
      prompts_mentioned: 5,
      mention_rate: 0.83,
      avg_position: 1.6,
      position_score: 0.68,
      citation_share: 0.24,
      visibility_score: 75.9,
      share_of_voice: 0.47,
      competitor_share_of_voice: { RunnerHub: 0.31, StridePro: 0.22 },
      avg_sentiment: 0.28,
      sentiment_label: "positive",
      visibility_score_delta: 6.8,
      share_of_voice_delta: 0.07,
      mention_rate_delta: 0.0,
      avg_position_delta: 0.6,
    },
    {
      engine: "gemini",
      prompts_total: 6,
      prompts_mentioned: 4,
      mention_rate: 0.67,
      avg_position: 2.5,
      position_score: 0.41,
      citation_share: 0.11,
      visibility_score: 55.2,
      share_of_voice: 0.36,
      competitor_share_of_voice: { RunnerHub: 0.4, StridePro: 0.24 },
      avg_sentiment: 0.12,
      sentiment_label: "neutral",
      visibility_score_delta: -1.9,
      share_of_voice_delta: -0.02,
      mention_rate_delta: 0.0,
      avg_position_delta: -0.3,
    },
    {
      engine: "google_ai_overviews",
      prompts_total: 6,
      prompts_mentioned: 3,
      mention_rate: 0.5,
      avg_position: 3.0,
      position_score: 0.29,
      citation_share: 0.08,
      visibility_score: 42.7,
      share_of_voice: 0.27,
      competitor_share_of_voice: { RunnerHub: 0.45, StridePro: 0.28 },
      avg_sentiment: 0.05,
      sentiment_label: "neutral",
      visibility_score_delta: 2.1,
      share_of_voice_delta: 0.03,
      mention_rate_delta: 0.17,
      avg_position_delta: 0.2,
    },
  ],
  overall: {
    prompts_total: 24,
    prompts_mentioned: 17,
    mention_rate: 0.71,
    avg_position: 2.2,
    position_score: 0.5,
    citation_share: 0.15,
    visibility_score: 61.3,
    share_of_voice: 0.39,
    competitor_share_of_voice: { RunnerHub: 0.37, StridePro: 0.24 },
    avg_sentiment: 0.2,
    sentiment_label: "positive",
    visibility_score_delta: 2.8,
    share_of_voice_delta: 0.03,
    mention_rate_delta: 0.08,
    avg_position_delta: 0.2,
  },
};

export const mockTrackerHistory: VisibilityRollup[] = [
  {
    config_id: "trk_0001",
    brand: "Example Shop",
    run_at: "2026-06-24T06:00:00Z",
    engines: [],
    overall: {
      prompts_total: 24,
      prompts_mentioned: 13,
      mention_rate: 0.54,
      avg_position: 2.7,
      position_score: 0.4,
      citation_share: 0.1,
      visibility_score: 51.9,
      share_of_voice: 0.31,
      competitor_share_of_voice: { RunnerHub: 0.42, StridePro: 0.27 },
      avg_sentiment: 0.11,
      sentiment_label: "neutral",
      visibility_score_delta: null,
      share_of_voice_delta: null,
      mention_rate_delta: null,
      avg_position_delta: null,
    },
  },
  {
    config_id: "trk_0001",
    brand: "Example Shop",
    run_at: "2026-07-01T06:00:00Z",
    engines: [],
    overall: {
      prompts_total: 24,
      prompts_mentioned: 15,
      mention_rate: 0.63,
      avg_position: 2.4,
      position_score: 0.45,
      citation_share: 0.13,
      visibility_score: 58.5,
      share_of_voice: 0.36,
      competitor_share_of_voice: { RunnerHub: 0.39, StridePro: 0.25 },
      avg_sentiment: 0.16,
      sentiment_label: "neutral",
      visibility_score_delta: 6.6,
      share_of_voice_delta: 0.05,
      mention_rate_delta: 0.09,
      avg_position_delta: 0.3,
    },
  },
  mockVisibilityRollup,
];

// ---------------------------------------------------------------------------
// Mention-Gap report (latest run)
// ---------------------------------------------------------------------------

export const mockMentionGapReport: MentionGapReport = {
  config_id: "trk_0001",
  brand: "Example Shop",
  run_at: "2026-07-08T06:00:00Z",
  total_prompts: 6,
  entries: [
    {
      prompt: "best place to buy running shoes with free returns",
      gap_engines: ["gemini", "google_ai_overviews"],
      competitors_mentioned: ["RunnerHub", "StridePro"],
      opportunity_score: 4.0,
    },
    {
      prompt: "where should I buy trail running shoes online",
      gap_engines: ["google_ai_overviews"],
      competitors_mentioned: ["RunnerHub", "StridePro"],
      opportunity_score: 2.0,
    },
    {
      prompt: "what is the best online running shoe store",
      gap_engines: ["gemini"],
      competitors_mentioned: ["RunnerHub"],
      opportunity_score: 1.0,
    },
  ],
};

// ---------------------------------------------------------------------------
// Full run report (returned by POST /configs/{id}/run)
// ---------------------------------------------------------------------------

export const mockTrackerRunReport: TrackerRunReport = {
  config_id: "trk_0001",
  brand: "Example Shop",
  run_at: "2026-07-08T06:00:00Z",
  engines: ["chatgpt", "perplexity", "gemini", "google_ai_overviews"],
  answers: [
    {
      engine: "chatgpt",
      prompt: "what is the best online running shoe store",
      text: "Top picks include Example Shop, RunnerHub and StridePro. Example Shop stands out for fit guidance and fast shipping.",
      ranked_list: ["Example Shop", "RunnerHub", "StridePro"],
      citations: [
        { url: "https://www.example-shop.com", domain: "example-shop.com", title: "Example Shop" },
        { url: "https://www.runnersworld.com/best-stores", domain: "runnersworld.com", title: "Best Running Stores" },
      ],
      brand_mentioned: true,
      brand_mentions: 2,
      brand_position: 1,
      competitors_mentioned: ["RunnerHub", "StridePro"],
      sentiment_label: "positive",
      sentiment_score: 0.6,
    },
    {
      engine: "gemini",
      prompt: "what is the best online running shoe store",
      text: "RunnerHub is a popular option with a wide selection and generous return window.",
      ranked_list: ["RunnerHub"],
      citations: [
        { url: "https://www.runnerhub.com", domain: "runnerhub.com", title: "RunnerHub" },
      ],
      brand_mentioned: false,
      brand_mentions: 0,
      brand_position: null,
      competitors_mentioned: ["RunnerHub"],
      sentiment_label: "neutral",
      sentiment_score: 0.0,
    },
  ],
  rollup: mockVisibilityRollup,
  mention_gap: mockMentionGapReport,
};

// ---------------------------------------------------------------------------
// Background jobs
// ---------------------------------------------------------------------------

export const mockJobs: Job[] = [
  {
    id: "job_running_01",
    org_id: "org_demo_0001",
    type: "crawl",
    status: "running",
    progress: 45,
    submitted_at: "2026-07-10T08:40:00Z",
    started_at: "2026-07-10T08:40:05Z",
    finished_at: null,
    result_ref: null,
    error: null,
    attempts: 1,
  },
  {
    id: "job_queued_01",
    org_id: "org_demo_0001",
    type: "rank_poll",
    status: "queued",
    progress: 0,
    submitted_at: "2026-07-10T08:42:00Z",
    started_at: null,
    finished_at: null,
    result_ref: null,
    error: null,
    attempts: 0,
  },
  {
    id: "job_done_01",
    org_id: "org_demo_0001",
    type: "crawl",
    status: "succeeded",
    progress: 100,
    submitted_at: "2026-07-09T14:00:00Z",
    started_at: "2026-07-09T14:00:02Z",
    finished_at: "2026-07-09T14:03:41Z",
    result_ref: "crawl_demo_0001",
    error: null,
    attempts: 1,
  },
  {
    id: "job_done_02",
    org_id: "org_demo_0001",
    type: "report",
    status: "succeeded",
    progress: 100,
    submitted_at: "2026-07-08T09:00:00Z",
    started_at: "2026-07-08T09:00:01Z",
    finished_at: "2026-07-08T09:00:19Z",
    result_ref: "rep_demo_0001",
    error: null,
    attempts: 1,
  },
  {
    id: "job_failed_01",
    org_id: "org_demo_0001",
    type: "rank_poll",
    status: "failed",
    progress: 60,
    submitted_at: "2026-07-07T11:20:00Z",
    started_at: "2026-07-07T11:20:03Z",
    finished_at: "2026-07-07T11:21:10Z",
    result_ref: null,
    error: "SERP provider timed out after 3 retries.",
    attempts: 3,
  },
  {
    id: "job_cancelled_01",
    org_id: "org_demo_0001",
    type: "report",
    status: "cancelled",
    progress: 0,
    submitted_at: "2026-07-06T16:00:00Z",
    started_at: null,
    finished_at: "2026-07-06T16:00:30Z",
    result_ref: null,
    error: null,
    attempts: 0,
  },
];
