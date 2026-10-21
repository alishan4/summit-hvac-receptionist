import type {
  Branding, CallEvents, CallRow, ChatReply, ChatSession, DayView, Stats, WebCall,
} from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public retryAfter?: number,
  ) {
    super(message);
  }
  /** Friendly text for the UI. */
  get friendly(): string {
    if (this.code === "network") return "Can't reach the demo server. Check your connection and try again.";
    return this.message;
  }
}

interface Opts {
  method?: "GET" | "POST";
  code?: string;
  body?: unknown;
  signal?: AbortSignal;
}

async function request<T>(path: string, { method = "GET", code, body, signal }: Opts = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      signal,
      headers: {
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(code ? { "X-Demo-Code": code } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, "network", "Network error");
  }
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    /* non-JSON error body (e.g. a platform error page) */
  }
  if (!res.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail;
    const d = typeof detail === "object" && detail !== null ? (detail as { error?: string; message?: string }) : {};
    const fallback = res.status >= 500 ? "The demo server had a problem. Try again in a moment." : "Request failed.";
    throw new ApiError(
      res.status,
      d.error ?? `http_${res.status}`,
      d.message ?? (typeof detail === "string" ? detail : fallback),
      Number(res.headers.get("retry-after")) || undefined,
    );
  }
  return data as T;
}

/** Typed client bound to the access code the visitor entered. */
export function createApi(code: string) {
  return {
    session: () => request<{ ok: true; voice_ready: boolean; chat_ready: boolean }>("/demo/session", { code }),
    webCall: () => request<WebCall>("/demo/web-call", { method: "POST", code }),
    chatCreate: () => request<ChatSession>("/demo/chat", { method: "POST", code }),
    chatMessage: (id: string, content: string) =>
      request<ChatReply>(`/demo/chat/${encodeURIComponent(id)}/message`, { method: "POST", code, body: { content } }),
    chatEnd: (id: string) => request<{ ok: true }>(`/demo/chat/${encodeURIComponent(id)}/end`, { method: "POST", code }),
    events: (id: string, signal?: AbortSignal) =>
      request<CallEvents>(`/demo/calls/${encodeURIComponent(id)}/events`, { code, signal }),
    appointments: (date?: string, signal?: AbortSignal) =>
      request<DayView>(`/demo/appointments${date ? `?date=${date}` : ""}`, { code, signal }),
    stats: (signal?: AbortSignal) => request<Stats>("/demo/stats", { code, signal }),
    calls: (signal?: AbortSignal) => request<{ calls: CallRow[] }>("/demo/calls", { code, signal }),
    reset: () => request<{ ok: true }>("/demo/reset", { method: "POST", code }),
  };
}
export type Api = ReturnType<typeof createApi>;

export const fetchBranding = (signal?: AbortSignal) => request<Branding>("/demo/branding", { signal });
export const logoSrc = (b: Branding) => `${API_BASE}${b.logo_url}`;
