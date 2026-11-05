/**
 * Typed client for the FastAPI backend.
 *
 * Every request carries the login token (see auth-token.ts). If the API answers
 * 401 (not logged in, or the token expired), the token is cleared and
 * `onUnauthorized` listeners are told, so the app can send you to the login page.
 * The types here mirror the backend's Pydantic models.
 */

import { clearToken, getToken } from "@/lib/auth-token";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types: agent and applications
// ---------------------------------------------------------------------------
export type Importance = "must_have" | "nice_to_have";
export type MatchLevel = "strong" | "partial" | "missing";
export type Verdict = "strong_fit" | "good_fit" | "stretch" | "poor_fit";
export type ReviewTarget = "bullets" | "cover_letter" | "outreach";

export const STATUSES = ["draft", "ready", "applied", "interviewing", "offer", "rejected", "archived"] as const;
export type ApplicationStatus = (typeof STATUSES)[number];

export const STATUS_LABEL: Record<ApplicationStatus, string> = {
  draft: "To review",
  ready: "Ready to send",
  applied: "Applied",
  interviewing: "Interviewing",
  offer: "Offer",
  rejected: "Rejected",
  archived: "Archived",
};

export interface Experience {
  title: string;
  company: string;
  start?: string | null;
  end?: string | null;
  bullets: string[];
}

export interface ResumeProfile {
  name: string;
  headline: string;
  summary: string;
  email: string;
  phone: string;
  location: string;
  linkedin_url: string;
  github_url: string;
  portfolio_url: string;
  skills: string[];
  experience: Experience[];
  projects: { name: string; description: string; tech: string[]; bullets: string[] }[];
  education: string[];
}

export interface Resume {
  id: number;
  label: string;
  file_name: string;
  has_file: boolean;
  profile: ResumeProfile;
  created_at: string;
}

export interface RequirementMatch {
  requirement: string;
  importance: Importance;
  level: MatchLevel;
  evidence: string;
}

export interface MatchReport {
  matches: RequirementMatch[];
  strengths: string[];
  gaps: string[];
  suggestions: string[];
  fit_score: number;
  verdict: Verdict;
  missing_keywords: string[];
}

export interface TailoredBullet {
  original: string;
  rewritten: string;
  reason: string;
}

export interface AgentState {
  job?: { title: string; company: string; seniority: string; summary: string; keywords: string[] };
  match?: MatchReport;
  bullets?: TailoredBullet[];
  cover_letter?: string;
  outreach?: string;
  review_history?: { action: string; target: ReviewTarget | null; feedback: string }[];
}

export interface Application {
  id: number;
  resume_id: number;
  company: string;
  title: string;
  job_url: string;
  status: ApplicationStatus;
  fit_score: number | null;
  notes: string;
  created_at: string;
  updated_at: string;
  awaiting_review: boolean;
  agent: AgentState;
}

export const VERDICT_LABEL: Record<Verdict, string> = {
  strong_fit: "Strong fit",
  good_fit: "Good fit",
  stretch: "Stretch",
  poor_fit: "Poor fit",
};

// ---------------------------------------------------------------------------
// Types: accounts and profile (mirror backend/app/profile_schema.py)
// ---------------------------------------------------------------------------
export interface User {
  id: number;
  email: string;
  created_at: string;
}

export type YesNo = "yes" | "no";
export type WorkMode = "remote" | "hybrid" | "onsite";
export type JobType = "full_time" | "internship" | "contract" | "part_time";
export type ExperienceLevel = "internship" | "entry" | "mid" | "senior" | "lead";

export interface EducationEntry {
  degree: string;
  field_of_study: string;
  institution: string;
  start_year: number | null;
  end_year: number | null;
  grade: string;
}

export interface ProfileData {
  personal: {
    first_name: string;
    last_name: string;
    preferred_name: string;
    email: string;
    phone: string;
    city: string;
    state: string;
    country: string;
    linkedin_url: string;
    github_url: string;
    portfolio_url: string;
  };
  education: {
    entries: EducationEntry[];
    class_10_percentage: number | null;
    class_12_percentage: number | null;
  };
  work: {
    total_experience_years: number | null;
    current_company: string;
    current_title: string;
    skills: string[];
  };
  preferences: {
    titles: string[];
    locations: string[];
    work_modes: WorkMode[];
    job_types: JobType[];
    experience_level: ExperienceLevel | null;
    salary_min_lpa: number | null;
    salary_max_lpa: number | null;
    excluded_companies: string[];
  };
  answers: {
    notice_period_days: number | null;
    currently_serving_notice: YesNo | null;
    last_working_day: string | null;
    current_ctc_lpa: number | null;
    expected_ctc_lpa: number | null;
    willing_to_relocate: YesNo | null;
    authorized_to_work_in_india: YesNo | null;
    requires_visa_sponsorship: YesNo | null;
    languages: string[];
  };
  demographics: {
    date_of_birth: string | null;
    gender: "female" | "male" | "non_binary" | "prefer_not_to_say" | null;
    disability: YesNo | "prefer_not_to_say" | null;
    veteran: YesNo | "prefer_not_to_say" | null;
  };
}

