/**
 * Root layout: page shell with the top navigation bar, shared by every page.
 * <AuthProvider> makes "who is logged in" available everywhere.
 */
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";
import { NavLinks } from "@/components/NavLinks";

export const metadata: Metadata = {
  title: "Job Copilot",
  description: "Tailor every job application without making anything up.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="antialiased">
      <body className="min-h-screen">
        <AuthProvider>
          <header className="border-b border-rule bg-sheet">
            <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-2 px-5 py-3">
              <Link href="/" className="font-serif text-xl font-semibold tracking-tight">
                Job Copilot
              </Link>
              <Suspense fallback={null}>
                <NavLinks />
              </Suspense>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
