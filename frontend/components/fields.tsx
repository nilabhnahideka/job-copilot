"use client";

/**
 * Form inputs used by the profile page. Each one shows a label (and optional
 * hint) and reports changes with an already-converted value:
 * numbers come back as number | null (empty box = null), lists as string[].
 */
import { useId, useState } from "react";

const box = "mt-1 block w-full rounded-sm border border-rule bg-sheet px-3 py-2 font-normal";

function Label({ id, label, hint, required }: { id: string; label: string; hint?: string; required?: boolean }) {
  return (
    <>
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
        {required && (
          <span className="text-redpen" title="Needed before applying">
            {" "}
            ✱
          </span>
        )}
      </label>
      {hint && <span className="block text-xs text-graphite">{hint}</span>}
    </>
  );
}

type Common = { label: string; hint?: string; required?: boolean; className?: string };

export function TextField({
  value,
  onChange,
  type = "text",
  autoComplete,
  placeholder,
  ...c
}: Common & {
  value: string;
  onChange: (v: string) => void;
  type?: "text" | "email" | "tel" | "url";
  autoComplete?: string;
  placeholder?: string;
}) {
  const id = useId();
  return (
    <div className={c.className}>
      <Label id={id} {...c} />
      <input
        id={id}
        type={type}
        value={value}
        autoComplete={autoComplete}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={box}
      />
    </div>
  );
}

export function NumberField({
  value,
  onChange,
  min,
  max,
  step = "any",
  suffix,
  ...c
}: Common & {
  value: number | null;
  onChange: (v: number | null) => void;
  min?: number;
  max?: number;
  step?: number | "any";
  suffix?: string;
}) {
  const id = useId();
  return (
    <div className={c.className}>
      <Label id={id} {...c} />
      <div className="relative">
        <input
          id={id}
          type="number"
          inputMode="decimal"
          value={value ?? ""}
          min={min}
          max={max}
          step={step}
          onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
          className={`${box} ${suffix ? "pr-14" : ""}`}
        />
        {suffix && (
          <span className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 pt-0.5 text-sm text-graphite">
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}

export function DateField({ value, onChange, ...c }: Common & { value: string | null; onChange: (v: string | null) => void }) {
  const id = useId();
  return (
    <div className={c.className}>
      <Label id={id} {...c} />
      <input id={id} type="date" value={value ?? ""} onChange={(e) => onChange(e.target.value || null)} className={box} />
    </div>
  );
}

export function SelectField<T extends string>({
  value,
  onChange,
  options,
  ...c
}: Common & { value: T | null; onChange: (v: T | null) => void; options: { value: T; label: string }[] }) {
  const id = useId();
  return (
    <div className={c.className}>
      <Label id={id} {...c} />
      <select id={id} value={value ?? ""} onChange={(e) => onChange((e.target.value || null) as T | null)} className={box}>
        <option value="">Not set</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export const YES_NO = [
  { value: "yes" as const, label: "Yes" },
  { value: "no" as const, label: "No" },
];

export function CheckboxGroup<T extends string>({
  value,
  onChange,
  options,
  ...c
}: Common & { value: T[]; onChange: (v: T[]) => void; options: { value: T; label: string }[] }) {
  return (
    <fieldset className={c.className}>
      <legend className="block text-sm font-medium">
        {c.label}
        {c.required && <span className="text-redpen"> ✱</span>}
      </legend>
      {c.hint && <span className="block text-xs text-graphite">{c.hint}</span>}
      <div className="mt-1.5 flex flex-wrap gap-x-5 gap-y-2">
        {options.map((o) => (
          <label key={o.value} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={value.includes(o.value)}
              onChange={(e) => onChange(e.target.checked ? [...value, o.value] : value.filter((v) => v !== o.value))}
              className="h-4 w-4 accent-ink"
            />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/** A list of short texts (job titles, cities, skills). Type and press Enter or comma to add. */
export function ChipsField({
  value,
  onChange,
  placeholder,
  ...c
}: Common & { value: string[]; onChange: (v: string[]) => void; placeholder?: string }) {
  const id = useId();
  const [draft, setDraft] = useState("");

  function add(text: string) {
    const items = text
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t && !value.some((v) => v.toLowerCase() === t.toLowerCase()));
    if (items.length) onChange([...value, ...items]);
    setDraft("");
  }

  return (
    <div className={c.className}>
      <Label id={id} {...c} />
      <div className="mt-1 flex flex-wrap items-center gap-1.5 rounded-sm border border-rule bg-sheet px-2 py-1.5 focus-within:outline-2 focus-within:outline-ink">
        {value.map((v) => (
          <span key={v} className="flex items-center gap-1 rounded-sm bg-paper px-2 py-0.5 text-sm">
            {v}
            <button
              type="button"
              onClick={() => onChange(value.filter((x) => x !== v))}
              aria-label={`Remove ${v}`}
              className="px-0.5 text-graphite hover:text-redpen"
            >
              ×
            </button>
          </span>
        ))}
        <input
          id={id}
          value={draft}
          placeholder={value.length ? "" : placeholder}
          onChange={(e) => (e.target.value.endsWith(",") ? add(e.target.value) : setDraft(e.target.value))}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add(draft);
            } else if (e.key === "Backspace" && !draft && value.length) {
              onChange(value.slice(0, -1));
            }
          }}
          onBlur={() => draft && add(draft)}
          className="min-w-[8rem] flex-1 bg-transparent px-1 py-0.5 outline-none"
        />
      </div>
      <span className="mt-0.5 block text-xs text-graphite">Press Enter after each one</span>
    </div>
  );
}
