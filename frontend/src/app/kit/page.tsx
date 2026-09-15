"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Loader2,
  Map,
  Play,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge, { severityTone, type BadgeTone } from "@/components/Badge";
import {
  ApiError,
  approveAction,
  buildActionPlan,
  buildCalendar,
  listQueue,
  mapKeywords,
  runQueue,
  type ActionItemPlan,
  type ContentCalendar,
  type ExecutionStatus,
  type KeywordMapResult,
  type QueuedAction,
} from "@/lib/api";
import { DEMO_URL, mockKeywordResearchResult } from "@/lib/mock";
import {
  mockActionItemPlan,
  mockContentCalendar,
  mockKeywordMapResult,
  mockQueuedActions,
} from "@/lib/mock-ai";
import { formatDate, formatNumber, titleCase, truncate } from "@/lib/utils";

const DEMO_MAP_KEYWORDS = [
  "best running shoes for beginners",
  "trail running shoes",
  "when to replace running shoes",
  "running shoe subscription",
];

const DEMO_MAP_PAGES = [
  {
    url: "https://www.example-shop.com/guides/beginner-running-shoes",
    title: "Best Running Shoes for Beginners",
    content: "Guide to the best running shoes for beginners, covering cushioning, fit and when to replace running shoes.",
  },
  {
    url: "https://www.example-shop.com/collections/trail",
    title: "Trail Running Shoes",
    content: "Shop trail running shoes with aggressive grip for off-road runs.",
  },
  {
    url: "https://www.example-shop.com/guides/when-to-replace-shoes",
    title: "When to Replace Running Shoes",
    content: "How many miles running shoes last and the signs it is time to replace running shoes.",
  },
];

function executionStatusTone(status: ExecutionStatus): BadgeTone {
  switch (status) {
    case "completed":
      return "success";
    case "running":
      return "info";
    case "awaiting_approval":
      return "warning";
    case "failed":
      return "danger";
    default:
      return "neutral";
  }
}

