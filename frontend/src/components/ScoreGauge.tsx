import { cn, clampPercent, scoreTone, TONE_CLASSES } from "@/lib/utils";

interface ScoreGaugeProps {
  score: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
  className?: string;
}

const STROKE_BY_TONE = {
  good: "#34d399",
  warning: "#fbbf24",
  danger: "#fb7185",
} as const;

/** SVG circular gauge (0-100) used for site health, content score, on-page score. */
export default function ScoreGauge({ score, size = 128, strokeWidth = 10, label, className }: ScoreGaugeProps) {
  const pct = clampPercent(score);
  const tone = scoreTone(pct);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - pct / 100);
  const center = size / 2;

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle cx={center} cy={center} r={radius} fill="none" stroke="#1f2536" strokeWidth={strokeWidth} />
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={STROKE_BY_TONE[tone]}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("text-2xl font-bold tabular-nums", TONE_CLASSES[tone].text)}>{pct}</span>
        {label && <span className="mt-0.5 text-center text-[10px] uppercase tracking-wide text-slate-500">{label}</span>}
      </div>
    </div>
  );
}
