"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, Loader2, Sparkles, UserPlus } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { safeRedirectPath } from "@/lib/utils";

export default function SignupPage() {
  const router = useRouter();
  const { signup } = useAuth();

  const [fullName, setFullName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!email.trim() || !password) return;
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    if (password.length < 8) {
      setError("Use at least 8 characters for your password.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await signup(email.trim(), password, fullName.trim(), orgName.trim());
      const redirect = new URLSearchParams(window.location.search).get("redirect");
      router.push(safeRedirectPath(redirect, "/onboarding"));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not reach the API. Check NEXT_PUBLIC_API_BASE_URL and that the backend is running.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-400 text-white shadow-glow">
            <Sparkles className="h-5 w-5" />
          </span>
          <div>
            <p className="text-lg font-semibold text-slate-50">MySEOapp</p>
            <p className="text-xs text-slate-500">SEO Operations Dashboard</p>
          </div>
        </div>

        <div className="rounded-2xl border border-surface-border bg-surface-card p-6 shadow-card">
          <h1 className="text-lg font-semibold text-slate-50">Create your account</h1>
          <p className="mt-1 text-sm text-slate-400">Starts on the Free plan — upgrade any time from Billing.</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="signup-name" className="label-base">
                Full name <span className="normal-case text-slate-600">(optional)</span>
              </label>
              <input
                id="signup-name"
                type="text"
                autoComplete="name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Jordan Rivera"
                className="input-base"
              />
            </div>
            <div>
              <label htmlFor="signup-org" className="label-base">
                Organization <span className="normal-case text-slate-600">(optional)</span>
              </label>
              <input
                id="signup-org"
                type="text"
                autoComplete="organization"
                value={orgName}
                onChange={(event) => setOrgName(event.target.value)}
                placeholder="Scaling Firm"
                className="input-base"
              />
            </div>
            <div>
              <label htmlFor="signup-email" className="label-base">
                Email
              </label>
              <input
                id="signup-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@company.com"
                className="input-base"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="signup-password" className="label-base">
                  Password
                </label>
                <input
                  id="signup-password"
                  type="password"
                  required
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                  className="input-base"
                />
              </div>
              <div>
                <label htmlFor="signup-confirm" className="label-base">
                  Confirm
                </label>
                <input
                  id="signup-confirm"
                  type="password"
                  required
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  placeholder="••••••••"
                  className="input-base"
                />
              </div>
            </div>

            {error && (
              <p className="flex items-start gap-1.5 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {error}
              </p>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              Create account
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-brand-300 transition hover:text-brand-200">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
