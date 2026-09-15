"use client";

import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, Loader2, Plus, Radar, ScanSearch, ShieldAlert, XCircle } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import ScoreGauge from "@/components/ScoreGauge";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge, { severityTone, type BadgeTone } from "@/components/Badge";
import {
  ApiError,
  addGeoPrompt,
  geoReadinessAudit,
  geoSentimentScan,
  geoVisibilityScan,
  getCitationDomains,
  getPromptTracker,
  listGeoPrompts,
  researchGeoPrompts,
  type AnswerEngine,
  type DomainCategory,
  type DomainTrustReport,
  type FunnelStage,
  type PromptResearchResult,
  type PromptTrackerEntry,
  type PromptTrackerReport,
  type ReadinessReport,
  type SentimentLabel,
  type SentimentReport,
  type TrackedPrompt,
  type VisibilityReport,
} from "@/lib/api";
import { DEMO_URL } from "@/lib/mock";
import {
  DEMO_BRAND,
  DEMO_COMPETITORS,
  DEMO_PROMPT_TOPIC,
  mockDomainTrustReport,
  mockPromptTrackerReport,
  mockReadinessReport,
  mockSentimentReport,
  mockTrackedPrompts,
  mockVisibilityReport,
} from "@/lib/mock-ai";
import { cn, formatDate, formatNumber, formatSigned, titleCase, truncate } from "@/lib/utils";

const ENGINE_LABELS: Record<AnswerEngine, string> = {
  chatgpt: "ChatGPT",
  claude: "Claude",
  perplexity: "Perplexity",
  copilot: "Copilot",
  gemini: "Gemini",
  google_ai_overviews: "AI Overviews",
};

function funnelTone(stage: FunnelStage): BadgeTone {
  switch (stage) {
    case "bofu":
      return "success";
    case "mofu":
      return "brand";
    default:
      return "info";
  }
}

function categoryTone(category: DomainCategory): BadgeTone {
  switch (category) {
    case "encyclopedia":
    case "review_platform":
      return "success";
    case "community":
    case "qa_forum":
      return "info";
    case "own_domain":
      return "brand";
    case "news":
      return "warning";
    default:
      return "neutral";
  }
}

function sentimentCellClass(label: SentimentLabel): string {
  switch (label) {
    case "positive":
      return "bg-emerald-500/25 text-emerald-200 ring-emerald-500/30";
    case "negative":
      return "bg-rose-500/25 text-rose-200 ring-rose-500/30";
    default:
      return "bg-slate-500/15 text-slate-300 ring-slate-500/25";
  }
}

