"use client";

import { ArrowLeft, Headset, MessageCircle, Mic, Phone, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { listen, toParent } from "@/lib/bridge";
import { useDemo } from "@/lib/demo";
import { useCallEvents } from "@/lib/hooks";
import { useVoiceCall } from "@/lib/useVoiceCall";
import { ChatPanel } from "../ChatPanel";
import { CodeForm } from "../CodeForm";
import { Logo } from "../Brand";
import { BookingCard } from "./BookingCard";
import { WidgetVoice } from "./WidgetVoice";

type View = "menu" | "voice" | "chat";
interface WidgetApi { open: (view?: "voice" | "chat") => void }
const WidgetCtx = createContext<WidgetApi>({ open: () => undefined });
/** Lets any CTA on the page ("Talk to us now", "Book service") open the same assistant. */
export const useWidget = () => useContext(WidgetCtx);

export function WidgetProvider({ children }: { children: ReactNode }) {
  const { branding, api, code } = useDemo();
  const [isOpen, setOpen] = useState(false);
  const [view, setView] = useState<View>("menu");
  const [session, setSession] = useState<{ id: string; kind: "voice" | "chat" } | null>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);

  const onSession = useCallback((id: string, kind: "voice" | "chat") => {
    setSession({ id, kind });
    toParent({ type: "demo-session", id, kind }); // presenter mode: tell the dashboard next to us
  }, []);
  const voice = useVoiceCall(api, useCallback((id: string) => onSession(id, "voice"), [onSession]));
  const { data } = useCallEvents(api, session?.id ?? null);

  const open = useCallback((v?: "voice" | "chat") => {
    if (document.activeElement instanceof HTMLElement) returnFocus.current = document.activeElement;
    setOpen(true);
    if (v) setView(v);
  }, []);
  const api2 = useMemo(() => ({ open }), [open]);

  useEffect(
    () => listen((m) => {
      if (m.type === "demo-draft") { // presenter dropped a scenario script into the chat
        setOpen(true);
        setView("chat");
        setDraft(m.text);
      }
    }),
    [],
  );
  // Dialog focus management: move focus in when it opens, hand it back to the opener when it closes.
  useEffect(() => {
    if (isOpen) {
      const t = setTimeout(() => panelRef.current?.focus(), 0);
      return () => clearTimeout(t);
    }
    returnFocus.current?.focus();
    returnFocus.current = null;
  }, [isOpen]);
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen]);

  const onCall = voice.status === "live" || voice.status === "connecting" || voice.status === "creating";
  const canGoBack = view !== "menu" && !onCall;
  const maxSeconds = branding.limits.max_call_seconds;
  const name = branding.company.name;

  return (
    <WidgetCtx.Provider value={api2}>
      {children}

      <button
        onClick={() => open()}
        aria-expanded={isOpen} aria-controls="assistant-panel"
        className={`fixed bottom-4 right-4 z-40 flex items-center gap-2.5 rounded-full bg-accent py-3 pl-4 pr-5 text-sm font-semibold text-white shadow-xl shadow-black/20 transition hover:scale-[1.03] hover:bg-accent-strong focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-accent-ring sm:bottom-6 sm:right-6 ${isOpen ? "pointer-events-none scale-90 opacity-0" : ""}`}
      >
        <span className="relative grid size-6 place-items-center">
          {onCall ? <Phone className="size-5 animate-blink" aria-hidden /> : <Headset className="size-5" aria-hidden />}
          <span className="absolute -right-0.5 -top-0.5 size-2.5 rounded-full bg-emerald-400 ring-2 ring-accent" />
        </span>
        <span className="text-left leading-tight">
          {onCall ? "On a call · tap to return" : <>Need help?<span className="block text-[11px] font-medium">We answer 24/7</span></>}
        </span>
      </button>

      {/* stays mounted while closed so a live call or chat keeps going when minimised */}
      <div
        id="assistant-panel" ref={panelRef} tabIndex={-1} role="dialog" aria-label={`${name} assistant`} hidden={!isOpen}
        className="outline-none fixed inset-0 z-50 flex flex-col overflow-hidden bg-white shadow-2xl ring-1 ring-black/10 sm:inset-auto sm:bottom-6 sm:right-6 sm:h-[min(680px,calc(100dvh-3rem))] sm:w-[400px] sm:rounded-2xl"
      >
        <div className="flex shrink-0 items-center gap-3 bg-accent px-4 py-3.5 text-white">
          {canGoBack ? (
            <button onClick={() => setView("menu")} aria-label="Back" className="grid size-8 place-items-center rounded-lg hover:bg-white/15 focus-visible:outline-2 focus-visible:outline-white"><ArrowLeft className="size-5" /></button>
          ) : (
            <Logo branding={branding} size={34} className="bg-white p-0.5" />
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-semibold leading-tight">{name}</p>
            <p className="flex items-center gap-1.5 text-xs"><span className="size-1.5 rounded-full bg-emerald-300" /> AI assistant · answers instantly</p>
          </div>
          <button onClick={() => setOpen(false)} aria-label="Minimise assistant" className="grid size-8 place-items-center rounded-lg hover:bg-white/15 focus-visible:outline-2 focus-visible:outline-white"><X className="size-5" /></button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
          {!code || !api ? (
            <div className="my-auto">
              <CodeForm
                intro="This is a live AI demo. Enter the access code you were given to start a call or chat."
                cta="Unlock the assistant"
              />
            </div>
          ) : (
            <>
              <BookingCard data={data} />
              {view === "menu" && (
                <div className="flex flex-1 flex-col justify-center gap-3">
                  <p className="text-[15px] font-semibold">How would you like to reach us?</p>
                  <button onClick={() => setView("voice")} className="group flex items-center gap-4 rounded-2xl border border-line p-4 text-left transition hover:border-accent hover:bg-accent-soft/50 focus-visible:outline-2 focus-visible:outline-accent">
                    <span className="grid size-11 place-items-center rounded-xl bg-accent-soft text-accent"><Mic className="size-5" /></span>
                    <span><span className="block text-sm font-semibold">Call us</span><span className="block text-[13px] text-muted">Talk to our AI receptionist. No phone needed.</span></span>
                  </button>
                  <button onClick={() => setView("chat")} className="group flex items-center gap-4 rounded-2xl border border-line p-4 text-left transition hover:border-accent hover:bg-accent-soft/50 focus-visible:outline-2 focus-visible:outline-accent">
                    <span className="grid size-11 place-items-center rounded-xl bg-accent-soft text-accent"><MessageCircle className="size-5" /></span>
                    <span><span className="block text-sm font-semibold">Chat with us</span><span className="block text-[13px] text-muted">Type your question. We reply in seconds.</span></span>
                  </button>
                  <p className="text-center text-xs text-muted">Our assistant is an AI. In an emergency, call 911.</p>
                </div>
              )}
              <div className={view === "voice" ? "min-h-0 flex-1" : "hidden"}>
                <WidgetVoice voice={voice} maxSeconds={maxSeconds} serverTranscript={session?.kind === "voice" ? data?.call.transcript ?? [] : []} />
              </div>
              <div className={view === "chat" ? "min-h-0 flex-1" : "hidden"}>
                <ChatPanel fill api={api} branding={branding} onSession={(id) => onSession(id, "chat")} draft={draft} onDraftUsed={() => setDraft(null)} />
              </div>
            </>
          )}
        </div>
      </div>
    </WidgetCtx.Provider>
  );
}
