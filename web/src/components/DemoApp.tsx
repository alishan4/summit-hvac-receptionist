"use client";

import { RotateCcw } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { ApiError, createApi } from "@/lib/api";
import { localDate } from "@/lib/format";
import { useCallEvents } from "@/lib/hooks";
import type { Branding } from "@/lib/types";
import { ActivityTimeline } from "./ActivityTimeline";
import { AppointmentCard } from "./AppointmentCard";
import { Header } from "./Brand";
import { CallPanel, type Mode } from "./CallPanel";
import { DayView } from "./DayView";
import { NotificationPreview } from "./NotificationPreview";
import { ResultsStrip } from "./ResultsStrip";
import { btnGhost } from "./ui";

export function DemoApp({ branding, code, onLock }: { branding: Branding; code: string; onLock: () => void }) {
  const api = useMemo(() => createApi(code), [code]);
  const [session, setSession] = useState<{ id: string; kind: Mode } | null>(null);
  const [resetKey, setResetKey] = useState(0);
  const [resetting, setResetting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const { data, loading } = useCallEvents(api, session?.id ?? null);

  const handleSession = useCallback((id: string, kind: Mode) => setSession({ id, kind }), []);
  const tick = `${data?.events.length ?? 0}:${data?.call.outcome ?? ""}`; // nudges the side panels to refetch
  const jumpTo = data?.appointment ? localDate(data.appointment.slot_start) : null;

  async function reset() {
    if (!window.confirm("Clear all demo calls and bookings so the next demo starts clean?")) return;
    setResetting(true);
    setNotice(null);
    try {
      await api.reset();
      setSession(null);
      setResetKey((k) => k + 1);
      setNotice("Demo data cleared.");
    } catch (e) {
      setNotice(e instanceof ApiError ? e.friendly : "Couldn't reset.");
    } finally {
      setResetting(false);
    }
  }

  return (
    <>
      <Header branding={branding} onLock={onLock} />
      <main className="mx-auto max-w-[1320px] space-y-6 px-4 py-6 sm:px-8 sm:py-8">
        <div className="max-w-2xl animate-rise">
          <h2 className="text-balance text-2xl font-semibold tracking-tight sm:text-3xl">{branding.tagline}</h2>
          <p className="mt-2 text-[15px] text-muted">
            Talk to the receptionist on the left. Watch the business side update on the right, live.
          </p>
        </div>

        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
          <div className="scroll-thin min-w-0 pb-1 lg:sticky lg:top-24 lg:max-h-[calc(100dvh-7rem)] lg:overflow-y-auto lg:pr-1">
            <CallPanel
              key={resetKey} api={api} branding={branding} onSession={handleSession}
              serverTranscript={session?.kind === "voice" ? data?.call.transcript ?? [] : []}
            />
          </div>
          <div className="min-w-0 space-y-6">
            <ActivityTimeline data={data} loading={loading} hasSession={session !== null} />
            <AppointmentCard data={data} />
            <NotificationPreview data={data} />
            <DayView api={api} timezone={branding.company.timezone} jumpTo={jumpTo} tick={tick} />
          </div>
        </div>

        <ResultsStrip api={api} tick={tick} />

        <footer className="flex flex-wrap items-center justify-between gap-4 border-t border-line pt-5 text-[13px] text-muted">
          <ul className="space-y-1">
            {branding.demo_tips.map((t) => <li key={t}>• {t}</li>)}
          </ul>
          <div className="flex items-center gap-3">
            {notice && <span role="status" className="text-slate-600">{notice}</span>}
            <button onClick={reset} disabled={resetting} className={btnGhost}>
              <RotateCcw className="size-4" /> {resetting ? "Clearing…" : "Reset demo data"}
            </button>
          </div>
        </footer>
      </main>
    </>
  );
}
