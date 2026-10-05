// API client: talks to the FastAPI backend with the JWT issued by Supabase Auth (GoTrue).
// v1 keeps the token in localStorage; moving it to an httpOnly cookie is a later hardening step.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const AUTH_URL = process.env.NEXT_PUBLIC_AUTH_URL ?? "http://localhost:9999";
const TOKEN_KEY = "ra.token";
const REFRESH_KEY = "ra.refresh";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function setTokens(access: string | null, refresh: string | null) {
  try {
    if (access) localStorage.setItem(TOKEN_KEY, access);
    else localStorage.removeItem(TOKEN_KEY);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
    else localStorage.removeItem(REFRESH_KEY);
  } catch {
    /* storage unavailable: the session just will not persist */
  }
}

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((d: { msg: string }) => d.msg).join("; ");
    return body.msg ?? body.message ?? body.error_description ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (res.status === 401 && token && (await refreshSession())) {
    headers.set("Authorization", `Bearer ${getToken()}`);
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  }
  if (!res.ok) throw new ApiError(res.status, await readError(res));
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---- auth

export async function login(email: string, password: string): Promise<void> {
  const res = await fetch(`${AUTH_URL}/token?grant_type=password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new ApiError(res.status, await readError(res));
  const body = await res.json();
  setTokens(body.access_token, body.refresh_token);
}

async function refreshSession(): Promise<boolean> {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  const res = await fetch(`${AUTH_URL}/token?grant_type=refresh_token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    setTokens(null, null);
    return false;
  }
  const body = await res.json();
  setTokens(body.access_token, body.refresh_token);
  return true;
}

export function logout() {
  setTokens(null, null);
}

export interface SignupInput {
  email: string;
  password: string;
  invite_code: string;
  accept_terms: boolean;
  accept_privacy: boolean;
  accept_disclaimer: boolean;
  is_adult: boolean;
}

export async function signup(input: SignupInput): Promise<void> {
  await api("/auth/signup", { method: "POST", body: JSON.stringify(input) });
  await login(input.email, input.password);
}

// ---- types mirrored from api/schemas.py

export interface Runner {
  id: string;
  display_name: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  sex: string | null;
  birth_year: number | null;
  profile_complete: boolean;
}

export interface Me {
  account_id: string;
  email: string;
  role: string;
  runner: Runner;
  notify_analysis_ready: boolean;
}

export interface Video {
  slot: "side_a" | "side_b" | "rear"; // upload slot
  view: "left_side" | "right_side" | "rear" | "side"; // "side" until the running direction is recognized
  uploaded: boolean;
  deleted: boolean;
  duration_s: number | null;
  container_fps: number | null;
  capture_fps: number | null;
  check_result: Record<string, unknown> | null;
}

export interface Session {
  id: string;
  recorded_on: string;
  speed_kmh: number;
  incline_pct: number;
  shoes: string | null;
  state: string;
  created_at: string;
  videos: Video[];
  analysis_state: string | null;
  analysis_progress: string | null;
  progress_pct: number | null;
  eta_seconds: number | null;
  queue_position: number | null;
  failure_reason: string | null;
  failure_report: "asked" | "open" | "closed" | null; // docs/SPEC.md §11
}

export function formatEta(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "";
  if (seconds < 90) return "about a minute";
  const min = Math.round(seconds / 60);
  if (min < 60) return `about ${min} minutes`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `about ${h} h${m ? ` ${m} min` : ""}`;
}

export interface UploadTarget {
  slot: "side_a" | "side_b" | "rear";
  url: string;
  max_bytes: number;
}

export interface Metric {
  metric_key: string;
  view: string;
  side: string;
  label: string;
  unit: string | null;
  mean: number | null;
  sd: number | null;
  n_cycles: number;
  mean_score: number | null;
  state: "measured" | "descriptor" | "unmeasurable";
  reason: string | null;
  value_text: string | null;
  typical_low: number | null;
  typical_high: number | null;
  source_id: string | null;
  advice_eligible: boolean;
  per_view: Record<string, number | null> | null; // whole-body Metric from two Side Views
  unreliable_reason: string | null; // Recording Check warning that may bias the value
}

export interface Analysis {
  session: Session;
  pipeline_version: string;
  finished_at: string | null;
  window: Record<string, { start_frame: number; end_frame: number; fps: number; source_fps?: number } | null> | null;
  camera_check: Record<string, unknown> | null;
  video_urls: Record<string, string>;
  keypoints_urls: Record<string, string>;
  metrics: Metric[];
  advice: { metric_key: string; body: string }[];
  info: { sources: Record<string, { title: string; url: string }> } | null;
}

export const FAILURE_TEXT: Record<string, string> = {
  too_large: "The video is larger than 1 GB. Trim it to the running part, 20–30 seconds are enough.",
  fps_too_low: "The video has fewer than 60 frames per second. Record at 60 fps or more, or use slow motion for the whole clip.",
  too_short: "The video is shorter than 20 seconds of running.",
  runner_not_found: "No runner could be found in the video. Make sure the whole body is in frame.",
  body_not_fully_visible: "The legs are not fully visible. Move the camera back or raise it.",
  no_steady_running: "No stretch of steady running was found. Start recording once you are at speed and keep running for 20–30 seconds.",
  camera_too_low: "The camera was too low: angles cannot be measured reliably. Place the phone at hip height.",
  internal_error: "Something went wrong on our side. The team has been notified.",
  same_side: "Both side videos show the same side of the runner. Replace one with a video filmed from the other side of the treadmill.",
  no_side_video: "A side view video is required.",
  not_side_view: "The running direction cannot be recognized: film from the side, with the phone perpendicular to the belt.",
  video_rejected: "One of the videos was rejected by the recording check: replace or remove it.",
  checks_pending: "The videos are still being checked. Try again in a few seconds.",
  email_mismatch: "The email does not match your account.",
};
