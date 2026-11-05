import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import "./globals.css";
import { NavLinks } from "@/components/NavLinks";

export const metadata: Metadata = {
  title: "Job Copilot",
  description: "Tailor every job application without making anything up.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="antialiased">
      <body className="min-h-screen">
        <header className="border-b border-rule bg-sheet">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-2 px-5 py-3">
            <Link href="/" className="font-serif text-xl font-semibold tracking-tight">
              Job Copilot
            </Link>
            <Suspense fallback={<span className="text-sm text-graphite">Applications</span>}>
              <NavLinks />
            </Suspense>
            <Link
              href="/new"
              className="ml-auto rounded-sm bg-ink px-3.5 py-1.5 text-sm font-medium text-sheet hover:bg-ink/90"
            >
              Analyse a job
            </Link>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>
      </body>
    </html>
  );
}
