# MySEOapp

[![CI](https://github.com/MoTechnocious/MySEOapp/actions/workflows/ci.yml/badge.svg)](https://github.com/MoTechnocious/MySEOapp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Backend: FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](backend/)
[![Frontend: Next.js 14](https://img.shields.io/badge/frontend-Next.js%2014-black.svg)](frontend/)
[![MCP](https://img.shields.io/badge/MCP-server-8A2BE2.svg)](mcp-server/)
[![Tests](https://img.shields.io/badge/tests-358%20passing-brightgreen.svg)](#testing)

A unified, self-hostable SEO platform that combines the core capabilities of
**Screaming Frog** (technical crawl/audit), **Surfer SEO** (content optimization),
**Rank Math** (on-page rule engine + schema), and **Hike SEO** (rank tracking,
action plans, white-label agency reporting) — exposed over a **REST API**, an
**MCP server** (55 tools), and a **React/Next.js dashboard**, with **Make.com + CRM**
integration pipelines.

Built as the core infrastructure for scalingfirm.com's client SEO automation, and
released here under the MIT licence so it can be self-hosted, studied, or extended.

Every data provider ships with a deterministic mock implementation, so the whole
stack runs end to end with no API keys and no network access.

---

## Monorepo layout

```
MySEOapp/
├── backend/            # Python 3.10+ FastAPI engine + REST API (the heart)
│   └── app/
│       ├── core/       # crawler · onpage · keywords · reporting engines
│       ├── integrations/  # Make.com gateway · CRM pipeline · webhooks
│       ├── api/        # FastAPI routers (/api/v1)
│       ├── models/     # strictly-typed Pydantic v2 contracts (shared)
│       ├── middleware/ # rate limiting · request context · error handling
│       ├── services/   # persistence seam (in-memory; DB-ready)
│       └── utils/      # URL · text/NLP · HTML parsing helpers
├── mcp-server/         # TypeScript MCP server (55 SEO tools over the REST API)
├── frontend/           # Next.js 14 (App Router) + TS + Tailwind dashboard
├── docs/
│   ├── research/       # competitor feature inventories (the 4 tools)
│   ├── spec/           # FEATURE_MATRIX.md · PRODUCT_SPEC.md
│   ├── ARCHITECTURE.md
│   └── API_REFERENCE.md
├── SYSTEM_STATE.md     # live architectural map + module status + code debt
├── HANDOFF_BRIEF.md    # technical handoff (how it automates the workflows)
├── .env.template       # copy to .env — no secrets are hardcoded
└── .gitignore
```

## Quickstart

### 1. Backend (FastAPI engine + REST API)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate     # optional
pip install -r requirements.txt
cp ../.env.template ../.env                             # then edit values

# Run the test suite (269 tests, deterministic, no network)
python -m pytest -q

# Serve the API (OpenAPI docs at http://localhost:8000/docs)
uvicorn app.main:app --reload --port 8000
```

Key endpoints (all under `/api/v1`): `audit/page`, `audit/crawl`, `onpage/analyze`,
`onpage/content-score`, `onpage/schema`, `keywords/research`, `keywords/serp`,
`rankings/track`, `reports/action-plan`, `reports/build`, `integrations/leads`,
`integrations/webhooks/make`. Full list in [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

### 2. MCP server (TypeScript)

```bash
cd mcp-server
npm install
npm run build && npm test
node dist/index.js         # stdio MCP server
```

Register in an MCP client (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "myseoapp": {
      "command": "node",
      "args": ["/absolute/path/to/MySEOapp/mcp-server/dist/index.js"],
      "env": { "MYSEOAPP_API_BASE_URL": "http://localhost:8000" }
    }
  }
}
```

### 3. Frontend (Next.js dashboard)

```bash
cd frontend
npm install
npm run typecheck
npm run dev                # http://localhost:3000
```

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`. Pages fall back to mock data
when the API is offline, so the UI is demoable standalone.

## Configuration

All backend settings come from environment variables with the `SEO_` prefix (see
`.env.template`). **No API keys are hardcoded.** Data providers are pluggable and
default to deterministic **mock** implementations; supply credentials to enable
real adapters (DataForSEO, Google Search Console, HubSpot/Salesforce, Make.com).

## Testing

| Suite | Command | Status |
|-------|---------|--------|
| Backend (269 tests) | `cd backend && python -m pytest -q` | ✅ green |
| MCP server (89 tests) | `cd mcp-server && npm test` | ✅ green |
| Frontend (typecheck) | `cd frontend && npm run typecheck` | ✅ green |

All suites are deterministic and run offline against the mock providers.

## Contributing

Issues and pull requests are welcome. Please run the three suites above before
opening a PR, and keep new provider adapters behind the existing pluggable seam
so the mock path stays green without credentials.

## License

Released under the [MIT Licence](LICENSE). Copyright (c) 2026 Mohamed SG Omar.

Original implementation. The competitor feature inventories in `docs/research/`
describe publicly documented capabilities in our own words for parity planning.
No third-party code or copyrighted text is included.
