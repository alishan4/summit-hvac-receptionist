"use client";

import { useEffect } from "react";
import { CodeForm } from "@/components/CodeForm";
import { Dashboard } from "@/components/dashboard/Dashboard";
import { Logo } from "@/components/Brand";
import { useDemo } from "@/lib/demo";

export default function DashboardPage() {
  const { api, branding } = useDemo();
  useEffect(() => { document.title = `${branding.company.name} · AI Receptionist dashboard`; }, [branding]);

  if (!api) {
    return (
      <main className="grid min-h-dvh place-items-center bg-canvas px-6">
        <div className="animate-rise w-full max-w-sm rounded-2xl border border-line bg-white p-8 shadow-card">
          <div className="mb-6 flex flex-col items-center text-center">
            <Logo branding={branding} size={52} />
            <h1 className="mt-4 text-xl font-semibold tracking-tight">{branding.company.name} — AI Receptionist</h1>
            <p className="mt-1 text-sm text-muted">Business dashboard</p>
          </div>
          <CodeForm intro="Enter the access code to open the live dashboard." cta="Open dashboard" />
        </div>
      </main>
    );
  }
  return <Dashboard />;
}
