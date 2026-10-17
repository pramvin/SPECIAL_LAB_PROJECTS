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
