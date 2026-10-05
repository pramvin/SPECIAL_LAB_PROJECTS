"use client";

import { useState } from "react";
import { Card, CardHeader, SectionLabel } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { ProvenanceBadge } from "@/components/ui/ProvenanceBadge";
import { GoalCard } from "./GoalCard";
import { CreateGoalDrawer } from "./CreateGoalDrawer";
import {
  ADVISORY_GUIDELINE,
  DRAFT_GOAL,
  GOALS,
  GOALS_SUMMARY,
} from "@/lib/data/goals";
import { formatCurrency } from "@/lib/format";

type Tab = "active" | "paused" | "archived";

const TABS: { id: Tab; label: string; count: number }[] = [
  { id: "active", label: "Active", count: GOALS_SUMMARY.activeCount },
  { id: "paused", label: "Paused", count: GOALS_SUMMARY.pausedCount },
  { id: "archived", label: "Archived", count: GOALS_SUMMARY.archivedCount },
];

function DraftGoalCard() {
  return (
    <Card className="flex flex-col gap-space-md">
      <CardHeader
        icon="edit_note"
        title={DRAFT_GOAL.title}
        subtitle={DRAFT_GOAL.subtitle}
        badge={
          <ProvenanceBadge
            provenance="ai"
            label={`${DRAFT_GOAL.refCode} Incomplete State`}
          />
        }
        action={
          <Button variant="secondary" size="sm">
            Resume Setup
          </Button>
        }
      />
      <div className="grid grid-cols-2 gap-space-md lg:grid-cols-4">
        {DRAFT_GOAL.steps.map((step) => (
          <div
            key={step.label}
            className="flex flex-col gap-1 rounded-md border border-surface-container-high p-space-sm"
          >
            <span className="flex items-center justify-between font-label-code text-label-code uppercase tracking-wide text-on-surface-variant">
              {step.label}
              <Icon
                name={step.done ? "check" : "radio_button_unchecked"}
                className={`text-[14px] ${step.done ? "text-primary" : "text-on-surface-variant"}`}
              />
            </span>
            <span
              className={`font-body-sm text-body-sm ${
                step.done ? "text-on-surface" : "text-error"
              }`}
            >
              {step.value}
            </span>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-space-sm border-t border-surface-container-high pt-space-sm">
        <span className="font-body-sm text-body-sm text-on-surface-variant">
          {DRAFT_GOAL.note}
        </span>
        <button
          type="button"
          className="font-body-sm text-body-sm font-medium text-error hover:underline"
        >
          Discard Draft
        </button>
      </div>
    </Card>
  );
}

export function GoalsView() {
  const [tab, setTab] = useState<Tab>("active");
  const [drawerOpen, setDrawerOpen] = useState(false);

  const visibleGoals = tab === "active" ? GOALS : [];
  const emptyCopy: Record<Tab, string> = {
    active: "No active goals yet.",
    paused: "No paused goals. Pausing is a decision your team must support.",
    archived: "Archived goals appear here once that workflow is approved.",
  };

  return (
    <>
      <div className="flex flex-col gap-space-md lg:flex-row lg:items-end lg:justify-between">
        <div className="flex flex-col gap-1">
          <SectionLabel>
            {GOALS_SUMMARY.eyebrow} • {GOALS_SUMMARY.activePoolsLabel}
          </SectionLabel>
          <h1 className="font-headline-lg text-headline-lg font-bold tracking-tight text-primary">
            {GOALS_SUMMARY.title}
          </h1>
          <p className="font-headline-sm text-headline-sm text-on-surface">
            {formatCurrency(GOALS_SUMMARY.totalSaved)} saved across{" "}
            {GOALS_SUMMARY.activeCount} active goals
          </p>
          <p className="max-w-2xl font-body-sm text-body-sm text-on-surface-variant">
            Track progress, simulate timelines, and inspect calculation
            parameters against institutional forecasting standards.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-space-sm">
          <div
            role="tablist"
            aria-label="Goal status"
            className="flex items-center gap-1 rounded-lg border border-surface-container-high bg-surface-container-lowest p-1"
          >
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => setTab(t.id)}
                className={`inline-flex items-center gap-1.5 rounded-md px-space-md py-1.5 font-body-sm text-body-sm transition-colors ${
                  tab === t.id
                    ? "bg-primary-container text-on-primary"
                    : "text-on-surface-variant hover:bg-surface-container-low"
                }`}
              >
                {t.label}
                <span className="font-label-code text-label-code opacity-80">
                  {t.count}
                </span>
              </button>
            ))}
          </div>
          <Button icon="add" onClick={() => setDrawerOpen(true)}>
            Create New Goal
          </Button>
        </div>
      </div>

      <Card className="flex flex-col gap-space-md lg:flex-row lg:items-center lg:gap-space-xl">
        <div className="flex flex-1 items-center gap-space-md">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-secondary-fixed text-secondary">
            <Icon name="speed" />
          </span>
          <div className="flex flex-col">
            <span className="font-label-code text-label-code uppercase tracking-wide text-on-surface-variant">
              Portfolio Target Velocity
            </span>
            <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
              {formatCurrency(GOALS_SUMMARY.velocity)}
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                /month
              </span>{" "}
              <span className="font-label-code text-label-code text-on-surface-variant">
                Aggregated Auto-Debit
              </span>
            </span>
          </div>
        </div>
        <div className="flex flex-col">
          <span className="font-label-code text-label-code uppercase tracking-wide text-on-surface-variant">
            Combined Target
          </span>
          <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
            {formatCurrency(GOALS_SUMMARY.combinedTarget, { decimals: 2 })}
          </span>
        </div>
        <div className="flex w-full max-w-[240px] flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="font-label-code text-label-code uppercase tracking-wide text-on-surface-variant">
              Aggregate Funded
            </span>
            <span className="font-title-md text-title-md tabular-nums text-primary">
              {GOALS_SUMMARY.aggregateFundedPct}%
            </span>
          </div>
          <ProgressBar value={GOALS_SUMMARY.aggregateFundedPct} size="sm" />
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-space-lg xl:grid-cols-[2fr_1fr]">
        <div className="flex flex-col gap-space-lg">
          {visibleGoals.length > 0 ? (
            visibleGoals.map((goal) => <GoalCard key={goal.id} goal={goal} />)
          ) : (
            <Card className="flex flex-col items-center gap-space-sm py-space-xl text-center">
              <Icon
                name="inbox"
                className="text-[32px] text-on-surface-variant"
              />
              <span className="font-title-md text-title-md text-on-surface">
                {emptyCopy[tab]}
              </span>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                Example data only.
              </span>
            </Card>
          )}
          <DraftGoalCard />
        </div>

        <div className="flex flex-col gap-space-lg">
          <Card className="flex flex-col gap-space-md">
            <div className="flex items-center justify-between">
              <span className="font-label-code text-label-code uppercase tracking-wider text-on-surface-variant">
                Interactive Modal / Drawer
              </span>
              <span className="inline-flex items-center gap-1 font-body-sm text-body-sm text-on-surface-variant">
                <Icon name="touch_app" className="text-[16px]" />
                Create Goal
              </span>
            </div>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Open the create-goal drawer to review the prototype form,
              validation states, and calculation disclosure.
            </p>
            <Button
              variant="secondary"
              icon="open_in_new"
              onClick={() => setDrawerOpen(true)}
            >
              Open Create Goal Drawer
            </Button>
          </Card>

          <Card className="flex flex-col gap-space-sm">
            <CardHeader
              icon="verified"
              title={ADVISORY_GUIDELINE.title}
              subtitle="Illustrative guideline, not personalized advice."
            />
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              {ADVISORY_GUIDELINE.body}
            </p>
            <div className="flex items-center justify-between border-t border-surface-container-high pt-space-sm">
              <span className="font-label-code text-label-code text-on-surface-variant">
                Guideline Rev: {ADVISORY_GUIDELINE.revision}
              </span>
              <a
                href="#"
                className="font-body-sm text-body-sm font-medium text-primary hover:underline"
              >
                View Allocation Policy
              </a>
            </div>
          </Card>
        </div>
      </div>

      <CreateGoalDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  );
}
