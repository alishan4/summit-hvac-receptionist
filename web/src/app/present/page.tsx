"use client";

import { Check, Copy, ExternalLink, Globe, LayoutDashboard, MessageSquare } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { CodeForm } from "@/components/CodeForm";
import { Logo } from "@/components/Brand";
import { Dashboard } from "@/components/dashboard/Dashboard";
import { btnGhost } from "@/components/ui";
import { listen, post } from "@/lib/bridge";
import { useDemo } from "@/lib/demo";
import type { Scenario } from "@/lib/types";

const DOT = { urgent: "bg-amber-400", emergency: "bg-red-500", neutral: "bg-slate-400" } as const;
const plain = (s: Scenario) => s.script.replace(/^"|"$/g, "");

export default function PresentPage() {
  const { api, branding } = useDemo();
  const [pane, setPane] = useState<"site" | "business">("site"); // only used below the lg breakpoint
  const [liveId, setLiveId] = useState<string | null>(null);
  const [frameKey, setFrameKey] = useState(0);
  const [openScenario, setOpenScenario] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const frame = useRef<HTMLIFrameElement>(null);

  useEffect(() => { document.title = `Presenter · ${branding.company.name}`; }, [branding]);
  useEffect(() => listen((m) => { if (m.type === "demo-session") setLiveId(m.id); }), []);

  const sendToChat = useCallback((s: Scenario) => post(frame.current?.contentWindow, { type: "demo-draft", text: plain(s) }), []);
  async function copy(s: Scenario) {
    try {
      await navigator.clipboard.writeText(plain(s));
      setCopied(s.id);
      setTimeout(() => setCopied(null), 1500);
    } catch { /* clipboard blocked: the script is shown on screen anyway */ }
  }
  const afterReset = () => { setLiveId(null); setFrameKey((k) => k + 1); }; // fresh widget = fresh chat

  const active = branding.scenarios.find((s) => s.id === openScenario);
  // Locked: the access-code form lives in the business pane, so on phones that pane must be the one showing.
  const shown = api ? pane : "business";

  return (
    <div className="flex h-dvh flex-col bg-canvas">
      <header className="shrink-0 border-b border-line bg-white">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <Logo branding={branding} size={28} />
            <span className="hidden text-sm font-semibold sm:inline">Presenter mode</span>
          </div>

          <div role="tablist" aria-label="View" className="grid flex-1 grid-cols-2 gap-1 rounded-xl bg-slate-100 p-1 lg:hidden">
            {([["site", "Homeowner view", <Globe key="g" className="size-4" />], ["business", "Business view", <LayoutDashboard key="l" className="size-4" />]] as const).map(([id, label, icon]) => (
              <button key={id} role="tab" aria-selected={shown === id} onClick={() => setPane(id)}
                className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-[13px] font-medium sm:px-3 sm:text-sm ${shown === id ? "bg-white shadow-sm" : "text-muted"}`}>{icon}{label}</button>
            ))}
          </div>

          <ul className="scroll-thin order-last flex w-full min-w-0 items-center gap-2 overflow-x-auto pb-1 lg:order-none lg:w-auto lg:flex-1 lg:pb-0" aria-label="Scenarios">
            {branding.scenarios.map((s) => (
              <li key={s.id} className={`flex shrink-0 items-center overflow-hidden rounded-xl border bg-white text-[13px] ${openScenario === s.id ? "border-accent ring-2 ring-accent-ring" : "border-line"}`}>
                <button onClick={() => setOpenScenario(openScenario === s.id ? null : s.id)} aria-expanded={openScenario === s.id}
                  className="flex items-center gap-2 px-3 py-1.5 font-medium hover:bg-slate-50">
                  <span className={`size-2 rounded-full ${DOT[s.tone]}`} />{s.title}
                </button>
                <button onClick={() => copy(s)} aria-label={`Copy script: ${s.title}`} title="Copy script" className="border-l border-line px-2.5 py-2 text-slate-500 hover:bg-slate-50 hover:text-slate-900">
                  {copied === s.id ? <Check className="size-3.5 text-emerald-600" /> : <Copy className="size-3.5" />}
                </button>
                <button onClick={() => sendToChat(s)} aria-label={`Send to chat: ${s.title}`} title="Put in the website chat" className="border-l border-line px-2.5 py-2 text-slate-500 hover:bg-slate-50 hover:text-slate-900">
                  <MessageSquare className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>

          <div className="ml-auto hidden items-center gap-2 sm:flex lg:ml-0">
            <Link href="/dashboard" target="_blank" className={btnGhost}><ExternalLink className="size-4" aria-hidden /> Dashboard</Link>
          </div>
        </div>
        {active && (
          <div className="animate-rise border-t border-line bg-accent-soft/50 px-4 py-2.5 text-[15px] italic leading-relaxed text-slate-800">
            <span className="mr-2 text-xs font-bold uppercase not-italic tracking-wider text-accent-strong">Say this</span>{active.script}
          </div>
        )}
      </header>

      <main className="grid min-h-0 flex-1 lg:grid-cols-[60fr_40fr]">
        <section aria-label="Homeowner view" className={`min-h-0 flex-col border-line lg:flex lg:border-r ${shown === "site" ? "flex" : "hidden"}`}>
          <div className="flex shrink-0 items-center gap-3 bg-slate-100 px-4 py-2">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-600">Homeowner view</h2>
            <span className="truncate rounded-md bg-white px-3 py-1 text-xs text-slate-600 ring-1 ring-line">https://{branding.site.domain}</span>
          </div>
          <iframe ref={frame} key={frameKey} src="/" title={`${branding.company.name} website`} className="min-h-0 w-full flex-1 border-0 bg-white" />
        </section>

        <section aria-label="Business view" className={`min-h-0 flex-col lg:flex ${shown === "business" ? "flex" : "hidden"}`}>
          <div className="flex shrink-0 items-center gap-3 bg-slate-100 px-4 py-2">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-600">Business view</h2>
            <span className="text-xs text-slate-600">live, updates as the call happens</span>
          </div>
          <div className="scroll-thin min-h-0 flex-1 overflow-y-auto p-4">
            {api ? (
              <Dashboard compact liveSessionId={liveId} onReset={afterReset} />
            ) : (
              <div className="mx-auto mt-10 max-w-sm rounded-2xl border border-line bg-white p-6 shadow-card">
                <CodeForm intro="Enter the access code once: it unlocks both halves." cta="Start presenting" />
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
