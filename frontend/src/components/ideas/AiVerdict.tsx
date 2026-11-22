import type { ReactNode } from "react";
import { Badge } from "@/components/ui/Badge";
import { SectionLabel } from "@/components/ui/Card";
import { AiRatingBadge } from "./AiRatingBadge";
import type { Agrees, AiSummary } from "@/lib/recommendations";

const LIGHT: Record<"green" | "amber" | "red", { color: string; word: string }> = {
  green: { color: "#1a7f37", word: "supports the idea" },
  amber: { color: "#b7791f", word: "mixed" },
  red: { color: "#d70015", word: "argues against" },
};

const CHECKS = [
  ["trend", "Trend"],
  ["business", "Business"],
  ["news_market", "News and market"],
  ["risk", "Risk"],
] as const;

const AGREE: Record<
  Agrees,
  { label: string; tone: "success" | "warning" | "danger" | "neutral"; icon: string }
> = {
  agree: { label: "Agrees with the rules", tone: "success", icon: "check_circle" },
  caution: { label: "Less positive than the rules", tone: "warning", icon: "error" },
  disagree: { label: "Disagrees with the rules", tone: "danger", icon: "cancel" },
  review: { label: "Needs review", tone: "neutral", icon: "help" },
};

/**
 * The short, plain-language top of the AI review: one sentence, four traffic lights,
 * how to act and what would change the call. Everything detailed lives under MoreInfo.
 * `fallback` is the long summary, shown only for reviews stored before these fields existed.
 */
export function AiVerdict({
  ai,
  label,
  fallback,
  footnote,
}: {
  ai: AiSummary;
  label: string;
  fallback: string;
  footnote: string;
}) {
  const verdict = ai.verdict;
  const checks = CHECKS.filter(([key]) => verdict?.checks?.[key]);
  const agree = AGREE[ai.agrees];
  return (
    <div className="flex flex-col gap-4 rounded-[20px] border border-surface-container-high p-4 md:p-5">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <AiRatingBadge rating={ai.rating} label={label} />
          {ai.confidence && <Badge tone="neutral">Confidence: {ai.confidence}</Badge>}
          <Badge tone={agree.tone} icon={agree.icon}>
            {agree.label}
          </Badge>
        </div>
        <p className="font-body-md text-body-md leading-relaxed text-on-surface">
          {verdict?.headline || fallback}
        </p>
      </div>

      {checks.length > 0 && (
        <div className="flex flex-col gap-2">
          <SectionLabel>Four quick checks</SectionLabel>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {checks.map(([key, title]) => {
              const check = verdict!.checks[key]!;
              const light = LIGHT[check.light];
              return (
                <div
                  key={key}
                  className="flex flex-col gap-1 rounded-[14px] bg-surface-container-low p-3"
                >
                  <span className="flex items-center gap-2 font-body-sm text-body-sm font-medium text-on-surface">
                    <span
                      aria-hidden
                      className="inline-block h-2 w-2 rounded-full"
                      style={{ backgroundColor: light.color }}
                    />
                    {title}
                    <span className="sr-only"> — {light.word}</span>
                  </span>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    {check.line}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {(verdict?.how_to_act || verdict?.change_if) && (
        <div className="grid gap-2 md:grid-cols-2">
          {verdict.how_to_act && (
            <div className="flex flex-col gap-1 rounded-[14px] bg-surface-container-low p-3">
              <SectionLabel>How to act</SectionLabel>
              <p className="font-body-sm text-body-sm text-on-surface">{verdict.how_to_act}</p>
            </div>
          )}
          {verdict.change_if && (
            <div className="flex flex-col gap-1 rounded-[14px] bg-surface-container-low p-3">
              <SectionLabel>AI changes its mind if</SectionLabel>
              <p className="font-body-sm text-body-sm text-on-surface">{verdict.change_if}</p>
            </div>
          )}
        </div>
      )}

      <p className="font-body-sm text-body-sm text-on-surface-variant">{footnote}</p>
    </div>
  );
}

/** The collapsed area for everything complicated. */
export function MoreInfo({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <SectionLabel>More info</SectionLabel>
      <div className="flex flex-col">{children}</div>
    </div>
  );
}

export function MoreRow({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <details className="group border-t border-surface-container-high py-3">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 font-body-md text-body-md text-on-surface [&::-webkit-details-marker]:hidden">
        <span className="flex flex-col">
          {title}
          {hint && (
            <span className="font-body-sm text-body-sm text-on-surface-variant">{hint}</span>
          )}
        </span>
        <span aria-hidden className="text-on-surface-variant transition-transform group-open:rotate-180">
          ▾
        </span>
      </summary>
      <div className="flex flex-col gap-4 pt-4">{children}</div>
    </details>
  );
}
