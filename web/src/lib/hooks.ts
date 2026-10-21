"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, fetchBranding, type Api } from "./api";
import type { Branding, CallEvents } from "./types";

/** Runs `fn` every `ms` while `enabled`, immediately first. Aborts in-flight work on cleanup. */
export function usePolling(fn: (signal: AbortSignal) => Promise<void>, ms: number, enabled: boolean, deps: unknown[] = []) {
  const fnRef = useRef(fn);
  fnRef.current = fn;
  useEffect(() => {
    if (!enabled) return;
    const ctl = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        await fnRef.current(ctl.signal);
      } catch {
        /* transient: next tick retries */
      }
      if (!ctl.signal.aborted) timer = setTimeout(tick, ms);
    };
    void tick();
    return () => {
      ctl.abort();
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, enabled, ...deps]);
}

export type BrandingState =
  | { status: "loading" | "waking" }
  | { status: "ready"; branding: Branding }
  | { status: "error"; message: string };

/** Loads white-label branding, riding out a serverless cold start ("Waking up the receptionist..."). */
export function useBranding(): BrandingState & { retry: () => void } {
  const [state, setState] = useState<BrandingState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setState({ status: "loading" });
    const wake = setTimeout(() => setState((s) => (s.status === "loading" ? { status: "waking" } : s)), 1500);
    (async () => {
      let last: unknown;
      for (let i = 0; i < 6 && !ctl.signal.aborted; i++) {
        try {
          const branding = await fetchBranding(ctl.signal);
          if (!ctl.signal.aborted) setState({ status: "ready", branding });
          return;
        } catch (e) {
          if (e instanceof DOMException && e.name === "AbortError") return;
          last = e;
          await new Promise((r) => setTimeout(r, 2000));
        }
      }
      if (!ctl.signal.aborted)
        setState({ status: "error", message: last instanceof ApiError ? last.friendly : "Couldn't load the demo." });
    })();
    return () => {
      ctl.abort();
      clearTimeout(wake);
    };
  }, [attempt]);

  return { ...state, retry: () => setAttempt((n) => n + 1) };
}

/**
 * Polls the live timeline for one call/chat (every 1.5s while it's running, and until the owner summary
 * lands after it ends). Keeps the last good snapshot so the panel never flickers empty.
 */
export function useCallEvents(api: Api, callId: string | null) {
  const [data, setData] = useState<CallEvents | null>(null);
  const [loading, setLoading] = useState(false);
  const endedAt = useRef<number | null>(null);

  useEffect(() => {
    setData(null);
    endedAt.current = null;
    setLoading(callId !== null);
  }, [callId]);

  const finished = data?.call.status === "ended" && (data.call.summary_ready || (endedAt.current !== null && Date.now() - endedAt.current > 90_000));
  usePolling(
    async (signal) => {
      if (!callId) return;
      try {
        const next = await api.events(callId, signal);
        if (next.call.status === "ended" && endedAt.current === null) endedAt.current = Date.now();
        setData(next);
      } catch (e) {
        if (!(e instanceof ApiError && e.status === 404)) throw e; // 404 = not created yet: keep waiting
      } finally {
        setLoading(false);
      }
    },
    1500,
    callId !== null && !finished,
    [callId, api],
  );

  return { data, loading };
}
