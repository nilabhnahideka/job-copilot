"use client";

/**
 * Route /. The application board: every analysed job, grouped by status.
 */
import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorNote } from "@/components/ui";
import { api, type Application, type ApplicationStatus, STATUS_LABEL, STATUSES } from "@/lib/api";

const COLUMNS: ApplicationStatus[] = ["draft", "ready", "applied", "interviewing", "offer", "rejected"];

export default function Board() {
  const [apps, setApps] = useState<Application[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listApplications().then(setApps).catch((e) => setError(e.message));
  }, []);

  async function move(app: Application, status: ApplicationStatus) {
    setApps((prev) => prev?.map((a) => (a.id === app.id ? { ...a, status } : a)) ?? null);
    try {
      await api.updateApplication(app.id, { status });
    } catch (e) {
      setError((e as Error).message);
      setApps((prev) => prev?.map((a) => (a.id === app.id ? app : a)) ?? null);
    }
  }

  if (error) return <ErrorNote message={error} />;
  if (!apps) return <p className="text-graphite">Loading applications…</p>;

  if (apps.length === 0) {
    return (
      <section className="max-w-xl py-10">
        <h1 className="font-serif text-4xl font-medium leading-tight">
          Paste a job post. Get an honest fit check and a tailored application.
        </h1>
        <p className="mt-4 text-graphite">
          Start by adding your resume, then analyse your first job. Every application you analyse lands
          on this board so you can track it from draft to offer.
        </p>
        <div className="mt-6 flex gap-3">
          <Link href="/resume" className="rounded-sm bg-ink px-3.5 py-2 text-sm font-medium text-sheet">
            Add your resume
          </Link>
          <Link href="/new" className="rounded-sm border border-ink/30 px-3.5 py-2 text-sm font-medium">
            Analyse a job
          </Link>
        </div>
      </section>
    );
  }

  return (
    <>
      <h1 className="mb-6 font-serif text-3xl font-medium">Applications</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {COLUMNS.map((col) => {
          const items = apps.filter((a) => a.status === col);
          return (
            <section key={col} aria-labelledby={`col-${col}`} className="min-w-0">
              <h2 id={`col-${col}`} className="mb-2 flex items-baseline justify-between border-b border-ink/80 pb-1.5 text-sm font-semibold">
                {STATUS_LABEL[col]}
                <span className="font-normal text-graphite">{items.length}</span>
              </h2>
              <ul className="space-y-2">
                {items.map((a) => (
                  <li key={a.id} className="border border-rule bg-sheet p-3">
                    <Link href={`/applications/${a.id}`} className="block hover:underline">
                      <span className="block font-medium leading-snug">{a.title || "Untitled role"}</span>
                      <span className="block text-sm text-graphite">{a.company || "Unknown company"}</span>
                    </Link>
                    <div className="mt-2 flex items-center justify-between gap-2">
                      {a.fit_score != null && (
                        <span className="whitespace-nowrap text-sm tabular-nums">
                          <span className="highlight font-semibold">{a.fit_score}</span>
                          <span className="text-graphite"> fit</span>
                        </span>
                      )}
                      <label className="sr-only" htmlFor={`move-${a.id}`}>
                        Move {a.title}
                      </label>
                      <select
                        id={`move-${a.id}`}
                        value={a.status}
                        onChange={(e) => move(a, e.target.value as ApplicationStatus)}
                        className="ml-auto max-w-[8.5rem] rounded-sm border border-rule bg-sheet px-1 py-0.5 text-xs text-graphite"
                      >
                        {STATUSES.map((s) => (
                          <option key={s} value={s}>
                            {STATUS_LABEL[s]}
                          </option>
                        ))}
                      </select>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
    </>
  );
}
