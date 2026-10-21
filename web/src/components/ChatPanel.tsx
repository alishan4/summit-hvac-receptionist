"use client";

import { Send, Settings2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ApiError, type Api } from "@/lib/api";
import type { Branding } from "@/lib/types";
import { Spinner, btnGhost } from "./ui";

interface Msg {
  role: "agent" | "user";
  content: string;
  tools?: string[];
}

export function ChatPanel({
  api, branding, onSession, draft = null, onDraftUsed, fill = false,
}: {
  api: Api;
  branding: Branding;
  onSession: (id: string) => void;
  draft?: string | null;
  onDraftUsed?: () => void;
  /** fill the parent's height (used inside the widget) instead of a fixed-height box */
  fill?: boolean;
}) {
  const greeting: Msg = { role: "agent", content: branding.company.greeting };
  const [messages, setMessages] = useState<Msg[]>([greeting]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [closed, setClosed] = useState<string | null>(null);
  const chatId = useRef<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (draft) {
      setInput(draft);
      onDraftUsed?.();
    }
  }, [draft, onDraftUsed]);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  async function send() {
    const text = input.trim();
    if (!text || sending || closed) return;
    setSending(true);
    setError(null);
    try {
      if (!chatId.current) {
        const s = await api.chatCreate();
        chatId.current = s.chat_id;
        onSession(s.chat_id);
      }
      setMessages((m) => [...m, { role: "user", content: text }]);
      setInput("");
      const r = await api.chatMessage(chatId.current, text);
      setMessages((m) => [
        ...m,
        ...(r.replies.length ? r.replies : ["(no reply)"]).map((content, i) => ({
          role: "agent" as const, content, tools: i === 0 ? r.tools : undefined,
        })),
      ]);
    } catch (e) {
      if (e instanceof ApiError && (e.code === "session_expired" || e.code === "message_limit")) setClosed(e.message);
      else setError(e instanceof ApiError ? e.friendly : "Couldn't send. Try again.");
    } finally {
      setSending(false);
    }
  }

  function newChat() {
    if (chatId.current) void api.chatEnd(chatId.current).catch(() => undefined);
    chatId.current = null;
    setMessages([greeting]);
    setClosed(null);
    setError(null);
    setInput("");
  }

  return (
    <div className={fill ? "flex h-full min-h-0 flex-col gap-3" : "space-y-3"}>
      <div className={`scroll-thin space-y-3 overflow-y-auto rounded-2xl bg-slate-50/70 p-4 ${fill ? "min-h-0 flex-1" : "h-[22rem]"}`} role="log" aria-live="polite" aria-label="Conversation" tabIndex={0}>
        {messages.map((m, i) => (
          <div key={i} className={`animate-rise flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
            <p className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-[13.5px] leading-relaxed ${m.role === "user" ? "rounded-br-md bg-accent text-white" : "rounded-bl-md bg-white text-slate-800 ring-1 ring-line"}`}>
              {m.content}
            </p>
            {m.tools && m.tools.length > 0 && (
              <p className="mt-1 flex flex-wrap items-center gap-1 text-[11px] text-muted">
                <Settings2 className="size-3" /> {m.tools.map((t) => t.replace(/_/g, " ")).join(" · ")}
              </p>
            )}
          </div>
        ))}
        {sending && (
          <div className="flex items-center gap-2 text-[13px] text-muted">
            <Spinner className="size-3.5" /> Receptionist is typing…
          </div>
        )}
        <div ref={end} />
      </div>

      {closed ? (
        <div className="flex items-center justify-between gap-3 rounded-xl bg-amber-50 px-4 py-3 text-[13px] text-amber-900">
          <span>{closed}</span>
          <button onClick={newChat} className={btnGhost}>New chat</button>
        </div>
      ) : (
        <form onSubmit={(e) => { e.preventDefault(); void send(); }} className="flex items-end gap-2">
          <textarea
            value={input} onChange={(e) => setInput(e.target.value)} rows={2} maxLength={500}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); } }}
            placeholder="Type as the homeowner…  (Enter to send)"
            aria-label="Message"
            className="min-h-[3.25rem] flex-1 resize-none rounded-xl border border-line bg-white px-3.5 py-2.5 text-sm outline-none transition placeholder:text-slate-400 focus:border-accent focus:ring-4 focus:ring-accent-ring"
          />
          <button type="submit" disabled={!input.trim() || sending}
            className="grid size-11 shrink-0 place-items-center rounded-xl bg-accent text-white transition hover:bg-accent-strong disabled:opacity-40" aria-label="Send">
            <Send className="size-4" />
          </button>
        </form>
      )}
      {error && <p role="alert" className="text-[13px] text-red-600">{error}</p>}
      {!closed && messages.length > 1 && (
        <button onClick={newChat} className="text-xs text-muted underline-offset-2 hover:text-slate-800 hover:underline">Start a new chat</button>
      )}
    </div>
  );
}
