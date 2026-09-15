import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: string;
  description?: string;
  actions?: ReactNode;
  padded?: boolean;
}

/** Generic surface container used across every page — rounded, bordered, dark. */
export default function Card({ children, className, title, description, actions, padded = true }: CardProps) {
  const hasHeader = Boolean(title || description || actions);
  return (
    <div className={cn("rounded-2xl border border-surface-border bg-surface-card shadow-card", className)}>
      {hasHeader && (
        <div className="flex items-start justify-between gap-4 border-b border-surface-border px-5 py-4">
          <div>
            {title && <h3 className="text-sm font-semibold text-slate-100">{title}</h3>}
            {description && <p className="mt-0.5 text-xs text-slate-400">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={padded ? "p-5" : undefined}>{children}</div>
    </div>
  );
}
