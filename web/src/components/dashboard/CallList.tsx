"use client";

import { MessageSquare, Mic, PhoneIncoming } from "lucide-react";
import type { CallRow } from "@/lib/types";
import { Chip, Empty } from "../ui";

const OUTCOME: Record<string, { label: string; tone: "success" | "danger" | "warn" | "neutral" }> = {
  booked: { label: "Booked", tone: "success" },
  emergency: { label: "Emergency", tone: "danger" },
  callback: { label: "Callback", tone: "warn" },
  info_only: { label: "Info only", tone: "neutral" },
  abandoned: { label: "Hung up", tone: "neutral" },
};
const CHANNEL = {
  web: { label: "Website call", icon: <Mic className="size-3.5" /> },
  chat: { label: "Website chat", icon: <MessageSquare className="size-3.5" /> },
  phone: { label: "Phone call", icon: <PhoneIncoming className="size-3.5" /> },
} as const;

const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

export function CallList({ calls, selected, onSelect }: { calls: CallRow[] | null; selected: string | null; onSelect: (id: string) => void }) {
  if (calls === null) return <div className="space-y-2 p-4">{[0, 1, 2].map((i) => <div key={i} className="skeleton h-16 rounded-xl" />)}</div>;
  if (calls.length === 0) {
    return <div className="p-4"><Empty icon={<PhoneIncoming className="size-5" />} title="No calls yet today" hint="Calls and chats from the website show up here the moment they start." /></div>;
  }
  return (
    <ul className="scroll-thin max-h-[26rem] divide-y divide-line overflow-y-auto" aria-label="Today's calls" tabIndex={0}>
      {calls.map((c) => {
        const ch = CHANNEL[c.channel];
        const out = c.outcome ? OUTCOME[c.outcome] : null;
        const live = c.status === "in_progress";
        return (
          <li key={c.call_id}>
            <button
              onClick={() => onSelect(c.call_id)} aria-current={selected === c.call_id}
              className={`flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-slate-50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent ${selected === c.call_id ? "bg-accent-soft/60" : ""}`}
            >
              <span className="grid size-9 shrink-0 place-items-center rounded-full bg-slate-100 text-slate-600">{ch.icon}</span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="truncate text-sm font-semibold">{c.caller ?? (c.channel === "phone" ? "Unknown caller" : "Website visitor")}</span>
                  {live && <span className="flex items-center gap-1 rounded-full bg-emerald-50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-700"><span className="size-1.5 animate-blink rounded-full bg-emerald-500" />Live</span>}
                </span>
                <span className="block truncate text-xs text-muted">{ch.label} · {time(c.started_at)}{c.appointment ? ` · ${c.appointment}` : ""}</span>
              </span>
              {out ? <Chip tone={out.tone}>{out.label}</Chip> : <Chip>{live ? "In progress" : "Ended"}</Chip>}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
