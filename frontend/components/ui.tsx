"use client";

/**
 * Small shared UI pieces: buttons, the copy-to-clipboard button, error messages.
 */
import { useState } from "react";

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="border-l-2 border-redpen bg-sheet px-3 py-2 text-sm text-redpen">
      {message}
    </p>
  );
}

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="rounded-sm border border-rule px-2.5 py-1 text-xs text-graphite hover:border-ink hover:text-ink"
    >
      {copied ? "Copied" : label}
    </button>
  );
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" }) {
  const base =
    "rounded-sm px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50";
  const styles =
    variant === "primary"
      ? "bg-ink text-sheet hover:bg-ink/90"
      : "border border-ink/30 bg-sheet text-ink hover:border-ink";
  return <button className={`${base} ${styles} ${className}`} {...props} />;
}
