import { Card, CardHeader } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { LineChart } from "@/components/ui/LineChart";
import { GOAL_TARGET_SUMMARY, PORTFOLIO_IMPACT } from "@/lib/data/assistant";
import { formatCurrency, formatShortMonthYear, progressPct } from "@/lib/format";

export function GoalTargetPanel() {
  const pct = progressPct(
    GOAL_TARGET_SUMMARY.funded,
    GOAL_TARGET_SUMMARY.target,
  );

  return (
    <Card className="flex flex-col gap-5">
      <CardHeader
        icon="flag"
        title={GOAL_TARGET_SUMMARY.title}
        action={<Icon name="info" className="text-on-surface-variant" />}
      />
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-3">
          <span className="font-title-md text-title-md text-on-surface">
            {GOAL_TARGET_SUMMARY.label}
          </span>
          <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
            {formatCurrency(GOAL_TARGET_SUMMARY.target)}
          </span>
        </div>
        <ProgressBar value={pct} size="md" label="Down payment goal progress" />
        <span className="font-body-sm text-body-sm text-on-surface-variant">
          Funded: {formatCurrency(GOAL_TARGET_SUMMARY.funded)} ({pct.toFixed(0)}%)
          · Target {formatShortMonthYear(GOAL_TARGET_SUMMARY.targetDate)}
        </span>
      </div>
      <div className="flex flex-col gap-2">
        <span className="font-body-sm text-body-sm text-on-surface-variant">
          Portfolio impact
        </span>
        <div className="rounded-xl bg-surface-container-low p-3">
          <LineChart
            height={110}
            target={GOAL_TARGET_SUMMARY.target}
            ariaLabel="Projected down payment trajectory"
            series={[
              {
                points: PORTFOLIO_IMPACT.baseline,
                color: "#86868b",
                dashed: true,
              },
              {
                points: PORTFOLIO_IMPACT.reallocated,
                color: "#0071e3",
                area: true,
              },
            ]}
          />
        </div>
        <span className="font-body-sm text-body-sm text-on-surface-variant">
          Blue = reallocated ($1,050/mo) · dashed = baseline
        </span>
      </div>
    </Card>
  );
}
