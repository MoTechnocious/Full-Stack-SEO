"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, ArrowRight, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import Card from "@/components/Card";
import { useAuth } from "@/lib/auth";
import { acceptInvite, ApiError } from "@/lib/api";

/**
 * Landing page for invite links shared from the Team page. Reads `?token=`
 * directly from `window.location.search` (not `useSearchParams`) so this
 * route doesn't need a Suspense boundary. Works for both guests (who need to
 * log in/sign up first, token stays in the URL) and signed-in users (who can
 * accept immediately).
 */
export default function AcceptInvitePage() {
  const router = useRouter();
  const { isAuthenticated, switchOrg } = useAuth();

  const [token, setToken] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "accepting" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setToken(new URLSearchParams(window.location.search).get("token"));
    }
  }, []);

  async function handleAccept() {
    if (!token) return;
    setStatus("accepting");
    setError(null);
    try {
      const result = await acceptInvite({ token });
      try {
        await switchOrg(result.org_id);
      } catch {
        // Joined successfully even if the auto-switch fails — they can
        // switch manually from the org switcher in the top bar.
      }
      setStatus("done");
    } catch (err) {
      setStatus("error");
      setError(err instanceof ApiError ? err.message : "Could not reach the API — try again in a moment.");
    }
  }

  const returnTo = token ? `/accept-invite?token=${encodeURIComponent(token)}` : "/accept-invite";
  const loginHref = `/login?redirect=${encodeURIComponent(returnTo)}`;
  const signupHref = `/signup?redirect=${encodeURIComponent(returnTo)}`;

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-3 text-center">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-400 text-white shadow-glow">
            <Sparkles className="h-5 w-5" />
          </span>
          <p className="text-lg font-semibold text-slate-50">MySEOapp</p>
        </div>

        <Card>
          {!token ? (
            <p className="flex items-start gap-2 text-sm text-slate-400">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" /> This invite link is missing its token. Ask
              whoever invited you to resend it.
            </p>
          ) : status === "done" ? (
            <div className="flex flex-col items-center gap-3 py-2 text-center">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-400">
                <CheckCircle2 className="h-6 w-6" />
              </span>
              <p className="text-sm font-medium text-slate-100">You&apos;re in! The organization has been added to your account.</p>
              <button type="button" onClick={() => router.push("/")} className="btn-primary">
                Go to dashboard <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          ) : !isAuthenticated ? (
            <div className="space-y-4 text-center">
              <p className="text-sm text-slate-300">Log in or create an account to accept this invite.</p>
              <div className="flex gap-2">
                <Link href={loginHref} className="btn-secondary flex-1">
                  Log in
                </Link>
                <Link href={signupHref} className="btn-primary flex-1">
                  Sign up
                </Link>
              </div>
              <p className="text-xs text-slate-500">Come back to this exact link afterward to finish joining.</p>
            </div>
          ) : (
            <div className="space-y-4 text-center">
              <p className="text-sm text-slate-300">You&apos;ve been invited to join an organization on MySEOapp.</p>
              {error && (
                <p className="flex items-start gap-1.5 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-left text-xs text-rose-300">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {error}
                </p>
              )}
              <button type="button" onClick={handleAccept} disabled={status === "accepting"} className="btn-primary w-full">
                {status === "accepting" ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                Accept invite
              </button>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
