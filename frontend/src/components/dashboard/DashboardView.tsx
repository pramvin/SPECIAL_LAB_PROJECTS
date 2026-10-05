import { Card, CardHeader, SectionLabel } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { RingProgress } from "@/components/ui/RingProgress";
import { NoticeBanner } from "@/components/ui/NoticeBanner";
import { LineChart } from "@/components/ui/LineChart";
import { MetricCard } from "./MetricCard";
import { PROFILE, REGULATORY_NOTICE, SOURCE_NOTE } from "@/lib/data/profile";
import {
  AGENT_INSIGHT,
  HEADLINE,
  LIQUIDITY_TRAJECTORY,
  METRICS,
  PERSONALIZED_STRATEGY,
} from "@/lib/data/dashboard";
import { GOALS } from "@/lib/data/goals";
import { formatCurrency, progressPct } from "@/lib/format";

function CompletenessBanner() {
  return (
    <div className="flex flex-col gap-space-sm rounded-lg bg-surface-container-low p-space-lg md:flex-row md:items-center md:justify-between">
      <div className="flex items-center gap-space-md">
        <RingProgress value={PROFILE.completenessPct} size={44} stroke={4} />
        <div className="flex flex-col">
          <div className="flex flex-wrap items-center gap-space-xs">
            <span className="font-title-md text-title-md text-on-surface">
              Input Completeness: {PROFILE.completenessPct}%
            </span>
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-error" />
            <span className="font-body-sm text-body-sm font-medium text-error">
              {PROFILE.incompleteReviewCount} items need your review
            </span>
          </div>
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Complete your baseline profile to lock conservative portfolio
            simulations.
          </span>
        </div>
      </div>
      <Button icon="fact_check" className="self-start md:self-auto">
        Complete Setup
      </Button>
    </div>
  );
}

function SourceBar() {
  return (
    <div className="flex flex-wrap items-center gap-space-xs rounded-lg bg-surface-container-lowest p-1.5 shadow-sm">
      <span className="flex items-center gap-space-xs rounded bg-surface-container-low px-space-sm py-1">
        <Icon name="database" className="text-body-sm text-secondary" />
        <span className="font-label-code text-label-code text-on-surface-variant">
          {SOURCE_NOTE}
        </span>
      </span>
      <span className="h-4 w-px bg-surface-container" />
      <button
        type="button"
        className="inline-flex items-center gap-space-xs rounded px-space-sm py-1 font-body-sm text-body-sm text-on-surface transition-colors hover:bg-surface-container-high"
      >
        <Icon name="visibility_off" className="text-body-sm text-secondary" />
        <span className="font-label-code text-label-code">Mask Figures</span>
      </button>
      <span className="flex items-center gap-1.5 px-space-xs font-label-code text-label-code text-on-surface-variant">
        <span className="h-2 w-2 rounded-full bg-primary-container" />
        {HEADLINE.auditedLabel}
      </span>
    </div>
  );
}

function AgentObservation() {
  return (
    <Card className="flex flex-col gap-space-md">
      <CardHeader
        icon="psychology"
        title="Personalized Agent Observation"
        subtitle="Draft guidance — not accredited financial advice"
        badge={
          <span className="flex flex-wrap gap-1">
            <ProvenanceBadge provenance="ai" label="AI Draft" />
            <ProvenanceBadge provenance="ai" label="AI · Assumptions" />
          </span>
        }
      />
      <p className="border-l-2 border-primary-fixed-dim pl-space-md font-body-md text-body-md text-on-surface">
        Based on your monthly surplus of{" "}
        <strong className="tabular-nums">$1,250</strong> and conservative risk
        preference, allocating an extra{" "}
        <strong className="tabular-nums">$300/mo</strong> to your Emergency
        Fund accelerates completion by 5 months, reaching the 6-month
        resilience buffer by May 2027.
      </p>
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between font-label-code text-label-code uppercase tracking-wide text-on-surface-variant">
          <span>Timeline to Resilience Goal</span>
          <span className="text-primary">5 Months Accelerated</span>
        </div>
        <ProgressBar value={62} tone="primary" label="Timeline to resilience goal" />
        <div className="flex items-center justify-between font-label-code text-label-code text-on-surface-variant">
          <span className="text-primary">On track</span>
          <span>27 vs Oct &apos;27</span>
        </div>
      </div>
      <details className="group rounded-md border border-surface-container-high">
        <summary className="flex cursor-pointer list-none items-center justify-between px-space-md py-space-sm font-title-md text-title-md text-on-surface">
          <span className="inline-flex items-center gap-2">
            <Icon name="schema" className="text-[18px]" />
            Inspect Assumptions &amp; Inputs
          </span>
          <Icon
            name="expand_more"
            className="transition-transform group-open:rotate-180"
          />
        </summary>
        <div className="flex flex-wrap gap-space-sm border-t border-surface-container-high p-space-md">
          {AGENT_INSIGHT.assumptions.map((a) => (
            <ProvenanceBadge key={a} provenance="example" label={a} />
          ))}
        </div>
      </details>
      <div className="flex flex-wrap items-center gap-space-sm">
        <Button icon="forum">Discuss with Assistant</Button>
        <Button variant="secondary" icon="tune">
          Adjust Assumptions
        </Button>
      </div>
      <span className="inline-flex items-center gap-1.5 font-label-code text-label-code text-on-surface-variant">
        <Icon name="lock" className="text-[14px]" />
        Private Session
      </span>
    </Card>
  );
}

