"use client";

import { useEffect, useState } from "react";
import { AccessGate } from "@/components/AccessGate";
import { DemoApp } from "@/components/DemoApp";
import { ErrorScreen, WakingScreen } from "@/components/StatusScreens";
import { API_BASE } from "@/lib/api";
import { useBranding } from "@/lib/hooks";

const STORAGE_KEY = "demo_code";

export default function Page() {
  const state = useBranding();
  const [code, setCode] = useState<string | null | undefined>(undefined); // undefined = not read yet

  useEffect(() => {
    try {
      setCode(sessionStorage.getItem(STORAGE_KEY));
    } catch {
      setCode(null); // storage blocked: the gate still works, it just asks again after a reload
    }
  }, []);

  useEffect(() => {
    if (state.status !== "ready") return;
    document.documentElement.style.setProperty("--accent", state.branding.accent_color);
    document.title = `${state.branding.company.name} · ${state.branding.badge}`;
  }, [state]);

  if (!API_BASE) {
    return <ErrorScreen title="Demo isn't configured" message="Set NEXT_PUBLIC_API_BASE_URL to the API's URL and redeploy." />;
  }
  if (state.status === "error") {
    return <ErrorScreen title="Couldn't reach the receptionist" message={state.message} onRetry={state.retry} />;
  }
  if (state.status !== "ready" || code === undefined) {
    return <WakingScreen waking={state.status === "waking"} />;
  }

  const lock = () => {
    try { sessionStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
    setCode(null);
  };

  return code ? (
    <DemoApp branding={state.branding} code={code} onLock={lock} />
  ) : (
    <AccessGate
      branding={state.branding}
      onUnlock={(c) => {
        try { sessionStorage.setItem(STORAGE_KEY, c); } catch { /* ignore */ }
        setCode(c);
      }}
    />
  );
}
