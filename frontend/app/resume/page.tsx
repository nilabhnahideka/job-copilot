"use client";

/**
 * Route /resume. Upload a PDF or paste resume text, and view the parsed profiles.
 */
import { useEffect, useState } from "react";
import { Button, ErrorNote } from "@/components/ui";
import { api, type Resume } from "@/lib/api";

export default function ResumePage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [label, setLabel] = useState("My resume");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listResumes().then(setResumes).catch((e) => setError(e.message));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api.uploadResume({ file: file ?? undefined, text: file ? undefined : text, label });
      setResumes((prev) => [r, ...prev]);
      setFile(null);
      setText("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,26rem)_1fr]">
      <form onSubmit={submit} className="space-y-4">
        <h1 className="font-serif text-3xl font-medium">Your resume</h1>
        <p className="text-graphite">
          Upload a PDF or paste the text. It&apos;s turned into a structured profile that every analysis
          checks against, so nothing gets claimed that isn&apos;t on it.
        </p>

        <label className="block text-sm font-medium">
          Name this version
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            className="mt-1 block w-full rounded-sm border border-rule bg-sheet px-3 py-2 font-normal"
          />
        </label>

        <label className="block text-sm font-medium">
          PDF or text file
          <input
            type="file"
            accept=".pdf,.txt"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="mt-1 block w-full text-sm font-normal file:mr-3 file:rounded-sm file:border file:border-ink/30 file:bg-sheet file:px-3 file:py-1.5 file:text-ink"
          />
        </label>

        {!file && (
          <label className="block text-sm font-medium">
            Or paste it
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={10}
              className="mt-1 block w-full rounded-sm border border-rule bg-sheet px-3 py-2 font-serif text-[15px] font-normal"
            />
          </label>
        )}

        <ErrorNote message={error} />
        <Button type="submit" disabled={busy || (!file && text.trim().length < 50)}>
          {busy ? "Reading your resume…" : "Save resume"}
        </Button>
      </form>

      <section aria-label="Saved resumes" className="space-y-6">
        {resumes.length === 0 && <p className="text-graphite">No resumes saved yet.</p>}
        {resumes.map((r) => (
          <article key={r.id} className="border border-rule bg-sheet p-6">
            <div className="flex items-baseline justify-between gap-4">
              <h2 className="font-serif text-2xl">{r.profile.name || r.label}</h2>
              <span className="text-sm text-graphite">{r.label}</span>
            </div>
            {r.profile.headline && <p className="text-graphite">{r.profile.headline}</p>}
            <p className="mt-4 text-sm leading-relaxed">
              {r.profile.skills.join(", ")}
            </p>
            {r.profile.experience.map((e, i) => (
              <div key={i} className="mt-4">
                <h3 className="font-medium">
                  {e.title}, {e.company}
                </h3>
                <ul className="mt-1 list-disc space-y-1 pl-5 font-serif text-[15px]">
                  {e.bullets.map((b, j) => (
                    <li key={j}>{b}</li>
                  ))}
                </ul>
              </div>
            ))}
          </article>
        ))}
      </section>
    </div>
  );
}
