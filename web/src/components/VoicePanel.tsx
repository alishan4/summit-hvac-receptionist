"use client";

import { AlertCircle, Mic, MicOff, Phone, PhoneOff, RotateCcw } from "lucide-react";
import { clock } from "@/lib/format";
import type { Api } from "@/lib/api";
import type { Turn } from "@/lib/types";
import { useVoiceCall } from "@/lib/useVoiceCall";
import { Transcript } from "./Transcript";
import { Spinner, btnGhost } from "./ui";
import { Waveform } from "./Waveform";

const STATUS_COPY: Record<string, string> = {
  requesting_mic: "Waiting for microphone permission…",
  creating: "Setting up your call…",
  connecting: "Connecting to the receptionist…",
};

export function VoicePanel({
  api, maxSeconds, onSession, serverTranscript,
}: {
  api: Api;
  maxSeconds: number;
  onSession: (id: string) => void;
  serverTranscript: Turn[];
}) {
  const v = useVoiceCall(api, onSession);
  const busy = v.status === "requesting_mic" || v.status === "creating" || v.status === "connecting";
  const live = v.status === "live";
  const sdkCaptions = v.transcript.length > 0;
  const turns = sdkCaptions ? v.transcript : serverTranscript;
  const showFallbackNote = (live || v.status === "ended") && !sdkCaptions && serverTranscript.length > 0;

  return (
    <div className="space-y-5">
      <div className="flex flex-col items-center rounded-2xl bg-gradient-to-b from-accent-soft/70 to-white px-4 pb-5 pt-7 text-center">
        {!live && !busy && v.status !== "ended" && v.status !== "error" && (
          <>
            <button
              onClick={v.start}
              className="animate-ring group grid size-24 place-items-center rounded-full bg-accent text-white shadow-lg shadow-accent/30 transition hover:scale-105 hover:bg-accent-strong focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-accent-ring"
              aria-label="Start voice call"
            >
              <Phone className="size-9 transition group-hover:rotate-6" />
            </button>
            <p className="mt-4 text-base font-semibold tracking-tight">Start voice call</p>
            <p className="mt-1 max-w-xs text-[13px] text-muted">
              Uses your browser microphone. Calls end automatically after {Math.round(maxSeconds / 60)} minutes.
            </p>
          </>
        )}

        {busy && (
          <div className="flex h-[150px] flex-col items-center justify-center gap-3">
            <Spinner className="size-8 text-accent" />
            <p className="text-sm font-medium text-slate-700">{STATUS_COPY[v.status]}</p>
          </div>
        )}

        {live && (
          <div className="w-full animate-pop">
            <div className="flex items-center justify-center gap-2 text-sm font-semibold">
              <span className={`size-2 rounded-full ${v.agentSpeaking ? "bg-accent animate-blink" : "bg-emerald-500"}`} />
              {v.agentSpeaking ? "AI is speaking" : v.muted ? "You're muted" : "Listening to you"}
              <span className="ml-2 rounded-md bg-white px-2 py-0.5 font-mono text-xs text-muted ring-1 ring-line">
                {clock(v.secondsLeft ?? 0)} left
              </span>
            </div>
            <Waveform levelRef={v.level} live speaking={v.agentSpeaking} />
            <div className="mt-2 flex items-center justify-center gap-3">
              <button onClick={v.toggleMute} className={btnGhost} aria-pressed={v.muted}>
                {v.muted ? <MicOff className="size-4 text-red-500" /> : <Mic className="size-4" />}
                {v.muted ? "Unmute" : "Mute"}
              </button>
              <button
                onClick={v.end}
                className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600"
              >
                <PhoneOff className="size-4" /> End call
              </button>
            </div>
          </div>
        )}

        {v.status === "ended" && (
          <div className="flex h-[150px] animate-pop flex-col items-center justify-center gap-3">
            <p className="text-base font-semibold tracking-tight">Call ended</p>
            <p className="text-[13px] text-muted">Watch the right side: the summary and owner email finish a few seconds later.</p>
            <button onClick={v.reset} className={btnGhost}>
              <RotateCcw className="size-4" /> Start another call
            </button>
          </div>
        )}

        {v.status === "error" && v.error && (
          <div role="alert" className="flex min-h-[150px] animate-pop flex-col items-center justify-center gap-3">
            <span className="grid size-10 place-items-center rounded-full bg-red-50 text-red-600">
              {v.error.kind === "mic_denied" || v.error.kind === "no_mic" ? <MicOff className="size-5" /> : <AlertCircle className="size-5" />}
            </span>
            <p className="max-w-sm text-sm text-slate-700">{v.error.message}</p>
            <button onClick={v.reset} className={btnGhost}>
              <RotateCcw className="size-4" /> Try again
            </button>
          </div>
        )}
      </div>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">Live transcript</h3>
        <Transcript
          turns={turns}
          empty={live ? "The conversation will appear here as you talk." : "Start a call and the transcript appears here."}
          note={showFallbackNote ? "Captions refresh each time the receptionist checks a system; the full transcript lands when the call ends." : undefined}
        />
      </div>
    </div>
  );
}
