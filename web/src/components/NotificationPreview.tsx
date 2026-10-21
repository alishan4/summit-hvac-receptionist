"use client";

import { BellRing, Mail, Smartphone } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { CallEvents, EmailPreview, SmsPreview } from "@/lib/types";
import { Card, Chip, Empty, PanelHeader } from "./ui";

type TabId = "sms" | "summary" | "alert";

function Sms({ sms, label }: { sms: SmsPreview; label: string }) {
  return (
    <div className="mx-auto w-full max-w-[19rem] animate-pop rounded-[1.75rem] border border-slate-300 bg-slate-50 p-3 shadow-inner">
      <p className="pb-2 text-center text-[11px] font-medium text-muted">{label} · {sms.to}</p>
      <p className="whitespace-pre-wrap rounded-2xl rounded-bl-md bg-white px-3.5 py-2.5 text-[13px] leading-relaxed text-slate-800 ring-1 ring-line">{sms.body}</p>
      <p className="px-1 pt-1.5 text-right text-[10px] text-muted">{sms.sent ? "Delivered" : "Queued"}</p>
    </div>
  );
}

function Email({ mail, draft }: { mail: EmailPreview; draft?: boolean }) {
  return (
    <div className="animate-pop overflow-hidden rounded-xl border border-line">
      <div className="space-y-1 border-b border-line bg-slate-50/80 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm font-semibold leading-snug">{mail.subject}</p>
          <Chip tone={draft ? "warn" : "success"}>{draft ? "Draft" : mail.sent ? "Sent" : "Ready"}</Chip>
        </div>
        <p className="text-xs text-muted">To: {mail.to}</p>
      </div>
      <pre tabIndex={0} aria-label="Email body" className="scroll-thin max-h-72 overflow-auto whitespace-pre-wrap px-4 py-3 font-sans text-[13px] leading-relaxed text-slate-700">{mail.body}</pre>
    </div>
  );
}

export function NotificationPreview({ data }: { data: CallEvents | null }) {
  const n = data?.notifications;
  const tabs = useMemo(
    () => [
      n?.confirmation_sms && { id: "sms" as const, label: "Caller text", icon: <Smartphone className="size-4" /> },
      n?.owner_alert && { id: "alert" as const, label: "Owner alert", icon: <BellRing className="size-4" /> },
      n?.owner_summary && { id: "summary" as const, label: "Owner email", icon: <Mail className="size-4" /> },
    ].filter(Boolean) as { id: TabId; label: string; icon: React.ReactNode }[],
    [n],
  );
  const [picked, setPicked] = useState<TabId | null>(null);
  const newest = n?.owner_alert ? "alert" : n?.confirmation_sms ? "sms" : "summary";

  // Jump to whichever notification just appeared, unless the presenter already chose a tab that exists.
  useEffect(() => setPicked(null), [newest]);
  const active = (picked && tabs.some((t) => t.id === picked) ? picked : tabs.some((t) => t.id === newest) ? newest : tabs[0]?.id) ?? null;

  return (
    <Card>
      <PanelHeader icon={<BellRing className="size-[18px]" />} title="Notifications" subtitle="Generated from this call's real data." />
      <div className="space-y-4 px-5 py-5 sm:px-6">
        {tabs.length === 0 ? (
          <Empty icon={<Mail className="size-5" />} title="Nothing sent yet" hint="The caller's confirmation text and the owner's email or emergency alert preview here." />
        ) : (
          <>
            <div role="tablist" className="flex gap-1 rounded-xl bg-slate-100 p-1">
              {tabs.map((t) => (
                <button key={t.id} role="tab" aria-selected={active === t.id} onClick={() => setPicked(t.id)}
                  className={`inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg py-1.5 text-[13px] font-medium transition ${active === t.id ? "bg-white shadow-sm" : "text-muted hover:text-slate-800"} ${t.id === "alert" ? "text-red-700" : ""}`}>
                  {t.icon} {t.label}
                </button>
              ))}
            </div>
            {active === "sms" && n?.confirmation_sms && <Sms sms={n.confirmation_sms} label="Text to caller" />}
            {active === "summary" && n?.owner_summary && <Email mail={n.owner_summary} draft={!n.owner_summary.final} />}
            {active === "alert" && n?.owner_alert && (
              <div className="space-y-4">
                <Sms sms={n.owner_alert.sms} label="Text to owner" />
                <Email mail={n.owner_alert.email} />
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  );
}
