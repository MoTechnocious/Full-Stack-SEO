"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { CreditCard, Loader2, ShieldAlert, X } from "lucide-react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { useAuth } from "@/lib/auth";

/** Unauthenticated-only routes: redirect to "/" once logged in. */
const GUEST_PATHS = new Set(["/login", "/signup"]);

/** Routes that work for both guests and members — no forced redirect either way. */
const OPEN_PATHS = new Set(["/accept-invite"]);

/** Routes that render full-bleed, without Sidebar/Topbar. */
const NO_CHROME_PATHS = new Set(["/login", "/signup", "/onboarding", "/accept-invite"]);

function FullScreenSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface">
      <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
    </div>
  );
}

function UpgradeBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="mb-4 flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
      <CreditCard className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="font-medium">Upgrade your plan</p>
        <p className="mt-0.5 text-xs text-amber-300/90">{message}</p>
        <Link href="/billing" className="mt-1.5 inline-block text-xs font-semibold text-amber-200 underline underline-offset-2">
          View plans
        </Link>
      </div>
      <button type="button" onClick={onDismiss} className="shrink-0 text-amber-300/70 transition hover:text-amber-100">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

function ForbiddenBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="mb-4 flex items-start gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
      <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="font-medium">Insufficient permissions</p>
        <p className="mt-0.5 text-xs text-rose-300/90">{message}</p>
      </div>
      <button type="button" onClick={onDismiss} className="shrink-0 text-rose-300/70 transition hover:text-rose-100">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

/**
 * Single client-side router guard + chrome switcher.
 *
 * Route classes:
 *  - `/login`, `/signup`  — guests only; redirect to "/" once authenticated.
 *  - `/accept-invite`     — open to both; never force-redirected either way
 *                            (an invite link must work for someone with no
 *                            account yet). The page itself branches on auth.
 *  - `/onboarding`        — requires auth, renders full-bleed (no chrome).
 *  - everything else      — requires auth, renders inside the dashboard shell.
 *
 * We never flash protected content: `isLoading` (localStorage hydration +
 * the `/auth/me` check in AuthProvider) gates every branch below.
 */
export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isLoading, isAuthenticated, upgradeNotice, forbiddenNotice, dismissUpgradeNotice, dismissForbiddenNotice } =
    useAuth();
  const isGuestPath = GUEST_PATHS.has(pathname);
  const isOpenPath = OPEN_PATHS.has(pathname);
  const hasChrome = !NO_CHROME_PATHS.has(pathname);

  useEffect(() => {
    if (isLoading || isOpenPath) return;
    if (!isAuthenticated && !isGuestPath) {
      router.replace("/login");
    } else if (isAuthenticated && isGuestPath) {
      router.replace("/");
    }
  }, [isLoading, isAuthenticated, isGuestPath, isOpenPath, router]);

  if (isOpenPath) {
    if (isLoading) return <FullScreenSpinner />;
    return <>{children}</>;
  }

  if (isGuestPath) {
    if (isLoading || isAuthenticated) return <FullScreenSpinner />;
    return <>{children}</>;
  }

  if (isLoading || !isAuthenticated) {
    return <FullScreenSpinner />;
  }

  if (!hasChrome) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl animate-fade-in">
            {upgradeNotice && <UpgradeBanner message={upgradeNotice} onDismiss={dismissUpgradeNotice} />}
            {forbiddenNotice && <ForbiddenBanner message={forbiddenNotice} onDismiss={dismissForbiddenNotice} />}
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
