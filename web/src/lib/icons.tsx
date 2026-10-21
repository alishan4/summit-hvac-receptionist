import {
  BadgeDollarSign, CalendarCheck, Clock, Flame, Home, Leaf, ShieldCheck, Siren, Snowflake, Sparkles, Star,
  Thermometer, Users, Waves, Wind, Wrench, type LucideIcon,
} from "lucide-react";

// Icon names usable in config/branding.yaml (site.services[].icon, site.why_choose[].icon).
const ICONS: Record<string, LucideIcon> = {
  snowflake: Snowflake, flame: Flame, waves: Waves, wind: Wind, wrench: Wrench, thermometer: Thermometer,
  home: Home, "shield-check": ShieldCheck, clock: Clock, "calendar-check": CalendarCheck,
  "badge-dollar-sign": BadgeDollarSign, siren: Siren, leaf: Leaf, star: Star, users: Users, sparkles: Sparkles,
};

export function Icon({ name, className }: { name: string; className?: string }) {
  const C = ICONS[name] ?? Wrench;
  return <C className={className} aria-hidden />;
}
