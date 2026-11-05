import type { RequirementMatch } from "@/lib/api";

/**
 * The fit score, shown as what it's made of: one segment per job requirement,
 * width = weight (must-haves count double), fill = how well the resume covers it.
 */
export function RequirementStrip({
  matches,
  size = "lg",
}: {
  matches: RequirementMatch[];
  size?: "sm" | "lg";
}) {
  if (!matches.length) return null;
  const h = size === "lg" ? "h-7" : "h-2";
  return (
    <div className={`flex w-full gap-[3px] ${h}`} role="img" aria-label={summary(matches)}>
      {matches.map((m, i) => (
        <div
          key={i}
          title={size === "lg" ? `${m.requirement} (${m.level})` : undefined}
          style={{
            flexGrow: m.importance === "must_have" ? 2 : 1,
            animationDelay: size === "lg" ? `${i * 45}ms` : undefined,
          }}
          className={`${size === "lg" ? "draw-in" : ""} basis-0 rounded-[2px] ${
            m.level === "strong"
              ? "bg-marker"
              : m.level === "partial"
                ? "hatch border border-marker"
                : "border border-dashed border-redpen/70 bg-sheet"
          }`}
        />
      ))}
    </div>
  );
}

function summary(matches: RequirementMatch[]) {
  const count = (l: string) => matches.filter((m) => m.level === l).length;
  return `${count("strong")} strong, ${count("partial")} partial, ${count("missing")} missing of ${matches.length} requirements`;
}

export function StripLegend() {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-graphite">
      <span className="flex items-center gap-1.5">
        <i className="inline-block h-3 w-4 rounded-[2px] bg-marker" /> Covered
      </span>
      <span className="flex items-center gap-1.5">
        <i className="hatch inline-block h-3 w-4 rounded-[2px] border border-marker" /> Partly covered
      </span>
      <span className="flex items-center gap-1.5">
        <i className="inline-block h-3 w-4 rounded-[2px] border border-dashed border-redpen/70" /> Missing
      </span>
      <span>Wider segments are must-haves</span>
    </div>
  );
}
