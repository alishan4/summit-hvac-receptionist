"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { isOpenNow } from "@/lib/format";
import { useDemo } from "@/lib/demo";
import { useWidget } from "../widget/AssistantWidget";

/** Time-aware (company timezone): after hours it invites the visitor to book with the assistant right now. */
export function AfterHoursBanner() {
  const { branding } = useDemo();
  const { open } = useWidget();
  const [openNow, setOpenNow] = useState<boolean | null>(null); // null until mounted: avoids a hydration mismatch

  useEffect(() => {
    const tick = () => setOpenNow(isOpenNow(branding.company.business_hours, branding.company.timezone));
    tick();
    const t = setInterval(tick, 60_000);
    return () => clearInterval(t);
  }, [branding]);

  if (openNow === null) return <div className="h-11 bg-[#1d2740]" aria-hidden />;
  const after = !openNow;
  return (
    <div role="status" className={`${after ? "bg-[#1d2740] text-white" : "bg-amber-100 text-amber-950"}`}>
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-4 gap-y-1 px-4 py-2.5 text-center text-sm sm:px-6">
        {after ? <Moon className="size-4 shrink-0 text-amber-300" aria-hidden /> : <Sun className="size-4 shrink-0 text-amber-700" aria-hidden />}
        <span className="font-medium">
          {after
            ? "It's after hours, but our assistant can book your visit right now."
            : "Our team is on the clock. Skip the phone tree: our assistant can book you in about two minutes."}
        </span>
        <button onClick={() => open()} className={`rounded-lg px-3 py-1 text-[13px] font-semibold underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 ${after ? "bg-white/10 text-white focus-visible:outline-white" : "bg-amber-900/10 focus-visible:outline-amber-900"}`}>
          Book now →
        </button>
      </div>
    </div>
  );
}
