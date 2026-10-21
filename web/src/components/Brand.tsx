import { logoSrc } from "@/lib/api";
import type { Branding } from "@/lib/types";

export function Logo({ branding, size = 40 }: { branding: Branding; size?: number }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={logoSrc(branding)} alt={`${branding.company.name} logo`} width={size} height={size}
      className="rounded-xl object-contain" style={{ width: size, height: size }} />
  );
}

export function Header({ branding, onLock }: { branding: Branding; onLock?: () => void }) {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-[1320px] flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3 sm:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <Logo branding={branding} />
          <div className="min-w-0">
            <h1 className="truncate text-[17px] font-semibold leading-tight tracking-tight">{branding.company.name}</h1>
            <p className="mt-0.5 inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-2.5 py-0.5 text-[11px] font-semibold text-accent-strong">
              <span className="size-1.5 rounded-full bg-accent animate-blink" />
              {branding.badge}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-[13px] text-muted">
          {branding.agency.show_powered_by && (
            <span>
              Powered by <strong className="font-semibold text-slate-700">{branding.agency.name}</strong>
            </span>
          )}
          {onLock && (
            <button onClick={onLock} className="rounded-lg px-2 py-1 transition hover:bg-slate-100 hover:text-slate-800">
              Lock
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
