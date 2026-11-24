import { cookies } from "next/headers";

export type Horizon = "1w" | "1m" | "3m";

export const HORIZONS: { value: Horizon; label: string }[] = [
  { value: "1w", label: "1 week" },
  { value: "1m", label: "1 month" },
  { value: "3m", label: "3 months" },
];

/** Label attached to a headline by the local sentiment model. */
export type Sentiment = "positive" | "neutral" | "negative";

export interface NewsHeadline {
  title: string;
  source: string;
  url?: string;
  published?: string;
  published_at?: string;
  sentiment?: Sentiment | null;
}

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
  /** The 3 newest headlines for this ticker, already sentiment-labeled. */
  news: NewsHeadline[];
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
}

export interface Quote {
  price: number;
  /** Timestamp of the latest 1-minute bar (ISO, with offset). */
  quote_time: string;
}

export interface DataStatus {
  server_time: string;
  news_updated_at: string | null;
  news_count: number;
  sentiment_updated_at: string | null;
  recommendations_generated_at: string | null;
}

export interface LatestNewsItem {
  ticker: string;
  name: string;
  title: string;
  source: string;
  url: string;
  published_at: string;
  sentiment: Sentiment | null;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  price_date: string | null;
}

export interface LatestNews {
  items: LatestNewsItem[];
  refreshed_at: string | null;
}

export interface PriceBar {
  date: string;
  close: number;
  volume: number;
}

export interface Prices {
  ticker: string;
  name: string;
  /** Oldest first. */
  bars: PriceBar[];
  price: number;
  change: number;
  change_pct: number;
}

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

async function backendGet<T>(path: string): Promise<T | null> {
  const session = (await cookies()).get("session")?.value;
  if (!session) return null;
  try {
    const res = await fetch(`${BACKEND_URL}${path}`, {
      headers: { cookie: `session=${session}` },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}

export async function getRecommendations(
  horizon: Horizon,
): Promise<Recommendation[] | null> {
  const data = await backendGet<{ items: Recommendation[] }>(
    `/api/recommendations?horizon=${horizon}`,
  );
  return data?.items ?? null;
}

export async function getQuotes(
  tickers: string[],
): Promise<Record<string, Quote>> {
  if (tickers.length === 0) return {};
  const data = await backendGet<{ quotes: Record<string, Quote> }>(
    `/api/quotes?tickers=${encodeURIComponent(tickers.slice(0, 30).join(","))}`,
  );
  return data?.quotes ?? {};
}

/** Newest headlines for the served stocks, with the last close and its daily change. */
export async function getLatestNews(limit = 10): Promise<LatestNews | null> {
  return backendGet<LatestNews>(`/api/latest-news?limit=${limit}`);
}

/** Daily closes (oldest first) for one ticker; null when unknown or unavailable. */
export async function getPrices(
  ticker: string,
  days = 60,
): Promise<Prices | null> {
  return backendGet<Prices>(
    `/api/prices/${encodeURIComponent(ticker)}?days=${days}`,
  );
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
