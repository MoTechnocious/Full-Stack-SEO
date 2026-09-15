"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Check, CreditCard, Gauge, Loader2, Lock, ShieldAlert, Sparkles } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import Badge from "@/components/Badge";
import { useAuth } from "@/lib/auth";
import { ApiError, createBillingPortal, createCheckout, getSubscription, listPlans, type Plan, type Subscription } from "@/lib/api";
import { mockPlans, mockSubscription } from "@/lib/mock";
import { formatDate, formatNumber, titleCase } from "@/lib/utils";

const FEATURE_LABELS: Record<string, string> = {
  white_label: "White-label reports",
  api_access: "API access",
  mcp_access: "MCP server access",
  content_ai: "AI content scoring",
  competitor_analysis: "Competitor analysis",
  scheduled_crawls: "Scheduled crawls",
  priority_support: "Priority support",
};

function featureLabel(feature: string): string {
  return FEATURE_LABELS[feature] ?? titleCase(feature);
}

export default function BillingPage() {
  const { canManageBilling, refreshMe } = useAuth();

  const [plans, setPlans] = useState<Plan[]>(mockPlans);
  const [subscription, setSubscription] = useState<Subscription>(mockSubscription);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [pendingPlan, setPendingPlan] = useState<string | null>(null);
  const [portalPending, setPortalPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([listPlans(), getSubscription()]).then(([plansResult, subResult]) => {
      if (cancelled) return;
      if (plansResult.status === "fulfilled") setPlans(plansResult.value);
      if (subResult.status === "fulfilled") setSubscription(subResult.value);
      if (plansResult.status === "rejected" || subResult.status === "rejected") {
        const err = plansResult.status === "rejected" ? plansResult.reason : subResult.status === "rejected" ? subResult.reason : null;
        setNotice(err instanceof ApiError ? `${err.message} — showing demo data instead.` : "Could not reach the API — showing demo data instead.");
      } else {
        setNotice(null);
      }
      setLoading(false);
      void refreshMe().catch(() => undefined);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleUpgrade(planCode: string) {
    if (!canManageBilling || typeof window === "undefined") return;
    setPendingPlan(planCode);
    setCheckoutError(null);
    try {
      const origin = window.location.origin;
      const result = await createCheckout({
        plan_code: planCode,
        success_url: `${origin}/billing/success?plan=${encodeURIComponent(planCode)}`,
        cancel_url: `${origin}/billing`,
      });
      window.location.href = result.checkout_url;
    } catch (err) {
      setCheckoutError(err instanceof ApiError ? err.message : "Could not start checkout — API unreachable.");
      setPendingPlan(null);
    }
  }

  async function handlePortal() {
    if (!canManageBilling) return;
    setPortalPending(true);
    setCheckoutError(null);
    try {
      const result = await createBillingPortal();
      window.location.href = result.portal_url;
    } catch (err) {
      setCheckoutError(err instanceof ApiError ? err.message : "Could not open the billing portal — API unreachable.");
    } finally {
      setPortalPending(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Billing"
        description="Manage your subscription, compare plans, and see what each tier unlocks."
        actions={
          <Link href="/usage" className="btn-secondary">
            <Gauge className="h-4 w-4" /> View usage
          </Link>
        }
      />

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading billing details…
        </div>
      ) : (
        <>
          <Card className="mb-6" title="Current plan" description="Your organization's active subscription.">
            <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-500/10 text-brand-300">
                  <CreditCard className="h-5 w-5" />
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-base font-semibold text-slate-100">{subscription.plan.name}</p>
                    <Badge tone={subscription.status === "active" ? "success" : "warning"}>{titleCase(subscription.status)}</Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {subscription.plan.price_monthly > 0 ? `$${subscription.plan.price_monthly}/month` : "No cost"}
                    {subscription.current_period_end ? ` · renews ${formatDate(subscription.current_period_end)}` : ""} ·{" "}
                    {formatNumber(subscription.seats)} seat{subscription.seats === 1 ? "" : "s"}
                  </p>
                </div>
              </div>
              {canManageBilling ? (
                <button type="button" onClick={handlePortal} disabled={portalPending} className="btn-secondary">
                  {portalPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CreditCard className="h-4 w-4" />}
                  Manage billing
                </button>
              ) : (
                <p className="flex items-center gap-1.5 text-xs text-slate-500">
                  <Lock className="h-3.5 w-3.5" /> Only the owner can manage billing.
                </p>
              )}
            </div>
            {checkoutError && (
              <p className="mt-4 flex items-start gap-1.5 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
                <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {checkoutError}
              </p>
            )}
          </Card>

          {notice && (
            <p className="mb-4 flex items-center gap-1.5 text-xs text-amber-400">
              <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
            </p>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
            {plans.map((plan) => {
              const isCurrent = plan.code === subscription.plan_code;
              return (
                <Card
                  key={plan.code}
                  className={isCurrent ? "ring-1 ring-brand-500/50" : undefined}
                  padded={false}
                >
                  <div className="flex h-full flex-col p-5">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-slate-100">{plan.name}</p>
                      {isCurrent && <Badge tone="brand">Current</Badge>}
                    </div>
                    <p className="mt-2 flex items-baseline gap-1">
                      <span className="text-2xl font-bold text-slate-50">
                        {plan.is_custom ? "Custom" : plan.price_monthly > 0 ? `$${plan.price_monthly}` : "Free"}
                      </span>
                      {!plan.is_custom && plan.price_monthly > 0 && <span className="text-xs text-slate-500">/mo</span>}
                    </p>
                    <p className="mt-2 text-xs text-slate-400">{plan.description}</p>

                    <ul className="mt-4 space-y-1.5 text-xs text-slate-400">
                      <li>{plan.limits.sites < 0 ? "Unlimited" : formatNumber(plan.limits.sites)} sites</li>
                      <li>{plan.limits.tracked_keywords < 0 ? "Unlimited" : formatNumber(plan.limits.tracked_keywords)} tracked keywords</li>
                      <li>{plan.limits.crawls_per_month < 0 ? "Unlimited" : formatNumber(plan.limits.crawls_per_month)} crawls/mo</li>
                      <li>{plan.limits.reports_per_month < 0 ? "Unlimited" : formatNumber(plan.limits.reports_per_month)} reports/mo</li>
                      <li>{plan.limits.seats < 0 ? "Unlimited" : formatNumber(plan.limits.seats)} seats</li>
                    </ul>

                    {plan.features.length > 0 && (
                      <ul className="mt-4 space-y-1.5 border-t border-surface-border pt-3 text-xs text-slate-300">
                        {plan.features.map((feature) => (
                          <li key={feature} className="flex items-center gap-1.5">
                            <Check className="h-3.5 w-3.5 shrink-0 text-emerald-400" /> {featureLabel(feature)}
                          </li>
                        ))}
                      </ul>
                    )}

                    <div className="mt-5 flex-1" />

                    {isCurrent ? (
                      <button type="button" disabled className="btn-secondary w-full !cursor-default opacity-60">
                        Current plan
                      </button>
                    ) : plan.is_custom ? (
                      <a href="mailto:sales@myseoapp.example" className="btn-secondary w-full">
                        Contact sales
                      </a>
                    ) : canManageBilling ? (
                      <button
                        type="button"
                        onClick={() => handleUpgrade(plan.code)}
                        disabled={pendingPlan !== null}
                        className="btn-primary w-full"
                      >
                        {pendingPlan === plan.code ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                        Choose {plan.name}
                      </button>
                    ) : (
                      <button type="button" disabled title="Only the owner can change plans" className="btn-secondary w-full !cursor-not-allowed opacity-60">
                        <Lock className="h-3.5 w-3.5" /> Owner only
                      </button>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
