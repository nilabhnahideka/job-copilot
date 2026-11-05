/**
 * Where the login token is kept in the browser.
 *
 * localStorage keeps you logged in across tabs and restarts (until the token
 * expires after 7 days). Access is wrapped in try/catch because some browsers
 * block storage (e.g. strict private modes); the app then just keeps the token
 * in memory for this tab.
 */

const KEY = "job-copilot.token";
let memoryToken: string | null = null;

export function getToken(): string | null {
  try {
    return localStorage.getItem(KEY) ?? memoryToken;
  } catch {
    return memoryToken;
  }
}

export function setToken(token: string): void {
  memoryToken = token;
  try {
    localStorage.setItem(KEY, token);
  } catch {}
}

export function clearToken(): void {
  memoryToken = null;
  try {
    localStorage.removeItem(KEY);
  } catch {}
}
