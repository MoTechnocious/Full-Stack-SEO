"use client";

import { LogOut, Sparkles } from "lucide-react";
import Badge from "@/components/Badge";
import OrgSwitcher from "@/components/OrgSwitcher";
import { useAuth } from "@/lib/auth";
import { titleCase } from "@/lib/utils";

const DISPLAY_DATE = "Friday, July 10, 2026";

function initialsFrom(email: string): string {
  const handle = email.split("@")[0] ?? "";
  return handle.slice(0, 2).toUpperCase() || "U";
}

/** Top bar: branding on mobile, org switcher + plan badge + account menu. */
export default function Topbar() {
  const { email, planCode, logout } = useAuth();
  const displayEmail = email ?? "—";

  return (
    <header className="flex h-16 items-center justify-between gap-4 border-b border-surface-border bg-surface/80 px-4 backdrop-blur-xl sm:px-6">
      <div className="flex items-center gap-2 lg:hidden">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-accent-400 text-white">
          <Sparkles className="h-3.5 w-3.5" />
        </span>
        <span className="text-sm font-semibold text-slate-50">MySEOapp</span>
      </div>

      <div className="hidden text-sm text-slate-400 sm:block">{DISPLAY_DATE}</div>

      <div className="flex items-center gap-2 sm:gap-3">
        <OrgSwitcher />
        <Badge tone="brand">{titleCase(planCode ?? "free")}</Badge>
        <div className="flex items-center gap-2 rounded-full border border-surface-border bg-surface-raised py-1 pl-1 pr-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-500/20 text-[10px] font-semibold text-brand-200">
            {initialsFrom(displayEmail)}
          </span>
          <span className="hidden max-w-[10rem] truncate text-xs font-medium text-slate-300 sm:inline">{displayEmail}</span>
          <button
            type="button"
            onClick={logout}
            title="Log out"
            className="ml-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-slate-500 transition hover:bg-white/5 hover:text-rose-300"
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
}
