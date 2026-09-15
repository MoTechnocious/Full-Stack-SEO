"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { Loader2, Lock, Play, Plus, ShieldAlert } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import ScoreGauge from "@/components/ScoreGauge";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge, { scoreBadgeTone, type BadgeTone } from "@/components/Badge";
import {
  ApiError,
  createTrackerConfig,
  getTrackerHistory,
  getTrackerMentionGap,
  getTrackerVisibility,
  listTrackerConfigs,
  runTrackerConfig,
  type EngineRollup,
  type MentionGapEntry,
  type MentionGapReport,
  type RefreshCadence,
  type SentimentLabel,
  type TrackerConfig,
  type TrackerEngine,
  type VisibilityRollup,
} from "@/lib/api";
import {
  mockMentionGapReport,
  mockTrackerConfigs,
  mockTrackerHistory,
  mockVisibilityRollup,
} from "@/lib/mock-tracker";
import { cn, formatDate, titleCase, truncate } from "@/lib/utils";

const ENGINE_LABELS: Record<TrackerEngine, string> = {
  chatgpt: "ChatGPT",
  perplexity: "Perplexity",
  gemini: "Gemini",
  google_ai_overviews: "AI Overviews",
  google_ai_mode: "AI Mode",
};

const ALL_ENGINES: TrackerEngine[] = [
  "chatgpt",
  "perplexity",
  "gemini",
  "google_ai_overviews",
  "google_ai_mode",
];

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function sentimentTone(label: SentimentLabel): BadgeTone {
  if (label === "positive") return "success";
  if (label === "negative") return "danger";
  return "neutral";
}

/** Run-over-run trend for a rate/share delta, expressed in percentage points. */
function rateTrend(delta: number | null): { trend: "up" | "down" | "flat"; label: string } {
  if (delta === null) return { trend: "flat", label: "n/a" };
  if (delta === 0) return { trend: "flat", label: "±0 pts" };
  return {
    trend: delta > 0 ? "up" : "down",
    label: `${delta > 0 ? "+" : ""}${Math.round(delta * 100)} pts`,
  };
}

/** Small colored run-over-run delta chip; `fmt` renders the non-zero value. */
function DeltaChip({ value, fmt }: { value: number | null; fmt: (v: number) => string }) {
  if (value === null) return <span className="text-xs text-slate-600">—</span>;
  if (value === 0) return <span className="text-xs text-slate-500">±0</span>;
  return (
    <span className={cn("text-xs font-medium tabular-nums", value > 0 ? "text-emerald-400" : "text-rose-400")}>
      {fmt(value)}
    </span>
  );
}

const fmtScoreDelta = (v: number) => `${v > 0 ? "+" : ""}${v.toFixed(1)}`;
const fmtPtsDelta = (v: number) => `${v > 0 ? "+" : ""}${Math.round(v * 100)} pts`;