export interface Profile {
  data: ProfileData;
  active_resume: { id: number; label: string; file_name: string; created_at: string } | null;
  missing: string[];
  updated_at: string;
}

export interface SavedAnswer {
  id: number;
  question: string;
  answer: string;
  source: "manual" | "application";
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Requests
// ---------------------------------------------------------------------------
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

type Listener = () => void;
const unauthorizedListeners = new Set<Listener>();

/** Called whenever the API says you're not logged in. Returns an unsubscribe function. */
export function onUnauthorized(fn: Listener): () => void {
  unauthorizedListeners.add(fn);
  return () => unauthorizedListeners.delete(fn);
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Turns FastAPI's error body into one readable sentence. */
function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    // Validation errors: [{loc: ["body", "preferences", "salary_min_lpa"], msg: "..."}]
    const first = detail[0] as { loc?: unknown[]; msg?: string };
    const field = first.loc?.filter((p) => p !== "body").join(" › ");
    return field ? `${field}: ${first.msg}` : (first.msg ?? fallback);
  }
  return fallback;
}

async function send(path: string, init: RequestInit = {}): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers: { ...authHeaders(), ...init.headers } });
  } catch {
    throw new ApiError(`Can't reach the API at ${API_URL}. Is the backend running?`, 0);
  }
  if (res.status === 401 && !path.startsWith("/api/auth/")) {
    clearToken();
    unauthorizedListeners.forEach((fn) => fn());
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(errorMessage(body, `Request failed (${res.status})`), res.status);
  }
  return res;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await send(path, init);
  return res.status === 204 ? (undefined as T) : res.json();
}

const json = (body: unknown): RequestInit => ({
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  // accounts
  signup: (email: string, password: string) =>
    request<{ access_token: string; user: User }>("/api/auth/signup", { method: "POST", ...json({ email, password }) }),
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>("/api/auth/login", { method: "POST", ...json({ email, password }) }),
  me: () => request<User>("/api/auth/me"),

  // profile
  getProfile: () => request<Profile>("/api/profile"),
  saveProfile: (data: ProfileData) => request<Profile>("/api/profile", { method: "PUT", ...json(data) }),
  setActiveResume: (resume_id: number) =>
    request<Profile>("/api/profile/active-resume", { method: "PUT", ...json({ resume_id }) }),

  listAnswers: () => request<SavedAnswer[]>("/api/profile/answers"),
  addAnswer: (question: string, answer: string) =>
    request<SavedAnswer>("/api/profile/answers", { method: "POST", ...json({ question, answer }) }),
  editAnswer: (id: number, body: { question?: string; answer?: string }) =>
    request<SavedAnswer>(`/api/profile/answers/${id}`, { method: "PATCH", ...json(body) }),
  deleteAnswer: (id: number) => request<void>(`/api/profile/answers/${id}`, { method: "DELETE" }),

  // resumes
  listResumes: () => request<Resume[]>("/api/resumes"),
  uploadResume: (input: { file?: File; text?: string; label?: string }) => {
    const form = new FormData();
    if (input.file) form.append("file", input.file);
    if (input.text) form.append("text", input.text);
    if (input.label) form.append("label", input.label);
    return request<Resume & { prefilled: string[] }>("/api/resumes", { method: "POST", body: form });
  },
  /** Downloads the original file (needs the login token, so it can't be a plain link). */
  downloadResume: async (id: number, fileName: string) => {
    const blob = await (await send(`/api/resumes/${id}/file`)).blob();
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement("a"), { href: url, download: fileName || "resume" });
    document.body.appendChild(a); // some browsers only download links that are on the page
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },

  // applications
  listApplications: () => request<Application[]>("/api/applications"),
  getApplication: (id: number | string) => request<Application>(`/api/applications/${id}`),
  updateApplication: (id: number, body: Partial<Pick<Application, "status" | "notes">>) =>
    request<Application>(`/api/applications/${id}`, { method: "PATCH", ...json(body) }),
  deleteApplication: (id: number) => request<void>(`/api/applications/${id}`, { method: "DELETE" }),
  review: (id: number, body: { action: "approve" } | { action: "revise"; target: ReviewTarget; feedback: string }) =>
    request<Application>(`/api/applications/${id}/review`, { method: "POST", ...json(body) }),
};

export type StreamEvent =
  | { type: "created"; id: number }
  | { type: "node"; node: string }
  | { type: "done"; application: Application }
  | { type: "error"; detail: string };

/** Runs the agent and calls `onEvent` for each server-sent event. */
export async function createApplicationStream(
  body: { resume_id?: number; job_text: string; job_url?: string },
  onEvent: (e: StreamEvent) => void,
): Promise<void> {
  const res = await send("/api/applications/stream", { method: "POST", ...json(body) });
  if (!res.body) throw new ApiError("The server sent an empty response", res.status);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const line = chunk.trim();
      if (line.startsWith("data: ")) onEvent(JSON.parse(line.slice(6)));
    }
  }
}
