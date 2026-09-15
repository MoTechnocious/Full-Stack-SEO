"use client";

import { useEffect, useState } from "react";
import { Building2, Check, ChevronDown, Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { ApiError, listOrgs, type Org } from "@/lib/api";
import { cn, titleCase } from "@/lib/utils";

/** Topbar dropdown: lists every org the user belongs to and switches the active one. */
export default function OrgSwitcher() {
  const { orgId, orgName, switchOrg, isAuthenticated } = useAuth();
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    listOrgs()
      .then((result) => {
        if (!cancelled) setOrgs(result);
      })
      .catch(() => {
        // Offline/degraded: keep the dropdown showing just the current org.
      });
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  async function handleSwitch(id: string) {
    if (id === orgId) {
      setOpen(false);
      return;
    }
    setSwitching(true);
    setError(null);
    try {
      await switchOrg(id);
      setOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not switch organizations.");
    } finally {
      setSwitching(false);
    }
  }

  if (!isAuthenticated) return null;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-full border border-surface-border bg-surface-raised py-1.5 pl-3 pr-2.5 text-xs font-medium text-slate-200 transition hover:border-brand-500/40"
      >
        <Building2 className="h-3.5 w-3.5 shrink-0 text-brand-300" />
        <span className="max-w-[9rem] truncate">{orgName ?? "Select organization"}</span>
        {switching ? (
          <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-slate-500" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-slate-500" />
        )}
      </button>

      {open && (
        <>
          {/* Click-outside catcher */}
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-2 w-64 rounded-xl border border-surface-border bg-surface-card p-1.5 shadow-card">
            <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
              Your organizations
            </p>
            {orgs.length === 0 ? (
              <p className="px-3 py-2 text-xs text-slate-500">{orgName ?? "No organizations found."}</p>
            ) : (
              orgs.map((org) => (
                <button
                  key={org.id}
                  type="button"
                  disabled={switching}
                  onClick={() => handleSwitch(org.id)}
                  className={cn(
                    "flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-60",
                    org.id === orgId ? "text-brand-200" : "text-slate-300",
                  )}
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{org.name}</span>
                    <span className="block text-[11px] text-slate-500">
                      {titleCase(org.role)} · {titleCase(org.plan_code)}
                    </span>
                  </span>
                  {org.id === orgId && <Check className="h-3.5 w-3.5 shrink-0 text-brand-400" />}
                </button>
              ))
            )}
            {error && <p className="px-3 py-1.5 text-[11px] text-rose-400">{error}</p>}
          </div>
        </>
      )}
    </div>
  );
}
