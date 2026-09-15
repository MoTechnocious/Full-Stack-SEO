"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { ArrowDown, ArrowUp, Loader2, Minus, Plus, RefreshCw, ShieldAlert } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import {
  ApiError,
  getRankings,
  trackRankings,
  type RankTrackingSummary,
  type TrackedKeyword,
} from "@/lib/api";
import { DEMO_COUNTRY, DEMO_DOMAIN, mockRankTrackingSummary } from "@/lib/mock";
import { formatNumber, keywordDelta } from "@/lib/utils";

function renderDelta(current: number | null, previous: number | null): ReactNode {
  const delta = keywordDelta(current, previous);
  if (delta === null) return <span className="text-slate-600">—</span>;
  if (delta > 0) {
    return (
      <span className="inline-flex items-center gap-1 font-medium text-emerald-400">
        <ArrowUp className="h-3 w-3" /> {delta}
      </span>
    );
  }
  if (delta < 0) {
    return (
      <span className="inline-flex items-center gap-1 font-medium text-rose-400">
        <ArrowDown className="h-3 w-3" /> {Math.abs(delta)}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-slate-500">
      <Minus className="h-3 w-3" /> 0
    </span>
  );
}

const columns: Array<DataTableColumn<TrackedKeyword>> = [
  { key: "keyword", header: "Keyword", render: (k) => <span className="font-medium text-slate-200">{k.keyword}</span> },
  {
    key: "current",
    header: "Current",
    render: (k) => (k.current_position !== null ? k.current_position : <span className="text-slate-600">Not ranking</span>),
  },
  { key: "previous", header: "Previous", render: (k) => (k.previous_position !== null ? k.previous_position : "—") },
  { key: "delta", header: "Change", render: (k) => renderDelta(k.current_position, k.previous_position) },
  { key: "best", header: "Best", render: (k) => (k.best_position !== null ? k.best_position : "—") },
  { key: "volume", header: "Volume", render: (k) => formatNumber(k.search_volume) },
  {
    key: "trend",
    header: "7-Day Trend",
    render: (k) => <span className="font-mono text-[11px] text-slate-500">{k.history.map((h) => h.position ?? "–").join(" → ")}</span>,
  },
];

export default function RankingsPage() {
  const [domain, setDomain] = useState(DEMO_DOMAIN);
  const [country, setCountry] = useState(DEMO_COUNTRY);
  const [summary, setSummary] = useState<RankTrackingSummary>(mockRankTrackingSummary);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>("Showing demo data — refresh to fetch live rankings.");

  const [newKeywordsText, setNewKeywordsText] = useState("");
  const [addLoading, setAddLoading] = useState(false);

  async function handleRefresh(event: FormEvent) {
    event.preventDefault();
    if (!domain.trim()) return;
    setLoading(true);
    try {
      const result = await getRankings({ domain: domain.trim(), country });
      setSummary(result);
      setNotice(null);
    } catch (err) {
      setSummary(mockRankTrackingSummary);
      setNotice(
        err instanceof ApiError ? `${err.message} — showing demo data instead.` : "Could not reach the API — showing demo data instead.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleAddKeywords(event: FormEvent) {
    event.preventDefault();
    const keywords = newKeywordsText
      .split(/[,\n]/)
      .map((k) => k.trim())
      .filter(Boolean);
    if (keywords.length === 0 || !domain.trim()) return;
    setAddLoading(true);
    try {
      const result = await trackRankings({ domain: domain.trim(), keywords, country });
      setSummary(result);
      setNotice(null);
      setNewKeywordsText("");
    } catch (err) {
      setSummary(mockRankTrackingSummary);
      setNotice(
        err instanceof ApiError ? `${err.message} — showing demo data instead.` : "Could not reach the API — showing demo data instead.",
      );
    } finally {
      setAddLoading(false);
    }
  }

  return (
    <div>
      <PageHeader title="Rank Tracking" description="Monitor keyword positions over time and track overall visibility for a domain." />

      <Card>
        <form onSubmit={handleRefresh} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor="rank-domain" className="label-base">
              Domain
            </label>
            <input
              id="rank-domain"
              type="text"
              value={domain}
              onChange={(event) => setDomain(event.target.value)}
              className="input-base"
              autoComplete="off"
            />
          </div>
          <div className="sm:w-40">
            <label htmlFor="rank-country" className="label-base">
              Country
            </label>
            <input
              id="rank-country"
              type="text"
              value={country}
              onChange={(event) => setCountry(event.target.value)}
              className="input-base"
              autoComplete="off"
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary h-[42px]">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Refresh Rankings
          </button>
        </form>
        {notice && (
          <p className="mt-3 flex items-center gap-1.5 text-xs text-amber-400">
            <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
          </p>
        )}
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Avg. Position" value={summary.avg_position.toFixed(1)} />
        <KpiCard label="Visibility Score" value={summary.visibility_score.toFixed(1)} />
        <KpiCard label="Top 3" value={formatNumber(summary.top3)} />
        <KpiCard label="Top 10" value={formatNumber(summary.top10)} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card title="Tracked Keywords" className="xl:col-span-2" padded={false}>
          <DataTable columns={columns} data={summary.keywords} getRowKey={(k) => `${k.keyword}-${k.device}`} emptyMessage="No keywords tracked yet." />
        </Card>

        <Card title="Add Keywords" description="One per line or comma-separated">
          <form onSubmit={handleAddKeywords} className="space-y-3">
            <textarea
              value={newKeywordsText}
              onChange={(event) => setNewKeywordsText(event.target.value)}
              rows={6}
              placeholder={"running shoes for beginners\ntrail running shoes"}
              className="input-base resize-y text-xs"
              spellCheck={false}
            />
            <button type="submit" disabled={addLoading} className="btn-secondary w-full">
              {addLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Track Keywords
            </button>
            <div className="flex flex-wrap gap-2 pt-1 text-xs text-slate-500">
              <span>{summary.improved} improved</span>
              <span>·</span>
              <span>{summary.declined} declined</span>
              <span>·</span>
              <span>{summary.unchanged} unchanged</span>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
