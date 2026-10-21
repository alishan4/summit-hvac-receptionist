export function clock(totalSeconds: number): string {
  const s = Math.max(0, Math.round(totalSeconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

/** "2026-10-22T08:00:00-06:00" -> "2026-10-22" (the *local* date in the offset the API gave us). */
export function localDate(iso: string): string {
  return iso.slice(0, 10);
}

export function addDays(date: string, days: number): string {
  const d = new Date(`${date}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function prettyDate(date: string): string {
  return new Date(`${date}T12:00:00Z`).toLocaleDateString("en-US", {
    weekday: "long", month: "short", day: "numeric", timeZone: "UTC",
  });
}

export function money(n: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

/** Replaces {dispatch_fee}, {company} and {phone} in config-driven copy. */
export function fill(text: string, vars: Record<string, string>): string {
  return text.replace(/\{(\w+)\}/g, (m, k: string) => vars[k] ?? m);
}

export function telHref(phone: string): string {
  return `tel:+1${phone.replace(/\D/g, "").slice(-10)}`;
}

const DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

/** Is the business open right now in its own timezone? `hours` is the company.yaml schedule ("HH:MM"). */
export function isOpenNow(hours: Record<string, [string, string]>, timezone: string, now = new Date()): boolean {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone, weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(now);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  const day = get("weekday").slice(0, 3).toLowerCase();
  const slot = hours[DAYS.includes(day) ? day : ""];
  if (!slot) return false;
  const mins = (Number(get("hour")) % 24) * 60 + Number(get("minute"));
  const [oh, om] = slot[0].split(":").map(Number);
  const [ch, cm] = slot[1].split(":").map(Number);
  return mins >= oh * 60 + om && mins < ch * 60 + cm;
}