export default function KitPage() {
  const [site, setSite] = useState(DEMO_URL);
  const [plan, setPlan] = useState<ActionItemPlan>(mockActionItemPlan);
  const [planLoading, setPlanLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(
    "Showing demo data — generate a plan for your site to fetch live results.",
  );
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const [queue, setQueue] = useState<QueuedAction[]>(mockQueuedActions);
  const [queueIsMock, setQueueIsMock] = useState(true);
  const [queueRunning, setQueueRunning] = useState(false);
  const [queueNotice, setQueueNotice] = useState<string | null>(null);

  const [keywordMap, setKeywordMap] = useState<KeywordMapResult>(mockKeywordMapResult);
  const [mapIsMock, setMapIsMock] = useState(true);
  const [mapLoading, setMapLoading] = useState(false);

  const [calendar, setCalendar] = useState<ContentCalendar>(mockContentCalendar);
  const [calendarIsMock, setCalendarIsMock] = useState(true);
  const [calendarLoading, setCalendarLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listQueue()
      .then((actions) => {
        if (!cancelled) {
          setQueue(actions.length > 0 ? actions : mockQueuedActions);
          setQueueIsMock(actions.length === 0);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setQueue(mockQueuedActions);
          setQueueIsMock(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleGeneratePlan(event: FormEvent) {
    event.preventDefault();
    if (!site.trim()) return;
    setPlanLoading(true);
    try {
      const data = await buildActionPlan({ site: site.trim() });
      setPlan(data);
      setNotice(null);
    } catch (err) {
      setPlan(mockActionItemPlan);
      setNotice(
        err instanceof ApiError ? `${err.message} — showing demo data instead.` : "Could not reach the API — showing demo data instead.",
      );
    } finally {
      setPlanLoading(false);
    }
  }

  async function handleApprove(id: string) {
    try {
      const updated = await approveAction(id);
      setQueue((q) => q.map((a) => (a.id === id ? updated : a)));
    } catch {
      setQueue((q) =>
        q.map((a) => (a.id === id ? { ...a, status: "pending" as ExecutionStatus, approval_required: false } : a)),
      );
      setQueueNotice("Could not reach the API — approval simulated on demo data.");
    }
  }

  async function handleRunQueue() {
    setQueueRunning(true);
    try {
      const report = await runQueue();
      setQueue(report.actions);
      setQueueIsMock(false);
      setQueueNotice(
        `Run finished: ${report.executed} executed, ${report.completed} completed, ${report.failed} failed, ${report.skipped_awaiting_approval} awaiting approval.`,
      );
    } catch {
      setQueue((q) =>
        q.map((a) =>
          a.status === "pending" ? { ...a, status: "completed" as ExecutionStatus, attempts: a.attempts + 1 } : a,
        ),
      );
      setQueueNotice("Could not reach the API — queue run simulated on demo data.");
    } finally {
      setQueueRunning(false);
    }
  }

  async function handleMapKeywords() {
    setMapLoading(true);
    try {
      const data = await mapKeywords({ keywords: DEMO_MAP_KEYWORDS, pages: DEMO_MAP_PAGES });
      setKeywordMap(data);
      setMapIsMock(false);
    } catch {
      setKeywordMap(mockKeywordMapResult);
      setMapIsMock(true);
    } finally {
      setMapLoading(false);
    }
  }

  async function handleBuildCalendar() {
    setCalendarLoading(true);
    try {
      const data = await buildCalendar({
        keywords: mockKeywordResearchResult.keywords.slice(0, 6),
        start_date: "2026-07-13",
        cadence: "weekly",
        max_entries: 6,
      });
      setCalendar(data);
      setCalendarIsMock(false);
    } catch {
      setCalendar(mockContentCalendar);
      setCalendarIsMock(true);
    } finally {
      setCalendarLoading(false);
    }
  }

  const queueColumns: Array<DataTableColumn<QueuedAction>> = [
    {
      key: "type",
      header: "Action",
      render: (a) => (
        <div>
          <p className="font-medium text-slate-200">{titleCase(a.type)}</p>
          {a.last_error && <p className="mt-0.5 text-xs text-rose-400">{truncate(a.last_error, 60)}</p>}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (a) => (
        <Badge tone={executionStatusTone(a.status)} dot>
          {titleCase(a.status)}
        </Badge>
      ),
    },
    {
      key: "attempts",
      header: "Attempts",
      render: (a) => (
        <span className="tabular-nums text-slate-300">
          {a.attempts}/{a.max_attempts}
        </span>
      ),
    },
    { key: "updated", header: "Updated", render: (a) => <span className="text-slate-400">{formatDate(a.updated_at)}</span> },
    {
      key: "actions",
      header: "",
      render: (a) =>
        a.status === "awaiting_approval" ? (
          <button
            type="button"
            onClick={() => handleApprove(a.id)}
            className="inline-flex items-center gap-1 text-xs font-medium text-brand-300 transition hover:text-brand-200"
          >
            <CheckCircle2 className="h-3.5 w-3.5" /> Approve
          </button>
        ) : null,
    },
  ];

  const totalMinutes = plan.items.reduce((sum, item) => sum + item.estimated_minutes, 0);
  const urgentCount = plan.items.filter((i) => i.severity === "critical" || i.severity === "high").length;

  return (
    <div>
      <PageHeader
        title="Kit AI Assistant"
        description="A prioritized, plain-English to-do list with guided fixes, an agentic execution queue, keyword mapping and a content calendar."
      />

      <Card>
        <form onSubmit={handleGeneratePlan} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor="kit-site" className="label-base">
              Site URL
            </label>
            <input
              id="kit-site"
              type="text"
              value={site}
              onChange={(event) => setSite(event.target.value)}
              className="input-base"
              autoComplete="off"
            />
          </div>
          <button type="submit" disabled={planLoading} className="btn-primary h-[42px]">
            {planLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Generate Action Plan
          </button>
        </form>
        {notice && (
          <p className="mt-3 flex items-center gap-1.5 text-xs text-amber-400">
            <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
          </p>
        )}
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Action Items" value={formatNumber(plan.total)} />
        <KpiCard label="High Priority" value={formatNumber(urgentCount)} />
        <KpiCard label="Est. Time" value={`${formatNumber(totalMinutes)} min`} />
        <KpiCard label="Queued Actions" value={formatNumber(queue.length)} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card
          title="Action Plan"
          description={`Prioritized fixes for ${plan.site} — click an item for guided steps`}
          padded={false}
        >
          <ul className="divide-y divide-surface-border">
            {plan.items.map((item) => {
              const expanded = expandedId === item.id;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => setExpandedId(expanded ? null : item.id)}
                    className="flex w-full items-start justify-between gap-3 px-5 py-4 text-left transition hover:bg-white/[0.03]"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={severityTone(item.severity)} dot>
                          {titleCase(item.severity)}
                        </Badge>
                        <span className="text-xs text-slate-500">Priority {item.priority_score}</span>
                        <span className="text-xs text-slate-500">~{item.estimated_minutes} min</span>
                      </div>
                      <p className="mt-1.5 text-sm font-medium text-slate-200">{item.title}</p>
                      {item.page_url && <p className="mt-0.5 truncate text-xs text-slate-500">{item.page_url}</p>}
                    </div>
                    {expanded ? (
                      <ChevronUp className="mt-1 h-4 w-4 shrink-0 text-slate-500" />
                    ) : (
                      <ChevronDown className="mt-1 h-4 w-4 shrink-0 text-slate-500" />
                    )}
                  </button>
                  {expanded && (
                    <div className="border-t border-surface-border bg-white/[0.02] px-5 py-4">
                      <p className="text-xs text-slate-400">
                        <span className="font-semibold text-slate-300">What it means: </span>
                        {item.what_it_means}
                      </p>
                      <p className="mt-1.5 text-xs text-slate-400">
                        <span className="font-semibold text-slate-300">Why it matters: </span>
                        {item.why_it_matters}
                      </p>
                      <ol className="mt-3 space-y-2">
                        {item.steps.map((step) => (
                          <li key={step.number} className="flex items-start gap-2.5 text-sm text-slate-300">
                            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-500/15 text-[11px] font-semibold text-brand-300">
                              {step.number}
                            </span>
                            {step.instruction}
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </Card>

        <Card
          title="Execution Queue"
          description={queueIsMock ? "Demo data — API unavailable or queue empty" : "Live queue for this organization"}
          padded={false}
          actions={
            <button type="button" onClick={handleRunQueue} disabled={queueRunning} className="btn-primary">
              {queueRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Run Queue
            </button>
          }
        >
          {queueNotice && (
            <p className="flex items-center gap-1.5 border-b border-surface-border px-5 py-3 text-xs text-amber-400">
              <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {queueNotice}
            </p>
          )}
          <DataTable
            columns={queueColumns}
            data={queue}
            getRowKey={(a) => a.id}
            emptyMessage="No actions queued — Kit enqueues work from your action plan."
          />
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card
          title="Keyword Map & Cannibalization"
          description={mapIsMock ? "Demo data — map your keywords for live results" : "Live results"}
          actions={
            <button type="button" onClick={handleMapKeywords} disabled={mapLoading} className="btn-secondary">
              {mapLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Map className="h-4 w-4" />}
              Map Keywords
            </button>
          }
        >
          <div className="space-y-3">
            {keywordMap.assignments.map((a) => (
              <div key={a.keyword} className="rounded-xl border border-surface-border bg-surface-raised/40 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-slate-200">{a.keyword}</p>
                  <Badge tone={a.page_url ? "success" : "warning"}>{a.page_url ? `${Math.round(a.score * 100)}% fit` : "Unmapped"}</Badge>
                </div>
                {a.page_url && <p className="mt-1 truncate text-xs text-slate-500">{a.page_url}</p>}
              </div>
            ))}
          </div>

          {keywordMap.unmapped_keywords.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Unmapped keywords</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {keywordMap.unmapped_keywords.map((k) => (
                  <Badge key={k} tone="warning">
                    {k}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {keywordMap.cannibalization.length > 0 && (
            <div className="mt-4 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Cannibalization flags</p>
              {keywordMap.cannibalization.map((flag) => (
                <div key={flag.keyword} className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-3">
                  <div className="flex items-center gap-2">
                    <Badge tone="danger" dot>
                      Conflict
                    </Badge>
                    <p className="text-sm font-medium text-slate-200">{flag.keyword}</p>
                  </div>
                  <p className="mt-1.5 text-xs text-slate-400">
                    Primary: <span className="text-slate-300">{truncate(flag.primary_page, 60)}</span> competing with{" "}
                    {flag.competing_pages.length} other page{flag.competing_pages.length === 1 ? "" : "s"}.
                  </p>
                  <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-slate-400">
                    {flag.suggested_actions.map((action) => (
                      <li key={action}>{action}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card
          title="Content Calendar"
          description={
            calendarIsMock
              ? "Demo data — build a calendar from your keyword research"
              : `${titleCase(calendar.cadence)} cadence from ${formatDate(calendar.start_date)}`
          }
          actions={
            <button type="button" onClick={handleBuildCalendar} disabled={calendarLoading} className="btn-secondary">
              {calendarLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CalendarDays className="h-4 w-4" />}
              Build Calendar
            </button>
          }
        >
          <div className="space-y-3">
            {calendar.entries.map((entry) => (
              <div key={`${entry.publish_date}-${entry.title}`} className="rounded-xl border border-surface-border bg-surface-raised/40 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Badge tone="brand">{formatDate(entry.publish_date)}</Badge>
                  {entry.cluster && <span className="text-xs text-slate-500">{entry.cluster}</span>}
                </div>
                <p className="mt-2 text-sm font-medium text-slate-200">{entry.title}</p>
                <p className="mt-1 text-xs text-slate-400">
                  Target: <span className="text-slate-300">{entry.outline.target_keyword}</span> · {titleCase(entry.outline.intent)} ·{" "}
                  {entry.outline.headings.length} sections
                </p>
                {entry.outline.supporting_keywords.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {entry.outline.supporting_keywords.map((k) => (
                      <Badge key={k} tone="neutral">
                        {k}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