function CompletenessSources() {
  const rows = [
    {
      icon: "account_balance",
      title: "Connected Assets",
      meta: "3 Accounts",
      note: "High Yield Savings, Traditional Checking, Brokerage · Manual entry mode enabled",
      action: null,
      tone: "neutral" as const,
    },
    {
      icon: "warning",
      title: "Retirement Contribution Rate",
      meta: "Needs Review",
      note: "Employer 401(k) match parameters unverified.",
      action: "Verify Contribution Formula",
      tone: "warning" as const,
    },
    {
      icon: "account_tree",
      title: "State Tax Localization",
      meta: "Pending Entry",
      note: "Defaulted to standard federal progressive bracket.",
      action: null,
      tone: "info" as const,
    },
  ];

  return (
    <Card className="flex flex-col gap-space-md">
      <CardHeader
        icon="fact_check"
        title="Completeness & Sources"
        subtitle="Real-time status of connected asset integrations and onboarding baseline checklist."
        badge={<ProvenanceBadge provenance="example" label="FR-FE-004" />}
      />
      <div className="flex flex-col divide-y divide-surface-container-high">
        {rows.map((row) => (
          <div
            key={row.title}
            className="flex items-start gap-space-sm py-space-md first:pt-0"
          >
            <Icon
              name={row.icon}
              className={`mt-0.5 text-[20px] ${
                row.tone === "warning" ? "text-error" : "text-secondary"
              }`}
            />
            <div className="flex min-w-0 flex-col gap-1">
              <div className="flex flex-wrap items-center gap-space-xs">
                <span className="font-title-md text-title-md text-on-surface">
                  {row.title}
                </span>
                <span className="font-label-code text-label-code text-on-surface-variant">
                  {row.meta}
                </span>
              </div>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                {row.note}
              </span>
              {row.action && (
                <a
                  href="#"
                  className="mt-1 inline-flex items-center gap-1 font-body-sm text-body-sm font-medium text-error hover:underline"
                >
                  {row.action}
                  <Icon name="arrow_forward" className="text-[14px]" />
                </a>
              )}
            </div>
          </div>
        ))}
        <div className="flex items-center justify-between py-space-md">
          <span className="inline-flex items-center gap-space-xs font-body-sm text-body-sm text-on-surface-variant">
            <Icon name="verified_user" className="text-[18px] text-secondary" />
            Zero read credentials retained
          </span>
          <a
            href="#"
            className="font-body-sm text-body-sm font-medium text-secondary hover:underline"
          >
            Manage Feeds
          </a>
        </div>
      </div>
    </Card>
  );
}

