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
    <Card className="flex flex-col gap-6">
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
            Resume setup
          </Button>
        }
      />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {DRAFT_GOAL.steps.map((step) => (
          <div
            key={step.label}
            className="flex flex-col gap-1 rounded-xl bg-surface-container-low p-4"
          >
            <span className="flex items-center justify-between font-body-sm text-body-sm text-on-surface-variant">
              {step.label}
              <Icon
                name={step.done ? "check" : "radio_button_unchecked"}
                className={`text-[15px] ${step.done ? "text-tertiary-accent" : "text-on-surface-variant"}`}
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
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-container-high pt-5">
        <span className="font-body-sm text-body-sm text-on-surface-variant">
          {DRAFT_GOAL.note}
        </span>
        <button
          type="button"
          className="font-body-sm text-body-sm font-medium text-error hover:underline"
        >
          Discard draft
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
      <header className="flex flex-col gap-6">
        <div className="flex flex-col gap-3">
          <SectionLabel>
            {GOALS_SUMMARY.eyebrow} · {GOALS_SUMMARY.activePoolsLabel}
          </SectionLabel>
          <h1 className="max-w-3xl font-headline-lg text-headline-lg-mobile tracking-tight text-on-surface sm:text-headline-lg">
            {GOALS_SUMMARY.title}
          </h1>
          <p className="max-w-2xl font-body-lg text-body-lg text-on-surface-variant">
            {formatCurrency(GOALS_SUMMARY.totalSaved)} saved across{" "}
            {GOALS_SUMMARY.activeCount} active goals. Track progress, simulate
            timelines, and inspect the assumptions behind each projection.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div
            role="tablist"
            aria-label="Goal status"
            className="inline-flex items-center rounded-full bg-surface-container-low p-1"
          >
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => setTab(t.id)}
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 font-body-sm text-body-sm font-medium transition-colors ${
                  tab === t.id
                    ? "bg-white text-on-surface shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                {t.label}
                <span className="text-on-surface-variant/70">{t.count}</span>
              </button>
            ))}
          </div>
          <Button icon="add" onClick={() => setDrawerOpen(true)}>
            Create goal
          </Button>
        </div>
      </header>

      <Card className="grid gap-8 md:grid-cols-3">
        <div className="flex flex-col gap-1">
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Portfolio target velocity
          </span>
          <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
            {formatCurrency(GOALS_SUMMARY.velocity)}
            <span className="ml-1 font-body-sm text-body-sm text-on-surface-variant">
              /month
            </span>
          </span>
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Aggregated automatic debit
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Combined target
          </span>
          <span className="font-metric-md text-metric-md tabular-nums text-on-surface">
            {formatCurrency(GOALS_SUMMARY.combinedTarget, { decimals: 2 })}
          </span>
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Across all active goals
          </span>
        </div>
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Aggregate funded
            </span>
            <span className="font-title-md text-title-md tabular-nums text-tertiary-accent">
              {GOALS_SUMMARY.aggregateFundedPct}%
            </span>
          </div>
          <ProgressBar value={GOALS_SUMMARY.aggregateFundedPct} size="md" />
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Example data only
          </span>
        </div>
      </Card>

      <section className="flex flex-col gap-6">
        {visibleGoals.length > 0 ? (
          <div className="grid gap-6 lg:grid-cols-2">
            {visibleGoals.map((goal) => (
              <GoalCard key={goal.id} goal={goal} />
            ))}
          </div>
        ) : (
          <Card className="flex flex-col items-center gap-3 py-16 text-center">
            <Icon name="inbox" className="text-[32px] text-on-surface-variant" />
            <span className="font-title-md text-title-md text-on-surface">
              {emptyCopy[tab]}
            </span>
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Example data only.
            </span>
          </Card>
        )}
        <DraftGoalCard />
      </section>

      <Card className="flex flex-col gap-3">
        <CardHeader
          icon="verified"
          title={ADVISORY_GUIDELINE.title}
          subtitle="Illustrative guideline, not personalized advice."
        />
        <p className="max-w-3xl font-body-md text-body-md text-on-surface-variant">
          {ADVISORY_GUIDELINE.body}
        </p>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-container-high pt-4">
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            Guideline revision {ADVISORY_GUIDELINE.revision}
          </span>
          <a
            href="#"
            className="font-body-sm text-body-sm font-medium text-tertiary-accent hover:underline"
          >
            View allocation policy
          </a>
        </div>
      </Card>

      <CreateGoalDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  );
}
