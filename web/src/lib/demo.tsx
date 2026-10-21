"use client";

import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useState, type ReactNode } from "react";
import { ErrorScreen, WakingScreen } from "@/components/StatusScreens";
import { API_BASE, createApi, type Api } from "./api";
import { listen, toFrames, toParent } from "./bridge";
import { useBranding } from "./hooks";
import type { Branding } from "./types";

const STORAGE_KEY = "demo_code";

interface DemoCtx {
  branding: Branding;
  /** null until the visitor enters the access code (the website itself never needs it). */
  code: string | null;
  api: Api | null;
  unlock: (code: string) => void;
  lock: () => void;
}

const Ctx = createContext<DemoCtx | null>(null);

export function useDemo(): DemoCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("useDemo must be used inside <DemoProvider>");
  return v;
}

function readCode(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null; // storage blocked: the code is kept in memory only
  }
}

function writeCode(code: string | null) {
  try {
    if (code) sessionStorage.setItem(STORAGE_KEY, code);
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/** Loads white-label branding (riding out a cold start), applies the accent colour, owns the access code. */
export function DemoProvider({ children }: { children: ReactNode }) {
  const state = useBranding();
  const [code, setCode] = useState<string | null>(null);

  useEffect(() => {
    setCode(readCode());
    return listen((m) => {
      if (m.type === "demo-code") {
        writeCode(m.code);
        setCode(m.code);
      }
    });
  }, []);

  // layout effect: the accent must be in place before the first paint (no flash of the default colour)
  useLayoutEffect(() => {
    if (state.status === "ready") document.documentElement.style.setProperty("--accent", state.branding.accent_color);
  }, [state]);

  const unlock = useCallback((c: string) => {
    writeCode(c);
    setCode(c);
    toParent({ type: "demo-code", code: c });
    toFrames({ type: "demo-code", code: c });
  }, []);
  const lock = useCallback(() => {
    writeCode(null);
    setCode(null);
    toParent({ type: "demo-code", code: null });
    toFrames({ type: "demo-code", code: null });
  }, []);

  const api = useMemo(() => (code ? createApi(code) : null), [code]);
  const branding = state.status === "ready" ? state.branding : null;
  const value = useMemo(() => (branding ? { branding, code, api, unlock, lock } : null), [branding, code, api, unlock, lock]);

  if (!API_BASE) {
    return <ErrorScreen title="Demo isn't configured" message="Set NEXT_PUBLIC_API_BASE_URL to the API's URL and redeploy." />;
  }
  if (state.status === "error") {
    return <ErrorScreen title="Couldn't reach the receptionist" message={state.message} onRetry={state.retry} />;
  }
  if (!value) return <WakingScreen waking={state.status === "waking"} />;
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
