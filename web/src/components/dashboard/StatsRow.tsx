"use client";

import { CalendarCheck, PhoneCall, PhoneForwarded, ShieldAlert, TrendingUp } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { money } from "@/lib/format";
import { usePolling } from "@/lib/hooks";
import type { Stats } from "@/lib/types";
import { useDemo } from "@/lib/demo";

function Count({ value, format = (n: number) => String(n) }: { value: number; format?: (n: number) => string }) {
  const [shown, setShown] = useState(value);
  const from = useRef(value);
  useEffect(() => {
    const start = from.current;
    if (start === value) return;
    const t0 = performance.now();
    let raf = 0;
    const step = (t: number) => {
      const p = Math.min(1, (t - t0) / 700);
      setShown(start + (value - start) * (1 - (1 - p) ** 3));
      if (p < 1) raf = requestAnimationFrame(step);
      else from.current = value;
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{format(Math.round(shown))}</>;
}

function Tile({ label, icon, tint, value, format, hint, className = "" }: {
  label: string; icon: ReactNode; tint: string; value: number | undefined; format?: (n: number) => string; hint?: string; className?: string;
}) {
  return (
    <div className={`flex items-center gap-3.5 rounded-2xl border border-line bg-white px-4 py-4 shadow-card sm:px-5 ${className}`}>
      <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${tint}`}>{icon}</span>
      <div className="min-w-0">
        <p className="text-2xl font-semibold leading-none tracking-tight tabular-nums">
          {value === undefined ? <span className="skeleton inline-block h-6 w-12 rounded" /> : <Count value={value} format={format} />}
        </p>
        <p className="mt-1 truncate text-xs text-muted">{label}</p>
        {hint && <p className="mt-0.5 text-[11px] text-slate-500">{hint}</p>}
      </div>
    </div>
  );
}

export function StatsRow({ tick, compact = false }: { tick: string; compact?: boolean }) {
  const { api } = useDemo();
  const [stats, setStats] = useState<Stats | null>(null);
  usePolling(async (signal) => { if (api) setStats(await api.stats(signal)); }, 5000, api !== null, [api, tick]);

  return (
    <section aria-label="Today's results" className={`grid gap-3 ${compact ? "grid-cols-2" : "grid-cols-2 lg:grid-cols-5"}`}>
      <Tile label="Calls today" value={stats?.calls_today} icon={<PhoneCall className="size-4" />} tint="bg-accent-soft text-accent-strong" />
      <Tile label="Appointments booked" value={stats?.booked} icon={<CalendarCheck className="size-4" />} tint="bg-emerald-50 text-emerald-700" />
      <Tile label="Emergencies handled" value={stats?.emergencies} icon={<ShieldAlert className="size-4" />} tint="bg-red-50 text-red-700" />
      <Tile label="Callbacks requested" value={stats?.callbacks} icon={<PhoneForwarded className="size-4" />} tint="bg-amber-50 text-amber-800" />
      <Tile
        label="Revenue protected (est.)" value={stats?.revenue_protected} format={money}
        icon={<TrendingUp className="size-4" />} tint="bg-emerald-600 text-white"
        hint={stats ? `after-hours: ${stats.booked} booked × ${money(stats.average_job_value)}` : undefined}
        className={compact ? "col-span-2" : "col-span-2 lg:col-span-1"}
      />
    </section>
  );
}
