"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, CheckCircle2, Globe, Loader2, Sparkles } from "lucide-react";
import Card from "@/components/Card";
import Badge from "@/components/Badge";
import { useAuth } from "@/lib/auth";
import { listPlans, type Plan } from "@/lib/api";
import { mockPlans } from "@/lib/mock";
import { formatNumber, titleCase } from "@/lib/utils";

const PRIMARY_DOMAIN_STORAGE_KEY = "myseoapp.onboarding.primaryDomain";

export default function OnboardingPage() {
  const router = useRouter();
  const { orgName, planCode } = useAuth();

  const [domain, setDomain] = useState("");
  const [saving, setSaving] = useState(false);
  const [plans, setPlans] = useState<Plan[]>(mockPlans);

  useEffect(() => {
    let cancelled = false;
    listPlans()
      .then((result) => {
        if (!cancelled) setPlans(result);
      })
      .catch(() => {
        // Offline: keep the bundled mock plan catalog.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const currentPlan = plans.find((plan) => plan.code === planCode) ?? null;

  function finish(event?: FormEvent) {
    event?.preventDefault();
    setSaving(true);
    if (typeof window !== "undefined") {
      // No `/projects` API yet — this is stored locally as a convenience
      // default; the SEO tool pages still accept any URL you type in.
      if (domain.trim()) {
        window.localStorage.setItem(PRIMARY_DOMAIN_STORAGE_KEY, domain.trim());
      } else {
        window.localStorage.removeItem(PRIMARY_DOMAIN_STORAGE_KEY);
      }
    }
    router.push("/");
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg">
        <div className="mb-6 flex flex-col items-center gap-3 text-center">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-400 text-white shadow-glow">
            <Sparkles className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-lg font-semibold text-slate-50">Welcome to MySEOapp{orgName ? `, ${orgName}` : ""}!</h1>
            <p className="mt-1 text-sm text-slate-400">Let&apos;s get your workspace ready in two quick steps.</p>
          </div>
        </div>

        <Card
          className="mb-4"
          title="Your plan"
          description="You can change this any time from Billing."
          actions={<Badge tone="brand">{titleCase(planCode ?? "free")}</Badge>}
        >
          {currentPlan ? (
            <div className="space-y-3">
              <div className="flex items-baseline gap-1.5">
                <span className="text-2xl font-bold text-slate-50">
                  {currentPlan.price_monthly > 0 ? `$${currentPlan.price_monthly}` : "Free"}
                </span>
                {currentPlan.price_monthly > 0 && <span className="text-xs text-slate-500">/ month</span>}
              </div>
              <p className="text-sm text-slate-400">{currentPlan.description}</p>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 sm:grid-cols-3">
                <p>
                  <span className="font-semibold text-slate-200">{formatNumber(currentPlan.limits.sites)}</span> sites
                </p>
                <p>
                  <span className="font-semibold text-slate-200">{formatNumber(currentPlan.limits.tracked_keywords)}</span>{" "}
                  keywords
                </p>
                <p>
                  <span className="font-semibold text-slate-200">{formatNumber(currentPlan.limits.seats)}</span> seats
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Plan details unavailable right now — you&apos;re all set regardless.</p>
          )}
        </Card>

        <Card title="Your first site" description="Optional — add the domain you'll be optimizing.">
          <form onSubmit={finish} className="space-y-4">
            <div>
              <label htmlFor="onboarding-domain" className="label-base">
                Domain
              </label>
              <div className="relative">
                <Globe className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  id="onboarding-domain"
                  type="text"
                  value={domain}
                  onChange={(event) => setDomain(event.target.value)}
                  placeholder="www.example.com"
                  className="input-base pl-9"
                  autoComplete="off"
                  spellCheck={false}
                />
              </div>
            </div>

            <div className="flex flex-col gap-2 sm:flex-row">
              <button type="submit" disabled={saving} className="btn-primary flex-1">
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                Finish setup
              </button>
              <button type="button" onClick={() => finish()} disabled={saving} className="btn-secondary flex-1">
                Skip for now <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
