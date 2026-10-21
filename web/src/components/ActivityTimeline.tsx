import {
  CalendarCheck, CheckCircle2, ClipboardList, MailCheck, MapPin, MessageSquareText, PhoneCall, PhoneOff,
  PhoneForwarded, Radar, ShieldAlert, Siren, TriangleAlert, Activity,
} from "lucide-react";
import type { ReactNode } from "react";
import type { CallEvents, TimelineEvent } from "@/lib/types";
import { Card, Empty, PanelHeader, Spinner, TONE } from "./ui";

const ICON: Record<string, ReactNode> = {
  call_started: <PhoneCall className="size-4" />,
  service_area_checked: <MapPin className="size-4" />,
  slots_found: <Radar className="size-4" />,
  appointment_booked: <CalendarCheck className="size-4" />,
  booking_failed: <TriangleAlert className="size-4" />,
  confirmation_sms_sent: <MessageSquareText className="size-4" />,
  emergency_flagged: <ShieldAlert className="size-4" />,
  emergency_alert_sent: <Siren className="size-4" />,
  callback_requested: <PhoneForwarded className="size-4" />,
  summary_email_sent: <MailCheck className="size-4" />,
  summary_ready: <ClipboardList className="size-4" />,
  call_ended: <PhoneOff className="size-4" />,
};

function time(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" });
}

function Step({ ev, last }: { ev: TimelineEvent; last: boolean }) {
  const t = TONE[ev.tone];
  return (
    <li className="animate-rise relative flex gap-3 pb-5 last:pb-0">
      {!last && <span className="absolute left-[15px] top-8 h-[calc(100%-1.5rem)] w-px bg-line" aria-hidden />}
      <span className={`relative z-10 grid size-8 shrink-0 place-items-center rounded-full ring-4 ring-white ${t.chip}`}>
        {ICON[ev.kind] ?? <CheckCircle2 className="size-4" />}
      </span>
      <div className="min-w-0 flex-1 pt-0.5">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-sm font-semibold leading-tight">{ev.label}</p>
          <time className="shrink-0 font-mono text-[11px] text-muted" dateTime={ev.at}>{time(ev.at)}</time>
        </div>
        {ev.sub && <p className="mt-0.5 text-[13px] leading-snug text-muted">{ev.sub}</p>}
      </div>
    </li>
  );
}

function Pending({ children }: { children: ReactNode }) {
  return (
    <li className="relative flex items-center gap-3 pt-5 text-[13px] text-muted">
      <span className="grid size-8 place-items-center rounded-full border border-dashed border-slate-300 bg-white">
        <Spinner className="size-3.5 text-slate-400" />
      </span>
      <span className="animate-blink">{children}</span>
    </li>
  );
}

export function ActivityTimeline({ data, loading, hasSession }: { data: CallEvents | null; loading: boolean; hasSession: boolean }) {
  const events = data?.events ?? [];
  const ended = data?.call.status === "ended";
  const waitingSummary = ended && !data?.call.summary_ready;
  const inProgress = hasSession && !ended;

  return (
    <Card>
      <PanelHeader icon={<Activity className="size-[18px]" />} title="Live activity" subtitle="Every step the receptionist takes, as it happens." />
      <div className="px-5 py-5 sm:px-6">
        {events.length === 0 && !loading && !hasSession && (
          <Empty icon={<Activity className="size-5" />} title="Waiting for a call" hint="Start a voice call or text chat on the left and the workflow appears here, step by step." />
        )}
        {events.length === 0 && (loading || hasSession) && (
          <ul><Pending>Connecting to the live feed…</Pending></ul>
        )}
        {events.length > 0 && (
          <ol aria-live="polite">
            {events.map((ev, i) => (
              <Step key={ev.id} ev={ev} last={i === events.length - 1 && !inProgress && !waitingSummary} />
            ))}
            {inProgress && <Pending>Listening for the next step…</Pending>}
            {waitingSummary && <Pending>Writing the call summary…</Pending>}
          </ol>
        )}
      </div>
    </Card>
  );
}
