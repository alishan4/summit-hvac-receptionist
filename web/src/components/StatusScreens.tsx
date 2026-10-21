import type { ReactNode } from "react";
import { Spinner, btnPrimary } from "./ui";

export function FullScreen({ children }: { children: ReactNode }) {
  return <main className="grid min-h-dvh place-items-center px-6">{children}</main>;
}

export function WakingScreen({ waking }: { waking: boolean }) {
  return (
    <FullScreen>
      <div className="animate-rise flex max-w-sm flex-col items-center gap-4 text-center">
        <div className="relative grid size-14 place-items-center rounded-2xl bg-white shadow-card">
          <Spinner className="size-6 text-accent" />
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-tight">{waking ? "Waking up the receptionist…" : "Loading the demo…"}</h1>
          <p className="mt-1 text-sm text-muted">
            {waking ? "The server was asleep. This takes a few seconds the first time." : "One moment."}
          </p>
        </div>
      </div>
    </FullScreen>
  );
}

export function ErrorScreen({ title, message, onRetry }: { title: string; message: string; onRetry?: () => void }) {
  return (
    <FullScreen>
      <div className="animate-rise flex max-w-md flex-col items-center gap-4 rounded-2xl border border-line bg-white p-8 text-center shadow-card">
        <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
        <p className="text-sm text-muted">{message}</p>
        {onRetry && (
          <button className={btnPrimary} onClick={onRetry}>
            Try again
          </button>
        )}
      </div>
    </FullScreen>
  );
}
