import { Card } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { RingProgress } from "@/components/ui/RingProgress";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import type { Goal } from "@/lib/types";
import { formatCurrency, formatShortMonthYear, progressPct } from "@/lib/format";

const STATUS_TONE: Record<
  Goal["status"],
  { className: string; icon: string }
> = {
  "on-track": {
    className:
      "bg-provenance-input-bg text-provenance-input-text border-provenance-input-border",
    icon: "check_circle",
  },
  behind: {
    className:
      "bg-provenance-warning-bg text-provenance-warning-text border-provenance-warning-border",
    icon: "error",
  },
  paused: {
    className:
      "bg-surface-container-low text-on-surface-variant border-outline-variant",
    icon: "pause_circle",
  },
  draft: {
    className:
      "bg-provenance-ai-bg text-provenance-ai-text border-provenance-ai-border",
    icon: "edit_note",
  },
  archived: {
    className:
      "bg-surface-container-low text-on-surface-variant border-outline-variant",
    icon: "archive",
  },
};

export function GoalCard({ goal }: { goal: Goal }) {
  const tone = STATUS_TONE[goal.status];
  const pct = progressPct(goal.current, goal.target);

  return (
    <Card className="flex flex-col gap-space-md">
      <div className="flex items-start justify-between gap-space-sm">
        <div className="flex items-start gap-space-sm">
          <RingProgress value={pct} size={56} stroke={6} tone={goal.accent} />
          <div className="flex flex-col">
            <div className="flex flex-wrap items-center gap-space-xs">
              <h3 className="font-headline-sm text-headline-sm text-on-surface">
                {goal.title}
              </h3>
              <ProvenanceBadge
                provenance={goal.provenance}
                label={goal.meta[0]?.value}
              />
              <span
                className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-label-code text-label-code uppercase tracking-wide ${tone.className}`}
              >
                <Icon name={tone.icon} className="text-[12px]" />
                {goal.statusLabel}
              </span>
            </div>
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              {goal.subtitle}
            </span>
          </div>
        </div>
        <button
          type="button"
          aria-label="Goal actions"
          className="text-on-surface-variant hover:text-on-surface"
        >
          <Icon name="more_vert" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-space-md sm:grid-cols-3">
        <div className="flex flex-col rounded-md bg-surface-container-low p-space-sm">
          <span className="font-label-code text-label-code uppercase tracking-wide text-on-surface-variant">
            Current Status
          </span>
          <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
            {formatCurrency(goal.current)}
          </span>
          <span className="font-label-code text-label-code text-on-surface-variant">
            of {formatCurrency(goal.target)} Target
          </span>
        </div>
        <div className="flex flex-col rounded-md bg-surface-container-low p-space-sm">
          <span className="font-label-code text-label-code uppercase tracking-wide text-on-surface-variant">
            Monthly Contribution
          </span>
          <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
            {formatCurrency(goal.monthlyContribution)}
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              /mo
            </span>
          </span>
          <span className="font-label-code text-label-code text-on-surface-variant">
            Automatic debit
          </span>
        </div>
        <div className="col-span-2 flex flex-col rounded-md bg-surface-container-low p-space-sm sm:col-span-1">
          <span className="font-label-code text-label-code uppercase tracking-wide text-on-surface-variant">
            Target Date
          </span>
          <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
            {formatShortMonthYear(goal.targetDate)}
          </span>
          <span className="font-label-code text-label-code text-on-surface-variant">
            {goal.status === "behind" ? "Projected slip: 2029" : "On schedule"}
          </span>
        </div>
      </div>

      <ProgressBar value={pct} tone={goal.accent} size="sm" label={`${goal.title} progress`} />

      <div className="flex flex-wrap gap-x-space-lg gap-y-1">
        {goal.meta.slice(1).map((m) => (
          <span
            key={m.label}
            className="font-label-code text-label-code text-on-surface-variant"
          >
            <span className="text-on-surface-variant/70">{m.label}:</span>{" "}
            <span className="text-on-surface">{m.value}</span>
          </span>
        ))}
      </div>

      {goal.status === "behind" && (
        <div className="flex flex-wrap items-center justify-between gap-space-sm rounded-md bg-provenance-warning-bg p-space-sm">
          <span className="font-body-sm text-body-sm text-provenance-warning-text">
            Rebalance recommendation: Increase monthly deposit to $950/mo or
            extend target horizon by 90 days.
          </span>
          <button
            type="button"
            className="rounded-md bg-surface-container-lowest px-space-md py-1 font-body-sm text-body-sm font-medium text-on-surface"
          >
            Adjust Pace
          </button>
        </div>
      )}
    </Card>
  );
}
