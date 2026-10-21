"use client";

import { useEffect, useRef, type RefObject } from "react";

const BARS = 40;

/** Animated bars. Heights are written straight to the DOM from the audio level ref (no React re-render per frame). */
export function Waveform({ levelRef, live, speaking }: { levelRef: RefObject<number>; live: boolean; speaking: boolean }) {
  const bars = useRef<(HTMLSpanElement | null)[]>([]);

  useEffect(() => {
    let raf = 0;
    const loop = (t: number) => {
      const lvl = live ? levelRef.current : 0;
      bars.current.forEach((el, i) => {
        if (!el) return;
        const idle = 0.5 + 0.5 * Math.sin(t / 420 + i * 0.5);
        const voice = lvl * (0.45 + 0.55 * Math.sin(t / 95 + i * 1.3) ** 2);
        el.style.transform = `scaleY(${Math.min(1, 0.07 + (live ? 0.07 * idle : 0.03 * idle) + voice)})`;
      });
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [live, levelRef]);

  return (
    <div className="flex h-16 items-center justify-center gap-[3px]" aria-hidden>
      {Array.from({ length: BARS }, (_, i) => (
        <span
          key={i}
          ref={(el) => { bars.current[i] = el; }}
          className={`h-full w-[3px] origin-center rounded-full transition-colors duration-300 ${
            live ? (speaking ? "bg-accent" : "bg-slate-300") : "bg-slate-200"
          }`}
          style={{ transform: "scaleY(0.07)" }}
        />
      ))}
    </div>
  );
}
