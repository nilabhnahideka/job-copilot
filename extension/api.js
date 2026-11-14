// Talks to the Job Copilot API (the same one the website uses).
//
// Settings and the login token are kept in chrome.storage.local: private to this
// browser profile and this extension. The extension can call the API directly
// (no CORS setup needed) because its address is listed in manifest.json
// under host_permissions.

import { DEFAULT_API_URL, DEFAULT_WEB_URL } from "./config.js";

const store = chrome.storage.local;

/** Forgiving about how an address was typed: trims, removes trailing "/", adds https://. */
export function normaliseUrl(raw) {
  const url = (raw || "").trim().replace(/\/+$/, "");
  if (!url) return "";
  return url.includes("://") ? url : `https://${url}`;
}

export async function getSettings() {
  const s = await store.get(["apiUrl", "webUrl"]);
  return {
    apiUrl: normaliseUrl(s.apiUrl || DEFAULT_API_URL),
    webUrl: normaliseUrl(s.webUrl || DEFAULT_WEB_URL),
  };
}

export async function saveSettings({ apiUrl, webUrl }) {
  await store.set({ apiUrl: normaliseUrl(apiUrl), webUrl: normaliseUrl(webUrl) });
}

export async function getSession() {
  const { token, email } = await store.get(["token", "email"]);
  return token ? { token, email } : null;
}

export async function logout() {
  await store.remove(["token", "email"]);
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

/** Turns FastAPI's error body into one readable sentence. */
function errorMessage(body, fallback) {
  const detail = body && body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0];
    const field = (first.loc || []).filter((p) => p !== "body").join(" › ");
    return field ? `${field}: ${first.msg}` : first.msg || fallback;
  }
  return fallback;
}

async function send(path, init = {}) {
  const { apiUrl } = await getSettings();
  const session = await getSession();
  const headers = { ...(init.headers || {}) };
  if (session) headers.Authorization = `Bearer ${session.token}`;

  let res;
  try {
    res = await fetch(`${apiUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      `Can't reach the API at ${apiUrl}. On the free plan it may be waking up; wait a minute and try again.`,
      0,
    );
  }
  if (res.status === 401 && !path.startsWith("/api/auth/")) {
    await logout(); // token expired or invalid: log in again
    throw new ApiError("Your login expired. Log in again.", 401);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(errorMessage(body, `Request failed (${res.status})`), res.status);
  }
  return res;
}

const json = (body) => ({ headers: { "content-type": "application/json" }, body: JSON.stringify(body) });

export async function login(email, password) {
  const res = await send("/api/auth/login", { method: "POST", ...json({ email, password }) });
  const data = await res.json();
  await store.set({ token: data.access_token, email: data.user.email });
  return data.user;
}

export async function getProfile() {
  return (await send("/api/profile")).json();
}

/**
 * Runs the agent on a job post and calls `onEvent` for each progress event:
 * {type:"created", id} → {type:"node", node}… → {type:"done", application} or {type:"error", detail}.
 */
export async function analyseJob({ jobText, jobUrl }, onEvent) {
  const res = await send("/api/applications/stream", {
    method: "POST",
    ...json({ job_text: jobText, job_url: jobUrl || "" }),
  });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";
    for (const chunk of chunks) {
      const line = chunk.trim();
      if (line.startsWith("data: ")) onEvent(JSON.parse(line.slice(6)));
    }
  }
}
