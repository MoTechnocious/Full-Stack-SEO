"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { FileBarChart, Globe, Loader2, RefreshCw, ShieldAlert, TrendingUp, XCircle } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge, { type BadgeTone } from "@/components/Badge";
import {
  ApiError,
  cancelJob,
  listJobs,
  submitCrawlJob,
  submitRankPollJob,
  submitReportJob,
  type Job,
  type JobStatus,
  type JobType,
} from "@/lib/api";
import { DEMO_URL } from "@/lib/mock";
import { mockJobs } from "@/lib/mock-tracker";
import { cn, formatDate, formatNumber, titleCase, truncate } from "@/lib/utils";

const POLL_INTERVAL_MS = 4000;

const STATUS_OPTIONS: Array<{ value: "all" | JobStatus; label: string }> = [
  { value: "all", label: "All statuses" },
  { value: "queued", label: "Queued" },
  { value: "running", label: "Running" },
  { value: "succeeded", label: "Succeeded" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
];

function jobStatusTone(status: JobStatus): BadgeTone {
  switch (status) {
    case "running":
      return "info";
    case "succeeded":
      return "success";
    case "failed":
      return "danger";
    case "cancelled":
      return "warning";
    default:
      return "neutral";
  }
}

const JOB_TYPE_LABELS: Record<JobType, string> = {
  crawl: "Site Crawl",
  rank_poll: "Rank Poll",
  report: "Report Build",
};

/** Where the finished artifact lives in the app, per job type. */
const RESULT_LINKS: Record<JobType, { href: string; label: string }> = {
  crawl: { href: "/audit", label: "View in Site Audit" },
  rank_poll: { href: "/rankings", label: "View in Rankings" },
  report: { href: "/reports", label: "View in Reports" },
};

function isActive(job: Job): boolean {
  return job.status === "queued" || job.status === "running";
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>(mockJobs);
  const [jobsAreMock, setJobsAreMock] = useState(true);
  const [statusFilter, setStatusFilter] = useState<"all" | JobStatus>("all");
  const [notice, setNotice] = useState<string | null>(
    "Showing demo data — submit a job to fetch the live queue.",
  );

  const [crawlUrl, setCrawlUrl] = useState(DEMO_URL);
  const [crawlSubmitting, setCrawlSubmitting] = useState(false);
  const [rankDomain, setRankDomain] = useState("example-shop.com");
  const [rankKeywords, setRankKeywords] = useState("running shoes, trail running shoes");
  const [rankSubmitting, setRankSubmitting] = useState(false);
  const [reportSite, setReportSite] = useState(DEMO_URL);
  const [reportStart, setReportStart] = useState("2026-06-01");
  const [reportEnd, setReportEnd] = useState("2026-06-30");
  const [reportSubmitting, setReportSubmitting] = useState(false);

  const refresh = useCallback(async () => {
    const data = await listJobs();
    setJobs(data.items.length > 0 ? data.items : mockJobs);
    setJobsAreMock(data.items.length === 0);
  }, []);

  useEffect(() => {
    let cancelled = false;
    listJobs()
      .then((data) => {
        if (!cancelled && data.items.length > 0) {
          setJobs(data.items);
          setJobsAreMock(false);
          setNotice(null);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  // Poll the live queue every few seconds while any job is queued/running.
  useEffect(() => {
    if (jobsAreMock || !jobs.some(isActive)) return;
    const timer = setInterval(() => {
      refresh().catch(() => undefined);
    }, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [jobs, jobsAreMock, refresh]);

  function simulateLocalJob(type: JobType) {
    setJobs((prev) => [
      {
        id: `job_local_${prev.length + 1}`,
        org_id: "org_demo_0001",
        type,
        status: "queued",
        progress: 0,
        submitted_at: new Date().toISOString(),
        started_at: null,
        finished_at: null,
        result_ref: null,
        error: null,
        attempts: 0,
      },
      ...prev,
    ]);
  }

  async function afterSubmit(jobId: string, status: JobStatus) {
    setNotice(`Job ${jobId} submitted (${status}).`);
    try {
      await refresh();
    } catch {
      // keep whatever we have; the poller will retry
    }
  }

  function submitFailed(err: unknown, type: JobType) {
    simulateLocalJob(type);
    setNotice(
      err instanceof ApiError
        ? `${err.message} — job simulated on demo data instead.`
        : "Could not reach the API — job simulated on demo data instead.",
    );
  }

  async function handleSubmitCrawl(event: FormEvent) {
    event.preventDefault();
    if (!crawlUrl.trim()) return;
    setCrawlSubmitting(true);
    try {
      const res = await submitCrawlJob({ start_url: crawlUrl.trim() });
      await afterSubmit(res.job_id, res.status);
    } catch (err) {
      submitFailed(err, "crawl");
    } finally {
      setCrawlSubmitting(false);
    }
  }

  async function handleSubmitRankPoll(event: FormEvent) {
    event.preventDefault();
    const keywords = rankKeywords
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean);
    if (!rankDomain.trim() || keywords.length === 0) return;
    setRankSubmitting(true);
    try {
      const res = await submitRankPollJob({ domain: rankDomain.trim(), keywords });
      await afterSubmit(res.job_id, res.status);
    } catch (err) {
      submitFailed(err, "rank_poll");
    } finally {
      setRankSubmitting(false);
    }
  }

  async function handleSubmitReport(event: FormEvent) {
    event.preventDefault();
    if (!reportSite.trim() || !reportStart || !reportEnd) return;
    setReportSubmitting(true);
    try {
      const res = await submitReportJob({
        site: reportSite.trim(),
        period_start: reportStart,
        period_end: reportEnd,
      });
      await afterSubmit(res.job_id, res.status);
    } catch (err) {
      submitFailed(err, "report");
    } finally {
      setReportSubmitting(false);
    }
  }

  async function handleCancel(jobId: string) {
    try {
      const updated = await cancelJob(jobId);
      setJobs((prev) => prev.map((j) => (j.id === jobId ? updated : j)));
    } catch {
      setJobs((prev) =>
        prev.map((j) =>
          j.id === jobId && j.status === "queued" ? { ...j, status: "cancelled" as JobStatus } : j,
        ),
      );
      setNotice("Could not reach the API — cancellation simulated on demo data.");
    }
  }

  const sorted = [...jobs].sort((a, b) => b.submitted_at.localeCompare(a.submitted_at));
  const filtered = statusFilter === "all" ? sorted : sorted.filter((j) => j.status === statusFilter);
  const activeCount = jobs.filter(isActive).length;
  const succeededCount = jobs.filter((j) => j.status === "succeeded").length;
  const failedCount = jobs.filter((j) => j.status === "failed").length;

  const columns: Array<DataTableColumn<Job>> = [
    {
      key: "type",
      header: "Job",
      render: (job) => (
        <div>
          <p className="font-medium text-slate-200">{JOB_TYPE_LABELS[job.type]}</p>
          <p className="mt-0.5 text-xs text-slate-500">{job.id}</p>
          {job.error && <p className="mt-0.5 text-xs text-rose-400">{truncate(job.error, 64)}</p>}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (job) => (
        <Badge tone={jobStatusTone(job.status)} dot>
          {titleCase(job.status)}
        </Badge>
      ),
    },
    {
      key: "progress",
      header: "Progress",
      render: (job) => (
        <div className="w-32">
          <div className="h-1.5 overflow-hidden rounded-full bg-surface-raised">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                job.status === "failed" ? "bg-rose-400" : job.status === "succeeded" ? "bg-emerald-400" : "bg-brand-400",
              )}
              style={{ width: `${job.progress}%` }}
            />
          </div>
          <p className="mt-1 text-xs tabular-nums text-slate-500">{job.progress}%</p>
        </div>
      ),
    },
    {
      key: "submitted",
      header: "Submitted",
      render: (job) => (
        <span className="text-slate-400">
          {formatDate(job.submitted_at, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
        </span>
      ),
    },
    {
      key: "finished",
      header: "Finished",
      render: (job) =>
        job.finished_at ? (
          <span className="text-slate-400">
            {formatDate(job.finished_at, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
          </span>
        ) : (
          <span className="text-slate-600">—</span>
        ),
    },
    {
      key: "result",
      header: "Result",
      render: (job) => {
        if (job.status === "succeeded") {
          const link = RESULT_LINKS[job.type];
          return (
            <div>
              <Link href={link.href} className="text-xs font-medium text-brand-300 transition hover:text-brand-200">
                {link.label}
              </Link>
              {job.result_ref && <p className="mt-0.5 text-xs text-slate-600">{truncate(job.result_ref, 28)}</p>}
            </div>
          );
        }
        if (job.status === "queued") {
          return (
            <button
              type="button"
              onClick={() => handleCancel(job.id)}
              className="inline-flex items-center gap-1 text-xs font-medium text-rose-400 transition hover:text-rose-300"
            >
              <XCircle className="h-3.5 w-3.5" /> Cancel
            </button>
          );
        }
        return <span className="text-slate-600">—</span>;
      },
    },
  ];

  return (
    <div>
      <PageHeader
        title="Jobs"
        description="Background job queue for long-running work: site crawls, rank polls and report builds. Quotas are enforced at submission; results land in their usual pages."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Site Crawl" description="Crawl a site in the background (crawls_per_month quota)">
          <form onSubmit={handleSubmitCrawl} className="flex flex-col gap-3">
            <div>
              <label htmlFor="job-crawl-url" className="label-base">
                Start URL
              </label>
              <input
                id="job-crawl-url"
                type="text"
                value={crawlUrl}
                onChange={(e) => setCrawlUrl(e.target.value)}
                className="input-base"
                autoComplete="off"
              />
            </div>
            <button type="submit" disabled={crawlSubmitting} className="btn-primary self-start">
              {crawlSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Globe className="h-4 w-4" />}
              Queue Crawl
            </button>
          </form>
        </Card>

        <Card title="Rank Poll" description="Refresh rank tracking for a domain's keywords">
          <form onSubmit={handleSubmitRankPoll} className="flex flex-col gap-3">
            <div>
              <label htmlFor="job-rank-domain" className="label-base">
                Domain
              </label>
              <input
                id="job-rank-domain"
                type="text"
                value={rankDomain}
                onChange={(e) => setRankDomain(e.target.value)}
                className="input-base"
                autoComplete="off"
              />
            </div>
            <div>
              <label htmlFor="job-rank-keywords" className="label-base">
                Keywords (comma-separated)
              </label>
              <input
                id="job-rank-keywords"
                type="text"
                value={rankKeywords}
                onChange={(e) => setRankKeywords(e.target.value)}
                className="input-base"
                autoComplete="off"
              />
            </div>
            <button type="submit" disabled={rankSubmitting} className="btn-primary self-start">
              {rankSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <TrendingUp className="h-4 w-4" />}
              Queue Rank Poll
            </button>
          </form>
        </Card>

        <Card title="Report Build" description="Build a white-label report for a period">
          <form onSubmit={handleSubmitReport} className="flex flex-col gap-3">
            <div>
              <label htmlFor="job-report-site" className="label-base">
                Site
              </label>
              <input
                id="job-report-site"
                type="text"
                value={reportSite}
                onChange={(e) => setReportSite(e.target.value)}
                className="input-base"
                autoComplete="off"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="job-report-start" className="label-base">
                  Period start
                </label>
                <input
                  id="job-report-start"
                  type="date"
                  value={reportStart}
                  onChange={(e) => setReportStart(e.target.value)}
                  className="input-base"
                />
              </div>
              <div>
                <label htmlFor="job-report-end" className="label-base">
                  Period end
                </label>
                <input
                  id="job-report-end"
                  type="date"
                  value={reportEnd}
                  onChange={(e) => setReportEnd(e.target.value)}
                  className="input-base"
                />
              </div>
            </div>
            <button type="submit" disabled={reportSubmitting} className="btn-primary self-start">
              {reportSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileBarChart className="h-4 w-4" />}
              Queue Report
            </button>
          </form>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Total Jobs" value={formatNumber(jobs.length)} />
        <KpiCard label="Active" value={formatNumber(activeCount)} />
        <KpiCard label="Succeeded" value={formatNumber(succeededCount)} />
        <KpiCard label="Failed" value={formatNumber(failedCount)} />
      </div>

      <Card
        className="mt-6"
        title="Job Queue"
        description={
          jobsAreMock
            ? "Demo data — API unavailable or queue empty"
            : activeCount > 0
              ? `Auto-refreshing every ${POLL_INTERVAL_MS / 1000}s while ${activeCount} job${activeCount === 1 ? " is" : "s are"} active`
            : "Live queue for this organization"
        }
        padded={false}
        actions={
          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as "all" | JobStatus)}
              className="input-base w-40"
              aria-label="Filter by status"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => {
                refresh().catch(() => setNotice("Could not reach the API — showing current data."));
              }}
              className="btn-secondary"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
        }
      >
        {notice && (
          <p className="flex items-center gap-1.5 border-b border-surface-border px-5 py-3 text-xs text-amber-400">
            <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
          </p>
        )}
        <DataTable
          columns={columns}
          data={filtered}
          getRowKey={(job) => job.id}
          emptyMessage="No jobs match this filter — submit a crawl, rank poll or report above."
        />
      </Card>
    </div>
  );
}
