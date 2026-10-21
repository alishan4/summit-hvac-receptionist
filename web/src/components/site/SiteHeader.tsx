"use client";

import { Menu, Phone, X } from "lucide-react";
import { useState } from "react";
import { telHref } from "@/lib/format";
import { useDemo } from "@/lib/demo";
import { Logo } from "../Brand";
import { useWidget } from "../widget/AssistantWidget";

const NAV = [
  { href: "#services", label: "Services" },
  { href: "#reviews", label: "Reviews" },
  { href: "#service-area", label: "Service Area" },
  { href: "#about", label: "About" },
];

export function SiteHeader() {
  const { branding } = useDemo();
  const { open } = useWidget();
  const [menu, setMenu] = useState(false);
  const { site } = branding;

  return (
    <header className="sticky top-0 z-30 border-b border-stone-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3 sm:px-6">
        <a href="#top" className="flex min-w-0 items-center gap-2.5 rounded-lg focus-visible:outline-2 focus-visible:outline-accent" aria-label={`${branding.company.name} home`}>
          <Logo branding={branding} size={38} />
          <span className="line-clamp-2 font-display text-[17px] font-semibold leading-tight tracking-tight text-[#1d2740] sm:line-clamp-1 sm:text-xl">{branding.company.name}</span>
        </a>

        <nav aria-label="Main" className="ml-8 hidden items-center gap-1 lg:flex">
          {NAV.map((n) => (
            <a key={n.href} href={n.href} className="rounded-lg px-3 py-2 text-[15px] font-medium text-stone-600 transition hover:bg-stone-100 hover:text-[#1d2740] focus-visible:outline-2 focus-visible:outline-accent">{n.label}</a>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <a href={telHref(site.phone)} className="hidden items-center gap-2 rounded-lg px-2 py-1.5 text-[15px] font-semibold text-[#1d2740] hover:text-accent-strong focus-visible:outline-2 focus-visible:outline-accent md:flex">
            <Phone className="size-4 text-accent" aria-hidden /> {site.phone}
          </a>
          <a href={telHref(site.phone)} aria-label={`Call ${site.phone}`} className="grid size-10 place-items-center rounded-full border border-stone-200 text-accent md:hidden"><Phone className="size-[18px]" /></a>
          <button onClick={() => open()} className="whitespace-nowrap rounded-xl bg-accent px-3 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-accent-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:px-4">
            <span className="hidden sm:inline">Book service — 24/7</span>
            <span className="sm:hidden">Book 24/7</span>
          </button>
          <button onClick={() => setMenu((m) => !m)} aria-expanded={menu} aria-controls="mobile-nav" aria-label="Menu" className="grid size-10 place-items-center rounded-lg text-stone-700 hover:bg-stone-100 lg:hidden">
            {menu ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>
        </div>
      </div>
      {menu && (
        <nav id="mobile-nav" aria-label="Mobile" className="animate-rise border-t border-stone-200 bg-white px-4 py-2 lg:hidden">
          {NAV.map((n) => (
            <a key={n.href} href={n.href} onClick={() => setMenu(false)} className="block rounded-lg px-3 py-3 text-base font-medium text-stone-700 hover:bg-stone-50">{n.label}</a>
          ))}
        </nav>
      )}
    </header>
  );
}
