import { CalendarCheck, Check, PhoneForwarded, ShieldAlert } from "lucide-react";
import type { CallEvents } from "@/lib/types";

/** What the homeowner sees inside the widget once the receptionist has done something for them. */
export function BookingCard({ data }: { data: CallEvents | null }) {
  const appt = data?.appointment;
  const outcome = data?.call.outcome;

  if (appt) {
    return (
      <div key={appt.id} role="status" className="animate-pop rounded-xl border border-emerald-200 bg-emerald-50 p-3.5">
        <p className="flex items-center gap-2 text-sm font-semibold text-emerald-900">
          <span className="grid size-6 place-items-center rounded-full bg-emerald-600 text-white"><Check className="size-3.5" /></span>
          You&apos;re booked: {appt.short_label} · {appt.address}
        </p>
        <p className="mt-1 flex items-center gap-1.5 pl-8 text-[13px] text-emerald-900">
          <CalendarCheck className="size-3.5" aria-hidden />
          {appt.sms_sent ? `Confirmation text sent to ${appt.phone}` : "A confirmation text is on its way"}
        </p>
      </div>
    );
  }
  if (outcome === "emergency") {
    return (
      <div role="alert" className="animate-pop rounded-xl border border-red-200 bg-red-50 p-3.5">
        <p className="flex items-center gap-2 text-sm font-semibold text-red-900"><ShieldAlert className="size-4" aria-hidden /> Safety first</p>
        <p className="mt-1 text-[13px] leading-relaxed text-red-900">
          Leave the home now and call 911 and your gas utility from outside. Our owner has been alerted.
        </p>
      </div>
    );
  }
  if (outcome === "callback") {
    return (
      <div role="status" className="animate-pop rounded-xl border border-amber-200 bg-amber-50 p-3.5">
        <p className="flex items-center gap-2 text-sm font-semibold text-amber-900"><PhoneForwarded className="size-4" aria-hidden /> Message received</p>
        <p className="mt-1 text-[13px] text-amber-900">Someone from the team will call you back.</p>
      </div>
    );
  }
  return null;
}
