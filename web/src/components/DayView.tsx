"use client";

import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import type { Api } from "@/lib/api";
import { addDays, prettyDate } from "@/lib/format";
import { usePolling } from "@/lib/hooks";
import type { DayView as DayData } from "@/lib/types";
import { Card, Empty, PanelHeader, btnGhost } from "./ui";

export function DayView({
  api, timezone, jumpTo, tick,
}: { api: Api; timezone: string; jumpTo: string | null; tick: string }) {
  const today = new Date().toLocaleDateString("en-CA", { timeZone: timezone });
  const [date, setDate] = useState(today);
  const [data, setData] = useState<DayData | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (jumpTo) setDate(jumpTo); // follow a freshly booked appointment to its day
  }, [jumpTo]);

  usePolling(async (signal) => {
    try {
      setData(await api.appointments(date, signal));
      setFailed(false);
    } catch (e) {
      if (!(e instanceof DOMException)) setFailed(true);
      throw e;
    }
  }, 5000, true, [api, date, tick]);

  return (
    <Card>
      <PanelHeader
        icon={<CalendarDays className="size-[18px]" />} title="Technician schedule" subtitle="Booked arrival windows from our own database."
        right={
          <div className="flex items-center gap-1">
            <button className={`${btnGhost} !px-2 !py-1.5`} onClick={() => setDate(addDays(date, -1))} aria-label="Previous day"><ChevronLeft className="size-4" /></button>
            <button className={`${btnGhost} !px-2.5 !py-1.5 text-xs`} onClick={() => setDate(today)} disabled={date === today}>Today</button>
            <button className={`${btnGhost} !px-2 !py-1.5`} onClick={() => setDate(addDays(date, 1))} aria-label="Next day"><ChevronRight className="size-4" /></button>
          </div>
        }
      />
      <div className="px-5 py-5 sm:px-6">
        <p className="mb-3 text-sm font-semibold">{prettyDate(date)}</p>
        {!data && !failed && <div className="space-y-2">{[0, 1, 2].map((i) => <div key={i} className="skeleton h-11 rounded-xl" />)}</div>}
        {failed && !data && <Empty icon={<CalendarDays className="size-5" />} title="Couldn't load the schedule" hint="It will retry automatically." />}
        {data?.closed && <Empty icon={<CalendarDays className="size-5" />} title="Closed this day" hint="No arrival windows are offered on this day." />}
        {data && !data.closed && (
          <ul className="space-y-2">
            {data.windows.map((w) => (
              <li key={w.start}
                className={`flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm transition ${
                  w.status === "booked" ? "animate-pop bg-accent-soft ring-1 ring-accent-ring"
                  : w.status === "past" ? "bg-slate-50 text-slate-400"
                  : "border border-dashed border-line text-slate-500"}`}>
                <span className="w-28 shrink-0 font-mono text-xs">{w.label}</span>
                {w.appointment ? (
                  <span className="min-w-0 flex-1 truncate">
                    <strong className="font-semibold text-accent-strong">{w.appointment.customer_name}</strong>
                    <span className="text-slate-600"> · {w.appointment.issue_label} · {w.appointment.address}</span>
                  </span>
                ) : (
                  <span className="flex-1 text-xs">{w.status === "past" ? "Past" : "Open"}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
