"use client";

/**
 * The profile page: everything an application form might ask, filled in once.
 *
 * - The sections are edited locally; "Save profile" sends them all in one request.
 *   A bar at the bottom appears when there are unsaved changes, and the browser
 *   warns before leaving the page with unsaved changes.
 * - Uploading a resume saves pending edits first, then the server fills any EMPTY
 *   fields from the resume and the form reloads.
 * - Saved answers are separate: each add/edit/delete is saved immediately.
 * - The checklist at the top comes from the server (`missing`), so it reflects
 *   what's actually saved.
 */
import { useCallback, useEffect, useState } from "react";
import {
  CheckboxGroup,
  ChipsField,
  DateField,
  NumberField,
  SelectField,
  TextField,
  YES_NO,
} from "@/components/fields";
import { Button, ErrorNote } from "@/components/ui";
import { api, type EducationEntry, type Profile, type ProfileData, type Resume, type SavedAnswer } from "@/lib/api";

const SECTIONS = [
  { id: "resume", label: "Resume", required: ["Resume"] },
  { id: "personal", label: "Personal details", required: ["First name", "Last name", "Email", "Phone", "City"] },
  { id: "preferences", label: "Jobs you want", required: ["Job titles you want", "Locations"] },
  { id: "answers", label: "Common questions", required: ["Notice period", "Expected salary"] },
  { id: "work", label: "Work", required: [] },
  { id: "education", label: "Education", required: [] },
  { id: "optional", label: "Optional questions", required: [] },
  { id: "saved", label: "Saved answers", required: [] },
] as const;

const EMPTY_EDUCATION: EducationEntry = {
  degree: "",
  field_of_study: "",
  institution: "",
  start_year: null,
  end_year: null,
  grade: "",
};

