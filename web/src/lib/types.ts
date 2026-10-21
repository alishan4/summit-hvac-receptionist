export interface Scenario {
  id: string;
  title: string;
  subtitle: string;
  tone: "urgent" | "emergency" | "neutral";
  script: string;
}

export interface SiteService { icon: string; title: string; blurb: string }
export interface SiteWhy { icon: string; title: string; text: string }
export interface SiteReview { name: string; area: string; text: string; rating: number }

export interface Site {
  domain: string;
  phone: string;
  address: string;
  hours_text: string;
  eyebrow: string;
  hero_headline: string;
  hero_subline: string;
  years_in_business: number;
  rating: number;
  review_count: number;
  services: SiteService[];
  why_choose: SiteWhy[];
  reviews: SiteReview[];
  service_area_names: string[];
  about: string[];
  cta_headline: string;
  cta_subline: string;
  disclaimer: string;
}

export interface Branding {
  agency: { name: string; show_powered_by: boolean };
  badge: string;
  tagline: string;
  accent_color: string;
  logo_url: string;
  scenarios: Scenario[];
  demo_tips: string[];
  site: Site;
  dashboard: { average_job_value: number };
  service_area: { description: string; zips: string[] };
  company: {
    name: string;
    location: string;
    timezone: string;
    greeting: string;
    dispatch_fee: string;
    business_hours: Record<string, [string, string]>;
  };
  limits: { max_call_seconds: number };
}

export type Tone = "neutral" | "success" | "warn" | "danger";

export interface TimelineEvent {
  id: number;
  kind: string;
  label: string;
  sub: string | null;
  tone: Tone;
  at: string;
}

export interface Turn {
  role: "agent" | "user";
  content: string;
}

export interface AppointmentData {
  id: number;
  customer_name: string;
  phone: string;
  address: string;
  zip: string;
  issue_type: string;
  issue_label: string;
  issue_description: string | null;
  system_info: string | null;
  urgency: "routine" | "urgent";
  slot_start: string;
  slot_end: string;
  window_label: string;
  short_label: string;
  sms_sent: boolean;
  added_to_calendar: boolean;
}

export interface SmsPreview {
  to: string;
  body: string;
  sent: boolean;
}

export interface EmailPreview {
  to: string;
  subject: string;
  body: string;
  sent: boolean;
  final?: boolean;
}

export interface CallEvents {
  call: {
    call_id: string;
    status: "in_progress" | "ended";
    outcome: "booked" | "emergency" | "callback" | "info_only" | "abandoned" | null;
    urgency: string | null;
    duration: number | null;
    summary: string | null;
    summary_ready: boolean;
    transcript: Turn[];
  };
  events: TimelineEvent[];
  appointment: AppointmentData | null;
  notifications: {
    confirmation_sms: SmsPreview | null;
    owner_alert: { sms: SmsPreview; email: EmailPreview } | null;
    owner_summary: EmailPreview | null;
  };
}

export interface DayWindow {
  start: string;
  end: string;
  label: string;
  status: "booked" | "open" | "past";
  appointment: AppointmentData | null;
}

export interface DayView {
  date: string;
  timezone: string;
  closed: boolean;
  windows: DayWindow[];
  appointments: AppointmentData[];
}

export interface Stats {
  calls_today: number;
  booked: number;
  emergencies: number;
  callbacks: number;
  average_job_value: number;
  revenue_protected: number;
}

export interface CallRow {
  call_id: string;
  channel: "web" | "chat" | "phone";
  started_at: string;
  status: "in_progress" | "ended";
  outcome: "booked" | "emergency" | "callback" | "info_only" | "abandoned" | null;
  urgency: string | null;
  caller: string | null;
  duration: number | null;
  summary: string | null;
  appointment: string | null;
}

export interface WebCall {
  call_id: string;
  access_token: string;
  transport: "livekit" | "gateway" | null;
  ice_servers: RTCIceServer[] | null;
  expires_at: number | null;
  max_seconds: number;
}

export interface ChatSession {
  chat_id: string;
  max_seconds: number;
  max_messages: number;
}

export interface ChatReply {
  replies: string[];
  tools: string[];
}
