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
      "bg-surface-container-low text-on-surface-variant border-surface-container-high",
    icon: "pause_circle",
  },
  draft: {
    className:
      "bg-provenance-ai-bg text-provenance-ai-text border-provenance-ai-border",
    icon: "edit_note",
  },
  archived: {
    className:
      "bg-surface-container-low text-on-surface-variant border-surface-container-high",
    icon: "archive",
  },
};

export function GoalCard({ goal }: { goal: Goal }) {
  const tone = STATUS_TONE[goal.status];
  const pct = progressPct(goal.current, goal.target);

  return (
    <Card className="flex flex-col gap-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <RingProgress value={pct} size={64} stroke={6} tone={goal.accent} />
          <div className="flex flex-col gap-2">
            <h3 className="font-headline-sm text-headline-sm text-on-surface">
              {goal.title}
            </h3>
            <div className="flex flex-wrap items-center gap-2">
              <ProvenanceBadge
                provenance={goal.provenance}
                label={goal.meta[0]?.value}
              />
              <span
                className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 font-body-sm text-[11px] font-medium ${tone.className}`}
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
          className="text-on-surface-variant transition-colors hover:text-on-surface"
        >
          <Icon name="more_vert" />
        </button>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between gap-3">
          <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
            {formatCurrency(goal.current)}
          </span>
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            of {formatCurrency(goal.target)}
          </span>
        </div>
        <ProgressBar
          value={pct}
          tone={goal.accent}
          size="sm"
          label={`${goal.title} progress`}
        />
      </div>

      <div className="grid grid-cols-3 gap-4 border-t border-surface-container-high pt-5">
        <div className="flex flex-col gap-1">
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Monthly
          </span>
          <span className="font-title-md text-title-md tabular-nums text-on-surface">
            {formatCurrency(goal.monthlyContribution)}
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Target date
          </span>
          <span className="font-title-md text-title-md tabular-nums text-on-surface">
            {formatShortMonthYear(goal.targetDate)}
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Status
          </span>
          <span className="font-title-md text-title-md text-on-surface">
            {goal.status === "behind" ? "Behind" : "On schedule"}
          </span>
        </div>
      </div>

      {goal.meta.length > 1 && (
        <div className="flex flex-wrap gap-x-5 gap-y-1">
          {goal.meta.slice(1).map((m) => (
            <span
              key={m.label}
              className="font-body-sm text-body-sm text-on-surface-variant"
            >
              <span className="text-on-surface-variant/70">{m.label}:</span>{" "}
              <span className="text-on-surface">{m.value}</span>
            </span>
          ))}
        </div>
      )}

      {goal.status === "behind" && (
        <div className="flex flex-col gap-3 rounded-xl bg-provenance-warning-bg p-4 sm:flex-row sm:items-center sm:justify-between">
          <span className="font-body-sm text-body-sm text-provenance-warning-text">
            Rebalance recommendation: increase monthly deposit to $950/mo or
            extend the target horizon by 90 days.
          </span>
          <button
            type="button"
            className="shrink-0 rounded-full bg-white px-4 py-2 font-body-sm text-body-sm font-medium text-on-surface"
          >
            Adjust pace
          </button>
        </div>
      )}
    </Card>
  );
}
