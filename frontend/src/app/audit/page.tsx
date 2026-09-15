"use client";

import { useState, type FormEvent } from "react";
import { AlertTriangle, CheckCircle2, Globe, Loader2, Search, ShieldAlert } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import ScoreGauge from "@/components/ScoreGauge";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge, { indexabilityTone, scoreBadgeTone, severityTone, statusCodeTone } from "@/components/Badge";
import { ApiError, auditPage, runCrawl, type CrawlResult, type PageAuditResult } from "@/lib/api";
import { DEMO_URL, mockCrawlResult, mockPageAuditResult } from "@/lib/mock";
import { formatNumber, titleCase } from "@/lib/utils";

export default function AuditPage() {
  const [url, setUrl] = useState(DEMO_URL);

  const [crawl, setCrawl] = useState<CrawlResult>(mockCrawlResult);
  const [crawlLoading, setCrawlLoading] = useState(false);
  const [crawlIsMock, setCrawlIsMock] = useState(true);
  const [crawlNotice, setCrawlNotice] = useState<string | null>("Showing demo data — run a crawl to fetch live results.");

  const [quickResult, setQuickResult] = useState<PageAuditResult | null>(null);
  const [quickLoading, setQuickLoading] = useState(false);
  const [quickIsMock, setQuickIsMock] = useState(false);

  async function handleRunCrawl(event: FormEvent) {
    event.preventDefault();
    if (!url.trim()) return;
    setCrawlLoading(true);
    try {
      const result = await runCrawl({ start_url: url.trim() });
      setCrawl(result);
      setCrawlIsMock(false);
      setCrawlNotice(null);
    } catch (err) {
      setCrawl(mockCrawlResult);
      setCrawlIsMock(true);
      setCrawlNotice(
        err instanceof ApiError
          ? `${err.message} — showing demo data instead.`
          : "Could not reach the API — showing demo data instead.",
      );
    } finally {
      setCrawlLoading(false);
    }
  }

  async function handleQuickCheck() {
    if (!url.trim()) return;
    setQuickLoading(true);
    try {
      const result = await auditPage({ url: url.trim() });
      setQuickResult(result);
      setQuickIsMock(false);
    } catch {
      setQuickResult(mockPageAuditResult);
      setQuickIsMock(true);
    } finally {
      setQuickLoading(false);
    }
  }

  const columns: Array<DataTableColumn<PageAuditResult>> = [
    {
      key: "url",
      header: "URL",
      render: (page) => (
        <span className="block max-w-xs truncate text-slate-200" title={page.url}>
          {page.url.replace(crawl.start_url, "") || "/"}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (page) => <Badge tone={statusCodeTone(page.status_code)}>{page.status_code || "—"}</Badge>,
    },
    {
      key: "title",
      header: "Title",
      render: (page) =>
        page.title ? (
          <span className="block max-w-xs truncate text-slate-300">{page.title}</span>
        ) : (
          <span className="italic text-rose-400">Missing</span>
        ),
    },
    {
      key: "indexability",
      header: "Index",
      render: (page) => (
        <Badge tone={indexabilityTone(page.indexability)}>{page.indexability === "indexable" ? "Indexable" : "Blocked"}</Badge>
      ),
    },
    { key: "words", header: "Words", render: (page) => formatNumber(page.word_count) },
    {
      key: "score",
      header: "Score",
      render: (page) => <Badge tone={scoreBadgeTone(page.score)}>{page.score}</Badge>,
    },
    {
      key: "issues",
      header: "Issues",
      render: (page) =>
        page.issues.length > 0 ? <Badge tone="warning">{page.issues.length}</Badge> : <Badge tone="success">0</Badge>,
    },
  ];

  return (
    <div>
      <PageHeader
        title="Site Audit"
        description="Crawl a site to surface technical SEO issues, or run an instant check on a single page."
      />

      <Card>
        <form onSubmit={handleRunCrawl} className="flex flex-col gap-3 sm:flex-row">
          <div className="flex-1">
            <label htmlFor="audit-url" className="label-base">
              Start URL
            </label>
            <input
              id="audit-url"
              type="text"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://example.com"
              className="input-base"
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <div className="flex gap-2 sm:items-end sm:pb-0">
            <button type="submit" disabled={crawlLoading} className="btn-primary h-[42px] sm:mt-6">
              {crawlLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Globe className="h-4 w-4" />}
              Run Full Crawl
            </button>
            <button
              type="button"
              onClick={handleQuickCheck}
              disabled={quickLoading}
              className="btn-secondary h-[42px] sm:mt-6"
            >
              {quickLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Quick Page Check
            </button>
          </div>
        </form>
        {crawlNotice && (
          <p className="mt-3 flex items-center gap-1.5 text-xs text-amber-400">
            <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {crawlNotice}
          </p>
        )}
      </Card>

      {quickResult && (
        <Card
          className="mt-4"
          title="Quick page check"
          description={quickIsMock ? "Demo result — API unavailable" : "Live result"}
        >
          <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
            <ScoreGauge score={quickResult.score} label="Page Score" />
            <div className="min-w-0 flex-1 space-y-2 text-sm">
              <p className="truncate font-medium text-slate-100">{quickResult.title ?? "Missing title"}</p>
              <p className="truncate text-slate-400">{quickResult.url}</p>
              <div className="flex flex-wrap gap-2 pt-1">
                <Badge tone={statusCodeTone(quickResult.status_code)}>{quickResult.status_code}</Badge>
                <Badge tone={indexabilityTone(quickResult.indexability)}>
                  {quickResult.indexability === "indexable" ? "Indexable" : "Blocked"}
                </Badge>
                <Badge tone="neutral">{formatNumber(quickResult.word_count)} words</Badge>
                <Badge tone="neutral">{quickResult.response_time_ms} ms</Badge>
              </div>
              {quickResult.issues.length > 0 && (
                <ul className="space-y-1 pt-2">
                  {quickResult.issues.map((issue) => (
                    <li key={issue.code} className="flex items-center gap-2 text-xs text-slate-400">
                      <AlertTriangle className="h-3 w-3 shrink-0 text-amber-400" /> {issue.title}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </Card>
      )}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Pages Crawled" value={formatNumber(crawl.summary.total_pages)} />
        <KpiCard label="Average Score" value={`${crawl.summary.avg_score}`} />
        <KpiCard label="Indexable Pages" value={formatNumber(crawl.summary.indexable_pages)} />
        <KpiCard label="Broken Links" value={formatNumber(crawl.summary.broken_links_total)} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Top Issues" description={`${crawl.summary.pages_with_issues} of ${crawl.summary.total_pages} pages affected`} className="lg:col-span-1">
          {crawl.top_issues.length === 0 ? (
            <p className="flex items-center gap-2 text-sm text-emerald-400">
              <CheckCircle2 className="h-4 w-4" /> No issues found.
            </p>
          ) : (
            <ul className="space-y-3">
              {crawl.top_issues.map((issue) => (
                <li key={issue.code} className="flex items-start gap-2">
                  <Badge tone={severityTone(issue.severity)} className="mt-0.5 shrink-0">
                    {titleCase(issue.severity)}
                  </Badge>
                  <span className="text-sm text-slate-300">{issue.title}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Crawled Pages" className="lg:col-span-2" padded={false}>
          <DataTable columns={columns} data={crawl.pages} getRowKey={(page) => page.url} emptyMessage="Run a crawl to see pages here." />
        </Card>
      </div>
    </div>
  );
}
