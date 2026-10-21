export interface Scenario {
  id: string;
  title: string;
  subtitle: string;
  tone: "urgent" | "emergency" | "neutral";
  script: string;
}

export interface Branding {
  agency: { name: string; show_powered_by: boolean };
  badge: string;
  tagline: string;
  accent_color: string;
  logo_url: string;
  scenarios: Scenario[];
  demo_tips: string[];
  company: { name: string; location: string; timezone: string; greeting: string; dispatch_fee: string };
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
