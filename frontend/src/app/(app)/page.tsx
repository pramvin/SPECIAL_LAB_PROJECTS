import { IdeasView } from "@/components/ideas/IdeasView";
import {
  getDataStatus,
  getLatestNews,
  getQuotes,
  getRecommendations,
  type Horizon,
} from "@/lib/recommendations";
import { getMe } from "@/lib/session";
import { getWatchlist } from "@/lib/watchlist";
import { getPortfolio } from "@/lib/wallet";

const VALID: Horizon[] = ["1w", "1m", "3m"];

export default async function IdeasPage({
  searchParams,
}: {
  searchParams: Promise<{ h?: string }>;
}) {
  const { h } = await searchParams;
  const me = await getMe();
  const fallback = (me?.profile?.horizon as Horizon | undefined) ?? "1m";
  const horizon = VALID.includes(h as Horizon) ? (h as Horizon) : fallback;
  const [items, latestNews, dataStatus] = await Promise.all([
    getRecommendations(horizon),
    getLatestNews(10),
    getDataStatus(),
  ]);
  const quotes = await getQuotes((items ?? []).map((r) => r.ticker));
  const [portfolio, watchlist] = await Promise.all([
    getPortfolio(),
    getWatchlist(),
  ]);
  return (
    <IdeasView
      horizon={horizon}
      items={items}
      latestNews={latestNews}
      quotes={quotes}
      dataStatus={dataStatus}
      portfolio={portfolio}
      watchlist={new Set((watchlist ?? []).map((w) => w.ticker))}
    />
  );
}
