"use client";

import { BadgeCheck, Check, MapPin, MessageCircle, Mic, Phone, ShieldCheck, Star } from "lucide-react";
import { useId, useMemo, useState } from "react";
import { fill, telHref } from "@/lib/format";
import { useDemo } from "@/lib/demo";
import { Icon } from "@/lib/icons";
import { useWidget } from "../widget/AssistantWidget";
import { HeroIllustration } from "./HeroIllustration";

const wrap = "mx-auto max-w-6xl px-4 sm:px-6";
const eyebrow = "text-[13px] font-bold uppercase tracking-[0.14em] text-accent-strong";
const h2 = "font-display text-3xl font-semibold leading-tight tracking-tight text-[#1d2740] sm:text-4xl";

function Stars({ n, label }: { n: number; label?: string }) {
  return (
    <span className="inline-flex" role="img" aria-label={label ?? `${n} out of 5 stars`}>
      {Array.from({ length: 5 }, (_, i) => (
        <Star key={i} className={`size-4 ${i < Math.round(n) ? "fill-amber-400 text-amber-400" : "text-stone-300"}`} aria-hidden />
      ))}
    </span>
  );
}

export function Hero() {
  const { branding } = useDemo();
  const { open } = useWidget();
  const { site } = branding;
  return (
    <section id="top" className="relative overflow-hidden bg-gradient-to-b from-[#fff4ea] via-[#fffaf5] to-[#fffaf5]">
      <div className={`${wrap} grid items-center gap-10 py-12 sm:py-16 md:grid-cols-[1.05fr_0.95fr] lg:py-20`}>
        <div>
          {site.eyebrow && <p className={eyebrow}>{site.eyebrow}</p>}
          <h1 className="mt-3 text-balance font-display text-4xl font-semibold leading-[1.08] tracking-tight text-[#1d2740] sm:text-5xl lg:text-[3.4rem]">
            {site.hero_headline}
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-stone-600">{site.hero_subline}</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <button onClick={() => open("voice")} className="inline-flex items-center justify-center gap-2.5 rounded-xl bg-accent px-6 py-3.5 text-base font-semibold text-white shadow-lg shadow-accent/25 transition hover:-translate-y-0.5 hover:bg-accent-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
              <Mic className="size-5" aria-hidden /> Talk to us now
            </button>
            <button onClick={() => open("chat")} className="inline-flex items-center justify-center gap-2.5 rounded-xl border border-stone-300 bg-white px-6 py-3.5 text-base font-semibold text-[#1d2740] transition hover:-translate-y-0.5 hover:border-stone-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
              <MessageCircle className="size-5 text-accent" aria-hidden /> Chat with us
            </button>
          </div>
          <ul className="mt-9 flex flex-wrap gap-x-7 gap-y-3 text-[15px] text-stone-700">
            <li className="flex items-center gap-2"><ShieldCheck className="size-5 text-emerald-600" aria-hidden /> Licensed &amp; insured</li>
            <li className="flex items-center gap-2"><BadgeCheck className="size-5 text-emerald-600" aria-hidden /> {site.years_in_business} years in business</li>
            <li className="flex items-center gap-2"><Stars n={site.rating} label={`Rated ${site.rating} out of 5`} /> <span><strong>{site.rating.toFixed(1)}</strong> · {site.review_count} reviews</span></li>
          </ul>
        </div>
        <HeroIllustration className="mx-auto w-full max-w-[34rem] drop-shadow-[0_24px_40px_rgba(120,53,15,0.18)]" />
      </div>
    </section>
  );
}

