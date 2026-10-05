import type { Profile } from "../types";

/**
 * SYNTHETIC PROFILE — example data only (OVERVIEW.md §7).
 * Demo mode: no authentication, no real accounts, no stored credentials.
 */
export const PROFILE: Profile = {
  name: "Alex Morgan",
  tierLabel: "Private Wealth Tier",
  completenessPct: 75,
  incompleteReviewCount: 2,
};

export const SOURCE_NOTE = "Source: User-Entered & Demo Model";

export const REGULATORY_NOTICE =
  "This system is an exploratory financial planning demonstration using synthetic " +
  "client profiles and user-entered approximations. All calculations, projections, " +
  "and AI-generated observations are strictly for educational and illustrative " +
  "purposes. PlanWise AI is not a registered investment advisor, broker-dealer, tax " +
  "specialist, or fiduciary. No output constitutes a formal recommendation, financial " +
  "endorsement, legal counsel, or solicitation. Always consult an accredited financial " +
  "planner, CPA, or registered fiduciary before executing real-world capital " +
  "reallocations or commitments.";
