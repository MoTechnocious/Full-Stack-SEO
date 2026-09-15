"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Bot,
  Code2,
  CreditCard,
  Edit3,
  Fingerprint,
  Gauge,
  Globe,
  KeyRound,
  LayoutDashboard,
  ListChecks,
  MapPin,
  MessageCircleQuestion,
  Plug,
  Radar,
  Search,
  Sparkles,
  TrendingUp,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  description: string;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, description: "Overview" },
  { href: "/audit", label: "Site Audit", icon: Globe, description: "Crawl & technical SEO" },
  { href: "/onpage", label: "On-Page", icon: Edit3, description: "Content editor" },
  { href: "/keywords", label: "Keywords", icon: Search, description: "Research & SERP" },
  { href: "/rankings", label: "Rankings", icon: TrendingUp, description: "Rank tracking" },
  { href: "/reports", label: "Reports", icon: BarChart3, description: "White-label reports" },
  { href: "/integrations", label: "Integrations", icon: Plug, description: "Leads & webhooks" },
];

const AI_SEARCH_NAV_ITEMS: NavItem[] = [
  { href: "/kit", label: "Kit Assistant", icon: Bot, description: "Agentic plans & execution" },
  { href: "/geo", label: "AI Visibility", icon: Radar, description: "GEO — LLM tracking" },
  { href: "/ai-tracker", label: "AI Tracker", icon: Activity, description: "v2 — scheduled visibility" },
  { href: "/peo", label: "Entity", icon: Fingerprint, description: "PEO — Knowledge Graph" },
  { href: "/aeo", label: "Answers", icon: MessageCircleQuestion, description: "AEO — PAA & voice" },
];

const LOCAL_AGENCY_NAV_ITEMS: NavItem[] = [
  { href: "/local", label: "Local SEO", icon: MapPin, description: "GBP & citations" },
  { href: "/widget", label: "Lead Widget", icon: Code2, description: "Embeddable audits" },
];

const WORKSPACE_NAV_ITEMS: NavItem[] = [
  { href: "/jobs", label: "Jobs", icon: ListChecks, description: "Background queue" },
  { href: "/team", label: "Team", icon: Users, description: "Members & invites" },
  { href: "/api-keys", label: "API Keys", icon: KeyRound, description: "Programmatic access" },
  { href: "/billing", label: "Billing", icon: CreditCard, description: "Plans & subscription" },
  { href: "/usage", label: "Usage", icon: Gauge, description: "Quotas & metering" },
];

function isActivePath(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={cn(
        "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
        active
          ? "bg-brand-500/15 text-brand-200 ring-1 ring-inset ring-brand-500/30"
          : "text-slate-400 hover:bg-white/5 hover:text-slate-100",
      )}
    >
      <Icon className={cn("h-4 w-4 shrink-0", active ? "text-brand-300" : "text-slate-500 group-hover:text-slate-300")} />
      <span className="flex-1">{item.label}</span>
    </Link>
  );
}

/** Fixed left navigation rail. Client component: needs `usePathname` for the active state. */
export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-64 shrink-0 border-r border-surface-border bg-surface-raised/60 backdrop-blur-xl lg:flex lg:flex-col">
      <div className="flex h-16 items-center gap-2 border-b border-surface-border px-5">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-accent-400 text-white shadow-glow">
          <Sparkles className="h-4 w-4" />
        </span>
        <div className="leading-tight">
          <p className="text-sm font-semibold text-slate-50">MySEOapp</p>
          <p className="text-[11px] text-slate-500">SEO Operations</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4 scrollbar-thin">
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.href} item={item} active={isActivePath(pathname, item.href)} />
        ))}

        <p className="px-3 pb-1 pt-4 text-[10px] font-semibold uppercase tracking-wide text-slate-600">AI Search</p>
        {AI_SEARCH_NAV_ITEMS.map((item) => (
          <NavLink key={item.href} item={item} active={isActivePath(pathname, item.href)} />
        ))}

        <p className="px-3 pb-1 pt-4 text-[10px] font-semibold uppercase tracking-wide text-slate-600">Local &amp; Agency</p>
        {LOCAL_AGENCY_NAV_ITEMS.map((item) => (
          <NavLink key={item.href} item={item} active={isActivePath(pathname, item.href)} />
        ))}

        <p className="px-3 pb-1 pt-4 text-[10px] font-semibold uppercase tracking-wide text-slate-600">Workspace</p>
        {WORKSPACE_NAV_ITEMS.map((item) => (
          <NavLink key={item.href} item={item} active={isActivePath(pathname, item.href)} />
        ))}
      </nav>

      <div className="border-t border-surface-border px-5 py-4">
        <div className="rounded-xl border border-brand-500/20 bg-brand-500/5 p-3">
          <p className="text-xs font-medium text-brand-200">Connected API</p>
          <p className="mt-0.5 truncate text-[11px] text-slate-500">
            {process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}
          </p>
        </div>
      </div>
    </aside>
  );
}
