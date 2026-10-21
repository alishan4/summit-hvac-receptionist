import { logoSrc } from "@/lib/api";
import type { Branding } from "@/lib/types";

export function Logo({ branding, size = 40, className = "" }: { branding: Branding; size?: number; className?: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={logoSrc(branding)} alt={`${branding.company.name} logo`} width={size} height={size}
      className={`rounded-xl object-contain ${className}`} style={{ width: size, height: size }} />
  );
}
