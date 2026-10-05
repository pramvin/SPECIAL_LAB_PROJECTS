/**
 * Domain types for the PlanWise AI frontend prototype.
 *
 * NOTE: All financial reasoning and calculation is owned by the future
 * backend/domain layer (see OVERVIEW.md §8). These types describe what the
 * UI renders, not how figures are computed. Every numeric value rendered in
 * the prototype is synthetic example data (OVERVIEW.md §7).
 */

/** Where a displayed value came from — surfaced to the user for trust. */
export type Provenance = "input" | "ai" | "example" | "warning";

export type GoalStatus = "on-track" | "behind" | "paused" | "draft" | "archived";

export interface Profile {
  name: string;
  tierLabel: string;
  completenessPct: number;
  incompleteReviewCount: number;
}

export interface Metric {
  id: string;
  label: string;
  value: string;
  unit?: string;
  delta?: string;
  deltaTone?: "positive" | "negative" | "neutral";
  caption?: string;
  provenance: Provenance;
}

export interface Goal {
  id: string;
  title: string;
  subtitle: string;
  status: GoalStatus;
  statusLabel: string;
  current: number;
  target: number;
  monthlyContribution: number;
  targetDate: string;
  accent: "primary" | "secondary";
  provenance: Provenance;
  meta: { label: string; value: string }[];
}

export interface Milestone {
  period: string;
  amount: number;
  growthPct: number;
}

export interface ModelInput {
  id: string;
  label: string;
  value: string;
  note: string;
}

export interface Assumption {
  label: string;
  value: string;
  provenance: Provenance;
}

export interface RationaleStep {
  title: string;
  body: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  body?: string;
  headline?: string;
  verification?: string;
  stats?: { label: string; value: string; unit?: string }[];
  steps?: RationaleStep[];
  timestamp: string;
}
