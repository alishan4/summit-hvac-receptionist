"use client";

import { MessageSquare, Mic, PhoneCall } from "lucide-react";
import { useCallback, useState } from "react";
import type { Api } from "@/lib/api";
import type { Branding, Turn } from "@/lib/types";
import { ChatPanel } from "./ChatPanel";
import { ScenarioCards } from "./ScenarioCards";
import { Card, PanelHeader } from "./ui";
import { VoicePanel } from "./VoicePanel";

export type Mode = "voice" | "chat";

export function CallPanel({
  api, branding, onSession, serverTranscript,
}: {
  api: Api;
  branding: Branding;
  onSession: (id: string, kind: Mode) => void;
  serverTranscript: Turn[];
}) {
  const [mode, setMode] = useState<Mode>("voice");
  const [draft, setDraft] = useState<string | null>(null);
  const clearDraft = useCallback(() => setDraft(null), []);

  const tabs: { id: Mode; label: string; icon: React.ReactNode }[] = [
    { id: "voice", label: "Voice call", icon: <Mic className="size-4" /> },
    { id: "chat", label: "Text chat", icon: <MessageSquare className="size-4" /> },
  ];

  return (
    <Card>
      <PanelHeader icon={<PhoneCall className="size-[18px]" />} title="Call the receptionist" subtitle="You're the homeowner. Talk or type." />
      <div className="space-y-6 px-5 py-5 sm:px-6">
        <div role="tablist" aria-label="Contact method" className="grid grid-cols-2 gap-1 rounded-xl bg-slate-100 p-1">
          {tabs.map((t) => (
            <button
              key={t.id} role="tab" aria-selected={mode === t.id} onClick={() => setMode(t.id)}
              className={`inline-flex items-center justify-center gap-2 rounded-lg py-2 text-sm font-medium transition ${mode === t.id ? "bg-white text-ink shadow-sm" : "text-muted hover:text-slate-800"}`}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* both stay mounted so switching tabs never drops a live call or chat */}
        <div hidden={mode !== "voice"}>
          <VoicePanel api={api} maxSeconds={branding.limits.max_call_seconds} onSession={(id) => onSession(id, "voice")} serverTranscript={serverTranscript} />
        </div>
        <div hidden={mode !== "chat"}>
          <ChatPanel api={api} branding={branding} onSession={(id) => onSession(id, "chat")} draft={draft} onDraftUsed={clearDraft} />
        </div>

        <ScenarioCards scenarios={branding.scenarios} onUse={mode === "chat" ? setDraft : undefined} />
      </div>
    </Card>
  );
}
