# myseoapp-mcp

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that exposes MySEOapp's SEO
toolset — site auditing, on-page analysis, keyword research, SERP analysis, rank tracking,
reporting, and account usage — to any MCP-compatible client (Claude Desktop, Claude Code, etc.)
over stdio.

The server is a thin, strictly-typed wrapper around the MySEOapp backend REST API: every tool
validates its arguments with [Zod](https://zod.dev), calls the backend over HTTP with your
credentials attached, and returns the JSON result as MCP text content.

## Requirements

- Node.js 18 or later (uses the global `fetch` API)
- A running MySEOapp backend (see `../backend`)
- **An API key or bearer token.** The backend is multi-tenant and requires authentication on
  every `/api/v1` SEO endpoint — see [Authenticate](#authenticate) below.

## Install

```bash
cd MySEOapp/mcp-server
npm install
```

## Authenticate

The backend resolves the calling organization (and role) from the request's credentials, and
rejects unauthenticated calls to every SEO endpoint with `401`. Configure **one** of:

| Env var             | Header sent                  | Use case                                                        |
| -------------------- | ------------------------------ | ------------------------------------------------------------------ |
| `MYSEOAPP_API_KEY`   | `X-API-Key: <key>`             | Self-hosted API key. Recommended for MCP/automation use.          |
| `MYSEOAPP_TOKEN`     | `Authorization: Bearer <token>`| A signed-in user's session/IdP access token.                      |

If both are set, `MYSEOAPP_API_KEY` wins — the server always prefers `X-API-Key` over
`Authorization: Bearer`.

### Getting an API key

1. Sign in to the MySEOapp web app and open **Settings → API Keys**, or
2. Call the endpoint directly with a session/bearer token that has the `apikeys:manage`
   permission (editor role or above):

   ```bash
   curl -X POST "$MYSEOAPP_API_BASE_URL/api/v1/api-keys" \
     -H "Authorization: Bearer $YOUR_SESSION_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name": "mcp-server", "role": "editor"}'
   ```

The response's `secret` field (e.g. `msk_...`) is shown **once** — copy it into
`MYSEOAPP_API_KEY` right away, since only its SHA-256 hash is stored server-side and it cannot be
recovered later. List or revoke keys with `GET /api/v1/api-keys` and
`DELETE /api/v1/api-keys/{key_id}`.

## Configure

The server reads its configuration from environment variables — no config file is required.

| Variable                  | Required | Default                 | Description                                                                    |
| -------------------------- | -------- | ------------------------ | ---------------------------------------------------------------------------------- |
| `MYSEOAPP_API_BASE_URL`    | No       | `http://localhost:8000`  | Base URL of the MySEOapp backend (no trailing slash, no `/api/v1`).               |
| `MYSEOAPP_API_KEY`         | Yes\*    | _(unset)_                 | Self-hosted API key, sent as `X-API-Key`. Preferred over `MYSEOAPP_TOKEN`.        |
| `MYSEOAPP_TOKEN`           | Yes\*    | _(unset)_                 | Bearer token, sent as `Authorization: Bearer`. Used only if no API key is set.    |

\* One of `MYSEOAPP_API_KEY` / `MYSEOAPP_TOKEN` is required for any real backend deployment,
since every SEO endpoint now requires auth. The server still starts with neither set (so
`tools/list` keeps working), but every tool call will fail with a `401` until a credential is
configured.

All requests are made against `${MYSEOAPP_API_BASE_URL}/api/v1/...`.

## Build

```bash
npm run build      # compiles src/ -> dist/ with tsc
npm run typecheck   # type-checks only, no output
```

## Test

Tests run fully offline: `global.fetch` is stubbed with canned responses, so no backend needs to
be running. This includes assertions that the configured auth header is attached to every
request, and that 401/402/403 responses surface clear, actionable errors.

```bash
npm test
```

## Run

```bash
# after building:
MYSEOAPP_API_KEY=msk_... npm start
# equivalent to:
MYSEOAPP_API_KEY=msk_... node dist/index.js

# or, for local development without a build step:
MYSEOAPP_API_KEY=msk_... npm run dev
```

On startup the server logs a ready message to **stderr** (stdout is reserved for the MCP JSON-RPC
stream):

```
[myseoapp-mcp] v0.1.0 ready on stdio (backend: http://localhost:8000, auth: X-API-Key)
```

If no credential is configured, the same line reports
`auth: none (requests will fail with 401 until MYSEOAPP_API_KEY or MYSEOAPP_TOKEN is set)`.

## Tools exposed

| Tool               | Backend endpoint            | Purpose                                                             |
| ------------------- | ---------------------------- | ---------------------------------------------------------------------- |
| `run_audit`         | `POST /audit/crawl`          | Crawl a site from a start URL and run a full technical/on-page audit. |
| `audit_page`        | `POST /audit/page`           | Audit a single page from a URL or raw HTML.                          |
| `analyze_onpage`    | `POST /onpage/analyze`       | Analyze on-page SEO for a target keyword.                            |
| `content_score`     | `POST /onpage/content-score` | Score content quality/optimization, optionally vs. competitor texts. |
| `generate_schema`   | `POST /onpage/schema`        | Generate JSON-LD structured data (schema.org markup).                |
| `keyword_research`  | `POST /keywords/research`    | Expand a seed keyword into related keyword ideas.                    |
| `analyze_serp`      | `POST /keywords/serp`        | Analyze the current SERP for a keyword.                              |
| `track_rankings`    | `POST /rankings/track`       | Track keyword rankings for a domain.                                 |
| `generate_report`   | `POST /reports/build`        | Build an SEO performance report for a site/domain.                   |
| `account_usage`     | `GET /usage`                 | Get the authenticated org's monthly usage and plan limits.           |

Every request also carries whichever auth header is configured (see
[Authenticate](#authenticate)) — no tool takes a credential as an argument.

Each tool validates its input with a Zod schema before calling the backend, and returns:

```json
{ "content": [{ "type": "text", "text": "<pretty-printed JSON result>" }] }
```

If the backend returns a non-2xx response, or the arguments fail validation, the MCP `tools/call`
response comes back with `isError: true` and a text block describing the failure (thrown
`ApiError` / `ApiNetworkError` / Zod validation errors are all caught and formatted at the server
layer — see `src/server.ts`).

### Auth-related errors

`ApiError` (`src/apiClient.ts`) carries the backend's `status`, `statusText`, request `path`, and
parsed response `body`, and rewrites the three auth/billing status codes the backend uses into a
message that says exactly what to do next:

| Status | Backend error code                          | MCP tool error message                                                            |
| ------ | -------------------------------------------- | ------------------------------------------------------------------------------------ |
| `401`  | `not_authenticated`                          | Authentication failed — set `MYSEOAPP_API_KEY` (preferred) or `MYSEOAPP_TOKEN`.      |
| `402`  | `quota_exceeded` / `feature_not_available`   | Quota or plan limit reached — upgrade the plan or wait for the next billing cycle.   |
| `403`  | `forbidden`                                  | Insufficient role/permission for the action — use a higher-role API key or account.  |

Any other non-2xx status falls back to a generic `MySEOapp API request to <path> failed: <status>
<statusText>` message. Use the `account_usage` tool to check quota headroom proactively, or to
see current usage after hitting a `402`.

## Registering with an MCP client

### Claude Desktop

Add an entry to `claude_desktop_config.json` (Settings → Developer → Edit Config in Claude
Desktop), pointing `command`/`args` at the built entrypoint:

```json
{
  "mcpServers": {
    "myseoapp": {
      "command": "node",
      "args": ["/absolute/path/to/MySEOapp/mcp-server/dist/index.js"],
      "env": {
        "MYSEOAPP_API_BASE_URL": "http://localhost:8000",
        "MYSEOAPP_API_KEY": "msk_..."
      }
    }
  }
}
```

Use an absolute path to `dist/index.js` (relative paths are not resolved consistently across
clients). Restart Claude Desktop after editing the config. To authenticate with a bearer token
instead of an API key, replace `MYSEOAPP_API_KEY` with `MYSEOAPP_TOKEN` in `env`.

### Claude Code / other MCP clients

Any client that launches an MCP server as a subprocess over stdio can use the same
`node /absolute/path/to/dist/index.js` command with the same environment variables — consult your
client's documentation for where server definitions live.

## Project layout

```
src/
  config.ts       # env-based configuration (MYSEOAPP_API_BASE_URL, MYSEOAPP_API_KEY, MYSEOAPP_TOKEN)
  apiClient.ts     # typed fetch client (get/post, auth headers, ApiError w/ 401/402/403 messages, ApiNetworkError)
  tools/index.ts   # tool definitions: name, description, Zod schema, JSON Schema, handler
  server.ts        # wires tool definitions into an MCP Server (ListTools/CallTool handlers)
  index.ts         # entrypoint: connects the server to the stdio transport
test/
  tools.test.ts    # offline smoke tests (fetch stubbed, validation + auth-header + error-mapping assertions)
```
