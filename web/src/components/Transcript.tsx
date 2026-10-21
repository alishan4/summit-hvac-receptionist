"use client";

import { Bot, User } from "lucide-react";
import { useEffect, useRef } from "react";
import type { Turn } from "@/lib/types";

export function Transcript({
  turns, empty, note, className = "max-h-64 min-h-28",
}: { turns: Turn[]; empty: string; note?: string; className?: string }) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className={`scroll-thin space-y-3 overflow-y-auto rounded-xl bg-slate-50/70 p-4 ${className}`} role="log" aria-live="polite" aria-label="Call transcript" tabIndex={0}>
        {turns.length === 0 && <p className="py-6 text-center text-[13px] text-muted">{empty}</p>}
        {turns.map((t, i) => (
          <div key={i} className={`animate-rise flex gap-2.5 ${t.role === "user" ? "flex-row-reverse" : ""}`}>
            <span className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-full ${t.role === "user" ? "bg-slate-200 text-slate-600" : "bg-accent-soft text-accent"}`}>
              {t.role === "user" ? <User className="size-3.5" /> : <Bot className="size-3.5" />}
            </span>
            <p className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-[13.5px] leading-relaxed ${t.role === "user" ? "rounded-tr-md bg-accent text-white" : "rounded-tl-md bg-white text-slate-800 ring-1 ring-line"}`}>
              {t.content}
            </p>
          </div>
        ))}
        <div ref={end} />
      </div>
      {note && <p className="mt-2 text-xs text-muted">{note}</p>}
    </div>
  );
}
