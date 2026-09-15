# MySEOapp Frontend

Dashboard for MySEOapp — a Screaming Frog / Surfer / Rank Math / HikeSEO-style SEO
platform. Built with Next.js (App Router), TypeScript (strict) and Tailwind CSS.
No external UI kit; hand-rolled Tailwind components with `lucide-react` icons.

## Pages

| Route            | Purpose                                                              |
| ----------------- | --------------------------------------------------------------------- |
| `/`                | Dashboard overview — KPI cards, recent issues, quick links            |
| `/audit`           | Crawl a site (`runCrawl`) or check a single page (`auditPage`)        |
| `/onpage`          | Content editor — checklist (`analyzeOnpage`) + content score (`contentScore`) |
| `/keywords`        | Keyword research (`keywordResearch`) + SERP drill-down (`analyzeSerp`) |
| `/rankings`        | Rank tracking — `trackRankings` to add keywords, `getRankings` to refresh |
| `/reports`         | White-label report builder (`buildReport`) with a live branded preview |
| `/integrations`    | Lead capture (`submitLead`) + delivery log (`listDeliveries`)         |

## Getting started

```bash
npm install
cp ../.env.template .env.local   # or create .env.local manually, see below
npm run dev
```

The app runs at http://localhost:3000 and expects the backend API at
http://localhost:8000 by default.

## Environment variables

| Variable                    | Default                 | Description                                   |
| ---------------------------- | ------------------------ | ---------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL`   | `http://localhost:8000`  | Base URL of the MySEOapp REST API (no trailing slash; `/api/v1` is appended automatically by `src/lib/api.ts`) |

Create `.env.local` in this directory to override:

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
```

## Offline / demo mode

Every page seeds its UI from static, deterministic mock data
(`src/lib/mock.ts`) so the dashboard renders fully populated even with no
backend running. Any live API call that fails (network error or non-2xx
response) is caught and the page falls back to the same mock data with a
small "showing demo data" notice — the whole app is demoable offline.

## Scripts

```bash
npm run dev         # start the dev server
npm run build        # production build
npm run start         # run the production build
npm run lint           # ESLint (next/core-web-vitals)
npm run typecheck       # tsc --noEmit
```

## Project structure

```
src/
  app/                 # App Router pages (layout.tsx + one folder per route)
  components/          # Card, KpiCard, ScoreGauge, DataTable, Sidebar, Topbar, Badge, PageHeader
  lib/
    api.ts             # typed REST client — interfaces mirror the backend Pydantic models
    mock.ts             # static mock data matching those interfaces
    utils.ts             # small formatting/color helpers shared by pages & components
  styles/globals.css   # Tailwind directives + base dark theme
```

## Notes

- All API interfaces in `src/lib/api.ts` mirror the backend models field-for-field
  (`backend/app/models/*.py`), including wire-format `snake_case` keys.
- The API client never uses `any`: responses are parsed as `unknown` and
  returned via a single typed cast at the fetch boundary; request/response
  shapes are otherwise fully typed.
- Client components (`"use client"`) are used only where state or
  interactivity is needed (all six tool pages, plus `Sidebar`); the root
  layout, `Topbar`, `Card`, `KpiCard`, `ScoreGauge`, `DataTable`, `Badge` and
  the dashboard overview are server components.
