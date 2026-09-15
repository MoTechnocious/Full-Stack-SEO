"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CreditCard, Gauge, Loader2, ShieldAlert } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import Badge from "@/components/Badge";
import { ApiError, getUsage, type Usage, type UsageMetric } from "@/lib/api";
import { mockUsage } from "@/lib/mock";
import { clampPercent, cn, formatNumber, titleCase, TONE_CLASSES, type ScoreTone } from "@/lib/utils";

const MONTHLY_LABELS: Record<string, string> = {
  crawls_per_month: "Crawls",
  content_scores_per_month: "Content scores",
  keyword_lookups_per_month: "Keyword lookups",
  reports_per_month: "Reports",
};

const RESOURCE_LABELS: Record<string, string> = {
  sites: "Sites",
  tracked_keywords: "Tracked keywords",
};

function usageTone(pct: number): ScoreTone {
  if (pct >= 90) return "danger";
  if (pct >= 70) return "warning";
  return "good";
}

function Meter({ label, metric }: { label: string; metric: UsageMetric }) {
  const unlimited = metric.limit < 0;
  const pct = unlimited ? 0 : clampPercent(metric.limit === 0 ? 100 : (metric.used / metric.limit) * 100);
  const tone = unlimited ? "good" : usageTone(pct);

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-sm">
        <span className="text-slate-300">{label}</span>
        <span className={cn("font-medium tabular-nums", TONE_CLASSES[tone].text)}>
          {formatNumber(metric.used)} {unlimited ? "" : `/ ${formatNumber(metric.limit)}`}
          {unlimited && <span className="ml-1 text-slate-500">(unlimited)</span>}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-raised">
        <div
          className={cn("h-full rounded-full transition-all", TONE_CLASSES[tone].dot)}
          style={{ width: unlimited ? "100%" : `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function UsagePage() {
  const [usage, setUsage] = useState<Usage>(mockUsage);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getUsage()
      .then((result) => {
        if (!cancelled) {
          setUsage(result);
          setNotice(null);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setUsage(mockUsage);
        setNotice(
          err instanceof ApiError ? `${err.message} — showing demo data instead.` : "Could not reach the API — showing demo data instead.",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <PageHeader
        title="Usage"
        description="Monthly metering and resource limits for your current plan."
        actions={
          <Link href="/billing" className="btn-secondary">
            <CreditCard className="h-4 w-4" /> Manage plan
          </Link>
        }
      />

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading usage…
        </div>
      ) : (
        <>
          <div className="mb-4 flex items-center gap-2">
            <Gauge className="h-4 w-4 text-brand-300" />
            <span className="text-sm text-slate-400">
              Current plan: <Badge tone="brand">{titleCase(usage.plan_code)}</Badge>
            </span>
          </div>

          {notice && (
            <p className="mb-4 flex items-center gap-1.5 text-xs text-amber-400">
              <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
            </p>
          )}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card title="Monthly metrics" description="Resets at the start of each billing cycle.">
              <div className="space-y-5">
                {Object.entries(usage.monthly).map(([key, metric]) => (
                  <Meter key={key} label={MONTHLY_LABELS[key] ?? titleCase(key)} metric={metric} />
                ))}
              </div>
            </Card>

            <Card title="Resource usage" description="Live counts against your plan's absolute limits.">
              <div className="space-y-5">
                {Object.entries(usage.resources).map(([key, metric]) => (
                  <Meter key={key} label={RESOURCE_LABELS[key] ?? titleCase(key)} metric={metric} />
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
