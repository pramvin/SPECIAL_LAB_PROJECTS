import { cookies } from "next/headers";

export type Horizon = "1w" | "1m" | "3m";

export const HORIZONS: { value: Horizon; label: string }[] = [
  { value: "1w", label: "1 week" },
  { value: "1m", label: "1 month" },
  { value: "3m", label: "3 months" },
];

export interface Recommendation {
  ticker: string;
  name: string;
  sector: string;
  horizon: Horizon;
  action: "BUY";
  entry: number;
  stop: number;
  target: number;
  score: number;
  reasons: string[];
  news: { title: string; source: string; url?: string; published?: string; published_at?: string; sentiment?: string | null }[];
  stop_distance_pct: number;
  upside_pct: number;
  position_pct: number;
  loss_at_stop_pct: number;
  matches_interest: boolean;
  /** Cosine fit to the user's answers (0..1); null when no profile is saved yet. */
  fit: number | null;
  match_reasons: string[];
  is_example: boolean;
  as_of: string | null;
  /** Chance of a top-20% 5-day move (0..1); null when no model or horizon is not 1w. */
  bigmove_p: number | null;
  llm: LlmAnalysis | null;
  /** Newest AI review for this ticker + horizon; null when none has run yet. */
  ai: AiSummary | null;
}

export type Rating =
  | "Buy"
  | "Overweight"
  | "Hold"
  | "Underweight"
  | "Sell"
  | "REVIEW";

export type Signal = "bullish" | "neutral" | "bearish" | "no_data";

export type Agrees = "agree" | "caution" | "disagree" | "review";

export type SourceStatus = {
  status: "ok" | "unavailable" | "skipped";
  reason?: string;
};

export type Light = "green" | "amber" | "red";

/** The plain-language block of the AI card; absent or empty on reviews stored before it existed. */
export interface AiVerdictFields {
  headline: string;
  checks: Partial<
    Record<"trend" | "business" | "news_market" | "risk", { light: Light; line: string }>
  >;
  how_to_act: string;
  change_if: string;
}

/** One line of the AI opinion shown on the ideas list. */
export interface AiSummary {
  run_id: number;
  /** "full" = the 12-agent review; "quick" = one-call triage (has confidence + points). */
  mode: "full" | "quick";
  confidence?: "low" | "medium" | "high";
  points?: Point[];
  verdict?: AiVerdictFields;
  rating: Rating;
  summary: string;
  agrees: Agrees;
  as_of: string;
  created_at: string;
  model: string;
}

export interface Point {
  text: string;
  evidence: string[];
}

export type EvidenceKind =
  | "news"
  | "metric"
  | "fund"
  | "sec"
  | "social"
  | "macro"
  | "rule"
  | "agent"
  | "memory";

export interface Evidence {
  id: string;
  kind: EvidenceKind;
  label: string;
  value?: string;
  url?: string;
  published_at?: string;
  sentiment?: string | null;
}

export interface AnalystReview {
  signal: Signal;
  summary: string;
  points: Point[];
  data_gaps: string[];
}

export interface ManagerView {
  lean: Rating;
  rationale: string;
  evidence: string[];
}

export interface TraderPlan {
  stance: "enter" | "wait" | "avoid";
  rationale: string;
  evidence: string[];
  suggested_stop: number | null;
  suggested_target: number | null;
}

export interface RiskView {
  view: string;
  suggested_position_pct: number | null;
  evidence: string[];
}

export interface TrackRecordEntry {
  as_of: string;
  rating: Rating;
  return_pct: number | null;
  benchmark_return_pct: number | null;
  alpha_pct: number | null;
  reflection: string | null;
}

