/**
 * Per-tool tests for the background job (src/tools/jobs.ts) and AI
 * Answer-Engine Visibility Tracker (src/tools/aitracker.ts) suites, following
 * the mocked-fetch conventions of test/tools.test.ts. Auth header inheritance
 * and error mapping are covered globally there.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { ZodError } from "zod";
import { tools, type ToolDefinition } from "../src/tools/index.js";

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

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Background job tools
// ---------------------------------------------------------------------------

describe("jobs_submit_crawl", () => {
  it("POSTs to /api/v1/jobs/crawl with CrawlConfig fields and returns a text content block", async () => {
    const canned = { job_id: "job_1", status: "queued" };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("jobs_submit_crawl").handler({
      start_url: "https://example.com",
      max_pages: 50,
      max_depth: 3,
      respect_robots: false,
      exclude_patterns: ["/admin"],
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/jobs/crawl");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      start_url: "https://example.com",
      max_pages: 50,
      max_depth: 3,
      respect_robots: false,
      exclude_patterns: ["/admin"],
    });
    expect(result.content[0].type).toBe("text");
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'start_url' field, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("jobs_submit_crawl").handler({ max_pages: 50 })).rejects.toBeInstanceOf(
      ZodError
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("jobs_submit_rank_poll", () => {
  it("POSTs to /api/v1/jobs/rank-poll", async () => {
    const canned = { job_id: "job_2", status: "queued" };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("jobs_submit_rank_poll").handler({
      domain: "example.com",
      keywords: ["best crm"],
      country: "us",
      device: "mobile",
      search_volumes: { "best crm": 900 },
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/jobs/rank-poll");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      domain: "example.com",
      keywords: ["best crm"],
      country: "us",
      device: "mobile",
      search_volumes: { "best crm": 900 },
    });
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects an empty keywords array and unknown devices, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(
      getTool("jobs_submit_rank_poll").handler({ domain: "example.com", keywords: [] })
    ).rejects.toBeInstanceOf(ZodError);
    await expect(
      getTool("jobs_submit_rank_poll").handler({
        domain: "example.com",
        keywords: ["best crm"],
        device: "smartwatch",
      })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("jobs_submit_report", () => {
  it("POSTs to /api/v1/jobs/report", async () => {
    const canned = { job_id: "job_3", status: "queued" };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("jobs_submit_report").handler({
      site: "https://example.com",
      period_start: "2026-06-01",
      period_end: "2026-06-30",
      crawl_id: "crawl_1",
      branding: { logo_url: "https://example.com/logo.png" },
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/jobs/report");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      site: "https://example.com",
      period_start: "2026-06-01",
      period_end: "2026-06-30",
      crawl_id: "crawl_1",
      branding: { logo_url: "https://example.com/logo.png" },
    });
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'period_start' field, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(
      getTool("jobs_submit_report").handler({ site: "https://example.com", period_end: "2026-06-30" })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("jobs_list", () => {
  it("GETs /api/v1/jobs without a query string when no filters are given", async () => {
    const canned = { items: [], total: 0 };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("jobs_list").handler({});

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/jobs");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("passes status and type as query params and rejects unknown values", async () => {
    const fetchMock = stubFetchJson({ items: [], total: 0 });

    await getTool("jobs_list").handler({ status: "running", type: "crawl" });
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/jobs?status=running&type=crawl");

    await expect(getTool("jobs_list").handler({ status: "paused" })).rejects.toBeInstanceOf(
      ZodError
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("jobs_status", () => {
  it("GETs /api/v1/jobs/{job_id} with the id url-encoded and no body", async () => {
    const canned = { id: "job 1", type: "crawl", status: "succeeded", progress: 100 };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("jobs_status").handler({ job_id: "job 1" });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/jobs/job%201");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'job_id' field, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("jobs_status").handler({})).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("jobs_cancel", () => {
  it("POSTs to /api/v1/jobs/{job_id}/cancel with the id url-encoded", async () => {
    const canned = { id: "job_1", type: "crawl", status: "cancelled" };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("jobs_cancel").handler({ job_id: "job_1" });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/jobs/job_1/cancel");
    expect(init.method).toBe("POST");
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'job_id' field, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("jobs_cancel").handler({})).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// AI Answer-Engine Visibility Tracker tools
// ---------------------------------------------------------------------------

describe("tracker_create_config", () => {
  it("POSTs to /api/v1/ai-tracker/configs and returns a text content block", async () => {
    const canned = { id: "cfg_1", name: "Acme weekly", brand: "Acme", prompts: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("tracker_create_config").handler({
      name: "Acme weekly",
      brand: "Acme",
      prompts: ["best crm software"],
      competitors: ["Rival"],
      engines: ["chatgpt", "google_ai_mode"],
      refresh_cadence: "weekly",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/ai-tracker/configs");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      name: "Acme weekly",
      brand: "Acme",
      prompts: ["best crm software"],
      competitors: ["Rival"],
      engines: ["chatgpt", "google_ai_mode"],
      refresh_cadence: "weekly",
    });
    expect(result.content[0].type).toBe("text");
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'brand' field and unknown engines", async () => {
    const fetchMock = stubFetchJson({});

    await expect(
      getTool("tracker_create_config").handler({ name: "Acme weekly" })
    ).rejects.toBeInstanceOf(ZodError);
    await expect(
      getTool("tracker_create_config").handler({
        name: "Acme weekly",
        brand: "Acme",
        engines: ["claude"],
      })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("tracker_list_configs", () => {
  it("GETs /api/v1/ai-tracker/configs with no body", async () => {
    const canned = [{ id: "cfg_1", name: "Acme weekly", brand: "Acme" }];
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("tracker_list_configs").handler({});

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/ai-tracker/configs");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });
});

describe("tracker_get_config", () => {
  it("GETs /api/v1/ai-tracker/configs/{config_id} with the id url-encoded", async () => {
    const canned = { id: "cfg 1", name: "Acme weekly", brand: "Acme" };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("tracker_get_config").handler({ config_id: "cfg 1" });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/ai-tracker/configs/cfg%201");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'config_id' field, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("tracker_get_config").handler({})).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("tracker_update_config", () => {
  it("PUTs to /api/v1/ai-tracker/configs/{config_id} with only the changed fields in the body", async () => {
    const canned = { id: "cfg_1", name: "Acme daily", refresh_cadence: "daily" };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("tracker_update_config").handler({
      config_id: "cfg_1",
      name: "Acme daily",
      refresh_cadence: "daily",
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/ai-tracker/configs/cfg_1");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(String(init.body))).toEqual({ name: "Acme daily", refresh_cadence: "daily" });
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects unknown refresh cadences, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(
      getTool("tracker_update_config").handler({ config_id: "cfg_1", refresh_cadence: "hourly" })
    ).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("tracker_delete_config", () => {
  it("DELETEs /api/v1/ai-tracker/configs/{config_id} with no body", async () => {
    const canned = { deleted: true, id: "cfg_1" };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("tracker_delete_config").handler({ config_id: "cfg_1" });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/ai-tracker/configs/cfg_1");
    expect(init.method).toBe("DELETE");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'config_id' field, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("tracker_delete_config").handler({})).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("tracker_run", () => {
  it("POSTs to /api/v1/ai-tracker/configs/{config_id}/run without a query string by default", async () => {
    const canned = { config_id: "cfg_1", brand: "Acme", answers: [], engines: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("tracker_run").handler({ config_id: "cfg_1" });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/ai-tracker/configs/cfg_1/run");
    expect(init.method).toBe("POST");
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("passes 'now' as a query param when given", async () => {
    const fetchMock = stubFetchJson({ config_id: "cfg_1", answers: [] });

    await getTool("tracker_run").handler({ config_id: "cfg_1", now: "2026-07-10T00:00:00Z" });

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(
      "http://localhost:8000/api/v1/ai-tracker/configs/cfg_1/run?now=2026-07-10T00%3A00%3A00Z"
    );
  });
});

describe("tracker_history", () => {
  it("GETs /api/v1/ai-tracker/configs/{config_id}/history with no body", async () => {
    const canned = [{ config_id: "cfg_1", brand: "Acme", engines: [] }];
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("tracker_history").handler({ config_id: "cfg_1" });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/ai-tracker/configs/cfg_1/history");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });
});

describe("tracker_visibility", () => {
  it("GETs /api/v1/ai-tracker/configs/{config_id}/visibility with no body", async () => {
    const canned = { config_id: "cfg_1", brand: "Acme", overall: { visibility_score: 42.5 } };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("tracker_visibility").handler({ config_id: "cfg_1" });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/ai-tracker/configs/cfg_1/visibility");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("rejects calls missing the required 'config_id' field, without hitting the network", async () => {
    const fetchMock = stubFetchJson({});

    await expect(getTool("tracker_visibility").handler({})).rejects.toBeInstanceOf(ZodError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("tracker_mention_gap", () => {
  it("GETs /api/v1/ai-tracker/configs/{config_id}/mention-gap with no body", async () => {
    const canned = { config_id: "cfg_1", brand: "Acme", total_prompts: 3, entries: [] };
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("tracker_mention_gap").handler({ config_id: "cfg_1" });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/ai-tracker/configs/cfg_1/mention-gap");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });
});

describe("tracker_due", () => {
  it("GETs /api/v1/ai-tracker/due without a query string when no args are given", async () => {
    const canned = [{ config_id: "cfg_1", name: "Acme weekly", refresh_cadence: "weekly" }];
    const fetchMock = stubFetchJson(canned);

    const result = await getTool("tracker_due").handler({});

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/ai-tracker/due");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(JSON.parse(result.content[0].text)).toEqual(canned);
  });

  it("passes 'now' as a query param when given", async () => {
    const fetchMock = stubFetchJson([]);

    await getTool("tracker_due").handler({ now: "2026-07-10T00:00:00Z" });

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/v1/ai-tracker/due?now=2026-07-10T00%3A00%3A00Z");
  });
});
