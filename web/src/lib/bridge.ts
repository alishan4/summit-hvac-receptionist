/**
 * Presenter mode shows the public website in an iframe next to the dashboard. The two documents are
 * same-origin, so they coordinate over postMessage: the widget announces the live session, the
 * presenter can drop a scenario script into the widget's chat, and the access code is shared.
 */
export type BridgeMessage =
  | { type: "demo-session"; id: string; kind: "voice" | "chat" }
  | { type: "demo-code"; code: string | null }
  | { type: "demo-draft"; text: string };

export const isEmbedded = () => typeof window !== "undefined" && window.self !== window.top;

export function post(target: Window | null | undefined, msg: BridgeMessage) {
  target?.postMessage(msg, window.location.origin);
}

export function toParent(msg: BridgeMessage) {
  if (isEmbedded()) post(window.parent, msg);
}

export function toFrames(msg: BridgeMessage) {
  document.querySelectorAll("iframe").forEach((f) => post(f.contentWindow, msg));
}

export function listen(handler: (msg: BridgeMessage) => void): () => void {
  const fn = (e: MessageEvent) => {
    if (e.origin !== window.location.origin) return;
    const d = e.data as BridgeMessage | undefined;
    if (d && typeof d === "object" && "type" in d && typeof d.type === "string" && d.type.startsWith("demo-")) handler(d);
  };
  window.addEventListener("message", fn);
  return () => window.removeEventListener("message", fn);
}
