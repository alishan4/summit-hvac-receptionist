"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, type Api } from "./api";
import type { Turn } from "./types";

export type VoiceStatus = "idle" | "requesting_mic" | "creating" | "connecting" | "live" | "ended" | "error";
export interface VoiceError {
  kind: "mic_denied" | "no_mic" | "unsupported" | "api" | "connection";
  message: string;
}

// The slice of the SDK's (legacy) RetellWebClient we use. It stays in the package until 4.0;
// we start it from a server-minted access token so the Retell API key never reaches the browser.
interface RetellClientLike {
  on(event: string, cb: (...args: never[]) => void): unknown;
  startCall(cfg: {
    accessToken: string;
    callId: string;
    transport?: "livekit" | "gateway";
    iceServers?: RTCIceServer[];
    sampleRate?: number;
    emitRawAudioSamples?: boolean;
  }): Promise<void>;
  stopCall(): void;
  mute(): void;
  unmute(): void;
}

const SPEAKING_RMS = 0.02;

function rms(samples: Float32Array): number {
  let sum = 0;
  for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
  return Math.sqrt(sum / samples.length);
}

export function useVoiceCall(api: Api, onSession: (callId: string) => void) {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [error, setError] = useState<VoiceError | null>(null);
  const [transcript, setTranscript] = useState<Turn[]>([]);
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const [muted, setMuted] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);
  const [callId, setCallId] = useState<string | null>(null);

  const client = useRef<RetellClientLike | null>(null);
  const level = useRef(0); // smoothed agent-audio level, 0..1, read by the waveform every frame
  const sdkSpeechEvents = useRef(false); // true once the SDK itself reports talking state
  const speaking = useRef(false);
  const active = useRef(false);

  const teardown = useCallback(() => {
    active.current = false;
    try {
      client.current?.stopCall();
    } catch {
      /* already closed */
    }
    client.current = null;
    level.current = 0;
    speaking.current = false;
    setAgentSpeaking(false);
    setMuted(false);
    setSecondsLeft(null);
  }, []);

  const end = useCallback(() => {
    if (!active.current) return;
    teardown();
    setStatus("ended");
  }, [teardown]);

  const fail = useCallback((e: VoiceError) => {
    teardown();
    setError(e);
    setStatus("error");
  }, [teardown]);

  // 4-minute cap, mirrored client-side (the server enforces it too).
  useEffect(() => {
    if (status !== "live" || secondsLeft === null) return;
    if (secondsLeft <= 0) {
      end();
      return;
    }
    const t = setTimeout(() => setSecondsLeft((s) => (s === null ? s : s - 1)), 1000);
    return () => clearTimeout(t);
  }, [status, secondsLeft, end]);

  useEffect(() => teardown, [teardown]);

  const start = useCallback(async () => {
    setError(null);
    setTranscript([]);
    setCallId(null);
    sdkSpeechEvents.current = false;

    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      return fail({ kind: "unsupported", message: "This browser can't use the microphone here. Try Chrome, Edge or Safari over https." });
    }

    // 1) Microphone first: a denied prompt must not spend a Retell call.
    setStatus("requesting_mic");
    try {
      const probe = await navigator.mediaDevices.getUserMedia({ audio: true });
      probe.getTracks().forEach((t) => t.stop());
    } catch (e) {
      const name = e instanceof DOMException ? e.name : "";
      return fail(
        name === "NotFoundError"
          ? { kind: "no_mic", message: "No microphone found. Plug one in, or use the text chat tab instead." }
          : { kind: "mic_denied", message: "Microphone access was blocked. Allow it in your browser's site settings, then try again, or use the text chat tab." },
      );
    }

    // 2) Server mints the access token (gated by the access code, rate limited, capped).
    setStatus("creating");
    let call;
    try {
      call = await api.webCall();
    } catch (e) {
      return fail({ kind: "api", message: e instanceof ApiError ? e.friendly : "Couldn't start the call." });
    }
    setCallId(call.call_id);
    onSession(call.call_id);

    // 3) Connect audio.
    setStatus("connecting");
    try {
      const { RetellWebClient } = await import("retell-client-js-sdk");
      const c = new RetellWebClient() as unknown as RetellClientLike;
      client.current = c;
      active.current = true;

      c.on("call_ready", (() => {
        setStatus("live");
        setSecondsLeft(call.max_seconds);
      }) as never);
      c.on("call_ended", (() => end()) as never);
      c.on("error", ((err: unknown) => {
        fail({ kind: "connection", message: typeof err === "string" ? `Connection problem (${err}).` : "Connection problem." });
      }) as never);
      // Live captions: delivered by the SDK when the platform emits them for this call type.
      c.on("update", ((u: { transcript?: Turn[] }) => {
        if (u?.transcript?.length) setTranscript(u.transcript.map((t) => ({ role: t.role, content: t.content })));
      }) as never);
      c.on("agent_start_talking", (() => {
        sdkSpeechEvents.current = true;
        speaking.current = true;
        setAgentSpeaking(true);
      }) as never);
      c.on("agent_stop_talking", (() => {
        sdkSpeechEvents.current = true;
        speaking.current = false;
        setAgentSpeaking(false);
      }) as never);
      // Raw agent-audio frames drive the waveform, and the speaking indicator if the SDK doesn't report it.
      c.on("audio", ((samples: Float32Array) => {
        const v = Math.min(1, rms(samples) * 6);
        level.current = level.current * 0.6 + v * 0.4;
        if (!sdkSpeechEvents.current) {
          const now = rms(samples) > SPEAKING_RMS;
          if (now !== speaking.current) {
            speaking.current = now;
            setAgentSpeaking(now);
          }
        }
      }) as never);

      await c.startCall({
        accessToken: call.access_token,
        callId: call.call_id,
        transport: call.transport ?? "gateway",
        iceServers: call.ice_servers ?? undefined,
        sampleRate: 24000,
        emitRawAudioSamples: true,
      });
    } catch {
      fail({ kind: "connection", message: "Couldn't connect the call audio. Please try again." });
    }
  }, [api, end, fail, onSession]);

  const toggleMute = useCallback(() => {
    if (!client.current) return;
    setMuted((m) => {
      if (m) client.current?.unmute();
      else client.current?.mute();
      return !m;
    });
  }, []);

  const reset = useCallback(() => {
    teardown();
    setStatus("idle");
    setError(null);
    setTranscript([]);
    setCallId(null);
  }, [teardown]);

  return { status, error, transcript, agentSpeaking, muted, secondsLeft, callId, level, start, end, toggleMute, reset };
}
