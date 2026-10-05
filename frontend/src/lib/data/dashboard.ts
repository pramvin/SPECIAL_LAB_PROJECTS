import type { Metric } from "../types";

/**
 * Dashboard mock data. Every figure is synthetic and labeled with provenance.
 * Replace this module with API data later — the UI reads only these exports.
 */

export const HEADLINE = {
  eyebrow: "Portfolio Snapshot",
  tier: "Baseline Tier 1",
  title: "Financial Overview",
  auditedLabel: "Audited UTC 14:22",
  updatedLabel: "Updated 2 days ago",
};

export const METRICS: Metric[] = [
  {
    id: "net-worth",
    label: "Estimated Net Worth",
    value: "$142,500",
    provenance: "example",
    delta: "Trajectory +3.4% YoY",
    deltaTone: "positive",
    caption: "Updated 2 days ago",
  },
  {
    id: "surplus",
    label: "Monthly Cash Surplus",
    value: "$1,250",
    unit: "/mo",
    provenance: "input",
    delta: "+$250 above target benchmark",
    deltaTone: "positive",
    caption: "Allocated: $950 Discretionary",
  },
  {
    id: "emergency",
    label: "Emergency Reserve",
    value: "4.5 months",
    provenance: "example",
    caption: "Target: 6.0 months ($24,000)",
  },
  {
    id: "dti",
    label: "Debt-to-Income (DTI)",
    value: "18%",
    provenance: "example",
    caption: "Front-End: 14% • Back-End: 18%",
  },
];

/** Illustrative 30-day rolling liquidity trajectory (arbitrary units). */
export const LIQUIDITY_TRAJECTORY: number[] = [
  118000, 119500, 121000, 120200, 123000, 124800, 124000, 126500, 128000,
  130500, 129800, 132000,
];

export const HEADLINE_METRIC = {
  value: "$142,500",
  delta: "+4.2% YTD",
};

export const AGENT_INSIGHT = {
  title: "Agent Insight",
  badgeLabel: "AI Draft Analysis",
  body:
    "Increasing your emergency allocation by $300/mo reaches your 6-month safety " +
    "buffer by May 2027 instead of October 2027.",
  assumptions: ["HYSA 4.0%", "Inflation 2.8%"],
};

export const PERSONALIZED_STRATEGY = {
  tag: "Personalized Strategy",
  title: "Q2 Strategic Allocation Review",
};
