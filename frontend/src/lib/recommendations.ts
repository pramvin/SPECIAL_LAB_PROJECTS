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
  is_example: boolean;
  as_of: string | null;
  llm: LlmAnalysis | null;
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
 * Real Google News headlines per ticker (from the backend pipeline), plus
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
