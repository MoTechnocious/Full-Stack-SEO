/**
 * Runtime configuration for the MySEOapp MCP server.
 *
 * Values are read from environment variables so the server can be pointed at
 * different backend deployments (local dev, staging, production) without a
 * code change. See README.md for the full list of supported variables.
 *
 * The backend is multi-tenant and requires auth on every SEO endpoint, via
 * either a self-hosted API key (`X-API-Key`) or a bearer token
 * (`Authorization: Bearer`). See apiClient.ts for how these are attached.
 */

export interface McpServerConfig {
  /** Base URL of the MySEOapp backend, e.g. http://localhost:8000 (no trailing slash). */
  apiBaseUrl: string;
  /**
   * Self-hosted API key (from the app's API Keys page, or `POST /api/v1/api-keys`).
   * Sent as the `X-API-Key` header on every request. Preferred over `token` when
   * both are configured.
   */
  apiKey: string | undefined;
  /**
   * Optional bearer token (e.g. a signed-in user's session/IdP access token).
   * Sent as the `Authorization: Bearer` header on every request, but only when
   * no `apiKey` is configured.
   */
  token: string | undefined;
}

const DEFAULT_API_BASE_URL = "http://localhost:8000";

function stripTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

/** Reads and trims an environment variable, treating blank strings as unset. */
function readEnvString(name: string): string | undefined {
  const raw = process.env[name]?.trim();
  return raw && raw.length > 0 ? raw : undefined;
}

function loadConfig(): McpServerConfig {
  const rawBaseUrl = process.env.MYSEOAPP_API_BASE_URL?.trim();
  const apiBaseUrl = stripTrailingSlash(
    rawBaseUrl && rawBaseUrl.length > 0 ? rawBaseUrl : DEFAULT_API_BASE_URL
  );

  const apiKey = readEnvString("MYSEOAPP_API_KEY");
  const token = readEnvString("MYSEOAPP_TOKEN");

  return { apiBaseUrl, apiKey, token };
}

/** Process-wide configuration, resolved once from environment variables. */
export const config: McpServerConfig = loadConfig();
