// Typed client for the FastAPI backend.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Importance = "must_have" | "nice_to_have";
export type MatchLevel = "strong" | "partial" | "missing";
export type Verdict = "strong_fit" | "good_fit" | "stretch" | "poor_fit";
export type ReviewTarget = "bullets" | "cover_letter" | "outreach";

export const STATUSES = [
  "draft",
  "ready",
  "applied",
  "interviewing",
  "offer",
  "rejected",
  "archived",
] as const;
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
  skills: string[];
  experience: Experience[];
  projects: { name: string; description: string; tech: string[]; bullets: string[] }[];
  education: string[];
}

export interface Resume {
  id: number;
  label: string;
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new Error(`Can't reach the API at ${API_URL}. Is the backend running?`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

const json = (body: unknown): RequestInit => ({
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  listResumes: () => request<Resume[]>("/api/resumes"),

  uploadResume: (input: { file?: File; text?: string; label?: string }) => {
    const form = new FormData();
    if (input.file) form.append("file", input.file);
    if (input.text) form.append("text", input.text);
    if (input.label) form.append("label", input.label);
    return request<Resume>("/api/resumes", { method: "POST", body: form });
  },

  listApplications: () => request<Application[]>("/api/applications"),
  getApplication: (id: number | string) => request<Application>(`/api/applications/${id}`),

  updateApplication: (id: number, body: Partial<Pick<Application, "status" | "notes">>) =>
    request<Application>(`/api/applications/${id}`, { method: "PATCH", ...json(body) }),

  deleteApplication: (id: number) => request<void>(`/api/applications/${id}`, { method: "DELETE" }),

  review: (
    id: number,
    body: { action: "approve" } | { action: "revise"; target: ReviewTarget; feedback: string },
  ) => request<Application>(`/api/applications/${id}/review`, { method: "POST", ...json(body) }),
};

export type StreamEvent =
  | { type: "created"; id: number }
  | { type: "node"; node: string }
  | { type: "done"; application: Application }
  | { type: "error"; detail: string };

/** Runs the agent and calls `onEvent` for each server-sent event. */
export async function createApplicationStream(
  body: { resume_id: number; job_text: string; job_url?: string },
  onEvent: (e: StreamEvent) => void,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/applications/stream`, { method: "POST", ...json(body) });
  } catch {
    throw new Error(`Can't reach the API at ${API_URL}. Is the backend running?`);
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`);
  }

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
