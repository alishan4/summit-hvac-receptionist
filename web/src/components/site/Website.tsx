"use client";

import { WidgetProvider } from "../widget/AssistantWidget";
import { AfterHoursBanner } from "./AfterHoursBanner";
import { SiteHeader } from "./SiteHeader";
import { About, FinalCta, Footer, Hero, Reviews, ServiceArea, Services, WhyUs } from "./Sections";

/** The public, homeowner-facing website. The AI assistant widget floats on top of it. */
export function Website() {
  return (
    <WidgetProvider>
      <div className="site min-h-dvh bg-[#fffaf5] text-[#1d2740]">
        <a href="#main" className="sr-only z-50 rounded-lg bg-white px-4 py-2 font-semibold focus:not-sr-only focus:fixed focus:left-4 focus:top-4">Skip to content</a>
        <AfterHoursBanner />
        <SiteHeader />
        <main id="main">
          <Hero />
          <Services />
          <WhyUs />
          <Reviews />
          <ServiceArea />
          <About />
          <FinalCta />
        </main>
        <Footer />
      </div>
    </WidgetProvider>
  );
}