export function ProfileView() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState<ProfileData | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [resumes, setResumes] = useState<Resume[]>([]);

  const apply = useCallback((p: Profile, r: Resume[]) => {
    setProfile(p);
    setForm(p.data);
    setResumes(r);
    setDirty(false);
  }, []);

  /** Reload everything from the server (after a resume upload or switch). */
  const load = useCallback(async () => {
    const [p, r] = await Promise.all([api.getProfile(), api.listResumes()]);
    apply(p, r);
  }, [apply]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getProfile(), api.listResumes()])
      .then(([p, r]) => !cancelled && apply(p, r))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [apply]);

  // Warn before closing the tab with unsaved changes.
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  if (!form || !profile) return error ? <ErrorNote message={error} /> : <p className="text-graphite">Loading your profile…</p>;

  /** Update one section of the form: `update("personal", { phone: "..." })`. */
  function update<K extends keyof ProfileData>(section: K, patch: Partial<ProfileData[K]>) {
    setForm((f) => (f ? { ...f, [section]: { ...f[section], ...patch } } : f));
    setDirty(true);
    setNotice(null);
  }

  async function save(): Promise<boolean> {
    if (!form) return false;
    setSaving(true);
    setError(null);
    try {
      const p = await api.saveProfile(form);
      setProfile(p);
      setForm(p.data);
      setDirty(false);
      setNotice("Profile saved.");
      return true;
    } catch (e) {
      setError(`Couldn't save: ${(e as Error).message}`);
      return false;
    } finally {
      setSaving(false);
    }
  }

  const { personal: P, preferences: J, answers: A, work: W, education: E, demographics: D } = form;
  const missing = new Set(profile.missing);

  return (
    <div className="grid gap-10 pb-24 lg:grid-cols-[13rem_minmax(0,1fr)]">
      {/* Section list */}
      <nav aria-label="Profile sections" className="hidden lg:block">
        <ul className="sticky top-6 space-y-1.5 text-sm">
          {SECTIONS.map((s) => {
            const todo = s.required.filter((r) => missing.has(r)).length;
            return (
              <li key={s.id}>
                <a href={`#${s.id}`} className="flex items-center justify-between text-graphite hover:text-ink">
                  {s.label}
                  {todo > 0 && (
                    <span className="text-xs text-redpen" aria-label={`${todo} still needed`}>
                      {todo} to do
                    </span>
                  )}
                </a>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="min-w-0 max-w-3xl space-y-12">
        <header className="space-y-3">
          <h1 className="font-serif text-3xl font-medium">Your profile</h1>
          <p className="text-graphite">
            Fill this in once. Every application starts from it, and the app only asks you for what isn&apos;t
            here.
          </p>
          {profile.missing.length > 0 ? (
            <div className="border-l-2 border-redpen bg-sheet px-4 py-3 text-sm">
              <p className="font-medium">Before the app can apply for you, add:</p>
              <p className="mt-1 text-graphite">{profile.missing.join(", ")}</p>
            </div>
          ) : (
            <p className="border-l-2 border-marker bg-sheet px-4 py-3 text-sm">
              Your profile has everything needed for applying.
            </p>
          )}
          <p className="text-xs text-graphite">
            Fields marked <span className="text-redpen">✱</span> are needed before applying. Salaries are in lakhs
            per annum (LPA): 6.5 means ₹6,50,000 a year.
          </p>
        </header>

        <ResumeSection
          profile={profile}
          resumes={resumes}
          beforeUpload={async () => (dirty ? save() : true)}
          onChanged={async (message) => {
            await load();
            setNotice(message);
          }}
          onError={setError}
        />

        <Section id="personal" title="Personal details">
          <Grid>
            <TextField label="First name" required value={P.first_name} onChange={(v) => update("personal", { first_name: v })} autoComplete="given-name" />
            <TextField label="Last name" required value={P.last_name} onChange={(v) => update("personal", { last_name: v })} autoComplete="family-name" />
            <TextField label="Preferred name" hint="If you go by a different first name" value={P.preferred_name} onChange={(v) => update("personal", { preferred_name: v })} />
            <TextField label="Email" required type="email" value={P.email} onChange={(v) => update("personal", { email: v })} autoComplete="email" hint="Where recruiters should contact you" />
            <TextField label="Phone" required type="tel" value={P.phone} onChange={(v) => update("personal", { phone: v })} autoComplete="tel" placeholder="+91 98765 43210" hint="With country code" />
            <TextField label="City" required value={P.city} onChange={(v) => update("personal", { city: v })} autoComplete="address-level2" />
            <TextField label="State" value={P.state} onChange={(v) => update("personal", { state: v })} autoComplete="address-level1" />
            <TextField label="Country" value={P.country} onChange={(v) => update("personal", { country: v })} autoComplete="country-name" />
            <TextField label="LinkedIn" type="url" value={P.linkedin_url} onChange={(v) => update("personal", { linkedin_url: v })} placeholder="https://linkedin.com/in/…" />
            <TextField label="GitHub" type="url" value={P.github_url} onChange={(v) => update("personal", { github_url: v })} placeholder="https://github.com/…" />
            <TextField label="Portfolio or website" type="url" value={P.portfolio_url} onChange={(v) => update("personal", { portfolio_url: v })} className="sm:col-span-2" />
          </Grid>
        </Section>

        <Section id="preferences" title="Jobs you want" intro="Job search uses these to find and rank jobs for you.">
          <Grid>
            <ChipsField label="Job titles" required value={J.titles} onChange={(v) => update("preferences", { titles: v })} placeholder="e.g. GenAI Engineer" className="sm:col-span-2" />
            <ChipsField label="Locations" required value={J.locations} onChange={(v) => update("preferences", { locations: v })} placeholder="e.g. Bengaluru" hint="Cities you'd work in" className="sm:col-span-2" />
            <CheckboxGroup
              label="Work mode"
              value={J.work_modes}
              onChange={(v) => update("preferences", { work_modes: v })}
              options={[
                { value: "remote", label: "Remote" },
                { value: "hybrid", label: "Hybrid" },
                { value: "onsite", label: "In office" },
              ]}
            />
            <CheckboxGroup
              label="Job type"
              value={J.job_types}
              onChange={(v) => update("preferences", { job_types: v })}
              options={[
                { value: "full_time", label: "Full-time" },
                { value: "internship", label: "Internship" },
                { value: "contract", label: "Contract" },
                { value: "part_time", label: "Part-time" },
              ]}
            />
            <SelectField
              label="Experience level"
              value={J.experience_level}
              onChange={(v) => update("preferences", { experience_level: v })}
              options={[
                { value: "internship", label: "Internship" },
                { value: "entry", label: "Entry level (0–2 years)" },
                { value: "mid", label: "Mid level (2–5 years)" },
                { value: "senior", label: "Senior (5+ years)" },
                { value: "lead", label: "Lead / manager" },
              ]}
            />
            <div className="grid grid-cols-2 gap-3">
              <NumberField label="Salary from" suffix="LPA" min={0} value={J.salary_min_lpa} onChange={(v) => update("preferences", { salary_min_lpa: v })} />
              <NumberField label="Salary to" suffix="LPA" min={0} value={J.salary_max_lpa} onChange={(v) => update("preferences", { salary_max_lpa: v })} />
            </div>
            <ChipsField label="Companies to skip" hint="Never show jobs from these" value={J.excluded_companies} onChange={(v) => update("preferences", { excluded_companies: v })} className="sm:col-span-2" />
          </Grid>
        </Section>

        <Section id="answers" title="Common questions" intro="Asked on most application forms.">
          <Grid>
            <NumberField label="Notice period" required suffix="days" min={0} max={365} step={1} hint="0 if you can join immediately" value={A.notice_period_days} onChange={(v) => update("answers", { notice_period_days: v })} />
            <SelectField label="Currently serving notice?" options={YES_NO} value={A.currently_serving_notice} onChange={(v) => update("answers", { currently_serving_notice: v })} />
            {A.currently_serving_notice === "yes" && (
              <DateField label="Last working day" value={A.last_working_day} onChange={(v) => update("answers", { last_working_day: v })} />
            )}
            <NumberField label="Current salary (CTC)" suffix="LPA" min={0} hint="Leave empty if you're a fresher" value={A.current_ctc_lpa} onChange={(v) => update("answers", { current_ctc_lpa: v })} />
            <NumberField label="Expected salary (CTC)" required suffix="LPA" min={0} value={A.expected_ctc_lpa} onChange={(v) => update("answers", { expected_ctc_lpa: v })} />
            <SelectField label="Willing to relocate?" options={YES_NO} value={A.willing_to_relocate} onChange={(v) => update("answers", { willing_to_relocate: v })} />
            <SelectField label="Authorised to work in India?" options={YES_NO} value={A.authorized_to_work_in_india} onChange={(v) => update("answers", { authorized_to_work_in_india: v })} />
            <SelectField label="Need visa sponsorship?" hint="For jobs outside India" options={YES_NO} value={A.requires_visa_sponsorship} onChange={(v) => update("answers", { requires_visa_sponsorship: v })} />
            <ChipsField label="Languages you speak" value={A.languages} onChange={(v) => update("answers", { languages: v })} placeholder="e.g. English" className="sm:col-span-2" />
          </Grid>
        </Section>

        <Section id="work" title="Work">
          <Grid>
            <NumberField label="Total experience" suffix="years" min={0} max={60} hint="0 if you're a fresher" value={W.total_experience_years} onChange={(v) => update("work", { total_experience_years: v })} />
            <div className="hidden sm:block" />
            <TextField label="Current company" value={W.current_company} onChange={(v) => update("work", { current_company: v })} />
            <TextField label="Current job title" value={W.current_title} onChange={(v) => update("work", { current_title: v })} />
            <ChipsField label="Key skills" value={W.skills} onChange={(v) => update("work", { skills: v })} placeholder="e.g. Python" className="sm:col-span-2" />
          </Grid>
        </Section>

        <Section id="education" title="Education">
          <div className="space-y-6">
            {E.entries.map((entry, i) => {
              const setEntry = (patch: Partial<EducationEntry>) =>
                update("education", { entries: E.entries.map((x, j) => (j === i ? { ...x, ...patch } : x)) });
              return (
                <fieldset key={i} className="border-l-2 border-rule pl-4">
                  <legend className="sr-only">Degree {i + 1}</legend>
                  <Grid>
                    <TextField label="Degree" placeholder="e.g. B.Tech" value={entry.degree} onChange={(v) => setEntry({ degree: v })} />
                    <TextField label="Field of study" placeholder="e.g. Computer Science" value={entry.field_of_study} onChange={(v) => setEntry({ field_of_study: v })} />
                    <TextField label="College or university" value={entry.institution} onChange={(v) => setEntry({ institution: v })} className="sm:col-span-2" />
                    <div className="grid grid-cols-2 gap-3">
                      <NumberField label="Start year" min={1950} max={2100} step={1} value={entry.start_year} onChange={(v) => setEntry({ start_year: v })} />
                      <NumberField label="Graduation year" min={1950} max={2100} step={1} value={entry.end_year} onChange={(v) => setEntry({ end_year: v })} />
                    </div>
                    <TextField label="CGPA or percentage" placeholder="e.g. 8.4 CGPA" value={entry.grade} onChange={(v) => setEntry({ grade: v })} />
                  </Grid>
                  <button
                    type="button"
                    onClick={() => update("education", { entries: E.entries.filter((_, j) => j !== i) })}
                    className="mt-2 text-sm text-graphite hover:text-redpen"
                  >
                    Remove this degree
                  </button>
                </fieldset>
              );
            })}
            <Button variant="secondary" type="button" onClick={() => update("education", { entries: [...E.entries, EMPTY_EDUCATION] })}>
              Add a degree
            </Button>
            <Grid>
              <NumberField label="Class 10 marks" suffix="%" min={0} max={100} hint="Some Indian employers ask" value={E.class_10_percentage} onChange={(v) => update("education", { class_10_percentage: v })} />
              <NumberField label="Class 12 marks" suffix="%" min={0} max={100} value={E.class_12_percentage} onChange={(v) => update("education", { class_12_percentage: v })} />
            </Grid>
          </div>
        </Section>

        <Section
          id="optional"
          title="Optional questions"
          intro="Some forms ask these. Leave them empty or choose “Prefer not to say”; they're only used where a form requires an answer."
        >
          <Grid>
            <DateField label="Date of birth" value={D.date_of_birth} onChange={(v) => update("demographics", { date_of_birth: v })} />
            <SelectField
              label="Gender"
              value={D.gender}
              onChange={(v) => update("demographics", { gender: v })}
              options={[
                { value: "female", label: "Female" },
                { value: "male", label: "Male" },
                { value: "non_binary", label: "Non-binary" },
                { value: "prefer_not_to_say", label: "Prefer not to say" },
              ]}
            />
            <SelectField label="Do you have a disability?" value={D.disability} onChange={(v) => update("demographics", { disability: v })} options={[...YES_NO, { value: "prefer_not_to_say", label: "Prefer not to say" }]} />
            <SelectField label="Are you a veteran?" hint="Mostly asked by US companies" value={D.veteran} onChange={(v) => update("demographics", { veteran: v })} options={[...YES_NO, { value: "prefer_not_to_say", label: "Prefer not to say" }]} />
          </Grid>
        </Section>

        <SavedAnswers onError={setError} />
      </div>

      {/* Save bar */}
      <div aria-live="polite" className="fixed inset-x-0 bottom-0 z-10">
        {(dirty || notice || error) && (
          <div className="border-t border-rule bg-sheet">
            <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-5 py-3">
              {error ? (
                <p className="text-sm text-redpen">{error}</p>
              ) : dirty ? (
                <p className="text-sm">You have unsaved changes.</p>
              ) : (
                <p className="text-sm text-graphite">{notice}</p>
              )}
              <div className="ml-auto flex gap-2">
                {dirty && (
                  <Button variant="secondary" type="button" disabled={saving} onClick={() => profile && (setForm(profile.data), setDirty(false), setError(null))}>
                    Discard changes
                  </Button>
                )}
                {dirty && (
                  <Button type="button" disabled={saving} onClick={save}>
                    {saving ? "Saving…" : "Save profile"}
                  </Button>
                )}
                {!dirty && (
                  <button type="button" onClick={() => (setNotice(null), setError(null))} className="text-sm text-graphite hover:text-ink">
                    Dismiss
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Section({ id, title, intro, children }: { id: string; title: string; intro?: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="scroll-mt-6">
      <h2 id={`${id}-title`} className="border-b border-ink/80 pb-1.5 font-semibold">
        {title}
      </h2>
      {intro && <p className="mt-2 text-sm text-graphite">{intro}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return <div className="grid gap-x-5 gap-y-4 sm:grid-cols-2">{children}</div>;
}

// ---------------------------------------------------------------------------
function ResumeSection({
  profile,
  resumes,
  beforeUpload,
  onChanged,
  onError,
}: {
  profile: Profile;
  resumes: Resume[];
  beforeUpload: () => Promise<boolean>;
  onChanged: (message: string) => Promise<void>;
  onError: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const active = profile.active_resume;
  const others = resumes.filter((r) => r.id !== active?.id);

  async function upload(file: File) {
    setBusy(true);
    try {
      if (!(await beforeUpload())) return; // saving pending edits failed; the error is shown
      const r = await api.uploadResume({ file, label: file.name });
      await onChanged(
        r.prefilled.length
          ? `Resume uploaded. Filled from it: ${r.prefilled.join(", ")}. Check them below.`
          : "Resume uploaded.",
      );
    } catch (e) {
      onError(`Couldn't upload: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Section id="resume" title="Resume">
      {active ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border border-rule bg-sheet px-4 py-3">
          <div className="min-w-0">
            <p className="truncate font-medium">{active.file_name || active.label}</p>
            <p className="text-sm text-graphite">
              Used for new applications. Uploaded {new Date(active.created_at).toLocaleDateString()}
            </p>
          </div>
          {active.file_name && (
            <button
              type="button"
              onClick={() => api.downloadResume(active.id, active.file_name).catch((e) => onError(e.message))}
              className="ml-auto text-sm underline"
            >
              Download
            </button>
          )}
        </div>
      ) : (
        <p className="text-graphite">No resume yet. Upload one to get started; empty fields below are filled from it.</p>
      )}

      <label className="mt-4 block text-sm font-medium">
        {active ? "Replace with a new version" : "Upload your resume"}
        <span className="block text-xs font-normal text-graphite">
          PDF, up to 5 MB. The file itself is kept, so it can be attached to applications.
        </span>
        <input
          type="file"
          accept=".pdf,application/pdf"
          disabled={busy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = ""; // allow choosing the same file again
            if (f) upload(f);
          }}
          className="mt-2 block text-sm font-normal file:mr-3 file:rounded-sm file:border file:border-ink/30 file:bg-sheet file:px-3 file:py-1.5 file:text-ink"
        />
      </label>
      {busy && <p className="mt-2 text-sm text-graphite">Reading your resume…</p>}

      {others.length > 0 && (
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer text-graphite">Earlier versions ({others.length})</summary>
          <ul className="mt-2 divide-y divide-rule border-y border-rule">
            {others.map((r) => (
              <li key={r.id} className="flex items-center gap-3 py-2">
                <span className="min-w-0 truncate">{r.file_name || r.label}</span>
                <span className="text-graphite">{new Date(r.created_at).toLocaleDateString()}</span>
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      await api.setActiveResume(r.id);
                      await onChanged(`Now using ${r.file_name || r.label}.`);
                    } catch (e) {
                      onError((e as Error).message);
                    }
                  }}
                  className="ml-auto underline"
                >
                  Use this one
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}
    </Section>
  );
}

// ---------------------------------------------------------------------------
function SavedAnswers({ onError }: { onError: (message: string) => void }) {
  const [answers, setAnswers] = useState<SavedAnswer[] | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [editing, setEditing] = useState<number | null>(null);
  const [editText, setEditText] = useState("");

  useEffect(() => {
    api.listAnswers().then(setAnswers).catch((e) => onError(e.message));
  }, [onError]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    try {
      const saved = await api.addAnswer(question, answer);
      // The server merges answers to the same question, so replace rather than duplicate.
      setAnswers((a) => [saved, ...(a ?? []).filter((x) => x.id !== saved.id)]);
      setQuestion("");
      setAnswer("");
    } catch (err) {
      onError((err as Error).message);
    }
  }

  return (
    <Section
      id="saved"
      title="Saved answers"
      intro="Answers to other questions forms ask. When the app meets a question it can't answer while applying, it asks you once and saves it here. Changes here save straight away."
    >
      {answers && answers.length === 0 && <p className="text-sm text-graphite">None yet.</p>}
      <ul className="divide-y divide-rule">
        {answers?.map((a) => (
          <li key={a.id} className="py-3">
            <p className="font-medium">{a.question}</p>
            {editing === a.id ? (
              <div className="mt-1 space-y-2">
                <textarea value={editText} onChange={(e) => setEditText(e.target.value)} rows={3} className="block w-full rounded-sm border border-rule bg-sheet px-3 py-2" aria-label={`Answer to: ${a.question}`} />
                <div className="flex gap-2">
                  <Button
                    type="button"
                    disabled={!editText.trim()}
                    onClick={async () => {
                      try {
                        const saved = await api.editAnswer(a.id, { answer: editText });
                        setAnswers((all) => all?.map((x) => (x.id === a.id ? saved : x)) ?? null);
                        setEditing(null);
                      } catch (e) {
                        onError((e as Error).message);
                      }
                    }}
                  >
                    Save answer
                  </Button>
                  <Button variant="secondary" type="button" onClick={() => setEditing(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <p className="mt-0.5 whitespace-pre-line text-[15px] text-graphite">{a.answer}</p>
                <div className="mt-1 flex gap-4 text-sm">
                  <button type="button" onClick={() => (setEditing(a.id), setEditText(a.answer))} className="text-graphite hover:text-ink">
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        await api.deleteAnswer(a.id);
                        setAnswers((all) => all?.filter((x) => x.id !== a.id) ?? null);
                      } catch (e) {
                        onError((e as Error).message);
                      }
                    }}
                    className="text-graphite hover:text-redpen"
                  >
                    Delete
                  </button>
                </div>
              </>
            )}
          </li>
        ))}
      </ul>

      <form onSubmit={add} className="mt-4 space-y-3 border-t border-rule pt-4">
        <p className="text-sm font-medium">Add an answer</p>
        <TextField label="Question" value={question} onChange={setQuestion} placeholder="e.g. Why do you want to work in AI?" />
        <div>
          <label htmlFor="new-answer" className="block text-sm font-medium">
            Your answer
          </label>
          <textarea id="new-answer" value={answer} onChange={(e) => setAnswer(e.target.value)} rows={3} className="mt-1 block w-full rounded-sm border border-rule bg-sheet px-3 py-2" />
        </div>
        <Button type="submit" variant="secondary" disabled={question.trim().length < 2 || !answer.trim()}>
          Add answer
        </Button>
      </form>
    </Section>
  );
}