export default function AiTrackerPage() {
  const [configs, setConfigs] = useState<TrackerConfig[]>(mockTrackerConfigs);
  const [configsAreMock, setConfigsAreMock] = useState(true);
  const [planGated, setPlanGated] = useState(false);
  const [selectedId, setSelectedId] = useState<string>(mockTrackerConfigs[0].id);
  const [notice, setNotice] = useState<string | null>(
    "Showing demo data — create a tracker config and run it to fetch live results.",
  );

  const [rollup, setRollup] = useState<VisibilityRollup>(mockVisibilityRollup);
  const [gap, setGap] = useState<MentionGapReport>(mockMentionGapReport);
  const [history, setHistory] = useState<VisibilityRollup[]>(mockTrackerHistory);
  const [reportIsMock, setReportIsMock] = useState(true);
  const [running, setRunning] = useState(false);

  const [newName, setNewName] = useState("");
  const [newBrand, setNewBrand] = useState("");
  const [newPrompts, setNewPrompts] = useState("");
  const [newCompetitors, setNewCompetitors] = useState("");
  const [newEngines, setNewEngines] = useState<TrackerEngine[]>(["chatgpt", "perplexity"]);
  const [newCadence, setNewCadence] = useState<RefreshCadence>("weekly");
  const [creating, setCreating] = useState(false);

  const selected = configs.find((c) => c.id === selectedId) ?? configs[0];

  useEffect(() => {
    let cancelled = false;
    listTrackerConfigs()
      .then((data) => {
        if (!cancelled && data.length > 0) {
          setConfigs(data);
          setConfigsAreMock(false);
          setSelectedId(data[0].id);
          setNotice(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled && err instanceof ApiError && err.status === 402) setPlanGated(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (configsAreMock) return;
    let cancelled = false;
    const onError = (err: unknown) => {
      if (!cancelled && err instanceof ApiError && err.status === 402) setPlanGated(true);
    };
    getTrackerVisibility(selectedId)
      .then((data) => {
        if (!cancelled) {
          setRollup(data);
          setReportIsMock(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setRollup(mockVisibilityRollup);
          setReportIsMock(true);
        }
        onError(err);
      });
    getTrackerMentionGap(selectedId)
      .then((data) => {
        if (!cancelled) setGap(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setGap(mockMentionGapReport);
        onError(err);
      });
    getTrackerHistory(selectedId)
      .then((data) => {
        if (!cancelled) setHistory(data.length > 0 ? data : mockTrackerHistory);
      })
      .catch((err: unknown) => {
        if (!cancelled) setHistory(mockTrackerHistory);
        onError(err);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, configsAreMock]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    const prompts = newPrompts
      .split("\n")
      .map((p) => p.trim())
      .filter(Boolean);
    const competitors = newCompetitors
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);
    if (!newName.trim() || !newBrand.trim() || prompts.length === 0) return;
    setCreating(true);
    try {
      const created = await createTrackerConfig({
        name: newName.trim(),
        brand: newBrand.trim(),
        prompts,
        competitors,
        engines: newEngines,
        refresh_cadence: newCadence,
      });
      setConfigs((prev) => [created, ...prev]);
      setConfigsAreMock(false);
      setSelectedId(created.id);
      setNotice(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        setPlanGated(true);
      } else {
        const local: TrackerConfig = {
          id: `trk_local_${configs.length + 1}`,
          name: newName.trim(),
          brand: newBrand.trim(),
          prompts,
          competitors,
          engines: newEngines.length > 0 ? newEngines : ["chatgpt"],
          market: "global",
          language: "en",
          own_domain: `${newBrand.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-")}.com`,
          refresh_cadence: newCadence,
          created_at: "2026-07-10T00:00:00Z",
          last_run_at: null,
        };
        setConfigs((prev) => [local, ...prev]);
        setSelectedId(local.id);
        setNotice("Could not reach the API — config added to the demo list only.");
      }
    } finally {
      setCreating(false);
      setNewName("");
      setNewBrand("");
      setNewPrompts("");
      setNewCompetitors("");
    }
  }

  async function handleRun() {
    setRunning(true);
    try {
      const report = await runTrackerConfig(selected.id);
      setRollup(report.rollup);
      setGap(report.mention_gap);
      setReportIsMock(false);
      setHistory((prev) => [...prev.filter((h) => h.run_at !== report.run_at), report.rollup]);
      setConfigs((prev) => prev.map((c) => (c.id === selected.id ? { ...c, last_run_at: report.run_at } : c)));
      setNotice(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        setPlanGated(true);
        setNotice(null);
      } else {
        setNotice(
          err instanceof ApiError
            ? `${err.message} — showing demo run results instead.`
            : "Could not reach the API — showing demo run results instead.",
        );
      }
      setRollup(mockVisibilityRollup);
      setGap(mockMentionGapReport);
      setHistory(mockTrackerHistory);
      setReportIsMock(true);
    } finally {
      setRunning(false);
    }
  }

  const engineColumns: Array<DataTableColumn<EngineRollup>> = [
    {
      key: "engine",
      header: "Engine",
      render: (e) => <span className="font-medium text-slate-200">{ENGINE_LABELS[e.engine]}</span>,
    },
    {
      key: "visibility",
      header: "Visibility",
      render: (e) => (
        <span className="inline-flex items-center gap-2">
          <Badge tone={scoreBadgeTone(e.visibility_score)}>{e.visibility_score.toFixed(1)}</Badge>
          <DeltaChip value={e.visibility_score_delta} fmt={fmtScoreDelta} />
        </span>
      ),
    },
    {
      key: "sov",
      header: "Share of Voice",
      render: (e) => (
        <span className="inline-flex items-center gap-2 tabular-nums">
          <span className="font-semibold text-slate-200">{pct(e.share_of_voice)}</span>
          <DeltaChip value={e.share_of_voice_delta} fmt={fmtPtsDelta} />
        </span>
      ),
    },
    {
      key: "mention_rate",
      header: "Mention Rate",
      render: (e) => (
        <span className="inline-flex items-center gap-2 tabular-nums">
          <span className="text-slate-300">
            {pct(e.mention_rate)}
            <span className="text-slate-500"> ({e.prompts_mentioned}/{e.prompts_total})</span>
          </span>
          <DeltaChip value={e.mention_rate_delta} fmt={fmtPtsDelta} />
        </span>
      ),
    },
    {
      key: "position",
      header: "Avg. Position",
      render: (e) => (
        <span className="inline-flex items-center gap-2 tabular-nums">
          <span className="text-slate-300">{e.avg_position === null ? "—" : `#${e.avg_position.toFixed(1)}`}</span>
          <DeltaChip value={e.avg_position_delta} fmt={fmtScoreDelta} />
        </span>
      ),
    },
    {
      key: "citations",
      header: "Citation Share",
      render: (e) => <span className="tabular-nums text-slate-300">{pct(e.citation_share)}</span>,
    },
    {
      key: "sentiment",
      header: "Sentiment",
      render: (e) => (
        <Badge tone={sentimentTone(e.sentiment_label)} dot>
          {titleCase(e.sentiment_label)} ({e.avg_sentiment.toFixed(2)})
        </Badge>
      ),
    },
  ];

  const gapColumns: Array<DataTableColumn<MentionGapEntry>> = [
    {
      key: "prompt",
      header: "Prompt",
      render: (g) => <span className="block max-w-sm text-slate-200">{truncate(g.prompt, 64)}</span>,
    },
    {
      key: "engines",
      header: "Gap Engines",
      render: (g) => (
        <div className="flex flex-wrap gap-1">
          {g.gap_engines.map((engine) => (
            <Badge key={engine} tone="warning">
              {ENGINE_LABELS[engine]}
            </Badge>
          ))}
        </div>
      ),
    },
    {
      key: "competitors",
      header: "Competitors Mentioned",
      render: (g) => (
        <div className="flex flex-wrap gap-1">
          {g.competitors_mentioned.map((c) => (
            <Badge key={c} tone="danger">
              {c}
            </Badge>
          ))}
        </div>
      ),
    },
    {
      key: "opportunity",
      header: "Opportunity",
      render: (g) => <span className="font-semibold text-slate-200 tabular-nums">{g.opportunity_score.toFixed(1)}</span>,
    },
  ];

  const historyColumns: Array<DataTableColumn<VisibilityRollup>> = [
    {
      key: "run",
      header: "Run",
      render: (h) => (
        <span className="text-slate-300">{formatDate(h.run_at, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
      ),
    },
    {
      key: "visibility",
      header: "Visibility",
      render: (h) => (
        <span className="inline-flex items-center gap-2">
          <Badge tone={scoreBadgeTone(h.overall.visibility_score)}>{h.overall.visibility_score.toFixed(1)}</Badge>
          <DeltaChip value={h.overall.visibility_score_delta} fmt={fmtScoreDelta} />
        </span>
      ),
    },
    {
      key: "sov",
      header: "Share of Voice",
      render: (h) => (
        <span className="inline-flex items-center gap-2 tabular-nums">
          <span className="text-slate-300">{pct(h.overall.share_of_voice)}</span>
          <DeltaChip value={h.overall.share_of_voice_delta} fmt={fmtPtsDelta} />
        </span>
      ),
    },
    {
      key: "mention_rate",
      header: "Mention Rate",
      render: (h) => <span className="tabular-nums text-slate-300">{pct(h.overall.mention_rate)}</span>,
    },
    {
      key: "position",
      header: "Avg. Position",
      render: (h) => (
        <span className="tabular-nums text-slate-300">
          {h.overall.avg_position === null ? "—" : `#${h.overall.avg_position.toFixed(1)}`}
        </span>
      ),
    },
  ];

  const sovKpi = rateTrend(rollup.overall.share_of_voice_delta);
  const mentionKpi = rateTrend(rollup.overall.mention_rate_delta);
  const positionDelta = rollup.overall.avg_position_delta;

  return (
    <div>
      <PageHeader
        title="AI Tracker (v2)"
        description="Scheduled answer-engine visibility tracking: managed prompt sets, Visibility Score, share of voice and mention-gap opportunities across ChatGPT, Perplexity, Gemini and Google AI."
      />

      {planGated && (
        <Card className="mb-6 border-amber-500/30 bg-amber-500/5">
          <div className="flex items-start gap-3">
            <Lock className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
            <div>
              <p className="text-sm font-semibold text-amber-200">AI Tracker requires a Growth+ plan</p>
              <p className="mt-1 text-xs text-slate-400">
                Your current plan does not include the AI Answer-Engine Visibility Tracker. Upgrade to a plan with the
                <span className="mx-1 font-mono text-slate-300">ai_tracker</span>feature to create tracker configs and
                run live scans. The data below is demo data.
              </p>
              <Link href="/billing" className="btn-primary mt-3 inline-flex">
                View plans &amp; upgrade
              </Link>
            </div>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card
          title="Tracker Configs"
          description={configsAreMock ? "Demo data — managed prompt sets" : "Managed prompt sets for this organization"}
          padded={false}
        >
          <ul className="divide-y divide-surface-border">
            {configs.map((config) => (
              <li key={config.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(config.id)}
                  className={cn(
                    "w-full px-5 py-4 text-left transition hover:bg-white/[0.03]",
                    config.id === selected.id && "bg-brand-500/10",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-slate-200">{config.name}</p>
                    <Badge tone={config.refresh_cadence === "daily" ? "brand" : "info"}>
                      {titleCase(config.refresh_cadence)}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {config.brand} · {config.prompts.length} prompts · {config.engines.map((e) => ENGINE_LABELS[e]).join(", ")}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-600">
                    Last run: {config.last_run_at ? formatDate(config.last_run_at) : "never"}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card
          title="New Tracker"
          description="Create a managed prompt set with competitors, engines and a refresh cadence"
          className="xl:col-span-2"
        >
          <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="trk-name" className="label-base">
                Name
              </label>
              <input
                id="trk-name"
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Core brand prompts"
                className="input-base"
                autoComplete="off"
              />
            </div>
            <div>
              <label htmlFor="trk-brand" className="label-base">
                Brand
              </label>
              <input
                id="trk-brand"
                type="text"
                value={newBrand}
                onChange={(e) => setNewBrand(e.target.value)}
                placeholder="e.g. Example Shop"
                className="input-base"
                autoComplete="off"
              />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="trk-prompts" className="label-base">
                Prompts (one per line)
              </label>
              <textarea
                id="trk-prompts"
                value={newPrompts}
                onChange={(e) => setNewPrompts(e.target.value)}
                placeholder={"what is the best online running shoe store\nbest running shoes for beginners"}
                rows={4}
                className="input-base resize-y"
              />
            </div>
            <div>
              <label htmlFor="trk-competitors" className="label-base">
                Competitors (comma-separated)
              </label>
              <input
                id="trk-competitors"
                type="text"
                value={newCompetitors}
                onChange={(e) => setNewCompetitors(e.target.value)}
                placeholder="RunnerHub, StridePro"
                className="input-base"
                autoComplete="off"
              />
            </div>
            <div>
              <label htmlFor="trk-cadence" className="label-base">
                Refresh cadence
              </label>
              <select
                id="trk-cadence"
                value={newCadence}
                onChange={(e) => setNewCadence(e.target.value as RefreshCadence)}
                className="input-base"
              >
                <option value="weekly">Weekly</option>
                <option value="daily">Daily (higher tiers)</option>
              </select>
            </div>
            <div className="sm:col-span-2">
              <p className="label-base">Engines</p>
              <div className="flex flex-wrap gap-2">
                {ALL_ENGINES.map((engine) => {
                  const active = newEngines.includes(engine);
                  return (
                    <button
                      key={engine}
                      type="button"
                      onClick={() =>
                        setNewEngines((prev) => (active ? prev.filter((e) => e !== engine) : [...prev, engine]))
                      }
                      className={cn(
                        "rounded-full px-3 py-1.5 text-xs font-medium ring-1 ring-inset transition",
                        active
                          ? "bg-brand-500/15 text-brand-200 ring-brand-500/40"
                          : "bg-surface-raised/40 text-slate-400 ring-surface-border hover:text-slate-200",
                      )}
                    >
                      {ENGINE_LABELS[engine]}
                    </button>
                  );
                })}
              </div>
              <p className="mt-1.5 text-xs text-slate-600">Leave all unselected to use your plan&apos;s full engine set.</p>
            </div>
            <div className="sm:col-span-2">
              <button type="submit" disabled={creating} className="btn-primary">
                {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Create Tracker
              </button>
            </div>
          </form>
        </Card>
      </div>

      <Card
        className="mt-6"
        title={`${selected.name} — Latest Run`}
        description={
          reportIsMock
            ? "Demo data — run the tracker to fetch live visibility metrics"
            : `${rollup.brand} · run of ${formatDate(rollup.run_at, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}`
        }
        actions={
          <button type="button" onClick={handleRun} disabled={running} className="btn-primary">
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Run Now
          </button>
        }
      >
        {notice && (
          <p className="mb-4 flex items-center gap-1.5 text-xs text-amber-400">
            <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
          </p>
        )}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          <div className="flex flex-col items-center justify-center gap-2">
            <ScoreGauge score={rollup.overall.visibility_score} label="Visibility Score" size={150} />
            <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
              <DeltaChip value={rollup.overall.visibility_score_delta} fmt={fmtScoreDelta} /> vs previous run
            </span>
          </div>
          <div className="lg:col-span-3">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <KpiCard
                label="Overall Share of Voice"
                value={pct(rollup.overall.share_of_voice)}
                trend={sovKpi.trend}
                trendLabel={sovKpi.label}
              />
              <KpiCard
                label="Mention Rate"
                value={pct(rollup.overall.mention_rate)}
                trend={mentionKpi.trend}
                trendLabel={mentionKpi.label}
              />
              <KpiCard
                label="Avg. Position"
                value={rollup.overall.avg_position === null ? "—" : `#${rollup.overall.avg_position.toFixed(1)}`}
                trend={positionDelta === null || positionDelta === 0 ? "flat" : positionDelta > 0 ? "up" : "down"}
                trendLabel={positionDelta === null ? "n/a" : fmtScoreDelta(positionDelta)}
              />
            </div>
            {Object.keys(rollup.overall.competitor_share_of_voice).length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Competitor share of voice</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {Object.entries(rollup.overall.competitor_share_of_voice).map(([name, share]) => (
                    <Badge key={name} tone="neutral" dot>
                      {name}: {pct(share)}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {rollup.engines.map((engine) => {
          const kpi = rateTrend(engine.share_of_voice_delta);
          return (
            <KpiCard
              key={engine.engine}
              label={`${ENGINE_LABELS[engine.engine]} — Share of Voice`}
              value={pct(engine.share_of_voice)}
              trend={kpi.trend}
              trendLabel={kpi.label}
            />
          );
        })}
      </div>

      <Card className="mt-6" title="Per-Engine Breakdown" description="Latest run metrics with run-over-run deltas" padded={false}>
        <DataTable
          columns={engineColumns}
          data={rollup.engines}
          getRowKey={(e) => e.engine}
          emptyMessage="Run the tracker to see per-engine metrics."
        />
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card
          title="Mention Gap"
          description={`Prompts where competitors appear but ${gap.brand} does not — ranked by opportunity`}
          padded={false}
        >
          <DataTable
            columns={gapColumns}
            data={gap.entries}
            getRowKey={(g) => g.prompt}
            emptyMessage="No mention gaps — your brand shows up everywhere competitors do."
          />
        </Card>

        <Card
          title="Run History"
          description={reportIsMock ? "Demo data — stored rollups per run" : `${history.length} stored runs`}
          padded={false}
        >
          <DataTable
            columns={historyColumns}
            data={[...history].reverse()}
            getRowKey={(h) => h.run_at}
            emptyMessage="No runs yet — hit Run Now to record the first rollup."
          />
        </Card>
      </div>
    </div>
  );
}
