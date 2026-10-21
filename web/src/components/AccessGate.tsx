"use client";

import { Lock } from "lucide-react";
import { useState } from "react";
import { ApiError, createApi } from "@/lib/api";
import type { Branding } from "@/lib/types";
import { Logo } from "./Brand";
import { FullScreen } from "./StatusScreens";
import { Spinner, btnPrimary } from "./ui";

export function AccessGate({ branding, onUnlock }: { branding: Branding; onUnlock: (code: string) => void }) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const code = value.trim();
    if (!code || busy) return;
    setBusy(true);
    setError(null);
    try {
      await createApi(code).session();
      onUnlock(code);
    } catch (err) {
      setError(err instanceof ApiError ? err.friendly : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <FullScreen>
      <form onSubmit={submit} className="animate-rise w-full max-w-sm rounded-2xl border border-line bg-white p-8 shadow-card">
        <div className="flex flex-col items-center text-center">
          <Logo branding={branding} size={52} />
          <h1 className="mt-4 text-xl font-semibold tracking-tight">{branding.company.name}</h1>
          <p className="mt-1 text-sm text-muted">{branding.badge}</p>
        </div>
        <label htmlFor="code" className="mt-7 block text-[13px] font-medium text-slate-700">
          Access code
        </label>
        <div className="relative mt-1.5">
          <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
          <input
            id="code" type="password" autoFocus autoComplete="off" value={value}
            onChange={(e) => setValue(e.target.value)} placeholder="Enter the code you were given"
            aria-invalid={error ? true : undefined} aria-describedby={error ? "code-error" : undefined}
            className="w-full rounded-xl border border-line bg-white py-2.5 pl-9 pr-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-accent focus:ring-4 focus:ring-accent-ring"
          />
        </div>
        {error && (
          <p id="code-error" role="alert" className="mt-2 text-[13px] text-red-600">
            {error}
          </p>
        )}
        <button type="submit" disabled={!value.trim() || busy} className={`${btnPrimary} mt-5 w-full`}>
          {busy ? <Spinner className="size-4" /> : null}
          {busy ? "Checking…" : "Open the demo"}
        </button>
        <p className="mt-4 text-center text-xs text-muted">The code protects the live AI session from public use.</p>
      </form>
    </FullScreen>
  );
}
