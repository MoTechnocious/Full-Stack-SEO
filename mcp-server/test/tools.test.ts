import { afterEach, describe, expect, it, vi } from "vitest";
import { ZodError } from "zod";
import { tools, type ToolDefinition } from "../src/tools/index.js";
import { ApiError } from "../src/apiClient.js";

function getTool(name: string): ToolDefinition {
  const tool = tools.find((candidate) => candidate.name === name);
  if (!tool) {
    throw new Error(`Tool "${name}" is not registered`);
  }
  return tool;
}

/** Replaces global fetch with a stub that resolves to a canned JSON response, without touching the network. */
function stubFetchJson(body: unknown, status = 200) {
  const response = new Response(JSON.stringify(body), {
    status,
    statusText: status >= 200 && status < 300 ? "OK" : "Error",
    headers: { "content-type": "application/json" },
  });
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** Loads a fresh copy of the tools module, so top-level config re-reads current env vars. */
async function importFreshTools(): Promise<ToolDefinition[]> {
  vi.resetModules();
  const mod = await import("../src/tools/index.js");
  return mod.tools;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("tool registry", () => {
  it("exposes exactly the 55 MySEOapp tools with unique names", () => {
    const names = tools.map((tool) => tool.name).sort();
    expect(names).toEqual(
      [
        // Core SEO
        "account_usage",
        "analyze_onpage",
        "analyze_serp",
        "audit_page",
        "content_score",
        "generate_report",
        "generate_schema",
        "keyword_research",
        "run_audit",
        "track_rankings",
        // GEO
        "geo_visibility_scan",
        "geo_prompt_research",
        "geo_prompt_tracker",
        "geo_citations_scan",
        "geo_domain_trust",
        "geo_sentiment_scan",
        "geo_ai_readiness_audit",
        // PEO
        "peo_entity_search",
        "peo_entity_track",
        "peo_entity_sensor",
        "peo_build_bio",
        "peo_corroboration_audit",
        "peo_entity_schema",
        // AEO
        "aeo_extract_questions",
        "aeo_map_clusters",
        "aeo_schema_graph",
        "aeo_internal_links",
        "aeo_voice_audit",
        // Kit assistant
        "kit_action_plan",
        "kit_queue_action",
        "kit_run_queue",
        "kit_keyword_map",
        "kit_content_calendar",
        // Local SEO
        "local_gbp_post",
        "local_gbp_metrics",
        "local_gbp_reviews",
        "local_reply_review",
        "local_citation_sync",
        "local_citation_status",
        // Background jobs
        "jobs_submit_crawl",
        "jobs_submit_rank_poll",
        "jobs_submit_report",
        "jobs_list",
        "jobs_status",
        "jobs_cancel",
        // AI Answer-Engine Visibility Tracker
        "tracker_create_config",
        "tracker_list_configs",
        "tracker_get_config",
        "tracker_update_config",
        "tracker_delete_config",
        "tracker_run",
        "tracker_history",
        "tracker_visibility",
        "tracker_mention_gap",
        "tracker_due",
      ].sort()
    );
    expect(new Set(names).size).toBe(names.length);
  });

  it("gives every tool a non-empty description and an object-typed JSON Schema", () => {
    for (const tool of tools) {
      expect(tool.jsonSchema.type).toBe("object");
      expect(typeof tool.description).toBe("string");
      expect(tool.description.length).toBeGreaterThan(0);
    }
  });
});

describe("keyword_research", () => {
  it("POSTs to /api/v1/keywords/research and returns a text content block", async () => {
    const canned = { seed: "seo tools", ideas: [{ keyword: "best seo tools", volume: 1200 }] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("keyword_research").handler({
      seed: "seo tools",
      country: "US",
      limit: 10,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/keywords/research");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ seed: "seo tools", country: "US", limit: 10 });

    expect(result.content).toHaveLength(1);
    expect(result.content[0].type).toBe("text");
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'seed' field, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("keyword_research").handler({ country: "US" })).rejects.toBeInstanceOf(
      ZodError
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("analyze_onpage", () => {
  it("POSTs to /api/v1/onpage/analyze and returns a text content block", async () => {
    const canned = { score: 82, issues: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("analyze_onpage").handler({
      targetKeyword: "seo audit tool",
      content: "Some content about SEO tooling.",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/onpage/analyze");
    expect(init.method).toBe("POST");

    expect(result.content[0].type).toBe("text");
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'targetKeyword' field, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(
      getTool("analyze_onpage").handler({ content: "no keyword provided" })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("account_usage", () => {
  it("GETs /api/v1/usage with no body and returns a text content block", async () => {
    const canned = {
      plan_code: "free",
      monthly: { crawls_per_month: { used: 1, limit: 5 } },
      resources: { sites: { used: 1, limit: 1 } },
    };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("account_usage").handler({});

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/usage");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();

    expect(result.content[0].type).toBe("text");
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });
});

describe("apiClient error propagation", () => {
  it("rejects with ApiError when the backend responds with a non-2xx status", async () => {
    const fetchMock = stubFetchJson({ error: "boom" }, 500);

    await expect(
      getTool("keyword_research").handler({ seed: "seo tools" })
    ).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("surfaces a clear authentication error on 401, naming MYSEOAPP_API_KEY", async () => {
    const fetchMock = stubFetchJson(
      { error: "not_authenticated", detail: "Authentication required." },
      401
    );

    const promise = getTool("keyword_research").handler({ seed: "seo tools" });

    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(promise).rejects.toThrow(/authentication failed/i);
    await expect(promise).rejects.toThrow(/MYSEOAPP_API_KEY/);
    await expect(promise).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("surfaces a clear quota/plan-limit error on 402", async () => {
    const fetchMock = stubFetchJson(
      {
        error: "quota_exceeded",
        detail: "Monthly quota reached for 'crawls_per_month': 5/5 on the 'free' plan.",
      },
      402
    );

    const promise = getTool("run_audit").handler({ startUrl: "https://example.com" });

    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(promise).rejects.toThrow(/quota|plan limit/i);
    await expect(promise).rejects.toMatchObject({ status: 402 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("surfaces a clear insufficient-role error on 403", async () => {
    const fetchMock = stubFetchJson(
      { error: "forbidden", detail: "Your role 'client' lacks permission 'seo:run'." },
      403
    );

    const promise = getTool("run_audit").handler({ startUrl: "https://example.com" });

    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(promise).rejects.toThrow(/insufficient role/i);
    await expect(promise).rejects.toMatchObject({ status: 403 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("authentication headers", () => {
  const originalApiKey = process.env.MYSEOAPP_API_KEY;
  const originalToken = process.env.MYSEOAPP_TOKEN;

  afterEach(() => {
    if (originalApiKey === undefined) {
      delete process.env.MYSEOAPP_API_KEY;
    } else {
      process.env.MYSEOAPP_API_KEY = originalApiKey;
    }
    if (originalToken === undefined) {
      delete process.env.MYSEOAPP_TOKEN;
    } else {
      process.env.MYSEOAPP_TOKEN = originalToken;
    }
    vi.resetModules();
  });

  it("attaches X-API-Key when MYSEOAPP_API_KEY is set", async () => {
    process.env.MYSEOAPP_API_KEY = "msk_test_key";
    delete process.env.MYSEOAPP_TOKEN;

    const fetchMock = stubFetchJson({ ok: true });
    const freshTools = await importFreshTools();
    const tool = freshTools.find((candidate) => candidate.name === "keyword_research");
    if (!tool) throw new Error("keyword_research not registered");
    await tool.handler({ seed: "seo tools" });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["X-API-Key"]).toBe("msk_test_key");
    expect(headers["Authorization"]).toBeUndefined();
  });

  it("falls back to Authorization: Bearer when only MYSEOAPP_TOKEN is set", async () => {
    delete process.env.MYSEOAPP_API_KEY;
    process.env.MYSEOAPP_TOKEN = "token-abc123";

    const fetchMock = stubFetchJson({ ok: true });
    const freshTools = await importFreshTools();
    const tool = freshTools.find((candidate) => candidate.name === "keyword_research");
    if (!tool) throw new Error("keyword_research not registered");
    await tool.handler({ seed: "seo tools" });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer token-abc123");
    expect(headers["X-API-Key"]).toBeUndefined();
  });

  it("prefers X-API-Key over Authorization: Bearer when both are set", async () => {
    process.env.MYSEOAPP_API_KEY = "msk_test_key";
    process.env.MYSEOAPP_TOKEN = "token-abc123";

    const fetchMock = stubFetchJson({ ok: true });
    const freshTools = await importFreshTools();
    const tool = freshTools.find((candidate) => candidate.name === "keyword_research");
    if (!tool) throw new Error("keyword_research not registered");
    await tool.handler({ seed: "seo tools" });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["X-API-Key"]).toBe("msk_test_key");
    expect(headers["Authorization"]).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// GEO tools
// ---------------------------------------------------------------------------

describe("geo_visibility_scan", () => {
  it("POSTs to /api/v1/geo/visibility/scan and returns a text content block", async () => {
    const canned = { brand: "Acme", overall: { mentions: 3 }, engines: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("geo_visibility_scan").handler({
      brand: "Acme",
      competitors: ["Rival"],
      engines: ["chatgpt", "claude"],
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/geo/visibility/scan");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      brand: "Acme",
      competitors: ["Rival"],
      engines: ["chatgpt", "claude"],
    });

    expect(result.content[0].type).toBe("text");
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'brand' field, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(
      getTool("geo_visibility_scan").handler({ competitors: ["Rival"] })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects unknown answer engines, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(
      getTool("geo_visibility_scan").handler({ brand: "Acme", engines: ["altavista"] })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("geo_prompt_research", () => {
  it("POSTs to /api/v1/geo/prompts/research", async () => {
    const canned = { topic: "crm software", suggestions: [], total: 0 };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("geo_prompt_research").handler({ topic: "crm software", limit: 5 });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/geo/prompts/research");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ topic: "crm software", limit: 5 });
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'topic' field", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("geo_prompt_research").handler({})).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("geo_prompt_tracker", () => {
  it("GETs /api/v1/geo/prompts/tracker with repeated array query params and no body", async () => {
    const canned = { brand: "Acme", total_prompts: 2, entries: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("geo_prompt_tracker").handler({
      brand: "Acme",
      competitors: ["Rival"],
      engines: ["chatgpt", "claude"],
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(
      "http://localhost:8000/api/v1/geo/prompts/tracker?brand=Acme&competitors=Rival&engines=chatgpt&engines=claude"
    );
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });
});

describe("geo_citations_scan", () => {
  it("POSTs to /api/v1/geo/citations/scan", async () => {
    const canned = { brand: "Acme", total_citations: 4, domains: [] };
    const fetchMock = stubFetchJson(canned);

    await getTool("geo_citations_scan").handler({ brand: "Acme", own_domain: "acme.com" });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/geo/citations/scan");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ brand: "Acme", own_domain: "acme.com" });
  });
});

describe("geo_domain_trust", () => {
  it("GETs /api/v1/geo/citations/domains without a query string when no args are given", async () => {
    const fetchMock = stubFetchJson({ total_citations: 0, domains: [] });

    await getTool("geo_domain_trust").handler({});

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/geo/citations/domains");
    expect(init.method).toBe("GET");
  });

  it("passes own_domain as a query param when given", async () => {
    const fetchMock = stubFetchJson({ total_citations: 0, domains: [] });

    await getTool("geo_domain_trust").handler({ own_domain: "acme.com" });

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/geo/citations/domains?own_domain=acme.com");
  });
});

describe("geo_sentiment_scan", () => {
  it("POSTs to /api/v1/geo/sentiment/scan and rejects a missing brand", async () => {
    const fetchMock = stubFetchJson({ brand: "Acme", cells: [], overall_score: 0.2 });

    await getTool("geo_sentiment_scan").handler({ brand: "Acme", engines: ["gemini"] });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/geo/sentiment/scan");
    expect(init.method).toBe("POST");

    await expect(getTool("geo_sentiment_scan").handler({})).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("geo_ai_readiness_audit", () => {
  it("POSTs to /api/v1/geo/readiness/audit", async () => {
    const canned = { url: "https://example.com", score: 74, grade: "C", checks: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("geo_ai_readiness_audit").handler({ url: "https://example.com" });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/geo/readiness/audit");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ url: "https://example.com" });
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'url' field", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("geo_ai_readiness_audit").handler({})).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// PEO tools
// ---------------------------------------------------------------------------

describe("peo_entity_search", () => {
  it("POSTs to /api/v1/peo/entities/search", async () => {
    const canned = { query: "Jane Doe", entities: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("peo_entity_search").handler({
      query: "Jane Doe",
      types: ["Person"],
      limit: 5,
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/peo/entities/search");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ query: "Jane Doe", types: ["Person"], limit: 5 });
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'query' field", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("peo_entity_search").handler({ types: ["Person"] })).rejects.toBeInstanceOf(
      ZodError
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("peo_entity_track", () => {
  it("POSTs to /api/v1/peo/entities/track and requires kg_mid + name", async () => {
    const fetchMock = stubFetchJson({ kg_mid: "/g/abc", name: "Jane Doe", latest_score: 41.5 });

    await getTool("peo_entity_track").handler({ kg_mid: "/g/abc", name: "Jane Doe" });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/peo/entities/track");
    expect(init.method).toBe("POST");

    await expect(getTool("peo_entity_track").handler({ kg_mid: "/g/abc" })).rejects.toBeInstanceOf(
      ZodError
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("peo_entity_sensor", () => {
  it("GETs /api/v1/peo/entities/sensor with url-encoded kg_mid and points", async () => {
    const canned = { kg_mid: "/g/abc", trend: "rising", observations: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("peo_entity_sensor").handler({ kg_mid: "/g/abc", points: 8 });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/peo/entities/sensor?kg_mid=%2Fg%2Fabc&points=8");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });
});

describe("peo_build_bio", () => {
  it("POSTs to /api/v1/peo/bio/build", async () => {
    const fetchMock = stubFetchJson({ name: "Jane Doe", variants: [] });

    await getTool("peo_build_bio").handler({
      name: "Jane Doe",
      roles: ["CEO"],
      organizations: ["Acme Inc"],
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/peo/bio/build");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      name: "Jane Doe",
      roles: ["CEO"],
      organizations: ["Acme Inc"],
    });
  });
});

describe("peo_corroboration_audit", () => {
  it("POSTs to /api/v1/peo/corroboration/audit with nested source profiles", async () => {
    const canned = { entity_name: "Jane Doe", consistency_score: 67, comparisons: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("peo_corroboration_audit").handler({
      entity_name: "Jane Doe",
      canonical_facts: { employer: "Acme Inc" },
      profiles: [{ source: "linkedin", facts: { employer: "Acme" } }],
      fetch_sources: ["wikipedia"],
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/peo/corroboration/audit");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      entity_name: "Jane Doe",
      canonical_facts: { employer: "Acme Inc" },
      profiles: [{ source: "linkedin", facts: { employer: "Acme" } }],
      fetch_sources: ["wikipedia"],
    });
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects unknown source types, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(
      getTool("peo_corroboration_audit").handler({
        entity_name: "Jane Doe",
        canonical_facts: { employer: "Acme Inc" },
        profiles: [{ source: "myspace", facts: {} }],
      })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("peo_entity_schema", () => {
  it("POSTs to /api/v1/peo/schema/entity and rejects an invalid entity_type", async () => {
    const fetchMock = stubFetchJson({ entity_type: "Person", json_ld: {}, script_tag: "" });

    await getTool("peo_entity_schema").handler({
      entity_type: "Person",
      name: "Jane Doe",
      same_as: ["https://linkedin.com/in/janedoe"],
    });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/peo/schema/entity");
    expect(init.method).toBe("POST");

    await expect(
      getTool("peo_entity_schema").handler({ entity_type: "Robot", name: "Jane Doe" })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// AEO tools
// ---------------------------------------------------------------------------

describe("aeo_extract_questions", () => {
  it("POSTs to /api/v1/aeo/questions/extract", async () => {
    const canned = { seed: "seo audits", questions: [], autocomplete: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("aeo_extract_questions").handler({ seed: "seo audits", depth: 2 });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/aeo/questions/extract");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ seed: "seo audits", depth: 2 });
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'seed' field", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("aeo_extract_questions").handler({ depth: 2 })).rejects.toBeInstanceOf(
      ZodError
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("aeo_map_clusters", () => {
  it("POSTs to /api/v1/aeo/clusters/map with questions and pages", async () => {
    const fetchMock = stubFetchJson({ clusters: [], faq: [] });

    await getTool("aeo_map_clusters").handler({
      questions: ["what is seo?"],
      pages: [{ url: "https://example.com/seo", title: "SEO Guide" }],
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/aeo/clusters/map");
    expect(init.method).toBe("POST");
  });

  it("rejects an empty questions array, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("aeo_map_clusters").handler({ questions: [] })).rejects.toBeInstanceOf(
      ZodError
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("aeo_schema_graph", () => {
  it("POSTs to /api/v1/aeo/schema/graph with nested faq/how_to structures", async () => {
    const canned = { json_ld: {}, script_tag: "<script/>", node_types: ["WebPage"] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("aeo_schema_graph").handler({
      url: "https://example.com/guide",
      title: "Guide",
      faqs: [{ question: "Why?", answer: "Because." }],
      how_to: { name: "Do the thing", steps: [{ name: "Step one" }] },
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/aeo/schema/graph");
    expect(init.method).toBe("POST");
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'title' field", async () => {
    const fetchMock = stubFetchJson({});

    await expect(
      getTool("aeo_schema_graph").handler({ url: "https://example.com/guide" })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("aeo_internal_links", () => {
  it("POSTs to /api/v1/aeo/linking/suggest", async () => {
    const fetchMock = stubFetchJson({ suggestions: [], pages_analyzed: 2 });

    await getTool("aeo_internal_links").handler({
      pages: [
        { url: "https://example.com/a", body: "alpha content" },
        { url: "https://example.com/b", body: "beta content" },
      ],
      max_per_page: 3,
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/aeo/linking/suggest");
    expect(init.method).toBe("POST");
  });
});

describe("aeo_voice_audit", () => {
  it("POSTs to /api/v1/aeo/voice/audit and rejects missing content", async () => {
    const fetchMock = stubFetchJson({ score: 80, grade: "B", checks: [] });

    await getTool("aeo_voice_audit").handler({
      content: "SEO is search engine optimization.",
      question: "what is seo?",
    });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/aeo/voice/audit");
    expect(init.method).toBe("POST");

    await expect(getTool("aeo_voice_audit").handler({})).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// Kit assistant tools
// ---------------------------------------------------------------------------

describe("kit_action_plan", () => {
  it("POSTs to /api/v1/assistant/actions/plan with inline issues", async () => {
    const canned = { site: "example.com", items: [], total: 0 };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("kit_action_plan").handler({
      site: "example.com",
      issues: [{ code: "missing_title", title: "Missing title tag", severity: "high" }],
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/assistant/actions/plan");
    expect(init.method).toBe("POST");
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'site' field", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("kit_action_plan").handler({})).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("kit_queue_action", () => {
  it("POSTs to /api/v1/assistant/queue", async () => {
    const canned = { id: "act_1", type: "write_blog_post", status: "pending" };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("kit_queue_action").handler({
      type: "write_blog_post",
      params: { keyword: "best crm" },
      approval_required: true,
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/assistant/queue");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      type: "write_blog_post",
      params: { keyword: "best crm" },
      approval_required: true,
    });
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects unknown action types, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(
      getTool("kit_queue_action").handler({ type: "mine_bitcoin" })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("kit_run_queue", () => {
  it("POSTs to /api/v1/assistant/queue/run with no meaningful body", async () => {
    const canned = { executed: 2, completed: 2, failed: 0, actions: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("kit_run_queue").handler({});

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/assistant/queue/run");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({});
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });
});

describe("kit_keyword_map", () => {
  it("POSTs to /api/v1/assistant/keywords/map", async () => {
    const fetchMock = stubFetchJson({ assignments: [], cannibalization: [], unmapped_keywords: [] });

    await getTool("kit_keyword_map").handler({
      keywords: ["best crm"],
      pages: [{ url: "https://example.com/crm", title: "CRM", content: "crm software" }],
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/assistant/keywords/map");
    expect(init.method).toBe("POST");
  });

  it("rejects calls missing the required 'pages' field", async () => {
    const fetchMock = stubFetchJson({});

    await expect(
      getTool("kit_keyword_map").handler({ keywords: ["best crm"] })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("kit_content_calendar", () => {
  it("POSTs to /api/v1/assistant/calendar/build", async () => {
    const canned = { start_date: "2026-08-01", cadence: "weekly", entries: [], total: 0 };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("kit_content_calendar").handler({
      keywords: [{ keyword: "best crm", search_volume: 900, intent: "commercial" }],
      start_date: "2026-08-01",
      cadence: "weekly",
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/assistant/calendar/build");
    expect(init.method).toBe("POST");
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'start_date' field", async () => {
    const fetchMock = stubFetchJson({});

    await expect(
      getTool("kit_content_calendar").handler({ keywords: [{ keyword: "best crm" }] })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Local SEO tools
// ---------------------------------------------------------------------------

describe("local_gbp_post", () => {
  it("POSTs to /api/v1/local/gbp/posts and rejects an invalid topic", async () => {
    const canned = { id: "post_1", summary: "We are open late!", state: "live" };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("local_gbp_post").handler({
      summary: "We are open late!",
      topic: "update",
    });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/local/gbp/posts");
    expect(init.method).toBe("POST");
    expect(JSON.parse(result.content[0].text)).toEqual(canned);

    await expect(
      getTool("local_gbp_post").handler({ summary: "hi", topic: "rant" })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("local_gbp_metrics", () => {
  it("GETs /api/v1/local/gbp/metrics with period_days as a query param", async () => {
    const fetchMock = stubFetchJson({ period_days: 7, views_search: 120 });

    await getTool("local_gbp_metrics").handler({ period_days: 7 });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/local/gbp/metrics?period_days=7");
    expect(init.method).toBe("GET");
  });

  it("omits the query string when period_days is not given", async () => {
    const fetchMock = stubFetchJson({ period_days: 30 });

    await getTool("local_gbp_metrics").handler({});

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/local/gbp/metrics");
  });
});

describe("local_gbp_reviews", () => {
  it("GETs /api/v1/local/gbp/reviews with no body", async () => {
    const canned = { reviews: [], suggested_replies: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("local_gbp_reviews").handler({});

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/local/gbp/reviews");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });
});

describe("local_reply_review", () => {
  it("POSTs to /api/v1/local/gbp/reviews/{review_id}/reply with the review id url-encoded", async () => {
    const canned = { id: "rev 1", reply: "Thanks!" };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("local_reply_review").handler({
      review_id: "rev 1",
      text: "Thanks!",
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/local/gbp/reviews/rev%201/reply");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ text: "Thanks!" });
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'review_id' field", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("local_reply_review").handler({ text: "Thanks!" })).rejects.toBeInstanceOf(
      ZodError
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("local_citation_sync", () => {
  it("POSTs to /api/v1/local/citations/sync without a query string when no directory is given", async () => {
    const fetchMock = stubFetchJson({ results: [], delivered: 4, failed: 0 });

    await getTool("local_citation_sync").handler({});

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/local/citations/sync");
    expect(init.method).toBe("POST");
  });

  it("passes a single directory as a query param and rejects unknown directories", async () => {
    const fetchMock = stubFetchJson({ results: [], delivered: 1, failed: 0 });

    await getTool("local_citation_sync").handler({ directory: "yelp" });
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/local/citations/sync?directory=yelp");

    await expect(
      getTool("local_citation_sync").handler({ directory: "yellow_pages" })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("local_citation_status", () => {
  it("GETs /api/v1/local/citations/status with no body", async () => {
    const canned = { locked: false, drift_detected: true, directories: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("local_citation_status").handler({});

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/local/citations/status");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });
});
