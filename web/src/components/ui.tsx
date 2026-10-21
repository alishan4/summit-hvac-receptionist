import type { ReactNode } from "react";
import type { Tone } from "@/lib/types";

export function Card({ className = "", children }: { className?: string; children: ReactNode }) {
  return <section className={`rounded-2xl border border-line bg-white shadow-card ${className}`}>{children}</section>;
}

export function PanelHeader({ icon, title, subtitle, right }: { icon: ReactNode; title: string; subtitle?: string; right?: ReactNode }) {
  return (
    <header className="flex items-start justify-between gap-3 border-b border-line px-5 py-4 sm:px-6">
      <div className="flex items-center gap-3">
        <span className="grid size-9 place-items-center rounded-xl bg-accent-soft text-accent">{icon}</span>
        <div>
          <h2 className="text-[15px] font-semibold leading-tight tracking-tight">{title}</h2>
          {subtitle && <p className="mt-0.5 text-[13px] text-muted">{subtitle}</p>}
        </div>
      </div>
      {right}
    </header>
  );
}

export const TONE: Record<Tone, { dot: string; chip: string; ring: string }> = {
  neutral: { dot: "bg-slate-400", chip: "bg-slate-100 text-slate-700", ring: "ring-slate-200" },
  success: { dot: "bg-emerald-500", chip: "bg-emerald-50 text-emerald-700", ring: "ring-emerald-200" },
  warn: { dot: "bg-amber-500", chip: "bg-amber-50 text-amber-900", ring: "ring-amber-200" },
  danger: { dot: "bg-red-500", chip: "bg-red-50 text-red-700", ring: "ring-red-200" },
};

export function Chip({ tone = "neutral", children, className = "" }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${TONE[tone].chip} ${className}`}>
      {children}
    </span>
  );
}

export function Empty({ icon, title, hint }: { icon: ReactNode; title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-line px-6 py-8 text-center">
      <span className="grid size-10 place-items-center rounded-full bg-slate-50 text-slate-400">{icon}</span>
      <p className="text-sm font-medium text-slate-600">{title}</p>
      {hint && <p className="max-w-xs text-[13px] text-muted">{hint}</p>}
    </div>
  );
}

export function Spinner({ className = "size-5" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export const btnPrimary =
  "inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-accent-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50";
export const btnGhost =
  "inline-flex items-center justify-center gap-2 rounded-xl border border-line bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-50";
