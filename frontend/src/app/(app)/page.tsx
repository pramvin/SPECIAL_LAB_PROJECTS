import { IdeasView } from "@/components/ideas/IdeasView";
import {
  getDataStatus,
  getLatestNews,
  getQuotes,
  getRecommendations,
  type Horizon,
} from "@/lib/recommendations";
import { getWatchlist } from "@/lib/watchlist";
import { getPortfolio } from "@/lib/wallet";

// Only the 1 week view is open for now; 1 month and 3 months show "Coming soon" and cannot be picked.
const horizon: Horizon = "1w";

export default async function IdeasPage() {
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