function sentimentTone(label: SentimentLabel): BadgeTone {
  if (label === "positive") return "success";
  if (label === "negative") return "danger";
  return "neutral";
}

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export default function GeoPage() {
  const [brand, setBrand] = useState(DEMO_BRAND);
  const [competitors, setCompetitors] = useState(DEMO_COMPETITORS.join(", "));
  const [report, setReport] = useState<VisibilityReport>(mockVisibilityReport);
  const [scanLoading, setScanLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(
    "Showing demo data — run a visibility scan to fetch live results.",
  );

  const [prompts, setPrompts] = useState<TrackedPrompt[]>(mockTrackedPrompts);
  const [promptsAreMock, setPromptsAreMock] = useState(true);
  const [newPrompt, setNewPrompt] = useState("");
  const [addingPrompt, setAddingPrompt] = useState(false);

  const [researchTopic, setResearchTopic] = useState(DEMO_PROMPT_TOPIC);
  const [research, setResearch] = useState<PromptResearchResult | null>(null);
  const [researchLoading, setResearchLoading] = useState(false);

  const [tracker, setTracker] = useState<PromptTrackerReport>(mockPromptTrackerReport);
  const [trackerIsMock, setTrackerIsMock] = useState(true);

  const [domains, setDomains] = useState<DomainTrustReport>(mockDomainTrustReport);
  const [domainsAreMock, setDomainsAreMock] = useState(true);

  const [sentiment, setSentiment] = useState<SentimentReport>(mockSentimentReport);
  const [sentimentIsMock, setSentimentIsMock] = useState(true);
  const [sentimentLoading, setSentimentLoading] = useState(false);

  const [readinessUrl, setReadinessUrl] = useState(DEMO_URL);
  const [readiness, setReadiness] = useState<ReadinessReport>(mockReadinessReport);
  const [readinessIsMock, setReadinessIsMock] = useState(true);
  const [readinessLoading, setReadinessLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listGeoPrompts()
      .then((data) => {
        if (!cancelled && data.length > 0) {
          setPrompts(data);
          setPromptsAreMock(false);
        }
      })
      .catch(() => undefined);
    getPromptTracker({ brand: DEMO_BRAND })
      .then((data) => {
        if (!cancelled && data.entries.length > 0) {
          setTracker(data);
          setTrackerIsMock(false);
        }
      })
      .catch(() => undefined);
    getCitationDomains()
      .then((data) => {
        if (!cancelled && data.domains.length > 0) {
          setDomains(data);
          setDomainsAreMock(false);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  function parsedCompetitors(): string[] {
    return competitors
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);
  }

  async function handleScan(event: FormEvent) {
    event.preventDefault();
    if (!brand.trim()) return;
    setScanLoading(true);
    try {
      const data = await geoVisibilityScan({ brand: brand.trim(), competitors: parsedCompetitors() });
      setReport(data);
      setNotice(null);
    } catch (err) {
      setReport(mockVisibilityReport);
      setNotice(
        err instanceof ApiError ? `${err.message} — showing demo data instead.` : "Could not reach the API — showing demo data instead.",
      );
    } finally {
      setScanLoading(false);
    }
  }

  async function handleAddPrompt(event: FormEvent) {
    event.preventDefault();
    const text = newPrompt.trim();
    if (!text) return;
    setAddingPrompt(true);
    try {
      const created = await addGeoPrompt({ text });
      setPrompts((prev) => [created, ...prev]);
      setPromptsAreMock(false);
    } catch {
      setPrompts((prev) => [
        {
          id: `prm_local_${prev.length + 1}`,
          text,
          funnel_stage: "tofu",
          intent_tags: [],
          volume_estimate: 0,
          created_on: "2026-07-10",
        },
        ...prev,
      ]);
    } finally {
      setNewPrompt("");
      setAddingPrompt(false);
    }
  }

  async function handleResearch(event: FormEvent) {
    event.preventDefault();
    if (!researchTopic.trim()) return;
    setResearchLoading(true);
    try {
      const data = await researchGeoPrompts({ topic: researchTopic.trim() });
      setResearch(data);
    } catch {
      const { mockPromptResearchResult } = await import("@/lib/mock-ai");
      setResearch({ ...mockPromptResearchResult, topic: researchTopic.trim() });
    } finally {
      setResearchLoading(false);
    }
  }

  async function handleSentimentScan() {
    setSentimentLoading(true);
    try {
      const data = await geoSentimentScan({ brand: brand.trim() || DEMO_BRAND });
      setSentiment(data);
      setSentimentIsMock(false);
    } catch {
      setSentiment(mockSentimentReport);
      setSentimentIsMock(true);
    } finally {
      setSentimentLoading(false);
    }
  }

  async function handleReadinessAudit(event: FormEvent) {
    event.preventDefault();
    if (!readinessUrl.trim()) return;
    setReadinessLoading(true);
    try {
      const data = await geoReadinessAudit({ url: readinessUrl.trim() });
      setReadiness(data);
      setReadinessIsMock(false);
    } catch {
      setReadiness(mockReadinessReport);
      setReadinessIsMock(true);
    } finally {
      setReadinessLoading(false);
    }
  }

  const promptColumns: Array<DataTableColumn<TrackedPrompt>> = [
    { key: "text", header: "Prompt", render: (p) => <span className="block max-w-md text-slate-200">{p.text}</span> },
    { key: "stage", header: "Funnel", render: (p) => <Badge tone={funnelTone(p.funnel_stage)}>{p.funnel_stage.toUpperCase()}</Badge> },
    {
      key: "tags",
      header: "Intent",
      render: (p) => (
        <div className="flex flex-wrap gap-1">
          {p.intent_tags.length === 0 ? (
            <span className="text-slate-500">—</span>
          ) : (
            p.intent_tags.map((tag) => (
              <Badge key={tag} tone="neutral">
                {tag}
              </Badge>
            ))
          )}
        </div>
      ),
    },
    { key: "volume", header: "Est. Volume", render: (p) => formatNumber(p.volume_estimate) },
    { key: "created", header: "Added", render: (p) => <span className="text-slate-400">{formatDate(p.created_on)}</span> },
  ];

  const trackerColumns: Array<DataTableColumn<PromptTrackerEntry>> = [
    {
      key: "prompt",
      header: "Prompt",
      render: (entry) => <span className="block max-w-xs text-slate-200">{truncate(entry.prompt.text, 56)}</span>,
    },
    ...tracker.engines.map((engine): DataTableColumn<PromptTrackerEntry> => ({
      key: engine,
      header: ENGINE_LABELS[engine],
      render: (entry) => {
        const rank = entry.engines.find((e) => e.engine === engine);
        if (!rank || rank.current_rank === null) return <span className="text-slate-600">—</span>;
        const delta = rank.previous_rank !== null ? rank.previous_rank - rank.current_rank : null;
        return (
          <span className="inline-flex items-center gap-1.5 tabular-nums">
            <span className="font-semibold text-slate-200">#{rank.current_rank}</span>
            {delta !== null && delta !== 0 && (
              <span className={cn("text-xs", delta > 0 ? "text-emerald-400" : "text-rose-400")}>{formatSigned(delta)}</span>
            )}
          </span>
        );
      },
    })),
  ];

  const domainColumns: Array<DataTableColumn<DomainTrustReport["domains"][number]>> = [
    { key: "domain", header: "Domain", render: (d) => <span className="font-medium text-slate-200">{d.domain}</span> },
    { key: "category", header: "Category", render: (d) => <Badge tone={categoryTone(d.category)}>{titleCase(d.category)}</Badge> },
    { key: "trust", header: "Trust", render: (d) => <Badge tone={d.trust_weight >= 0.8 ? "success" : d.trust_weight >= 0.6 ? "warning" : "neutral"}>{pct(d.trust_weight)}</Badge> },
    { key: "citations", header: "Citations", render: (d) => formatNumber(d.citations) },
    { key: "frequency", header: "Frequency", render: (d) => pct(d.frequency) },
    { key: "priority", header: "Priority", render: (d) => <span className="font-semibold text-slate-200 tabular-nums">{d.priority_score.toFixed(1)}</span> },
  ];

  const heatmapEngines = Array.from(new Set(sentiment.cells.map((c) => c.engine)));
  const heatmapPrompts = Array.from(new Set(sentiment.cells.map((c) => c.prompt)));

  return (
    <div>
      <PageHeader
        title="AI Visibility (GEO)"
        description="Track how ChatGPT, Claude, Perplexity, Copilot, Gemini and Google AI Overviews mention, rank and cite your brand."
      />

      <Card>
        <form onSubmit={handleScan} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor="geo-brand" className="label-base">
              Brand
            </label>
            <input id="geo-brand" type="text" value={brand} onChange={(e) => setBrand(e.target.value)} className="input-base" autoComplete="off" />
          </div>
          <div className="flex-1">
            <label htmlFor="geo-competitors" className="label-base">
              Competitors (comma-separated)
            </label>
            <input
              id="geo-competitors"
              type="text"
              value={competitors}
              onChange={(e) => setCompetitors(e.target.value)}
              className="input-base"
              autoComplete="off"
            />
          </div>
          <button type="submit" disabled={scanLoading} className="btn-primary h-[42px]">
            {scanLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radar className="h-4 w-4" />}
            Run Visibility Scan
          </button>
        </form>
        {notice && (
          <p className="mt-3 flex items-center gap-1.5 text-xs text-amber-400">
            <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
          </p>
        )}
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {report.engines.map((engine) => {
          const delta = engine.share_of_voice_delta;
          return (
            <KpiCard
              key={engine.engine}
              label={`${ENGINE_LABELS[engine.engine]} — Share of Voice`}
              value={pct(engine.share_of_voice)}
              trend={delta === null || delta === 0 ? "flat" : delta > 0 ? "up" : "down"}
              trendLabel={delta === null ? "n/a" : `${delta > 0 ? "+" : ""}${Math.round(delta * 100)} pts`}
            />
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Overall Share of Voice" value={pct(report.overall.share_of_voice)} />
        <KpiCard label="Mention Frequency" value={pct(report.overall.mention_frequency)} />
        <KpiCard label="Avg. Position" value={report.overall.avg_position === null ? "—" : report.overall.avg_position.toFixed(1)} />
        <KpiCard label="Prompts Scanned" value={formatNumber(report.overall.prompts_scanned)} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card
          title="Prompt Library"
          description={promptsAreMock ? "Demo data — tracked conversational prompts" : "Tracked conversational prompts"}
          className="xl:col-span-2"
          padded={false}
        >
          <form onSubmit={handleAddPrompt} className="flex gap-2 border-b border-surface-border px-5 py-4">
            <input
              type="text"
              value={newPrompt}
              onChange={(e) => setNewPrompt(e.target.value)}
              placeholder="e.g. what is the best online running store"
              className="input-base flex-1"
              autoComplete="off"
            />
            <button type="submit" disabled={addingPrompt} className="btn-secondary shrink-0">
              {addingPrompt ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Track
            </button>
          </form>
          <DataTable columns={promptColumns} data={prompts} getRowKey={(p) => p.id} emptyMessage="No prompts tracked yet." />
        </Card>

        <Card title="Prompt Research" description="Discover prompts your buyers ask AI assistants">
          <form onSubmit={handleResearch} className="flex gap-2">
            <input
              type="text"
              value={researchTopic}
              onChange={(e) => setResearchTopic(e.target.value)}
              className="input-base flex-1"
              autoComplete="off"
            />
            <button type="submit" disabled={researchLoading} className="btn-secondary shrink-0">
              {researchLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanSearch className="h-4 w-4" />}
              Research
            </button>
          </form>
          {research && (
            <ul className="mt-4 space-y-3">
              {research.suggestions.map((s) => (
                <li key={s.text} className="rounded-xl border border-surface-border bg-surface-raised/40 p-3">
                  <p className="text-sm text-slate-200">{s.text}</p>
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Badge tone={funnelTone(s.funnel_stage)}>{s.funnel_stage.toUpperCase()}</Badge>
                      <span className="text-xs text-slate-500">{formatNumber(s.volume_estimate)} est. vol</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setNewPrompt(s.text);
                      }}
                      className="text-xs font-medium text-brand-300 transition hover:text-brand-200"
                    >
                      Use
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card
        className="mt-6"
        title="Prompt Tracker"
        description={trackerIsMock ? "Demo data — brand rank per prompt per engine" : `Brand rank per prompt per engine for ${tracker.brand}`}
        padded={false}
      >
        <DataTable
          columns={trackerColumns}
          data={tracker.entries}
          getRowKey={(entry) => entry.prompt.id}
          emptyMessage="Track prompts to start monitoring your rank in AI answers."
        />
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card
          title="Citation Sources"
          description={
            domainsAreMock
              ? "Demo data — domains AI engines cite, ranked by outreach priority"
              : `${formatNumber(domains.total_citations)} citations aggregated across scans`
          }
          padded={false}
        >
          <DataTable columns={domainColumns} data={domains.domains} getRowKey={(d) => d.domain} emptyMessage="Run a citation scan to populate this report." />
        </Card>

        <Card
          title="Sentiment Heatmap"
          description={sentimentIsMock ? "Demo data — how each engine portrays your brand per prompt" : `Overall: ${titleCase(sentiment.overall_label)} (${sentiment.overall_score.toFixed(2)})`}
          actions={
            <button type="button" onClick={handleSentimentScan} disabled={sentimentLoading} className="btn-secondary">
              {sentimentLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radar className="h-4 w-4" />}
              Scan Sentiment
            </button>
          }
        >
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[520px] border-separate border-spacing-1 text-left text-xs">
              <thead>
                <tr>
                  <th className="px-2 py-1 font-semibold uppercase tracking-wide text-slate-500">Engine</th>
                  {heatmapPrompts.map((prompt) => (
                    <th key={prompt} className="px-2 py-1 font-medium normal-case text-slate-500" title={prompt}>
                      {truncate(prompt, 24)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmapEngines.map((engine) => (
                  <tr key={engine}>
                    <td className="whitespace-nowrap px-2 py-1 font-medium text-slate-300">{ENGINE_LABELS[engine]}</td>
                    {heatmapPrompts.map((prompt) => {
                      const cell = sentiment.cells.find((c) => c.engine === engine && c.prompt === prompt);
                      if (!cell) {
                        return (
                          <td key={prompt} className="px-2 py-1 text-center text-slate-600">
                            —
                          </td>
                        );
                      }
                      return (
                        <td key={prompt} title={`${titleCase(cell.label)} (${cell.score.toFixed(2)})`}>
                          <div
                            className={cn(
                              "rounded-lg px-2 py-2 text-center font-semibold tabular-nums ring-1 ring-inset",
                              sentimentCellClass(cell.label),
                            )}
                          >
                            {cell.score > 0 ? "+" : ""}
                            {cell.score.toFixed(1)}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {sentiment.per_engine.map((e) => (
              <Badge key={e.engine} tone={sentimentTone(e.label)} dot>
                {ENGINE_LABELS[e.engine]}: {e.avg_score.toFixed(2)}
              </Badge>
            ))}
          </div>
        </Card>
      </div>

      <Card
        className="mt-6"
        title="AI Readiness"
        description={readinessIsMock ? "Demo data — audit how ready a page is for AI crawlers and answer engines" : `Live audit of ${readiness.url}`}
      >
        <form onSubmit={handleReadinessAudit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor="geo-readiness-url" className="label-base">
              Page URL
            </label>
            <input
              id="geo-readiness-url"
              type="text"
              value={readinessUrl}
              onChange={(e) => setReadinessUrl(e.target.value)}
              className="input-base"
              autoComplete="off"
            />
          </div>
          <button type="submit" disabled={readinessLoading} className="btn-primary h-[42px]">
            {readinessLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanSearch className="h-4 w-4" />}
            Audit Readiness
          </button>
        </form>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="flex flex-col items-center justify-center gap-3">
            <ScoreGauge score={readiness.score} label="AI Readiness" size={150} />
            <Badge tone={readiness.score >= 80 ? "success" : readiness.score >= 50 ? "warning" : "danger"}>
              Grade {readiness.grade} · {readiness.passed_count}/{readiness.total_count} checks passed
            </Badge>
            <div className="flex flex-wrap justify-center gap-1.5">
              {readiness.crawler_access.map((c) => (
                <Badge key={c.crawler} tone={c.allowed ? "success" : "danger"} dot>
                  {c.crawler}
                </Badge>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Checks</p>
            <ul className="space-y-2">
              {readiness.checks.map((check) => (
                <li key={check.code} className="flex items-start gap-2 text-sm">
                  {check.passed ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                  ) : (
                    <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                  )}
                  <div>
                    <p className="text-slate-200">{check.label}</p>
                    <p className="text-xs text-slate-500">{check.message}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Prioritized fixes</p>
            <div className="space-y-3">
              {readiness.fixes.map((fix) => (
                <div key={fix.code} className="rounded-xl border border-surface-border bg-surface-raised/40 p-3">
                  <div className="flex items-center gap-2">
                    <Badge tone={severityTone(fix.severity)} dot>
                      {titleCase(fix.severity)}
                    </Badge>
                    <p className="text-sm font-medium text-slate-200">{fix.title}</p>
                  </div>
                  <p className="mt-1.5 text-xs text-slate-400">{fix.recommendation}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
