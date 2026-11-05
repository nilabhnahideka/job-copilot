"use client";

/**
 * The log in and sign up form (same fields, different button and API call).
 * After success it goes to `?next=` if that's a page on this site, otherwise
 * to the board (log in) or the profile page (sign up, to start setting it up).
 */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { Button, ErrorNote } from "@/components/ui";

/** Only follow `next` to pages on this site, never to another website. */
function safeNext(fallback: string): string {
  const next = new URLSearchParams(window.location.search).get("next");
  return next && next.startsWith("/") && !next.startsWith("//") ? next : fallback;
}

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const { login, signup } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isSignup = mode === "signup";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (isSignup) {
        await signup(email, password);
        router.replace("/profile");
      } else {
        await login(email, password);
        router.replace(safeNext("/"));
      }
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-sm space-y-4 py-6">
      <h1 className="font-serif text-3xl font-medium">{isSignup ? "Create your account" : "Log in"}</h1>
      {isSignup && (
        <p className="text-graphite">Set up your profile once, and every application starts from it.</p>
      )}

      <label className="block text-sm font-medium">
        Email
        <input
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 block w-full rounded-sm border border-rule bg-sheet px-3 py-2 font-normal"
        />
      </label>

      <label className="block text-sm font-medium">
        Password
        <input
          type="password"
          required
          minLength={isSignup ? 8 : undefined}
          maxLength={128}
          autoComplete={isSignup ? "new-password" : "current-password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 block w-full rounded-sm border border-rule bg-sheet px-3 py-2 font-normal"
        />
        {isSignup && <span className="mt-1 block text-xs font-normal text-graphite">At least 8 characters</span>}
      </label>

      <ErrorNote message={error} />
      <Button type="submit" disabled={busy} className="w-full">
        {busy ? (isSignup ? "Creating account…" : "Logging in…") : isSignup ? "Create account" : "Log in"}
      </Button>

      <p className="text-sm text-graphite">
        {isSignup ? "Already have an account? " : "New here? "}
        <Link href={isSignup ? "/login" : "/signup"} className="text-ink underline">
          {isSignup ? "Log in" : "Create an account"}
        </Link>
      </p>
    </form>
  );
}
