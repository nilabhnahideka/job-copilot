"use client";

/**
 * Route /new. Paste a job post and run the agent, showing each step live as the
 * backend streams progress events. Redirects to the application page when done.
 */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button, ErrorNote } from "@/components/ui";
import { api, createApplicationStream, type Resume } from "@/lib/api";

const STEPS: { node: string; label: string }[] = [
  { node: "parse_job", label: "Reading the job post" },
  { node: "match_resume", label: "Checking each requirement against your resume" },
  { node: "tailor_bullets", label: "Rewriting your resume bullets for this role" },
  { node: "check_grounding", label: "Fact-checking the rewrites against your resume" },
  { node: "draft_cover_letter", label: "Writing the cover letter" },
  { node: "draft_outreach", label: "Writing a message for the recruiter" },
];

export default function NewApplication() {
  const router = useRouter();
  const [resumes, setResumes] = useState<Resume[] | null>(null);
  const [resumeId, setResumeId] = useState<number | null>(null);
  const [jobText, setJobText] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [running, setRunning] = useState(false);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listResumes()
      .then((r) => {
        setResumes(r);
        if (r[0]) setResumeId(r[0].id);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!resumeId) return;
    setRunning(true);
    setCounts({});
    setError(null);
    try {
      await createApplicationStream({ resume_id: resumeId, job_text: jobText, job_url: jobUrl }, (ev) => {
        if (ev.type === "node") setCounts((c) => ({ ...c, [ev.node]: (c[ev.node] ?? 0) + 1 }));
        if (ev.type === "error") throw new Error(ev.detail);
        if (ev.type === "done") router.push(`/applications/${ev.application.id}`);
      });
    } catch (err) {
      setError((err as Error).message);
      setRunning(false);
    }
  }

  if (resumes && resumes.length === 0) {
    return (
      <div className="max-w-lg">
        <h1 className="font-serif text-3xl font-medium">Add your resume first</h1>
        <p className="mt-3 text-graphite">Each job is checked against your resume, so the agent needs one to work from.</p>
        <Link href="/resume" className="mt-5 inline-block rounded-sm bg-ink px-3.5 py-2 text-sm font-medium text-sheet">
          Add your resume
        </Link>
      </div>
    );
  }

  return (
    <div className="grid gap-10 lg:grid-cols-[1fr_20rem]">
      <form onSubmit={run} className="space-y-4">
        <h1 className="font-serif text-3xl font-medium">Analyse a job</h1>

        {resumes && resumes.length > 1 && (
          <label className="block text-sm font-medium">
            Resume
            <select
              value={resumeId ?? ""}
              onChange={(e) => setResumeId(Number(e.target.value))}
              className="mt-1 block w-full rounded-sm border border-rule bg-sheet px-3 py-2 font-normal"
            >
              {resumes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="block text-sm font-medium">
          Job description
          <textarea
            required
            minLength={50}
            value={jobText}
            onChange={(e) => setJobText(e.target.value)}
            rows={16}
            disabled={running}
            placeholder="Paste the whole posting, including requirements and responsibilities."
            className="mt-1 block w-full rounded-sm border border-rule bg-sheet px-3 py-2 font-serif text-[15px] font-normal leading-relaxed"
          />
        </label>

        <label className="block text-sm font-medium">
          Link to the posting <span className="font-normal text-graphite">(optional, for your tracker)</span>
          <input
            type="url"
            value={jobUrl}
            onChange={(e) => setJobUrl(e.target.value)}
            disabled={running}
            className="mt-1 block w-full rounded-sm border border-rule bg-sheet px-3 py-2 font-normal"
          />
        </label>

        <ErrorNote message={error} />
        <Button type="submit" disabled={running || !resumeId || jobText.trim().length < 50}>
          {running ? "Analysing…" : "Analyse job"}
        </Button>
      </form>

      <aside aria-live="polite" className="lg:pt-14">
        <h2 className="mb-3 text-sm font-semibold">What the agent does</h2>
        <ol className="space-y-3">
          {STEPS.map((s, i) => {
            const n = counts[s.node] ?? 0;
            const done = n > 0;
            return (
              <li key={s.node} className="flex gap-3 text-sm">
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs tabular-nums ${
                    done ? "border-ink bg-ink text-sheet" : "border-rule text-graphite"
                  }`}
                  aria-hidden
                >
                  {done ? "✓" : i + 1}
                </span>
                <span className={done ? "text-ink" : "text-graphite"}>
                  {s.label}
                  {s.node === "check_grounding" && n > 1 && (
                    <span className="block text-xs text-redpen">Caught an overstatement and rewrote it</span>
                  )}
                </span>
              </li>
            );
          })}
        </ol>
      </aside>
    </div>
  );
}
