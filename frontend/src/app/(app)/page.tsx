import { IdeasView } from "@/components/ideas/IdeasView";
import { getRecommendations, getTopNews, type Horizon } from "@/lib/recommendations";
import { getMe } from "@/lib/session";

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
  const [items, topNews] = await Promise.all([
    getRecommendations(horizon),
    getTopNews(),
  ]);
  return <IdeasView horizon={horizon} items={items} topNews={topNews} />;
}