export function Services() {
  const { branding } = useDemo();
  return (
    <section id="services" className="scroll-mt-20 bg-white py-16 sm:py-20">
      <div className={wrap}>
        <p className={eyebrow}>What we do</p>
        <h2 className={`${h2} mt-2`}>Heating &amp; cooling, done right</h2>
        <ul className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {branding.site.services.map((s) => (
            <li key={s.title} className="group rounded-2xl border border-stone-200 bg-[#fffdfa] p-6 transition hover:-translate-y-1 hover:border-accent-ring hover:shadow-lg">
              <span className="grid size-12 place-items-center rounded-xl bg-accent-soft text-accent-strong transition group-hover:bg-accent group-hover:text-white"><Icon name={s.icon} className="size-6" /></span>
              <h3 className="mt-4 text-lg font-semibold text-[#1d2740]">{s.title}</h3>
              <p className="mt-1.5 leading-relaxed text-stone-600">{s.blurb}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export function WhyUs() {
  const { branding } = useDemo();
  const vars = useMemo(() => ({ dispatch_fee: branding.company.dispatch_fee, company: branding.company.name, phone: branding.site.phone }), [branding]);
  return (
    <section id="why-us" className="scroll-mt-20 bg-[#fff4ea] py-16 sm:py-20">
      <div className={`${wrap} grid gap-10 lg:grid-cols-[0.8fr_1.2fr]`}>
        <div>
          <p className={eyebrow}>Why homeowners choose us</p>
          <h2 className={`${h2} mt-2`}>Honest, on time, and there when it matters</h2>
          <div className="mt-6 inline-flex items-baseline gap-2 rounded-2xl bg-white px-5 py-4 shadow-sm ring-1 ring-stone-200">
            <span className="font-display text-4xl font-semibold text-accent-strong">{branding.company.dispatch_fee}</span>
            <span className="max-w-[10rem] text-sm leading-snug text-stone-600">diagnostic, applied to your repair</span>
          </div>
        </div>
        <ul className="grid gap-4 sm:grid-cols-2">
          {branding.site.why_choose.map((w) => (
            <li key={w.title} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-stone-200">
              <span className="grid size-10 place-items-center rounded-lg bg-accent-soft text-accent-strong"><Icon name={w.icon} className="size-5" /></span>
              <h3 className="mt-3 font-semibold text-[#1d2740]">{w.title}</h3>
              <p className="mt-1 text-[15px] leading-relaxed text-stone-600">{fill(w.text, vars)}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export function Reviews() {
  const { branding } = useDemo();
  const { site } = branding;
  return (
    <section id="reviews" className="scroll-mt-20 bg-white py-16 sm:py-20">
      <div className={wrap}>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className={eyebrow}>Customer stories</p>
            <h2 className={`${h2} mt-2`}>Neighbors who called us</h2>
          </div>
          <p className="flex items-center gap-2 text-[15px] text-stone-600"><Stars n={site.rating} /> <strong className="text-[#1d2740]">{site.rating.toFixed(1)}</strong> from {site.review_count} reviews</p>
        </div>
        <ul className="mt-10 grid gap-5 md:grid-cols-3">
          {site.reviews.map((r) => (
            <li key={r.name} className="flex flex-col rounded-2xl border border-stone-200 bg-[#fffdfa] p-6">
              <Stars n={r.rating} />
              <blockquote className="mt-3 flex-1 leading-relaxed text-stone-700">&ldquo;{r.text}&rdquo;</blockquote>
              <figcaption className="mt-5 flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-full bg-accent-soft text-sm font-bold text-accent-strong" aria-hidden>{r.name[0]}</span>
                <span className="text-sm"><strong className="block text-[#1d2740]">{r.name}</strong><span className="text-stone-500">{r.area}</span></span>
              </figcaption>
            </li>
          ))}
        </ul>
        <p className="mt-5 text-xs text-stone-500">Demo reviews written for a fictional business.</p>
      </div>
    </section>
  );
}

export function ServiceArea() {
  const { branding } = useDemo();
  const { site, service_area: area } = branding;
  const id = useId();
  const [zip, setZip] = useState("");
  const clean = zip.replace(/\D/g, "").slice(0, 5);
  const result = clean.length === 5 ? (area.zips.includes(clean) ? "yes" : "no") : null;

  return (
    <section id="service-area" className="scroll-mt-20 bg-[#f6f1ea] py-16 sm:py-20">
      <div className={`${wrap} grid gap-10 lg:grid-cols-2`}>
        <div>
          <p className={eyebrow}>Service area</p>
          <h2 className={`${h2} mt-2`}>Serving {area.description}</h2>
          <ul className="mt-6 flex flex-wrap gap-2.5" aria-label="Cities we serve">
            {site.service_area_names.map((c) => (
              <li key={c} className="flex items-center gap-1.5 rounded-full bg-white px-4 py-2 text-[15px] font-medium text-[#1d2740] shadow-sm ring-1 ring-stone-200"><MapPin className="size-4 text-accent" aria-hidden /> {c}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-stone-200">
          <label htmlFor={id} className="font-semibold text-[#1d2740]">Do we serve your ZIP code?</label>
          <input id={id} inputMode="numeric" autoComplete="postal-code" maxLength={5} value={clean} onChange={(e) => setZip(e.target.value)} placeholder="e.g. 80203"
            className="mt-3 w-full rounded-xl border border-stone-300 px-4 py-3 text-lg outline-none transition focus:border-accent focus:ring-4 focus:ring-accent-ring" />
          <p aria-live="polite" className="mt-3 min-h-6 text-[15px]">
            {result === "yes" && <span className="flex items-center gap-2 font-medium text-emerald-700"><Check className="size-5" aria-hidden /> Yes! We serve {clean}.</span>}
            {result === "no" && <span className="font-medium text-amber-800">{clean} is outside our current area. Call us and we&apos;ll point you in the right direction.</span>}
          </p>
          <details className="mt-3 text-sm text-stone-600">
            <summary className="cursor-pointer rounded font-medium text-accent-strong focus-visible:outline-2 focus-visible:outline-accent">See all {area.zips.length} ZIP codes</summary>
            <p className="mt-2 leading-relaxed">{area.zips.join(" · ")}</p>
          </details>
        </div>
      </div>
    </section>
  );
}

export function About() {
  const { branding } = useDemo();
  const { site } = branding;
  return (
    <section id="about" className="scroll-mt-20 bg-white py-16 sm:py-20">
      <div className={`${wrap} grid items-center gap-10 lg:grid-cols-[1.1fr_0.9fr]`}>
        <div>
          <p className={eyebrow}>About us</p>
          <h2 className={`${h2} mt-2`}>A Denver company that picks up the phone</h2>
          <div className="mt-5 space-y-4 text-lg leading-relaxed text-stone-600">
            {site.about.map((p) => <p key={p}>{p}</p>)}
          </div>
        </div>
        <dl className="grid grid-cols-3 gap-3 text-center">
          {[
            [`${site.years_in_business}`, "years serving Denver"],
            [`${site.rating.toFixed(1)}★`, `${site.review_count} reviews`],
            ["24/7", "someone answers"],
          ].map(([n, l]) => (
            <div key={l} className="rounded-2xl bg-[#fff4ea] px-3 py-6">
              <dt className="font-display text-3xl font-semibold text-accent-strong">{n}</dt>
              <dd className="mt-1 text-sm text-stone-600">{l}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

export function FinalCta() {
  const { branding } = useDemo();
  const { open } = useWidget();
  const { site } = branding;
  return (
    <section className="bg-accent-strong py-16 text-white sm:py-20">
      <div className={`${wrap} text-center`}>
        <h2 className="text-balance font-display text-3xl font-semibold tracking-tight sm:text-4xl">{site.cta_headline}</h2>
        <p className="mx-auto mt-3 max-w-xl text-lg text-white/85">{site.cta_subline}</p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <button onClick={() => open("voice")} className="inline-flex items-center gap-2.5 rounded-xl bg-white px-6 py-3.5 text-base font-semibold text-[#1d2740] shadow-lg transition hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">
            <Mic className="size-5 text-accent" aria-hidden /> Talk to us now
          </button>
          <button onClick={() => open("chat")} className="inline-flex items-center gap-2.5 rounded-xl border border-white/50 px-6 py-3.5 text-base font-semibold transition hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">
            <MessageCircle className="size-5" aria-hidden /> Chat with us
          </button>
          <a href={telHref(site.phone)} className="inline-flex items-center gap-2 px-4 py-3 text-base font-semibold underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-white">
            <Phone className="size-5" aria-hidden /> {site.phone}
          </a>
        </div>
      </div>
    </section>
  );
}

export function Footer() {
  const { branding } = useDemo();
  const { site } = branding;
  return (
    <footer className="bg-[#161e33] pb-28 pt-12 text-stone-300 sm:pb-24">
      <div className={`${wrap} grid gap-8 text-[15px] sm:grid-cols-2 lg:grid-cols-4`}>
        <div className="lg:col-span-2">
          <p className="font-display text-xl font-semibold text-white">{branding.company.name}</p>
          <p className="mt-2 max-w-sm leading-relaxed">{site.address}</p>
        </div>
        <div>
          <p className="font-semibold text-white">Call us</p>
          <a href={telHref(site.phone)} className="mt-2 block text-lg font-semibold text-white hover:underline">{site.phone}</a>
          <p className="mt-1">24/7, always answered</p>
        </div>
        <div>
          <p className="font-semibold text-white">Hours</p>
          <p className="mt-2 leading-relaxed">{site.hours_text}</p>
        </div>
      </div>
      <div className={`${wrap} mt-10 border-t border-white/10 pt-6 text-sm text-stone-400`}>
        <p>{site.disclaimer}</p>
        {branding.agency.show_powered_by && <p className="mt-1">AI receptionist powered by {branding.agency.name}.</p>}
      </div>
    </footer>
  );
}
