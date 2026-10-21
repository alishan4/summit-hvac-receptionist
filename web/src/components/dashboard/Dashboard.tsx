"use client";

import { ExternalLink, Inbox, LockKeyhole, RotateCcw, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";
import { useDemo } from "@/lib/demo";
import { useCallEvents, usePolling } from "@/lib/hooks";
import type { CallRow } from "@/lib/types";
import { ActivityTimeline } from "../ActivityTimeline";
import { AppointmentCard } from "../AppointmentCard";
import { Logo } from "../Brand";
import { DayView } from "../DayView";
import { NotificationPreview } from "../NotificationPreview";
import { Card, PanelHeader, btnGhost } from "../ui";
import { CallList } from "./CallList";
import { StatsRow } from "./StatsRow";

export function DashboardHeader({ compact = false, onReset, resetting }: { compact?: boolean; onReset: () => void; resetting: boolean }) {
  const { branding, lock } = useDemo();
  return (
    <header className={`flex flex-wrap items-center justify-between gap-3 ${compact ? "" : "border-b border-line bg-white px-4 py-3 sm:px-8"}`}>
      <div className="flex min-w-0 items-center gap-3">
        <Logo branding={branding} size={compact ? 32 : 40} />
        <div className="min-w-0">
          <h1 className={`truncate font-semibold leading-tight tracking-tight ${compact ? "text-[15px]" : "text-lg"}`}>{branding.company.name} — AI Receptionist</h1>
          <p className="text-xs text-muted">
            {branding.agency.show_powered_by ? <>Powered by <strong className="font-semibold text-slate-700">{branding.agency.name}</strong></> : "Business dashboard"}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {!compact && (
          <Link href="/" className={btnGhost}><ExternalLink className="size-4" aria-hidden /> View website</Link>
        )}
        <button onClick={onReset} disabled={resetting} className={btnGhost}><RotateCcw className="size-4" aria-hidden /> {resetting ? "Clearing…" : "Reset demo"}</button>
        {!compact && <button onClick={lock} className={btnGhost}><LockKeyhole className="size-4" aria-hidden /> Lock</button>}
      </div>
    </header>
  );
}

export function Dashboard({ liveSessionId = null, compact = false, onReset }: { liveSessionId?: string | null; compact?: boolean; onReset?: () => void }) {
  const { api, branding } = useDemo();
  const [calls, setCalls] = useState<CallRow[] | null>(null);
  const [manual, setManual] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  usePolling(async (signal) => { if (api) setCalls((await api.calls(signal)).calls); }, 2500, api !== null, [api]);

  // Follow the live call automatically; a manual click pins a call until the next one starts.
  const liveId = liveSessionId ?? calls?.find((c) => c.status === "in_progress")?.call_id ?? null;
  const prevLive = useRef<string | null>(null);
  useEffect(() => {
    if (liveId && liveId !== prevLive.current) setManual(null);
    prevLive.current = liveId;
  }, [liveId]);
  const selectedId = manual ?? liveId ?? calls?.[0]?.call_id ?? null;
  const selected = calls?.find((c) => c.call_id === selectedId) ?? null;
  const { data, loading } = useCallEvents(api, selectedId);
  const tick = `${data?.events.length ?? 0}:${data?.call.outcome ?? ""}:${calls?.length ?? 0}`;
  const isLive = calls?.some((c) => c.status === "in_progress") ?? false;
  const jumpTo = data?.appointment ? data.appointment.slot_start.slice(0, 10) : null;

  async function reset() {
    if (!api || !window.confirm("Clear all demo calls and bookings so the next demo starts clean?")) return;
    setResetting(true);
    setNotice(null);
    try {
      await api.reset();
      setManual(null);
      setCalls([]);
      setNotice("Demo data cleared.");
      onReset?.();
    } catch (e) {
      setNotice(e instanceof ApiError ? e.friendly : "Couldn't reset.");
    } finally {
      setResetting(false);
    }
  }

  // In the narrow presenter pane show the selected call plus the two newest; "Show all" expands.
  const visible =
    compact && !showAll && calls
      ? [...calls.filter((c) => c.call_id === selectedId), ...calls.filter((c) => c.call_id !== selectedId).slice(0, 2)]
      : calls;

  const list = (
    <Card>
      <PanelHeader
        icon={<Inbox className="size-[18px]" />} title="Today's calls" subtitle={`${calls?.length ?? 0} so far`}
        right={
          <span className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${isLive ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
            <span className={`size-1.5 rounded-full ${isLive ? "animate-blink bg-emerald-500" : "bg-slate-400"}`} />
            {isLive ? "Live" : "Idle"}
          </span>
        }
      />
      <CallList calls={visible} selected={selectedId} onSelect={setManual} />
      {compact && calls && calls.length > 3 && (
        <button onClick={() => setShowAll((v) => !v)} className="w-full border-t border-line py-2.5 text-xs font-medium text-accent-strong hover:bg-slate-50">
          {showAll ? "Show fewer" : `Show all ${calls.length} calls`}
        </button>
      )}
    </Card>
  );

  const timeline = <ActivityTimeline data={data} loading={loading} hasSession={selectedId !== null} />;
  const summary = (
    <Card>
      <PanelHeader icon={<Sparkles className="size-[18px]" />} title="AI call summary" subtitle={selected?.caller ?? "What the receptionist reports to the owner."} />
      <div className="px-5 py-4 text-[14px] leading-relaxed text-slate-700 sm:px-6">
        {data?.call.summary ?? (
          <span className="text-muted">
            {!selectedId ? "Select a call to see its summary." : data?.call.status === "ended" ? "Writing the summary…" : "Generated when the call ends."}
          </span>
        )}
      </div>
    </Card>
  );
  const outcome = <AppointmentCard data={data} />;
  const notifications = <NotificationPreview data={data} />;
  const schedule = api ? <DayView api={api} timezone={branding.company.timezone} jumpTo={jumpTo} tick={tick} /> : null;

  if (compact) {
    return (
      <div className="space-y-5">
        <DashboardHeader compact onReset={reset} resetting={resetting} />
        {notice && <p role="status" className="text-sm text-slate-600">{notice}</p>}
        <StatsRow tick={tick} compact />
        {list}
        {timeline}
        {summary}
        {outcome}
        {notifications}
        {schedule}
      </div>
    );
  }
  return (
    <div className="min-h-dvh bg-canvas">
      <div className="sticky top-0 z-20 bg-white/90 backdrop-blur"><DashboardHeader onReset={reset} resetting={resetting} /></div>
      <main className="mx-auto max-w-[1400px] space-y-6 px-4 py-6 sm:px-8">
        {notice && <p role="status" className="text-sm text-slate-600">{notice}</p>}
        <StatsRow tick={tick} />
        <div className="grid items-start gap-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
          <div className="lg:sticky lg:top-24">{list}</div>
          <div className="grid min-w-0 items-start gap-6 xl:grid-cols-2">
            <div className="min-w-0 space-y-6">{timeline}{summary}</div>
            <div className="min-w-0 space-y-6">{outcome}{notifications}</div>
          </div>
        </div>
        {schedule}
      </main>
    </div>
  );
}
