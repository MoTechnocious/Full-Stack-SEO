"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Loader2 } from "lucide-react";
import Card from "@/components/Card";
import { useAuth } from "@/lib/auth";
import { getSubscription, type Subscription } from "@/lib/api";
import { titleCase } from "@/lib/utils";

/**
 * Landing page for the (mock) checkout redirect — see `success_url` passed
 * from the billing page. Reads the query string directly (not
 * `useSearchParams`) so this route doesn't need a Suspense boundary.
 */
export default function BillingSuccessPage() {
  const { refreshMe } = useAuth();
  const [planParam, setPlanParam] = useState<string | null>(null);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setPlanParam(new URLSearchParams(window.location.search).get("plan"));
    }
    Promise.all([refreshMe().catch(() => undefined), getSubscription().catch(() => undefined)]).then(([, sub]) => {
      if (sub) setSubscription(sub);
      setLoading(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const planName = subscription?.plan.name ?? (planParam ? titleCase(planParam) : "your new plan");

  return (
    <div className="mx-auto max-w-md py-10">
      <Card>
        <div className="flex flex-col items-center gap-4 py-6 text-center">
          {loading ? (
            <Loader2 className="h-10 w-10 animate-spin text-brand-400" />
          ) : (
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-400">
              <CheckCircle2 className="h-7 w-7" />
            </span>
          )}
          <div>
            <h1 className="text-lg font-semibold text-slate-50">{loading ? "Finalizing your upgrade…" : `You're on the ${planName} plan!`}</h1>
            <p className="mt-1 text-sm text-slate-400">
              {loading ? "Confirming your subscription." : "Your organization's plan, limits and features have been updated."}
            </p>
          </div>
          {!loading && (
            <div className="flex gap-2">
              <Link href="/billing" className="btn-secondary">
                Back to billing
              </Link>
              <Link href="/" className="btn-primary">
                Go to dashboard <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
