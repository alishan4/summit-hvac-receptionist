"use client";

import { useEffect } from "react";
import { Website } from "@/components/site/Website";
import { useDemo } from "@/lib/demo";

export default function HomePage() {
  const { branding } = useDemo();
  useEffect(() => { document.title = `${branding.company.name} | ${branding.site.hero_headline}`; }, [branding]);
  return <Website />;
}
