import { cookies } from "next/headers";

/** One searchable instrument: an S&P 500 stock or the SCHD / QQQ ETF. */
export interface Instrument {
  ticker: string;
  name: string;
  kind: "stock" | "etf";
  /** Onboarding sector key (tech, finance, ...). null for ETFs. */
  sector: string | null;
  /** GICS sector name, e.g. "Information Technology". null for ETFs. */
  gics_sector: string | null;
  /** Last daily close from the prices table; null when we have no bars. */
  price: number | null;
  change: number | null;
  change_pct: number | null;
  price_date: string | null;
  in_watchlist: boolean;
}

export interface WatchlistItem extends Instrument {
  added_at: number;
}

export type SearchGroup = "all" | "sp500" | "etf";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/** The signed-in user's saved watchlist, or null if it could not be loaded. Server-side only. */
export async function getWatchlist(): Promise<WatchlistItem[] | null> {
  const session = (await cookies()).get("session")?.value;
  if (!session) return null;
  try {
    const res = await fetch(`${BACKEND_URL}/api/watchlist`, {
      headers: { cookie: `session=${session}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return ((await res.json()) as { items: WatchlistItem[] }).items;
  } catch {
    return null;
  }
}
