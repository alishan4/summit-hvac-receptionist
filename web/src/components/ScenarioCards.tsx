"use client";

import { Check, ChevronDown, Copy, Flame, Snowflake, MapPinOff, Send } from "lucide-react";
import { useState } from "react";
import type { Scenario } from "@/lib/types";

const TONE_STYLE = {
  urgent: { bar: "bg-amber-400", icon: <Snowflake className="size-4" />, chip: "bg-amber-50 text-amber-800" },
  emergency: { bar: "bg-red-500", icon: <Flame className="size-4" />, chip: "bg-red-50 text-red-700" },
  neutral: { bar: "bg-slate-400", icon: <MapPinOff className="size-4" />, chip: "bg-slate-100 text-slate-700" },
} as const;

export function ScenarioCards({ scenarios, onUse }: { scenarios: Scenario[]; onUse?: (script: string) => void }) {
  const [open, setOpen] = useState<string | null>(scenarios[0]?.id ?? null);
  const [copied, setCopied] = useState<string | null>(null);

  async function copy(s: Scenario) {
    try {
      await navigator.clipboard.writeText(s.script.replace(/^"|"$/g, ""));
      setCopied(s.id);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      /* clipboard blocked: the script is still on screen */
    }
  }

  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">Try a scenario</h3>
      <ul className="space-y-2">
        {scenarios.map((s) => {
          const t = TONE_STYLE[s.tone];
          const isOpen = open === s.id;
          return (
            <li key={s.id} className="overflow-hidden rounded-xl border border-line bg-white transition hover:border-slate-300">
              <button
                onClick={() => setOpen(isOpen ? null : s.id)} aria-expanded={isOpen}
                className="flex w-full items-center gap-3 px-4 py-3 text-left"
              >
                <span className={`w-1 self-stretch rounded-full ${t.bar}`} />
                <span className={`grid size-8 place-items-center rounded-lg ${t.chip}`}>{t.icon}</span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold leading-tight">{s.title}</span>
                  <span className="block text-xs text-muted">{s.subtitle}</span>
                </span>
                <ChevronDown className={`size-4 text-slate-400 transition ${isOpen ? "rotate-180" : ""}`} />
              </button>
              {isOpen && (
                <div className="animate-rise border-t border-line bg-slate-50/60 px-4 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">Say this</p>
                  <p className="mt-1 text-[13.5px] italic leading-relaxed text-slate-700">{s.script}</p>
                  <div className="mt-3 flex gap-2">
                    <button onClick={() => copy(s)} className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50">
                      {copied === s.id ? <Check className="size-3.5 text-emerald-600" /> : <Copy className="size-3.5" />}
                      {copied === s.id ? "Copied" : "Copy"}
                    </button>
                    {onUse && (
                      <button onClick={() => onUse(s.script.replace(/^"|"$/g, ""))} className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-accent-strong">
                        <Send className="size-3.5" /> Use in chat
                      </button>
                    )}
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
