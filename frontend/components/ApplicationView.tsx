"use client";

/**
 * Application page: fit score breakdown, gaps, tailored drafts and the
 * review step (ask for a revision or approve). Also status and notes.
 */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { RequirementStrip, StripLegend } from "@/components/RequirementStrip";
import { Button, CopyButton, ErrorNote } from "@/components/ui";
import {
  api,
  type Application,
  type ApplicationStatus,
  type ReviewTarget,
  STATUS_LABEL,
  STATUSES,
  type TailoredBullet,
  VERDICT_LABEL,
} from "@/lib/api";
import { diffRuns } from "@/lib/diff";

const TABS: { id: ReviewTarget; label: string; noun: string }[] = [
  { id: "bullets", label: "Resume bullets", noun: "the bullets" },
  { id: "cover_letter", label: "Cover letter", noun: "the cover letter" },
  { id: "outreach", label: "Recruiter message", noun: "the recruiter message" },
];

export function ApplicationView({ id }: { id: string }) {
  const router = useRouter();
  const [app, setApp] = useState<Application | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<ReviewTarget>("bullets");
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState<null | "revise" | "approve">(null);

  useEffect(() => {
    api.getApplication(id).then(setApp).catch((e) => setError(e.message));
  }, [id]);

  if (error && !app) return <ErrorNote message={error} />;
  if (!app) return <p className="text-graphite">Loading…</p>;

  const { match, bullets = [], cover_letter = "", outreach = "" } = app.agent;
  const current = TABS.find((t) => t.id === tab)!;

  async function review(action: "approve" | "revise") {
    if (!app) return;
    setBusy(action);
    setError(null);
    try {
      const updated =
        action === "approve"
          ? await api.review(app.id, { action })
          : await api.review(app.id, { action, target: tab, feedback });
      setApp(updated);
      setFeedback("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function patch(body: { status?: ApplicationStatus; notes?: string }) {
    if (!app) return;
    try {
      setApp(await api.updateApplication(app.id, body));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function remove() {
    if (!app || !confirm("Delete this application and its drafts?")) return;
    await api.deleteApplication(app.id);
    router.push("/");
  }

  return (
    <article className="space-y-12">
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link href="/" className="text-sm text-graphite hover:text-ink">
            Applications
          </Link>
          <h1 className="mt-1 font-serif text-4xl font-medium leading-tight">{app.title || "Untitled role"}</h1>
          <p className="text-lg text-graphite">
            {app.company}
            {app.job_url && (
              <>
                {", "}
                <a href={app.job_url} target="_blank" rel="noreferrer" className="underline hover:text-ink">
                  view posting
                </a>
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label htmlFor="status" className="text-sm text-graphite">
            Status
          </label>
          <select
            id="status"
            value={app.status}
            onChange={(e) => patch({ status: e.target.value as ApplicationStatus })}
            className="rounded-sm border border-rule bg-sheet px-2 py-1.5 text-sm"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABEL[s]}
              </option>
            ))}
          </select>
          <button onClick={remove} className="text-sm text-graphite hover:text-redpen">
            Delete
          </button>
        </div>
      </header>

      {/* Fit */}
      {match && (
        <section aria-labelledby="fit" className="space-y-3">
          <div className="flex items-baseline gap-3">
            <h2 id="fit" className="font-serif text-5xl font-semibold tabular-nums">
              {match.fit_score}
            </h2>
            <p className="text-lg">
              {VERDICT_LABEL[match.verdict]}
              <span className="text-graphite">
                {" "}
                across {match.matches.length} requirements
              </span>
            </p>
          </div>
          <RequirementStrip matches={match.matches} />
          <StripLegend />
        </section>
      )}

      {match && (
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
          <section aria-labelledby="reqs">
            <h2 id="reqs" className="mb-3 border-b border-ink/80 pb-1.5 font-semibold">
              Requirement by requirement
            </h2>
            <ul className="divide-y divide-rule">
              {match.matches.map((m, i) => (
                <li key={i} className="grid grid-cols-[1.5rem_1fr] gap-x-3 py-3">
                  <span
                    aria-label={m.level}
                    className={`mt-1 h-3.5 w-3.5 rounded-[2px] ${
                      m.level === "strong"
                        ? "bg-marker"
                        : m.level === "partial"
                          ? "hatch border border-marker"
                          : "border border-dashed border-redpen"
                    }`}
                  />
                  <div>
                    <p className="font-medium">
                      {m.requirement}
                      {m.importance === "must_have" && (
                        <span className="ml-2 text-xs font-normal text-graphite">must-have</span>
                      )}
                    </p>
                    {m.evidence ? (
                      <p className="font-serif text-[15px] italic text-graphite">{m.evidence}</p>
                    ) : (
                      <p className="text-sm text-redpen">Not on your resume</p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <aside className="space-y-8">
            {match.gaps.length > 0 && (
              <section>
                <h2 className="mb-2 font-semibold">Gaps</h2>
                <ul className="list-disc space-y-1 pl-5 text-[15px]">
                  {match.gaps.map((g, i) => (
                    <li key={i}>{g}</li>
                  ))}
                </ul>
              </section>
            )}
            {match.suggestions.length > 0 && (
              <section>
                <h2 className="mb-2 font-semibold">How to close them</h2>
                <ul className="list-disc space-y-1 pl-5 text-[15px]">
                  {match.suggestions.map((g, i) => (
                    <li key={i}>{g}</li>
                  ))}
                </ul>
              </section>
            )}
            {match.missing_keywords.length > 0 && (
              <section>
                <h2 className="font-semibold">Keywords missing from your resume</h2>
                <p className="mb-2 text-sm text-graphite">Add them only where they&apos;re true.</p>
                <ul className="flex flex-wrap gap-1.5">
                  {match.missing_keywords.map((k) => (
                    <li key={k} className="rounded-sm border border-dashed border-redpen/60 px-2 py-0.5 text-sm">
                      {k}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </aside>
        </div>
      )}

      {/* Drafts */}
      <section aria-labelledby="drafts">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b border-ink/80">
          <h2 id="drafts" className="sr-only">
            Drafts
          </h2>
          <div role="tablist" className="flex gap-6">
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => setTab(t.id)}
                className={`-mb-px border-b-[3px] pb-2 text-sm ${
                  tab === t.id ? "border-marker font-semibold" : "border-transparent text-graphite hover:text-ink"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className="pb-2">
            <CopyButton
              text={
                tab === "bullets" ? bullets.map((b) => `• ${b.rewritten}`).join("\n") : tab === "cover_letter" ? cover_letter : outreach
              }
            />
          </div>
        </div>

        <div role="tabpanel" className="border border-rule bg-sheet px-6 py-6 sm:px-10">
          {tab === "bullets" && <Bullets bullets={bullets} />}
          {tab === "cover_letter" && <Prose text={cover_letter} />}
          {tab === "outreach" && <Prose text={outreach} />}
        </div>
      </section>

      {/* Review */}
      <section aria-labelledby="review" className="max-w-2xl space-y-3">
        <h2 id="review" className="font-semibold">
          {app.awaiting_review ? "Review" : "Reviewed"}
        </h2>
        {app.awaiting_review ? (
          <>
            <label htmlFor="feedback" className="block text-sm text-graphite">
              What should change in {current.noun}?
            </label>
            <textarea
              id="feedback"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              rows={3}
              placeholder={
                tab === "cover_letter"
                  ? "Shorter, and lead with the RAG project"
                  : tab === "outreach"
                    ? "Less formal, mention I can start in January"
                    : "Emphasise the API latency work more"
              }
              className="block w-full rounded-sm border border-rule bg-sheet px-3 py-2"
            />
            <ErrorNote message={error} />
            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" disabled={!!busy || !feedback.trim()} onClick={() => review("revise")}>
                {busy === "revise" ? "Revising…" : `Revise ${current.noun}`}
              </Button>
              <Button disabled={!!busy} onClick={() => review("approve")}>
                {busy === "approve" ? "Approving…" : "Approve drafts"}
              </Button>
            </div>
          </>
        ) : (
          <p className="text-graphite">You approved these drafts. Move the application along the board as it progresses.</p>
        )}
        {app.agent.review_history && app.agent.review_history.length > 0 && (
          <p className="text-sm text-graphite">
            {app.agent.review_history.filter((r) => r.action === "revise").length} revision(s) requested so far.
          </p>
        )}
      </section>

      {/* Notes */}
      <section className="max-w-2xl">
        <label htmlFor="notes" className="mb-1 block font-semibold">
          Notes
        </label>
        <textarea
          id="notes"
          defaultValue={app.notes}
          onBlur={(e) => e.target.value !== app.notes && patch({ notes: e.target.value })}
          rows={3}
          placeholder="Referral, recruiter name, interview dates…"
          className="block w-full rounded-sm border border-rule bg-sheet px-3 py-2"
        />
      </section>
    </article>
  );
}

function Bullets({ bullets }: { bullets: TailoredBullet[] }) {
  if (!bullets.length) return <p className="text-graphite">No bullets were rewritten for this role.</p>;
  return (
    <ol className="max-w-[68ch] space-y-6">
      {bullets.map((b, i) => (
        <li key={i}>
          <p className="font-serif text-[17px] leading-relaxed">
            {diffRuns(b.original, b.rewritten).map((t, j) => (
              <span key={j}>
                {j > 0 && " "}
                {t.added ? <mark className="highlight text-inherit">{t.text}</mark> : t.text}
              </span>
            ))}
          </p>
          <p className="mt-1 text-sm text-graphite">
            <span className="line-through decoration-redpen/60">{b.original}</span>
          </p>
          {b.reason && <p className="mt-0.5 text-xs text-graphite">Targets: {b.reason}</p>}
        </li>
      ))}
    </ol>
  );
}

function Prose({ text }: { text: string }) {
  if (!text) return <p className="text-graphite">Nothing drafted yet.</p>;
  return (
    <div className="max-w-[66ch] space-y-4 font-serif text-[17px] leading-[1.7]">
      {text.split(/\n{2,}/).map((p, i) => (
        <p key={i} className="whitespace-pre-line">
          {p}
        </p>
      ))}
    </div>
  );
}
