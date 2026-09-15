import type { ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

export type KpiTrend = "up" | "down" | "flat";

interface KpiCardProps {
  label: string;
  value: string;
  icon?: ReactNode;
  trend?: KpiTrend;
  trendLabel?: string;
  /** Which trend direction should render as "good" (green). Defaults to "up". */
  trendGood?: "up" | "down";
  className?: string;
}

/** Dashboard KPI tile: label, big value, optional icon + trend chip. */
export default function KpiCard({ label, value, icon, trend, trendLabel, trendGood = "up", className }: KpiCardProps) {
  const isGood = trend && trend !== "flat" ? trend === trendGood : null;

  return (
    <div className={cn("rounded-2xl border border-surface-border bg-surface-card p-5 shadow-card", className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</span>
        {icon && <span className="text-brand-400">{icon}</span>}
      </div>
      <div className="mt-3 flex items-end justify-between gap-2">
        <span className="text-3xl font-bold text-slate-50 tabular-nums">{value}</span>
        {trend && trendLabel && (
          <span
            className={cn(
              "mb-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
              isGood === true && "bg-emerald-500/10 text-emerald-400",
              isGood === false && "bg-rose-500/10 text-rose-400",
              isGood === null && "bg-slate-500/10 text-slate-400",
            )}
          >
            {trend === "up" && <ArrowUpRight className="h-3 w-3" />}
            {trend === "down" && <ArrowDownRight className="h-3 w-3" />}
            {trend === "flat" && <Minus className="h-3 w-3" />}
            {trendLabel}
          </span>
        )}
      </div>
    </div>
  );
}
