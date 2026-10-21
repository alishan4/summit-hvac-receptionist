"use client";

import { CalendarCheck, PhoneCall, PhoneForwarded, ShieldAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Api } from "@/lib/api";
import { usePolling } from "@/lib/hooks";
import type { Stats } from "@/lib/types";

function Count({ value }: { value: number }) {
  const [shown, setShown] = useState(value);
  const from = useRef(value);
  useEffect(() => {
    const start = from.current;
    if (start === value) return;
    const t0 = performance.now();
    let raf = 0;
    const step = (t: number) => {
      const p = Math.min(1, (t - t0) / 600);
      setShown(Math.round(start + (value - start) * (1 - (1 - p) ** 3)));
      if (p < 1) raf = requestAnimationFrame(step);
      else from.current = value;
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{shown}</>;
}

export function ResultsStrip({ api, tick }: { api: Api; tick: string }) {
  const [stats, setStats] = useState<Stats | null>(null);
  usePolling(async (signal) => setStats(await api.stats(signal)), 8000, true, [api, tick]);

  const tiles = [
    { label: "Calls today", value: stats?.calls_today, icon: <PhoneCall className="size-4" />, tint: "bg-accent-soft text-accent" },
    { label: "Appointments booked", value: stats?.booked, icon: <CalendarCheck className="size-4" />, tint: "bg-emerald-50 text-emerald-700" },
    { label: "Emergencies handled", value: stats?.emergencies, icon: <ShieldAlert className="size-4" />, tint: "bg-red-50 text-red-700" },
    { label: "Callbacks requested", value: stats?.callbacks, icon: <PhoneForwarded className="size-4" />, tint: "bg-amber-50 text-amber-800" },
  ];
  return (
    <section aria-label="Today's results" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {tiles.map((t) => (
        <div key={t.label} className="flex items-center gap-3.5 rounded-2xl border border-line bg-white px-4 py-4 shadow-card sm:px-5">
          <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${t.tint}`}>{t.icon}</span>
          <div>
            <p className="text-2xl font-semibold leading-none tracking-tight tabular-nums">
              {t.value === undefined ? <span className="skeleton inline-block h-6 w-8 rounded" /> : <Count value={t.value} />}
            </p>
            <p className="mt-1 text-xs text-muted">{t.label}</p>
          </div>
        </div>
      ))}
    </section>
  );
}
