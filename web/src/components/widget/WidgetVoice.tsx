"use client";

import { AlertCircle, Mic, MicOff, Phone, PhoneOff, RotateCcw } from "lucide-react";
import { clock } from "@/lib/format";
import type { Turn } from "@/lib/types";
import type { useVoiceCall } from "@/lib/useVoiceCall";
import { Transcript } from "../Transcript";
import { Spinner, btnGhost } from "../ui";
import { Waveform } from "../Waveform";

type Voice = ReturnType<typeof useVoiceCall>;

const BUSY_COPY: Record<string, string> = {
  requesting_mic: "Waiting for microphone permission…",
  creating: "Setting up your call…",
  connecting: "Connecting you to our receptionist…",
};

export function WidgetVoice({ voice: v, maxSeconds, serverTranscript }: { voice: Voice; maxSeconds: number; serverTranscript: Turn[] }) {
  const busy = v.status === "requesting_mic" || v.status === "creating" || v.status === "connecting";
  const live = v.status === "live";
  const turns = v.transcript.length > 0 ? v.transcript : serverTranscript;

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="shrink-0 rounded-2xl bg-gradient-to-b from-accent-soft/80 to-white px-4 py-5 text-center">
        {(v.status === "idle") && (
          <>
            <button onClick={v.start} aria-label="Start call"
              className="animate-ring mx-auto grid size-20 place-items-center rounded-full bg-accent text-white shadow-lg shadow-accent/30 transition hover:scale-105 hover:bg-accent-strong focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-accent-ring">
              <Phone className="size-8" />
            </button>
            <p className="mt-3 text-[15px] font-semibold">Talk to our receptionist</p>
            <p className="mx-auto mt-1 max-w-[17rem] text-[13px] text-muted">
              Tap to start. Your browser will ask to use the microphone. Calls last up to {Math.round(maxSeconds / 60)} minutes.
            </p>
          </>
        )}
        {busy && (
          <div className="flex h-[132px] flex-col items-center justify-center gap-3">
            <Spinner className="size-7 text-accent" />
            <p className="text-sm font-medium text-slate-700">{BUSY_COPY[v.status]}</p>
          </div>
        )}
        {live && (
          <div className="animate-pop">
            <div className="flex flex-wrap items-center justify-center gap-2 text-sm font-semibold">
              <span className={`size-2 rounded-full ${v.agentSpeaking ? "animate-blink bg-accent" : "bg-emerald-500"}`} />
              {v.agentSpeaking ? "Speaking…" : v.muted ? "You're muted" : "Listening…"}
              <span className="rounded-md bg-white px-2 py-0.5 font-mono text-xs text-muted ring-1 ring-line">{clock(v.secondsLeft ?? 0)}</span>
            </div>
            <Waveform levelRef={v.level} live speaking={v.agentSpeaking} />
            <div className="flex items-center justify-center gap-2.5">
              <button onClick={v.toggleMute} className={btnGhost} aria-pressed={v.muted}>
                {v.muted ? <MicOff className="size-4 text-red-500" /> : <Mic className="size-4" />}
                {v.muted ? "Unmute" : "Mute"}
              </button>
              <button onClick={v.end}
                className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600">
                <PhoneOff className="size-4" /> End call
              </button>
            </div>
          </div>
        )}
        {v.status === "ended" && (
          <div className="flex h-[132px] animate-pop flex-col items-center justify-center gap-2.5">
            <p className="text-[15px] font-semibold">Thanks for calling!</p>
            <p className="text-[13px] text-muted">Your details are with our team.</p>
            <button onClick={v.reset} className={btnGhost}><RotateCcw className="size-4" /> Start another call</button>
          </div>
        )}
        {v.status === "error" && v.error && (
          <div role="alert" className="flex min-h-[132px] animate-pop flex-col items-center justify-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-full bg-red-50 text-red-600">
              {v.error.kind === "mic_denied" || v.error.kind === "no_mic" ? <MicOff className="size-4" /> : <AlertCircle className="size-4" />}
            </span>
            <p className="max-w-[18rem] text-[13px] text-slate-700">{v.error.message}</p>
            <button onClick={v.reset} className={btnGhost}><RotateCcw className="size-4" /> Try again</button>
          </div>
        )}
      </div>
      <Transcript turns={turns} className="min-h-0 flex-1" empty={live ? "Your conversation appears here." : "Captions appear here during the call."} />
    </div>
  );
}
