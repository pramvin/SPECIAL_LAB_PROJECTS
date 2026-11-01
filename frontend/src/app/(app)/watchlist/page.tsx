import { WatchlistView } from "@/components/watchlist/watchlist";
import { getWatchlist } from "@/lib/watchlist";

export default async function WatchlistPage() {
  const items = await getWatchlist();
  return <WatchlistView initial={items} />;
}