"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { Loader2, Lock, Palette, ShieldAlert, Sparkles } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import { ApiError, buildReport, getSubscription, type Report, type WhiteLabelBranding } from "@/lib/api";
import { DEMO_URL, mockBranding, mockReport, mockSubscription } from "@/lib/mock";
import { cn, formatDate, titleCase } from "@/lib/utils";

export default function ReportsPage() {
  const [site, setSite] = useState(DEMO_URL);
  const [periodStart, setPeriodStart] = useState(mockReport.period_start);
  const [periodEnd, setPeriodEnd] = useState(mockReport.period_end);
  const [branding, setBranding] = useState<WhiteLabelBranding>(mockBranding);
  const [report, setReport] = useState<Report>(mockReport);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>("Showing demo data — generate a report to fetch live results.");

  // Feature gate: white-label branding is a plan feature (see backend
  // billing/plans.py). Default to the bundled mock subscription's features
  // while offline/loading, then confirm against the live subscription.
  const [hasWhiteLabel, setHasWhiteLabel] = useState(mockSubscription.plan.features.includes("white_label"));

  useEffect(() => {
    let cancelled = false;
    getSubscription()
      .then((sub) => {
        if (!cancelled) setHasWhiteLabel(sub.plan.features.includes("white_label"));
      })
      .catch(() => {
        // Offline: keep the default derived from the bundled mock subscription.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleGenerate(event: FormEvent) {
    event.preventDefault();
    if (!site.trim()) return;
    setLoading(true);
    try {
      const result = await buildReport({
        site: site.trim(),
        period_start: periodStart,
        period_end: periodEnd,
        branding: hasWhiteLabel ? branding : undefined,
      });
      setReport(result);
      setBranding(result.branding);
      setNotice(null);
    } catch (err) {
      setReport({ ...mockReport, site: site.trim(), period_start: periodStart, period_end: periodEnd, branding });
      setNotice(
        err instanceof ApiError ? `${err.message} — showing demo data instead.` : "Could not reach the API — showing demo data instead.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader title="Reports" description="Generate a white-label client report using your own agency branding." />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        <Card className="xl:col-span-2">
          <form onSubmit={handleGenerate} className="space-y-4">
            <div>
              <label htmlFor="report-site" className="label-base">
                Site
              </label>
              <input id="report-site" type="text" value={site} onChange={(event) => setSite(event.target.value)} className="input-base" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="report-start" className="label-base">
                  Period start
                </label>
                <input
                  id="report-start"
                  type="date"
                  value={periodStart}
                  onChange={(event) => setPeriodStart(event.target.value)}
                  className="input-base"
                />
              </div>
              <div>
                <label htmlFor="report-end" className="label-base">
                  Period end
                </label>
                <input id="report-end" type="date" value={periodEnd} onChange={(event) => setPeriodEnd(event.target.value)} className="input-base" />
              </div>
            </div>

            <div className="flex items-center justify-between gap-1.5 border-t border-surface-border pt-4">
              <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <Palette className="h-3.5 w-3.5" /> Branding
              </div>
              {!hasWhiteLabel && (
                <Link
                  href="/billing"
                  className="flex items-center gap-1 text-[11px] font-medium text-amber-400 transition hover:text-amber-300"
                >
                  <Lock className="h-3 w-3" /> Agency plan feature
                </Link>
              )}
            </div>

            {!hasWhiteLabel && (
              <p className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-300">
                White-label branding is available on the Agency and Enterprise plans.{" "}
                <Link href="/billing" className="font-medium underline underline-offset-2">
                  Upgrade your plan
                </Link>{" "}
                to customize colors, agency name and footer text.
              </p>
            )}

            <fieldset disabled={!hasWhiteLabel} className={cn("space-y-4", !hasWhiteLabel && "opacity-50")}>
              <div>
                <label htmlFor="brand-agency" className="label-base">
                  Agency name
                </label>
                <input
                  id="brand-agency"
                  type="text"
                  value={branding.agency_name}
                  onChange={(event) => setBranding((prev) => ({ ...prev, agency_name: event.target.value }))}
                  className="input-base"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="brand-primary" className="label-base">
                    Primary color
                  </label>
                  <input
                    id="brand-primary"
                    type="color"
                    value={branding.primary_color}
                    onChange={(event) => setBranding((prev) => ({ ...prev, primary_color: event.target.value }))}
                    className="h-[42px] w-full cursor-pointer rounded-lg border border-surface-border bg-surface-raised p-1"
                  />
                </div>
                <div>
                  <label htmlFor="brand-accent" className="label-base">
                    Accent color
                  </label>
                  <input
                    id="brand-accent"
                    type="color"
                    value={branding.accent_color}
                    onChange={(event) => setBranding((prev) => ({ ...prev, accent_color: event.target.value }))}
                    className="h-[42px] w-full cursor-pointer rounded-lg border border-surface-border bg-surface-raised p-1"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="brand-agent" className="label-base">
                  AI agent name
                </label>
                <input
                  id="brand-agent"
                  type="text"
                  value={branding.agent_name}
                  onChange={(event) => setBranding((prev) => ({ ...prev, agent_name: event.target.value }))}
                  className="input-base"
                />
              </div>

              <div>
                <label htmlFor="brand-email" className="label-base">
                  Contact email
                </label>
                <input
                  id="brand-email"
                  type="email"
                  value={branding.contact_email ?? ""}
                  onChange={(event) => setBranding((prev) => ({ ...prev, contact_email: event.target.value }))}
                  className="input-base"
                />
              </div>

              <div>
                <label htmlFor="brand-footer" className="label-base">
                  Footer text
                </label>
                <input
                  id="brand-footer"
                  type="text"
                  value={branding.footer_text}
                  onChange={(event) => setBranding((prev) => ({ ...prev, footer_text: event.target.value }))}
                  className="input-base"
                />
              </div>
            </fieldset>

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              Generate Report
            </button>
            {notice && (
              <p className="flex items-center gap-1.5 text-xs text-amber-400">
                <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
              </p>
            )}
          </form>
        </Card>

        <Card className="xl:col-span-3" title="Live Preview" description="How this report will look to your client" padded={false}>
          <div className="overflow-hidden rounded-b-2xl">
            <div className="flex items-center justify-between px-5 py-4" style={{ backgroundColor: report.branding.primary_color }}>
              <div>
                <p className="text-sm font-semibold text-white">{report.branding.agency_name}</p>
                <p className="text-xs text-white/70">SEO Performance Report for {report.site.replace("https://", "")}</p>
              </div>
              <span className="rounded-full bg-white/15 px-3 py-1 text-xs font-medium text-white">
                {formatDate(report.period_start)} – {formatDate(report.period_end)}
              </span>
            </div>

            <div className="space-y-4 bg-surface-raised p-5">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {Object.entries(report.headline_metrics).map(([key, value]) => (
                  <div key={key} className="rounded-lg border border-surface-border bg-surface-card p-3">
                    <p className="text-[10px] uppercase tracking-wide text-slate-500">{titleCase(key)}</p>
                    <p className="mt-1 text-lg font-bold" style={{ color: report.branding.accent_color }}>
                      {String(value)}
                    </p>
                  </div>
                ))}
              </div>

              <div className="space-y-3">
                {report.sections.map((section) => (
                  <div key={section.title} className="rounded-lg border border-surface-border bg-surface-card p-3">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-slate-100">{section.title}</p>
                      <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate-500">
                        {section.type}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">{section.summary}</p>
                  </div>
                ))}
              </div>

              {report.branding.footer_text && (
                <p className="border-t border-surface-border pt-3 text-center text-[11px] text-slate-500">{report.branding.footer_text}</p>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
