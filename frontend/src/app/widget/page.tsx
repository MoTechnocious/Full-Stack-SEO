"use client";

import { useMemo, useState } from "react";
import { Check, Code2, Copy, Mail, Radar, Users } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import { useAuth } from "@/lib/auth";
import { widgetEmbedSnippet, widgetScriptUrl } from "@/lib/api";

const STEPS: Array<{ icon: typeof Radar; title: string; text: string }> = [
  {
    icon: Code2,
    title: "1 · Embed the snippet",
    text: "Paste the script tag anywhere on your agency site — landing pages, blog sidebars, or your pricing page. It renders a compact “Free SEO Audit” form styled to blend into any theme.",
  },
  {
    icon: Radar,
    title: "2 · Visitors run a free audit",
    text: "A visitor enters their website and email. The widget calls the public audit endpoint and instantly shows a teaser: health score, top issues found, and what a full audit covers.",
  },
  {
    icon: Mail,
    title: "3 · You capture the lead",
    text: "Every submission is validated, stored against your organization, and pushed through the lead pipeline (CRM + optional Make.com scenario) with delivery-state logging — the same flow as the Integrations page.",
  },
];

export default function WidgetPage() {
  const { orgName } = useAuth();
  const suggestedSlug = (orgName ?? "").toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  const [slug, setSlug] = useState<string>("");
  const [copied, setCopied] = useState(false);

  const effectiveSlug = slug.trim() || suggestedSlug || "your-org-slug";
  const snippet = useMemo(() => widgetEmbedSnippet(effectiveSlug), [effectiveSlug]);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <div>
      <PageHeader
        title="Lead-Gen Audit Widget"
        description="Embed a free automated SEO audit on your website and turn visitors into captured, CRM-ready leads."
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Your Embed Code" description="One script tag — no build step, no dependencies, async by default.">
          <div className="space-y-3">
            <div>
              <label htmlFor="widget-org" className="label-base">
                Organization slug
              </label>
              <input
                id="widget-org"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                className="input-base"
                placeholder={suggestedSlug || "your-org-slug"}
              />
              <p className="mt-1 text-[11px] text-slate-500">
                Leads submitted through the widget are attributed to this workspace.
              </p>
            </div>

            <div className="relative">
              <pre className="overflow-x-auto rounded-xl border border-surface-border bg-black/40 p-4 text-xs leading-relaxed text-emerald-200 scrollbar-thin">
                {snippet}
              </pre>
              <button
                type="button"
                onClick={handleCopy}
                className="btn-secondary absolute right-2 top-2"
                aria-label="Copy embed snippet"
              >
                {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>

            <p className="text-xs text-slate-500">
              Script URL: <span className="break-all text-slate-400">{widgetScriptUrl(effectiveSlug)}</span>
            </p>
          </div>
        </Card>

        <Card title="How It Works" description="From anonymous visitor to qualified lead in three steps.">
          <ul className="space-y-4">
            {STEPS.map((step) => {
              const Icon = step.icon;
              return (
                <li key={step.title} className="flex gap-3">
                  <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-500/15 text-brand-300">
                    <Icon className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="text-sm font-medium text-slate-200">{step.title}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-slate-400">{step.text}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      </div>

      <div className="mt-6">
        <Card
          title="Where Captured Leads Go"
          description="Widget submissions flow through the same validated lead pipeline as API-submitted leads."
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex items-center gap-2 text-sm text-slate-300">
              <Users className="h-4 w-4 text-brand-300" />
              Review deliveries, retries, and webhook state on the{" "}
              <a href="/integrations" className="text-brand-300 underline-offset-2 hover:underline">
                Integrations page
              </a>
              .
            </div>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Each lead is validated (email format, URL reachability rules, spam heuristics) before it is pushed to your CRM
            provider, and every push records a delivery state you can audit. Configure CRM &amp; Make.com credentials via
            environment settings — no keys are ever hardcoded.
          </p>
        </Card>
      </div>
    </div>
  );
}
