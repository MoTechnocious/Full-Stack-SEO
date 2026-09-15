/** Small, dependency-free UI helpers shared by pages and components. */

/** Join class names, skipping falsy values. Minimal `clsx` substitute. */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

/** Map a 0-100 score to a letter grade (A-F), mirroring backend `grade_from_score`. */
export function gradeFromScore(score: number): string {
  const s = Math.max(0, Math.min(100, score));
  if (s >= 90) return "A";
  if (s >= 80) return "B";
  if (s >= 70) return "C";
  if (s >= 60) return "D";
  if (s >= 50) return "E";
  return "F";
}

export type ScoreTone = "good" | "warning" | "danger";

/** Map a 0-100 score to a status tone, mirroring backend `status_label`. */
export function scoreTone(score: number): ScoreTone {
  if (score >= 80) return "good";
  if (score >= 50) return "warning";
  return "danger";
}

/** Tailwind color classes keyed by score tone, used across gauges/badges/bars. */
export const TONE_CLASSES: Record<ScoreTone, { text: string; bg: string; ring: string; dot: string }> = {
  good: { text: "text-emerald-400", bg: "bg-emerald-500/10", ring: "ring-emerald-500/30", dot: "bg-emerald-400" },
  warning: { text: "text-amber-400", bg: "bg-amber-500/10", ring: "ring-amber-500/30", dot: "bg-amber-400" },
  danger: { text: "text-rose-400", bg: "bg-rose-500/10", ring: "ring-rose-500/30", dot: "bg-rose-400" },
};

/** Format an ISO date/datetime string for display; falls back to the raw string. */
export function formatDate(iso: string | null | undefined, options?: Intl.DateTimeFormatOptions): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("en-US", options ?? { month: "short", day: "numeric", year: "numeric" }).format(d);
}

/** Format an integer with thousands separators. */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-US").format(value);
}

/** Format a number with an explicit +/- sign, used for rank/position deltas. */
export function formatSigned(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (value === 0) return "0";
  return value > 0 ? `+${value}` : `${value}`;
}

/** Replicates the (non-serialized) `TrackedKeyword.delta` property from the backend:
 * positive = improvement (moved closer to #1). */
export function keywordDelta(current: number | null, previous: number | null): number | null {
  if (current === null || previous === null) return null;
  return previous - current;
}

/** Bucket an HTTP status code into the "2xx"/"3xx"/... class used by crawl summaries. */
export function statusClass(code: number): string {
  if (code <= 0) return "0xx";
  return `${Math.floor(code / 100)}xx`;
}

/** Title-case a snake_case or lower-case token for display, e.g. "on_page" -> "On Page". */
export function titleCase(value: string): string {
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/** Clamp + round a number for progress bars / gauges. */
export function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

/** Truncate long strings (URLs, snippets) for compact table cells. */
export function truncate(value: string, max = 60): string {
  if (value.length <= max) return value;
  return `${value.slice(0, max - 1)}…`;
}

/** Extract a bare hostname from a URL string; falls back to the raw input. */
export function hostnameOf(value: string): string {
  try {
    return new URL(value).hostname;
  } catch {
    return value;
  }
}

/**
 * Sanitize a `?redirect=` query value into a same-app path. Only in-app
 * absolute paths ("/team", "/accept-invite?token=…") are honored; anything
 * external ("https://evil.com", "//evil.com") or malformed falls back, so the
 * login/signup pages can never be used as an open redirect.
 */
export function safeRedirectPath(raw: string | null | undefined, fallback: string): string {
  if (!raw) return fallback;
  let decoded = raw;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    return fallback;
  }
  if (decoded.startsWith("/") && !decoded.startsWith("//") && !decoded.includes("\\")) return decoded;
  return fallback;
}
