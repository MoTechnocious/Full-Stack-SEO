/**
 * Minimal typed HTTP client for the MySEOapp backend REST API.
 *
 * Uses the global `fetch` implementation provided by Node.js 18+, so no extra
 * HTTP dependency is required. All requests are prefixed with the versioned
 * `/api/v1` base path and carry an auth header whenever the server is
 * configured with credentials: `X-API-Key` (preferred) or
 * `Authorization: Bearer`.
 *
 * The backend is multi-tenant and now requires auth on every SEO endpoint.
 * Non-2xx responses are surfaced as a typed `ApiError`; the 401 / 402 / 403
 * cases the backend uses for auth/billing are rewritten into clear,
 * actionable messages (see `describeError` below) so MCP clients — and the
 * humans/agents driving them — immediately know what to fix.
 */

import { config } from "./config.js";

const API_PREFIX = "/api/v1";

/** Error thrown whenever the backend responds with a non-2xx status code. */
export class ApiError extends Error {
  /** HTTP status code returned by the backend. */
  readonly status: number;
  /** HTTP status text returned by the backend. */
  readonly statusText: string;
  /** Request path that triggered the error (relative, e.g. "/onpage/analyze"). */
  readonly path: string;
  /** Parsed JSON body of the error response, if any could be parsed. */
  readonly body: unknown;

  constructor(status: number, statusText: string, path: string, body: unknown, message?: string) {
    super(message ?? `MySEOapp API request to ${path} failed: ${status} ${statusText}`);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
    this.path = path;
    this.body = body;
  }
}

/** Error thrown when a request cannot be completed at all (network failure, etc). */
export class ApiNetworkError extends Error {
  readonly path: string;
  readonly cause: unknown;

  constructor(path: string, cause: unknown) {
    const reason = cause instanceof Error ? cause.message : String(cause);
    super(`MySEOapp API request to ${path} could not be completed: ${reason}`);
    this.name = "ApiNetworkError";
    this.path = path;
    this.cause = cause;
  }
}

function buildUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${config.apiBaseUrl}${API_PREFIX}${normalizedPath}`;
}

/** Pulls a human-readable `detail` string out of a parsed backend error body, if present. */
function extractDetail(body: unknown): string | undefined {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim().length > 0) {
      return detail;
    }
  }
  return undefined;
}

/**
 * Builds a clear, actionable error message for the auth/billing status codes the
 * backend uses:
 *  - 401 `not_authenticated`               — no/invalid credential.
 *  - 402 `quota_exceeded` / `feature_not_available` — plan/usage limit reached.
 *  - 403 `forbidden`                       — authenticated, but role lacks permission.
 * Returns `undefined` for any other status, so the caller falls back to the
 * generic `ApiError` message.
 */
function describeError(status: number, path: string, body: unknown): string | undefined {
  const detail = extractDetail(body);
  const suffix = detail ? ` (backend said: ${detail})` : "";

  switch (status) {
    case 401:
      return (
        `MySEOapp authentication failed calling ${path} — set MYSEOAPP_API_KEY to a valid ` +
        "self-hosted API key (preferred; sent as X-API-Key), or MYSEOAPP_TOKEN to a valid " +
        `bearer token (sent as Authorization: Bearer).${suffix}`
      );
    case 402:
      return (
        `MySEOapp quota or plan limit reached calling ${path}.${suffix} Upgrade the ` +
        "organization's plan, or wait for the next monthly billing cycle."
      );
    case 403:
      return (
        `MySEOapp request to ${path} was refused: insufficient role/permission for this ` +
        `action.${suffix} Ask an org owner/admin to grant the required role, or use an API ` +
        "key with a higher role."
      );
    default:
      return undefined;
  }
}

/** Returns the single configured auth header, preferring the API key over a bearer token. */
function buildAuthHeaders(): Record<string, string> {
  if (config.apiKey) {
    return { "X-API-Key": config.apiKey };
  }
  if (config.token) {
    return { Authorization: `Bearer ${config.token}` };
  }
  return {};
}

function buildHeaders(hasBody: boolean): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...buildAuthHeaders(),
  };
  if (hasBody) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (text.length === 0) {
    return undefined;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function request<T>(
  method: "GET" | "POST" | "PUT" | "DELETE",
  path: string,
  body?: unknown
): Promise<T> {
  const url = buildUrl(path);
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: buildHeaders(body !== undefined),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    throw new ApiNetworkError(path, cause);
  }

  const parsed = await parseBody(response);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      response.statusText,
      path,
      parsed,
      describeError(response.status, path, parsed)
    );
  }

  return parsed as T;
}

/** Typed API client bound to the configured MySEOapp backend. */
export const apiClient = {
  /** Performs a GET request against `${API_PREFIX}${path}` and returns the parsed JSON body as T. */
  get<T>(path: string): Promise<T> {
    return request<T>("GET", path);
  },

  /** Performs a POST request against `${API_PREFIX}${path}` with a JSON body and returns the parsed JSON body as T. */
  post<T>(path: string, body: unknown): Promise<T> {
    return request<T>("POST", path, body);
  },

  /** Performs a PUT request against `${API_PREFIX}${path}` with a JSON body and returns the parsed JSON body as T. */
  put<T>(path: string, body: unknown): Promise<T> {
    return request<T>("PUT", path, body);
  },

  /** Performs a DELETE request against `${API_PREFIX}${path}` and returns the parsed JSON body as T. */
  delete<T>(path: string): Promise<T> {
    return request<T>("DELETE", path);
  },
};

export type ApiClient = typeof apiClient;
