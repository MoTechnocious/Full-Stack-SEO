"use client";

import { useState, type FormEvent } from "react";
import { Loader2, Search, ShieldAlert } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge, { difficultyTone, intentTone } from "@/components/Badge";
import {
  ApiError,
  analyzeSerp,
  keywordResearch,
  type Keyword,
  type KeywordResearchResult,
  type SerpAnalysis,
  type SerpResultItem,
} from "@/lib/api";
import { DEMO_COUNTRY, DEMO_SEED_KEYWORD, mockKeywordResearchResult, mockSerpAnalysis } from "@/lib/mock";
import { formatNumber, titleCase } from "@/lib/utils";

const COUNTRIES = [
  { value: "us", label: "United States" },
  { value: "gb", label: "United Kingdom" },
  { value: "ca", label: "Canada" },
  { value: "au", label: "Australia" },
];

const serpColumns: Array<DataTableColumn<SerpResultItem>> = [
  { key: "position", header: "#", render: (r) => <span className="font-semibold text-slate-300">{r.position}</span> },
  { key: "domain", header: "Domain", render: (r) => <span className="text-slate-300">{r.domain}</span> },
  { key: "title", header: "Title", render: (r) => <span className="block max-w-sm truncate text-slate-200">{r.title}</span> },
  { key: "words", header: "Words", render: (r) => formatNumber(r.word_count) },
  { key: "backlinks", header: "Backlinks", render: (r) => formatNumber(r.backlinks) },
];

export default function KeywordsPage() {
  const [seed, setSeed] = useState(DEMO_SEED_KEYWORD);
  const [country, setCountry] = useState(DEMO_COUNTRY);
  const [result, setResult] = useState<KeywordResearchResult>(mockKeywordResearchResult);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>("Showing demo data — research a seed keyword to fetch live results.");

  const [serp, setSerp] = useState<SerpAnalysis | null>(null);
  const [serpLoading, setSerpLoading] = useState(false);
  const [serpIsMock, setSerpIsMock] = useState(false);

  async function handleResearch(event: FormEvent) {
    event.preventDefault();
    if (!seed.trim()) return;
    setLoading(true);
    try {
      const data = await keywordResearch({ seed: seed.trim(), country });
      setResult(data);
      setNotice(null);
    } catch (err) {
      setResult(mockKeywordResearchResult);
      setNotice(
        err instanceof ApiError ? `${err.message} — showing demo data instead.` : "Could not reach the API — showing demo data instead.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleViewSerp(keyword: string) {
    setSerp(null);
    setSerpLoading(true);
    try {
      const data = await analyzeSerp({ keyword, country });
      setSerp(data);
      setSerpIsMock(false);
    } catch {
      setSerp({ ...mockSerpAnalysis, keyword });
      setSerpIsMock(true);
    } finally {
      setSerpLoading(false);
    }
  }

  const columns: Array<DataTableColumn<Keyword>> = [
    { key: "keyword", header: "Keyword", render: (k) => <span className="font-medium text-slate-200">{k.keyword}</span> },
    { key: "volume", header: "Volume", render: (k) => formatNumber(k.search_volume) },
    { key: "difficulty", header: "Difficulty", render: (k) => <Badge tone={difficultyTone(k.difficulty)}>{k.difficulty}</Badge> },
    { key: "cpc", header: "CPC", render: (k) => `$${k.cpc.toFixed(2)}` },
    { key: "intent", header: "Intent", render: (k) => <Badge tone={intentTone(k.intent)}>{titleCase(k.intent)}</Badge> },
    {
      key: "actions",
      header: "",
      render: (k) => (
        <button
          type="button"
          onClick={() => handleViewSerp(k.keyword)}
          className="text-xs font-medium text-brand-300 transition hover:text-brand-200"
        >
          View SERP
        </button>
      ),
    },
  ];

  const totalVolume = result.keywords.reduce((sum, k) => sum + k.search_volume, 0);
  const avgDifficulty =
    result.keywords.length > 0
      ? Math.round(result.keywords.reduce((sum, k) => sum + k.difficulty, 0) / result.keywords.length)
      : 0;

  return (
    <div>
      <PageHeader title="Keyword Research" description="Expand a seed keyword into a full opportunity list with volume, difficulty, intent and clusters." />

      <Card>
        <form onSubmit={handleResearch} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor="kw-seed" className="label-base">
              Seed keyword
            </label>
            <input
              id="kw-seed"
              type="text"
              value={seed}
              onChange={(event) => setSeed(event.target.value)}
              className="input-base"
              autoComplete="off"
            />
          </div>
          <div className="sm:w-48">
            <label htmlFor="kw-country" className="label-base">
              Country
            </label>
            <select id="kw-country" value={country} onChange={(event) => setCountry(event.target.value)} className="input-base">
              {COUNTRIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" disabled={loading} className="btn-primary h-[42px]">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Research Keywords
          </button>
        </form>
        {notice && (
          <p className="mt-3 flex items-center gap-1.5 text-xs text-amber-400">
            <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
          </p>
        )}
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Keywords Found" value={formatNumber(result.total_keywords)} />
        <KpiCard label="Total Volume" value={formatNumber(totalVolume)} />
        <KpiCard label="Avg. Difficulty" value={`${avgDifficulty}`} />
        <KpiCard label="Clusters" value={formatNumber(result.clusters.length)} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card title="Keywords" className="xl:col-span-2" padded={false}>
          <DataTable columns={columns} data={result.keywords} getRowKey={(k) => k.keyword} emptyMessage="Research a seed keyword to see results here." />
        </Card>

        <Card title="Keyword Clusters" description="Grouped by shared topic and intent">
          <div className="space-y-5">
            {result.clusters.map((cluster) => (
              <div key={cluster.name}>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-slate-200">{cluster.name}</p>
                  <span className="shrink-0 text-xs text-slate-500">
                    {formatNumber(cluster.total_volume)} vol · {cluster.avg_difficulty.toFixed(1)} diff
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {cluster.keywords.map((k) => (
                    <Badge key={k.keyword} tone="neutral">
                      {k.keyword}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {(serpLoading || serp) && (
        <Card
          className="mt-6"
          title={serp ? `SERP Results — "${serp.keyword}"` : "Loading SERP…"}
          description={serp ? (serpIsMock ? "Demo data — API unavailable" : "Live results") : undefined}
        >
          {!serp ? (
            <div className="flex items-center gap-2 py-8 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading SERP results…
            </div>
          ) : (
            <>
              <div className="mb-4 flex flex-wrap gap-4 text-xs text-slate-400">
                <span>
                  Avg words: <span className="text-slate-200">{formatNumber(serp.avg_word_count)}</span>
                </span>
                <span>
                  Avg backlinks: <span className="text-slate-200">{formatNumber(serp.avg_backlinks)}</span>
                </span>
                <span>
                  Difficulty: <span className="text-slate-200">{serp.difficulty}</span>
                </span>
              </div>
              {serp.features.length > 0 && (
                <div className="mb-4 flex flex-wrap gap-1.5">
                  {serp.features.map((feature) => (
                    <Badge key={feature} tone="brand">
                      {titleCase(feature)}
                    </Badge>
                  ))}
                </div>
              )}
              <DataTable columns={serpColumns} data={serp.results} getRowKey={(r) => `${r.position}-${r.url}`} />
            </>
          )}
        </Card>
      )}
    </div>
  );
}
