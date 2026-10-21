"use client";

import { Lock } from "lucide-react";
import { useId, useState } from "react";
import { ApiError, createApi } from "@/lib/api";
import { useDemo } from "@/lib/demo";
import { Spinner, btnPrimary } from "./ui";

/** Inline access-code entry. The public website never needs it; only live AI sessions and the dashboard do. */
export function CodeForm({ intro, cta = "Unlock the demo" }: { intro: string; cta?: string }) {
  const { unlock } = useDemo();
  const id = useId();
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
      unlock(code);
    } catch (err) {
      setError(err instanceof ApiError ? err.friendly : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <p className="text-sm leading-relaxed text-slate-600">{intro}</p>
      <label htmlFor={id} className="block text-[13px] font-medium text-slate-700">Access code</label>
      <div className="relative">
        <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
        <input
          id={id} type="password" autoComplete="off" value={value} onChange={(e) => setValue(e.target.value)}
          placeholder="Enter the code you were given" aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-err` : undefined}
          className="w-full rounded-xl border border-line bg-white py-2.5 pl-9 pr-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-accent focus:ring-4 focus:ring-accent-ring"
        />
      </div>
      {error && <p id={`${id}-err`} role="alert" className="text-[13px] text-red-600">{error}</p>}
      <button type="submit" disabled={!value.trim() || busy} className={`${btnPrimary} w-full`}>
        {busy && <Spinner className="size-4" />}
        {busy ? "Checking…" : cta}
      </button>
    </form>
  );
}