function ActiveGoals() {
  return (
    <Card className="flex flex-col gap-space-md">
      <CardHeader
        icon="flag"
        title="Active Financial Goals"
        subtitle="Long-term milestone projections"
        action={
          <Button variant="secondary" size="sm" icon="add">
            Create New Goal
          </Button>
        }
      />
      <div className="flex flex-col divide-y divide-surface-container-high">
        {GOALS.map((goal) => (
          <div
            key={goal.id}
            className="flex flex-col gap-space-md py-space-md first:pt-0"
          >
            <div className="flex items-start justify-between gap-space-sm">
              <div className="flex flex-col">
                <span className="font-title-md text-title-md text-on-surface">
                  {goal.title}
                </span>
                <span className="font-body-sm text-body-sm text-on-surface-variant">
                  Target Date: {goal.targetDate.slice(0, 7).replace("-", " ")} ·{" "}
                  {goal.monthlyContribution ? `${formatCurrency(goal.monthlyContribution)}/mo allocation` : ""}
                </span>
              </div>
              <div className="text-right">
                <div className="font-metric-md text-metric-md tabular-nums text-on-surface">
                  {formatCurrency(goal.current)} /{" "}
                  <span className="text-on-surface-variant">
                    {formatCurrency(goal.target)}
                  </span>
                </div>
                <div className="font-label-code text-label-code text-primary">
                  {Math.round(progressPct(goal.current, goal.target))}% Funded
                </div>
              </div>
            </div>
            <ProgressBar
              value={progressPct(goal.current, goal.target)}
              tone={goal.accent}
              size="sm"
              label={`${goal.title} progress`}
            />
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between border-t border-surface-container-high pt-space-sm">
        <span className="font-body-sm text-body-sm text-on-surface-variant">
          2 active savings directives modeled
        </span>
        <a
          href="/goals"
          className="inline-flex items-center gap-1 font-body-sm text-body-sm font-medium text-primary hover:underline"
        >
          View All Goals
          <Icon name="arrow_forward" className="text-[16px]" />
        </a>
      </div>
    </Card>
  );
}

function StrategyCard() {
  return (
    <Card className="flex flex-col gap-space-md overflow-hidden p-0">
      <div className="relative flex h-40 items-end bg-gradient-to-br from-primary-container via-surface-tint to-secondary p-space-md">
        <div className="flex flex-col">
          <span className="font-label-code text-label-code uppercase tracking-wider text-primary-fixed-dim">
            {PERSONALIZED_STRATEGY.tag}
          </span>
          <span className="font-headline-sm text-headline-sm font-bold text-white">
            Preservation &amp; Predictability
          </span>
          <span className="font-label-code text-label-code text-white/80">
            {PERSONALIZED_STRATEGY.title}
          </span>
        </div>
        <span className="absolute right-3 top-3 rounded-full bg-black/20 px-2 py-0.5 font-label-code text-label-code text-white">
          Illustrative image
        </span>
      </div>
      <div className="flex flex-col gap-space-md px-space-lg pb-space-lg">
        <p className="font-body-md text-body-md text-on-surface">
          Your asset distribution is currently weighted toward high liquidity
          reserves. Once the primary emergency buffer hits 6.0 months, automated
          advice workflows will activate tax-advantaged reallocations.
        </p>
      <div className="flex items-center justify-between border-t border-surface-container-high pt-space-md">
          <span className="font-label-code text-label-code text-on-surface-variant">
            Framework Version: P0-MVP
          </span>
          <a
            href="#"
            className="inline-flex items-center gap-1 font-body-sm text-body-sm font-medium text-primary hover:underline"
          >
            View Planning Horizon
            <Icon name="arrow_forward" className="text-[16px]" />
          </a>
        </div>
      </div>
    </Card>
  );
}

export function DashboardView() {
  return (
    <>
      <NoticeBanner
        icon="biotech"
        tone="neutral"
        title={
          <span className="flex flex-wrap items-center gap-space-xs">
            Prototype Notice
            <ProvenanceBadge provenance="example" label="FR-FE-004 · OP-005" />
          </span>
        }
        action={
          <a
            href="#"
            className="inline-flex items-center gap-1 font-body-sm text-body-sm text-secondary hover:underline"
          >
            Review Audit Log
            <Icon name="arrow_forward" className="text-[16px]" />
          </a>
        }
      >
        Visual demonstration with example data. Financial calculations and backend
        integration pending advisory engineering sign-off.
      </NoticeBanner>

      <CompletenessBanner />

      <div className="flex flex-col gap-space-md md:flex-row md:items-end md:justify-between">
        <div>
          <SectionLabel>
            {HEADLINE.eyebrow} • {HEADLINE.tier}
          </SectionLabel>
          <h1 className="font-headline-lg text-headline-lg font-bold tracking-tight text-primary">
            {HEADLINE.title}
          </h1>
        </div>
        <SourceBar />
      </div>

      <div className="grid grid-cols-1 gap-space-lg sm:grid-cols-2 xl:grid-cols-4">
        {METRICS.map((metric) => (
          <MetricCard
            key={metric.id}
            {...metric}
            footer={
              metric.id === "net-worth" ? (
                <LineChart
                  height={44}
                  ariaLabel="30-day rolling liquidity trajectory"
                  series={[
                    {
                      points: LIQUIDITY_TRAJECTORY,
                      color: "#1b4332",
                      area: true,
                    },
                  ]}
                />
              ) : undefined
            }
          />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-space-lg lg:grid-cols-2">
        <AgentObservation />
        <CompletenessSources />
      </div>

      <div className="grid grid-cols-1 gap-space-lg lg:grid-cols-2">
        <ActiveGoals />
        <StrategyCard />
      </div>

      <div className="rounded-lg bg-surface-container-low p-space-lg">
        <div className="mb-space-md flex items-center gap-space-sm">
          <Icon name="gavel" className="text-secondary" />
          <span className="font-title-md text-title-md text-on-surface">
            Important Regulatory &amp; Non-Advisory Notice
          </span>
        </div>
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          {REGULATORY_NOTICE}
        </p>
        <p className="mt-space-sm font-label-code text-label-code text-on-surface-variant">
          FR-FE-007 Compliance Verified • AC-026 Standard Disclaimer Affirmation
          • Record ID: PW-2025-004-DEMO
        </p>
      </div>
    </>
  );
}
