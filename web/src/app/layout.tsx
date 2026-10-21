import type { Metadata, Viewport } from "next";
import { Fraunces, Inter } from "next/font/google";
import { DemoProvider } from "@/lib/demo";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces", display: "swap" });

export const metadata: Metadata = {
  title: "Summit Heating & Air | AI Receptionist Demo",
  description: "Demo website for a fictional business. Built to showcase AI receptionist technology.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#fffaf5" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${fraunces.variable}`}>
      <body className="min-h-dvh">
        <DemoProvider>{children}</DemoProvider>
      </body>
    </html>
  );
}
