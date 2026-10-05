import type { Goal, Milestone } from "../types";

/**
 * Goals mock data — synthetic example data only (OVERVIEW.md §7).
 * Progress rules and formulas remain TBD and are owned by the future domain
 * layer (OVERVIEW.md §8). The UI displays, and does not compute, these values.
 */

export const GOALS_SUMMARY = {
  eyebrow: "Capital Milestones",
  activePoolsLabel: "2 Active Target Pools",
  title: "Financial Goals",
  totalSaved: 63000,
  activeCount: 2,
  pausedCount: 0,
  archivedCount: 1,
  velocity: 1200,
  combinedTarget: 114000,
  aggregateFundedPct: 55.2,
};

export const GOALS: Goal[] = [
  {
    id: "emergency-fund",
    title: "Emergency Fund",
    subtitle: "Allocated to High Yield Liquidity Pool",
    status: "on-track",
    statusLabel: "On Track",
    current: 18000,
    target: 24000,
    monthlyContribution: 400,
    targetDate: "2027-10-01",
    accent: "primary",
    provenance: "example",
    meta: [
      { label: "Liquidity Tier", value: "Tier 1" },
      { label: "Custody", value: "Morgan Stanley Private Wealth" },
      { label: "Assumed Yield", value: "4.2% APY" },
    ],
  },
  {
    id: "home-down-payment",
    title: "Home Down Payment",
    subtitle: "Primary Residence Acquisition Fund",
    status: "behind",
    statusLabel: "Behind pace by 3 months",
    current: 45000,
    target: 90000,
    monthlyContribution: 800,
    targetDate: "2029-06-01",
    accent: "secondary",
    provenance: "ai",
    meta: [
      { label: "Recommended", value: "+$150/mo" },
      { label: "Index Portfolio", value: "Assumed Return 6.8%" },
      { label: "Re-forecasted", value: "2 days ago" },
    ],
  },
];

export const DRAFT_GOAL = {
  title: "Custom Goal Draft",
  statusLabel: "Incomplete",
  refCode: "FR-FE-011",
  subtitle: "Created yesterday by Alex Morgan • Lacks target amortization schedule",
  name: "Post-Grad Fund",
  steps: [
    { label: "1. Title & Category", value: "Post-Grad Fund", done: true },
    { label: "2. Target Capital", value: "$35,000", done: true },
    {
      label: "3. Contribution Cadence",
      value: "Missing Value",
      done: false,
    },
    { label: "4. Strategy Risk", value: "Unselected", done: false },
  ],
  note:
    "Incomplete goals do not participate in active net-worth forecasting or " +
    "automated ledger transfers.",
};

export const MILESTONES: Milestone[] = [
  { period: "Q4 2024", amount: 21200, growthPct: 8.4 },
  { period: "Q2 2025", amount: 33400, growthPct: 14.1 },
  { period: "Q4 2026", amount: 63000, growthPct: 28.0 },
];

export const ADVISORY_GUIDELINE = {
  title: "Advisory Guideline",
  body:
    "Per the Morgan Wealth Framework, cash reserve goals should maintain a " +
    "liquidity variance under 1.5% while real estate goals should absorb index " +
    "drawdown simulations of up to 12%.",
  revision: "Q3-2025",
};
