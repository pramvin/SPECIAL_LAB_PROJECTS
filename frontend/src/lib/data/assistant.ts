import type {
  Assumption,
  ChatMessage,
  ModelInput,
  RationaleStep,
} from "../types";

/**
 * Assistant workspace mock data — synthetic example data only.
 * "Generated guidance" is a visual placeholder; no AI call is made and no
 * API contract exists yet (OVERVIEW.md §8 note).
 */

export const ASSISTANT_HEADER = {
  title: "AI Agent Assistant",
  disclaimer:
    "Generated guidance with visible assumptions. Not certified financial advice.",
  scenario: "Scenario: Baseline Plan (Home + Buffer)",
  provenanceNote: "Traceability: 100% Deterministic",
};

export const SUGGESTED_PROMPTS: string[] = [
  "How does an extra $200/mo impact my down payment goal?",
  "What assumptions are used?",
];

export const VERIFICATION_NOTE =
  "Deterministic forecast • Model Rev. 4.2";

export const USER_QUESTION =
  "If I reallocate $250 from discretionary spending into my home down payment " +
  "fund, when can I realistically reach $90k?";

export const ANSWER = {
  headline: "Reallocating $250/month accelerates your completion by 8 months.",
  body:
    "Reallocating $250/month increases your combined monthly allocation to " +
    "$1,050. Under your current model inputs, you would reach your $90,000 " +
    "down payment target approximately 8 months earlier: October 2028 instead " +
    "of June 2029.",
  stats: [
    { label: "Accelerated Date", value: "Oct 2028", sub: "8 Mo Advantage" },
    { label: "New Monthly Pacing", value: "$1,050/mo", sub: "+$250 Discretionary Shift" },
    { label: "Compounded Interest", value: "$5,840", sub: "At 4.0% Benchmark APY" },
  ],
  caveat:
    "Caveat: Taxes on interest earnings are not deducted in this baseline " +
    "snapshot. Real estate asset price inflation in target zip codes is not " +
    "dynamically forecasted.",
};

export const ASSUMPTIONS: Assumption[] = [
  { label: "Current Balance", value: "$45,000", provenance: "input" },
  { label: "Monthly Deposit", value: "$800", provenance: "input" },
  { label: "Hypothetical Shift", value: "+$250", provenance: "ai" },
  { label: "Annual Benchmark Yield", value: "4.0% APY", provenance: "example" },
];

export const MODEL_INPUTS: ModelInput[] = [
  {
    id: "inflation",
    label: "Inflation Assumption",
    value: "2.80%",
    note: "annually • Fed Target Baseline",
  },
  {
    id: "cash-apy",
    label: "High-Yield Cash APY",
    value: "4.00%",
    note: "liquid yield • Treasury-Linked Index",
  },
  {
    id: "growth",
    label: "Investment Growth",
    value: "6.50%",
    note: "nominal • Conservative 60/40 Equity Mix",
  },
  {
    id: "tax",
    label: "Tax Bracket Estimate",
    value: "22.0%",
    note: "marginal • Single Filer Tier",
  },
];

export const RATIONALE: RationaleStep[] = [
  {
    title: "Discretionary Audit",
    body:
      "Dining and entertainment expenses averaged $610/mo over the past 90 days, " +
      "confirming the $250 reallocation maintains a safe discretionary buffer.",
  },
  {
    title: "Reserve Preservation",
    body:
      "This increase does not touch the 6-month core liquid emergency cushion " +
      "($24,000 kept inviolate).",
  },
];

export const ACTION_STEP =
  "Update auto-transfer schedule from Primary Checking to High-Yield Vault on " +
  "the 1st of each month.";

export const GOAL_TARGET_SUMMARY = {
  title: "Goal Target Summary",
  label: "Down Payment Goal",
  target: 90000,
  funded: 45000,
  fundedPct: 50,
  targetDate: "2028-10-01",
};

export const PORTFOLIO_IMPACT: { baseline: number[]; reallocated: number[] } = {
  baseline: [45000, 47000, 50000, 54000, 59000, 64000, 70000, 76000, 82000, 90000],
  reallocated: [45000, 48500, 52500, 57500, 63500, 70000, 77000, 84000, 90000, 96000],
};

/** Conversation history used to render the transcript. */
export const MESSAGES: ChatMessage[] = [
  {
    id: "u1",
    role: "user",
    body: USER_QUESTION,
    timestamp: "09:42 AM",
  },
  {
    id: "a1",
    role: "assistant",
    headline: ANSWER.headline,
    body: ANSWER.body,
    verification: VERIFICATION_NOTE,
    stats: ANSWER.stats,
    timestamp: "09:42 AM",
  },
];
