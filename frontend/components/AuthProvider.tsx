"use client";

/**
 * Knows who is logged in, for the whole app.
 *
 * - On load, if a token is saved, asks the API who it belongs to (`/api/auth/me`).
 * - `login` / `signup` save the new token; `logout` forgets it.
 * - If any API call says "not logged in" (expired token), you're logged out here too.
 *
 * <RequireAuth> wraps pages that need an account and sends visitors to /login,
 * remembering the page they wanted so they come back to it after logging in.
 */
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, onUnauthorized, type User } from "@/lib/api";
import { clearToken, getToken, setToken } from "@/lib/auth-token";

type AuthState = {
  user: User | null;
  /** True until we know whether a saved token is still valid. */
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // No saved token: nothing to check. Otherwise ask the API whose token it is.
    const check = getToken() ? api.me().then(setUser) : Promise.resolve();
    check.catch(() => clearToken()).finally(() => setLoading(false));
  }, []);

  useEffect(() => onUnauthorized(() => setUser(null)), []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const signup = useCallback(async (email: string, password: string) => {
    const res = await api.signup(email, password);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, login, signup, logout }), [user, loading, login, signup, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const path = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace(`/login?next=${encodeURIComponent(path)}`);
  }, [loading, user, router, path]);

  if (!user) return <p className="text-graphite">{loading ? "Loading…" : "Taking you to log in…"}</p>;
  return <>{children}</>;
}