/** Full AI review from `GET /api/agents/{ticker}`. */
export interface AgentReview {
  run_id: number;
  ticker: string;
  horizon: Horizon;
  as_of: string;
  model: string;
  deep_model: string;
  prompt_version: string;
  created_at: string;
  status: "ok" | "partial";
  sources: Record<
    "prices" | "news" | "fmp" | "sec" | "social" | "macro",
    SourceStatus
  >;
  review: {
    rating: Rating;
    summary: string;
    agrees: Agrees;
    key_risks: Point[];
    analysts: Record<
      "market" | "news" | "fundamentals" | "social",
      AnalystReview | null
    >;
    debate: {
      bull: Point[];
      bear: Point[];
      manager: ManagerView | null;
    };
    trader: TraderPlan | null;
    risk: Record<"aggressive" | "conservative" | "neutral", RiskView | null>;
    rules: { entry: number; stop: number; target: number; score: number };
  };
  evidence: Evidence[];
  track_record: TrackRecordEntry[];
}

export interface LlmAnalysis {
  direction: "up" | "down" | "none";
  magnitude: "low" | "medium" | "high";
  confidence: number;
  reasons: string[];
  caveats: string[];
  model: string;
  as_of: string;
  cited: { id: number; title: string; source: string; url?: string }[];
}

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function getRecommendations(
  horizon: Horizon,
): Promise<Recommendation[] | null> {
  const session = (await cookies()).get("session")?.value;
  if (!session) return null;
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/recommendations?horizon=${horizon}`,
      { headers: { cookie: `session=${session}` }, cache: "no-store" },
    );
    if (!res.ok) return null;
    return ((await res.json()) as { items: Recommendation[] }).items;
  } catch {
    return null;
  }
}

export interface Quote {
  price: number;
  /** Timestamp of the latest 1-minute bar (ISO, with offset). */
  quote_time: string;
}

export async function getQuotes(tickers: string[]): Promise<Record<string, Quote>> {
  const session = (await cookies()).get("session")?.value;
  if (!session || tickers.length === 0) return {};
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/quotes?tickers=${encodeURIComponent(tickers.slice(0, 30).join(","))}`,
      { headers: { cookie: `session=${session}` }, cache: "no-store" },
    );
    if (!res.ok) return {};
    return ((await res.json()) as { quotes: Record<string, Quote> }).quotes;
  } catch {
    return {};
  }
}

export interface TopNewsItem {
  ticker: string;
  name: string;
  title: string;
  source: string;
  url: string | null;
  published_at: string;
  sentiment?: string | null;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  price_date: string | null;
}

export async function getTopNews(): Promise<TopNewsItem[]> {
  const session = (await cookies()).get("session")?.value;
  if (!session) return [];
  try {
    const res = await fetch(`${BACKEND_URL}/api/top-news?limit=5`, {
      headers: { cookie: `session=${session}` },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as { items: TopNewsItem[] }).items : [];
  } catch {
    return [];
  }
}

export interface NewsSentimentItem {
  title: string;
  source: string;
  url: string;
  published_at: string;
  sentiment: "bullish" | "bearish" | "neutral" | null;
}

export interface TickerNewsSentiment {
  items: NewsSentimentItem[];
  distribution: {
    positive: number;
    neutral: number;
    negative: number;
    scored: number;
  } | null;
  has_sentiment: boolean;
}

/**
 * Real Yahoo Finance headlines per ticker (from the backend pipeline), plus
 * sentiment when the scoring model has been run. No synthetic fallback.
 */
export async function getNewsSentiment(
  tickers: string[],
): Promise<Record<string, TickerNewsSentiment>> {
  if (tickers.length === 0) return {};
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/news-sentiment?tickers=${encodeURIComponent(tickers.join(","))}&limit=3`,
      { cache: "no-store" },
    );
    if (!res.ok) return {};
    return ((await res.json()) as { tickers: Record<string, TickerNewsSentiment> })
      .tickers;
  } catch {
    return {};
  }
}

export interface DataStatus {
  server_time: string;
  news_updated_at: string | null;
  news_count: number;
  sentiment_updated_at: string | null;
  recommendations_generated_at: string | null;
}

/** Latest data-refresh times reported by the backend (null if unavailable). */
export async function getDataStatus(): Promise<DataStatus | null> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/data-status`, {
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as DataStatus) : null;
  } catch {
    return null;
  }
}
