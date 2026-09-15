import type { ReactNode } from "react";
import { cn, scoreTone } from "@/lib/utils";
import type { DeliveryStatus, Indexability, SearchIntent, Severity, TaskStatus, TermStatus } from "@/lib/api";

export type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger" | "brand";

const TONE_STYLES: Record<BadgeTone, string> = {
  neutral: "bg-slate-500/10 text-slate-300 ring-slate-500/25",
  info: "bg-sky-500/10 text-sky-300 ring-sky-500/25",
  success: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/25",
  warning: "bg-amber-500/10 text-amber-300 ring-amber-500/25",
  danger: "bg-rose-500/10 text-rose-300 ring-rose-500/25",
  brand: "bg-brand-500/10 text-brand-300 ring-brand-500/25",
};

const DOT_STYLES: Record<BadgeTone, string> = {
  neutral: "bg-slate-400",
  info: "bg-sky-400",
  success: "bg-emerald-400",
  warning: "bg-amber-400",
  danger: "bg-rose-400",
  brand: "bg-brand-400",
};

interface BadgeProps {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
  dot?: boolean;
}

/** Small colored status pill (aka StatusPill) used for severities, statuses, grades. */
export default function Badge({ children, tone = "neutral", className, dot = false }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset",
        TONE_STYLES[tone],
        className,
      )}
    >
      {dot && <span className={cn("h-1.5 w-1.5 rounded-full", DOT_STYLES[tone])} />}
      {children}
    </span>
  );
}

/** Alias kept for call-sites that read better as "StatusPill" (deliveries, tasks). */
export const StatusPill = Badge;

export function severityTone(severity: Severity): BadgeTone {
  switch (severity) {
    case "critical":
    case "high":
      return "danger";
    case "medium":
      return "warning";
    case "low":
      return "info";
    default:
      return "neutral";
  }
}

export function taskStatusTone(status: TaskStatus): BadgeTone {
  switch (status) {
    case "done":
      return "success";
    case "in_progress":
      return "info";
    case "flagged":
      return "danger";
    default:
      return "neutral";
  }
}

export function deliveryStatusTone(status: DeliveryStatus): BadgeTone {
  switch (status) {
    case "delivered":
    case "sent":
    case "validated":
      return "success";
    case "pending":
      return "info";
    case "failed":
    case "rejected":
      return "danger";
    default:
      return "neutral";
  }
}

export function indexabilityTone(value: Indexability): BadgeTone {
  return value === "indexable" ? "success" : "warning";
}

export function termStatusTone(status: TermStatus): BadgeTone {
  switch (status) {
    case "optimal":
      return "success";
    case "under":
      return "warning";
    case "over":
      return "danger";
    default:
      return "neutral";
  }
}

export function statusCodeTone(code: number): BadgeTone {
  if (code >= 200 && code < 300) return "success";
  if (code >= 300 && code < 400) return "info";
  if (code >= 400 && code < 500) return "warning";
  if (code >= 500) return "danger";
  return "neutral";
}

/** Maps a 0-100 score (site health / on-page / content score) onto a badge tone. */
export function scoreBadgeTone(score: number): BadgeTone {
  const tone = scoreTone(score);
  if (tone === "good") return "success";
  if (tone === "warning") return "warning";
  return "danger";
}

export function intentTone(intent: SearchIntent): BadgeTone {
  switch (intent) {
    case "transactional":
      return "success";
    case "commercial":
      return "brand";
    case "informational":
      return "info";
    case "navigational":
      return "neutral";
    default:
      return "neutral";
  }
}

/** Keyword difficulty (0-100, higher = harder) mapped onto a badge tone. */
export function difficultyTone(value: number): BadgeTone {
  if (value <= 30) return "success";
  if (value <= 60) return "warning";
  return "danger";
}
