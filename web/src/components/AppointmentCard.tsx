import { CalendarCheck, Check, Clock, MapPin, PhoneForwarded, ShieldAlert, Wrench } from "lucide-react";
import type { CallEvents } from "@/lib/types";
import { Card, Chip, Empty, PanelHeader } from "./ui";

function Row({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 text-sm">
      <span className="mt-0.5 text-slate-500">{icon}</span>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export function AppointmentCard({ data }: { data: CallEvents | null }) {
  const appt = data?.appointment;
  const outcome = data?.call.outcome;

  return (
    <Card>
      <PanelHeader icon={<CalendarCheck className="size-[18px]" />} title="Outcome"
        subtitle="What lands on the business's side." />
      <div className="px-5 py-5 sm:px-6">
        {appt ? (
          <div key={appt.id} className="animate-pop space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-lg font-semibold leading-tight tracking-tight">{appt.customer_name}</p>
                <p className="text-[13px] text-muted">{appt.phone}</p>
              </div>
              <Chip tone={appt.urgency === "urgent" ? "danger" : "neutral"}>
                {appt.urgency === "urgent" ? "Urgent" : "Routine"}
              </Chip>
            </div>
            <div className="space-y-3 rounded-xl bg-slate-50/80 p-4">
              <Row icon={<Clock className="size-4" />}>
                <p className="font-medium">{appt.window_label}</p>
                <p className="text-[13px] text-muted">2-hour arrival window</p>
              </Row>
              <Row icon={<MapPin className="size-4" />}>
                <p className="font-medium">{appt.address}</p>
                <p className="text-[13px] text-muted">ZIP {appt.zip}</p>
              </Row>
              <Row icon={<Wrench className="size-4" />}>
                <p className="font-medium">{appt.issue_label}</p>
                {(appt.issue_description || appt.system_info) && (
                  <p className="text-[13px] text-muted">{[appt.issue_description, appt.system_info].filter(Boolean).join(" · ")}</p>
                )}
              </Row>
            </div>
            <div className="flex flex-wrap gap-2">
              {appt.added_to_calendar && <Chip tone="success"><Check className="size-3.5" /> Added to calendar</Chip>}
              {appt.sms_sent && <Chip tone="success"><Check className="size-3.5" /> Confirmation text sent</Chip>}
            </div>
          </div>
        ) : outcome === "emergency" ? (
          <div className="animate-pop rounded-xl border border-red-200 bg-red-50 p-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-red-800"><ShieldAlert className="size-4" /> Safety emergency. Nothing was booked.</p>
            <p className="mt-1.5 text-[13px] leading-relaxed text-red-800">
              The caller was told to leave the home and call 911 and the gas utility. The owner was alerted instantly.
            </p>
          </div>
        ) : outcome === "callback" ? (
          <div className="animate-pop rounded-xl border border-amber-200 bg-amber-50 p-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-amber-900"><PhoneForwarded className="size-4" /> Callback requested</p>
            <p className="mt-1.5 text-[13px] leading-relaxed text-amber-900">A message was saved for the team to follow up.</p>
          </div>
        ) : outcome === "info_only" || outcome === "abandoned" ? (
          <div className="animate-pop rounded-xl bg-slate-50 p-4 text-sm text-slate-700">
            {outcome === "abandoned" ? "The caller left before booking. No appointment was made." : "Information only. No appointment was needed."}
          </div>
        ) : (
          <Empty icon={<CalendarCheck className="size-5" />} title="No appointment yet" hint="Booked jobs show customer, address, issue, urgency and arrival window here." />
        )}
      </div>
    </Card>
  );
}
